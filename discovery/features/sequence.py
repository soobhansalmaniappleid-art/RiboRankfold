"""Cheap, deterministic sequence statistics.

Everything here is computable on millions of loci without a model and without a
network call. That is the point: the expensive reasoning layer should only ever
see candidates that these functions have already found interesting.
"""

from __future__ import annotations

import math
from collections import Counter

NUCLEOTIDES = ("A", "C", "G", "T")


def normalise(sequence: str) -> str:
    """Upper-case, strip whitespace, and map U to T."""
    return "".join(sequence.split()).upper().replace("U", "T")


def gc_content(sequence: str) -> float:
    sequence = normalise(sequence)
    acgt = [base for base in sequence if base in NUCLEOTIDES]
    if not acgt:
        return math.nan
    return sum(base in ("G", "C") for base in acgt) / len(acgt)


def shannon_entropy(sequence: str, k: int = 1) -> float:
    """Entropy of the k-mer distribution, in bits per k-mer.

    Low entropy flags homopolymers and simple repeats, which are the most common
    source of false "unusual sequence" hits.
    """
    sequence = normalise(sequence)
    if k < 1:
        raise ValueError("k must be >= 1")
    if len(sequence) < k:
        return math.nan
    counts = Counter(sequence[i : i + k] for i in range(len(sequence) - k + 1))
    total = sum(counts.values())
    return -sum(
        (count / total) * math.log2(count / total) for count in counts.values() if count
    )


def kmer_profile(sequence: str, k: int = 3) -> dict[str, float]:
    """Normalised k-mer frequencies over canonical bases only."""
    sequence = normalise(sequence)
    counts = Counter(
        sequence[i : i + k]
        for i in range(len(sequence) - k + 1)
        if all(base in NUCLEOTIDES for base in sequence[i : i + k])
    )
    total = sum(counts.values())
    if not total:
        return {}
    return {kmer: count / total for kmer, count in counts.items()}


def low_complexity_fraction(sequence: str, window: int = 20, threshold: float = 1.2) -> float:
    """Fraction of windows whose per-base entropy falls below ``threshold``.

    With 4 bases the maximum is 2.0 bits; a window at 1.2 bits is already
    strongly skewed toward one or two bases.
    """
    sequence = normalise(sequence)
    if len(sequence) < window:
        return math.nan
    windows = [sequence[i : i + window] for i in range(len(sequence) - window + 1)]
    flagged = sum(shannon_entropy(item, k=1) < threshold for item in windows)
    return flagged / len(windows)


def sequence_features(sequence: str) -> dict[str, float]:
    """The standard deterministic block attached to every candidate."""
    sequence = normalise(sequence)
    return {
        "length": float(len(sequence)),
        "gc_content": gc_content(sequence),
        "entropy_1mer": shannon_entropy(sequence, k=1),
        "entropy_3mer": shannon_entropy(sequence, k=3),
        "low_complexity_fraction": low_complexity_fraction(sequence),
        "ambiguous_fraction": (
            sum(base not in NUCLEOTIDES for base in sequence) / len(sequence)
            if sequence
            else math.nan
        ),
    }
