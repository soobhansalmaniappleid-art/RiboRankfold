from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from riborank.splits import (
    LeakageError,
    Split,
    assign_families,
    check_leakage,
    family_level_folds,
    leave_one_group_out,
    split_report,
    target_level_folds,
)


def pool(n_targets: int = 10, per_target: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "target_id": np.repeat([f"R{i:02d}" for i in range(n_targets)], per_target),
            "candidate_id": [
                f"R{i:02d}_c{j}" for i in range(n_targets) for j in range(per_target)
            ],
            "true_quality": rng.random(n_targets * per_target),
        }
    )


# -- leakage detection --------------------------------------------------


def test_a_clean_split_passes():
    frame = pool()
    check_leakage(frame[frame.target_id < "R05"], frame[frame.target_id >= "R05"])


def test_a_candidate_level_split_is_caught():
    """The exact mistake this module exists to prevent."""
    frame = pool()
    shuffled = frame.sample(frac=1.0, random_state=1)
    train, test = shuffled.iloc[:80], shuffled.iloc[80:]
    with pytest.raises(LeakageError, match="appear in both train and test"):
        check_leakage(train, test)


def test_one_shared_target_is_enough_to_fail():
    frame = pool()
    train = frame[frame.target_id <= "R05"]
    test = frame[frame.target_id >= "R05"]  # R05 on both sides
    with pytest.raises(LeakageError, match="R05"):
        check_leakage(train, test)


def test_an_empty_test_side_is_rejected():
    frame = pool()
    with pytest.raises(LeakageError, match="both sides"):
        check_leakage(frame, frame.iloc[0:0])


def test_a_missing_group_column_is_rejected():
    frame = pool().drop(columns=["target_id"])
    with pytest.raises(LeakageError, match="must carry"):
        check_leakage(frame, frame)


# -- target-level folds -------------------------------------------------


def test_every_fold_is_leak_free():
    frame = pool()
    for split in target_level_folds(frame, n_folds=5):
        split.apply(frame)  # raises on leakage


def test_folds_cover_every_target_exactly_once():
    frame = pool()
    folds = target_level_folds(frame, n_folds=5)
    seen = [group for split in folds for group in split.test_groups]
    assert sorted(seen) == sorted(frame["target_id"].unique())
    assert len(seen) == len(set(seen))


def test_candidates_of_a_target_never_split():
    frame = pool()
    for split in target_level_folds(frame, n_folds=3):
        _, test = split.apply(frame)
        for target in test["target_id"].unique():
            assert (test["target_id"] == target).sum() == 12


def test_folds_are_reproducible():
    frame = pool()
    a = target_level_folds(frame, n_folds=5, seed=7)
    b = target_level_folds(frame, n_folds=5, seed=7)
    assert [s.test_groups for s in a] == [s.test_groups for s in b]


def test_a_different_seed_gives_a_different_partition():
    frame = pool()
    a = target_level_folds(frame, n_folds=5, seed=1)
    b = target_level_folds(frame, n_folds=5, seed=2)
    assert [s.test_groups for s in a] != [s.test_groups for s in b]


def test_more_folds_than_targets_is_rejected():
    with pytest.raises(ValueError, match="cannot build"):
        target_level_folds(pool(n_targets=3), n_folds=5)


def test_one_fold_is_rejected():
    with pytest.raises(ValueError, match="at least 2"):
        target_level_folds(pool(), n_folds=1)


# -- leave one out ------------------------------------------------------


def test_leave_one_out_produces_one_split_per_target():
    frame = pool(n_targets=6)
    splits = leave_one_group_out(frame)
    assert len(splits) == 6
    assert all(len(s.test_groups) == 1 for s in splits)


def test_leave_one_out_needs_two_groups():
    with pytest.raises(ValueError, match="at least two"):
        leave_one_group_out(pool(n_targets=1))


# -- families -----------------------------------------------------------


def test_unmapped_target_raises_by_default():
    frame = pool(n_targets=4)
    with pytest.raises(ValueError, match="no family"):
        assign_families(frame, {"R00": "riboswitch"})


def test_unmapped_target_can_be_a_singleton_when_asked():
    frame = pool(n_targets=4)
    assigned = assign_families(frame, {"R00": "riboswitch"}, strict=False)
    assert set(assigned["family_id"]) == {"riboswitch", "R01", "R02", "R03"}


def test_homologous_targets_stay_together():
    """Two targets in one family must never land on opposite sides."""
    frame = pool(n_targets=6)
    families = {
        "R00": "A", "R01": "A", "R02": "A",  # homologues
        "R03": "B", "R04": "B", "R05": "C",
    }
    assigned, folds = family_level_folds(frame, families, n_folds=3)
    for split in folds:
        train, test = split.apply(assigned)
        assert not set(train["family_id"]) & set(test["family_id"])
        # and the stronger statement: no target of a held-out family leaks
        held = set(test["target_id"])
        assert not held & set(train["target_id"])


def test_family_split_is_stricter_than_target_split():
    frame = pool(n_targets=4)
    families = {"R00": "A", "R01": "A", "R02": "A", "R03": "A"}  # all homologous
    # Four targets split into two folds fine...
    assert len(target_level_folds(frame, n_folds=2)) == 2
    # ...but they are one family, so a family-level split correctly refuses:
    # there is no way to hold out a family without emptying the training set.
    with pytest.raises(ValueError, match="cannot build"):
        family_level_folds(frame, families, n_folds=2)


# -- reporting ----------------------------------------------------------


def test_split_report_accounts_for_every_candidate():
    frame = pool()
    report = split_report(frame, target_level_folds(frame, n_folds=5))
    assert (report["train_candidates"] + report["test_candidates"] == len(frame)).all()
    assert report["test_fraction"].between(0, 1).all()


def test_split_report_names_each_fold():
    frame = pool()
    report = split_report(frame, target_level_folds(frame, n_folds=4))
    assert list(report["split"]) == ["fold0", "fold1", "fold2", "fold3"]


def test_a_handmade_leaky_split_is_refused_on_apply():
    frame = pool(n_targets=4)
    bad = Split(
        name="bad",
        train_groups=("R00", "R01"),
        test_groups=("R01", "R02"),  # R01 on both sides
        group_column="target_id",
    )
    with pytest.raises(LeakageError):
        bad.apply(frame)
