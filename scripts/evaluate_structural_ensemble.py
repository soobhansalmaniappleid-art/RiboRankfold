#!/usr/bin/env python
"""Thin CLI over ``riborank``. The logic lives in the package, not here."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from riborank.contract import BenchmarkSpec, build_candidate_table, build_summary_table
from riborank.pipeline import (
    add_labels,
    apply_labels,
    build_features,
    build_manifest,
    label_coverage,
    read_native_map,
)
from riborank.ranking import (
    evaluate_per_target,
    pairwise_ranking_accuracy,
    pick_diagnostics,
    power_table,
    retrieval_curve,
    source_shift_summary,
    summarize_methods,
    tie_diagnostics,
)
from riborank.report import render_ensemble_report
from riborank.scoring import add_scores
from riborank.usalign import UsalignError, find_usalign, score_frame


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
    parser.add_argument(
        "--usalign",
        default=None,
        help=(
            "Path to the US-align binary. Defaults to $RIBORANK_USALIGN or PATH. "
            "Use --no-usalign to fall back to the internal tm_like approximation."
        ),
    )
    parser.add_argument("--no-usalign", action="store_true")
    parser.add_argument(
        "--label-metric",
        choices=["usalign_tm", "true_tm_like"],
        default=None,
        help="Force the ground-truth metric instead of preferring official TM-score.",
    )
    parser.add_argument("--usalign-workers", type=int, default=8)
    parser.add_argument(
        "--benchmark-kind",
        choices=["prediction_pool", "experimental", "controlled_decoy"],
        required=True,
        help=(
            "What this benchmark is. Real prediction pools, independent experimental "
            "structures and controlled decoys answer different questions and must not "
            "be averaged together."
        ),
    )
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

    features = add_labels(build_features(manifest))
    if not args.no_usalign:
        try:
            binary = find_usalign(args.usalign)
        except UsalignError as error:
            if args.usalign or args.label_metric == "usalign_tm":
                raise SystemExit(str(error)) from error
            print(f"WARNING: {error}\nFalling back to the internal tm_like metric.")
        else:
            print(f"Scoring with US-align at {binary}")
            features = score_frame(features, binary, workers=args.usalign_workers)
    features = add_scores(apply_labels(features, prefer=args.label_metric))
    label_metric = features["label_metric"].iloc[0]
    print(f"Ground-truth metric: {label_metric}")
    manifest.to_csv(args.out_dir / "manifest.csv", index=False)
    features.to_csv(args.out_dir / "features.csv", index=False)
    coverage = label_coverage(features)
    coverage.to_csv(args.out_dir / "label_coverage.csv", index=False)
    if int(coverage["unlabelled"].sum()):
        print(
            f"WARNING: {int(coverage['unlabelled'].sum())} of {len(features)} candidates "
            f"could not be labelled with {label_metric}; see label_coverage.csv"
        )

    empty = pd.DataFrame()
    per_target = method_metrics = pairwise = source_shift = ties = versus_random = curve = power = empty
    if bool(features["has_native"].any()):
        per_target = evaluate_per_target(features, top_k=args.top_k)
        method_metrics = summarize_methods(per_target)
        pairwise = pairwise_ranking_accuracy(features)
        source_shift = source_shift_summary(features, top_k=args.top_k)
        ties = tie_diagnostics(features)
        versus_random = pick_diagnostics(features, top_k=args.top_k)
        curve = retrieval_curve(features)
        per_target.to_csv(args.out_dir / "per_target_metrics.csv", index=False)
        method_metrics.to_csv(args.out_dir / "method_metrics.csv", index=False)
        pairwise.to_csv(args.out_dir / "pairwise_accuracy.csv", index=False)
        source_shift.to_csv(args.out_dir / "source_shift_summary.csv", index=False)
        ties.to_csv(args.out_dir / "score_ties.csv", index=False)
        versus_random.to_csv(args.out_dir / "pick_diagnostics.csv", index=False)
        curve.to_csv(args.out_dir / "retrieval_curve.csv", index=False)
        spec = BenchmarkSpec(name=dataset_name, kind=args.benchmark_kind)
        contract_candidates = build_candidate_table(features, spec, top_k=args.top_k)
        contract_summary = build_summary_table(
            features, spec, contract_candidates, versus_random, pairwise, top_k=args.top_k
        )
        contract_candidates.to_csv(args.out_dir / "contract_candidates.csv", index=False)
        contract_summary.to_csv(args.out_dir / "contract_summary.csv", index=False)
        power = power_table(
            baseline=float(versus_random.loc[versus_random["method"] == "random", "hit@5"].iloc[0])
            if "hit@5" in versus_random.columns
            else 0.2,
            comparisons=max(1, int(len(curve))),
        )
        power["n_targets_available"] = contract_summary["n_targets"].iloc[0]
        power.to_csv(args.out_dir / "power_table.csv", index=False)

    report = render_ensemble_report(
        dataset_name=dataset_name,
        candidates_root=args.candidates_root,
        features=features,
        per_target=per_target,
        method_metrics=method_metrics,
        pairwise=pairwise,
        source_shift=source_shift,
        top_k=args.top_k,
        label_metric=label_metric,
        coverage=coverage,
        ties=ties,
        versus_random=versus_random,
        curve=curve,
        power=power,
    )
    (args.out_dir / "summary.md").write_text(report, encoding="utf-8")
    print(f"Wrote ensemble evaluation artifacts to {args.out_dir}")


if __name__ == "__main__":
    main()
