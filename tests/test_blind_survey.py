from __future__ import annotations

import inspect

import pytest

from sde.benchmarks import blind_rt, survey
from sde.benchmarks.blind_rt import RESEARCH_QUESTION, Corpus
from sde.benchmarks.survey import BudgetedSweep, cohort_anomaly, deterministic_sweep, score_survey
from sde.investigators import CheapestFirstInvestigator
from sde.state import CandidateState
from sde.tools import registry

#: Words that describe the planted signal. None may appear in the ranking code
#: or in what the engine is told.
LEAKS = ("repeat", "array", "crispr", "period", "spacing", "tandem", "copy_count")


# -- the benchmark must not leak its answer -----------------------------


def test_the_research_question_names_nothing_about_the_signal():
    lowered = RESEARCH_QUESTION.lower()
    assert not any(word in lowered for word in LEAKS)


def test_the_ranking_function_has_no_knowledge_of_the_planted_signal():
    """If the ranker knew what to look for, the benchmark would test nothing."""
    source = inspect.getsource(cohort_anomaly).lower()
    assert not any(word in source for word in LEAKS)


def test_engine_input_carries_no_ground_truth():
    corpus = Corpus.build(n_ordinary=5, n_planted=1)
    for entry in corpus.engine_inputs():
        assert "kind" not in entry
        assert not any(word in repr(entry.keys()).lower() for word in LEAKS)


def test_planted_loci_are_not_identifiable_by_id_length_or_order():
    corpus = Corpus.build()
    ids = [locus.locus_id for locus in corpus.loci]
    planted_positions = [i for i, lid in enumerate(ids) if lid in corpus.planted_ids]
    # shuffled, so they are not all at the end
    assert max(planted_positions) - min(planted_positions) > 2


# -- the corpus must be hard --------------------------------------------


def test_the_corpus_contains_confounders_and_known_systems():
    corpus = Corpus.build()
    assert len(corpus.confounder_ids) >= 10
    assert len(corpus.known_ids) >= 4
    assert len(corpus.planted_ids) == 3


def test_confounders_are_genuinely_irregular():
    """A confounder that is not unusual would not confound anything."""
    from discovery.features.sequence import low_complexity_fraction

    corpus = Corpus.build()
    low_complexity = [
        low_complexity_fraction(locus.sequence)
        for locus in corpus.loci
        if locus.kind == "confounder_low_complexity"
    ]
    ordinary = [
        low_complexity_fraction(locus.sequence)
        for locus in corpus.loci
        if locus.kind == "ordinary"
    ]
    assert min(low_complexity) > max(ordinary)


def test_dispersed_motif_confounder_is_not_a_regular_array():
    """It must recur without a constant period, or it is a second planted locus."""
    from discovery.features.repeats import find_repeat_arrays

    corpus = Corpus.build()
    for locus in corpus.loci:
        if locus.kind == "confounder_dispersed_motif":
            arrays = find_repeat_arrays(locus.sequence, max_period_cv=0.10)
            assert not arrays


def test_planted_loci_do_contain_a_regular_array():
    from discovery.features.repeats import find_repeat_arrays

    corpus = Corpus.build()
    for locus in corpus.loci:
        if locus.kind == "planted":
            assert find_repeat_arrays(locus.sequence)


def test_the_corpus_is_reproducible():
    a = [locus.sequence for locus in Corpus.build(seed=7).loci]
    b = [locus.sequence for locus in Corpus.build(seed=7).loci]
    assert a == b


def test_a_different_seed_gives_a_different_corpus():
    a = [locus.sequence for locus in Corpus.build(seed=1).loci]
    b = [locus.sequence for locus in Corpus.build(seed=2).loci]
    assert a != b


# -- ranking ------------------------------------------------------------


