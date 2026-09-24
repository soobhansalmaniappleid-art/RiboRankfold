from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def write_pdb(path: Path, coords: np.ndarray, chain: str = "A", atom: str = "C4'") -> Path:
    """Write representative-atom coordinates as a minimal PDB file."""
    lines = []
    for index, (x, y, z) in enumerate(coords, start=1):
        # Fixed-width PDB ATOM record; column indices are 0-based here.
        record = list(" " * 80)
        record[0:6] = "ATOM  "
        record[6:11] = f"{index:5d}"
        record[12:16] = f"{atom:<4s}"
        record[17:20] = "  A"
        record[21] = chain
        record[22:26] = f"{index:4d}"
        record[30:38] = f"{x:8.3f}"
        record[38:46] = f"{y:8.3f}"
        record[46:54] = f"{z:8.3f}"
        record[54:66] = "  1.00  0.00"
        lines.append("".join(record).rstrip())
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def helix() -> np.ndarray:
    """A deterministic helical backbone trace with ~6 A steps."""
    t = np.linspace(0.0, 6.0 * np.pi, 40)
    return np.stack([10.0 * np.cos(t), 10.0 * np.sin(t), 1.5 * t], axis=1)


@pytest.fixture
def make_pdb(tmp_path: Path):
    def _make(name: str, coords: np.ndarray, chain: str = "A") -> Path:
        return write_pdb(tmp_path / name, coords, chain=chain)

    return _make
