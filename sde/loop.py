"""The dynamic investigation loop.

    observe -> hypothesise -> request evidence -> execute -> update -> stop?

The agent decides *what to look at next*; the orchestrator decides *whether it
may*. That split is the whole design. An agent proposing
``{"tool": "infernal_scan", "reason": "...", "inputs": {...}}`` is proposing an
experiment, and the orchestrator is the one that runs it, pays for it, and
writes down what came back.

A loop like this fails in three ways, and each has a guard here:

* **It never stops.** Bounded by iterations, by budget, and by a
  no-new-evidence counter.
* **It goes in circles.** A repeated tool call with identical inputs is
  refused and recorded, so "ask again" is not a strategy.
* **It spends everything on one candidate.** The budget is per candidate and
  declared up front.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from sde.registry import ToolCost, ToolRegistry, ToolRequest
from sde.state import CandidateState, Hypothesis


class Investigator(Protocol):
    """Whatever decides the next step. Usually a model; anything works."""

    name: str

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class StopReason:
    code: str
    detail: str


@dataclass(slots=True)
class InvestigationResult:
    state: CandidateState
    iterations: int
    stop: StopReason
    requests_made: int
    requests_refused: int


PROMPT = """\
You are investigating one candidate locus. You cannot run code. You may ask the
orchestrator to run one registered tool, and it will return the result to you.

What is known so far:
{observation}

Open hypotheses:
{hypotheses}

Tools you may request:
{catalogue}

Budget remaining: {budget}

Reply with a single JSON object and nothing else:

{{
  "observation": "<what stands out in the evidence above>",
  "hypotheses": [
    {{"statement": "...",
     "discriminating_evidence": "<what observation would tell this apart>",
     "confidence": 0.0}}
  ],
  "request": {{"tool": "<name>", "reason": "<why this, now>",
               "inputs": {{}}}},
  "stop": false,
  "stop_reason": ""
}}

