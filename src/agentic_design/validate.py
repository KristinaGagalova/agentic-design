"""Check that a motif-scaffolding run preserved the motif it was given.

RFdiffusion reports which residues it held fixed, but reporting is not
verification: a run can exit 0, write the right contig into the .trb, and still
have moved the motif. This compares the actual coordinates.
"""
from pathlib import Path

import numpy as np

from .trb import read_trb

BACKBONE = ("N", "CA", "C")


def backbone_coords(pdb: str | Path, residues: list[tuple[str, int]]) -> np.ndarray:
    """Backbone N/CA/C coordinates for the given (chain, resnum) pairs, in order."""
    wanted = {(chain, num): {} for chain, num in residues}
    for line in Path(pdb).read_text().splitlines():
        if not line.startswith("ATOM"):
            continue
        key = (line[21], int(line[22:26]))
        if key not in wanted:
            continue
        atom = line[12:16].strip()
        if atom in BACKBONE:
            wanted[key][atom] = (float(line[30:38]), float(line[38:46]), float(line[46:54]))

    coords = []
    for key in residues:
        for atom in BACKBONE:
            if atom not in wanted[key]:
                raise ValueError(f"{pdb}: residue {key} is missing backbone atom {atom}")
            coords.append(wanted[key][atom])
    return np.array(coords)


def kabsch_rmsd(p: np.ndarray, q: np.ndarray) -> float:
    """RMSD after optimal superposition. Rigid-body placement is not a defect."""
    p = p - p.mean(axis=0)
    q = q - q.mean(axis=0)
    v, _, wt = np.linalg.svd(p.T @ q)
    # Guard against a reflection, which would fit a mirror image of the motif.
    d = np.sign(np.linalg.det(v @ wt))
    rotation = v @ np.diag([1.0, 1.0, d]) @ wt
    return float(np.sqrt(((p @ rotation - q) ** 2).sum() / len(p)))


def check_motif(trb: str | Path, design_pdb: str | Path, reference_pdb: str | Path) -> dict:
    """Compare the motif as built against the motif as supplied."""
    meta = read_trb(trb)
    ref_idx = [(c, int(n)) for c, n in meta["con_ref_pdb_idx"]]
    hal_idx = [(c, int(n)) for c, n in meta["con_hal_pdb_idx"]]

    rmsd = kabsch_rmsd(
        backbone_coords(reference_pdb, ref_idx),
        backbone_coords(design_pdb, hal_idx),
    )
    return {
        "design": Path(design_pdb).stem,
        "n_motif_residues": len(ref_idx),
        "reference_residues": [f"{c}{n}" for c, n in ref_idx],
        "design_residues": [f"{c}{n}" for c, n in hal_idx],
        "motif_backbone_rmsd": round(rmsd, 4),
    }
