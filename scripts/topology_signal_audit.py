#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import source_invariant_reranker as sir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit whether topology features add stable source-invariant RNA ranking signal."
    )
    parser.add_argument("--geometry-per-target", type=Path, required=True)
    parser.add_argument("--topology-features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--bootstrap-repeats", type=int, default=2000)
    parser.add_argument("--shuffle-repeats", type=int, default=50)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--pairwise-pairs-per-target", type=int, default=1500)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    topology_features = sir.add_group_columns(pd.read_csv(args.topology_features))
    topology_features = topology_features.dropna(subset=["true_tm_like", "true_rmsd"]).copy()
    feature_groups = build_feature_groups(topology_features)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    ablation_frames = []
    per_target_frames = []
    for group_name, columns in feature_groups.items():
        per_target = run_reranker(topology_features, columns, top_k=args.top_k, rng=rng, max_pairs=args.pairwise_pairs_per_target)
        per_target["feature_group"] = group_name
        metrics = sir.summarize(per_target, top_k=args.top_k)
        metrics["feature_group"] = group_name
        per_target_frames.append(per_target)
        ablation_frames.append(metrics)

    ablation = pd.concat(ablation_frames, ignore_index=True)
    ablation_per_target = pd.concat(per_target_frames, ignore_index=True)

    geometry_per_target = pd.read_csv(args.geometry_per_target)
    bootstrap = bootstrap_comparisons(
        geometry_per_target=geometry_per_target,
        topology_per_target=ablation_per_target,
        repeats=args.bootstrap_repeats,
        rng=rng,
        top_k=args.top_k,
    )
    ts232 = bootstrap_ts232(topology_per_target=ablation_per_target, repeats=args.bootstrap_repeats, rng=rng, top_k=args.top_k)
    shuffled = shuffled_topology_control(
        features=topology_features,
        feature_columns=feature_groups["geometry_plus_topology"],
        topology_columns=feature_groups["topology_only"] + feature_groups.get("target_z_topology_only", []),
        repeats=args.shuffle_repeats,
        top_k=args.top_k,
        rng=rng,
        max_pairs=args.pairwise_pairs_per_target,
    )
    feature_summary = feature_group_summary(feature_groups)

    ablation.to_csv(args.out_dir / "feature_group_ablation.csv", index=False)
    ablation_per_target.to_csv(args.out_dir / "feature_group_ablation_per_target.csv", index=False)
    bootstrap.to_csv(args.out_dir / "topology_vs_geometry_bootstrap.csv", index=False)
    ts232.to_csv(args.out_dir / "ts232_stability.csv", index=False)
    shuffled.to_csv(args.out_dir / "shuffled_topology_control.csv", index=False)
    feature_summary.to_csv(args.out_dir / "feature_groups.csv", index=False)
    (args.out_dir / "topology_signal_audit.md").write_text(
        render_report(ablation, bootstrap, ts232, shuffled, feature_summary, top_k=args.top_k),
        encoding="utf-8",
    )
    print(f"Wrote topology signal audit to {args.out_dir}")


def build_feature_groups(frame: pd.DataFrame) -> dict[str, list[str]]:
    base = [column for column in sir.STRUCTURAL_FEATURES if column in frame.columns]
    numeric = sir.infer_feature_columns(frame)
    topology = [
        column
        for column in numeric
        if column not in base and not column.startswith("target_z_")
    ]
    target_z = [column for column in numeric if column.startswith("target_z_")]
    contact_topology = [
        column
        for column in topology
        if any(
            key in column
            for key in [
                "contact",
                "degree",
                "component",
                "community",
                "modular",
                "modularity",
                "junction",
                "loop",
                "hub",
                "bridge",
                "order",
                "span",
                "fraction",
            ]
        )
    ]
    distance_shape = [
        column
        for column in topology
        if any(key in column for key in ["distance_p", "local_step", "turn_angle", "helix_like"])
    ]
    groups = {
        "geometry": base,
        "topology_only": topology,
        "contact_topology_only": contact_topology,
        "distance_shape_only": distance_shape,
        "target_z_topology_only": target_z,
        "geometry_plus_topology": numeric,
    }
    return {name: columns for name, columns in groups.items() if columns}


def run_reranker(
    features: pd.DataFrame,
    feature_columns: list[str],
    top_k: int,
    rng: np.random.Generator,
    max_pairs: int,
) -> pd.DataFrame:
    rows = []
    for split in sir.make_leave_oracle_group_out_splits(features):
        scored, _ = sir.score_split(split, feature_columns=feature_columns, rng=rng, max_pairs_per_target=max_pairs)
        rows.append(sir.evaluate_split(scored, top_k=top_k))
    return pd.concat(rows, ignore_index=True)


