from __future__ import annotations

from discovery.demo import annotate, build_pipeline, synthesise
from discovery.scoring import NoveltyScorer


def run():
    candidates, neighbourhoods = synthesise()
    annotate(candidates, neighbourhoods)
    return candidates, build_pipeline(NoveltyScorer()).run(candidates)


def test_low_complexity_junk_dies_at_qc():
    _, result = run()
    junk = [c for c in result.rejected() if c.candidate_id.startswith("junk")]
    assert len(junk) == 4
    assert all(c.dropped_by == "qc_complexity" for c in junk)


def test_known_systems_are_set_aside_by_the_known_stage():
    _, result = run()
    known = [c for c in result.rejected() if c.candidate_id.startswith("known")]
    assert len(known) == 6
    assert all(c.dropped_by == "known_systems" for c in known)


def test_the_planted_array_outranks_the_plain_unusual_partner():
    _, result = run()
    by_id = {c.candidate_id: c for c in result.survivors}
    assert by_id["array_0"].scores["priority"] > by_id["partner_0"].scores["priority"]


def test_the_array_locus_is_recovered_with_correct_geometry():
    _, result = run()
    array = next(c for c in result.survivors if c.candidate_id == "array_0")
    assert array.features["repeat_copy_count"] == 9.0
    assert array.features["repeat_mean_period"] == 140.0
    assert array.features["repeat_unit_identity"] == 1.0


def test_no_candidate_leaves_without_a_recorded_reason():
    candidates, result = run()
    for candidate in candidates:
        assert candidate.history, f"{candidate.candidate_id} has no history"
        if not candidate.alive:
            assert candidate.history[-1].reason


def test_every_candidate_is_accounted_for():
    candidates, result = run()
    assert len(result.survivors) + len(result.rejected()) == len(candidates)


def test_the_model_layer_sees_far_fewer_candidates_than_the_input():
    candidates, result = run()
    assert len(result.survivors) < len(candidates) / 2
