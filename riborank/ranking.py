"""Ranking evaluation: regret against the oracle candidate, and pairwise accuracy.

The central question this module answers is *not* "how good is the best model in
the pool" but "does a scoring mode retrieve it". ``oracle_hit_rate`` is the
honest headline: it is the fraction of targets where the best available
candidate appears in the selected top-k.
"""

from __future__ import annotations

import hashlib
import itertools
import math

import numpy as np
import pandas as pd

from riborank.scoring import SCORE_COLUMNS, method_name

# Every ordering in this module ends with a tie key and uses a stable sort.
#
# The tie key must be deterministic AND carry no information. Both halves were
# learned the hard way (docs/CORRECTIONS.md):
#
# * With no tie key, ties were broken by the sort implementation, which changed
#   between pandas versions.
# * With ``candidate_id`` itself as the key, ties were broken alphabetically,
#   and filenames are not neutral: in the synthetic benchmark
#   ``decoy_001_small_noise`` sorts first, so a mode that tied on everything
#   "found" the least-perturbed decoy 62.5% of the time. Reversing the order
#   dropped that to 0%.
#
# A hash of the ID is reproducible and uncorrelated with how files are named.
TIE_KEY = "_tie_key"

TM_SORT = (["true_tm_like", "true_rmsd", TIE_KEY], [False, True, True])
MULTI_SORT = (["multi_metric_quality", "true_tm_like", TIE_KEY], [False, False, True])


def tie_key(candidate_ids: pd.Series) -> pd.Series:
    """Deterministic, naming-independent ordering key for tied candidates."""
    return candidate_ids.astype(str).map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )


def _with_tie_key(frame: pd.DataFrame) -> pd.DataFrame:
    if TIE_KEY in frame.columns:
        return frame
    return frame.assign(**{TIE_KEY: tie_key(frame["candidate_id"])})


def _oracle_sort(oracle_type: str) -> tuple[list[str], list[bool]]:
    return TM_SORT if oracle_type == "tm_like" else MULTI_SORT


def _sort_by_oracle(frame: pd.DataFrame, oracle_type: str) -> pd.DataFrame:
    columns, ascending = _oracle_sort(oracle_type)
    return _with_tie_key(frame).sort_values(by=columns, ascending=ascending, kind="stable")


def rank_by_score(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    """Deterministically order candidates by a scoring mode, best first."""
    return _with_tie_key(frame).sort_values(
        by=[score_column, TIE_KEY], ascending=[False, True], kind="stable"
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


# -- comparison against random selection ---------------------------------
#
# Every number above is meaningless without this section. Until it existed, no
# report in this repository said what picking candidates at random would score,
# and on CASP15 every baseline turned out to be *below* it.

DEFAULT_HIT_KS = (1, 5, 10, 25)


def expected_random_best_of_k(values: np.ndarray, k: int) -> float:
    """Exact expected maximum of ``k`` values drawn without replacement.

    With values sorted ascending, the i-th smallest (1-based) is the maximum of
    a random k-subset with probability ``C(i-1, k-1) / C(n, k)``.
    """
    ordered = np.sort(np.asarray(values, dtype=float))
    n = len(ordered)
    if n == 0:
        return np.nan
    k = min(k, n)
    total = math.comb(n, k)
    weights = np.array([math.comb(i - 1, k - 1) for i in range(1, n + 1)], dtype=float)
    return float((weights * ordered).sum() / total)


def _percentile_within(values: np.ndarray, value: float) -> float:
    """Share of the *other* candidates strictly worse than ``value``, in [0, 100]."""
    n = len(values)
    if n < 2:
        return np.nan
    return 100.0 * float((values < value).sum()) / (n - 1)


def pick_diagnostics(
    features: pd.DataFrame,
    top_k: int = 5,
    hit_ks: tuple[int, ...] = DEFAULT_HIT_KS,
    draws: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """Score every mode against random selection on the same pools.

    Columns:

    * ``mean_percentile_of_pick`` -- where the top-1 pick sits in its pool
      (100 = best, random expectation ~50).
    * ``hit@k`` -- fraction of targets whose best candidate is in the top k.
    * ``best_of_{top_k}`` -- mean quality of the best of the top ``top_k``.
    * ``verdict`` -- ``best_of_{top_k}`` against the 95% interval of random
      selection: ``below random``, ``within random`` or ``above random``.

    A final ``random`` row carries the exact random expectations.
    """
    labeled = features.dropna(subset=["true_tm_like"])
    if labeled.empty:
        return pd.DataFrame()
    groups = [(target_id, group) for target_id, group in labeled.groupby("target_id")]
    best_col = f"best_of_{top_k}"

    rows = []
    for score_column in SCORE_COLUMNS:
        if score_column not in labeled.columns:
            continue
        percentiles, best_of_k = [], []
        hits = {k: [] for k in hit_ks}
        for _, group in groups:
            ranked = rank_by_score(group, score_column)
            values = ranked["true_tm_like"].to_numpy()
            percentiles.append(_percentile_within(values, values[0]))
            best_of_k.append(float(values[:top_k].max()))
            oracle = _sort_by_oracle(group, "tm_like").iloc[0].candidate_id
            order = list(ranked["candidate_id"])
            for k in hit_ks:
                hits[k].append(oracle in order[:k])
        row = {
            "method": method_name(score_column),
            "mean_percentile_of_pick": float(np.nanmean(percentiles)),
            best_col: float(np.mean(best_of_k)),
        }
        row.update({f"hit@{k}": float(np.mean(hits[k])) for k in hit_ks})
        rows.append(row)

    # Exact random expectations.
    random_row = {
        "method": "random",
        "mean_percentile_of_pick": float(
            np.nanmean(
                [
                    np.mean([_percentile_within(g["true_tm_like"].to_numpy(), v)
                             for v in g["true_tm_like"].to_numpy()])
                    for _, g in groups
                ]
            )
        ),
        best_col: float(
            np.mean([expected_random_best_of_k(g["true_tm_like"].to_numpy(), top_k)
                     for _, g in groups])
        ),
    }
    random_row.update(
        {f"hit@{k}": float(np.mean([min(k, len(g)) / len(g) for _, g in groups]))
         for k in hit_ks}
    )

    # Seeded interval for the random mean best-of-k across targets.
    rng = np.random.default_rng(seed)
    pools = [g["true_tm_like"].to_numpy() for _, g in groups]
    samples = np.empty(draws)
    for draw in range(draws):
        samples[draw] = np.mean(
            [pool[rng.choice(len(pool), size=min(top_k, len(pool)), replace=False)].max()
             for pool in pools]
        )
    low, high = np.percentile(samples, [2.5, 97.5])

    frame = pd.DataFrame(rows)
    frame["random_low"] = float(low)
    frame["random_high"] = float(high)
    frame["verdict"] = np.where(
        frame[best_col] < low,
        "below random",
        np.where(frame[best_col] > high, "above random", "within random"),
    )
    random_row.update({"random_low": float(low), "random_high": float(high),
                       "verdict": "reference"})
    frame = pd.concat([frame, pd.DataFrame([random_row])], ignore_index=True)
    ordered = ["method", "verdict", best_col, "random_low", "random_high",
               "mean_percentile_of_pick", *[f"hit@{k}" for k in hit_ks]]
    return frame[ordered]
