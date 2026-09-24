"""Manifest building, feature extraction and label assignment."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from riborank.geometry import best_structure_match, geometry_features, multi_metric_quality, tm_like
from riborank.structure import infer_candidate_source, representative_coords

UNLABELED = {
    "true_rmsd": np.nan,
    "true_tm_like": np.nan,
    "contact_map_f1": np.nan,
    "contact_map_precision": np.nan,
    "contact_map_recall": np.nan,
    "multi_metric_quality": np.nan,
    "aligned_residue_count": 0,
}


def read_native_map(path: Path | None) -> dict[str, str]:
    """Load an optional target_id -> native_path CSV."""
    if path is None:
        return {}
    frame = pd.read_csv(path)
    missing = {"target_id", "native_path"} - set(frame.columns)
    if missing:
        raise ValueError(f"native map missing columns: {sorted(missing)}")
    return {str(row.target_id): str(row.native_path) for row in frame.itertuples(index=False)}


def build_manifest(
    candidates_root: Path,
    native_name: str = "native.pdb",
    include_native: bool = False,
    native_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Discover candidates laid out as ``candidates_root/TARGET_ID/*.pdb``."""
    native_map = native_map or {}
    rows: list[dict[str, object]] = []
    for target_dir in sorted(path for path in Path(candidates_root).iterdir() if path.is_dir()):
        mapped = native_map.get(target_dir.name)
        native_path = Path(mapped) if mapped is not None else target_dir / native_name
        for candidate_path in sorted(target_dir.glob("*.pdb")):
            if candidate_path.name == native_name and not include_native:
                continue
            rows.append(
                {
                    "target_id": target_dir.name,
                    "candidate_id": candidate_path.stem,
                    "candidate_path": str(candidate_path),
                    "candidate_source": infer_candidate_source(candidate_path.stem),
                    "native_path": str(native_path) if native_path.exists() else "",
                    "has_native": native_path.exists(),
                }
            )
    return pd.DataFrame(rows)


def build_features(manifest: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for item in manifest.itertuples(index=False):
        row = item._asdict()
        row.update(geometry_features(representative_coords(Path(item.candidate_path))))
        rows.append(row)
    return pd.DataFrame(rows)


def add_labels(features: pd.DataFrame) -> pd.DataFrame:
    """Attach native-derived labels to every candidate that has a native."""
    rows = []
    for item in features.itertuples(index=False):
        row = item._asdict()
        if not bool(item.has_native):
            row.update(UNLABELED)
            rows.append(row)
            continue
        rmsd, aligned, contact_metrics = best_structure_match(
            Path(item.candidate_path), Path(item.native_path)
        )
        row["true_rmsd"] = rmsd
        row["true_tm_like"] = tm_like(rmsd, aligned) if aligned else np.nan
        row.update(contact_metrics)
        row["multi_metric_quality"] = multi_metric_quality(
            row["true_tm_like"], row["contact_map_f1"], row["clashes_per_residue"]
        )
        row["aligned_residue_count"] = aligned
        rows.append(row)
    return pd.DataFrame(rows)


#: Label metrics, best first. ``usalign_tm`` is the official TM-score and is
#: preferred whenever it has been computed; ``true_tm_like`` is the internal
#: approximation kept only as a fallback (docs/METRICS.md).
LABEL_METRICS = ("usalign_tm", "true_tm_like")
LABEL_RMSD = {"usalign_tm": "usalign_rmsd", "true_tm_like": "true_rmsd"}


def choose_label_metric(features: pd.DataFrame, prefer: str | None = None) -> str:
    """Pick which measured metric acts as ground truth for ranking.

    Preferring a metric that was never computed is an error, not a silent
    downgrade: a run asked for official TM-score must not quietly report
    internal numbers instead.
    """
    if prefer is not None:
        if prefer not in LABEL_METRICS:
            raise ValueError(f"unknown label metric {prefer!r}; expected one of {LABEL_METRICS}")
        if prefer not in features.columns or not features[prefer].notna().any():
            raise ValueError(f"label metric {prefer!r} requested but no values were computed")
        return prefer
    for metric in LABEL_METRICS:
        if metric in features.columns and features[metric].notna().any():
            return metric
    raise ValueError("no label metric available; run add_labels first")


def apply_labels(features: pd.DataFrame, prefer: str | None = None) -> pd.DataFrame:
    """Set ``true_quality``/``true_rmsd_used`` from the chosen metric.

    Ranking reads ``true_quality`` and never the raw columns, so switching
    between official and internal metrics changes one function, not the
    evaluation code.
    """
    metric = choose_label_metric(features, prefer)
    frame = features.copy()
    frame["label_metric"] = metric
    frame["true_quality"] = pd.to_numeric(frame[metric], errors="coerce")
    rmsd_column = LABEL_RMSD[metric]
    frame["true_rmsd_used"] = (
        pd.to_numeric(frame[rmsd_column], errors="coerce")
        if rmsd_column in frame.columns
        else np.nan
    )
    return frame


def label_coverage(features: pd.DataFrame) -> pd.DataFrame:
    """Per-target count of candidates that actually received a label.

    Exclusions are never invisible. US-align represents an RNA residue by C3',
    so a candidate deposited as a C4'-only backbone trace cannot be scored with
    it. Scoring those with ``-atom C4'`` instead would mix representative atoms
    within one benchmark and break comparability with published CASP numbers,
    so they are reported as unscored rather than patched.
    """
    metric = choose_label_metric(features)
    rows = []
    for target_id, group in features.groupby("target_id"):
        scored = int(group[metric].notna().sum())
        total = int(len(group))
        rows.append(
            {
                "target_id": target_id,
                "candidates": total,
                "labelled": scored,
                "unlabelled": total - scored,
                "coverage": scored / total if total else np.nan,
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values(by="coverage", ascending=True).reset_index(drop=True)
