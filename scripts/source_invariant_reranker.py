#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


GROUP_RE = re.compile(r"(TS\d+)")

STRUCTURAL_FEATURES = [
    "num_residues",
    "radius_of_gyration",
    "end_to_end_distance",
    "contact_density",
    "long_range_contact_density",
    "clashes_per_residue",
    "backbone_break_fraction",
    "compactness",
    "score_contact",
    "score_low_clash",
    "score_compact",
    "score_hybrid",
]
EXCLUDED_NUMERIC_FEATURES = {
    "true_rmsd",
    "true_tm_like",
    "contact_map_precision",
    "contact_map_recall",
    "contact_map_f1",
    "multi_metric_quality",
    "aligned_residue_count",
}

BASELINE_SCORES = {
    "hybrid": "score_hybrid",
    "compact": "score_compact",
    "low_clash": "score_low_clash",
    "contact": "score_contact",
}


@dataclass
class Split:
    heldout_group: str
    train: pd.DataFrame
    test: pd.DataFrame


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Train source-invariant RNA candidate rerankers without explicit source/group IDs and evaluate them "
            "on leave-oracle-group-out CASP splits."
        )
    )
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--pairwise-pairs-per-target", type=int, default=2500)
    parser.add_argument(
        "--auto-features",
        action="store_true",
        help="Use all non-label numeric feature columns instead of the default compact structural feature list.",
    )
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    features = pd.read_csv(args.features)
    features = add_group_columns(features)
    labeled = features.dropna(subset=["true_tm_like", "true_rmsd"]).copy()
    if labeled.empty:
        raise SystemExit("No native labels found")
    feature_columns = infer_feature_columns(labeled) if args.auto_features else STRUCTURAL_FEATURES
    missing = [column for column in feature_columns if column not in labeled.columns]
    if missing:
        raise SystemExit(f"Missing structural feature columns: {missing}")

    predictions = []
    importance_rows = []
    per_target_rows = []
    for split in make_leave_oracle_group_out_splits(labeled):
        split_predictions, split_importance = score_split(
            split,
            feature_columns=feature_columns,
            rng=rng,
            max_pairs_per_target=args.pairwise_pairs_per_target,
        )
        predictions.append(split_predictions)
        importance_rows.extend(split_importance)
        per_target_rows.append(evaluate_split(split_predictions, top_k=args.top_k))

    predictions_frame = pd.concat(predictions, ignore_index=True)
    per_target = pd.concat(per_target_rows, ignore_index=True)
    metrics = summarize(per_target, top_k=args.top_k)
    group_metrics = summarize_by_group(per_target, top_k=args.top_k)
    feature_importance = pd.DataFrame(importance_rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame.to_csv(args.out_dir / "source_invariant_predictions.csv", index=False)
    per_target.to_csv(args.out_dir / "source_invariant_per_target.csv", index=False)
    metrics.to_csv(args.out_dir / "source_invariant_metrics.csv", index=False)
    group_metrics.to_csv(args.out_dir / "source_invariant_by_group_metrics.csv", index=False)
    feature_importance.to_csv(args.out_dir / "source_invariant_feature_importance.csv", index=False)
    (args.out_dir / "source_invariant_report.md").write_text(
        render_report(metrics, group_metrics, per_target, feature_importance, top_k=args.top_k),
        encoding="utf-8",
    )
    print(f"Wrote source-invariant reranker evaluation to {args.out_dir}")


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["casp_group"] = frame["candidate_id"].map(extract_group)
    return frame


def extract_group(candidate_id: str) -> str:
    match = GROUP_RE.search(str(candidate_id))
    return match.group(1) if match else "unknown"


def make_leave_oracle_group_out_splits(features: pd.DataFrame) -> list[Split]:
    oracle_table = []
    for target_id, group in features.groupby("target_id"):
        oracle = get_oracle(group)
        oracle_table.append({"target_id": target_id, "oracle_group": oracle.casp_group})
    oracle_frame = pd.DataFrame(oracle_table)

    splits = []
    for heldout_group in sorted(oracle_frame["oracle_group"].unique()):
        heldout_targets = set(oracle_frame.loc[oracle_frame["oracle_group"] == heldout_group, "target_id"])
        train = features[~features["target_id"].isin(heldout_targets)].copy()
        # This enforces the unseen-source condition: no candidate from the held-out oracle group is visible in training.
        train = train[train["casp_group"] != heldout_group].copy()
        test = features[features["target_id"].isin(heldout_targets)].copy()
        splits.append(Split(heldout_group=heldout_group, train=train, test=test))
    return splits


def get_oracle(group: pd.DataFrame) -> pd.Series:
    return group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]


