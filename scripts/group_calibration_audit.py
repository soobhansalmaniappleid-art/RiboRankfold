#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


GROUP_RE = re.compile(r"(TS\d+)")
SCORE_COLUMNS = [
    "score_hybrid",
    "score_compact",
    "score_low_clash",
    "score_contact",
    "score_group_mean",
    "score_group_oracle_rate",
    "score_group_calibrated_hybrid",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether CASP group calibration is real source signal or a brittle group-ID shortcut. "
            "Runs real leave-one-target calibration, shuffled-group controls, and oracle-group masking."
        )
    )
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--shuffle-repeats", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    features = add_group_columns(features)
    labeled = features.dropna(subset=["true_tm_like", "true_rmsd", "multi_metric_quality"]).copy()
    if labeled.empty:
        raise SystemExit("No native labels found")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    real_predictions = build_leave_one_target_scores(labeled, mode="real")
    real_per_target, real_metrics = evaluate_predictions(real_predictions, top_k=args.top_k, condition="real")

    masked_predictions = build_leave_one_target_scores(labeled, mode="mask_oracle_group")
    masked_per_target, masked_metrics = evaluate_predictions(masked_predictions, top_k=args.top_k, condition="mask_oracle_group")

    shuffle_metrics_rows: list[pd.DataFrame] = []
    shuffle_per_target_rows: list[pd.DataFrame] = []
    rng = np.random.default_rng(args.seed)
    for repeat in range(args.shuffle_repeats):
        shuffled = shuffle_groups_within_target(labeled, rng)
        shuffled_predictions = build_leave_one_target_scores(shuffled, mode="real")
        per_target, metrics = evaluate_predictions(shuffled_predictions, top_k=args.top_k, condition="shuffled_group")
        per_target["repeat"] = repeat
        metrics["repeat"] = repeat
        shuffle_per_target_rows.append(per_target)
        shuffle_metrics_rows.append(metrics)

    shuffled_per_target = pd.concat(shuffle_per_target_rows, ignore_index=True)
    shuffled_metrics = pd.concat(shuffle_metrics_rows, ignore_index=True)
    shuffle_summary = summarize_shuffle(shuffled_metrics)

    audit_metrics = pd.concat([real_metrics, masked_metrics], ignore_index=True)
    audit_per_target = pd.concat([real_per_target, masked_per_target], ignore_index=True)

    audit_metrics.to_csv(args.out_dir / "real_and_masked_metrics.csv", index=False)
    audit_per_target.to_csv(args.out_dir / "real_and_masked_per_target.csv", index=False)
    shuffled_metrics.to_csv(args.out_dir / "shuffled_group_metrics.csv", index=False)
    shuffled_per_target.to_csv(args.out_dir / "shuffled_group_per_target.csv", index=False)
    shuffle_summary.to_csv(args.out_dir / "shuffled_group_summary.csv", index=False)

    report = render_report(
        real_metrics=real_metrics,
        masked_metrics=masked_metrics,
        shuffle_summary=shuffle_summary,
        real_per_target=real_per_target,
        masked_per_target=masked_per_target,
        top_k=args.top_k,
        shuffle_repeats=args.shuffle_repeats,
    )
    (args.out_dir / "calibration_audit_report.md").write_text(report, encoding="utf-8")
    print(f"Wrote group calibration audit to {args.out_dir}")


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["casp_group"] = frame["candidate_id"].map(extract_group)
    return frame


def extract_group(candidate_id: str) -> str:
    match = GROUP_RE.search(str(candidate_id))
    return match.group(1) if match else "unknown"


