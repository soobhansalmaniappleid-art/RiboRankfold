"""Discovery rate across repeated runs.

The single most useful number Anthropic published about their ART result is not
949 agents or 210 million tokens. It is this: they re-ran the same campaign ten
more times, and **no rerun read the DNA upstream of the enzyme. All ten missed
the array.**

That makes the discovery roughly 1 in 11, and it reframes everything. A
discovery engine is not a function that returns a finding; it is a process with
a *rate*, and a single successful run tells you almost nothing about that rate.

So this module measures the rate, with an interval, and refuses to report a
single run as a result. It exists so that any claim made here is comparable
with the only honest number anyone else has published.

## Why the investigator must be stochastic

Measuring a rate requires runs that can differ. The baseline policies in
`sde.investigators` are deterministic — eleven runs give one answer eleven
times, and the "rate" would be 0.0 or 1.0 with a meaningless interval.

A language-model agent is stochastic: that is exactly why Anthropic's reruns
diverged. `StochasticInvestigator` models that variance explicitly rather than
pretending it away, so the harness reports a rate that means something even
before a model is connected.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sde.benchmarks.blind_rt import Corpus
from sde.benchmarks.survey import SurveyResult, score_survey
from sde.registry import ToolCost, ToolRegistry
from sde.state import CandidateState

#: Anthropic re-ran the ART campaign ten more times; all ten missed the array.
#: Reported alongside our own rate so the comparison is never lost.
PUBLISHED_REFERENCE = (1, 11, "Anthropic ART campaign: 1 of 11 runs found the array")


@dataclass(slots=True)
class StochasticInvestigator:
    """Picks among affordable unused tools at random.

    Not a model, and not a claim about how a model behaves. It is a variance
    model: it has the property that matters for measuring a rate, which is that
    two runs can make different choices with the same evidence.

    ``exploration`` is the probability of choosing at random rather than taking
    the cheapest option. At 0.0 it collapses to the deterministic baseline.
    """

    entry: dict[str, Any]
    registry: ToolRegistry
    rng: random.Random
    exploration: float = 1.0
    max_cost: ToolCost = ToolCost.CHEAP
    name: str = "stochastic"
    _requested: set[str] = field(default_factory=set)

    def next_step(self, state: CandidateState, catalogue: str) -> dict[str, Any]:
        from sde.investigators import _inputs_for

        affordable = [
            spec
            for spec in self.registry.catalogue(self.max_cost)
            if spec.name not in self._requested
            and not spec.summary.startswith("[NOT INSTALLED]")
            and _inputs_for(self.entry, spec.requires) is not None
        ]
        if not affordable:
            return {"stop": True, "stop_reason": "no affordable unused tools remain"}

        if self.rng.random() < self.exploration:
            spec = self.rng.choice(affordable)
        else:
            spec = affordable[0]
        self._requested.add(spec.name)
        return {
            "request": {
                "tool": spec.name,
                "reason": "stochastic baseline policy",
                "inputs": _inputs_for(self.entry, spec.requires),
            }
        }


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Used rather than the normal approximation because the counts here are tiny
    and often include 0 successes, where the normal interval collapses to a
    point and would imply certainty this data cannot support.
    """
    if trials <= 0:
        return (float("nan"), float("nan"))
    p = successes / trials
    denominator = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denominator
    spread = (
        z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denominator
    )
    return (max(0.0, centre - spread), min(1.0, centre + spread))


@dataclass(slots=True)
class RunOutcome:
    run: int
    seed: int
    found: bool
    best_rank: int | None
    requested_decisive: int
    planted_total: int


