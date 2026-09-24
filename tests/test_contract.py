from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from riborank.contract import (
    CONTRACT_VERSION,
    BenchmarkSpec,
    ContractError,
    build_candidate_table,
    build_summary_table,
    validate_candidates,
    validate_summary,
)
from riborank.ranking import pairwise_ranking_accuracy, pick_diagnostics
from tests.test_random_baseline import multi_target_frame

SPEC = BenchmarkSpec(name="unit", kind="controlled_decoy", description="synthetic")


def scored_frame(**kwargs) -> pd.DataFrame:
    frame = multi_target_frame(**kwargs)
    frame["label_metric"] = "usalign_tm"
    return frame


def candidate_row(**overrides) -> pd.DataFrame:
    base = {
        "contract_version": CONTRACT_VERSION,
        "benchmark": "unit",
        "benchmark_kind": "controlled_decoy",
        "target_id": "T0",
        "candidate_id": "c0",
        "method": "hybrid",
        "label_metric": "usalign_tm",
        "label": 0.5,
        "rank": 1,
        "selected": True,
        "tie_group_size": 1,
        "labelled": True,
    }
    base.update(overrides)
    return pd.DataFrame([base])


# -- spec ---------------------------------------------------------------


def test_unknown_benchmark_kind_is_rejected():
    with pytest.raises(ContractError, match="unknown benchmark kind"):
        BenchmarkSpec(name="x", kind="vibes")


def test_empty_benchmark_name_is_rejected():
    with pytest.raises(ContractError, match="name must not be empty"):
        BenchmarkSpec(name="", kind="experimental")


def test_the_three_kinds_are_distinct():
    for kind in ("prediction_pool", "experimental", "controlled_decoy"):
        assert BenchmarkSpec(name="x", kind=kind).kind == kind


# -- candidate table validation -----------------------------------------


def test_a_well_formed_row_validates():
    assert len(validate_candidates(candidate_row())) == 1


def test_missing_column_is_rejected():
    frame = candidate_row().drop(columns=["label_metric"])
    with pytest.raises(ContractError, match="missing required columns"):
        validate_candidates(frame)


def test_extra_column_is_rejected():
    """Ad-hoc columns are how a schema quietly stops meaning anything."""
    frame = candidate_row()
    frame["my_special_score"] = 1.0
    with pytest.raises(ContractError, match="outside the contract"):
        validate_candidates(frame)


def test_wrong_contract_version_is_rejected():
    with pytest.raises(ContractError, match="contract_version"):
        validate_candidates(candidate_row(contract_version=99))


def test_mixed_label_metrics_are_rejected():
    """Half official TM-score and half internal approximation is not a table."""
    frame = pd.concat(
        [candidate_row(), candidate_row(candidate_id="c1", label_metric="true_tm_like")],
        ignore_index=True,
    )
    with pytest.raises(ContractError, match="one label metric"):
        validate_candidates(frame)


def test_labelled_row_without_a_label_is_rejected():
    with pytest.raises(ContractError, match="must carry a label"):
        validate_candidates(candidate_row(label=np.nan, labelled=True))


def test_unlabelled_row_carrying_a_label_is_rejected():
    with pytest.raises(ContractError, match="must not carry a label"):
        validate_candidates(candidate_row(label=0.5, labelled=False))


def test_zero_tie_group_is_rejected():
    with pytest.raises(ContractError, match="tie_group_size"):
        validate_candidates(candidate_row(tie_group_size=0))


def test_zero_rank_is_rejected():
    with pytest.raises(ContractError, match="rank is 1-based"):
        validate_candidates(candidate_row(rank=0))


def test_duplicate_candidate_rows_are_rejected():
    frame = pd.concat([candidate_row(), candidate_row(rank=2)], ignore_index=True)
    with pytest.raises(ContractError, match="duplicate"):
        validate_candidates(frame)


def test_empty_table_is_rejected():
    with pytest.raises(ContractError, match="empty"):
        validate_candidates(candidate_row().iloc[0:0])


# -- building from real frames ------------------------------------------


def test_candidate_table_covers_every_method_and_candidate():
    frame = scored_frame(targets=4, per_target=10)
    table = build_candidate_table(frame, SPEC, top_k=3)
    assert set(table["method"]) == {"hybrid", "contact", "low_clash", "compact", "plausibility"}
    assert len(table) == 5 * 4 * 10


