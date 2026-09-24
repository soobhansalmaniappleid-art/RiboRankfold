from __future__ import annotations

import numpy as np
import pytest

from riborank.geometry import (
    aligned_rmsd,
    comparable_segments,
    contact_map_metrics,
    geometry_features,
    multi_metric_quality,
    pairwise_distances,
    tm_like,
)


def test_empty_coords_give_defined_features():
    features = geometry_features(np.asarray([], dtype=float))
    assert features["num_residues"] == 0
    assert features["contact_density"] == 0.0
    assert np.isnan(features["radius_of_gyration"])


def test_identical_structures_have_zero_rmsd(helix):
    rmsd, aligned = aligned_rmsd(helix, helix)
    assert aligned == len(helix)
    assert rmsd == pytest.approx(0.0, abs=1e-9)


def test_rmsd_is_invariant_under_rotation_and_translation(helix):
    angle = 0.7
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    moved = helix @ rotation.T + np.array([100.0, -50.0, 7.0])
    rmsd, _ = aligned_rmsd(moved, helix)
    assert rmsd == pytest.approx(0.0, abs=1e-8)


def test_rmsd_grows_with_added_noise(helix):
    rng = np.random.default_rng(0)
    small, _ = aligned_rmsd(helix + rng.normal(0, 0.1, helix.shape), helix)
    large, _ = aligned_rmsd(helix + rng.normal(0, 2.0, helix.shape), helix)
    assert small < large


def test_tm_like_is_monotonically_decreasing_in_rmsd():
    scores = [tm_like(rmsd, 100) for rmsd in (0.0, 1.0, 5.0, 20.0)]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)
    assert 0.0 < scores[-1] < 1.0


def test_tm_like_rejects_degenerate_input():
    assert np.isnan(tm_like(np.nan, 100))
    assert np.isnan(tm_like(1.0, 0))


def test_contact_map_f1_is_one_for_identical_structures(helix):
    metrics = contact_map_metrics(helix, helix)
    assert metrics["contact_map_f1"] == pytest.approx(1.0)


def test_contact_map_needs_more_residues_than_the_separation_cutoff():
    short = np.zeros((5, 3))
    assert np.isnan(contact_map_metrics(short, short)["contact_map_f1"])


def test_pairwise_distances_are_symmetric_with_zero_diagonal(helix):
    distances = pairwise_distances(helix)
    assert np.allclose(distances, distances.T)
    assert np.allclose(np.diag(distances), 0.0)


def test_multi_metric_quality_weights_and_clamps():
    assert multi_metric_quality(1.0, 1.0, 0.0) == pytest.approx(0.95)
    # clash penalty saturates at 1.0
    assert multi_metric_quality(1.0, 1.0, 5.0) == pytest.approx(0.90)
    assert np.isnan(multi_metric_quality(np.nan, 1.0, 0.0))


def test_multi_metric_quality_treats_missing_contact_f1_as_zero():
    assert multi_metric_quality(1.0, np.nan, 0.0) == pytest.approx(0.65)


def test_comparable_segments_slides_the_shorter_chain():
    candidate = np.zeros((3, 3))
    native = np.zeros((5, 3))
    assert len(comparable_segments(candidate, native)) == 3
    assert len(comparable_segments(native, candidate)) == 3
    assert len(comparable_segments(native, native)) == 1


def test_comparable_segments_rejects_tiny_chains():
    assert comparable_segments(np.zeros((2, 3)), np.zeros((5, 3))) == []
    assert comparable_segments(np.asarray([]), np.zeros((5, 3))) == []


def test_clash_detection_counts_overlapping_residues():
    coords = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [20.0, 0.0, 0.0]])
    assert geometry_features(coords)["clashes_per_residue"] > 0.0


def test_backbone_break_detection():
    coords = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [500.0, 0.0, 0.0]])
    assert geometry_features(coords)["backbone_break_fraction"] == pytest.approx(0.5)


def test_long_range_contact_density_ignores_short_chains():
    assert geometry_features(np.zeros((4, 3)))["long_range_contact_density"] == 0.0


def test_long_range_contact_density_matches_reference_loop(helix):
    """Guards the vectorised rewrite against the original nested-loop version."""
    distances = pairwise_distances(helix)
    n = len(helix)
    count = possible = 0
    for i in range(n):
        for j in range(i + 8, n):
            possible += 1
            if distances[i, j] < 18.0:
                count += 1
    expected = count / possible
    assert geometry_features(helix)["long_range_contact_density"] == pytest.approx(expected)
