"""Geometry features and native-comparison metrics.

IMPORTANT: ``tm_like`` is an internal approximation, not the official US-align
TM-score. Numbers produced here are internally consistent but are NOT directly
comparable to published CASP TM-scores. See docs/METRICS.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from riborank.structure import representative_chains

CONTACT_THRESHOLD = 12.0
LONG_RANGE_THRESHOLD = 18.0
LONG_RANGE_SEPARATION = 8
CLASH_THRESHOLD = 2.5
BACKBONE_BREAK_THRESHOLD = 12.0


def pairwise_distances(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def geometry_features(coords: np.ndarray) -> dict[str, float]:
    """Label-free geometric descriptors of a single candidate structure."""
    n = int(len(coords))
    if n == 0:
        return {
            "num_residues": 0,
            "radius_of_gyration": np.nan,
            "end_to_end_distance": np.nan,
            "contact_density": 0.0,
            "long_range_contact_density": 0.0,
            "clashes_per_residue": np.nan,
            "backbone_break_fraction": np.nan,
            "compactness": 0.0,
        }

    centered = coords - coords.mean(axis=0)
    radius = float(np.sqrt((centered**2).sum(axis=1).mean()))
    end_to_end = float(np.linalg.norm(coords[-1] - coords[0])) if n > 1 else 0.0

    distances = pairwise_distances(coords)
    upper = distances[np.triu_indices(n, k=1)]
    contact_count = int((upper < CONTACT_THRESHOLD).sum()) if len(upper) else 0
    possible = n * (n - 1) / 2

    # Long-range contacts use a vectorised upper triangle offset by the
    # sequence-separation cutoff.
    if n > LONG_RANGE_SEPARATION:
        rows, cols = np.triu_indices(n, k=LONG_RANGE_SEPARATION)
        long_possible = int(len(rows))
        long_count = int((distances[rows, cols] < LONG_RANGE_THRESHOLD).sum())
    else:
        long_possible = 0
        long_count = 0

    steps = np.linalg.norm(np.diff(coords, axis=0), axis=1) if n > 1 else np.asarray([])
    breaks = int((steps > BACKBONE_BREAK_THRESHOLD).sum()) if len(steps) else 0
    clashes = int(((upper < CLASH_THRESHOLD) & (upper > 0.0)).sum()) if len(upper) else 0

    return {
        "num_residues": n,
        "radius_of_gyration": radius,
        "end_to_end_distance": end_to_end,
        "contact_density": float(contact_count / possible) if possible else 0.0,
        "long_range_contact_density": float(long_count / long_possible) if long_possible else 0.0,
        "clashes_per_residue": float(clashes / n),
        "backbone_break_fraction": float(breaks / max(n - 1, 1)),
        "compactness": float(n / (radius + 1e-6)),
    }


def aligned_rmsd(candidate: np.ndarray, native: np.ndarray) -> tuple[float, int]:
    """Kabsch-superposed RMSD over the first ``min(len)`` residues of each array."""
    n = min(len(candidate), len(native))
    if n == 0:
        return np.nan, 0
    candidate_centered = candidate[:n] - candidate[:n].mean(axis=0)
    native_centered = native[:n] - native[:n].mean(axis=0)
    covariance = candidate_centered.T @ native_centered
    u, _, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[2, 2] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ correction @ vt
    aligned = candidate_centered @ rotation
    rmsd = np.sqrt(((aligned - native_centered) ** 2).sum() / n)
    return float(rmsd), int(n)


def tm_like(rmsd: float, aligned_count: int) -> float:
    """Internal TM-score-shaped statistic. NOT official US-align TM-score."""
    if not np.isfinite(rmsd) or aligned_count <= 0:
        return np.nan
    d0 = max(1.0, 1.24 * ((max(aligned_count, 16) - 15) ** (1.0 / 3.0)) - 1.8)
    return float(1.0 / (1.0 + (rmsd / d0) ** 2))


def contact_map_metrics(
    candidate: np.ndarray,
    native: np.ndarray,
    threshold: float = LONG_RANGE_THRESHOLD,
    min_separation: int = LONG_RANGE_SEPARATION,
) -> dict[str, float]:
    n = min(len(candidate), len(native))
    if n <= min_separation:
        return {
            "contact_map_precision": np.nan,
            "contact_map_recall": np.nan,
            "contact_map_f1": np.nan,
        }
    candidate_distances = pairwise_distances(candidate[:n])
    native_distances = pairwise_distances(native[:n])
    mask = np.zeros((n, n), dtype=bool)
    rows, cols = np.triu_indices(n, k=min_separation)
    mask[rows, cols] = True

    candidate_contacts = (candidate_distances < threshold) & mask
    native_contacts = (native_distances < threshold) & mask
    tp = int((candidate_contacts & native_contacts).sum())
    pred = int(candidate_contacts.sum())
    truth = int(native_contacts.sum())
    precision = tp / pred if pred else 0.0
    recall = tp / truth if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "contact_map_precision": float(precision),
        "contact_map_recall": float(recall),
        "contact_map_f1": float(f1),
    }


def multi_metric_quality(
    tm_score: float, contact_f1: float, clashes_per_residue: float
) -> float:
    if not np.isfinite(tm_score):
        return np.nan
    contact = 0.0 if not np.isfinite(contact_f1) else contact_f1
    clash_penalty = (
        0.0 if not np.isfinite(clashes_per_residue) else min(float(clashes_per_residue), 1.0)
    )
    return float(0.65 * tm_score + 0.30 * contact - 0.05 * clash_penalty)


def comparable_segments(
    candidate: np.ndarray, native: np.ndarray
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Enumerate equal-length windows of a candidate/native chain pair."""
    c_len = len(candidate)
    n_len = len(native)
    if c_len == 0 or n_len == 0:
        return []
    if min(c_len, n_len) < 3:
        return []
    if c_len == n_len:
        return [(candidate, native)]
    if c_len < n_len:
        return [(candidate, native[start : start + c_len]) for start in range(n_len - c_len + 1)]
    return [(candidate[start : start + n_len], native) for start in range(c_len - n_len + 1)]


def best_structure_match(
    candidate_path: Path, native_path: Path
) -> tuple[float, int, dict[str, float]]:
    """Find the best chain/window match before computing labels.

    CASP RNA natives may contain multiple RNA chains and non-RNA molecules, while
    candidate files are often single-chain C4' traces. A naive concatenated
    alignment turns a valid candidate into a very high RMSD artifact, so labels
    are computed against the best chain/window pair.
    """
    candidate_chains = representative_chains(candidate_path)
    native_chains = representative_chains(native_path)
    best: tuple[float, int, dict[str, float]] | None = None
    for candidate in candidate_chains.values():
        for native in native_chains.values():
            for c_segment, n_segment in comparable_segments(candidate, native):
                rmsd, aligned = aligned_rmsd(c_segment, n_segment)
                if aligned == 0 or not np.isfinite(rmsd):
                    continue
                if best is None or rmsd < best[0]:
                    best = (rmsd, aligned, contact_map_metrics(c_segment, n_segment))
    if best is None:
        return (
            np.nan,
            0,
            {
                "contact_map_precision": np.nan,
                "contact_map_recall": np.nan,
                "contact_map_f1": np.nan,
            },
        )
    return best
