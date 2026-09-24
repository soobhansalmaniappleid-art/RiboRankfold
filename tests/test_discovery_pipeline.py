from __future__ import annotations

import json
import math

import pytest

from discovery.agents.base import RuleBasedClient, parse_verdict
from discovery.agents.review import AdversarialReview
from discovery.schema import AgentVerdict, Candidate
from discovery.scoring import NoveltyScorer, known_track, repeat_anomaly, reproducibility
from discovery.stages import Cost, Pipeline, Stage, StageResult, escalation_rule, threshold_rule


def make_candidate(cid: str = "c1", **features: float) -> Candidate:
    base = {
        "length": 5000.0,
        "low_complexity_fraction": 0.0,
        "ambiguous_fraction": 0.0,
        "architecture_novelty": 0.9,
        "unexplained_partner_fraction": 0.8,
        "repeat_copy_count": 9.0,
        "repeat_unit_identity": 0.97,
        "repeat_period_cv": 0.03,
        "cross_genome_support": 6.0,
    }
    base.update(features)
    return Candidate(candidate_id=cid, sequence="ACGT" * 100, features=base)


# -- schema / provenance ------------------------------------------------


def test_candidate_starts_alive_and_dies_once_dropped():
    candidate = make_candidate()
    assert candidate.alive
    candidate.record("qc", "drop", "too short")
    assert not candidate.alive
    assert candidate.dropped_by == "qc"


def test_first_drop_is_the_one_recorded():
    candidate = make_candidate()
    candidate.record("qc", "drop", "first")
    candidate.record("later", "drop", "second")
    assert candidate.dropped_by == "qc"


def test_json_round_trip_preserves_the_audit_trail(tmp_path):
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    candidate.record("qc", "keep", "passed")
    candidate.add_verdict(
        AgentVerdict(agent="skeptic", stance="refutes", confidence=0.6, rationale="maybe")
    )

    path = candidate.write_json(tmp_path / "c1.json")
    restored = Candidate.from_json(path)

    assert restored.candidate_id == candidate.candidate_id
    assert restored.sequence == candidate.sequence
    assert restored.history[0].reason == "passed"
    assert restored.verdicts[0].stance == "refutes"
    assert restored.scores["priority"] == pytest.approx(candidate.scores["priority"])


def test_unknown_schema_version_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 999, "candidate_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema version"):
        Candidate.from_json(path)


def test_confidence_outside_the_unit_interval_is_rejected():
    with pytest.raises(ValueError, match="confidence"):
        AgentVerdict(agent="a", stance="supports", confidence=1.5, rationale="")


# -- stages -------------------------------------------------------------


def test_pipeline_refuses_to_run_an_expensive_stage_before_a_cheap_one():
    expensive = Stage("agents", Cost.EXPENSIVE, lambda c: StageResult("keep", ""))
    cheap = Stage("qc", Cost.TRIVIAL, lambda c: StageResult("keep", ""))
    with pytest.raises(ValueError, match="cheapest-first"):
        Pipeline([expensive, cheap])


def test_pipeline_rejects_duplicate_stage_names():
    stage = Stage("qc", Cost.TRIVIAL, lambda c: StageResult("keep", ""))
    with pytest.raises(ValueError, match="duplicate"):
        Pipeline([stage, Stage("qc", Cost.CHEAP, lambda c: StageResult("keep", ""))])


def test_threshold_rule_keeps_and_drops():
    pipeline = Pipeline([Stage("len", Cost.TRIVIAL, threshold_rule("length", minimum=1000))])
    run = pipeline.run([make_candidate("keep"), make_candidate("drop", length=10.0)])
    assert [c.candidate_id for c in run.survivors] == ["keep"]
    assert run.rejected()[0].history[-1].reason.startswith("length=10")


def test_a_missing_feature_drops_rather_than_passes():
    candidate = Candidate(candidate_id="x", features={})
    run = Pipeline([Stage("s", Cost.TRIVIAL, threshold_rule("gc_content", minimum=0.1))]).run(
        [candidate]
    )
    assert not run.survivors
    assert "not computed" in candidate.history[-1].reason


