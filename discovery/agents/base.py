"""The model boundary.

Everything above this module is deterministic and reproducible. Everything below
is a model's opinion, and is recorded as such -- ``Evidence.kind == "model"``,
never mixed into the computed feature block.

The engine depends on the ``LLMClient`` protocol, not on any vendor SDK, so the
pipeline runs end to end offline with ``RuleBasedClient`` and the tests do not
need a network.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from discovery.schema import AgentVerdict, Candidate, Stance

VALID_STANCES: tuple[Stance, ...] = ("supports", "refutes", "inconclusive")


class LLMClient(Protocol):
    """Minimal text-in, text-out interface."""

    def complete(self, system: str, prompt: str) -> str: ...


@dataclass(slots=True)
class Agent:
    """A named role with a system prompt and a parsed, structured output.

    ``name`` and ``system`` are class attributes so subclasses can fix them
    while ``client`` stays the single constructor argument.
    """

    client: LLMClient

    name: ClassVar[str] = "agent"
    system: ClassVar[str] = ""

    def build_prompt(self, candidate: Candidate) -> str:
        raise NotImplementedError

    def review(self, candidate: Candidate) -> AgentVerdict:
        raw = self.client.complete(self.system, self.build_prompt(candidate))
        verdict = parse_verdict(raw, agent=self.name)
        candidate.add_verdict(verdict)
        candidate.add_evidence(
            f"{self.name}_stance",
            verdict.stance,
            source=f"agent:{self.name}",
            kind="model",
            note=verdict.rationale[:200],
        )
        return verdict


def describe_candidate(candidate: Candidate) -> str:
    """Render the computed evidence a model is allowed to reason over.

    The raw sequence is deliberately summarised rather than pasted in full: a
    model asked to eyeball a megabase will confabulate, and every number here
    was produced by a tool that can be re-run.
    """
    lines = [
        f"candidate_id: {candidate.candidate_id}",
        f"locus: {candidate.contig_id}:{candidate.start}-{candidate.end}",
        f"sequence_length: {len(candidate.sequence)}",
        "",
        "computed features:",
    ]
    for key in sorted(candidate.features):
        lines.append(f"  {key} = {candidate.features[key]:.6g}")
    if candidate.scores:
        lines.append("")
        lines.append("scores:")
        for key in sorted(candidate.scores):
            lines.append(f"  {key} = {candidate.scores[key]:.6g}")
    if candidate.verdicts:
        lines.append("")
        lines.append("prior agent verdicts:")
        for verdict in candidate.verdicts:
            lines.append(
                f"  [{verdict.agent}] {verdict.stance} "
                f"(confidence {verdict.confidence:.2f}): {verdict.rationale}"
            )
    return "\n".join(lines)


RESPONSE_CONTRACT = """
Respond with a single JSON object and nothing else:

{
  "stance": "supports" | "refutes" | "inconclusive",
  "confidence": <number between 0 and 1>,
  "rationale": "<two or three sentences>",
  "cites": ["<identifier or reference>", ...]
}

Use "inconclusive" when the evidence does not settle the question. Do not
assert anything the computed features above do not support.
""".strip()


def parse_verdict(raw: str, agent: str) -> AgentVerdict:
    """Parse a model response, degrading to 'inconclusive' rather than guessing.

    A malformed response is an absence of evidence. Coercing it into a stance
    would put a fabricated opinion into the audit trail, which is worse than
    recording that the agent failed to answer.
    """
    payload = _extract_json(raw)
    if payload is None:
        return AgentVerdict(
            agent=agent,
            stance="inconclusive",
            confidence=0.0,
            rationale=f"unparseable response: {raw.strip()[:200]}",
        )

    stance = str(payload.get("stance", "")).strip().lower()
    if stance not in VALID_STANCES:
        return AgentVerdict(
            agent=agent,
            stance="inconclusive",
            confidence=0.0,
            rationale=f"invalid stance {stance!r}",
        )

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    cites = payload.get("cites", [])
    if not isinstance(cites, list):
        cites = []

    return AgentVerdict(
        agent=agent,
        stance=stance,  # type: ignore[arg-type]
        confidence=confidence,
        rationale=str(payload.get("rationale", "")).strip(),
        cites=[str(item) for item in cites],
    )


def _extract_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


@dataclass(slots=True)
class RuleBasedClient:
    """Offline stand-in for a model, driven by the computed features.

    It exists so the pipeline is runnable and testable without a network. It is
    not a model and makes no attempt to imitate one -- it mechanically converts
    the priority score into a stance, which is exactly the shallow behaviour the
    agent layer is supposed to improve on.
    """

    threshold: float = 0.5
    invert: bool = False

    def complete(self, system: str, prompt: str) -> str:
        priority = _read_number(prompt, "priority")
        if priority is None:
            return json.dumps(
                {
                    "stance": "inconclusive",
                    "confidence": 0.0,
                    "rationale": "no priority score present",
                    "cites": [],
                }
            )
        interesting = priority >= self.threshold
        if self.invert:
            stance = "refutes" if interesting else "supports"
        else:
            stance = "supports" if interesting else "refutes"
        return json.dumps(
            {
                "stance": stance,
                "confidence": round(min(1.0, abs(priority - self.threshold) * 2), 3),
                "rationale": f"rule-based stand-in: priority={priority:.3g}",
                "cites": [],
            }
        )


def _read_number(prompt: str, key: str) -> float | None:
    match = re.search(rf"^\s*{re.escape(key)} = (\S+)", prompt, re.MULTILINE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
