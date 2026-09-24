#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a concise digest for an ensemble evaluation run.")
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--title", default="Expanded Native-Aware Evaluation Digest")
    parser.add_argument("--candidate-source", default="candidate ensemble")
    args = parser.parse_args()

    method = pd.read_csv(args.eval_dir / "method_metrics.csv")
    pairwise = pd.read_csv(args.eval_dir / "pairwise_accuracy.csv")
    per_target = pd.read_csv(args.eval_dir / "per_target_metrics.csv")
    features = pd.read_csv(args.eval_dir / "features.csv")
    ties_path = args.eval_dir / "score_ties.csv"
    ties = pd.read_csv(ties_path) if ties_path.exists() else None

    lines: list[str] = []
    lines.append(f"# {args.title}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Targets with native labels: `{features['target_id'].nunique()}`")
    lines.append(f"- Candidate structures: `{len(features)}`")
    lines.append(f"- Candidate source: {args.candidate_source}")
    lines.append("- Metric status: internal chain/window-aware `TM-like`, not official US-align TM-score")
    lines.append("")

    lines.append("## Top-5 Recovery")
    lines.append("")
    method_cols = [
        "oracle_type",
        "method",
        "targets",
        "mean_best_of_k_tm_like",
        "mean_best_of_k_multi_metric",
        "mean_tm_like_regret",
        "mean_rmsd_regret",
        "oracle_hit_rate",
    ]
    lines.append(method[method_cols].to_markdown(index=False))
    lines.append("")

    if ties is not None:
        lines.append("## Score Ties")
        lines.append("")
        lines.append(
            "Read this before the table above. A scoring mode that assigns the same "
            "score to most of its candidates is not ranking them; its top-5 is decided "
            "by the tie-break. See docs/METRICS.md."
        )
        lines.append("")
        lines.append(ties.to_markdown(index=False))
        lines.append("")
        degenerate = ties[ties["tied_fraction"] > 0.5]["method"].tolist()
        if degenerate:
            lines.append(
                "Modes whose ordering is mostly ties: "
                + ", ".join(f"`{name}`" for name in degenerate)
                + ". Their metrics are not evidence of ranking skill."
            )
            lines.append("")

    lines.append("## Pairwise Ranking Accuracy")
    lines.append("")
    lines.append(pairwise.to_markdown(index=False))
    lines.append("")

    top_method = (
        method[method["oracle_type"] == "tm_like"]
        .sort_values(["mean_best_of_k_tm_like", "oracle_hit_rate"], ascending=False)
        .iloc[0]
    )
    best_pairwise = pairwise.sort_values("mean_pairwise_accuracy", ascending=False).iloc[0]
    all_missed = bool((method["oracle_hit_rate"] == 0).all())

    lines.append("## Main Finding")
    lines.append("")
    lines.append(
        f"Best top-5 TM-like mode is `{top_method['method']}` "
        f"with mean best-of-5 TM-like `{top_method['mean_best_of_k_tm_like']:.6f}`. "
        f"Best pairwise mode is `{best_pairwise['method']}` "
        f"with mean pairwise accuracy `{best_pairwise['mean_pairwise_accuracy']:.6f}`."
    )
    if all_missed:
        lines.append("")
        lines.append(
            "No current scoring mode recovers the oracle candidate in top-5. "
            "This indicates the scoring modes are diagnostic baselines, not yet competition-grade rankers."
        )
    lines.append("")

    lines.append("## Per-Target Oracle Miss Summary")
    lines.append("")
    per_cols = [
        "target_id",
        "method",
        "num_candidates",
        "oracle_candidate",
        "oracle_tm_like",
        "selected_best_in_top5_candidate",
        "best_of_5_tm_like",
        "tm_like_regret",
        "oracle_in_top5",
    ]
    miss = per_target[per_target["oracle_type"] == "tm_like"][per_cols]
    lines.append(miss.to_markdown(index=False))
    lines.append("")

    lines.append("## Next Technical Implication")
    lines.append("")
    lines.append(
        "Next work should improve scoring representation and calibration, not UI: "
        "train/evaluate on expanded CASP features, add generator-aware calibration, "
        "and replace internal TM-like labels with official US-align scores where possible."
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
