"""Persistent candidate state.

The engine's promise is that if it ever says "this is novel", you can open one
file and read exactly what data, what computation, which agent and which
decision produced that claim. That promise is only kept if the state is
append-only: an investigation that overwrites what it previously believed
cannot be audited afterwards.

So `CandidateState` has one mutation primitive, `record`, and everything else
is a thin wrapper over it. Features and hypotheses can be updated, but the
update is itself an event, and the prior value stays in the log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

STATE_VERSION = 1

EventKind = Literal[
    "created",
    "feature",
    "tool_request",
    "tool_result",
    "hypothesis",
    "verdict",
    "decision",
    "note",
]

Status = Literal["open", "investigating", "eliminated", "reported"]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class Event:
    """One thing that happened, in order."""

    seq: int
    kind: EventKind
    actor: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "actor": self.actor,
            "summary": self.summary,
            "payload": self.payload,
            "at": self.at,
        }


@dataclass(slots=True)
class Hypothesis:
    """A proposed explanation, and what would settle it.

    ``discriminating_evidence`` is required. A hypothesis nobody can imagine
    testing is not a scientific claim, and the engine should not carry it
    forward as if it were.
    """

    statement: str
    proposed_by: str
    discriminating_evidence: str
    confidence: float = 0.5
    status: Literal["open", "supported", "refuted"] = "open"

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("a hypothesis needs a statement")
        if not self.discriminating_evidence.strip():
            raise ValueError(
                f"hypothesis {self.statement!r} has no discriminating evidence; "
                "say what observation would tell it apart from the alternatives"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "proposed_by": self.proposed_by,
            "discriminating_evidence": self.discriminating_evidence,
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass(slots=True)
class CandidateState:
    """Everything known about one candidate, and how it came to be known."""

    candidate_id: str
    sequence: str = ""
    contig_id: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    status: Status = "open"
    spent: int = 0

    def __post_init__(self) -> None:
        if not self.events:
            self.record("created", "engine", f"candidate {self.candidate_id} created")

    # -- the one mutation primitive -------------------------------------
    def record(
        self, kind: EventKind, actor: str, summary: str, **payload: Any
    ) -> Event:
        event = Event(
            seq=len(self.events), kind=kind, actor=actor, summary=summary, payload=payload
        )
        self.events.append(event)
        return event

    # -- wrappers -------------------------------------------------------
    def set_features(self, values: dict[str, Any], actor: str) -> None:
        """Update features, recording what changed and what it was before."""
        changed = {
            key: {"from": self.features.get(key), "to": value}
            for key, value in values.items()
            if self.features.get(key) != value
        }
        self.features.update(values)
        if changed:
            self.record(
                "feature", actor, f"{len(changed)} feature(s) updated", changes=changed
            )

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        self.hypotheses.append(hypothesis)
        self.record(
            "hypothesis",
            hypothesis.proposed_by,
            hypothesis.statement,
            **hypothesis.to_dict(),
        )
        return hypothesis

    def resolve_hypothesis(
        self, index: int, status: Literal["supported", "refuted"], actor: str, why: str
    ) -> None:
        hypothesis = self.hypotheses[index]
        hypothesis.status = status
        self.record(
            "decision", actor, f"hypothesis {status}: {hypothesis.statement}", why=why
        )

    def note_request(self, request: Any, actor: str) -> None:
        self.record(
            "tool_request",
            actor,
            f"requested {request.tool}",
            tool=request.tool,
            reason=request.reason,
            inputs={k: repr(v)[:200] for k, v in request.inputs.items()},
        )

    def note_result(self, result: Any, actor: str = "orchestrator") -> None:
        self.spent += int(result.cost)
        self.record(
            "tool_result",
            actor,
            f"{result.tool}: {'ok' if result.ok else 'failed'}",
            **result.to_dict(),
        )

    def decide(self, status: Status, actor: str, why: str) -> None:
        self.status = status
        self.record("decision", actor, f"status -> {status}", why=why)

    # -- queries --------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.status not in ("eliminated",)

    def tools_run(self) -> list[str]:
        return [
            event.payload["tool"]
            for event in self.events
            if event.kind == "tool_result" and event.payload.get("ok")
        ]

    def has_run(self, tool: str, inputs: dict[str, Any] | None = None) -> bool:
        """Whether this exact tool call already happened.

        The loop uses this to refuse repeats. An agent that asks for the same
        computation twice is looping, not investigating.
        """
        wanted = {k: repr(v)[:200] for k, v in (inputs or {}).items()}
        for event in self.events:
            if event.kind != "tool_request" or event.payload.get("tool") != tool:
                continue
            if inputs is None or event.payload.get("inputs") == wanted:
                return True
        return False

    def open_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.status == "open"]

    # -- persistence ----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "state_version": STATE_VERSION,
            "candidate_id": self.candidate_id,
            "contig_id": self.contig_id,
            "sequence_length": len(self.sequence),
            "status": self.status,
            "spent": self.spent,
            "features": self.features,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "events": [e.to_dict() for e in self.events],
        }

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        payload["sequence"] = self.sequence
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> CandidateState:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        version = payload.get("state_version")
        if version != STATE_VERSION:
            raise ValueError(
                f"unsupported state version {version!r}, expected {STATE_VERSION}"
            )
        state = cls.__new__(cls)  # bypass __post_init__, which would add an event
        state.candidate_id = payload["candidate_id"]
        state.sequence = payload.get("sequence", "")
        state.contig_id = payload.get("contig_id", "")
        state.features = payload.get("features", {})
        state.status = payload.get("status", "open")
        state.spent = payload.get("spent", 0)
        state.hypotheses = [Hypothesis(**h) for h in payload.get("hypotheses", [])]
        state.events = [Event(**e) for e in payload.get("events", [])]
        return state
