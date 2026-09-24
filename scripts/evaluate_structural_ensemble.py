#!/usr/bin/env python
"""Thin CLI over ``riborank``. The logic lives in the package, not here."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from riborank.pipeline import add_labels, build_features, build_manifest, read_native_map
from riborank.ranking import (
    evaluate_per_target,
    pairwise_ranking_accuracy,
    source_shift_summary,
    summarize_methods,
    tie_diagnostics,
)
from riborank.report import render_ensemble_report
from riborank.scoring import add_scores


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a distribution-shift evaluation harness for RNA 3D candidate ensembles. "
            "Targets are expected as CANDIDATES_ROOT/TARGET_ID/*.pdb. If native.pdb is "
            "present for a target, labels and ranking metrics are computed."
        )
    )
    parser.add_argument("--candidates-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--native-name", default="native.pdb")
    parser.add_argument(
        "--native-map",
        type=Path,
        default=None,
        help=(
            "Optional CSV with columns target_id,native_path for benchmarks whose "
            "natives are stored outside target folders."
        ),
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-native-candidate", action="store_true")
    args = parser.parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive")
    return args


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = args.dataset_name or args.candidates_root.name

    manifest = build_manifest(
        args.candidates_root,
        native_name=args.native_name,
        include_native=args.include_native_candidate,
        native_map=read_native_map(args.native_map),
    )
    if manifest.empty:
        raise SystemExit(f"No candidate PDB files found under {args.candidates_root}")

    features = add_scores(add_labels(build_features(manifest)))
    manifest.to_csv(args.out_dir / "manifest.csv", index=False)
    features.to_csv(args.out_dir / "features.csv", index=False)

    empty = pd.DataFrame()
    per_target = method_metrics = pairwise = source_shift = ties = empty
    if bool(features["has_native"].any()):
        per_target = evaluate_per_target(features, top_k=args.top_k)
        method_metrics = summarize_methods(per_target)
        pairwise = pairwise_ranking_accuracy(features)
        source_shift = source_shift_summary(features, top_k=args.top_k)
        ties = tie_diagnostics(features)
        per_target.to_csv(args.out_dir / "per_target_metrics.csv", index=False)
        method_metrics.to_csv(args.out_dir / "method_metrics.csv", index=False)
        pairwise.to_csv(args.out_dir / "pairwise_accuracy.csv", index=False)
        source_shift.to_csv(args.out_dir / "source_shift_summary.csv", index=False)
        ties.to_csv(args.out_dir / "score_ties.csv", index=False)

    report = render_ensemble_report(
        dataset_name=dataset_name,
        candidates_root=args.candidates_root,
        features=features,
        per_target=per_target,
        method_metrics=method_metrics,
        pairwise=pairwise,
        source_shift=source_shift,
        top_k=args.top_k,
        ties=ties,
    )
    (args.out_dir / "summary.md").write_text(report, encoding="utf-8")
    print(f"Wrote ensemble evaluation artifacts to {args.out_dir}")


if __name__ == "__main__":
    main()
