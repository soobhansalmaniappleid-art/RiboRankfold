"""Splits that hold out whole targets, and the leakage checks that enforce it.

A candidate-level split is the standard way to get an encouraging number from a
reranker that has learned nothing. Candidates for one target are near-copies of
each other, so putting some in train and others in test lets a model recognise
the target rather than judge the structure:

    target R1
      candidate A -> train
      candidate B -> test     <- B is a perturbed A; the model has seen the answer
      candidate C -> train

Every split here groups by target, and `check_leakage` refuses a split that
shares a target across folds. Where homologous targets exist, group by family
instead: two structures from the same family are close enough that holding out
one while training on the other is the same failure one level up.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


class LeakageError(AssertionError):
    """A split shares a group between train and test."""


@dataclass(frozen=True, slots=True)
class Split:
    """One train/test partition, described by the groups on each side."""

    name: str
    train_groups: tuple[str, ...]
    test_groups: tuple[str, ...]
    group_column: str

    def apply(self, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        column = features[self.group_column]
        train = features[column.isin(self.train_groups)]
        test = features[column.isin(self.test_groups)]
        check_leakage(train, test, group_column=self.group_column)
        return train, test


def check_leakage(
    train: pd.DataFrame, test: pd.DataFrame, group_column: str = "target_id"
) -> None:
    """Raise if any group appears on both sides, or if either side is empty.

    An empty side is treated as leakage-adjacent rather than merely odd: a fold
    with no test groups silently reports the training score, which reads as a
    very good result.
    """
    if group_column not in train.columns or group_column not in test.columns:
        raise LeakageError(f"both frames must carry {group_column!r}")
    shared = set(train[group_column]) & set(test[group_column])
    if shared:
        raise LeakageError(
            f"{len(shared)} {group_column} value(s) appear in both train and test: "
            f"{sorted(shared)[:5]}"
        )
    if train.empty or test.empty:
        raise LeakageError("a split must have candidates on both sides")


def target_level_folds(
    features: pd.DataFrame,
    n_folds: int = 5,
    group_column: str = "target_id",
    seed: int = 0,
) -> list[Split]:
    """Partition whole targets into ``n_folds`` test sets.

    Folds are built from a seeded shuffle of the distinct groups, so a target's
    candidates always travel together.
    """
    groups = sorted(pd.unique(features[group_column].astype(str)))
    if n_folds < 2:
        raise ValueError(f"n_folds must be at least 2, got {n_folds}")
    if len(groups) < n_folds:
        raise ValueError(
            f"cannot build {n_folds} folds from {len(groups)} {group_column} values; "
            "a fold with no held-out group cannot test anything"
        )
    shuffled = list(groups)
    np.random.default_rng(seed).shuffle(shuffled)
    chunks = [list(chunk) for chunk in np.array_split(np.array(shuffled, dtype=object), n_folds)]
    return [
        Split(
            name=f"fold{index}",
            test_groups=tuple(chunk),
            train_groups=tuple(g for g in shuffled if g not in set(chunk)),
            group_column=group_column,
        )
        for index, chunk in enumerate(chunks)
    ]


def leave_one_group_out(
    features: pd.DataFrame, group_column: str = "target_id"
) -> list[Split]:
    """One split per group. With few targets this is usually the only option."""
    groups = sorted(pd.unique(features[group_column].astype(str)))
    if len(groups) < 2:
        raise ValueError(f"need at least two {group_column} values, got {len(groups)}")
    return [
        Split(
            name=f"holdout_{group}",
            test_groups=(group,),
            train_groups=tuple(g for g in groups if g != group),
            group_column=group_column,
        )
        for group in groups
    ]


def assign_families(
    features: pd.DataFrame,
    families: dict[str, str],
    group_column: str = "target_id",
    family_column: str = "family_id",
    strict: bool = True,
) -> pd.DataFrame:
    """Attach a family label to each target.

    An unmapped target is its own family only when ``strict`` is False. By
    default it raises: silently treating an unknown target as a singleton is how
    a homologue ends up split across train and test.
    """
    frame = features.copy()
    targets = pd.unique(frame[group_column].astype(str))
    missing = [target for target in targets if target not in families]
    if missing and strict:
        raise ValueError(
            f"no family for {len(missing)} target(s): {sorted(missing)[:5]}. "
            "Pass strict=False to treat them as singleton families."
        )
    frame[family_column] = frame[group_column].astype(str).map(
        lambda target: families.get(target, target)
    )
    return frame


def family_level_folds(
    features: pd.DataFrame,
    families: dict[str, str],
    n_folds: int = 5,
    seed: int = 0,
    strict: bool = True,
) -> tuple[pd.DataFrame, list[Split]]:
    """Folds that hold out whole families, not just whole targets."""
    frame = assign_families(features, families, strict=strict)
    return frame, target_level_folds(
        frame, n_folds=n_folds, group_column="family_id", seed=seed
    )


def split_report(features: pd.DataFrame, splits: list[Split]) -> pd.DataFrame:
    """Summarise folds so an unbalanced or degenerate one is visible."""
    rows = []
    for split in splits:
        train, test = split.apply(features)
        rows.append(
            {
                "split": split.name,
                "group_column": split.group_column,
                "train_groups": len(split.train_groups),
                "test_groups": len(split.test_groups),
                "train_candidates": len(train),
                "test_candidates": len(test),
                "test_fraction": len(test) / (len(train) + len(test)),
            }
        )
    return pd.DataFrame(rows)