def bootstrap_comparisons(
    geometry_per_target: pd.DataFrame,
    topology_per_target: pd.DataFrame,
    repeats: int,
    rng: np.random.Generator,
    top_k: int,
) -> pd.DataFrame:
    comparisons = [
        {
            "comparison": "geometry_ensemble_vs_contact_topology_gbr",
            "left_frame": geometry_per_target,
            "left_group": None,
            "left_method": "invariant_ensemble",
            "right_frame": topology_per_target,
            "right_group": "contact_topology_only",
            "right_method": "invariant_gbr",
        },
        {
            "comparison": "geometry_gbr_vs_contact_topology_gbr",
            "left_frame": geometry_per_target,
            "left_group": None,
            "left_method": "invariant_gbr",
            "right_frame": topology_per_target,
            "right_group": "contact_topology_only",
            "right_method": "invariant_gbr",
        },
        {
            "comparison": "low_clash_vs_contact_topology_gbr",
            "left_frame": geometry_per_target,
            "left_group": None,
            "left_method": "low_clash",
            "right_frame": topology_per_target,
            "right_group": "contact_topology_only",
            "right_method": "invariant_gbr",
        },
        {
            "comparison": "geometry_ensemble_vs_all_topology_ensemble",
            "left_frame": geometry_per_target,
            "left_group": None,
            "left_method": "invariant_ensemble",
            "right_frame": topology_per_target,
            "right_group": "geometry_plus_topology",
            "right_method": "invariant_ensemble",
        },
    ]
    rows = []
    for comparison in comparisons:
        rows.extend(
            bootstrap_pair(
                comparison=comparison["comparison"],
                left_frame=comparison["left_frame"],
                right_frame=comparison["right_frame"],
                left_group=comparison["left_group"],
                right_group=comparison["right_group"],
                left_method=comparison["left_method"],
                right_method=comparison["right_method"],
                repeats=repeats,
                rng=rng,
                top_k=top_k,
            )
        )
    return pd.DataFrame(rows)


def bootstrap_pair(
    comparison: str,
    left_frame: pd.DataFrame,
    right_frame: pd.DataFrame,
    left_group: str | None,
    right_group: str | None,
    left_method: str,
    right_method: str,
    repeats: int,
    rng: np.random.Generator,
    top_k: int,
) -> list[dict[str, object]]:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    left = left_frame[left_frame["method"] == left_method].copy()
    if left_group is not None and "feature_group" in left.columns:
        left = left[left["feature_group"] == left_group]
    right = right_frame[right_frame["method"] == right_method].copy()
    if right_group is not None and "feature_group" in right.columns:
        right = right[right["feature_group"] == right_group]
    merged = left[["target_id", best_col, hit_col]].merge(
        right[["target_id", best_col, hit_col]],
        on="target_id",
        suffixes=("_left", "_right"),
    )
    targets = merged["target_id"].to_numpy()
    if len(targets) == 0:
        return []
    bootstrap_rows = []
    for repeat in range(repeats):
        sample_idx = rng.integers(0, len(targets), size=len(targets))
        sample = merged.iloc[sample_idx]
        bootstrap_rows.append(
            {
                "repeat": repeat,
                "left_mean_best_of_k": sample[f"{best_col}_left"].mean(),
                "right_mean_best_of_k": sample[f"{best_col}_right"].mean(),
                "delta_mean_best_of_k": sample[f"{best_col}_right"].mean() - sample[f"{best_col}_left"].mean(),
                "left_oracle_hit_rate": sample[f"{hit_col}_left"].mean(),
                "right_oracle_hit_rate": sample[f"{hit_col}_right"].mean(),
                "delta_oracle_hit_rate": sample[f"{hit_col}_right"].mean() - sample[f"{hit_col}_left"].mean(),
            }
        )
    frame = pd.DataFrame(bootstrap_rows)
    summary_rows = []
    for metric in [
        "left_mean_best_of_k",
        "right_mean_best_of_k",
        "delta_mean_best_of_k",
        "left_oracle_hit_rate",
        "right_oracle_hit_rate",
        "delta_oracle_hit_rate",
    ]:
        values = frame[metric].to_numpy(dtype=float)
        summary_rows.append(
            {
                "comparison": comparison,
                "left": f"{left_group or 'geometry_table'}:{left_method}",
                "right": f"{right_group or 'topology_table'}:{right_method}",
                "metric": metric,
                "mean": float(values.mean()),
                "ci_low": float(np.percentile(values, 2.5)),
                "ci_high": float(np.percentile(values, 97.5)),
            }
        )
    return summary_rows