@dataclass(slots=True)
class DiscoveryRate:
    """How often the engine finds the planted signal, over repeated runs."""

    arm: str
    top_n: int
    runs: list[RunOutcome] = field(default_factory=list)

    @property
    def successes(self) -> int:
        return sum(1 for run in self.runs if run.found)

    @property
    def trials(self) -> int:
        return len(self.runs)

    @property
    def rate(self) -> float:
        return self.successes / self.trials if self.trials else float("nan")

    @property
    def interval(self) -> tuple[float, float]:
        return wilson_interval(self.successes, self.trials)

    @property
    def decisive_rate(self) -> float:
        """Share of planted loci where the decisive analysis was requested."""
        asked = sum(run.requested_decisive for run in self.runs)
        total = sum(run.planted_total for run in self.runs)
        return asked / total if total else float("nan")

    def render(self) -> str:
        low, high = self.interval
        published_hits, published_runs, published_note = PUBLISHED_REFERENCE
        p_low, p_high = wilson_interval(published_hits, published_runs)
        lines = [
            f"arm: {self.arm}   top-{self.top_n} criterion",
            "",
            f"  discovery rate: {self.successes}/{self.trials} = {self.rate:.2f}",
            f"  95% interval  : [{low:.2f}, {high:.2f}]",
            f"  decisive analysis requested: {self.decisive_rate:.2f} of planted loci",
            "",
            f"  reference: {published_note}",
            f"            = {published_hits / published_runs:.2f} "
            f"[{p_low:.2f}, {p_high:.2f}]",
            "",
        ]
        if self.trials < 10:
            lines.append(
                f"  WARNING: {self.trials} runs cannot distinguish a rate of 0.1 "
                "from one of 0.5. Treat this as a smoke test, not a measurement."
            )
        if self.rate > published_hits / published_runs and not self.overlaps_published():
            lines.append(
                "  NOTE: this rate is well above the published reference. That is "
                "evidence the benchmark is EASIER, not that the engine is better: "
                "the corpus is synthetic, the signal is cleaner than reality, and "
                "the loci are pre-filtered to be RT-associated. A rate above the "
                "reference should prompt a harder benchmark, not a claim."
            )
        lines.append("  per run:")
        for run in self.runs:
            rank = run.best_rank if run.best_rank else "-"
            lines.append(
                f"    run {run.run:>2} (seed {run.seed}): "
                f"{'FOUND' if run.found else 'missed':<6} "
                f"best rank {rank:>4}, decisive {run.requested_decisive}/{run.planted_total}"
            )
        return "\n".join(lines)

    def overlaps_published(self) -> bool:
        """Whether our interval overlaps the published 1-in-11 interval."""
        low, high = self.interval
        p_low, p_high = wilson_interval(*PUBLISHED_REFERENCE[:2])
        return not (high < p_low or low > p_high)


def discovery_rate(
    run_survey: Callable[[Corpus, int], SurveyResult],
    corpus_factory: Callable[[int], Corpus] | None = None,
    n_runs: int = 11,
    top_n: int = 10,
    arm: str = "unnamed",
    decisive_tool: str = "repeat_scan",
) -> DiscoveryRate:
    """Repeat a survey and report how often it finds the planted signal.

    ``corpus_factory`` receives the run index and returns the corpus for it.
    Holding the corpus fixed measures the *engine's* variance; varying it
    measures whether the engine works across datasets. They are different
    questions and the caller has to choose, so there is no default that quietly
    picks one.
    """
    if n_runs < 1:
        raise ValueError(f"n_runs must be >= 1, got {n_runs}")
    factory = corpus_factory or (lambda index: Corpus.build(seed=2026))

    outcomes: list[RunOutcome] = []
    for index in range(n_runs):
        corpus = factory(index)
        result = run_survey(corpus, index)
        score = score_survey(corpus, result, decisive_tool=decisive_tool)
        ranks = [rank for rank in score.planted_ranks.values() if rank]
        outcomes.append(
            RunOutcome(
                run=index + 1,
                seed=index,
                found=bool(ranks) and min(ranks) <= top_n,
                best_rank=min(ranks) if ranks else None,
                requested_decisive=sum(score.analysed_the_planted_signal.values()),
                planted_total=len(score.analysed_the_planted_signal),
            )
        )
    return DiscoveryRate(arm=arm, top_n=top_n, runs=outcomes)
