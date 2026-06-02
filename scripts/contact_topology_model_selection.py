#!/usr/bin/env python
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

import source_invariant_reranker as sir
import topology_signal_audit as tsa


@dataclass(frozen=True)
class GbdtParams:
    n_estimators: int
    max_depth: int
    learning_rate: float
    min_samples_leaf: int

    @property
    def label(self) -> str:
        return (
            f"ne{self.n_estimators}_d{self.max_depth}_"
            f"lr{self.learning_rate:g}_leaf{self.min_samples_leaf}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Nested leave-oracle-group-out model selection for the contact-topology source-invariant reranker. "
            "Hyperparameters are selected using only training targets, then evaluated on unseen oracle-source targets."
        )
    )
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=31)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    features = sir.add_group_columns(pd.read_csv(args.features))
    features = features.dropna(subset=["true_tm_like", "true_rmsd"]).copy()
    feature_groups = tsa.build_feature_groups(features)
    feature_columns = feature_groups.get("contact_topology_only")
    if not feature_columns:
        raise SystemExit("No contact_topology_only feature group could be inferred")

    params_grid = build_param_grid()
    predictions = []
    per_target_rows = []
    grid_rows = []
    selected_rows = []
    importance_rows = []

    for split in sir.make_leave_oracle_group_out_splits(features):
        split_grid = score_grid_on_training_targets(
            split=split,
            feature_columns=feature_columns,
            params_grid=params_grid,
            top_k=args.top_k,
            rng=rng,
        )
        grid_rows.extend(split_grid)
        best_params = select_best_params(split_grid)
        selected_rows.append(
            {
                "heldout_oracle_group": split.heldout_group,
                "selected_params": best_params.label,
                **best_params.__dict__,
            }
        )
        scored, importance = score_heldout_split(
            split=split,
            feature_columns=feature_columns,
            params=best_params,
        )
        predictions.append(scored)
        importance_rows.extend(importance)
        per_target_rows.append(evaluate_contact_topology(scored, top_k=args.top_k))

    predictions_frame = pd.concat(predictions, ignore_index=True)
    per_target = pd.concat(per_target_rows, ignore_index=True)
    metrics = sir.summarize(per_target, top_k=args.top_k)
    group_metrics = sir.summarize_by_group(per_target, top_k=args.top_k)
    grid = pd.DataFrame(grid_rows)
    selected = pd.DataFrame(selected_rows)
    feature_importance = pd.DataFrame(importance_rows)
    stability = bootstrap_method_deltas(per_target, top_k=args.top_k, repeats=2000, rng=rng)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame.to_csv(args.out_dir / "contact_topology_predictions.csv", index=False)
    per_target.to_csv(args.out_dir / "contact_topology_per_target.csv", index=False)
    metrics.to_csv(args.out_dir / "contact_topology_metrics.csv", index=False)
    group_metrics.to_csv(args.out_dir / "contact_topology_by_group_metrics.csv", index=False)
    grid.to_csv(args.out_dir / "contact_topology_grid_metrics.csv", index=False)
    selected.to_csv(args.out_dir / "contact_topology_selected_params.csv", index=False)
    feature_importance.to_csv(args.out_dir / "contact_topology_feature_importance.csv", index=False)
    stability.to_csv(args.out_dir / "contact_topology_bootstrap_deltas.csv", index=False)
    (args.out_dir / "contact_topology_model_selection_report.md").write_text(
        render_report(
            feature_columns=feature_columns,
            metrics=metrics,
            group_metrics=group_metrics,
            selected=selected,
            grid=grid,
            per_target=per_target,
            feature_importance=feature_importance,
            stability=stability,
            top_k=args.top_k,
        ),
        encoding="utf-8",
    )
    print(f"Wrote contact-topology model selection to {args.out_dir}")


def build_param_grid() -> list[GbdtParams]:
    return [
        GbdtParams(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate, min_samples_leaf=leaf)
        for n_estimators in [80, 160, 240]
        for max_depth in [1, 2]
        for learning_rate in [0.03, 0.05]
        for leaf in [1, 4]
    ]


