"""Baseline investigators.

None of these is a model, and none is presented as one. They exist so the
budgeted arm of a survey can run at all, and so a real model has something to
be compared against. Their whole value is as a floor: a model that cannot beat
"run the cheapest tool you have not run yet" has not demonstrated judgement.

Every policy here is written without any knowledge of what a given benchmark
plants. A policy that knew would turn the benchmark into a demonstration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sde.registry import ToolCost, ToolRegistry
from sde.state import CandidateState


def _inputs_for(entry: dict[str, Any], spec_requires: tuple[str, ...]) -> dict[str, Any] | None:
    """Assemble a tool's inputs from a locus record, or None if impossible."""
    available: dict[str, Any] = {
        "sequence": entry.get("sequence"),
        "genes": entry.get("genes"),
        "anchor_family": entry.get("anchor_family"),
        "taxon": entry.get("taxon"),
        "known_architectures": entry.get("known_architectures"),
        "known_families": entry.get("known_families"),
    }
    inputs = {}
    for field_name in spec_requires:
        value = available.get(field_name)
        if value is None:
            return None
        inputs[field_name] = value
    return inputs


@dataclass(slots=True)
class CheapestFirstInvestigator:
    """Spend the budget on the cheapest analyses available, in cost order.

    The honest floor. It exercises no judgement at all: it never looks at what
    the previous tool returned. Any claim that an agent "investigated" something
    has to beat this.
    """

    entry: dict[str, Any]
    registry: ToolRegistry
    max_cost: ToolCost = ToolCost.CHEAP
    name: str = "cheapest_first"
    _requested: set[str] = field(default_factory=set)

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]:
        for spec in self.registry.catalogue(self.max_cost):
            if spec.name in self._requested or spec.summary.startswith("[NOT INSTALLED]"):
                continue
            inputs = _inputs_for(self.entry, spec.requires)
            if inputs is None:
                continue
            self._requested.add(spec.name)
            return {
                "observation": "no reasoning; running the cheapest unused analysis",
                "request": {
                    "tool": spec.name,
                    "reason": "baseline policy: cheapest unrun tool",
                    "inputs": inputs,
                },
            }
        return {"stop": True, "stop_reason": "no affordable unused tools remain"}


@dataclass(slots=True)
class DeviationDrivenInvestigator:
    """Escalate when a measured feature is far from what the cohort shows.

    Slightly more than a floor: it starts with the cheapest analysis, and only
    spends more when something it has already measured looks unusual against
    cohort statistics supplied from outside.

    It still chooses *which* further tool to run by cost alone. It has no way to
    know which analysis would explain a given deviation — that is exactly the
    judgement a language model would contribute, and its absence here is the
    point of the comparison.
    """

    entry: dict[str, Any]
    registry: ToolRegistry
    cohort: dict[str, tuple[float, float]] = field(default_factory=dict)
    threshold: float = 1.5
    max_cost: ToolCost = ToolCost.CHEAP
    name: str = "deviation_driven"
    _requested: set[str] = field(default_factory=set)

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]:
        anomalies = self._anomalies(state)
        if self._requested and not anomalies:
            return {
                "stop": True,
                "stop_reason": "nothing measured so far deviates from the cohort",
            }
        for spec in self.registry.catalogue(self.max_cost):
            if spec.name in self._requested or spec.summary.startswith("[NOT INSTALLED]"):
                continue
            inputs = _inputs_for(self.entry, spec.requires)
            if inputs is None:
                continue
            self._requested.add(spec.name)
            reason = (
                "baseline policy: first measurement"
                if not anomalies
                else f"baseline policy: escalating, {', '.join(sorted(anomalies))} deviates"
            )
            return {"request": {"tool": spec.name, "reason": reason, "inputs": inputs}}
        return {"stop": True, "stop_reason": "no affordable unused tools remain"}

    def _anomalies(self, state: CandidateState) -> set[str]:
        found = set()
        for key, (mean, spread) in self.cohort.items():
            value = state.features.get(key)
            if not isinstance(value, (int, float)) or spread <= 0:
                continue
            if abs((float(value) - mean) / spread) >= self.threshold:
                found.add(key)
        return found
