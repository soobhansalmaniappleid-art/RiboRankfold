"""Label-free baseline scoring modes.

These are diagnostic baselines, deliberately simple and hand-weighted. They are
the control that any learned reranker has to beat; they are not a model.

The first four modes reward compactness and contact density monotonically. On
CASP15 their top pick is almost always a collapsed structure far smaller than
its length allows (see docs/CORRECTIONS.md). ``score_plausibility`` replaces
"more compact is better" with "closer to the size a chain of this length should
have", using a polymer scaling law fitted without labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SCORE_COLUMNS = (
    "score_hybrid",
    "score_contact",
    "score_low_clash",
    "score_compact",
    "score_plausibility",
)


def normalize(series: pd.Series) -> pd.Series:
    """Z-score a column, returning zeros when the column is constant."""
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    std = values.std(ddof=0)
    if std == 0 or not np.isfinite(std):
        return values * 0.0
    return (values - values.mean()) / std


def fit_size_scaling(features: pd.DataFrame) -> tuple[float, float]:
    """Fit ``Rg = a * N**b`` by least squares in log space. Uses no labels.

    Returns ``(log_a, b)``. Rows without a positive length and radius are
    ignored; a frame with fewer than two usable rows raises ``ValueError``.
    """
    n = pd.to_numeric(features["num_residues"], errors="coerce")
    rg = pd.to_numeric(features["radius_of_gyration"], errors="coerce")
    usable = (n > 0) & (rg > 0) & np.isfinite(rg)
    if int(usable.sum()) < 2 or n[usable].nunique() < 2:
        raise ValueError("need at least two distinct chain lengths to fit size scaling")
    b, log_a = np.polyfit(np.log(n[usable]), np.log(rg[usable]), 1)
    return float(log_a), float(b)


def size_deviation(features: pd.DataFrame) -> pd.Series:
    """``|log(Rg / Rg_expected)|`` for every candidate, fitted leave-one-target-out.

    Each target's expected size comes from a scaling law fitted on the *other*
    targets' candidates, so no target's own pool shapes its own yardstick. With a
    single target there is nothing to leave out and the fit uses that target.
    """
    deviation = pd.Series(np.nan, index=features.index, dtype=float)
    targets = features["target_id"].unique()
    for target_id in targets:
        mask = features["target_id"] == target_id
        reference = features[~mask] if len(targets) > 1 else features
        try:
            log_a, b = fit_size_scaling(reference)
        except ValueError:
            try:
                log_a, b = fit_size_scaling(features)
            except ValueError:
                continue
        n = pd.to_numeric(features.loc[mask, "num_residues"], errors="coerce")
        rg = pd.to_numeric(features.loc[mask, "radius_of_gyration"], errors="coerce")
        with np.errstate(divide="ignore", invalid="ignore"):
            deviation.loc[mask] = np.abs(np.log(rg) - (log_a + b * np.log(n)))
    # Unmeasurable size is treated as maximally implausible, not as ideal.
    worst = deviation.max() if deviation.notna().any() else 0.0
    return deviation.replace([np.inf, -np.inf], np.nan).fillna(worst)


def add_scores(features: pd.DataFrame) -> pd.DataFrame:
    """Attach every baseline scoring mode to a feature frame."""
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
    frame["size_deviation"] = size_deviation(frame)
    # Weights were set after diagnosing the compactness failure on CASP15, so
    # CASP15 numbers for this mode are in-sample. See docs/CORRECTIONS.md.
    frame["score_plausibility"] = (
        0.5 * normalize(frame["long_range_contact_density"])
        - 1.0 * normalize(frame["size_deviation"])
        - 0.2 * normalize(frame["clashes_per_residue"])
    )
    return frame


def method_name(score_column: str) -> str:
    return score_column.replace("score_", "")