def test_cohort_anomaly_ignores_features_that_are_missing():
    """Not measured is not typical."""
    a = CandidateState("a")
    a.set_features({"x": 1.0, "y": 5.0}, actor="t")
    b = CandidateState("b")
    b.set_features({"x": 1.0}, actor="t")  # y missing entirely
    c = CandidateState("c")
    c.set_features({"x": 1.0, "y": 5.0}, actor="t")
    ranking = dict(cohort_anomaly({"a": a, "b": b, "c": c}))
    assert ranking["b"] == pytest.approx(0.0)


def test_cohort_anomaly_ranks_an_outlier_first():
    states = {}
    for i in range(10):
        state = CandidateState(f"n{i}")
        state.set_features({"x": 1.0 + i * 0.01}, actor="t")
        states[f"n{i}"] = state
    outlier = CandidateState("outlier")
    outlier.set_features({"x": 99.0}, actor="t")
    states["outlier"] = outlier
    assert cohort_anomaly(states)[0][0] == "outlier"


def test_cohort_anomaly_is_empty_when_nothing_varies():
    states = {}
    for i in range(5):
        state = CandidateState(f"n{i}")
        state.set_features({"x": 1.0}, actor="t")
        states[f"n{i}"] = state
    assert all(score == 0.0 for _, score in cohort_anomaly(states))


# -- arm A --------------------------------------------------------------


def test_deterministic_sweep_beats_random_on_top_ten_recall():
    corpus = Corpus.build(seed=2026)
    score = score_survey(corpus, deterministic_sweep(corpus))
    assert score.planted_in_top[10] > score.random_top10_rate


def test_deterministic_sweep_does_not_promote_known_systems():
    corpus = Corpus.build(seed=2026)
    score = score_survey(corpus, deterministic_sweep(corpus))
    assert score.known_in_top10 <= 1


def test_the_sweep_records_every_tool_it_ran():
    corpus = Corpus.build(n_ordinary=4, n_planted=1)
    result = deterministic_sweep(corpus)
    for locus_id, tools in result.tools_per_locus.items():
        assert "sequence_stats" in tools, locus_id


# -- arm B --------------------------------------------------------------


def test_the_budgeted_baseline_is_recorded_as_failing():
    """The floor must be honestly reported, not quietly omitted."""
    corpus = Corpus.build(seed=2026)
    sweep = BudgetedSweep(
        registry=registry,
        investigator_factory=lambda e: CheapestFirstInvestigator(e, registry),
        budget=4,
    )
    score = score_survey(corpus, sweep.run(corpus))
    assert score.planted_in_top[20] == 0.0
    assert not any(score.analysed_the_planted_signal.values())


def test_a_budget_that_covers_everything_matches_the_sweep():
    corpus = Corpus.build(seed=2026, n_ordinary=8, n_planted=1)
    sweep = BudgetedSweep(
        registry=registry,
        investigator_factory=lambda e: CheapestFirstInvestigator(e, registry),
        budget=100,
    )
    budgeted = sweep.run(corpus)
    for tools in budgeted.tools_per_locus.values():
        assert "repeat_scan" in tools


# -- scoring ------------------------------------------------------------


def test_the_scorer_counts_confounders_above_the_worst_planted():
    corpus = Corpus.build(seed=2026)
    score = score_survey(corpus, deterministic_sweep(corpus))
    assert (
        score.confounders_above_worst_planted >= score.confounders_above_best_planted
    )


def test_the_scorer_names_the_decisive_tool_only_after_the_run():
    """The scorer may know the answer; nothing upstream of it may."""
    source = inspect.getsource(survey.deterministic_sweep).lower()
    assert "repeat_scan" not in source
    assert "repeat_scan" in inspect.signature(score_survey).parameters["decisive_tool"].default


def test_the_render_states_the_random_expectation():
    corpus = Corpus.build(seed=2026)
    text = score_survey(corpus, deterministic_sweep(corpus)).render()
    assert "random expectation" in text


def test_module_docstring_says_the_corpus_is_synthetic():
    assert "synthetic" in blind_rt.__doc__.lower()
    assert "not Anthropic's data" in blind_rt.__doc__
