"""A blind benchmark: RT-associated loci, one of which hides an array.

The question put to the engine is deliberately generic:

    Survey these reverse-transcriptase-associated genomic systems and identify
    unusual, previously uncharacterised systems worth investigating.

Nothing anywhere in the corpus, the question, or the scoring mentions repeats,
arrays, CRISPR, spacing or periodicity. Putting the answer in the question is
the easiest way to build a demo that proves nothing.

The corpus is **synthetic**. It is not Anthropic's data, which has not been
published in a form that could be downloaded, and it must never be described as
a reproduction of their result. What it can honestly test is whether this
engine's generic machinery surfaces an unusual locus without being told what
kind of unusual to look for.

## Why the confounders matter

A corpus of ordinary loci plus one array is trivial: anything that notices
*any* irregularity wins. So the corpus contains loci built specifically to
defeat the lazy heuristics:

* **Low-complexity** regions — a naive "low entropy is interesting" rule fires
  on these, and they are biologically mundane.
* **Homopolymer runs** — likewise, and they are often sequencing artifacts.
* **Biased composition** — extreme GC, which shifts entropy without meaning
  anything.
* **Short dispersed motifs** — a recurring motif at *irregular* spacing, which
  is what most genomes contain and what a real array must be distinguished from.
* **Known architectures** — real systems that are already described, which a
  novelty-seeking system must rank *down* rather than up.

A method that ranks the planted locus above the ordinary loci but below the
confounders has not succeeded; it has just found the most irregular sequence.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

# The planted architecture. Named neutrally on purpose: nothing downstream may
# key on these strings.
PLANTED_UNIT = "CATGTGTATCGCATGTTACGTACGT"

KNOWN_ARCHITECTURES: tuple[tuple[str, ...], ...] = (
    ("RT", "capsid"),
    ("RT", "integrase", "capsid"),
    ("RT", "maturase"),
    ("RT", "helicase", "capsid"),
)
KNOWN_FAMILIES: frozenset[str] = frozenset(
    {"RT", "capsid", "integrase", "maturase", "helicase", "terminase", "portal"}
)


@dataclass(slots=True)
class Locus:
    """One RT-associated locus, as the engine will receive it."""

    locus_id: str
    sequence: str
    genes: list[dict[str, Any]]
    taxon: str
    #: Ground truth, used ONLY by the scorer. Never passed to the engine.
    kind: str = "ordinary"

    def to_engine_input(self) -> dict[str, Any]:
        """Exactly what the engine may see. Note the absence of ``kind``."""
        return {
            "locus_id": self.locus_id,
            "sequence": self.sequence,
            "genes": self.genes,
            "anchor_family": "RT",
            "taxon": self.taxon,
        }


def _dna(n: int, rng: random.Random, gc: float = 0.5) -> str:
    """Random sequence with a target GC fraction."""
    weights = [(1 - gc) / 2, gc / 2, gc / 2, (1 - gc) / 2]
    return "".join(rng.choices("ATGC", weights=weights, k=n))


def _genes(families: list[str]) -> list[dict[str, Any]]:
    return [
        {"gene_id": f"g{i}", "family": family, "start": i * 900, "end": i * 900 + 780}
        for i, family in enumerate(families)
    ]


def build_corpus(
    n_ordinary: int = 40,
    n_planted: int = 3,
    seed: int = 20260924,
) -> list[Locus]:
    """Build the blind corpus. Order is shuffled so position carries nothing."""
    rng = random.Random(seed)
    loci: list[Locus] = []

    # Ordinary: an RT beside an unnamed partner, nothing special in the DNA.
    for i in range(n_ordinary):
        loci.append(
            Locus(
                locus_id=f"L{i:04d}",
                sequence=_dna(rng.randint(1400, 2200), rng, gc=rng.uniform(0.38, 0.62)),
                genes=_genes(["RT", rng.choice(["orfA", "orfB", "orfC"])]),
                taxon=f"tax_{rng.randint(1, 60)}",
                kind="ordinary",
            )
        )

    # Known systems: real, described, and must be ranked DOWN by a
    # novelty-seeking method rather than up.
    for i, architecture in enumerate(KNOWN_ARCHITECTURES * 2):
        loci.append(
            Locus(
                locus_id=f"K{i:04d}",
                sequence=_dna(rng.randint(1600, 2000), rng),
                genes=_genes(list(architecture)),
                taxon=f"tax_{rng.randint(1, 60)}",
                kind="known_system",
            )
        )

    # Confounders: irregular in ways that have nothing to do with the planted
    # signal. These defeat "lowest entropy wins".
    for i in range(4):
        body = _dna(400, rng) + "AT" * 350 + _dna(400, rng)
        loci.append(
            Locus(f"C_lowcomp_{i}", body, _genes(["RT", "orfD"]), f"tax_{rng.randint(1, 60)}",
                   "confounder_low_complexity")
        )
    for i in range(3):
        body = _dna(500, rng) + "A" * 300 + _dna(500, rng)
        loci.append(
            Locus(f"C_homopol_{i}", body, _genes(["RT", "orfE"]), f"tax_{rng.randint(1, 60)}",
                   "confounder_homopolymer")
        )
    for i in range(3):
        loci.append(
            Locus(f"C_gcbias_{i}", _dna(1800, rng, gc=0.78), _genes(["RT", "orfF"]),
                   f"tax_{rng.randint(1, 60)}", "confounder_gc_bias")
        )
    for i in range(4):
        # A motif that recurs at IRREGULAR spacing: the thing a real array has
        # to be told apart from.
        motif = _dna(22, rng)
        body = _dna(300, rng)
        # Bimodal gaps, so the spacing coefficient of variation stays high. A
        # uniform range occasionally produces a near-regular run by chance,
        # which would make this a second planted locus rather than a decoy.
        for step in range(7):
            gap = rng.randint(40, 90) if step % 2 else rng.randint(350, 500)
            body += motif + _dna(gap, rng)
        loci.append(
            Locus(f"C_dispersed_{i}", body + _dna(300, rng), _genes(["RT", "orfG"]),
                  f"tax_{rng.randint(1, 60)}", "confounder_dispersed_motif")
        )

    # The planted loci: a conserved unit at near-constant spacing, beside an RT
    # with partners that match no described architecture, recurring across
    # unrelated taxa.
    for i in range(n_planted):
        copies = rng.randint(9, 14)
        period = rng.choice([120, 140, 165])
        body = _dna(400, rng)
        for _ in range(copies):
            unit = PLANTED_UNIT
            if rng.random() < 0.3:  # real arrays are not perfectly identical
                position = rng.randrange(len(unit))
                unit = unit[:position] + rng.choice("ACGT") + unit[position + 1 :]
            body += unit + _dna(period - len(PLANTED_UNIT), rng)
        loci.append(
            Locus(
                locus_id=f"P{i:04d}",
                sequence=body + _dna(400, rng),
                genes=_genes(["RT", "orfX", "orfY"]),
                taxon=f"planted_tax_{i}",
                kind="planted",
            )
        )

    rng.shuffle(loci)
    return loci


@dataclass(slots=True)
class Corpus:
    loci: list[Locus] = field(default_factory=list)

    @classmethod
    def build(cls, **kwargs: Any) -> Corpus:
        return cls(loci=build_corpus(**kwargs))

    @property
    def planted_ids(self) -> set[str]:
        return {locus.locus_id for locus in self.loci if locus.kind == "planted"}

    @property
    def confounder_ids(self) -> set[str]:
        return {locus.locus_id for locus in self.loci if locus.kind.startswith("confounder")}

    @property
    def known_ids(self) -> set[str]:
        return {locus.locus_id for locus in self.loci if locus.kind == "known_system"}

    def engine_inputs(self) -> list[dict[str, Any]]:
        """What the engine receives: no ground truth of any kind."""
        return [locus.to_engine_input() for locus in self.loci]

    def kinds(self) -> dict[str, str]:
        return {locus.locus_id: locus.kind for locus in self.loci}


#: The only instruction the engine is given. Deliberately generic.
RESEARCH_QUESTION = (
    "Survey these reverse-transcriptase-associated genomic systems and identify "
    "unusual, previously uncharacterised systems worth investigating."
)
