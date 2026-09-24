"""Genomic neighbourhood description and novelty.

The signal that matters is rarely a single odd gene. It is a gene sitting in an
arrangement that does not match anything already described -- and doing so
repeatedly, in genomes that are not close relatives.

This module has no opinion about which databases you use. It takes an already
annotated neighbourhood and a catalogue of known architectures, and reports how
well the neighbourhood is explained.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(slots=True)
class Gene:
    gene_id: str
    family: str
    start: int
    end: int
    strand: int = 1

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(slots=True)
class Neighbourhood:
    """Genes flanking an anchor locus, on one contig."""

    contig_id: str
    anchor_family: str
    genes: list[Gene] = field(default_factory=list)
    taxon: str = ""

    def architecture(self) -> tuple[str, ...]:
        """Ordered family composition, the key used to match known systems."""
        return tuple(gene.family for gene in sorted(self.genes, key=lambda g: g.start))

    def partner_families(self) -> set[str]:
        return {gene.family for gene in self.genes if gene.family != self.anchor_family}


def architecture_novelty(
    neighbourhood: Neighbourhood, known_architectures: set[tuple[str, ...]]
) -> float:
    """0.0 when the exact architecture is catalogued, 1.0 when nothing matches.

    Intermediate values come from the best partial overlap with any known
    architecture, so a system that shares half its components with a described
    one does not read as fully novel.
    """
    architecture = neighbourhood.architecture()
    if not architecture:
        return math.nan
    if architecture in known_architectures:
        return 0.0
    observed = set(architecture)
    best = 0.0
    for known in known_architectures:
        candidate = set(known)
        union = observed | candidate
        if union:
            best = max(best, len(observed & candidate) / len(union))
    return 1.0 - best


def unexplained_fraction(neighbourhood: Neighbourhood, known_families: set[str]) -> float:
    """Fraction of flanking genes belonging to no described family."""
    partners = neighbourhood.partner_families()
    if not partners:
        return math.nan
    return sum(family not in known_families for family in partners) / len(partners)


def cross_genome_support(
    neighbourhoods: list[Neighbourhood], min_shared: int = 2
) -> dict[tuple[str, ...], int]:
    """Count how many distinct taxa show each architecture.

    A single occurrence of a strange arrangement is usually an assembly
    artifact. The same arrangement in several unrelated genomes is the thing
    worth spending a model's attention on.
    """
    seen: dict[tuple[str, ...], set[str]] = {}
    for neighbourhood in neighbourhoods:
        architecture = neighbourhood.architecture()
        if len(architecture) < min_shared:
            continue
        seen.setdefault(architecture, set()).add(neighbourhood.taxon or neighbourhood.contig_id)
    return {architecture: len(taxa) for architecture, taxa in seen.items()}


def neighbourhood_features(
    neighbourhood: Neighbourhood,
    known_architectures: set[tuple[str, ...]],
    known_families: set[str],
    support: dict[tuple[str, ...], int] | None = None,
) -> dict[str, float]:
    support = support or {}
    return {
        "neighbour_count": float(len(neighbourhood.genes)),
        "partner_family_count": float(len(neighbourhood.partner_families())),
        "architecture_novelty": architecture_novelty(neighbourhood, known_architectures),
        "unexplained_partner_fraction": unexplained_fraction(neighbourhood, known_families),
        "cross_genome_support": float(support.get(neighbourhood.architecture(), 1)),
    }
