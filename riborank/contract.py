"""The evaluation contract.

Every benchmark writes the same two tables, with the same columns, validated
before they are saved. This exists because renaming a column or swapping a
metric has already invalidated whole runs in this repository twice
(docs/CORRECTIONS.md), and a stored result that does not say which metric
produced it cannot be compared with anything later.

Two rules the schema enforces rather than documents:

* **Every record names its metric.** ``label_metric`` is per row, so a table
  can never be silently half official TM-score and half internal approximation.
* **Every record names its tie group.** A selection is only meaningful
  alongside how many candidates shared its score, so the number that a
  tie-break could have changed is never stored without that context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

#: Bump when a column is added, removed or redefined. Stored tables carry it,
#: so a reader can refuse a table it does not understand instead of guessing.
CONTRACT_VERSION = 1

#: Kind of benchmark. Mixing these in one summary hides exactly the effect that
#: `data/real` demonstrated: synthetic decoys tell a different story from real
#: prediction pools, and averaging them produces a number that describes
#: neither.
BENCHMARK_KINDS = ("prediction_pool", "experimental", "controlled_decoy")

CANDIDATE_COLUMNS: dict[str, str] = {
    "contract_version": "int64",
    "benchmark": "object",
    "benchmark_kind": "object",
    "target_id": "object",
    "candidate_id": "object",
    "method": "object",
    "label_metric": "object",
    "label": "float64",
    "rank": "int64",
    "selected": "bool",
    "tie_group_size": "int64",
    "labelled": "bool",
}

SUMMARY_COLUMNS: dict[str, str] = {
    "contract_version": "int64",
    "benchmark": "object",
    "benchmark_kind": "object",
    "method": "object",
    "label_metric": "object",
    "n_targets": "int64",
    "n_candidates": "int64",
    "label_coverage": "float64",
    "mean_selected_label": "float64",
    "mean_oracle_label": "float64",
    "selected_percentile": "float64",
    "pairwise_accuracy": "float64",
    "random_top1": "float64",
    "random_best_of_k": "float64",
    "mean_best_of_k": "float64",
    "best_of_k_low": "float64",
    "best_of_k_high": "float64",
    "verdict": "object",
}


class ContractError(ValueError):
    """A table does not satisfy the evaluation contract."""


@dataclass(slots=True)
class BenchmarkSpec:
    """Identity of a benchmark, carried into every row it produces."""

    name: str
    kind: str
    description: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ContractError("benchmark name must not be empty")
        if self.kind not in BENCHMARK_KINDS:
            raise ContractError(
                f"unknown benchmark kind {self.kind!r}; expected one of {BENCHMARK_KINDS}"
            )


def _check_columns(frame: pd.DataFrame, expected: dict[str, str], what: str) -> None:
    missing = [name for name in expected if name not in frame.columns]
    if missing:
        raise ContractError(f"{what} is missing required columns: {missing}")
    extra = [name for name in frame.columns if name not in expected]
    if extra:
        raise ContractError(
            f"{what} has columns outside the contract: {extra}. "
            "Add them to the schema and bump CONTRACT_VERSION rather than "
            "writing them ad hoc."
        )


def validate_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the per-candidate table, returning it with contract dtypes."""
    _check_columns(frame, CANDIDATE_COLUMNS, "candidate table")
    if frame.empty:
        raise ContractError("candidate table is empty")

    versions = set(frame["contract_version"].unique())
    if versions != {CONTRACT_VERSION}:
        raise ContractError(f"expected contract_version {CONTRACT_VERSION}, found {versions}")

    kinds = set(frame["benchmark_kind"].unique()) - set(BENCHMARK_KINDS)
    if kinds:
        raise ContractError(f"unknown benchmark kinds: {sorted(kinds)}")

    if frame["label_metric"].nunique() != 1:
        raise ContractError(
            "a candidate table must use one label metric; found "
            f"{sorted(frame['label_metric'].unique())}"
        )

    if (frame["tie_group_size"] < 1).any():
        raise ContractError("tie_group_size must be at least 1")
    if (frame["rank"] < 1).any():
        raise ContractError("rank is 1-based and must be at least 1")

    labelled = frame["labelled"].astype(bool)
    if frame.loc[labelled, "label"].isna().any():
        raise ContractError("rows marked labelled must carry a label")
    if frame.loc[~labelled, "label"].notna().any():
        raise ContractError("rows marked unlabelled must not carry a label")

    duplicated = frame.duplicated(subset=["benchmark", "target_id", "candidate_id", "method"])
    if duplicated.any():
        raise ContractError(
            f"{int(duplicated.sum())} duplicate (benchmark, target, candidate, method) rows"
        )

    return frame.astype(CANDIDATE_COLUMNS)