def shuffle_groups_within_target(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    shuffled_parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("target_id", sort=False):
        part = group.copy()
        values = part["casp_group"].to_numpy(copy=True)
        rng.shuffle(values)
        part["casp_group"] = values
        shuffled_parts.append(part)
    return pd.concat(shuffled_parts, ignore_index=True)


def build_leave_one_target_scores(features: pd.DataFrame, mode: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for target_id in sorted(features["target_id"].unique()):
        train = features[features["target_id"] != target_id].copy()
        test = features[features["target_id"] == target_id].copy()
        oracle_group = get_target_oracle(test).casp_group
        priors = build_group_priors(train)
        global_mean = float(train["true_tm_like"].mean())

        if mode == "mask_oracle_group":
            priors = priors[priors["casp_group"] != oracle_group].copy()

        test = test.merge(priors, on="casp_group", how="left")
        test["group_mean_tm_like"] = test["group_mean_tm_like"].fillna(global_mean)
        test["group_max_tm_like"] = test["group_max_tm_like"].fillna(global_mean)
        test["group_oracle_rate"] = test["group_oracle_rate"].fillna(0.0)
        test["score_group_mean"] = test["group_mean_tm_like"]
        test["score_group_max"] = test["group_max_tm_like"]
        test["score_group_oracle_rate"] = test["group_oracle_rate"]
        test["score_group_calibrated_hybrid"] = (
            0.50 * normalize_within(test["score_hybrid"])
            + 0.35 * normalize_within(test["score_group_mean"])
            + 0.15 * normalize_within(test["score_group_oracle_rate"])
        )
        test["audit_oracle_group"] = oracle_group
        test["audit_mode"] = mode
        rows.append(test)
    return pd.concat(rows, ignore_index=True)


def get_target_oracle(group: pd.DataFrame) -> pd.Series:
    return group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]


def build_group_priors(train: pd.DataFrame) -> pd.DataFrame:
    oracle_rows = []
    for target_id, group in train.groupby("target_id"):
        oracle = get_target_oracle(group)
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


def evaluate_predictions(predictions: pd.DataFrame, top_k: int, condition: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for target_id, group in predictions.groupby("target_id"):
        oracle = get_target_oracle(group)
        for score_column in SCORE_COLUMNS:
            if score_column not in group.columns:
                continue
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            selected_top1 = selected.iloc[0]
            selected_best = selected.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
            rows.append(
                {
                    "condition": condition,
                    "target_id": target_id,
                    "method": score_column.replace("score_", ""),
                    "oracle_candidate": oracle.candidate_id,
                    "oracle_group": oracle.casp_group,
                    "oracle_tm_like": oracle.true_tm_like,
                    "selected_top1_candidate": selected_top1.candidate_id,
                    "selected_top1_group": selected_top1.casp_group,
                    f"selected_best_in_top{top_k}_candidate": selected_best.candidate_id,
                    "selected_best_group": selected_best.casp_group,
                    f"best_of_{top_k}_tm_like": selected_best.true_tm_like,
                    "tm_like_regret": oracle.true_tm_like - selected_best.true_tm_like,
                    f"oracle_in_top{top_k}": bool(oracle.candidate_id in set(selected["candidate_id"])),
                }
            )
    per_target = pd.DataFrame(rows)
    metrics = summarize(per_target, top_k=top_k)
    metrics["condition"] = condition
    metrics = metrics[
        [
            "condition",
            "method",
            "targets",
            "mean_best_of_k_tm_like",
            "mean_tm_like_regret",
            "oracle_hit_rate",
        ]
    ]
    return per_target, metrics


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


def summarize_shuffle(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby("method")
        .agg(
            repeats=("repeat", "nunique"),
            mean_best_of_k_tm_like_mean=("mean_best_of_k_tm_like", "mean"),
            mean_best_of_k_tm_like_std=("mean_best_of_k_tm_like", "std"),
            mean_tm_like_regret_mean=("mean_tm_like_regret", "mean"),
            mean_tm_like_regret_std=("mean_tm_like_regret", "std"),
            oracle_hit_rate_mean=("oracle_hit_rate", "mean"),
            oracle_hit_rate_std=("oracle_hit_rate", "std"),
            oracle_hit_rate_max=("oracle_hit_rate", "max"),
        )
        .reset_index()
        .sort_values(["oracle_hit_rate_mean", "mean_best_of_k_tm_like_mean"], ascending=False)
    )


def render_report(
    real_metrics: pd.DataFrame,
    masked_metrics: pd.DataFrame,
    shuffle_summary: pd.DataFrame,
    real_per_target: pd.DataFrame,
    masked_per_target: pd.DataFrame,
    top_k: int,
    shuffle_repeats: int,
) -> str:
    lines: list[str] = []
    lines.append("# Group Calibration Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit checks whether group-aware CASP calibration is a meaningful source signal or a brittle group-ID shortcut."
    )
    lines.append("")
    lines.append("## Real Leave-One-Target Calibration")
    lines.append("")
    lines.append(real_metrics.to_markdown(index=False))
    lines.append("")
    lines.append("## Oracle-Group Masking")
    lines.append("")
    lines.append(
        "The held-out target oracle group is removed from the train-derived priors before scoring the held-out target. "
        "Large performance collapse means the improvement depends strongly on recognizing the oracle-producing group."
    )
    lines.append("")
    lines.append(masked_metrics.to_markdown(index=False))
    lines.append("")
    lines.append(f"## Shuffled Group Control ({shuffle_repeats} repeats)")
    lines.append("")
    lines.append(
        "Group labels are shuffled within each target before leave-one-target calibration. "
        "If shuffled performance stays high, the group signal is probably not meaningful."
    )
    lines.append("")
    lines.append(shuffle_summary.to_markdown(index=False))
    lines.append("")

    hit_col = f"oracle_in_top{top_k}"
    real_best = real_metrics.sort_values(["oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=False).iloc[0]
    masked_best = masked_metrics[masked_metrics["method"] == real_best.method].iloc[0]
    shuffled_row = shuffle_summary[shuffle_summary["method"] == real_best.method]
    lines.append("## Audit Verdict")
    lines.append("")
    lines.append(
        f"Best real method: `{real_best.method}` with oracle hit rate `{real_best.oracle_hit_rate:.3f}` "
        f"and mean best-of-{top_k} TM-like `{real_best.mean_best_of_k_tm_like:.6f}`."
    )
    lines.append(
        f"When oracle-group priors are masked, the same method has oracle hit rate `{masked_best.oracle_hit_rate:.3f}`."
    )
    if not shuffled_row.empty:
        shuffled = shuffled_row.iloc[0]
        lines.append(
            f"Under shuffled group labels, the same method has mean oracle hit rate "
            f"`{shuffled.oracle_hit_rate_mean:.3f}` +/- `{shuffled.oracle_hit_rate_std:.3f}`."
        )
    lines.append("")
    lines.append(
        "Interpretation: if real calibration is much higher than shuffled control but collapses under oracle-group masking, "
        "then group identity contains real source signal, but the current improvement is heavily dependent on group/source priors."
    )
    lines.append("")
    lines.append(f"## Real Per-Target Results for Best Method")
    lines.append("")
    display = real_per_target[real_per_target["method"] == real_best.method][
        [
            "target_id",
            "oracle_group",
            "selected_top1_group",
            "selected_best_group",
            f"best_of_{top_k}_tm_like",
            "tm_like_regret",
            hit_col,
        ]
    ]
    lines.append(display.to_markdown(index=False))
    lines.append("")
    lines.append(f"## Masked Per-Target Results for Best Method")
    lines.append("")
    masked_display = masked_per_target[masked_per_target["method"] == real_best.method][
        [
            "target_id",
            "oracle_group",
            "selected_top1_group",
            "selected_best_group",
            f"best_of_{top_k}_tm_like",
            "tm_like_regret",
            hit_col,
        ]
    ]
    lines.append(masked_display.to_markdown(index=False))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
