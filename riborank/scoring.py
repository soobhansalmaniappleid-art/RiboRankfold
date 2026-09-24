"""Label-free baseline scoring modes.

These are diagnostic baselines, deliberately simple and hand-weighted. They are
the control that any learned reranker has to beat; they are not a model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SCORE_COLUMNS = ("score_hybrid", "score_contact", "score_low_clash", "score_compact")


def normalize(series: pd.Series) -> pd.Series:
    """Z-score a column, returning zeros when the column is constant."""
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    std = values.std(ddof=0)
    if std == 0 or not np.isfinite(std):
        return values * 0.0
    return (values - values.mean()) / std


def add_scores(features: pd.DataFrame) -> pd.DataFrame:
    """Attach the four baseline scoring modes to a feature frame."""
    frame = features.copy()
    frame["score_contact"] = normalize(frame["contact_density"]) + 0.5 * normalize(
        frame["long_range_contact_density"]
    )
    frame["score_low_clash"] = -normalize(frame["clashes_per_residue"]) - 0.5 * normalize(
        frame["backbone_break_fraction"]
    )
    frame["score_compact"] = normalize(frame["compactness"]) - 0.25 * normalize(
        frame["radius_of_gyration"]
    )
    frame["score_hybrid"] = (
        0.45 * normalize(frame["contact_density"])
        + 0.25 * normalize(frame["long_range_contact_density"])
        - 0.20 * normalize(frame["clashes_per_residue"])
        - 0.10 * normalize(frame["backbone_break_fraction"])
        + 0.10 * normalize(frame["compactness"])
    )
    return frame


def method_name(score_column: str) -> str:
    return score_column.replace("score_", "")