def test_a_nan_feature_drops():
    candidate = make_candidate(gc_content=math.nan)
    run = Pipeline([Stage("s", Cost.TRIVIAL, threshold_rule("gc_content", minimum=0.1))]).run(
        [candidate]
    )
    assert not run.survivors
    assert "NaN" in candidate.history[-1].reason


def test_dropped_candidates_are_retained_for_audit():
    run = Pipeline([Stage("len", Cost.TRIVIAL, threshold_rule("length", minimum=1000))]).run(
        [make_candidate("a"), make_candidate("b", length=5.0)]
    )
    assert len(run.all_candidates) == 2
    assert [c.candidate_id for c in run.rejected()] == ["b"]


def test_later_stages_only_see_survivors():
    seen: list[str] = []

    def spy(candidate):
        seen.append(candidate.candidate_id)
        return StageResult("keep", "")

    Pipeline(
        [
            Stage("len", Cost.TRIVIAL, threshold_rule("length", minimum=1000)),
            Stage("spy", Cost.EXPENSIVE, spy),
        ]
    ).run([make_candidate("a"), make_candidate("b", length=5.0)])
    assert seen == ["a"]


def test_stats_account_for_every_candidate():
    run = Pipeline([Stage("len", Cost.TRIVIAL, threshold_rule("length", minimum=1000))]).run(
        [make_candidate("a"), make_candidate("b", length=5.0)]
    )
    stat = run.stats[0]
    assert stat.seen == stat.kept + stat.dropped == 2


def test_funnel_renders_the_narrowing():
    run = Pipeline([Stage("len", Cost.TRIVIAL, threshold_rule("length", minimum=1000))]).run(
        [make_candidate("a"), make_candidate("b", length=5.0)]
    )
    funnel = run.funnel()
    assert "input" in funnel and "len" in funnel and "-1" in funnel


def test_escalation_rule_marks_high_scores():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    run = Pipeline([Stage("esc", Cost.CHEAP, escalation_rule("priority", minimum=0.1))]).run(
        [candidate]
    )
    assert run.stats[0].escalated == 1
    assert candidate.alive


# -- scoring ------------------------------------------------------------


def test_repeat_anomaly_needs_at_least_three_copies():
    assert repeat_anomaly({"repeat_copy_count": 2.0, "repeat_unit_identity": 1.0,
                           "repeat_period_cv": 0.0}) == 0.0


def test_repeat_anomaly_rewards_regularity():
    regular = repeat_anomaly(
        {"repeat_copy_count": 9.0, "repeat_unit_identity": 0.98, "repeat_period_cv": 0.01}
    )
    irregular = repeat_anomaly(
        {"repeat_copy_count": 9.0, "repeat_unit_identity": 0.98, "repeat_period_cv": 0.24}
    )
    assert regular > irregular > 0.0


def test_a_single_observation_has_no_reproducibility():
    assert reproducibility({"cross_genome_support": 1.0}) == 0.0


def test_reproducibility_saturates():
    assert reproducibility({"cross_genome_support": 100.0}) == pytest.approx(1.0)


def test_low_complexity_sequence_cannot_score_highly():
    clean = make_candidate("clean")
    junk = make_candidate("junk", low_complexity_fraction=0.95, ambiguous_fraction=0.3)
    scorer = NoveltyScorer()
    assert scorer.score(clean)["priority"] > scorer.score(junk)["priority"]


def test_priority_collapses_without_independent_support():
    scorer = NoveltyScorer()
    supported = scorer.score(make_candidate("s"))["priority"]
    lone = scorer.score(make_candidate("l", cross_genome_support=1.0))["priority"]
    assert supported > lone


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        NoveltyScorer(weights={"architecture_novelty": 0.5})


