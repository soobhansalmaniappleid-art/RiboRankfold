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