def test_ranks_are_dense_and_start_at_one():
    table = build_candidate_table(scored_frame(targets=2, per_target=6), SPEC)
    for (_, _), group in table.groupby(["method", "target_id"]):
        assert sorted(group["rank"]) == list(range(1, 7))


def test_exactly_top_k_are_selected_per_target():
    table = build_candidate_table(scored_frame(targets=3, per_target=9), SPEC, top_k=4)
    counts = table[table["selected"]].groupby(["method", "target_id"]).size()
    assert set(counts) == {4}


def test_tie_group_size_records_how_many_shared_the_score():
    frame = scored_frame(targets=1, per_target=8)
    frame["score_hybrid"] = 0.0  # everything tied
    table = build_candidate_table(frame, SPEC)
    hybrid = table[table["method"] == "hybrid"]
    assert set(hybrid["tie_group_size"]) == {8}


def test_tie_group_size_is_one_when_nothing_ties():
    frame = scored_frame(targets=1, per_target=8)
    frame["score_hybrid"] = np.arange(8, dtype=float)
    table = build_candidate_table(frame, SPEC)
    assert set(table[table["method"] == "hybrid"]["tie_group_size"]) == {1}


def test_unlabelled_candidates_are_marked_not_dropped():
    frame = scored_frame(targets=2, per_target=5)
    frame.loc[frame.index[:3], "true_quality"] = np.nan
    table = build_candidate_table(frame, SPEC)
    assert (~table["labelled"]).sum() == 3 * 5  # 3 candidates x 5 methods
    assert table["label"].isna().sum() == 3 * 5


def test_the_metric_is_carried_onto_every_row():
    table = build_candidate_table(scored_frame(targets=2), SPEC)
    assert set(table["label_metric"]) == {"usalign_tm"}


def test_a_frame_with_no_scores_is_rejected():
    frame = scored_frame(targets=2)
    frame = frame.drop(columns=[c for c in frame.columns if c.startswith("score_")])
    with pytest.raises(ContractError, match="no scoring columns"):
        build_candidate_table(frame, SPEC)


# -- summary ------------------------------------------------------------


def summary_for(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = build_candidate_table(frame, SPEC, top_k=5)
    return build_summary_table(
        frame,
        SPEC,
        candidates,
        pick_diagnostics(frame, top_k=5, draws=200),
        pairwise_ranking_accuracy(frame),
    )


def test_summary_has_one_row_per_method_and_no_random_row():
    summary = summary_for(scored_frame(targets=4))
    assert set(summary["method"]) == {
        "hybrid", "contact", "low_clash", "compact", "plausibility"
    }
    assert "random" not in set(summary["method"])


def test_summary_records_the_random_reference_as_columns():
    summary = summary_for(scored_frame(targets=4))
    assert summary["random_top1"].notna().all()
    assert summary["random_best_of_k"].notna().all()


def test_selected_mean_never_exceeds_the_oracle_mean():
    summary = summary_for(scored_frame(targets=5, per_target=20))
    assert (summary["mean_selected_label"] <= summary["mean_oracle_label"] + 1e-9).all()


def test_coverage_reflects_unlabelled_candidates():
    frame = scored_frame(targets=4, per_target=10)
    frame.loc[frame.index[:8], "true_quality"] = np.nan
    summary = summary_for(frame)
    assert summary["label_coverage"].iloc[0] == pytest.approx(1 - 8 / 40)


def test_summary_rejects_impossible_coverage():
    summary = summary_for(scored_frame(targets=3))
    summary.loc[0, "label_coverage"] = 1.5
    with pytest.raises(ContractError, match="label_coverage"):
        validate_summary(summary)


def test_summary_rejects_a_wrong_version():
    summary = summary_for(scored_frame(targets=3))
    summary["contract_version"] = 42
    with pytest.raises(ContractError, match="contract_version"):
        validate_summary(summary)


def test_summary_survives_a_csv_round_trip(tmp_path):
    summary = summary_for(scored_frame(targets=3))
    path = tmp_path / "summary.csv"
    summary.to_csv(path, index=False)
    assert len(validate_summary(pd.read_csv(path))) == len(summary)


def test_candidate_table_survives_a_csv_round_trip(tmp_path):
    table = build_candidate_table(scored_frame(targets=3, per_target=7), SPEC)
    path = tmp_path / "candidates.csv"
    table.to_csv(path, index=False)
    assert len(validate_candidates(pd.read_csv(path))) == len(table)