def test_novelty_renormalises_over_missing_components():
    """Absent components are excluded; a measured zero is not absent."""
    scorer = NoveltyScorer()
    # Only architecture_novelty (0.35) and repeat_anomaly (0.25, measured as 0.0
    # because there is no array) are available, so the denominator is 0.60.
    assert scorer.novelty({"architecture_novelty": 1.0}) == pytest.approx(0.35 / 0.60)
    # Supplying the remaining components moves the result, proving they count.
    full = scorer.novelty(
        {
            "architecture_novelty": 1.0,
            "unexplained_partner_fraction": 1.0,
            "low_complexity_fraction": 0.0,
            "ambiguous_fraction": 0.0,
        }
    )
    assert full == pytest.approx(0.75)


def test_novelty_is_nan_when_nothing_is_measurable():
    assert math.isnan(NoveltyScorer(weights={"architecture_novelty": 1.0}).novelty({}))


def test_scoring_writes_an_evidence_entry():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    assert any(item.key == "priority" for item in candidate.evidence)


def test_known_track_is_separate_from_elimination():
    assert known_track({"architecture_novelty": 0.1}) is True
    assert known_track({"architecture_novelty": 0.9}) is False
    assert known_track({}) is False


# -- agents -------------------------------------------------------------


def test_verdict_parses_from_a_fenced_block():
    raw = '```json\n{"stance": "supports", "confidence": 0.8, "rationale": "ok"}\n```'
    verdict = parse_verdict(raw, agent="x")
    assert verdict.stance == "supports"
    assert verdict.confidence == pytest.approx(0.8)


def test_verdict_parses_json_embedded_in_prose():
    raw = 'Here is my answer: {"stance": "refutes", "confidence": 0.3, "rationale": "r"} done.'
    assert parse_verdict(raw, agent="x").stance == "refutes"


def test_unparseable_response_becomes_inconclusive_not_a_guess():
    verdict = parse_verdict("I think it's probably novel!", agent="x")
    assert verdict.stance == "inconclusive"
    assert verdict.confidence == 0.0


def test_invalid_stance_becomes_inconclusive():
    raw = '{"stance": "very_exciting", "confidence": 0.9, "rationale": "r"}'
    assert parse_verdict(raw, agent="x").stance == "inconclusive"


def test_out_of_range_confidence_is_clamped():
    raw = '{"stance": "supports", "confidence": 42, "rationale": "r"}'
    assert parse_verdict(raw, agent="x").confidence == pytest.approx(1.0)


def test_review_records_every_agent():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    outcome = AdversarialReview(client=RuleBasedClient(threshold=0.0)).run(candidate)
    assert {v.agent for v in outcome.verdicts} == {
        "investigator",
        "skeptic",
        "literature",
        "artifact",
    }
    assert len(candidate.verdicts) == 4


def test_unanimous_refutation_eliminates():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    outcome = AdversarialReview(client=RuleBasedClient(threshold=0.0, invert=True)).run(candidate)
    assert not outcome.survived
    assert candidate.dropped_by == "adversarial_review"


def test_refutation_outweighs_equal_support():
    """One refutation must beat one endorsement of the same confidence."""
    from discovery.agents.review import REFUTATION_WEIGHT

    assert REFUTATION_WEIGHT > 1.0


def test_inconclusive_verdicts_cannot_carry_a_candidate():
    class Mute:
        def complete(self, system: str, prompt: str) -> str:
            return "no idea"

    candidate = make_candidate()
    outcome = AdversarialReview(client=Mute()).run(candidate)
    assert outcome.support == 0.0
    assert not outcome.survived


def test_review_summary_mentions_the_outcome():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    summary = AdversarialReview(client=RuleBasedClient(threshold=0.0)).run(candidate).summary()
    assert "SURVIVED" in summary or "ELIMINATED" in summary
    assert "skeptic" in summary


def test_agent_evidence_is_labelled_as_model_output():
    candidate = make_candidate()
    NoveltyScorer().score(candidate)
    AdversarialReview(client=RuleBasedClient(threshold=0.0)).run(candidate)
    model_evidence = [item for item in candidate.evidence if item.kind == "model"]
    assert len(model_evidence) == 4
    assert all(item.source.startswith("agent:") for item in model_evidence)
