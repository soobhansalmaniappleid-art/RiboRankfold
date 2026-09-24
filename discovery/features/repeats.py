"""Tandem repeat array detection.

This is the deterministic detector that stands in for the moment in an
agent-driven campaign where someone finally looks at the raw DNA and notices the
sequence is repeating. A model should not be the thing that spots this; a model
should be the thing that explains what it means.

The detector is seed-and-extend:

1. index every k-mer position,
2. keep k-mers that recur at a *regular* period,
3. extend each seed into a repeat unit and measure copy identity,
4. merge overlapping seeds so one array is reported once.

Arrays in this shape -- a conserved unit repeated at a near-constant period with
variable sequence in between -- cover CRISPR arrays, and were the signature that
made the ART locus interesting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from discovery.features.sequence import normalise


@dataclass(slots=True)
class RepeatArray:
    start: int
    end: int
    unit_length: int
    copy_count: int
    mean_period: float
    period_cv: float
    unit_identity: float
    consensus: str
    positions: list[int] = field(default_factory=list)

    @property
    def span(self) -> int:
        return self.end - self.start


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _identity(left: str, right: str) -> float:
    """Ungapped identity over the overlapping prefix of two strings."""
    n = min(len(left), len(right))
    if n == 0:
        return 0.0
    return sum(a == b for a, b in zip(left[:n], right[:n], strict=True)) / n


def _consensus(units: list[str]) -> str:
    if not units:
        return ""
    width = min(len(unit) for unit in units)
    out = []
    for index in range(width):
        column = [unit[index] for unit in units]
        out.append(max(set(column), key=column.count))
    return "".join(out)


def find_repeat_arrays(
    sequence: str,
    seed_k: int = 20,
    min_copies: int = 3,
    min_period: int = 25,
    max_period: int = 400,
    max_period_cv: float = 0.25,
    min_identity: float = 0.80,
) -> list[RepeatArray]:
    """Find tandem repeat arrays with a near-constant period.

    ``min_copies`` is the strongest guard against noise: two matching k-mers are
    a coincidence, and the false-positive rate falls steeply with each further
    regularly spaced copy.
    """
    sequence = normalise(sequence)
    if seed_k < 4:
        raise ValueError("seed_k must be >= 4")
    if min_copies < 2:
        raise ValueError("min_copies must be >= 2")
    if min_period > max_period:
        raise ValueError("min_period must not exceed max_period")
    if len(sequence) < seed_k * min_copies:
        return []

    positions: dict[str, list[int]] = {}
    for index in range(len(sequence) - seed_k + 1):
        kmer = sequence[index : index + seed_k]
        if "N" in kmer:
            continue
        positions.setdefault(kmer, []).append(index)

    arrays: list[RepeatArray] = []
    for kmer, hits in positions.items():
        if len(hits) < min_copies:
            continue
        for run in _regular_runs(hits, min_period, max_period, max_period_cv, min_copies):
            array = _build_array(sequence, kmer, run, seed_k, max_period)
            if array is not None and array.unit_identity >= min_identity:
                arrays.append(array)

    return _merge_overlapping(arrays)


def _regular_runs(
    hits: list[int],
    min_period: int,
    max_period: int,
    max_period_cv: float,
    min_copies: int,
) -> list[list[int]]:
    """Split k-mer hit positions into maximal runs of acceptable, regular period."""
    runs: list[list[int]] = []
    current = [hits[0]]
    for previous, position in pairwise(hits):
        gap = position - previous
        if min_period <= gap <= max_period:
            current.append(position)
            continue
        if len(current) >= min_copies:
            runs.append(current)
        current = [position]
    if len(current) >= min_copies:
        runs.append(current)

    accepted = []
    for run in runs:
        gaps = [float(b - a) for a, b in pairwise(run)]
        mean = _mean(gaps)
        if mean and _std(gaps) / mean <= max_period_cv:
            accepted.append(run)
    return accepted


def _build_array(
    sequence: str, kmer: str, run: list[int], seed_k: int, max_period: int
) -> RepeatArray | None:
    gaps = [float(b - a) for a, b in pairwise(run)]
    mean_period = _mean(gaps)
    if not mean_period or math.isnan(mean_period):
        return None

    # Extend the seed rightwards while the copies still agree, without running
    # past the next copy's start.
    limit = min(int(mean_period), max_period)
    unit_length = seed_k
    while unit_length < limit:
        column = {sequence[position + unit_length] for position in run[:-1]}
        if len(column) > 1:
            break
        unit_length += 1

    units = [sequence[position : position + unit_length] for position in run]
    units = [unit for unit in units if len(unit) == unit_length]
    if len(units) < 2:
        return None
    identities = [
        _identity(left, right) for i, left in enumerate(units) for right in units[i + 1 :]
    ]
    return RepeatArray(
        start=run[0],
        end=run[-1] + unit_length,
        unit_length=unit_length,
        copy_count=len(run),
        mean_period=mean_period,
        period_cv=_std(gaps) / mean_period,
        unit_identity=_mean(identities),
        consensus=_consensus(units),
        positions=list(run),
    )


def _merge_overlapping(arrays: list[RepeatArray]) -> list[RepeatArray]:
    """Keep the strongest array among any set of overlapping detections."""
    if not arrays:
        return []
    ordered = sorted(arrays, key=lambda a: (-a.copy_count, a.period_cv, a.start))
    kept: list[RepeatArray] = []
    for array in ordered:
        if any(array.start < other.end and other.start < array.end for other in kept):
            continue
        kept.append(array)
    return sorted(kept, key=lambda a: a.start)


def repeat_features(sequence: str, **kwargs: object) -> dict[str, float]:
    """Summarise repeat structure as a flat feature block."""
    arrays = find_repeat_arrays(sequence, **kwargs)  # type: ignore[arg-type]
    if not arrays:
        return {
            "repeat_array_count": 0.0,
            "repeat_copy_count": 0.0,
            "repeat_unit_length": math.nan,
            "repeat_mean_period": math.nan,
            "repeat_period_cv": math.nan,
            "repeat_unit_identity": math.nan,
            "repeat_span_fraction": 0.0,
        }
    best = max(arrays, key=lambda a: a.copy_count)
    total_span = sum(array.span for array in arrays)
    return {
        "repeat_array_count": float(len(arrays)),
        "repeat_copy_count": float(best.copy_count),
        "repeat_unit_length": float(best.unit_length),
        "repeat_mean_period": float(best.mean_period),
        "repeat_period_cv": float(best.period_cv),
        "repeat_unit_identity": float(best.unit_identity),
        "repeat_span_fraction": float(total_span / len(normalise(sequence)) or 0.0),
    }
