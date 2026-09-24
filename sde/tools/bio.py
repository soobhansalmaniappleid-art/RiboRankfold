"""Real bioinformatics tools, replacing the declared-but-absent stubs.

Three of the tools the architecture calls for are now genuinely implemented:

* ``gene_predict`` — Prodigal via `pyrodigal`. Real ORF calling.
* ``hmmsearch`` — HMMER3 via `pyhmmer`. Real profile search. This is the step
  that makes a billion-sequence space tractable, and its absence was the
  honest reason this engine could investigate candidates but not find them.
* ``mmseqs_search`` / ``mmseqs_cluster`` — the real MMseqs2 binary, when one is
  on PATH or at ``$SDE_MMSEQS``.

Nothing here fabricates a result. A tool whose backend is missing raises with
the command that would install it, exactly as the stubs did, because a
plausible-looking number is indistinguishable from a real one in a report.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sde.registry import ToolCost, ToolRegistry


class BackendMissing(RuntimeError):
    """A tool's backend is not installed."""


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


# -- gene prediction ----------------------------------------------------


def gene_predict(inputs: dict[str, Any]) -> dict[str, Any]:
    """Call genes on a nucleotide sequence with Prodigal.

    ``meta=True`` (the default) uses metagenomic mode, which is the right
    choice for a contig of unknown provenance and the only safe default when
    the caller has not said what the sequence is.
    """
    try:
        import pyrodigal
    except ImportError as error:  # pragma: no cover - exercised by absence
        raise BackendMissing("gene_predict needs `pip install pyrodigal`") from error

    sequence = str(inputs["sequence"])
    gene_finder = pyrodigal.GeneFinder(meta=bool(inputs.get("meta", True)))
    genes = gene_finder.find_genes(sequence.encode())
    records = [
        {
            "gene_id": f"orf{index}",
            "start": int(gene.begin),
            "end": int(gene.end),
            "strand": int(gene.strand),
            "partial": bool(gene.partial_begin or gene.partial_end),
            "protein": gene.translate(),
        }
        for index, gene in enumerate(genes, start=1)
    ]
    lengths = [record["end"] - record["start"] for record in records]
    return {
        "genes": records,
        "gene_count": float(len(records)),
        "coding_density": float(sum(lengths) / len(sequence)) if sequence else 0.0,
        "mean_gene_length": float(sum(lengths) / len(lengths)) if lengths else 0.0,
    }


# -- profile search -----------------------------------------------------