Set "stop": true when further tools would not change the conclusion. Prefer
stopping over requesting something whose result you could already predict.
Do not propose a hypothesis you cannot say how to test.
"""


def render_observation(state: CandidateState) -> str:
    lines = [f"candidate: {state.candidate_id}", f"length: {len(state.sequence)}"]
    if state.features:
        lines.append("features:")
        for key in sorted(state.features):
            lines.append(f"  {key} = {state.features[key]}")
    ran = state.tools_run()
    if ran:
        lines.append(f"tools already run: {', '.join(sorted(set(ran)))}")
    return "\n".join(lines)


def render_hypotheses(state: CandidateState) -> str:
    if not state.open_hypotheses():
        return "  (none yet)"
    return "\n".join(
        f"  [{h.confidence:.2f}] {h.statement} (would be settled by: {h.discriminating_evidence})"
        for h in state.open_hypotheses()
    )


@dataclass(slots=True)
class InvestigationLoop:
    registry: ToolRegistry
    investigator: Investigator
    budget: int = 100
    max_iterations: int = 12
    max_barren_rounds: int = 3
    max_cost: ToolCost | None = None
    seen_keys: set[tuple] = field(default_factory=set)

    def run(self, state: CandidateState) -> InvestigationResult:
        made = refused = barren = 0
        stop = StopReason("exhausted_iterations", "loop hit max_iterations")

        iteration = 0
        for iteration in range(1, self.max_iterations + 1):  # noqa: B007
            remaining = self.budget - state.spent
            if remaining <= 0:
                stop = StopReason("budget_exhausted", f"spent {state.spent} of {self.budget}")
                break

            step = self._ask(state, remaining)
            self._absorb_hypotheses(state, step)

            if step.get("stop"):
                stop = StopReason("agent_stopped", str(step.get("stop_reason", "")).strip())
                break

            request = self._build_request(step)
            if request is None:
                refused += 1
                state.record(
                    "note", self.investigator.name, "no valid request produced", step=step
                )
                barren += 1
                if barren >= self.max_barren_rounds:
                    stop = StopReason("no_progress", f"{barren} rounds without new evidence")
                    break
                continue

            if state.has_run(request.tool, request.inputs) or request.key() in self.seen_keys:
                refused += 1
                state.record(
                    "note",
                    "orchestrator",
                    f"refused repeat of {request.tool} with identical inputs",
                    tool=request.tool,
                )
                barren += 1
                if barren >= self.max_barren_rounds:
                    stop = StopReason("no_progress", "agent repeated itself")
                    break
                continue

            spec_cost = self._cost_of(request)
            if spec_cost is not None and spec_cost > remaining:
                refused += 1
                state.record(
                    "note",
                    "orchestrator",
                    f"refused {request.tool}: costs {spec_cost}, {remaining} left",
                )
                stop = StopReason("budget_exhausted", f"cannot afford {request.tool}")
                break

            self.seen_keys.add(request.key())
            state.note_request(request, self.investigator.name)
            result = self.registry.execute(request)
            state.note_result(result)
            made += 1

            if result.ok and result.outputs:
                state.set_features(result.outputs, actor=f"tool:{result.tool}")
                barren = 0
            else:
                barren += 1
                if barren >= self.max_barren_rounds:
                    stop = StopReason("no_progress", f"{barren} rounds without new evidence")
                    break

        state.record(
            "note",
            "orchestrator",
            f"investigation stopped: {stop.code}",
            code=stop.code,
            detail=stop.detail,
        )
        return InvestigationResult(
            state=state,
            iterations=iteration,
            stop=stop,
            requests_made=made,
            requests_refused=refused,
        )

    # -- internals ------------------------------------------------------
    def _ask(self, state: CandidateState, remaining: int) -> dict[str, Any]:
        catalogue = self.registry.describe(self.max_cost)
        try:
            step = self.investigator.next_step(state, catalogue)
        except Exception as error:  # noqa: BLE001 - an agent failure is data
            state.record(
                "note", self.investigator.name, f"investigator failed: {error}"
            )
            return {"stop": True, "stop_reason": f"investigator error: {error}"}
        return step if isinstance(step, dict) else {"stop": True, "stop_reason": "bad reply"}

    def _absorb_hypotheses(self, state: CandidateState, step: dict[str, Any]) -> None:
        for raw in step.get("hypotheses") or []:
            if not isinstance(raw, dict):
                continue
            try:
                state.add_hypothesis(
                    Hypothesis(
                        statement=str(raw.get("statement", "")),
                        proposed_by=self.investigator.name,
                        discriminating_evidence=str(raw.get("discriminating_evidence", "")),
                        confidence=float(raw.get("confidence", 0.5)),
                    )
                )
            except (ValueError, TypeError) as error:
                # A malformed or untestable hypothesis is rejected and recorded,
                # never silently accepted at face value.
                state.record(
                    "note",
                    "orchestrator",
                    f"rejected hypothesis: {error}",
                    raw=str(raw)[:300],
                )

    def _build_request(self, step: dict[str, Any]) -> ToolRequest | None:
        raw = step.get("request")
        if not isinstance(raw, dict) or not raw.get("tool"):
            return None
        try:
            return ToolRequest(
                tool=str(raw["tool"]),
                reason=str(raw.get("reason", "")),
                inputs=dict(raw.get("inputs") or {}),
            )
        except Exception:  # noqa: BLE001 - malformed request is not fatal
            return None

    def _cost_of(self, request: ToolRequest) -> int | None:
        try:
            return int(self.registry.get(request.tool).cost)
        except Exception:  # noqa: BLE001 - unknown tool is handled at execute time
            return None


# -- investigators ------------------------------------------------------


@dataclass(slots=True)
class LLMInvestigator:
    """Wraps a text-in/text-out client into an investigator."""

    client: Any  # needs .complete(system, prompt) -> str
    name: str = "investigator"
    system: str = (
        "You are part of an automated genomic discovery engine. You reason over "
        "evidence produced by deterministic tools; you never assert a fact the "
        "evidence does not support, and you never treat the absence of a database "
        "match as positive proof of novelty."
    )

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]:
        prompt = PROMPT.format(
            observation=render_observation(state),
            hypotheses=render_hypotheses(state),
            catalogue=catalogue,
            budget=state.spent,
        )
        raw = self.client.complete(self.system, prompt)
        return _parse_step(raw)


@dataclass(slots=True)
class ScriptedInvestigator:
    """Replays a fixed list of steps. For tests and for offline demonstration.

    It is not a model and does not pretend to be one: it exists so the loop's
    control flow can be exercised deterministically.
    """

    steps: Sequence[dict[str, Any]]
    name: str = "scripted"
    _index: int = 0

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]:
        if self._index >= len(self.steps):
            return {"stop": True, "stop_reason": "script exhausted"}
        step = self.steps[self._index]
        self._index += 1
        return dict(step)


def _parse_step(raw: str) -> dict[str, Any]:
    """Parse a model reply, degrading to a stop rather than inventing a step."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        text = text.removeprefix("json").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {"stop": True, "stop_reason": f"unparseable reply: {raw[:120]}"}
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {"stop": True, "stop_reason": f"unparseable reply: {raw[:120]}"}
    return payload if isinstance(payload, dict) else {"stop": True, "stop_reason": "not an object"}