def validate_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the summary table, returning it with contract dtypes."""
    _check_columns(frame, SUMMARY_COLUMNS, "summary table")
    if frame.empty:
        raise ContractError("summary table is empty")
    versions = set(frame["contract_version"].unique())
    if versions != {CONTRACT_VERSION}:
        raise ContractError(f"expected contract_version {CONTRACT_VERSION}, found {versions}")
    coverage = frame["label_coverage"]
    if ((coverage < 0.0) | (coverage > 1.0)).any():
        raise ContractError("label_coverage must be a fraction in [0, 1]")
    if frame["n_targets"].le(0).any() or frame["n_candidates"].le(0).any():
        raise ContractError("n_targets and n_candidates must be positive")
    return frame.astype(SUMMARY_COLUMNS)


def build_candidate_table(
    features: pd.DataFrame,
    spec: BenchmarkSpec,
    top_k: int = 5,
    score_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Flatten a scored feature frame into the contract's long-form table."""
    from riborank.ranking import SCORE_COLUMNS, rank_by_score

    columns = score_columns or SCORE_COLUMNS
    metric = (
        features["label_metric"].iloc[0] if "label_metric" in features.columns else "unknown"
    )
    rows: list[dict[str, Any]] = []
    for score_column in columns:
        if score_column not in features.columns:
            continue
        method = score_column.replace("score_", "")
        for target_id, group in features.groupby("target_id"):
            ranked = rank_by_score(group, score_column).reset_index(drop=True)
            scores = pd.to_numeric(ranked[score_column], errors="coerce")
            group_sizes = scores.map(scores.value_counts()).fillna(1).astype(int)
            labels = pd.to_numeric(ranked.get("true_quality"), errors="coerce")
            for position, candidate_id in enumerate(ranked["candidate_id"], start=1):
                label = labels.iloc[position - 1]
                rows.append(
                    {
                        "contract_version": CONTRACT_VERSION,
                        "benchmark": spec.name,
                        "benchmark_kind": spec.kind,
                        "target_id": target_id,
                        "candidate_id": candidate_id,
                        "method": method,
                        "label_metric": metric,
                        "label": label,
                        "rank": position,
                        "selected": position <= top_k,
                        "tie_group_size": int(group_sizes.iloc[position - 1]),
                        "labelled": bool(pd.notna(label)),
                    }
                )
    if not rows:
        raise ContractError("no scoring columns present; nothing to record")
    return validate_candidates(pd.DataFrame(rows))


def build_summary_table(
    features: pd.DataFrame,
    spec: BenchmarkSpec,
    candidates: pd.DataFrame,
    pick_diagnostics: pd.DataFrame,
    pairwise: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """Assemble the summary table from the candidate table and diagnostics.

    ``mean_selected_label`` comes from the candidate table rather than being
    recomputed, so the summary can never disagree with the rows it summarises.
    """
    metric = (
        features["label_metric"].iloc[0] if "label_metric" in features.columns else "unknown"
    )
    labelled_mask = (
        features["true_quality"].notna()
        if "true_quality" in features.columns
        else pd.Series(False, index=features.index)
    )
    coverage = float(labelled_mask.mean()) if len(features) else np.nan
    labelled_frame = features[labelled_mask]
    oracle_mean = (
        float(labelled_frame.groupby("target_id")["true_quality"].max().mean())
        if not labelled_frame.empty
        else np.nan
    )

    selected = candidates[candidates["selected"] & candidates["labelled"]]
    selected_mean = selected.groupby("method")["label"].mean().to_dict()

    best_column = next(
        (c for c in pick_diagnostics.columns if c.startswith("best_of_")), f"best_of_{top_k}"
    )
    random_row = pick_diagnostics[pick_diagnostics["method"] == "random"]
    pairwise_by_method = (
        pairwise.set_index("method")["mean_pairwise_accuracy"].to_dict()
        if not pairwise.empty
        else {}
    )

    rows = []
    for record in pick_diagnostics.itertuples(index=False):
        if record.method == "random":
            continue
        rows.append(
            {
                "contract_version": CONTRACT_VERSION,
                "benchmark": spec.name,
                "benchmark_kind": spec.kind,
                "method": record.method,
                "label_metric": metric,
                "n_targets": int(labelled_frame["target_id"].nunique()),
                "n_candidates": int(len(features)),
                "label_coverage": coverage,
                "mean_selected_label": float(selected_mean.get(record.method, np.nan)),
                "mean_oracle_label": oracle_mean,
                "selected_percentile": float(record.mean_percentile_of_pick),
                "pairwise_accuracy": float(pairwise_by_method.get(record.method, np.nan)),
                "random_top1": float(random_row["mean_percentile_of_pick"].iloc[0])
                if not random_row.empty
                else np.nan,
                "random_best_of_k": float(random_row[best_column].iloc[0])
                if not random_row.empty
                else np.nan,
                "mean_best_of_k": float(getattr(record, best_column)),
                "best_of_k_low": float(record.random_low),
                "best_of_k_high": float(record.random_high),
                "verdict": str(record.verdict),
            }
        )
    return validate_summary(pd.DataFrame(rows))
