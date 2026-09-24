from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from riborank.ranking import (
    evaluate_per_target,
    pairwise_ranking_accuracy,
    source_shift_summary,
    summarize_methods,
)
from riborank.scoring import add_scores, normalize


def make_frame(n: int = 10, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tm = np.linspace(0.05, 0.9, n)
    return pd.DataFrame(
        {
            "target_id": ["T1"] * n,
            "candidate_id": [f"c{i}" for i in range(n)],
            "candidate_source": ["casp"] * n,
            "has_native": [True] * n,
            "true_quality": tm,
            "true_rmsd_used": 20.0 - 20.0 * tm,
            "contact_map_f1": tm,
            "multi_metric_quality": tm,
            "contact_density": rng.random(n),
            "long_range_contact_density": rng.random(n),
            "clashes_per_residue": rng.random(n),
            "backbone_break_fraction": rng.random(n),
            "compactness": rng.random(n),
            "radius_of_gyration": rng.random(n) + 10.0,
            "num_residues": rng.integers(20, 200, n),
        }
    )


def test_a_perfect_ranker_has_hit_rate_one():
    frame = add_scores(make_frame())
    # Overwrite one scoring mode with the ground truth itself.
    frame["score_hybrid"] = frame["true_quality"]
    per_target = evaluate_per_target(frame, top_k=3)
    hybrid = per_target[
        (per_target["method"] == "hybrid") & (per_target["oracle_type"] == "tm_like")
    ]
    assert hybrid["oracle_in_top3"].all()
    assert hybrid["quality_regret"].abs().max() == pytest.approx(0.0)


def test_an_inverted_ranker_misses_the_oracle():
    frame = add_scores(make_frame())
    frame["score_hybrid"] = -frame["true_quality"]
    per_target = evaluate_per_target(frame, top_k=3)
    hybrid = per_target[
        (per_target["method"] == "hybrid") & (per_target["oracle_type"] == "tm_like")
    ]
    assert not hybrid["oracle_in_top3"].any()
    assert hybrid["quality_regret"].min() > 0.0


def test_top_k_covering_the_pool_always_hits():
    frame = add_scores(make_frame(n=4))
    per_target = evaluate_per_target(frame, top_k=4)
    assert per_target["oracle_in_top4"].all()


def test_regret_is_never_negative():
    frame = add_scores(make_frame(seed=3))
    per_target = evaluate_per_target(frame, top_k=3)
    assert (per_target["quality_regret"] >= -1e-12).all()
    assert (per_target["rmsd_regret"] >= -1e-12).all()


def test_pairwise_accuracy_is_one_for_a_perfect_ranker():
    frame = add_scores(make_frame())
    frame["score_hybrid"] = frame["true_quality"]
    summary = pairwise_ranking_accuracy(frame).set_index("method")
    assert summary.loc["hybrid", "mean_pairwise_accuracy"] == pytest.approx(1.0)


def test_pairwise_accuracy_is_zero_for_an_inverted_ranker():
    frame = add_scores(make_frame())
    frame["score_hybrid"] = -frame["true_quality"]
    summary = pairwise_ranking_accuracy(frame).set_index("method")
    assert summary.loc["hybrid", "mean_pairwise_accuracy"] == pytest.approx(0.0)


def test_tied_labels_are_excluded_from_the_denominator():
    frame = add_scores(make_frame(n=6))
    frame["true_quality"] = 0.5
    summary = pairwise_ranking_accuracy(frame)
    assert (summary["pairwise_comparisons"] == 0).all()


def test_unlabeled_rows_are_dropped():
    frame = add_scores(make_frame())
    frame.loc[frame.index[:5], "true_quality"] = np.nan
    frame.loc[frame.index[:5], "true_rmsd"] = np.nan
    frame.loc[frame.index[:5], "multi_metric_quality"] = np.nan
    per_target = evaluate_per_target(frame, top_k=2)
    assert (per_target["num_candidates"] == 5).all()


def test_empty_input_produces_empty_output():
    empty = pd.DataFrame(
        columns=["target_id", "true_quality", "true_rmsd", "multi_metric_quality"]
    )
    assert evaluate_per_target(empty).empty
    assert summarize_methods(pd.DataFrame()).empty
    assert source_shift_summary(empty).empty


def test_summary_reports_one_row_per_method_and_oracle():
    frame = add_scores(make_frame())
    summary = summarize_methods(evaluate_per_target(frame, top_k=3))
    assert len(summary) == 10  # 5 methods x 2 oracle definitions
    assert set(summary["oracle_type"]) == {"tm_like", "multi_metric"}


def test_source_shift_reports_the_oracle_source():
    frame = add_scores(make_frame())
    frame.loc[frame.index[-1], "candidate_source"] = "rhofold"
    summary = source_shift_summary(frame, top_k=3)
    assert set(summary["oracle_source"]) == {"rhofold"}


def test_normalize_handles_a_constant_column():
    assert (normalize(pd.Series([2.0] * 5)) == 0.0).all()


def test_normalize_produces_unit_variance():
    values = normalize(pd.Series([1.0, 2.0, 3.0, 4.0]))
    assert values.mean() == pytest.approx(0.0)
    assert values.std(ddof=0) == pytest.approx(1.0)


def test_selection_is_deterministic_under_massive_ties():
    """The low_clash baseline ties on most candidates; selection must not drift."""
    frame = add_scores(make_frame(n=12, seed=7))
    frame["score_hybrid"] = 0.0  # every candidate tied
    first = evaluate_per_target(frame, top_k=3)
    shuffled = frame.sample(frac=1.0, random_state=11).reset_index(drop=True)
    second = evaluate_per_target(shuffled, top_k=3)
    key = ["target_id", "method", "oracle_type"]
    pd.testing.assert_frame_equal(
        first.sort_values(by=key).reset_index(drop=True),
        second.sort_values(by=key).reset_index(drop=True),
    )


def test_tie_diagnostics_flags_a_degenerate_scoring_mode():
    from riborank.ranking import tie_diagnostics

    frame = add_scores(make_frame(n=10))
    frame["score_low_clash"] = 0.0
    diagnostics = tie_diagnostics(frame).set_index("method")
    assert diagnostics.loc["low_clash", "tied_fraction"] == pytest.approx(0.9)
    assert diagnostics.loc["hybrid", "tied_fraction"] == pytest.approx(0.0)
