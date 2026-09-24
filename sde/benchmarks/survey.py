"""Running the blind survey, and scoring it honestly.

Two arms, because they answer different questions:

**Arm A — deterministic sweep.** Run every cheap tool on every locus, then rank
by how far each locus sits from the cohort. This tests the *machinery*: does
generic anomaly scoring surface the planted locus without being told what to
look for?

**Arm B — selective agent.** The agent gets a budget that cannot cover every
tool, so it has to choose which analysis to request. This tests *judgement*.

Arm B is the interesting one and is the one this repository cannot currently
answer, because no model is connected. It is built so that it can be, and it
runs with a stated baseline policy in the meantime — which is reported as a
baseline, not as insight.

## The rule that keeps this a test

`cohort_anomaly` ranks on **z-scores of whatever numeric features exist**,
computed against the cohort. It contains no reference to repeats, periodicity,
copy counts or any other property of the planted signal. If it were allowed to
weight `repeat_copy_count` specially, the benchmark would be measuring nothing.
A test asserts this: the ranking code must not mention the planted feature
names.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from sde.benchmarks.blind_rt import KNOWN_ARCHITECTURES, KNOWN_FAMILIES, Corpus
from sde.loop import InvestigationLoop
from sde.registry import ToolCost, ToolRegistry, ToolRequest
from sde.state import CandidateState
from sde.tools import registry as default_registry

#: Features that describe the cohort rather than the locus, so they carry no
#: anomaly signal and would only add noise.
IGNORED_FEATURES = frozenset({"length", "neighbour_count", "partner_family_count"})


@dataclass(slots=True)
class SurveyResult:
    states: dict[str, CandidateState]
    ranking: list[tuple[str, float]]
    tools_per_locus: dict[str, list[str]]
    arm: str

    def rank_of(self, locus_id: str) -> int | None:
        for position, (candidate, _) in enumerate(self.ranking, start=1):
            if candidate == locus_id:
                return position
        return None

    def top(self, n: int) -> list[str]:
        return [candidate for candidate, _ in self.ranking[:n]]


def _tool_inputs(entry: dict[str, Any], tool: str) -> dict[str, Any]:
    if tool in ("sequence_stats", "repeat_scan", "repeat_detail"):
        return {"sequence": entry["sequence"]}
    if tool == "neighbourhood_novelty":
        return {
            "genes": entry["genes"],
            "anchor_family": entry["anchor_family"],
            "known_architectures": [list(a) for a in KNOWN_ARCHITECTURES],
            "known_families": sorted(KNOWN_FAMILIES),
            "taxon": entry["taxon"],
        }
    return {}


def deterministic_sweep(
    corpus: Corpus, registry: ToolRegistry | None = None, max_cost: ToolCost = ToolCost.CHEAP
) -> SurveyResult:
    """Arm A: run every affordable tool on every locus."""
    registry = registry or default_registry
    tools = [
        spec.name
        for spec in registry.catalogue(max_cost)
        if not spec.summary.startswith("[NOT INSTALLED]")
    ]
    states: dict[str, CandidateState] = {}
    ran: dict[str, list[str]] = {}

    for entry in corpus.engine_inputs():
        state = CandidateState(
            candidate_id=entry["locus_id"],
            sequence=entry["sequence"],
            contig_id=entry["locus_id"],
        )
        for tool in tools:
            inputs = _tool_inputs(entry, tool)
            if not inputs:
                continue
            result = registry.execute(
                ToolRequest(tool=tool, reason="deterministic sweep of all cheap tools",
                            inputs=inputs)
            )
            state.note_result(result)
            if result.ok:
                state.set_features(
                    {k: v for k, v in result.outputs.items() if isinstance(v, (int, float))},
                    actor=f"tool:{tool}",
                )
        states[state.candidate_id] = state
        ran[state.candidate_id] = state.tools_run()

    return SurveyResult(
        states=states, ranking=cohort_anomaly(states), tools_per_locus=ran, arm="deterministic"
    )


def cohort_anomaly(states: dict[str, CandidateState]) -> list[tuple[str, float]]:
    """Rank loci by distance from the cohort, over whatever features exist.

    Deliberately feature-agnostic. It has no idea what the planted signal is,
    and must not: the moment this function knows, the benchmark stops being a
    test of anything.

    A feature that is missing for a locus contributes nothing rather than zero,
    since "not measured" is not "typical".
    """
    columns: dict[str, list[float]] = {}
    for state in states.values():
        for key, value in state.features.items():
            if key in IGNORED_FEATURES or not isinstance(value, (int, float)):
                continue
            if isinstance(value, float) and math.isnan(value):
                continue
            columns.setdefault(key, []).append(float(value))

    stats: dict[str, tuple[float, float]] = {}
    for key, values in columns.items():
        if len(values) < 3:
            continue
        spread = statistics.pstdev(values)
        if spread > 0:
            stats[key] = (statistics.fmean(values), spread)

    scored: list[tuple[str, float]] = []
    for candidate_id, state in states.items():
        deviations = []
        for key, (mean, spread) in stats.items():
            value = state.features.get(key)
            if not isinstance(value, (int, float)):
                continue
            if isinstance(value, float) and math.isnan(value):
                continue
            deviations.append(abs((float(value) - mean) / spread))
        # Max deviation, not mean: one strongly unusual property is what makes a
        # locus worth a look, and averaging buries it under ordinary features.
        scored.append((candidate_id, max(deviations) if deviations else 0.0))
    return sorted(scored, key=lambda item: (-item[1], item[0]))


@dataclass(slots=True)
class BudgetedSweep:
    """Arm B: the agent may only afford a subset of the tools."""

    registry: ToolRegistry
    investigator_factory: Any
    budget: int = 4

    def run(self, corpus: Corpus) -> SurveyResult:
        states: dict[str, CandidateState] = {}
        ran: dict[str, list[str]] = {}
        for entry in corpus.engine_inputs():
            state = CandidateState(
                candidate_id=entry["locus_id"],
                sequence=entry["sequence"],
                contig_id=entry["locus_id"],
            )
            loop = InvestigationLoop(
                registry=self.registry,
                investigator=self.investigator_factory(entry),
                budget=self.budget,
                max_cost=ToolCost.CHEAP,
            )
            loop.run(state)
            states[state.candidate_id] = state
            ran[state.candidate_id] = state.tools_run()
        return SurveyResult(
            states=states, ranking=cohort_anomaly(states), tools_per_locus=ran, arm="budgeted"
        )


# -- scoring ------------------------------------------------------------


@dataclass(slots=True)
class SurveyScore:
    arm: str
    n_loci: int
    planted_ranks: dict[str, int | None] = field(default_factory=dict)
    planted_in_top: dict[int, float] = field(default_factory=dict)
    confounders_above_best_planted: int = 0
    confounders_above_worst_planted: int = 0
    known_in_top10: int = 0
    random_top10_rate: float = 0.0
    analysed_the_planted_signal: dict[str, bool] = field(default_factory=dict)

    def render(self) -> str:
        lines = [
            f"arm: {self.arm}",
            f"loci: {self.n_loci}",
            "",
            "planted loci, rank in the survey (1 = most anomalous):",
        ]
        for locus_id, rank in sorted(self.planted_ranks.items()):
            lines.append(f"  {locus_id}: {rank if rank else 'not ranked'}")
        lines.append("")
        for n, rate in sorted(self.planted_in_top.items()):
            lines.append(
                f"  planted in top-{n}: {rate:.0%} "
                f"(random expectation {min(1.0, n / self.n_loci):.0%})"
            )
        lines += [
            "",
            f"  confounders above the BEST planted locus:  "
            f"{self.confounders_above_best_planted}",
            f"  confounders above the WORST planted locus: "
            f"{self.confounders_above_worst_planted}",
            f"  known systems in top 10: {self.known_in_top10} (should be low)",
        ]
        if self.analysed_the_planted_signal:
            chose = sum(self.analysed_the_planted_signal.values())
            total = len(self.analysed_the_planted_signal)
            lines.append(
                f"  planted loci where the agent requested the decisive analysis: "
                f"{chose}/{total}"
            )
        return "\n".join(lines)


def score_survey(
    corpus: Corpus, result: SurveyResult, decisive_tool: str = "repeat_scan"
) -> SurveyScore:
    """Score a survey against ground truth.

    ``decisive_tool`` is named only here, in the scorer, which runs after the
    engine has finished and never influences it.
    """
    kinds = corpus.kinds()
    planted = corpus.planted_ids
    ranks = {locus_id: result.rank_of(locus_id) for locus_id in planted}
    n = len(result.ranking)

    in_top = {}
    for cut in (1, 3, 5, 10, 20):
        hits = sum(1 for rank in ranks.values() if rank is not None and rank <= cut)
        in_top[cut] = hits / len(planted) if planted else 0.0

    found = [r for r in ranks.values() if r]
    best_planted = min(found, default=n)
    worst_planted = max(found, default=n)

    def confounders_above(cut: int) -> int:
        return sum(
            1
            for position, (locus_id, _) in enumerate(result.ranking, start=1)
            if position < cut and kinds.get(locus_id, "").startswith("confounder")
        )

    above_best = confounders_above(best_planted)
    above_worst = confounders_above(worst_planted)
    known_top10 = sum(1 for locus_id in result.top(10) if kinds.get(locus_id) == "known_system")

    chose = {
        locus_id: decisive_tool in result.tools_per_locus.get(locus_id, [])
        for locus_id in sorted(planted)
    }

    return SurveyScore(
        arm=result.arm,
        n_loci=n,
        planted_ranks=ranks,
        planted_in_top=in_top,
        confounders_above_best_planted=above_best,
        confounders_above_worst_planted=above_worst,
        known_in_top10=known_top10,
        random_top10_rate=min(1.0, 10 / n) if n else 0.0,
        analysed_the_planted_signal=chose,
    )
