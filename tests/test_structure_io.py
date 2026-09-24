from __future__ import annotations

import numpy as np
import pytest

from riborank.structure import (
    infer_candidate_source,
    representative_chains,
    representative_coords,
    residue_number,
)
from tests.conftest import write_pdb


def test_roundtrip_of_coordinates(tmp_path, helix):
    path = write_pdb(tmp_path / "x.pdb", helix)
    assert np.allclose(representative_coords(path), helix, atol=1e-3)


def test_chains_are_kept_separate(tmp_path, helix):
    first = write_pdb(tmp_path / "a.pdb", helix[:10], chain="A").read_text()
    second = write_pdb(tmp_path / "b.pdb", helix[10:20], chain="B").read_text()
    path = tmp_path / "two.pdb"
    path.write_text(first.replace("END\n", "") + second, encoding="utf-8")

    chains = representative_chains(path)
    assert sorted(chains) == ["A", "B"]
    assert len(chains["A"]) == 10
    assert len(chains["B"]) == 10


def test_non_representative_atoms_are_ignored(tmp_path):
    path = tmp_path / "o.pdb"
    path.write_text(
        "ATOM      1  OP1  A A   1       1.000   2.000   3.000  1.00  0.00\n"
        "ATOM      2  C4'  A A   1       4.000   5.000   6.000  1.00  0.00\n"
        "END\n",
        encoding="utf-8",
    )
    coords = representative_coords(path)
    assert coords.shape == (1, 3)
    assert np.allclose(coords[0], [4.0, 5.0, 6.0])


def test_malformed_coordinate_lines_are_skipped(tmp_path):
    path = tmp_path / "bad.pdb"
    path.write_text(
        "ATOM      1  C4'  A A   1         NaNX    ????    ????  1.00  0.00\n"
        "ATOM      2  C4'  A A   2       4.000   5.000   6.000  1.00  0.00\n"
        "END\n",
        encoding="utf-8",
    )
    assert representative_coords(path).shape == (1, 3)


def test_missing_atoms_give_empty_result(tmp_path):
    path = tmp_path / "empty.pdb"
    path.write_text("HEADER nothing here\nEND\n", encoding="utf-8")
    assert representative_coords(path).size == 0
    assert representative_chains(path) == {}


def test_residue_number_tolerates_junk():
    assert residue_number("42") == 42
    assert residue_number("") == 0
    assert residue_number("12A") == 0


@pytest.mark.parametrize(
    ("candidate_id", "expected"),
    [
        ("casp15_R1107TS232_1", "casp"),
        ("rhofold_model_1", "rhofold"),
        ("drfold_x", "drfold"),
        ("farfar2_y", "farfar2"),
        ("template_z", "template"),
        ("decoy_1", "synthetic_decoy"),
        ("native", "native"),
        ("something_else", "unknown"),
    ],
)
def test_candidate_source_inference(candidate_id, expected):
    assert infer_candidate_source(candidate_id) == expected
