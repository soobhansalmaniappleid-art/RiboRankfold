from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from riborank.ranking import expected_random_best_of_k, pick_diagnostics
from riborank.scoring import add_scores


def multi_target_frame(targets: int = 8, per_target: int = 30, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for t in range(targets):
        quality = rng.random(per_target)
        frames.append(
            pd.DataFrame(
                {
                    "target_id": [f"T{t}"] * per_target,
                    "candidate_id": [f"T{t}_c{i}" for i in range(per_target)],
                    "candidate_source": ["casp"] * per_target,
                    "has_native": [True] * per_target,
                    "true_quality": quality,
                    "true_rmsd_used": 20.0 * (1.0 - quality),
                    "contact_map_f1": quality,
                    "multi_metric_quality": quality,
                    "num_residues": [50 + 10 * t] * per_target,
                    "radius_of_gyration": rng.random(per_target) + 15.0,
                    "contact_density": rng.random(per_target),
                    "long_range_contact_density": rng.random(per_target),
                    "clashes_per_residue": rng.random(per_target),
                    "backbone_break_fraction": rng.random(per_target),
                    "compactness": rng.random(per_target),
                }
            )
        )
    return add_scores(pd.concat(frames, ignore_index=True))


@pytest.mark.parametrize("k", [1, 2, 3, 5])
def test_exact_expectation_matches_brute_force(k):
    values = np.array([0.1, 0.7, 0.3, 0.3, 0.9, 0.05, 0.6])
    subsets = list(itertools.combinations(values, k))
    brute = np.mean([max(subset) for subset in subsets])
    assert expected_random_best_of_k(values, k) == pytest.approx(brute)


def test_k_of_one_is_the_mean():
    values = np.array([1.0, 2.0, 6.0])
    assert expected_random_best_of_k(values, 1) == pytest.approx(3.0)


def test_k_covering_the_pool_is_the_maximum():
    values = np.array([0.2, 0.8, 0.5])
    assert expected_random_best_of_k(values, 3) == pytest.approx(0.8)
    assert expected_random_best_of_k(values, 10) == pytest.approx(0.8)


def test_empty_pool():
    assert np.isnan(expected_random_best_of_k(np.array([]), 3))


def diagnostics_for(frame: pd.DataFrame) -> pd.DataFrame:
    return pick_diagnostics(frame, top_k=5, draws=500).set_index("method")


def test_a_perfect_ranker_is_above_random():
    frame = multi_target_frame()
    frame["score_hybrid"] = frame["true_quality"]
    diagnostics = diagnostics_for(frame)
    assert diagnostics.loc["hybrid", "verdict"] == "above random"
    assert diagnostics.loc["hybrid", "mean_percentile_of_pick"] == pytest.approx(100.0)
    assert diagnostics.loc["hybrid", "hit@1"] == pytest.approx(1.0)


def test_an_inverted_ranker_is_below_random():
    frame = multi_target_frame()
    frame["score_hybrid"] = -frame["true_quality"]
    diagnostics = diagnostics_for(frame)
    assert diagnostics.loc["hybrid", "verdict"] == "below random"
    assert diagnostics.loc["hybrid", "mean_percentile_of_pick"] == pytest.approx(0.0)
    assert diagnostics.loc["hybrid", "hit@25"] == pytest.approx(0.0)


def test_random_row_carries_exact_expectations():
    frame = multi_target_frame(per_target=30)
    random_row = diagnostics_for(frame).loc["random"]
    assert random_row["hit@1"] == pytest.approx(1 / 30)
    assert random_row["hit@25"] == pytest.approx(25 / 30)
    assert random_row["mean_percentile_of_pick"] == pytest.approx(50.0)
    assert random_row["random_low"] <= random_row["best_of_5"] <= random_row["random_high"]


def test_every_scoring_mode_gets_a_row():
    methods = set(diagnostics_for(multi_target_frame()).index)
    assert methods == {"hybrid", "contact", "low_clash", "compact", "plausibility", "random"}


def test_diagnostics_are_reproducible():
    frame = multi_target_frame()
    pd.testing.assert_frame_equal(
        pick_diagnostics(frame, draws=300, seed=4), pick_diagnostics(frame, draws=300, seed=4)
    )


def test_unlabeled_input_gives_an_empty_frame():
    frame = multi_target_frame()
    frame["true_quality"] = np.nan
    assert pick_diagnostics(frame).empty


def test_tie_break_does_not_follow_candidate_names():
    """Names that sort in quality order must not leak through the tie-break."""
    frames = []
    for t in range(40):
        quality = np.linspace(1.0, 0.1, 10)  # a_... is best, j_... is worst
        frames.append(
            pd.DataFrame(
                {
                    "target_id": [f"T{t}"] * 10,
                    "candidate_id": [f"{chr(97 + i)}_T{t}" for i in range(10)],
                    "true_quality": quality,
                    "true_rmsd_used": 1.0 - quality,
                    "score_low_clash": 0.0,  # every candidate tied
                }
            )
        )
    frame = pd.concat(frames, ignore_index=True)
    from riborank.ranking import rank_by_score

    hit1 = np.mean(
        [rank_by_score(g, "score_low_clash").iloc[0]["true_quality"] == 1.0
         for _, g in frame.groupby("target_id")]
    )
    # Alphabetical tie-breaking would give 1.0 here; chance is 0.1.
    assert hit1 < 0.3


def _brute_force_over_tie_orders(scores, quality, oracle, k):
    """Average top-k statistics over every order consistent with the scores."""
    scores, quality = np.asarray(scores, float), np.asarray(quality, float)
    results = []
    for order in itertools.permutations(range(len(scores))):
        ranked = list(order)
        if any(scores[a] < scores[b] for a, b in zip(ranked, ranked[1:], strict=False)):
            continue  # not a valid ranking under these scores
        results.append((quality[ranked[:k]].max(), oracle in ranked[:k]))
    best, hit = zip(*results, strict=True)
    return float(np.mean(best)), float(np.mean(hit))


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_tie_aware_pick_matches_brute_force(k):
    from riborank.ranking import tie_aware_pick

    scores = [0.9, 0.5, 0.5, 0.5, 0.1, 0.1]
    quality = [0.2, 0.8, 0.3, 0.6, 0.95, 0.1]
    oracle = 4
    expected_best, expected_hit = _brute_force_over_tie_orders(scores, quality, oracle, k)
    result = tie_aware_pick(np.array(scores), np.array(quality), oracle, (k,), k)
    assert result["best"] == pytest.approx(expected_best)
    assert result[f"hit@{k}"] == pytest.approx(expected_hit)


def test_a_fully_tied_mode_scores_exactly_like_random():
    frame = multi_target_frame()
    frame["score_low_clash"] = 0.0
    diagnostics = diagnostics_for(frame)
    columns = ["best_of_5", "mean_percentile_of_pick", "hit@1", "hit@5", "hit@10", "hit@25"]
    pd.testing.assert_series_equal(
        diagnostics.loc["low_clash", columns].astype(float),
        diagnostics.loc["random", columns].astype(float),
        check_names=False,
    )


def test_diagnostics_do_not_depend_on_candidate_names():
    frame = multi_target_frame()
    frame["score_low_clash"] = np.round(frame["score_low_clash"], 0)  # heavy ties
    renamed = frame.copy()
    renamed["candidate_id"] = "zz_" + renamed["candidate_id"].str[::-1]
    columns = ["best_of_5", "mean_percentile_of_pick", "hit@1", "hit@5", "hit@10", "hit@25"]
    pd.testing.assert_frame_equal(
        pick_diagnostics(frame, draws=200)[columns],
        pick_diagnostics(renamed, draws=200)[columns],
    )


# -- retrieval curve ----------------------------------------------------


def test_a_perfect_ranker_retrieves_at_every_k():
    from riborank.ranking import retrieval_curve

    # 20 targets: a sign-flip test on 8 targets bottoms out at p ~ 2^-8, which
    # is too close to the Holm threshold for a stable assertion.
    frame = multi_target_frame(targets=20)
    frame["score_hybrid"] = frame["true_quality"]
    curve = retrieval_curve(frame, ks=(1, 5), draws=2000)
    hybrid = curve[curve["method"] == "hybrid"].set_index("k")
    assert hybrid.loc[1, "hit@k"] == pytest.approx(1.0)
    assert hybrid.loc[5, "hit@k"] == pytest.approx(1.0)
    assert bool(hybrid.loc[1, "survives_holm"])


def test_a_small_benchmark_cannot_detect_even_a_perfect_ranker():
    """The sign-flip floor is 2^-n, so ten targets cannot clear a wide grid."""
    from riborank.ranking import retrieval_curve

    frame = multi_target_frame(targets=5)
    frame["score_hybrid"] = frame["true_quality"]
    curve = retrieval_curve(frame, ks=(1, 2, 5, 10), draws=2000)
    assert not curve["survives_holm"].any()


def test_an_uninformative_ranker_does_not_survive_correction():
    from riborank.ranking import retrieval_curve

    frame = multi_target_frame()
    frame["score_hybrid"] = 0.0  # fully tied, i.e. random
    curve = retrieval_curve(frame, ks=(1, 5, 10), draws=2000)
    hybrid = curve[curve["method"] == "hybrid"]
    assert not hybrid["survives_holm"].any()
    assert hybrid["delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_random_expectation_matches_k_over_pool_size():
    from riborank.ranking import retrieval_curve

    curve = retrieval_curve(multi_target_frame(per_target=30), ks=(3,), draws=500)
    assert curve["random_hit@k"].iloc[0] == pytest.approx(3 / 30)


def test_holm_is_stricter_than_the_raw_p_value():
    from riborank.ranking import _holm

    # A single p just under 0.05 survives alone but not in a family of twenty.
    assert _holm([0.04]) == [True]
    assert _holm([0.04] + [0.9] * 19)[0] is False


def test_holm_is_step_down_not_bonferroni():
    from riborank.ranking import _holm

    assert _holm([0.001, 0.02]) == [True, True]  # 0.02 <= 0.05/1 once the first rejects


def test_targets_needed_grows_as_the_effect_shrinks():
    from riborank.ranking import targets_needed

    assert targets_needed(0.4, 0.375) < targets_needed(0.15, 0.187)
    assert targets_needed(0.15, 0.187, power=0.9) > targets_needed(0.15, 0.187, power=0.8)


def test_targets_needed_rejects_impossible_inputs():
    from riborank.ranking import targets_needed

    with pytest.raises(ValueError):
        targets_needed(0.0, 0.5)
    with pytest.raises(ValueError):
        targets_needed(0.1, 1.5)
