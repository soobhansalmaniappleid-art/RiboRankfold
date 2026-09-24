"""PDB reading for RNA candidate structures.

Candidate models in this project are frequently backbone traces rather than
all-atom structures, so residues are represented by a single atom chosen from
``REPRESENTATIVE_ATOMS`` in priority order.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

REPRESENTATIVE_ATOMS = ("C4'", "C4*", "P")


def residue_number(value: str) -> int:
    """Parse a PDB residue sequence number, tolerating malformed fields."""
    try:
        return int(value)
    except ValueError:
        return 0


def representative_chains(path: Path) -> dict[str, np.ndarray]:
    """Return one representative coordinate per residue, grouped by chain."""
    residues: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    with Path(path).open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith(("ATOM", "HETATM")) or len(line) < 54:
                continue
            atom = line[12:16].strip()
            if atom not in REPRESENTATIVE_ATOMS:
                continue
            chain = line[21].strip() or "_"
            resseq = line[22:26].strip()
            icode = line[26].strip()
            try:
                coord = np.array(
                    [float(line[30:38]), float(line[38:46]), float(line[46:54])],
                    dtype=float,
                )
            except ValueError:
                continue
            residues.setdefault((chain, resseq, icode), {})[atom] = coord

    chains: dict[str, list[np.ndarray]] = {}
    for key in sorted(residues, key=lambda item: (item[0], residue_number(item[1]), item[2])):
        atoms = residues[key]
        chosen = next((atoms[name] for name in REPRESENTATIVE_ATOMS if name in atoms), None)
        if chosen is not None:
            chains.setdefault(key[0], []).append(chosen)
    return {chain: np.asarray(coords, dtype=float) for chain, coords in chains.items()}


def representative_coords(path: Path) -> np.ndarray:
    """Return all representative coordinates, chains concatenated in chain order."""
    chains = representative_chains(path)
    if not chains:
        return np.asarray([], dtype=float)
    coords: list[np.ndarray] = []
    for chain_id in sorted(chains):
        coords.extend(chains[chain_id])
    return np.asarray(coords, dtype=float)


def infer_candidate_source(candidate_id: str) -> str:
    """Map a candidate filename stem to the generator that produced it."""
    lowered = candidate_id.lower()
    prefixes = {
        "casp": "casp",
        "rhofold": "rhofold",
        "drfold": "drfold",
        "farfar": "farfar2",
        "template": "template",
        "decoy": "synthetic_decoy",
        "native": "native",
    }
    for prefix, source in prefixes.items():
        if lowered.startswith(prefix):
            return source
    return "unknown"
