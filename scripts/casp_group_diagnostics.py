#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


TOPK_PREFIX = "best_of_"
GROUP_RE = re.compile(r"(TS\d+)")
MODEL_RE = re.compile(r"TS\d+[_-]?(\d+)$")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose CASP group/source bias in native-aware RNA ensemble evaluation artifacts."
    )
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    features = pd.read_csv(args.eval_dir / "features.csv")
    per_target = pd.read_csv(args.eval_dir / "per_target_metrics.csv")
    features = add_group_columns(features)
    per_target = add_group_columns_to_per_target(per_target, args.top_k)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    group_summary = build_group_summary(features)
    method_bias = build_method_group_bias(features, per_target, top_k=args.top_k)
    target_summary = build_target_group_summary(features, per_target, top_k=args.top_k)
    oracle_table = build_oracle_table(features)

    group_summary.to_csv(args.out_dir / "group_summary.csv", index=False)
    method_bias.to_csv(args.out_dir / "method_group_bias.csv", index=False)
    target_summary.to_csv(args.out_dir / "target_group_summary.csv", index=False)
    oracle_table.to_csv(args.out_dir / "oracle_groups.csv", index=False)

    report = render_report(group_summary, method_bias, target_summary, oracle_table, top_k=args.top_k)
    (args.out_dir / "group_diagnostics.md").write_text(report, encoding="utf-8")
    print(f"Wrote CASP group diagnostics to {args.out_dir}")


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["casp_group"] = frame["candidate_id"].map(extract_group)
    frame["casp_model_index"] = frame["candidate_id"].map(extract_model_index)
    return frame


def add_group_columns_to_per_target(frame: pd.DataFrame, top_k: int) -> pd.DataFrame:
    frame = frame.copy()
    selected_best_col = f"selected_best_in_top{top_k}_candidate"
    frame["oracle_group"] = frame["oracle_candidate"].map(extract_group)
    frame["selected_top1_group"] = frame["selected_top1_candidate"].map(extract_group)
    frame["selected_best_group"] = frame[selected_best_col].map(extract_group)
    return frame


def extract_group(candidate_id: str) -> str:
    match = GROUP_RE.search(str(candidate_id))
    return match.group(1) if match else "unknown"


def extract_model_index(candidate_id: str) -> int | None:
    match = MODEL_RE.search(str(candidate_id))
    return int(match.group(1)) if match else None