def bootstrap_ts232(topology_per_target: pd.DataFrame, repeats: int, rng: np.random.Generator, top_k: int) -> pd.DataFrame:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    subset = topology_per_target[
        (topology_per_target["heldout_oracle_group"] == "TS232")
        & (topology_per_target["feature_group"] == "geometry_plus_topology")
        & (topology_per_target["method"].isin(["invariant_rf", "invariant_ensemble", "low_clash"]))
    ].copy()
    rows = []
    for method, group in subset.groupby("method"):
        targets = group["target_id"].unique()
        if len(targets) == 0:
            continue
        target_frame = group.set_index("target_id")
        sampled_hits = []
        sampled_scores = []
        for _ in range(repeats):
            sample_targets = rng.choice(targets, size=len(targets), replace=True)
            sample = target_frame.loc[sample_targets]
            sampled_hits.append(float(sample[hit_col].mean()))
            sampled_scores.append(float(sample[best_col].mean()))
        rows.append(
            {
                "method": method,
                "targets": len(targets),
                "oracle_hit_rate": float(group[hit_col].mean()),
                "oracle_hit_rate_ci_low": float(np.percentile(sampled_hits, 2.5)),
                "oracle_hit_rate_ci_high": float(np.percentile(sampled_hits, 97.5)),
                "mean_best_of_k_tm_like": float(group[best_col].mean()),
                "mean_best_of_k_ci_low": float(np.percentile(sampled_scores, 2.5)),
                "mean_best_of_k_ci_high": float(np.percentile(sampled_scores, 97.5)),
            }
        )
    return pd.DataFrame(rows).sort_values(["oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=False)


def shuffled_topology_control(
    features: pd.DataFrame,
    feature_columns: list[str],
    topology_columns: list[str],
    repeats: int,
    top_k: int,
    rng: np.random.Generator,
    max_pairs: int,
) -> pd.DataFrame:
    rows = []
    for repeat in range(repeats):
        shuffled = shuffle_columns_within_target(features, topology_columns, rng)
        per_target = run_reranker(shuffled, feature_columns, top_k=top_k, rng=rng, max_pairs=max_pairs)
        metrics = sir.summarize(per_target, top_k=top_k)
        metrics["repeat"] = repeat
        rows.append(metrics)
    all_metrics = pd.concat(rows, ignore_index=True)
    return (
        all_metrics.groupby("method")
        .agg(
            repeats=("repeat", "nunique"),
            mean_best_of_k_tm_like_mean=("mean_best_of_k_tm_like", "mean"),
            mean_best_of_k_tm_like_std=("mean_best_of_k_tm_like", "std"),
            oracle_hit_rate_mean=("oracle_hit_rate", "mean"),
            oracle_hit_rate_std=("oracle_hit_rate", "std"),
            oracle_hit_rate_max=("oracle_hit_rate", "max"),
        )
        .reset_index()
        .sort_values(["oracle_hit_rate_mean", "mean_best_of_k_tm_like_mean"], ascending=False)
    )


def shuffle_columns_within_target(frame: pd.DataFrame, columns: list[str], rng: np.random.Generator) -> pd.DataFrame:
    shuffled = frame.copy()
    for _, idx in shuffled.groupby("target_id").groups.items():
        idx = list(idx)
        for column in columns:
            values = shuffled.loc[idx, column].to_numpy(copy=True)
            rng.shuffle(values)
            shuffled.loc[idx, column] = values
    return shuffled


def feature_group_summary(groups: dict[str, list[str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"feature_group": name, "num_features": len(columns), "features": ",".join(columns)} for name, columns in groups.items()]
    )


def render_report(
    ablation: pd.DataFrame,
    bootstrap: pd.DataFrame,
    ts232: pd.DataFrame,
    shuffled: pd.DataFrame,
    feature_summary: pd.DataFrame,
    top_k: int,
) -> str:
    lines = []
    lines.append("# Topology Signal Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit tests whether topology features add stable source-invariant signal, rather than one lucky hit."
    )
    lines.append("")
    lines.append("## Feature Groups")
    lines.append("")
    lines.append(feature_summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Feature Group Ablation")
    lines.append("")
    display = ablation[["feature_group", "method", "targets", "mean_best_of_k_tm_like", "mean_tm_like_regret", "oracle_hit_rate"]]
    lines.append(display.sort_values(["oracle_hit_rate", "mean_best_of_k_tm_like"], ascending=False).to_markdown(index=False))
    lines.append("")
    lines.append("## Geometry vs Topology Bootstrap")
    lines.append("")
    lines.append(bootstrap.to_markdown(index=False))
    lines.append("")
    lines.append("## TS232 Stability")
    lines.append("")
    lines.append(ts232.to_markdown(index=False))
    lines.append("")
    lines.append("## Shuffled Topology Control")
    lines.append("")
    lines.append(shuffled.to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        f"If topology is real signal, geometry_plus_topology should improve mean best-of-{top_k} over geometry, "
        "and shuffled topology should reduce that improvement. If confidence intervals include zero, the result is directional but not stable yet."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
