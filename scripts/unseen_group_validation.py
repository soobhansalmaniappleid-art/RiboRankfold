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
            "Run leave-oracle-group-out validation for CASP-style source-aware RNA candidate ranking. "
            "This estimates what happens when the oracle-producing source/group is unseen during calibration."
        )
    )
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    features = add_group_columns(features)
    labeled = features.dropna(subset=["true_tm_like", "true_rmsd"]).copy()
    if labeled.empty:
        raise SystemExit("No native labels found")

    oracle_table = build_oracle_table(labeled)
    results = run_leave_oracle_group_out(labeled, oracle_table, top_k=args.top_k)
    metrics = summarize(results, top_k=args.top_k)
    group_metrics = summarize_by_heldout_group(results, top_k=args.top_k)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    oracle_table.to_csv(args.out_dir / "oracle_table.csv", index=False)
    results.to_csv(args.out_dir / "unseen_group_per_target.csv", index=False)
    metrics.to_csv(args.out_dir / "unseen_group_metrics.csv", index=False)
    group_metrics.to_csv(args.out_dir / "unseen_group_by_group_metrics.csv", index=False)
    (args.out_dir / "unseen_group_report.md").write_text(
        render_report(oracle_table, metrics, group_metrics, results, top_k=args.top_k),
        encoding="utf-8",
    )
    print(f"Wrote unseen-group validation to {args.out_dir}")


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["casp_group"] = frame["candidate_id"].map(extract_group)
    return frame


def extract_group(candidate_id: str) -> str:
    match = GROUP_RE.search(str(candidate_id))
    return match.group(1) if match else "unknown"


def build_oracle_table(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for target_id, group in features.groupby("target_id"):
        oracle = get_oracle(group)
        rows.append(
            {
                "target_id": target_id,
                "oracle_candidate": oracle.candidate_id,
                "oracle_group": oracle.casp_group,
                "oracle_tm_like": oracle.true_tm_like,
                "oracle_rmsd": oracle.true_rmsd,
            }
        )
    return pd.DataFrame(rows)


def get_oracle(group: pd.DataFrame) -> pd.Series:
    return group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]


def run_leave_oracle_group_out(features: pd.DataFrame, oracle_table: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    oracle_groups = sorted(oracle_table["oracle_group"].unique())
    for heldout_group in oracle_groups:
        test_targets = set(oracle_table.loc[oracle_table["oracle_group"] == heldout_group, "target_id"])
        train = features[~features["target_id"].isin(test_targets)].copy()
        train_without_heldout_group = train[train["casp_group"] != heldout_group].copy()
        priors = build_group_priors(train_without_heldout_group)
        global_mean = float(train_without_heldout_group["true_tm_like"].mean()) if not train_without_heldout_group.empty else 0.0

        for target_id in sorted(test_targets):
            test = features[features["target_id"] == target_id].copy()
            oracle = get_oracle(test)
            scored = add_scores(test, priors, global_mean)
            for method, score_column in score_columns().items():
                selected = scored.sort_values(score_column, ascending=False).head(top_k)
                selected_best = selected.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
                selected_top1 = selected.iloc[0]
                rows.append(
                    {
                        "heldout_oracle_group": heldout_group,
                        "target_id": target_id,
                        "method": method,
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
                        "oracle_group_seen_in_train": bool(heldout_group in set(priors["casp_group"])),
                    }
                )
    return pd.DataFrame(rows)


def build_group_priors(train: pd.DataFrame) -> pd.DataFrame:
    if train.empty:
        return pd.DataFrame(
            columns=[
                "casp_group",
                "group_mean_tm_like",
                "group_max_tm_like",
                "group_oracle_rate",
                "group_targets",
            ]
        )
    oracle_rows = []
    for target_id, group in train.groupby("target_id"):
        oracle = get_oracle(group)
        oracle_rows.append({"target_id": target_id, "casp_group": oracle.casp_group})
    oracle = pd.DataFrame(oracle_rows)
    target_count = train["target_id"].nunique()
    oracle_counts = oracle["casp_group"].value_counts().rename("oracle_count")
    priors = (
        train.groupby("casp_group")
        .agg(
            group_mean_tm_like=("true_tm_like", "mean"),
            group_max_tm_like=("true_tm_like", "max"),
            group_targets=("target_id", "nunique"),
        )
        .join(oracle_counts, how="left")
        .fillna({"oracle_count": 0})
        .reset_index()
    )
    priors["group_oracle_rate"] = priors["oracle_count"] / max(target_count, 1)
    return priors


def add_scores(test: pd.DataFrame, priors: pd.DataFrame, global_mean: float) -> pd.DataFrame:
    scored = test.merge(priors, on="casp_group", how="left")
    scored["group_mean_tm_like"] = scored["group_mean_tm_like"].fillna(global_mean)
    scored["group_max_tm_like"] = scored["group_max_tm_like"].fillna(global_mean)
    scored["group_oracle_rate"] = scored["group_oracle_rate"].fillna(0.0)
    scored["score_unseen_group_mean"] = scored["group_mean_tm_like"]
    scored["score_unseen_group_oracle_rate"] = scored["group_oracle_rate"]
    scored["score_unseen_group_hybrid"] = (
        0.50 * normalize(scored["score_hybrid"])
        + 0.35 * normalize(scored["group_mean_tm_like"])
        + 0.15 * normalize(scored["group_oracle_rate"])
    )
    scored["score_unseen_group_compact"] = (
        0.50 * normalize(scored["score_compact"])
        + 0.35 * normalize(scored["group_mean_tm_like"])
        + 0.15 * normalize(scored["group_oracle_rate"])
    )
    scored["score_unseen_fallback_hybrid"] = np.where(
        scored["group_targets"].isna(),
        normalize(scored["score_hybrid"]),
        scored["score_unseen_group_hybrid"],
    )
    scored["score_unseen_fallback_compact"] = np.where(
        scored["group_targets"].isna(),
        normalize(scored["score_compact"]),
        scored["score_unseen_group_compact"],
    )
    return scored


def normalize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - float(values.mean())) / std


