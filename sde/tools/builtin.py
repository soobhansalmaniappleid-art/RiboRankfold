"""The tools the engine ships with.

Each is a thin adapter over code that already exists and is tested elsewhere:
`discovery.features` for sequence and repeat analysis, `riborank` for structural
work. The engine owns none of the science — it owns which questions get asked,
in what order, and at what cost.

Tools not implemented here are declared as *absent* rather than faked. Calling
one raises with the command needed to install it, because a stub that returns
plausible numbers is far worse than a tool that is missing.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from discovery.features.neighborhood import (
    Gene,
    Neighbourhood,
    architecture_novelty,
    unexplained_fraction,
)
from discovery.features.repeats import find_repeat_arrays, repeat_features
from discovery.features.sequence import sequence_features
from sde.registry import ToolCost, ToolRegistry

registry = ToolRegistry()


@registry.tool(
    "sequence_stats",
    ToolCost.TRIVIAL,
    "Length, GC, entropy and low-complexity fraction of a sequence.",
    requires=("sequence",),
    produces=("length", "gc_content", "entropy_1mer", "low_complexity_fraction"),
)
def _sequence_stats(inputs: dict[str, Any]) -> dict[str, Any]:
    return sequence_features(str(inputs["sequence"]))


@registry.tool(
    "repeat_scan",
    ToolCost.CHEAP,
    "Detect tandem repeat arrays: copy count, unit length, period regularity.",
    requires=("sequence",),
    produces=("repeat_copy_count", "repeat_mean_period", "repeat_period_cv"),
)
def _repeat_scan(inputs: dict[str, Any]) -> dict[str, Any]:
    return repeat_features(str(inputs["sequence"]))


@registry.tool(
    "repeat_detail",
    ToolCost.CHEAP,
    "The consensus unit and positions of each detected repeat array.",
    requires=("sequence",),
    produces=("arrays",),
)
def _repeat_detail(inputs: dict[str, Any]) -> dict[str, Any]:
    arrays = find_repeat_arrays(str(inputs["sequence"]))
    return {
        "arrays": [
            {
                "start": a.start,
                "end": a.end,
                "copies": a.copy_count,
                "unit_length": a.unit_length,
                "period": round(a.mean_period, 2),
                "consensus": a.consensus,
            }
            for a in arrays
        ]
    }


@registry.tool(
    "neighbourhood_novelty",
    ToolCost.CHEAP,
    "How poorly a gene neighbourhood is explained by known architectures.",
    requires=("genes", "anchor_family", "known_architectures"),
    produces=("architecture_novelty", "unexplained_partner_fraction"),
)
def _neighbourhood_novelty(inputs: dict[str, Any]) -> dict[str, Any]:
    genes = [
        Gene(
            gene_id=str(g.get("gene_id", i)),
            family=str(g["family"]),
            start=int(g.get("start", i * 1000)),
            end=int(g.get("end", i * 1000 + 800)),
        )
        for i, g in enumerate(inputs["genes"])
    ]
    neighbourhood = Neighbourhood(
        contig_id=str(inputs.get("contig_id", "")),
        anchor_family=str(inputs["anchor_family"]),
        genes=genes,
        taxon=str(inputs.get("taxon", "")),
    )
    known = {tuple(a) for a in inputs["known_architectures"]}
    families = set(inputs.get("known_families") or [])
    return {
        "architecture_novelty": architecture_novelty(neighbourhood, known),
        "unexplained_partner_fraction": unexplained_fraction(neighbourhood, families),
    }


@registry.tool(
    "structure_rank",
    ToolCost.EXPENSIVE,
    "Rank RNA 3D candidate structures for a target with RiboRank.",
    requires=("candidates_root", "target_id"),
    produces=("ranking", "ranker_caveat"),
)
def _structure_rank(inputs: dict[str, Any]) -> dict[str, Any]:
    """RiboRank as an instrument of the engine.

    It returns its own caveat alongside the ranking. On real prediction pools no
    RiboRank scoring mode beats random selection, so an agent must not read this
    ordering as evidence of quality. Shipping the caveat inside the tool output
    is the only way to be sure it travels with the number.
    """
    from riborank.pipeline import add_labels, build_features, build_manifest
    from riborank.ranking import rank_by_score
    from riborank.scoring import add_scores

    root = Path(str(inputs["candidates_root"]))
    target = str(inputs["target_id"])
    manifest = build_manifest(root)
    manifest = manifest[manifest["target_id"] == target]
    if manifest.empty:
        raise ValueError(f"no candidates for target {target!r} under {root}")

    features = add_scores(add_labels(build_features(manifest)))
    mode = str(inputs.get("mode", "score_plausibility"))
    ranked = rank_by_score(features, mode).head(int(inputs.get("top_k", 5)))
    return {
        "ranking": list(ranked["candidate_id"]),
        "ranker_caveat": (
            "RiboRank scoring modes do not beat random selection on real "
            "prediction pools. Treat this ordering as a pool reduction with no "
            "demonstrated skill, not as evidence of structural quality."
        ),
    }


@registry.tool(
    "structure_compare",
    ToolCost.MODERATE,
    "Official US-align TM-score between two structures.",
    requires=("candidate_path", "reference_path"),
    produces=("tm_score", "rmsd", "aligned_length"),
)
def _structure_compare(inputs: dict[str, Any]) -> dict[str, Any]:
    from riborank.usalign import find_usalign, run_usalign

    binary = find_usalign(inputs.get("usalign"))
    result = run_usalign(
        Path(str(inputs["candidate_path"])),
        Path(str(inputs["reference_path"])),
        binary,
        mol=str(inputs.get("mol", "RNA")),
    )
    return {
        "tm_score": result.tm_score,
        "rmsd": result.rmsd,
        "aligned_length": result.aligned_length,
        "coverage": result.coverage,
    }


# -- declared but not implemented ---------------------------------------
#
# These are the tools the architecture calls for and this engine does not have.
# They are registered so an agent can see they exist as concepts and so the gap
# is visible in the catalogue, and they raise with the install command. A stub
# returning plausible numbers would be indistinguishable from a working tool in
# the report, which is the one outcome worth preventing.

_MISSING: dict[str, tuple[ToolCost, str, str, tuple[str, ...]]] = {
    "mmseqs_search": (
        ToolCost.MODERATE,
        "Sequence similarity search against a large database.",
        "conda install -c bioconda mmseqs2",
        ("sequence",),
    ),
    "mmseqs_cluster": (
        ToolCost.EXPENSIVE,
        "Cluster millions of sequences into families.",
        "conda install -c bioconda mmseqs2",
        ("sequences",),
    ),
    "hmmsearch": (
        ToolCost.MODERATE,
        "Profile HMM search, the step that makes a billion-sequence space tractable.",
        "conda install -c bioconda hmmer",
        ("sequence",),
    ),
    "infernal_scan": (
        ToolCost.MODERATE,
        "Scan for structured RNA families (Rfam covariance models).",
        "conda install -c bioconda infernal",
        ("sequence",),
    ),
    "rnafold": (
        ToolCost.MODERATE,
        "Secondary structure and folding free energy.",
        "conda install -c bioconda viennarna",
        ("sequence",),
    ),
    "literature_search": (
        ToolCost.EXTERNAL,
        "Search the literature for a described system matching this architecture.",
        "requires network access and a literature API key",
        ("query",),
    ),
    "taxonomy_lookup": (
        ToolCost.EXTERNAL,
        "Taxonomic distribution of a family, for horizontal-transfer signals.",
        "requires network access to NCBI",
        ("family",),
    ),
}


def _make_missing(name: str, install: str):
    def _missing(inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            f"tool {name!r} is declared but not installed in this engine. "
            f"To enable it: {install}. It deliberately raises rather than "
            "returning placeholder values."
        )

    return _missing


for _name, (_cost, _summary, _install, _requires) in _MISSING.items():
    registry.tool(
        _name,
        _cost,
        f"[NOT INSTALLED] {_summary}",
        requires=_requires,
        produces=(),
    )(_make_missing(_name, _install))


def available_tools() -> list[str]:
    """Tools that are actually implemented, not merely declared."""
    return [
        spec.name
        for spec in registry.catalogue()
        if not spec.summary.startswith("[NOT INSTALLED]")
    ]


def external_binary_present(name: str) -> bool:
    return shutil.which(name) is not None
