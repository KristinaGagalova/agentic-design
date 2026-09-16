"""Tests for motif verification. No GPU, weights, or RFdiffusion needed."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_design.validate import backbone_coords, kabsch_rmsd  # noqa: E402

PDB = """\
ATOM      1  N   LEU A  72      10.000  10.000  10.000  1.00  0.00           N
ATOM      2  CA  LEU A  72      11.000  10.000  10.000  1.00  0.00           C
ATOM      3  C   LEU A  72      12.000  10.000  10.000  1.00  0.00           C
ATOM      4  CB  LEU A  72      99.000  99.000  99.000  1.00  0.00           C
ATOM      5  N   ARG A  73      10.000  11.000  10.000  1.00  0.00           N
ATOM      6  CA  ARG A  73      11.000  11.500  10.000  1.00  0.00           C
ATOM      7  C   ARG A  73      12.000  11.000  10.500  1.00  0.00           C
"""


def test_backbone_coords_selects_only_n_ca_c(tmp_path):
    pdb = tmp_path / "t.pdb"
    pdb.write_text(PDB)
    coords = backbone_coords(pdb, [("A", 72), ("A", 73)])
    assert coords.shape == (6, 3)
    # The CB at (99,99,99) must not be picked up.
    assert coords.max() < 90


def test_backbone_coords_rejects_incomplete_residue(tmp_path):
    pdb = tmp_path / "t.pdb"
    pdb.write_text("ATOM      1  CA  LEU A  72      10.000  10.000  10.000\n")
    with pytest.raises(ValueError, match="missing backbone atom"):
        backbone_coords(pdb, [("A", 72)])


def test_rmsd_is_zero_under_rigid_motion():
    """Translation and rotation are not defects; the motif is placed, not deformed."""
    rng = np.random.default_rng(0)
    motif = rng.random((15, 3)) * 10
    theta = 0.7
    rotation = np.array([[np.cos(theta), -np.sin(theta), 0],
                         [np.sin(theta), np.cos(theta), 0],
                         [0, 0, 1]])
    assert kabsch_rmsd(motif, motif @ rotation.T + [5, -3, 12]) == pytest.approx(0, abs=1e-9)


def test_rmsd_detects_a_deformed_motif():
    rng = np.random.default_rng(0)
    motif = rng.random((15, 3)) * 10
    bent = motif.copy()
    bent[0] += 3.0
    assert kabsch_rmsd(motif, bent) > 0.5


def test_rmsd_does_not_accept_a_mirror_image():
    """Without a reflection guard, SVD would fit a mirrored motif as perfect."""
    rng = np.random.default_rng(1)
    motif = rng.random((15, 3)) * 10
    assert kabsch_rmsd(motif, motif * [1, 1, -1]) > 0.5


def test_parse_hotspots_accepts_the_run_spec_string():
    from agentic_design.validate import parse_hotspots
    assert parse_hotspots("[A8,A44,A70]") == [("A", 8), ("A", 44), ("A", 70)]
    assert parse_hotspots(["A8", "B12"]) == [("A", 8), ("B", 12)]


def test_check_motif_explains_itself_on_a_binder_trb(tmp_path, monkeypatch):
    """Binder runs leave con_ref_pdb_idx empty; that used to surface as IndexError."""
    from agentic_design import validate
    monkeypatch.setattr(validate, "read_trb",
                        lambda _: {"con_ref_pdb_idx": [], "con_hal_pdb_idx": []})
    with pytest.raises(ValueError, match="check_binder"):
        validate.check_motif(tmp_path / "x.trb", tmp_path / "x.pdb", tmp_path / "r.pdb")


COMPLEX = """\
ATOM      1  N   LEU A   8       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  LEU A   8       1.000   0.000   0.000  1.00  0.00           C
ATOM      3  C   LEU A   8       2.000   0.000   0.000  1.00  0.00           C
ATOM      4  N   ILE A  44      20.000   0.000   0.000  1.00  0.00           N
ATOM      5  CA  ILE A  44      21.000   0.000   0.000  1.00  0.00           C
ATOM      6  C   ILE A  44      22.000   0.000   0.000  1.00  0.00           C
ATOM      7  N   GLY B   1       1.000   3.000   0.000  1.00  0.00           N
ATOM      8  CA  GLY B   1       2.000   3.000   0.000  1.00  0.00           C
ATOM      9  C   GLY B   1       3.000   3.000   0.000  1.00  0.00           C
"""


def test_check_binder_separates_contacted_from_missed_hotspots(tmp_path):
    from agentic_design.validate import check_binder
    pdb = tmp_path / "d.pdb"
    pdb.write_text(COMPLEX)

    r = check_binder(pdb, pdb, "[A8,A44]")
    # Binder sits ~3 A from A8 and ~18 A from A44.
    assert r["hotspots_contacted"] == ["A8"]
    assert r["hotspot_min_distance"]["A8"] < 5.0
    assert r["hotspot_min_distance"]["A44"] > 15.0
    assert r["binder_residues"] == 1
    # Compared against itself, the target cannot have moved.
    assert r["target_backbone_rmsd"] == pytest.approx(0, abs=1e-9)


def test_check_binder_rejects_a_single_chain_design(tmp_path):
    from agentic_design.validate import check_binder
    pdb = tmp_path / "d.pdb"
    pdb.write_text(PDB)
    with pytest.raises(ValueError, match="no chain B"):
        check_binder(pdb, pdb, "[A72]")