def build_oracle_table(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labeled = features.dropna(subset=["true_tm_like", "multi_metric_quality"])
    for target_id, group in labeled.groupby("target_id"):
        tm_oracle = group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
        multi_oracle = group.sort_values(["multi_metric_quality", "true_tm_like"], ascending=[False, False]).iloc[0]
        for oracle_type, oracle in [("tm_like", tm_oracle), ("multi_metric", multi_oracle)]:
            rows.append(
                {
                    "target_id": target_id,
                    "oracle_type": oracle_type,
                    "oracle_candidate": oracle.candidate_id,
                    "oracle_group": oracle.casp_group,
                    "oracle_tm_like": oracle.true_tm_like,
                    "oracle_rmsd": oracle.true_rmsd,
                    "oracle_contact_f1": oracle.contact_map_f1,
                    "oracle_multi_metric_quality": oracle.multi_metric_quality,
                }
            )
    return pd.DataFrame(rows)


def build_group_summary(features: pd.DataFrame) -> pd.DataFrame:
    labeled = features.dropna(subset=["true_tm_like", "multi_metric_quality"]).copy()
    oracle = build_oracle_table(labeled)
    tm_oracle_counts = (
        oracle[oracle["oracle_type"] == "tm_like"]["oracle_group"].value_counts().rename("tm_like_oracle_count")
    )
    multi_oracle_counts = (
        oracle[oracle["oracle_type"] == "multi_metric"]["oracle_group"].value_counts().rename("multi_metric_oracle_count")
    )
    summary = (
        labeled.groupby("casp_group")
        .agg(
            candidates=("candidate_id", "count"),
            targets_covered=("target_id", "nunique"),
            mean_tm_like=("true_tm_like", "mean"),
            median_tm_like=("true_tm_like", "median"),
            max_tm_like=("true_tm_like", "max"),
            mean_multi_metric=("multi_metric_quality", "mean"),
            max_multi_metric=("multi_metric_quality", "max"),
            mean_clashes=("clashes_per_residue", "mean"),
            mean_contact_density=("contact_density", "mean"),
            mean_compactness=("compactness", "mean"),
        )
        .join(tm_oracle_counts, how="left")
        .join(multi_oracle_counts, how="left")
        .fillna({"tm_like_oracle_count": 0, "multi_metric_oracle_count": 0})
        .reset_index()
    )
    summary["tm_like_oracle_count"] = summary["tm_like_oracle_count"].astype(int)
    summary["multi_metric_oracle_count"] = summary["multi_metric_oracle_count"].astype(int)
    return summary.sort_values(["tm_like_oracle_count", "max_tm_like"], ascending=[False, False])


def build_method_group_bias(features: pd.DataFrame, per_target: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labeled = features.dropna(subset=["true_tm_like"])
    oracle_tm = per_target[per_target["oracle_type"] == "tm_like"].copy()
    methods = sorted(oracle_tm["method"].unique())
    for method in methods:
        score_col = f"score_{method}"
        if score_col not in labeled.columns:
            continue
        selected_rows = []
        for target_id, group in labeled.groupby("target_id"):
            selected = group.sort_values(score_col, ascending=False).head(top_k).copy()
            selected_rows.append(selected)
        selected_frame = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
        selected_counts = selected_frame["casp_group"].value_counts()
        top1_counts = oracle_tm[oracle_tm["method"] == method]["selected_top1_group"].value_counts()
        best_counts = oracle_tm[oracle_tm["method"] == method]["selected_best_group"].value_counts()
        oracle_counts = oracle_tm[["target_id", "oracle_group"]].drop_duplicates()["oracle_group"].value_counts()
        all_groups = sorted(set(selected_counts.index) | set(top1_counts.index) | set(best_counts.index) | set(oracle_counts.index))
        for casp_group in all_groups:
            rows.append(
                {
                    "method": method,
                    "casp_group": casp_group,
                    "topk_selection_count": int(selected_counts.get(casp_group, 0)),
                    "top1_selection_count": int(top1_counts.get(casp_group, 0)),
                    "selected_best_count": int(best_counts.get(casp_group, 0)),
                    "oracle_count": int(oracle_counts.get(casp_group, 0)),
                    "topk_minus_oracle": int(selected_counts.get(casp_group, 0) - oracle_counts.get(casp_group, 0)),
                    "top1_minus_oracle": int(top1_counts.get(casp_group, 0) - oracle_counts.get(casp_group, 0)),
                }
            )
    return pd.DataFrame(rows).sort_values(["method", "topk_selection_count", "oracle_count"], ascending=[True, False, False])


def build_target_group_summary(features: pd.DataFrame, per_target: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labeled = features.dropna(subset=["true_tm_like"])
    oracle_tm = per_target[per_target["oracle_type"] == "tm_like"].copy()
    for item in oracle_tm.itertuples(index=False):
        target = labeled[labeled["target_id"] == item.target_id]
        method = item.method
        score_col = f"score_{method}"
        if score_col not in target.columns:
            continue
        topk = target.sort_values(score_col, ascending=False).head(top_k)
        rows.append(
            {
                "target_id": item.target_id,
                "method": method,
                "oracle_candidate": item.oracle_candidate,
                "oracle_group": item.oracle_group,
                "selected_top1_candidate": item.selected_top1_candidate,
                "selected_top1_group": item.selected_top1_group,
                "selected_best_group": item.selected_best_group,
                "oracle_in_topk": bool(getattr(item, f"oracle_in_top{top_k}")),
                "topk_groups": ",".join(topk["casp_group"].astype(str).tolist()),
                "unique_topk_groups": ",".join(sorted(topk["casp_group"].astype(str).unique())),
                "tm_like_regret": item.tm_like_regret,
                "oracle_tm_like": item.oracle_tm_like,
                f"best_of_{top_k}_tm_like": getattr(item, f"best_of_{top_k}_tm_like"),
            }
        )
    return pd.DataFrame(rows).sort_values(["target_id", "method"])


def render_report(
    group_summary: pd.DataFrame,
    method_bias: pd.DataFrame,
    target_summary: pd.DataFrame,
    oracle_table: pd.DataFrame,
    top_k: int,
) -> str:
    lines: list[str] = []
    lines.append("# CASP Group Diagnostics")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report checks whether expanded CASP failures are driven by group/source bias: "
        "which CASP groups produce oracle candidates, and which groups each scoring mode over-selects."
    )
    lines.append("")
    lines.append("## Oracle Groups")
    lines.append("")
    oracle_counts = (
        oracle_table[oracle_table["oracle_type"] == "tm_like"]["oracle_group"]
        .value_counts()
        .rename_axis("casp_group")
        .reset_index(name="tm_like_oracle_count")
    )
    lines.append(oracle_counts.to_markdown(index=False))
    lines.append("")
    lines.append("## Best Groups by Native-Aware Quality")
    lines.append("")
    display_cols = [
        "casp_group",
        "candidates",
        "targets_covered",
        "tm_like_oracle_count",
        "mean_tm_like",
        "max_tm_like",
        "mean_clashes",
        "mean_contact_density",
        "mean_compactness",
    ]
    lines.append(group_summary[display_cols].head(20).to_markdown(index=False))
    lines.append("")
    lines.append(f"## Top-{top_k} Selection Bias by Method")
    lines.append("")
    for method, group in method_bias.groupby("method"):
        lines.append(f"### {method}")
        lines.append("")
        lines.append(group.head(15).to_markdown(index=False))
        lines.append("")
    lines.append("## Per-Target Group Misses")
    lines.append("")
    lines.append(target_summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "If oracle groups rarely appear in top-k groups, the failure is not just score calibration; "
        "the selected structural regime is different from the near-native CASP regime. "
        "If one group dominates top-k selections without matching oracle frequency, the scorer has group/source bias."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
