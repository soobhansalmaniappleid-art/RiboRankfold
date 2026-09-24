"""The staged funnel.

A stage takes candidates and either keeps, drops or escalates each one, always
writing the reason onto the candidate. Two properties matter:

* **Nothing disappears silently.** A dropped candidate is retained with the
  stage and reason that dropped it, so "why did we never look at X" is always
  answerable.
* **Expensive stages run last.** Stages declare a ``cost``; the pipeline refuses
  to run a costlier stage before a cheaper one, which is the structural way to
  keep a language model from being the first thing that touches a million loci.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from itertools import pairwise

from discovery.schema import Candidate, Decision


class Cost(IntEnum):
    """Relative expense of a stage. Ordering is enforced by the pipeline."""

    TRIVIAL = 0  # string statistics
    CHEAP = 1  # indexed lookups, k-mer scans
    MODERATE = 2  # alignment, HMM search, structure prediction
    EXPENSIVE = 3  # language-model reasoning, literature retrieval


@dataclass(slots=True)
class StageResult:
    decision: Decision
    reason: str


# A rule inspects one candidate and says what should happen to it.
Rule = Callable[[Candidate], StageResult]


@dataclass(slots=True)
class Stage:
    name: str
    cost: Cost
    rule: Rule
    description: str = ""

    def apply(self, candidate: Candidate) -> Candidate:
        result = self.rule(candidate)
        candidate.record(self.name, result.decision, result.reason)
        return candidate


@dataclass(slots=True)
class StageStats:
    stage: str
    cost: int
    seen: int
    kept: int
    dropped: int
    escalated: int


@dataclass(slots=True)
class Pipeline:
    """An ordered funnel of stages, cheapest first."""

    stages: list[Stage] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate(self.stages)

    @staticmethod
    def _validate(stages: Sequence[Stage]) -> None:
        names = [stage.name for stage in stages]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"duplicate stage names: {sorted(duplicates)}")
        for earlier, later in pairwise(stages):
            if later.cost < earlier.cost:
                raise ValueError(
                    f"stage {later.name!r} (cost {later.cost.name}) cannot run after "
                    f"{earlier.name!r} (cost {earlier.cost.name}); order stages "
                    "cheapest-first so expensive analysis only sees survivors"
                )

    def add(self, stage: Stage) -> Pipeline:
        self._validate([*self.stages, stage])
        self.stages.append(stage)
        return self

    def run(self, candidates: Iterable[Candidate]) -> PipelineRun:
        alive = list(candidates)
        everything = list(alive)
        stats: list[StageStats] = []

        for stage in self.stages:
            seen = len(alive)
            survivors: list[Candidate] = []
            dropped = escalated = 0
            for candidate in alive:
                stage.apply(candidate)
                if candidate.alive:
                    survivors.append(candidate)
                    if candidate.history[-1].decision == "escalate":
                        escalated += 1
                else:
                    dropped += 1
            stats.append(
                StageStats(
                    stage=stage.name,
                    cost=int(stage.cost),
                    seen=seen,
                    kept=len(survivors),
                    dropped=dropped,
                    escalated=escalated,
                )
            )
            alive = survivors

        return PipelineRun(survivors=alive, all_candidates=everything, stats=stats)


@dataclass(slots=True)
class PipelineRun:
    survivors: list[Candidate]
    all_candidates: list[Candidate]
    stats: list[StageStats]

    def funnel(self) -> str:
        """Render the narrowing as a plain-text funnel.

        This is the diagram that should appear in any write-up: a claim about a
        discovery is only interpretable next to the size of the space it was
        drawn from.
        """
        if not self.stats:
            return f"{len(self.all_candidates)} candidates (no stages run)"
        width = max(len(stat.stage) for stat in self.stats)
        lines = [f"{'input':>{width}} : {self.stats[0].seen}"]
        for stat in self.stats:
            lines.append(f"{'':>{width}}   |")
            lines.append(f"{stat.stage:>{width}} : {stat.kept}  (-{stat.dropped})")
        return "\n".join(lines)

    def rejected(self) -> list[Candidate]:
        return [candidate for candidate in self.all_candidates if not candidate.alive]


# -- common rules -------------------------------------------------------


def threshold_rule(
    feature: str, minimum: float | None = None, maximum: float | None = None
) -> Rule:
    """Keep candidates whose feature sits inside a range.

    A missing feature is a *drop with a stated reason*, never a silent pass:
    a stage that cannot evaluate a candidate has not cleared it.
    """

    def rule(candidate: Candidate) -> StageResult:
        if feature not in candidate.features:
            return StageResult("drop", f"{feature} not computed")
        value = candidate.features[feature]
        if value != value:  # NaN
            return StageResult("drop", f"{feature} is NaN")
        if minimum is not None and value < minimum:
            return StageResult("drop", f"{feature}={value:.4g} < {minimum:.4g}")
        if maximum is not None and value > maximum:
            return StageResult("drop", f"{feature}={value:.4g} > {maximum:.4g}")
        return StageResult("keep", f"{feature}={value:.4g} within range")

    return rule


def escalation_rule(score: str, minimum: float) -> Rule:
    """Escalate high-scoring candidates, keep the rest for later review."""

    def rule(candidate: Candidate) -> StageResult:
        value = candidate.scores.get(score)
        if value is None:
            return StageResult("drop", f"{score} not scored")
        if value >= minimum:
            return StageResult("escalate", f"{score}={value:.4g} >= {minimum:.4g}")
        return StageResult("keep", f"{score}={value:.4g} below escalation threshold")

    return rule
