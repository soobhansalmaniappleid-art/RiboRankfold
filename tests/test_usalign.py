"""US-align adapter tests.

These run without the real binary: a stub script stands in for it, so parsing,
failure handling and frame wiring are covered on any machine. Tests that need
the real thing are skipped unless RIBORANK_USALIGN points at it.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from riborank.usalign import (
    UsalignError,
    find_usalign,
    parse_outfmt2,
    run_usalign,
    score_frame,
)

HEADER = "#PDBchain1\tPDBchain2\tTM1\tTM2\tRMSD\tID1\tID2\tIDali\tL1\tL2\tLali"
ROW = "cand.pdb:0\tnative.pdb:B\t0.5644\t0.4210\t3.14\t0.812\t0.812\t0.862\t69\t82\t65"


def make_stub(tmp_path: Path, stdout: str, exit_code: int = 0) -> Path:
    script = tmp_path / "stub_usalign"
    body = stdout.replace("\\", "\\\\").replace("'", "'\\''")
    script.write_text(f"#!/bin/sh\nprintf '%s' '{body}'\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


# -- parsing ------------------------------------------------------------


def test_parses_a_normal_row():
    result = parse_outfmt2(f"{HEADER}\n{ROW}\n")
    assert result.tm_score == pytest.approx(0.4210)  # TM2, normalised by native
    assert result.rmsd == pytest.approx(3.14)
    assert result.aligned_length == 65
    assert result.candidate_length == 69
    assert result.native_length == 82
    assert result.native_chain == "B"


def test_normalisation_uses_the_native_not_the_candidate():
    """TM1 and TM2 differ when lengths differ; we must report TM2."""
    result = parse_outfmt2(f"{HEADER}\n{ROW}\n")
    assert result.tm_score != pytest.approx(0.5644)


def test_coverage_is_relative_to_the_native():
    assert parse_outfmt2(f"{HEADER}\n{ROW}\n").coverage == pytest.approx(65 / 82)


def test_banner_before_the_table_is_ignored():
    noisy = f" *** US-align banner ***\n\n{HEADER}\n{ROW}\n\n#Total CPU time is 0.01 seconds\n"
    assert parse_outfmt2(noisy).aligned_length == 65


def test_missing_table_raises():
    with pytest.raises(UsalignError, match="no US-align table"):
        parse_outfmt2("some unrelated error text")


def test_missing_data_row_raises():
    with pytest.raises(UsalignError, match="no alignment row"):
        parse_outfmt2(HEADER + "\n")


def test_unexpected_columns_raise():
    with pytest.raises(UsalignError, match="unexpected US-align columns"):
        parse_outfmt2("#PDBchain1\tPDBchain2\tTM1\n" + "a\tb\t0.5\n")


def test_non_numeric_field_raises_instead_of_guessing():
    broken = ROW.replace("0.4210", "n/a")
    with pytest.raises(UsalignError, match="non-numeric"):
        parse_outfmt2(f"{HEADER}\n{broken}\n")


def test_short_row_raises():
    with pytest.raises(UsalignError, match="malformed"):
        parse_outfmt2(f"{HEADER}\ncand.pdb:0\tnative.pdb:B\t0.5\n")


# -- process handling ---------------------------------------------------


def test_run_uses_the_stub(tmp_path):
    stub = make_stub(tmp_path, f"{HEADER}\n{ROW}\n")
    result = run_usalign(tmp_path / "c.pdb", tmp_path / "n.pdb", stub)
    assert result.tm_score == pytest.approx(0.4210)


def test_nonzero_exit_raises(tmp_path):
    stub = make_stub(tmp_path, "", exit_code=3)
    with pytest.raises(UsalignError, match="exit 3"):
        run_usalign(tmp_path / "c.pdb", tmp_path / "n.pdb", stub)


def test_find_usalign_reports_how_to_build_it(monkeypatch):
    monkeypatch.delenv("RIBORANK_USALIGN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(UsalignError, match="make USalign"):
        find_usalign()


def test_find_usalign_honours_the_environment(tmp_path, monkeypatch):
    stub = make_stub(tmp_path, "")
    monkeypatch.setenv("RIBORANK_USALIGN", str(stub))
    assert find_usalign() == stub.resolve()


# -- frame wiring -------------------------------------------------------


def frame_with(has_native: list[bool], tmp_path: Path) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": [f"c{i}" for i in range(len(has_native))],
            "candidate_path": [str(tmp_path / f"c{i}.pdb") for i in range(len(has_native))],
            "native_path": [str(tmp_path / "n.pdb") if h else "" for h in has_native],
            "has_native": has_native,
        }
    )


def test_score_frame_adds_columns(tmp_path):
    stub = make_stub(tmp_path, f"{HEADER}\n{ROW}\n")
    scored = score_frame(frame_with([True, True], tmp_path), stub)
    assert list(scored["usalign_tm"]) == pytest.approx([0.4210, 0.4210])
    assert list(scored["usalign_aligned"]) == [65.0, 65.0]


def test_rows_without_a_native_are_nan(tmp_path):
    stub = make_stub(tmp_path, f"{HEADER}\n{ROW}\n")
    scored = score_frame(frame_with([True, False], tmp_path), stub)
    assert scored["usalign_tm"].iloc[0] == pytest.approx(0.4210)
    assert np.isnan(scored["usalign_tm"].iloc[1])


def test_a_failure_is_nan_not_zero(tmp_path):
    """A broken alignment must not rank above a genuinely poor structure."""
    stub = make_stub(tmp_path, "catastrophe", 1)
    scored = score_frame(frame_with([True], tmp_path), stub)
    assert np.isnan(scored["usalign_tm"].iloc[0])


def test_failures_can_be_made_fatal(tmp_path):
    stub = make_stub(tmp_path, "catastrophe", 1)
    with pytest.raises(UsalignError):
        score_frame(frame_with([True], tmp_path), stub, on_error="raise")


def test_bad_on_error_value_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="on_error"):
        score_frame(frame_with([True], tmp_path), make_stub(tmp_path, ""), on_error="ignore")


def test_the_original_frame_is_not_mutated(tmp_path):
    stub = make_stub(tmp_path, f"{HEADER}\n{ROW}\n")
    original = frame_with([True], tmp_path)
    score_frame(original, stub)
    assert "usalign_tm" not in original.columns


# -- against the real binary, when available ----------------------------

REAL = os.environ.get("RIBORANK_USALIGN")
CASP = Path("data/casp15_rna")
HAVE_REAL = bool(REAL) and (CASP / "natives").is_dir()


@pytest.mark.skipif(not HAVE_REAL, reason="needs RIBORANK_USALIGN and CASP15 data")
def test_real_binary_self_alignment_is_one():
    native = next((CASP / "natives").glob("*.pdb"))
    result = run_usalign(native, native, Path(REAL))
    assert result.tm_score == pytest.approx(1.0, abs=1e-3)
    assert result.rmsd == pytest.approx(0.0, abs=1e-3)


@pytest.mark.skipif(not HAVE_REAL, reason="needs RIBORANK_USALIGN and CASP15 data")
def test_real_binary_scores_are_in_range():
    native = CASP / "natives" / "R1107_7QR4.pdb"
    candidates = sorted((CASP / "candidates" / "R1107").glob("*.pdb"))[:5]
    for candidate in candidates:
        result = run_usalign(candidate, native, Path(REAL))
        assert 0.0 <= result.tm_score <= 1.0
        assert result.rmsd >= 0.0


# -- label selection ----------------------------------------------------


def label_frame(**columns) -> pd.DataFrame:
    base = {"candidate_id": ["a", "b"], "true_rmsd": [1.0, 2.0]}
    base.update(columns)
    return pd.DataFrame(base)


def test_official_tm_score_is_preferred_when_present():
    from riborank.pipeline import apply_labels

    frame = apply_labels(label_frame(true_tm_like=[0.1, 0.2], usalign_tm=[0.8, 0.9],
                                     usalign_rmsd=[3.0, 4.0]))
    assert (frame["label_metric"] == "usalign_tm").all()
    assert list(frame["true_quality"]) == pytest.approx([0.8, 0.9])
    assert list(frame["true_rmsd_used"]) == pytest.approx([3.0, 4.0])


def test_falls_back_to_the_internal_metric():
    from riborank.pipeline import apply_labels

    frame = apply_labels(label_frame(true_tm_like=[0.1, 0.2]))
    assert (frame["label_metric"] == "true_tm_like").all()
    assert list(frame["true_quality"]) == pytest.approx([0.1, 0.2])


def test_an_all_nan_usalign_column_does_not_count_as_available():
    from riborank.pipeline import apply_labels

    frame = apply_labels(label_frame(true_tm_like=[0.1, 0.2], usalign_tm=[np.nan, np.nan]))
    assert (frame["label_metric"] == "true_tm_like").all()


def test_requesting_an_uncomputed_metric_raises_instead_of_downgrading():
    from riborank.pipeline import apply_labels

    with pytest.raises(ValueError, match="no values were computed"):
        apply_labels(label_frame(true_tm_like=[0.1, 0.2]), prefer="usalign_tm")


def test_unknown_metric_is_rejected():
    from riborank.pipeline import apply_labels

    with pytest.raises(ValueError, match="unknown label metric"):
        apply_labels(label_frame(true_tm_like=[0.1, 0.2]), prefer="vibes")


def test_no_metric_at_all_raises():
    from riborank.pipeline import apply_labels

    with pytest.raises(ValueError, match="no label metric available"):
        apply_labels(pd.DataFrame({"candidate_id": ["a"]}))


def test_coverage_counts_unlabelled_candidates():
    from riborank.pipeline import label_coverage

    frame = pd.DataFrame(
        {
            "target_id": ["A", "A", "A", "B", "B"],
            "usalign_tm": [0.5, np.nan, 0.3, 0.9, 0.8],
        }
    )
    coverage = label_coverage(frame).set_index("target_id")
    assert coverage.loc["A", "unlabelled"] == 1
    assert coverage.loc["A", "coverage"] == pytest.approx(2 / 3)
    assert coverage.loc["B", "coverage"] == pytest.approx(1.0)


def test_coverage_lists_the_worst_target_first():
    from riborank.pipeline import label_coverage

    frame = pd.DataFrame(
        {"target_id": ["good", "bad"], "usalign_tm": [0.5, np.nan]}
    )
    assert label_coverage(frame).iloc[0]["target_id"] == "bad"