def score_grid_on_training_targets(
    split: sir.Split,
    feature_columns: list[str],
    params_grid: list[GbdtParams],
    top_k: int,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    train_targets = sorted(split.train["target_id"].unique())
    rows = []
    if len(train_targets) < 2:
        return [
            {
                "heldout_oracle_group": split.heldout_group,
                "params": params.label,
                **params.__dict__,
                "inner_targets": len(train_targets),
                "inner_mean_best_of_k_tm_like": np.nan,
                "inner_mean_tm_like_regret": np.nan,
                "inner_oracle_hit_rate": np.nan,
            }
            for params in params_grid
        ]

    for params in params_grid:
        inner_rows = []
        for validation_target in train_targets:
            inner_train = split.train[split.train["target_id"] != validation_target].copy()
            inner_test = split.train[split.train["target_id"] == validation_target].copy()
            if inner_train.empty or inner_test.empty:
                continue
            scored, _ = fit_predict_gbdt(
                train=inner_train,
                test=inner_test,
                feature_columns=feature_columns,
                params=params,
                random_state=int(rng.integers(0, 1_000_000)),
            )
            inner_rows.append(evaluate_contact_topology(scored, top_k=top_k))
        if inner_rows:
            inner_per_target = pd.concat(inner_rows, ignore_index=True)
            selected_metrics = sir.summarize(inner_per_target, top_k=top_k)
            tuned = selected_metrics[selected_metrics["method"] == "contact_topology_tuned"]
            if tuned.empty:
                metric_row = {
                    "inner_targets": len(inner_per_target["target_id"].unique()),
                    "inner_mean_best_of_k_tm_like": np.nan,
                    "inner_mean_tm_like_regret": np.nan,
                    "inner_oracle_hit_rate": np.nan,
                }
            else:
                record = tuned.iloc[0]
                metric_row = {
                    "inner_targets": int(record.targets),
                    "inner_mean_best_of_k_tm_like": float(record.mean_best_of_k_tm_like),
                    "inner_mean_tm_like_regret": float(record.mean_tm_like_regret),
                    "inner_oracle_hit_rate": float(record.oracle_hit_rate),
                }
        else:
            metric_row = {
                "inner_targets": 0,
                "inner_mean_best_of_k_tm_like": np.nan,
                "inner_mean_tm_like_regret": np.nan,
                "inner_oracle_hit_rate": np.nan,
            }
        rows.append(
            {
                "heldout_oracle_group": split.heldout_group,
                "params": params.label,
                **params.__dict__,
                **metric_row,
            }
        )
    return rows


def select_best_params(grid_rows: list[dict[str, object]]) -> GbdtParams:
    grid = pd.DataFrame(grid_rows).copy()
    grid = grid.sort_values(
        ["inner_oracle_hit_rate", "inner_mean_best_of_k_tm_like", "inner_mean_tm_like_regret"],
        ascending=[False, False, True],
        na_position="last",
    )
    row = grid.iloc[0]
    return GbdtParams(
        n_estimators=int(row.n_estimators),
        max_depth=int(row.max_depth),
        learning_rate=float(row.learning_rate),
        min_samples_leaf=int(row.min_samples_leaf),
    )


def score_heldout_split(
    split: sir.Split,
    feature_columns: list[str],
    params: GbdtParams,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    scored, importances = fit_predict_gbdt(
        train=split.train,
        test=split.test,
        feature_columns=feature_columns,
        params=params,
        random_state=41,
    )
    scored.attrs["heldout_oracle_group"] = split.heldout_group
    importance_rows = [
        {
            "heldout_oracle_group": split.heldout_group,
            "params": params.label,
            "feature": feature,
            "importance": importance,
        }
        for feature, importance in importances
    ]
    return scored, importance_rows


def fit_predict_gbdt(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    params: GbdtParams,
    random_state: int,
) -> tuple[pd.DataFrame, list[tuple[str, float]]]:
    scored = test.copy()
    x_train = sir.clean_features(train, feature_columns)
    y_train = train["true_tm_like"].astype(float).to_numpy()
    x_test = sir.clean_features(scored, feature_columns)
    weights = sir.balanced_weights(train)
    model = GradientBoostingRegressor(
        random_state=random_state,
        n_estimators=params.n_estimators,
        max_depth=params.max_depth,
        learning_rate=params.learning_rate,
        min_samples_leaf=params.min_samples_leaf,
    )
    model.fit(x_train, y_train, sample_weight=weights)
    scored["score_contact_topology_tuned"] = model.predict(x_test)
    importances = [(feature, float(value)) for feature, value in zip(feature_columns, model.feature_importances_)]
    return scored, importances


def evaluate_contact_topology(scored: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows = []
    methods = {
        "contact_topology_tuned": "score_contact_topology_tuned",
        "low_clash": "score_low_clash",
        "contact": "score_contact",
        "compact": "score_compact",
        "hybrid": "score_hybrid",
    }
    for target_id, group in scored.groupby("target_id"):
        oracle = sir.get_oracle(group)
        for method, score_column in methods.items():
            if score_column not in group:
                continue
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            selected_best = selected.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
            selected_top1 = selected.iloc[0]
            rows.append(
                {
                    "heldout_oracle_group": scored.attrs.get("heldout_oracle_group", oracle.casp_group),
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
    return pd.DataFrame(rows)


def bootstrap_method_deltas(per_target: pd.DataFrame, top_k: int, repeats: int, rng: np.random.Generator) -> pd.DataFrame:
    comparisons = [
        ("low_clash", "contact_topology_tuned"),
        ("contact", "contact_topology_tuned"),
        ("hybrid", "contact_topology_tuned"),
    ]
    best_col = f"best_of_{top_k}_tm_like"
    hit_col = f"oracle_in_top{top_k}"
    rows = []
    for left_method, right_method in comparisons:
        left = per_target[per_target["method"] == left_method][["target_id", best_col, hit_col]]
        right = per_target[per_target["method"] == right_method][["target_id", best_col, hit_col]]
        merged = left.merge(right, on="target_id", suffixes=("_left", "_right"))
        if merged.empty:
            continue
        samples = []
        for _ in range(repeats):
            sample = merged.iloc[rng.integers(0, len(merged), size=len(merged))]
            samples.append(
                {
                    "delta_mean_best_of_k": sample[f"{best_col}_right"].mean() - sample[f"{best_col}_left"].mean(),
                    "delta_oracle_hit_rate": sample[f"{hit_col}_right"].mean() - sample[f"{hit_col}_left"].mean(),
                }
            )
        sample_frame = pd.DataFrame(samples)
        for metric in ["delta_mean_best_of_k", "delta_oracle_hit_rate"]:
            values = sample_frame[metric].to_numpy(dtype=float)
            rows.append(
                {
                    "comparison": f"{left_method}_vs_{right_method}",
                    "metric": metric,
                    "mean": float(values.mean()),
                    "ci_low": float(np.percentile(values, 2.5)),
                    "ci_high": float(np.percentile(values, 97.5)),
                }
            )
    return pd.DataFrame(rows)


def render_report(
    feature_columns: list[str],
    metrics: pd.DataFrame,
    group_metrics: pd.DataFrame,
    selected: pd.DataFrame,
    grid: pd.DataFrame,
    per_target: pd.DataFrame,
    feature_importance: pd.DataFrame,
    stability: pd.DataFrame,
    top_k: int,
) -> str:
    lines: list[str] = []
    lines.append("# Contact-Topology Model Selection")
    lines.append("")
    lines.append("## Protocol")
    lines.append("")
    lines.append(
        "This run focuses only on contact-network topology features. For each leave-oracle-group-out split, "
        "GBDT hyperparameters are selected by leave-target-out validation inside the training targets only. "
        "The held-out oracle group is not used for model selection."
    )
    lines.append("")
    lines.append("## Feature Set")
    lines.append("")
    lines.append(pd.DataFrame({"feature": feature_columns}).to_markdown(index=False))
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append(metrics.to_markdown(index=False))
    lines.append("")
    lines.append("## Selected Parameters by Held-Out Oracle Group")
    lines.append("")
    lines.append(selected.to_markdown(index=False))
    lines.append("")
    lines.append("## Metrics by Held-Out Oracle Group")
    lines.append("")
    lines.append(group_metrics.to_markdown(index=False))
    lines.append("")
    lines.append("## Bootstrap Deltas")
    lines.append("")
    lines.append(stability.to_markdown(index=False))
    lines.append("")
    lines.append(f"## Per-Target Top-{top_k}")
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
    ].sort_values(["target_id", "method"])
    lines.append(display.to_markdown(index=False))
    lines.append("")
    lines.append("## Top Feature Importances")
    lines.append("")
    if feature_importance.empty:
        lines.append("_No importances available._")
    else:
        importance = (
            feature_importance.groupby("feature")
            .agg(mean_importance=("importance", "mean"), max_importance=("importance", "max"))
            .reset_index()
            .sort_values("mean_importance", ascending=False)
            .head(20)
        )
        lines.append(importance.to_markdown(index=False))
    lines.append("")
    lines.append("## Inner Grid Search Summary")
    lines.append("")
    grid_display = grid.sort_values(
        ["heldout_oracle_group", "inner_oracle_hit_rate", "inner_mean_best_of_k_tm_like"],
        ascending=[True, False, False],
    ).groupby("heldout_oracle_group").head(5)
    lines.append(grid_display.to_markdown(index=False))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "A gain over low_clash in mean best-of-k supports transferable contact-topology signal. "
        "A wide oracle-hit confidence interval means retrieval is still not stable enough for a strong scientific claim."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
