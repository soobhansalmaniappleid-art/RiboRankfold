"""Candidate records.

Every decision the engine makes is attached to the candidate that it was made
about. If the pipeline ever says "this looks novel", it must be possible to open
one JSON file and read the entire chain of reasoning that led there -- which
stage computed which number, which stage dropped which sibling, and what each
agent argued.

Nothing in this module talks to a model or to a database. It is the contract the
rest of the engine writes into.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1

Decision = Literal["keep", "drop", "escalate"]
Stance = Literal["supports", "refutes", "inconclusive"]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class Evidence:
    """One computed observation about a candidate.

    ``source`` names the tool or stage that produced it, so a reviewer can
    distinguish a deterministic measurement from a model's assertion.
    """

    key: str
    value: Any
    source: str
    kind: Literal["computed", "database", "literature", "model"] = "computed"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StageRecord:
    """What a pipeline stage did to a candidate, and why."""

    stage: str
    decision: Decision
    reason: str
    at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentVerdict:
    """A model's argument about a candidate.

    ``stance`` is deliberately three-valued: an agent that cannot tell must be
    able to say so rather than being forced into a yes/no that later reads as
    evidence.
    """

    agent: str
    stance: Stance
    confidence: float
    rationale: str
    cites: list[str] = field(default_factory=list)
    at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Candidate:
    """A locus under investigation, with its full provenance."""

    candidate_id: str
    sequence: str = ""
    contig_id: str = ""
    start: int = 0
    end: int = 0
    features: dict[str, float] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    history: list[StageRecord] = field(default_factory=list)
    verdicts: list[AgentVerdict] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    dropped_by: str | None = None

    # -- provenance -----------------------------------------------------
    def add_evidence(self, key: str, value: Any, source: str, **kwargs: Any) -> None:
        self.evidence.append(Evidence(key=key, value=value, source=source, **kwargs))

    def record(self, stage: str, decision: Decision, reason: str) -> None:
        self.history.append(StageRecord(stage=stage, decision=decision, reason=reason))
        if decision == "drop" and self.dropped_by is None:
            self.dropped_by = stage

    def add_verdict(self, verdict: AgentVerdict) -> None:
        self.verdicts.append(verdict)

    @property
    def alive(self) -> bool:
        return self.dropped_by is None

    # -- serialisation --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "contig_id": self.contig_id,
            "start": self.start,
            "end": self.end,
            "sequence_length": len(self.sequence),
            "features": self.features,
            "scores": self.scores,
            "evidence": [item.to_dict() for item in self.evidence],
            "history": [item.to_dict() for item in self.history],
            "verdicts": [item.to_dict() for item in self.verdicts],
            "dropped_by": self.dropped_by,
        }

    def write_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        payload["sequence"] = self.sequence
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
        return path

    @classmethod
    def from_json(cls, path: Path) -> Candidate:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported candidate schema version {version!r}, expected {SCHEMA_VERSION}"
            )
        candidate = cls(
            candidate_id=payload["candidate_id"],
            sequence=payload.get("sequence", ""),
            contig_id=payload.get("contig_id", ""),
            start=payload.get("start", 0),
            end=payload.get("end", 0),
            features=payload.get("features", {}),
            scores=payload.get("scores", {}),
            dropped_by=payload.get("dropped_by"),
        )
        candidate.evidence = [Evidence(**item) for item in payload.get("evidence", [])]
        candidate.history = [StageRecord(**item) for item in payload.get("history", [])]
        candidate.verdicts = [AgentVerdict(**item) for item in payload.get("verdicts", [])]
        return candidate
