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
