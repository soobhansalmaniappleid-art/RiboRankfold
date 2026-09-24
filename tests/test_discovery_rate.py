from __future__ import annotations

import random

import pytest

from sde.benchmarks.blind_rt import Corpus, build_corpus
from sde.benchmarks.rate import (
    PUBLISHED_REFERENCE,
    DiscoveryRate,
    RunOutcome,
    StochasticInvestigator,
    discovery_rate,
    wilson_interval,
)
from sde.benchmarks.survey import BudgetedSweep, deterministic_sweep
from sde.tools import registry


def hard_corpus(index: int) -> Corpus:
    return Corpus(loci=build_corpus(n_ordinary=60, n_planted=1, seed=3000 + index))


# -- Wilson interval ----------------------------------------------------


def test_wilson_never_collapses_to_a_point_at_zero_successes():
    """The normal approximation would imply certainty here; it must not."""
    low, high = wilson_interval(0, 11)
    assert low == pytest.approx(0.0, abs=1e-12)
    assert high > 0.2


def test_wilson_never_reaches_certainty_at_full_successes():
    low, high = wilson_interval(11, 11)
    assert high == 1.0
    assert low < 0.8


def test_wilson_narrows_as_trials_grow():
    narrow = wilson_interval(50, 100)
    wide = wilson_interval(5, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_wilson_on_no_trials_is_nan():
    low, high = wilson_interval(0, 0)
    assert low != low and high != high  # NaN


def test_the_published_reference_is_one_in_eleven():
    hits, runs, _ = PUBLISHED_REFERENCE
    assert (hits, runs) == (1, 11)


# -- rate mechanics -----------------------------------------------------


def make_rate(found: list[bool]) -> DiscoveryRate:
    return DiscoveryRate(
        arm="t",
        top_n=10,
        runs=[
            RunOutcome(i + 1, i, f, 1 if f else 99, 1 if f else 0, 1)
            for i, f in enumerate(found)
        ],
    )


def test_rate_counts_successes():
    assert make_rate([True, False, True, False]).rate == pytest.approx(0.5)


def test_a_single_run_is_flagged_as_not_a_measurement():
    assert "smoke test" in make_rate([True]).render()


def test_ten_or_more_runs_are_not_flagged():
    assert "smoke test" not in make_rate([True] * 10).render()


def test_a_rate_matching_the_reference_overlaps_it():
    assert make_rate([True] + [False] * 10).overlaps_published()


def test_a_perfect_rate_does_not_overlap_the_reference():
    assert not make_rate([True] * 11).overlaps_published()


def test_beating_the_reference_is_reported_as_an_easier_benchmark():
    """A high rate must not read as a better engine."""
    text = make_rate([True] * 11).render()
    assert "EASIER" in text
    assert "not that the engine is better" in text


def test_matching_the_reference_does_not_trigger_the_easier_note():
    assert "EASIER" not in make_rate([True] + [False] * 10).render()


def test_the_reference_is_always_rendered():
    assert "Anthropic ART campaign" in make_rate([False] * 11).render()


def test_zero_runs_is_rejected():
    with pytest.raises(ValueError, match="n_runs"):
        discovery_rate(lambda c, i: deterministic_sweep(c), n_runs=0)


# -- stochastic investigator -------------------------------------------


def test_the_stochastic_investigator_varies_between_seeds():
    """Without variance, a 'rate' over repeated runs would be meaningless."""
    corpus = hard_corpus(0)

    def choices(seed: int) -> list[list[str]]:
        rng = random.Random(seed)
        sweep = BudgetedSweep(
            registry=registry,
            investigator_factory=lambda e: StochasticInvestigator(e, registry, rng),
            budget=4,
        )
        return sorted(sorted(v) for v in sweep.run(corpus).tools_per_locus.values())

    assert choices(1) != choices(2)


def test_zero_exploration_collapses_to_the_deterministic_baseline():
    corpus = hard_corpus(0)
    rng = random.Random(0)
    sweep = BudgetedSweep(
        registry=registry,
        investigator_factory=lambda e: StochasticInvestigator(
            e, registry, rng, exploration=0.0
        ),
        budget=4,
    )
    runs = list(sweep.run(corpus).tools_per_locus.values())
    assert all(sorted(tools) == sorted(runs[0]) for tools in runs)


# -- end to end ---------------------------------------------------------


def test_the_full_sweep_beats_the_budgeted_agent():
    full = discovery_rate(
        lambda c, i: deterministic_sweep(c), corpus_factory=hard_corpus, n_runs=6, arm="A"
    )

    def budgeted(corpus, index):
        rng = random.Random(9000 + index)
        return BudgetedSweep(
            registry=registry,
            investigator_factory=lambda e: StochasticInvestigator(e, registry, rng),
            budget=4,
        ).run(corpus)

    partial = discovery_rate(budgeted, corpus_factory=hard_corpus, n_runs=6, arm="B")
    assert full.rate >= partial.rate


def test_the_budgeted_agent_does_not_always_request_the_decisive_tool():
    def budgeted(corpus, index):
        rng = random.Random(500 + index)
        return BudgetedSweep(
            registry=registry,
            investigator_factory=lambda e: StochasticInvestigator(e, registry, rng),
            budget=4,
        ).run(corpus)

    rate = discovery_rate(budgeted, corpus_factory=hard_corpus, n_runs=8, arm="B")
    assert rate.decisive_rate < 1.0


def test_a_fixed_corpus_isolates_engine_variance():
    fixed = Corpus.build(seed=2026)
    rate = discovery_rate(
        lambda c, i: deterministic_sweep(c),
        corpus_factory=lambda i: fixed,
        n_runs=3,
        arm="fixed",
    )
    assert len({run.best_rank for run in rate.runs}) == 1
