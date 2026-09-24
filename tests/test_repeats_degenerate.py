"""Regression tests for degenerate repeat arrays.

The detector passed every synthetic test and then failed completely the first
time it was pointed at a spike-in on a real genome: 0 of 4 planted arrays found.

The cause was that a point mutation inside the seed k-mer hides that copy,
leaving one gap of about twice the period. Scored on raw gaps, that single
absence pushes the coefficient of variation past the threshold — gaps of
[140, 280, 140, 140, ...] score 0.35 against a limit of 0.25 — even though
every remaining copy sits exactly where it should.

Real arrays have degenerate copies. A detector that only works on sequence too
clean to be real is not a detector, so these tests fix the behaviour that
synthetic data could not.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from discovery.features.repeats import _period_cv, find_repeat_arrays

UNIT = "CATGTGTATCGCATGTTACGTACGT"

#: A real 391 kb bacterial contig bundled with pyhmmer's test data.
REAL_CONTIG = Path(
    "/usr/local/lib/python3.11/dist-packages/pyhmmer/tests/data/seqs/"
    "1390.SAMEA104415756.OFHT01000022.fna"
)


def planted(copies: int, period: int, mutate: float, seed: int) -> str:
    rng = random.Random(seed)
    out = []
    for _ in range(copies):
        unit = UNIT
        if rng.random() < mutate:
            index = rng.randrange(len(unit))
            unit = unit[:index] + rng.choice("ACGT") + unit[index + 1 :]
        out.append(unit + "".join(rng.choice("ACGT") for _ in range(period - len(UNIT))))
    return "".join(out)


def background(length: int, seed: int) -> str:
    rng = random.Random(1000 + seed)
    return "".join(rng.choice("ACGT") for _ in range(length))


# -- the period estimator ----------------------------------------------


def test_one_missed_copy_no_longer_rejects_a_perfect_array():
    """The exact gap pattern that broke the detector on real data."""
    assert _period_cv([140.0, 280.0, 140.0, 140.0, 140.0, 140.0]) == pytest.approx(0.0)


def test_two_missed_copies_in_a_row_are_tolerated():
    assert _period_cv([140.0, 420.0, 140.0, 140.0, 140.0, 140.0]) == pytest.approx(0.0)


def test_irregular_spacing_is_still_rejected():
    """Allowing missed copies must not explain away genuine irregularity."""
    assert _period_cv([109.0, 377.0, 111.0, 250.0, 88.0]) == float("inf")


def test_mostly_multiples_is_rejected_as_too_sparse():
    """A motif whose gaps are nearly all multiples is scattered, not an array."""
    assert _period_cv([100.0, 200.0, 300.0, 200.0, 200.0]) == float("inf")


def test_a_gap_off_a_multiple_is_rejected():
    # 210 sits between one and two periods of 140, so it is irregular spacing
    # rather than a missed copy. (A gap within ~12% of a multiple is allowed,
    # because real spacers vary in length.)
    assert _period_cv([140.0, 210.0, 140.0, 140.0]) == float("inf")


def test_a_gap_slightly_off_a_multiple_is_still_a_missed_copy():
    """Real spacers vary; a 7% deviation from 2x must not reject the array."""
    assert _period_cv([140.0, 260.0, 140.0, 140.0]) < 0.1


def test_empty_gaps_are_infinite():
    assert _period_cv([]) == float("inf")


# -- synthetic background ----------------------------------------------


@pytest.mark.parametrize("mutate", [0.0, 0.2, 0.3, 0.4])
def test_detection_survives_degenerate_copies(mutate):
    found = 0
    for seed in range(10):
        sequence = background(300, seed) + planted(10, 140, mutate, seed) + background(300, seed)
        found += bool(find_repeat_arrays(sequence))
    assert found >= 8, f"only {found}/10 detected at mutation rate {mutate}"


def test_the_reported_period_is_the_true_period_not_the_mean_gap():
    """With a copy missing, the mean gap overstates the period; the min does not."""
    sequence = background(300, 0) + planted(12, 140, 0.35, 5) + background(300, 0)
    arrays = find_repeat_arrays(sequence)
    assert arrays
    assert arrays[0].mean_period == pytest.approx(140.0, abs=1.0)


def test_random_sequence_still_yields_nothing():
    assert find_repeat_arrays(background(20000, 42)) == []


# -- real genomic background -------------------------------------------

pytestmark_real = pytest.mark.skipif(
    not REAL_CONTIG.is_file(), reason="needs pyhmmer's bundled real contig"
)


def read_real_contig() -> str:
    from pyhmmer.easel import SequenceFile

    with SequenceFile(str(REAL_CONTIG), digital=False) as handle:
        return list(handle)[0].sequence


@pytestmark_real
def test_no_false_positives_on_a_real_genome():
    """391 kb of real bacterial DNA must not produce a single array."""
    assert find_repeat_arrays(read_real_contig()) == []


@pytestmark_real
@pytest.mark.parametrize("period", [110, 140, 165])
def test_a_degenerate_array_spiked_into_a_real_genome_is_found(period):
    real = read_real_contig()
    insert = planted(9, period, 0.3, period)
    at = 200_000
    arrays = find_repeat_arrays(real[:at] + insert + real[at:])
    hits = [a for a in arrays if at - 200 <= a.start <= at + len(insert) + 200]
    assert hits, f"missed a 9-copy array at period {period} in a real genome"
    assert hits[0].mean_period == pytest.approx(period, abs=1.0)
