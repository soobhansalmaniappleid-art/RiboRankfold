"""Ranking evaluation: regret against the oracle candidate, and pairwise accuracy.

The central question this module answers is *not* "how good is the best model in
the pool" but "does a scoring mode retrieve it". ``oracle_hit_rate`` is the
honest headline: it is the fraction of targets where the best available
candidate appears in the selected top-k.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

from riborank.scoring import SCORE_COLUMNS, method_name

# Every ordering in this module ends with ``candidate_id`` and uses a stable
# sort. Without that, ties are broken by whatever order the underlying sort
# happens to produce, which differs between pandas versions -- and the
# ``low_clash`` baseline ties on the majority of its candidates. See
# docs/METRICS.md, "Tie-breaking".
TIE_BREAK = "candidate_id"

TM_SORT = (["true_tm_like", "true_rmsd", TIE_BREAK], [False, True, True])
MULTI_SORT = (["multi_metric_quality", "true_tm_like", TIE_BREAK], [False, False, True])


def _oracle_sort(oracle_type: str) -> tuple[list[str], list[bool]]:
    return TM_SORT if oracle_type == "tm_like" else MULTI_SORT


def _sort_by_oracle(frame: pd.DataFrame, oracle_type: str) -> pd.DataFrame:
    columns, ascending = _oracle_sort(oracle_type)
    return frame.sort_values(by=columns, ascending=ascending, kind="stable")


def rank_by_score(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    """Deterministically order candidates by a scoring mode, best first."""
    return frame.sort_values(
        by=[score_column, TIE_BREAK], ascending=[False, True], kind="stable"
    )


def tie_diagnostics(features: pd.DataFrame) -> pd.DataFrame:
    """Report how much of each scoring mode's ordering is decided by ties.

    A high ``tied_fraction`` means the mode's top-k is largely arbitrary and its
    headline metrics should not be read as ranking skill.
    """
    labeled = features.dropna(subset=["true_tm_like"])
    rows = []
    for score_column in SCORE_COLUMNS:
        if score_column not in labeled.columns:
            continue
        total = int(len(labeled))
        distinct = int(labeled[score_column].nunique())
        rows.append(
            {
                "method": method_name(score_column),
                "candidates": total,
                "distinct_scores": distinct,
                "tied_fraction": float((total - distinct) / total) if total else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(by="tied_fraction", ascending=False)


def evaluate_per_target(features: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """Per-target regret for every (scoring mode, oracle definition) pair."""
    rows: list[dict[str, object]] = []
    labeled = features.dropna(subset=["true_tm_like", "true_rmsd", "multi_metric_quality"])
    for target_id, group in labeled.groupby("target_id"):
        oracles = {
            oracle_type: _sort_by_oracle(group, oracle_type).iloc[0]
            for oracle_type in ("tm_like", "multi_metric")
        }
        for score_column in SCORE_COLUMNS:
            selected = rank_by_score(group, score_column).head(top_k)
            selected_top1 = selected.iloc[0]
            selected_ids = set(selected["candidate_id"])
            for oracle_type, oracle in oracles.items():
                selected_best = _sort_by_oracle(selected, oracle_type).iloc[0]
                rows.append(
                    {
                        "target_id": target_id,
                        "method": method_name(score_column),
                        "oracle_type": oracle_type,
                        "num_candidates": int(len(group)),
                        "oracle_candidate": oracle.candidate_id,
                        "oracle_tm_like": float(oracle.true_tm_like),
                        "oracle_rmsd": float(oracle.true_rmsd),
                        "oracle_contact_f1": float(oracle.contact_map_f1),
                        "oracle_multi_metric_quality": float(oracle.multi_metric_quality),
                        "selected_top1_candidate": selected_top1.candidate_id,
                        "selected_top1_tm_like": float(selected_top1.true_tm_like),
                        "selected_top1_rmsd": float(selected_top1.true_rmsd),
                        "selected_top1_contact_f1": float(selected_top1.contact_map_f1),
                        "selected_top1_multi_metric_quality": float(
                            selected_top1.multi_metric_quality
                        ),
                        f"selected_best_in_top{top_k}_candidate": selected_best.candidate_id,
                        f"best_of_{top_k}_tm_like": float(selected_best.true_tm_like),
                        f"best_of_{top_k}_rmsd": float(selected_best.true_rmsd),
                        f"best_of_{top_k}_contact_f1": float(selected_best.contact_map_f1),
                        f"best_of_{top_k}_multi_metric_quality": float(
                            selected_best.multi_metric_quality
                        ),
                        "tm_like_regret": float(oracle.true_tm_like - selected_best.true_tm_like),
                        "rmsd_regret": float(selected_best.true_rmsd - oracle.true_rmsd),
                        "multi_metric_regret": float(
                            oracle.multi_metric_quality - selected_best.multi_metric_quality
                        ),
                        f"oracle_in_top{top_k}": bool(oracle.candidate_id in selected_ids),
                    }
                )
    return pd.DataFrame(rows)


def summarize_methods(per_target: pd.DataFrame) -> pd.DataFrame:
    if per_target.empty:
        return pd.DataFrame()
    topk_column = next(
        column
        for column in per_target.columns
        if column.startswith("best_of_") and column.endswith("_tm_like")
    )
    topk_multi_column = next(
        column
        for column in per_target.columns
        if column.startswith("best_of_") and column.endswith("_multi_metric_quality")
    )
    hit_column = next(
        column for column in per_target.columns if column.startswith("oracle_in_top")
    )
    return (
        per_target.groupby(["oracle_type", "method"])
        .agg(
            targets=("target_id", "nunique"),
            mean_best_of_k_tm_like=(topk_column, "mean"),
            mean_best_of_k_multi_metric=(topk_multi_column, "mean"),
            mean_tm_like_regret=("tm_like_regret", "mean"),
            mean_multi_metric_regret=("multi_metric_regret", "mean"),
            mean_rmsd_regret=("rmsd_regret", "mean"),
            oracle_hit_rate=(hit_column, "mean"),
        )
        .reset_index()
        .sort_values("mean_best_of_k_tm_like", ascending=False)
    )


def pairwise_ranking_accuracy(features: pd.DataFrame) -> pd.DataFrame:
    """Fraction of candidate pairs a scoring mode orders the same way as truth.

    Ties in either the true label or the score are excluded from the denominator.
    """
    rows = []
    labeled = features.dropna(subset=["true_tm_like"])
    for target_id, group in labeled.groupby("target_id"):
        pairs = list(itertools.combinations(group.index, 2))
        for score_column in SCORE_COLUMNS:
            total = 0
            correct = 0
            for left_idx, right_idx in pairs:
                left = group.loc[left_idx]
                right = group.loc[right_idx]
                if left.true_tm_like == right.true_tm_like:
                    continue
                truth = math.copysign(1.0, left.true_tm_like - right.true_tm_like)
                pred = (
                    math.copysign(1.0, left[score_column] - right[score_column])
                    if left[score_column] != right[score_column]
                    else 0.0
                )
                total += 1
                if pred == truth:
                    correct += 1
            rows.append(
                {
                    "target_id": target_id,
                    "method": method_name(score_column),
                    "pairwise_comparisons": total,
                    "pairwise_accuracy": correct / total if total else np.nan,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return (
        frame.groupby("method")
        .agg(
            targets=("target_id", "nunique"),
            pairwise_comparisons=("pairwise_comparisons", "sum"),
            mean_pairwise_accuracy=("pairwise_accuracy", "mean"),
        )
        .reset_index()
        .sort_values("mean_pairwise_accuracy", ascending=False)
    )


def source_shift_summary(features: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """Report source composition and whether a scoring mode selects across sources.

    With true multi-generator inputs this exposes whether a method generalizes
    beyond the dominant source.
    """
    labeled = features.dropna(subset=["true_tm_like"])
    if labeled.empty:
        return pd.DataFrame()
    rows = []
    for target_id, group in labeled.groupby("target_id"):
        oracle = _sort_by_oracle(group, "tm_like").iloc[0]
        source_counts = group["candidate_source"].value_counts().to_dict()
        for score_column in SCORE_COLUMNS:
            selected = rank_by_score(group, score_column).head(top_k)
            rows.append(
                {
                    "target_id": target_id,
                    "method": method_name(score_column),
                    "candidate_sources": ";".join(
                        f"{key}:{value}" for key, value in sorted(source_counts.items())
                    ),
                    "oracle_source": oracle.candidate_source,
                    "selected_top1_source": selected.iloc[0].candidate_source,
                    f"selected_top{top_k}_source_count": int(
                        selected["candidate_source"].nunique()
                    ),
                    "oracle_source_in_selected": bool(
                        oracle.candidate_source in set(selected["candidate_source"])
                    ),
                }
            )
    return pd.DataFrame(rows)