def infer_feature_columns(frame: pd.DataFrame) -> list[str]:
    numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
    return [
        column
        for column in numeric_columns
        if column not in EXCLUDED_NUMERIC_FEATURES
    ]


def score_split(
    split: Split,
    feature_columns: list[str],
    rng: np.random.Generator,
    max_pairs_per_target: int,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    scored = split.test.copy()
    scored.attrs["heldout_oracle_group"] = split.heldout_group
    train = split.train.copy()
    if train.empty:
        for name in model_score_names():
            scored[name] = 0.0
        return scored, []

    x_train = clean_features(train, feature_columns)
    y_train = train["true_tm_like"].astype(float).to_numpy()
    x_test = clean_features(scored, feature_columns)
    weights = balanced_weights(train)

    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=None))
    ridge.fit(x_train, y_train, ridge__sample_weight=weights)
    scored["score_invariant_ridge"] = ridge.predict(x_test)

    gbr = GradientBoostingRegressor(random_state=13, n_estimators=160, max_depth=2, learning_rate=0.04)
    gbr.fit(x_train, y_train, sample_weight=weights)
    scored["score_invariant_gbr"] = gbr.predict(x_test)

    rf = RandomForestRegressor(
        random_state=17,
        n_estimators=220,
        max_depth=5,
        min_samples_leaf=3,
        n_jobs=-1,
    )
    rf.fit(x_train, y_train, sample_weight=weights)
    scored["score_invariant_rf"] = rf.predict(x_test)

    pairwise_model = fit_pairwise_ranker(train, feature_columns, rng=rng, max_pairs_per_target=max_pairs_per_target)
    scored["score_invariant_pairwise"] = score_pairwise(scored, pairwise_model, feature_columns)

    # Combine source-invariant learned structure signal with conservative sanity filters.
    scored["score_invariant_ensemble"] = (
        0.40 * normalize_within(scored["score_invariant_gbr"])
        + 0.25 * normalize_within(scored["score_invariant_rf"])
        + 0.25 * normalize_within(scored["score_invariant_pairwise"])
        + 0.10 * normalize_within(scored["score_low_clash"])
    )
    importance_rows = []
    for model_name, importances in [
        ("invariant_gbr", gbr.feature_importances_),
        ("invariant_rf", rf.feature_importances_),
    ]:
        for feature, importance in zip(feature_columns, importances):
            importance_rows.append(
                {
                    "heldout_oracle_group": split.heldout_group,
                    "model": model_name,
                    "feature": feature,
                    "importance": float(importance),
                }
            )
    return scored, importance_rows


def model_score_names() -> list[str]:
    return [
        "score_invariant_ridge",
        "score_invariant_gbr",
        "score_invariant_rf",
        "score_invariant_pairwise",
        "score_invariant_ensemble",
    ]