def score_columns() -> dict[str, str]:
    return {
        "hybrid": "score_hybrid",
        "compact": "score_compact",
        "low_clash": "score_low_clash",
        "contact": "score_contact",
        "unseen_group_mean": "score_unseen_group_mean",
        "unseen_group_oracle_rate": "score_unseen_group_oracle_rate",
        "unseen_group_hybrid": "score_unseen_group_hybrid",
        "unseen_group_compact": "score_unseen_group_compact",
        "unseen_fallback_hybrid": "score_unseen_fallback_hybrid",
        "unseen_fallback_compact": "score_unseen_fallback_compact",
    }


def summarize(results: pd.DataFrame, top_k: int) -> pd.DataFrame:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    return (
        results.groupby("method")
        .agg(
            targets=("target_id", "nunique"),
            mean_best_of_k_tm_like=(best_col, "mean"),
            mean_tm_like_regret=("tm_like_regret", "mean"),
            oracle_hit_rate=(hit_col, "mean"),
        )
        .reset_index()
        .sort_values(["oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=False)
    )


def summarize_by_heldout_group(results: pd.DataFrame, top_k: int) -> pd.DataFrame:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    return (
        results.groupby(["heldout_oracle_group", "method"])
        .agg(
            targets=("target_id", "nunique"),
            mean_best_of_k_tm_like=(best_col, "mean"),
            mean_tm_like_regret=("tm_like_regret", "mean"),
            oracle_hit_rate=(hit_col, "mean"),
        )
        .reset_index()
        .sort_values(["heldout_oracle_group", "oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=[True, False, False])
    )


def render_report(
    oracle_table: pd.DataFrame,
    metrics: pd.DataFrame,
    group_metrics: pd.DataFrame,
    results: pd.DataFrame,
    top_k: int,
) -> str:
    lines: list[str] = []
    lines.append("# Unseen Group Validation")
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        "For each oracle-producing CASP group, all targets whose oracle comes from that group are held out. "
        "Group priors are trained on the remaining targets after removing candidates from the held-out oracle group. "
        "This evaluates source-aware ranking when the best source is unseen during calibration."
    )
    lines.append("")
    lines.append("## Oracle Groups")
    lines.append("")
    lines.append(
        oracle_table["oracle_group"]
        .value_counts()
        .rename_axis("oracle_group")
        .reset_index(name="targets")
        .to_markdown(index=False)
    )
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append(metrics.to_markdown(index=False))
    lines.append("")
    lines.append("## Metrics by Held-Out Oracle Group")
    lines.append("")
    for heldout_group, frame in group_metrics.groupby("heldout_oracle_group"):
        lines.append(f"### {heldout_group}")
        lines.append("")
        lines.append(frame.to_markdown(index=False))
        lines.append("")
    lines.append("## Per-Target Results")
    lines.append("")
    display = results[
        [
            "heldout_oracle_group",
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
        "If unseen-group methods collapse to candidate-level baselines, the strong group calibration result depends on repeated source identity. "
        "If fallback methods improve, candidate-level structure features can partially recover when source priors are unavailable."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