def hmmsearch(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search proteins against HMM profiles with HMMER3.

    Accepts ``proteins`` (a list of sequences, or of records carrying one) and
    ``hmm_paths``. Returns the significant hits and, importantly, a count of
    proteins with **no** hit: an unannotated neighbour is the signal that
    matters when looking for a system nothing describes.
    """
    try:
        from pyhmmer import hmmsearch as _hmmsearch
        from pyhmmer.easel import Alphabet, TextSequence
        from pyhmmer.plan7 import HMMFile
    except ImportError as error:  # pragma: no cover
        raise BackendMissing("hmmsearch needs `pip install pyhmmer`") from error

    raw = inputs["proteins"]
    proteins: list[tuple[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, dict):
            sequence = item.get("protein") or item.get("sequence")
            name = str(item.get("gene_id", f"p{index}"))
        else:
            sequence, name = str(item), f"p{index}"
        if sequence:
            proteins.append((name, str(sequence).rstrip("*")))
    if not proteins:
        return {"hits": [], "hit_count": 0.0, "unannotated_fraction": float("nan")}

    alphabet = Alphabet.amino()
    digital = [
        TextSequence(name=name.encode(), sequence=sequence).digitize(alphabet)
        for name, sequence in proteins
    ]

    paths = inputs.get("hmm_paths") or default_hmm_paths()
    if not paths:
        raise BackendMissing(
            "hmmsearch needs HMM profiles; pass hmm_paths or set $SDE_HMM_DIR"
        )

    hits_out: list[dict[str, Any]] = []
    annotated: set[str] = set()
    threshold = float(inputs.get("evalue", 1e-5))
    for path in paths:
        with HMMFile(path) as handle:
            profiles = [hmm for hmm in handle if str(hmm.alphabet) == str(alphabet)]
        if not profiles:
            continue
        for top_hits in _hmmsearch(profiles, digital):
            for hit in top_hits:
                if hit.evalue > threshold:
                    continue
                name = _text(hit.name)
                annotated.add(name)
                hits_out.append(
                    {
                        "protein": name,
                        "profile": _text(top_hits.query.name),
                        "evalue": float(hit.evalue),
                        "score": float(hit.score),
                    }
                )

    return {
        "hits": sorted(hits_out, key=lambda h: h["evalue"])[:200],
        "hit_count": float(len(hits_out)),
        "annotated_protein_count": float(len(annotated)),
        "unannotated_fraction": float(1.0 - len(annotated) / len(proteins)),
    }


def default_hmm_paths() -> list[str]:
    """HMM profiles from ``$SDE_HMM_DIR``, if one is configured."""
    directory = os.environ.get("SDE_HMM_DIR")
    if not directory or not Path(directory).is_dir():
        return []
    return sorted(str(path) for path in Path(directory).glob("*.hmm"))


# -- MMseqs2 ------------------------------------------------------------


def find_mmseqs() -> str:
    for candidate in (os.environ.get("SDE_MMSEQS"), "mmseqs"):
        if not candidate:
            continue
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
        found = shutil.which(candidate)
        if found:
            return found
    raise BackendMissing(
        "mmseqs not found. Build it: git clone --depth 1 "
        "https://github.com/soedinglab/MMseqs2 && cmake -DCMAKE_BUILD_TYPE=Release .. "
        "&& make, then set $SDE_MMSEQS."
    )


def _write_fasta(records: list[Any], path: Path) -> int:
    lines = []
    for index, item in enumerate(records, start=1):
        if isinstance(item, dict):
            sequence = item.get("protein") or item.get("sequence") or ""
            name = str(item.get("gene_id", f"s{index}"))
        else:
            sequence, name = str(item), f"s{index}"
        if sequence:
            lines.append(f">{name}\n{sequence}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def mmseqs_cluster(inputs: dict[str, Any]) -> dict[str, Any]:
    """Cluster sequences with MMseqs2, the step that shrinks a huge space."""
    binary = find_mmseqs()
    sequences = inputs["sequences"]
    identity = float(inputs.get("min_seq_id", 0.5))
    coverage = float(inputs.get("coverage", 0.8))

    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        fasta = root / "in.fasta"
        count = _write_fasta(sequences, fasta)
        if count < 2:
            return {"cluster_count": float(count), "clusters": [], "sequences": float(count)}
        completed = subprocess.run(
            [
                binary, "easy-cluster", str(fasta), str(root / "out"), str(root / "tmp"),
                "--min-seq-id", str(identity), "-c", str(coverage),
                "--threads", str(inputs.get("threads", 2)), "-v", "1",
            ],
            capture_output=True, text=True, timeout=float(inputs.get("timeout", 900)),
        )
        if completed.returncode != 0:
            raise RuntimeError(f"mmseqs easy-cluster failed: {completed.stderr[-400:]}")
        clusters: dict[str, list[str]] = {}
        tsv = root / "out_cluster.tsv"
        for line in tsv.read_text(encoding="utf-8").splitlines():
            if "\t" not in line:
                continue
            representative, member = line.split("\t", 1)
            clusters.setdefault(representative, []).append(member)

    sizes = sorted((len(v) for v in clusters.values()), reverse=True)
    return {
        "sequences": float(count),
        "cluster_count": float(len(clusters)),
        "largest_cluster": float(sizes[0]) if sizes else 0.0,
        "singleton_fraction": (
            float(sum(1 for s in sizes if s == 1) / len(sizes)) if sizes else float("nan")
        ),
        "clusters": [
            {"representative": key, "size": len(value)}
            for key, value in sorted(clusters.items(), key=lambda kv: -len(kv[1]))[:50]
        ],
    }


def mmseqs_search(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search query sequences against a target set with MMseqs2."""
    binary = find_mmseqs()
    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        query, target = root / "q.fasta", root / "t.fasta"
        n_query = _write_fasta(inputs["queries"], query)
        n_target = _write_fasta(inputs["targets"], target)
        if not n_query or not n_target:
            return {"hit_count": 0.0, "hits": []}
        completed = subprocess.run(
            [
                binary, "easy-search", str(query), str(target), str(root / "hits.m8"),
                str(root / "tmp"), "--threads", str(inputs.get("threads", 2)), "-v", "1",
            ],
            capture_output=True, text=True, timeout=float(inputs.get("timeout", 900)),
        )
        if completed.returncode != 0:
            raise RuntimeError(f"mmseqs easy-search failed: {completed.stderr[-400:]}")
        rows = []
        for line in (root / "hits.m8").read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 11:
                rows.append(
                    {
                        "query": parts[0],
                        "target": parts[1],
                        "identity": float(parts[2]),
                        "evalue": float(parts[10]),
                    }
                )
    matched = {row["query"] for row in rows}
    return {
        "hit_count": float(len(rows)),
        "matched_query_fraction": float(len(matched) / n_query) if n_query else float("nan"),
        "hits": sorted(rows, key=lambda r: r["evalue"])[:200],
    }


def register_real_tools(registry: ToolRegistry) -> list[str]:
    """Replace the absent stubs with working implementations.

    Only registers what the machine can actually run, so the catalogue keeps
    telling the truth about which tools exist.
    """
    installed: list[str] = []
    specs = [
        ("gene_predict", ToolCost.MODERATE, "Call genes on a nucleotide sequence (Prodigal).",
         ("sequence",), ("genes", "gene_count", "coding_density"), gene_predict, "pyrodigal"),
        ("hmmsearch", ToolCost.MODERATE, "Search proteins against HMM profiles (HMMER3).",
         ("proteins",), ("hits", "unannotated_fraction"), hmmsearch, "pyhmmer"),
        ("mmseqs_cluster", ToolCost.EXPENSIVE, "Cluster sequences into families (MMseqs2).",
         ("sequences",), ("cluster_count", "singleton_fraction"), mmseqs_cluster, "mmseqs"),
        ("mmseqs_search", ToolCost.MODERATE, "Search sequences against a target set (MMseqs2).",
         ("queries", "targets"), ("hit_count",), mmseqs_search, "mmseqs"),
    ]
    for name, cost, summary, requires, produces, function, backend in specs:
        if not _backend_available(backend):
            continue
        if name in registry:
            registry._tools.pop(name)  # replace the declared-but-absent stub
        registry.tool(name, cost, summary, requires=requires, produces=produces)(function)
        installed.append(name)
    return installed


def _backend_available(backend: str) -> bool:
    if backend == "mmseqs":
        try:
            find_mmseqs()
        except BackendMissing:
            return False
        return True
    try:
        __import__(backend)
    except ImportError:
        return False
    return True
