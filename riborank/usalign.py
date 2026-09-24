"""Official US-align TM-score.

This replaces ``riborank.geometry.tm_like``, which applied the TM-score formula
to a single global RMSD and systematically understated quality (docs/METRICS.md).
US-align optimises the alignment and sums a per-residue term, which is the
metric CASP and the RNA structure literature report.

The binary is not vendored. Build it once:

    git clone --depth 1 https://github.com/pylelab/USalign
    cd USalign && make USalign

then point ``RIBORANK_USALIGN`` at the result, or pass ``--usalign PATH``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

#: Columns of ``USalign -outfmt 2``.
_HEADER = (
    "#PDBchain1", "PDBchain2", "TM1", "TM2", "RMSD", "ID1", "ID2", "IDali", "L1", "L2", "Lali",
)


class UsalignError(RuntimeError):
    """US-align could not be run, or produced output we refuse to guess at."""


@dataclass(frozen=True, slots=True)
class UsalignResult:
    """One candidate-versus-native alignment.

    ``tm_score`` is normalised by the **reference** (the native), which is the
    convention US-align itself recommends and the only one comparable across
    candidates of differing length.
    """

    tm_score: float
    rmsd: float
    aligned_length: int
    candidate_length: int
    native_length: int
    seq_identity: float
    candidate_chain: str = ""
    native_chain: str = ""

    @property
    def coverage(self) -> float:
        if not self.native_length:
            return float("nan")
        return self.aligned_length / self.native_length


def find_usalign(explicit: str | Path | None = None) -> Path:
    """Locate the binary: explicit path, then ``RIBORANK_USALIGN``, then PATH."""
    candidates = [explicit, os.environ.get("RIBORANK_USALIGN"), "USalign", "usalign"]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
        found = shutil.which(str(candidate))
        if found:
            return Path(found).resolve()
    raise UsalignError(
        "US-align binary not found. Build it with "
        "`git clone --depth 1 https://github.com/pylelab/USalign && cd USalign && make USalign`, "
        "then set RIBORANK_USALIGN or pass --usalign."
    )


def run_usalign(
    candidate_path: Path,
    native_path: Path,
    binary: Path,
    mol: str = "RNA",
    timeout: float = 300.0,
) -> UsalignResult:
    """Align one candidate against a native. The native is the reference."""
    command = [
        str(binary),
        str(candidate_path),
        str(native_path),
        "-mol", mol,
        "-outfmt", "2",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as error:
        raise UsalignError(f"US-align timed out on {candidate_path}") from error
    if completed.returncode != 0:
        raise UsalignError(
            f"US-align failed on {candidate_path} (exit {completed.returncode}): "
            f"{completed.stderr.strip()[:300]}"
        )
    return parse_outfmt2(completed.stdout, source=str(candidate_path))


def parse_outfmt2(stdout: str, source: str = "") -> UsalignResult:
    """Parse ``-outfmt 2`` output.

    Anything unexpected raises rather than returning a plausible-looking number:
    a silently wrong score is worse than a crash, because it becomes a label.
    """
    lines = [line for line in stdout.splitlines() if line.strip()]
    header = next((line for line in lines if line.startswith("#PDBchain1")), None)
    if header is None:
        raise UsalignError(f"no US-align table in output for {source}: {stdout[:200]!r}")
    columns = header.split("\t")
    if tuple(columns) != _HEADER:
        raise UsalignError(f"unexpected US-align columns for {source}: {columns}")

    data = lines[lines.index(header) + 1 :]
    if not data:
        raise UsalignError(f"US-align produced no alignment row for {source}")
    fields = data[0].split("\t")
    if len(fields) != len(_HEADER):
        raise UsalignError(f"malformed US-align row for {source}: {fields}")

    row = dict(zip(_HEADER, fields, strict=True))
    try:
        return UsalignResult(
            # TM2 is normalised by structure 2, which we always pass as the native.
            tm_score=float(row["TM2"]),
            rmsd=float(row["RMSD"]),
            aligned_length=int(row["Lali"]),
            candidate_length=int(row["L1"]),
            native_length=int(row["L2"]),
            seq_identity=float(row["IDali"]),
            candidate_chain=row["#PDBchain1"].rpartition(":")[2],
            native_chain=row["PDBchain2"].rpartition(":")[2],
        )
    except ValueError as error:
        raise UsalignError(f"non-numeric US-align field for {source}: {row}") from error


def score_frame(
    features,
    binary: Path,
    mol: str = "RNA",
    workers: int = 8,
    on_error: str = "nan",
):
    """Add official US-align columns to a feature frame.

    Adds ``usalign_tm``, ``usalign_rmsd``, ``usalign_aligned``,
    ``usalign_coverage`` and ``usalign_seq_id``. Rows without a native get NaN.

    ``on_error='nan'`` records a failed alignment as NaN and carries on;
    ``on_error='raise'`` stops. Failures are never silently scored as zero,
    which would rank a broken file above a genuinely poor structure.
    """
    if on_error not in {"nan", "raise"}:
        raise ValueError("on_error must be 'nan' or 'raise'")

    frame = features.copy()
    jobs = [
        (index, Path(row.candidate_path), Path(row.native_path))
        for index, row in zip(frame.index, frame.itertuples(index=False), strict=True)
        if bool(row.has_native) and str(row.native_path)
    ]

    def one(job):
        index, candidate_path, native_path = job
        try:
            return index, run_usalign(candidate_path, native_path, binary, mol=mol)
        except UsalignError:
            if on_error == "raise":
                raise
            return index, None

    results = {}
    if jobs:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            for index, result in pool.map(one, jobs):
                results[index] = result

    columns = {
        "usalign_tm": lambda r: r.tm_score,
        "usalign_rmsd": lambda r: r.rmsd,
        "usalign_aligned": lambda r: float(r.aligned_length),
        "usalign_coverage": lambda r: r.coverage,
        "usalign_seq_id": lambda r: r.seq_identity,
    }
    for name, extract in columns.items():
        frame[name] = [
            extract(results[index]) if results.get(index) is not None else np.nan
            for index in frame.index
        ]
    return frame
