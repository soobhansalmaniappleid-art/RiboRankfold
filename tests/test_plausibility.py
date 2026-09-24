from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from riborank.scoring import add_scores, fit_size_scaling, size_deviation


def pool(target: str, length: int, radii: list[float]) -> pd.DataFrame:
    count = len(radii)
    return pd.DataFrame(
        {
            "target_id": [target] * count,
            "candidate_id": [f"{target}_{i}" for i in range(count)],
            "num_residues": [length] * count,
            "radius_of_gyration": radii,
            "contact_density": [0.3] * count,
            "long_range_contact_density": [0.3] * count,
            "clashes_per_residue": [0.0] * count,
            "backbone_break_fraction": [0.0] * count,
            "compactness": [length / r for r in radii],
        }
    )


def ideal_rg(length: int) -> float:
    return 3.0 * length**0.4


def test_scaling_fit_recovers_a_known_power_law():
    lengths = np.array([20, 50, 100, 200, 400, 800])
    frame = pd.DataFrame(
        {"num_residues": lengths, "radius_of_gyration": [ideal_rg(n) for n in lengths]}
    )
    log_a, b = fit_size_scaling(frame)
    assert b == pytest.approx(0.4, abs=1e-9)
    assert np.exp(log_a) == pytest.approx(3.0, rel=1e-9)


def test_scaling_fit_needs_distinct_lengths():
    frame = pd.DataFrame({"num_residues": [50, 50, 50], "radius_of_gyration": [10.0, 11.0, 12.0]})
    with pytest.raises(ValueError):
        fit_size_scaling(frame)


def test_a_collapsed_structure_is_the_least_plausible():
    frames = [pool(f"T{n}", n, [ideal_rg(n)] * 3) for n in (40, 120, 300)]
    frames.append(pool("Q", 720, [ideal_rg(720), ideal_rg(720) * 0.25, ideal_rg(720) * 1.02]))
    scored = add_scores(pd.concat(frames, ignore_index=True))
    query = scored[scored["target_id"] == "Q"].set_index("candidate_id")
    assert query["score_plausibility"].idxmin() == "Q_1"
    # The old compactness mode prefers exactly that collapsed structure.
    assert query["score_compact"].idxmax() == "Q_1"


def test_over_expansion_is_penalised_like_collapse():
    frames = [pool(f"T{n}", n, [ideal_rg(n)] * 3) for n in (40, 120, 300)]
    frames.append(pool("Q", 200, [ideal_rg(200), ideal_rg(200) * 4.0]))
    scored = add_scores(pd.concat(frames, ignore_index=True))
    query = scored[scored["target_id"] == "Q"].set_index("candidate_id")
    assert query.loc["Q_0", "score_plausibility"] > query.loc["Q_1", "score_plausibility"]


def test_deviation_is_fitted_leave_one_target_out():
    """A target's own extreme pool must not move its own yardstick."""
    base = [pool(f"T{n}", n, [ideal_rg(n)] * 3) for n in (40, 120, 300)]
    shrunk = pool("Q", 500, [ideal_rg(500) * 0.3] * 3)
    deviation = size_deviation(pd.concat([*base, shrunk], ignore_index=True))
    q = deviation.iloc[-3:]
    assert (q > 1.0).all()  # |log 0.3| ~ 1.2 against the other targets' law


def test_missing_size_is_treated_as_worst_not_ideal():
    frames = [pool(f"T{n}", n, [ideal_rg(n)] * 2) for n in (40, 120, 300)]
    frame = pd.concat(frames, ignore_index=True)
    frame.loc[0, "radius_of_gyration"] = np.nan
    deviation = size_deviation(frame)
    assert deviation.iloc[0] == pytest.approx(deviation.max())


def test_single_target_falls_back_to_its_own_fit():
    frame = pd.concat(
        [pool("A", 30, [ideal_rg(30)]), pool("A", 90, [ideal_rg(90)])], ignore_index=True
    )
    assert size_deviation(frame).max() == pytest.approx(0.0, abs=1e-9)
