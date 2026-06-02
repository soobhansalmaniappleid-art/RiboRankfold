#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


GROUP_RE = re.compile(r"(TS\d+)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate leave-one-target-out CASP group calibration. "
            "Group priors are learned only from other targets, then applied to the held-out target."
        )
    )
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    features = add_group_columns(features)
    labeled = features.dropna(subset=["true_tm_like", "multi_metric_quality"]).copy()
    if labeled.empty:
        raise SystemExit("No native labels found in features file")

    predictions = build_leave_one_target_scores(labeled)
    per_target = evaluate(predictions, top_k=args.top_k)
    metrics = summarize(per_target, top_k=args.top_k)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.out_dir / "group_calibrated_predictions.csv", index=False)
    per_target.to_csv(args.out_dir / "group_calibrated_per_target.csv", index=False)
    metrics.to_csv(args.out_dir / "group_calibrated_metrics.csv", index=False)
    (args.out_dir / "group_calibrated_report.md").write_text(
        render_report(metrics, per_target, top_k=args.top_k),
        encoding="utf-8",
    )
    print(f"Wrote group-calibrated evaluation to {args.out_dir}")


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["casp_group"] = frame["candidate_id"].map(extract_group)
    return frame


def extract_group(candidate_id: str) -> str:
    match = GROUP_RE.search(str(candidate_id))
    return match.group(1) if match else "unknown"


def build_leave_one_target_scores(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    target_ids = sorted(features["target_id"].unique())
    for target_id in target_ids:
        train = features[features["target_id"] != target_id].copy()
        test = features[features["target_id"] == target_id].copy()
        priors = build_group_priors(train)
        global_mean = float(train["true_tm_like"].mean())
        global_oracle_rate = 0.0
        test = test.merge(priors, on="casp_group", how="left")
        test["group_mean_tm_like"] = test["group_mean_tm_like"].fillna(global_mean)
        test["group_max_tm_like"] = test["group_max_tm_like"].fillna(global_mean)
        test["group_oracle_rate"] = test["group_oracle_rate"].fillna(global_oracle_rate)
        test["score_group_mean"] = test["group_mean_tm_like"]
        test["score_group_max"] = test["group_max_tm_like"]
        test["score_group_oracle_rate"] = test["group_oracle_rate"]
        test["score_group_calibrated_hybrid"] = (
            0.50 * normalize_within(test["score_hybrid"])
            + 0.35 * normalize_within(test["score_group_mean"])
            + 0.15 * normalize_within(test["score_group_oracle_rate"])
        )
        test["score_group_calibrated_compact"] = (
            0.50 * normalize_within(test["score_compact"])
            + 0.35 * normalize_within(test["score_group_mean"])
            + 0.15 * normalize_within(test["score_group_oracle_rate"])
        )
        rows.append(test)
    return pd.concat(rows, ignore_index=True)


def build_group_priors(train: pd.DataFrame) -> pd.DataFrame:
    oracle_rows = []
    for target_id, group in train.groupby("target_id"):
        oracle = group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
        oracle_rows.append({"target_id": target_id, "casp_group": oracle.casp_group})
    oracle = pd.DataFrame(oracle_rows)
    target_count = train["target_id"].nunique()
    oracle_counts = oracle["casp_group"].value_counts().rename("oracle_count")
    priors = (
        train.groupby("casp_group")
        .agg(
            group_candidates=("candidate_id", "count"),
            group_targets=("target_id", "nunique"),
            group_mean_tm_like=("true_tm_like", "mean"),
            group_max_tm_like=("true_tm_like", "max"),
            group_mean_multi_metric=("multi_metric_quality", "mean"),
        )
        .join(oracle_counts, how="left")
        .fillna({"oracle_count": 0})
        .reset_index()
    )
    priors["oracle_count"] = priors["oracle_count"].astype(int)
    priors["group_oracle_rate"] = priors["oracle_count"] / max(target_count, 1)
    return priors


def normalize_within(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - float(values.mean())) / std


def evaluate(predictions: pd.DataFrame, top_k: int) -> pd.DataFrame:
    score_columns = [
        "score_hybrid",
        "score_compact",
        "score_low_clash",
        "score_contact",
        "score_group_mean",
        "score_group_max",
        "score_group_oracle_rate",
        "score_group_calibrated_hybrid",
        "score_group_calibrated_compact",
    ]
    rows: list[dict[str, object]] = []
    for target_id, group in predictions.groupby("target_id"):
        oracle = group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
        for score_column in score_columns:
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            selected_top1 = selected.iloc[0]
            selected_best = selected.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
            rows.append(
                {
                    "target_id": target_id,
                    "method": score_column.replace("score_", ""),
                    "oracle_candidate": oracle.candidate_id,
                    "oracle_group": oracle.casp_group,
                    "oracle_tm_like": oracle.true_tm_like,
                    "oracle_rmsd": oracle.true_rmsd,
                    "selected_top1_candidate": selected_top1.candidate_id,
                    "selected_top1_group": selected_top1.casp_group,
                    f"selected_best_in_top{top_k}_candidate": selected_best.candidate_id,
                    "selected_best_group": selected_best.casp_group,
                    f"best_of_{top_k}_tm_like": selected_best.true_tm_like,
                    f"best_of_{top_k}_rmsd": selected_best.true_rmsd,
                    "tm_like_regret": oracle.true_tm_like - selected_best.true_tm_like,
                    f"oracle_in_top{top_k}": bool(oracle.candidate_id in set(selected["candidate_id"])),
                }
            )
    return pd.DataFrame(rows)


def summarize(per_target: pd.DataFrame, top_k: int) -> pd.DataFrame:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    return (
        per_target.groupby("method")
        .agg(
            targets=("target_id", "nunique"),
            mean_best_of_k_tm_like=(best_col, "mean"),
            mean_tm_like_regret=("tm_like_regret", "mean"),
            oracle_hit_rate=(hit_col, "mean"),
        )
        .reset_index()
        .sort_values(["oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=False)
    )


def render_report(metrics: pd.DataFrame, per_target: pd.DataFrame, top_k: int) -> str:
    lines: list[str] = []
    lines.append("# CASP Group-Calibrated Evaluation")
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        "For each held-out target, CASP group priors are learned from all other targets only. "
        "This tests whether generator/group-aware calibration helps without using native labels from the target being evaluated."
    )
    lines.append("")
    lines.append("## Method Metrics")
    lines.append("")
    lines.append(metrics.to_markdown(index=False))
    lines.append("")
    lines.append(f"## Per-Target Top-{top_k} Results")
    lines.append("")
    display = per_target[
        [
            "target_id",
            "method",
            "oracle_group",
            "selected_top1_group",
            "selected_best_group",
            f"best_of_{top_k}_tm_like",
            "tm_like_regret",
            f"oracle_in_top{top_k}",
        ]
    ]
    lines.append(display.to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "If group-calibrated methods improve oracle hit rate, the expanded CASP failure is partly source-calibration failure. "
        "If they do not, the current candidate-level representation remains the main bottleneck."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