def clean_features(frame: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    values = frame[feature_columns].replace([np.inf, -np.inf], np.nan)
    values = values.fillna(values.median(numeric_only=True)).fillna(0.0)
    return values.to_numpy(dtype=float)


def balanced_weights(train: pd.DataFrame) -> np.ndarray:
    target_counts = train["target_id"].map(train["target_id"].value_counts()).astype(float)
    group_counts = train["casp_group"].map(train["casp_group"].value_counts()).astype(float)
    weights = 1.0 / np.sqrt(target_counts * group_counts)
    weights = weights / float(weights.mean())
    return weights.to_numpy(dtype=float)


def fit_pairwise_ranker(train: pd.DataFrame, feature_columns: list[str], rng: np.random.Generator, max_pairs_per_target: int):
    x_rows = []
    y_rows = []
    for _, group in train.groupby("target_id"):
        group = group.sort_values("candidate_id").reset_index(drop=True)
        if len(group) < 2:
            continue
        possible = [(i, j) for i in range(len(group)) for j in range(i + 1, len(group))]
        if len(possible) > max_pairs_per_target:
            selected_idx = rng.choice(len(possible), size=max_pairs_per_target, replace=False)
            pairs = [possible[int(idx)] for idx in selected_idx]
        else:
            pairs = possible
        features = clean_features(group, feature_columns)
        quality = group["true_tm_like"].to_numpy(dtype=float)
        for i, j in pairs:
            if quality[i] == quality[j]:
                continue
            if rng.random() < 0.5:
                a, b = i, j
            else:
                a, b = j, i
            x_rows.append(features[a] - features[b])
            y_rows.append(int(quality[a] > quality[b]))
    if not x_rows:
        return None
    x_pair = np.vstack(x_rows)
    y_pair = np.array(y_rows, dtype=int)
    if len(set(y_pair.tolist())) < 2:
        return None
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"),
    )
    model.fit(x_pair, y_pair)
    return model


def score_pairwise(test: pd.DataFrame, model, feature_columns: list[str]) -> pd.Series:
    if model is None:
        return pd.Series(np.zeros(len(test)), index=test.index)
    scores = pd.Series(np.zeros(len(test)), index=test.index, dtype=float)
    for target_id, group in test.groupby("target_id"):
        if len(group) < 2:
            continue
        features = clean_features(group, feature_columns)
        local_scores = np.zeros(len(group), dtype=float)
        for i in range(len(group)):
            diffs = features[i] - features
            probs = model.predict_proba(diffs)[:, 1]
            local_scores[i] = float(np.mean(probs))
        scores.loc[group.index] = local_scores
    return scores


def normalize_within(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - float(values.mean())) / std


def evaluate_split(scored: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows = []
    score_columns = {**BASELINE_SCORES, **{name.replace("score_", ""): name for name in model_score_names()}}
    for target_id, group in scored.groupby("target_id"):
        oracle = get_oracle(group)
        for method, score_column in score_columns.items():
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            selected_best = selected.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
            selected_top1 = selected.iloc[0]
            rows.append(
                {
                    "heldout_oracle_group": scored.attrs.get("heldout_oracle_group", ""),
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
                }
            )
    frame = pd.DataFrame(rows)
    if "heldout_oracle_group" not in frame or not frame["heldout_oracle_group"].any():
        # Recover from target oracle table; attrs are not preserved by concat-heavy paths.
        target_to_group = {
            target_id: get_oracle(group).casp_group for target_id, group in scored.groupby("target_id")
        }
        frame["heldout_oracle_group"] = frame["target_id"].map(target_to_group)
    return frame


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


def summarize_by_group(per_target: pd.DataFrame, top_k: int) -> pd.DataFrame:
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    return (
        per_target.groupby(["heldout_oracle_group", "method"])
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
    metrics: pd.DataFrame,
    group_metrics: pd.DataFrame,
    per_target: pd.DataFrame,
    feature_importance: pd.DataFrame,
    top_k: int,
) -> str:
    lines: list[str] = []
    lines.append("# Source-Invariant Reranker Evaluation")
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        "Models are trained without explicit CASP group/source ID. Evaluation uses leave-oracle-group-out splits: "
        "targets whose oracle comes from a held-out group are tested, and all candidates from that held-out group are removed from training."
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
    lines.append(f"## Per-Target Top-{top_k} Results")
    lines.append("")
    display = per_target[
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
        "If source-invariant learned models beat low-clash or recover nonzero oracle hits, structural features contain transferable signal. "
        "If they remain at zero oracle hit rate, the current handcrafted representation is still insufficient for unseen-source transfer."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
