from __future__ import annotations

import math
import random

import pytest

from discovery.features.neighborhood import (
    Gene,
    Neighbourhood,
    architecture_novelty,
    cross_genome_support,
    unexplained_fraction,
)
from discovery.features.repeats import find_repeat_arrays, repeat_features
from discovery.features.sequence import (
    gc_content,
    low_complexity_fraction,
    sequence_features,
    shannon_entropy,
)

UNIT = "CATGTGTATCGCATGTTACGTACGT"


def random_dna(n: int, seed: int = 0) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(n))


def build_array(copies: int, period: int = 120, seed: int = 0, unit: str = UNIT) -> str:
    rng = random.Random(seed)
    out = [random_dna(200, seed)]
    for _ in range(copies):
        spacer = "".join(rng.choice("ACGT") for _ in range(period - len(unit)))
        out.append(unit + spacer)
    out.append(random_dna(200, seed + 1))
    return "".join(out)


# -- sequence -----------------------------------------------------------


def test_gc_content():
    assert gc_content("GGCC") == pytest.approx(1.0)
    assert gc_content("ATAT") == pytest.approx(0.0)
    assert gc_content("GCAT") == pytest.approx(0.5)


def test_gc_content_ignores_ambiguous_bases():
    assert gc_content("GCNNNN") == pytest.approx(1.0)
    assert math.isnan(gc_content("NNNN"))


def test_uracil_is_treated_as_thymine():
    assert gc_content("AUAU") == gc_content("ATAT")


def test_entropy_is_zero_for_a_homopolymer():
    assert shannon_entropy("A" * 50) == pytest.approx(0.0)


def test_entropy_approaches_two_bits_for_random_dna():
    assert shannon_entropy(random_dna(5000)) > 1.9


def test_low_complexity_detection():
    assert low_complexity_fraction("A" * 200) == pytest.approx(1.0)
    assert low_complexity_fraction(random_dna(2000)) == pytest.approx(0.0)


def test_sequence_features_are_all_present():
    features = sequence_features(random_dna(500))
    assert set(features) == {
        "length",
        "gc_content",
        "entropy_1mer",
        "entropy_3mer",
        "low_complexity_fraction",
        "ambiguous_fraction",
    }
    assert features["length"] == 500.0


# -- repeats ------------------------------------------------------------


def test_finds_a_planted_array():
    arrays = find_repeat_arrays(build_array(8))
    assert len(arrays) == 1
    array = arrays[0]
    assert array.copy_count == 8
    assert array.unit_length == len(UNIT)
    assert array.mean_period == pytest.approx(120.0)
    assert array.unit_identity == pytest.approx(1.0)
    assert array.consensus == UNIT


def test_no_arrays_in_random_sequence():
    assert find_repeat_arrays(random_dna(5000, seed=4)) == []


def test_homopolymer_does_not_register_as_an_array():
    # A long poly-A has no regular period at the scale we search for.
    assert find_repeat_arrays("A" * 2000) == []


@pytest.mark.parametrize("copies", [3, 5, 12])
def test_copy_count_is_recovered(copies):
    arrays = find_repeat_arrays(build_array(copies, seed=copies))
    assert arrays and arrays[0].copy_count == copies


def test_min_copies_is_enforced():
    assert find_repeat_arrays(build_array(3), min_copies=5) == []


def test_irregular_spacing_is_rejected():
    rng = random.Random(1)
    seq = random_dna(200)
    for _ in range(6):
        seq += UNIT + "".join(rng.choice("ACGT") for _ in range(rng.randint(30, 380)))
    assert find_repeat_arrays(seq, max_period_cv=0.05) == []


def test_period_outside_the_search_window_is_ignored():
    assert find_repeat_arrays(build_array(6, period=120), max_period=60) == []


def test_repeat_features_on_empty_input():
    features = repeat_features("")
    assert features["repeat_array_count"] == 0.0
    assert math.isnan(features["repeat_unit_length"])


def test_two_separate_arrays_are_reported_separately():
    left = build_array(5, period=120, seed=2)
    right = build_array(5, period=150, seed=3, unit="GGTTACCAGGTTACCAGGTTACCA")
    arrays = find_repeat_arrays(left + random_dna(500, 9) + right)
    assert len(arrays) == 2


def test_invalid_parameters_are_rejected():
    with pytest.raises(ValueError):
        find_repeat_arrays("ACGT" * 100, seed_k=2)
    with pytest.raises(ValueError):
        find_repeat_arrays("ACGT" * 100, min_copies=1)
    with pytest.raises(ValueError):
        find_repeat_arrays("ACGT" * 100, min_period=500, max_period=100)


# -- neighbourhood ------------------------------------------------------


def make_neighbourhood(families: list[str], taxon: str = "t1") -> Neighbourhood:
    genes = [
        Gene(gene_id=f"g{i}", family=family, start=i * 1000, end=i * 1000 + 800)
        for i, family in enumerate(families)
    ]
    return Neighbourhood(contig_id="c1", anchor_family="RT", genes=genes, taxon=taxon)


def test_known_architecture_scores_zero_novelty():
    n = make_neighbourhood(["RT", "capsid"])
    assert architecture_novelty(n, {("RT", "capsid")}) == pytest.approx(0.0)


def test_entirely_unknown_architecture_scores_one():
    n = make_neighbourhood(["RT", "orfX"])
    assert architecture_novelty(n, {("integrase", "capsid")}) == pytest.approx(1.0)


def test_partial_overlap_scores_between():
    n = make_neighbourhood(["RT", "orfX"])
    novelty = architecture_novelty(n, {("RT", "capsid")})
    assert 0.0 < novelty < 1.0


def test_novelty_against_an_empty_catalogue_is_maximal():
    assert architecture_novelty(make_neighbourhood(["RT"]), set()) == pytest.approx(1.0)


def test_unexplained_partner_fraction():
    n = make_neighbourhood(["RT", "orfX", "capsid"])
    assert unexplained_fraction(n, {"capsid"}) == pytest.approx(0.5)


def test_anchor_family_is_not_counted_as_a_partner():
    n = make_neighbourhood(["RT"])
    assert math.isnan(unexplained_fraction(n, {"capsid"}))


def test_cross_genome_support_counts_distinct_taxa():
    architecture = ("RT", "orfX")
    support = cross_genome_support(
        [
            make_neighbourhood(list(architecture), taxon="a"),
            make_neighbourhood(list(architecture), taxon="b"),
            make_neighbourhood(list(architecture), taxon="a"),  # same taxon, not new
        ]
    )
    assert support[architecture] == 2
