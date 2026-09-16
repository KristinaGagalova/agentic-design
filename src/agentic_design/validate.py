"""Check that a design is what it was asked to be.

RFdiffusion reports what it intended to do, but reporting is not verification:
a run can exit 0, write the right contig into the .trb, and still have moved the
target or missed the surface it was aimed at. These checks read coordinates.

Two problem shapes, two entry points. Motif scaffolding holds a few residues and
builds around them -- use `check_motif`. Binder design holds a whole target chain
and grows a second chain against it -- use `check_binder`.
"""
import re
from pathlib import Path

import numpy as np

from .trb import read_trb

BACKBONE = ("N", "CA", "C")


def _atoms(pdb: str | Path, chain: str) -> tuple[np.ndarray, np.ndarray]:
    """Heavy-atom coordinates and their residue numbers for one chain."""
    coords, resnums = [], []
    for line in Path(pdb).read_text().splitlines():
        if line.startswith("ATOM") and line[21] == chain:
            coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
            resnums.append(int(line[22:26]))
    return np.array(coords), np.array(resnums)


def parse_hotspots(spec: str | list) -> list[tuple[str, int]]:
    """'[A8,A44,A70]' -> [('A', 8), ('A', 44), ('A', 70)].

    Accepts the same string the run spec feeds to ppi.hotspot_res, so a check
    can be driven straight from the config that produced the design.
    """
    if isinstance(spec, str):
        spec = re.findall(r"[A-Za-z]\d+", spec)
    return [(s[0], int(s[1:])) for s in spec]


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
    """Compare a scaffolded motif as built against the motif as supplied."""
    meta = read_trb(trb)
    if not len(meta.get("con_ref_pdb_idx", [])):
        raise ValueError(
            f"{trb} records no scaffolded motif (con_ref_pdb_idx is empty). "
            "Binder runs hold a whole target chain instead of scaffolding a "
            "motif, and RFdiffusion leaves this mapping empty for them -- "
            "use check_binder() for those."
        )
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


def check_binder(
    design_pdb: str | Path,
    reference_pdb: str | Path,
    hotspot_res: str | list,
    target_chain: str = "A",
    binder_chain: str = "B",
    contact_cutoff: float = 5.0,
) -> dict:
    """Did the binder land on the surface it was aimed at, and was the target held?

    Hotspots bias RFdiffusion, they do not constrain it, so a run can succeed
    mechanically while the binder engages the wrong face. Two things decide
    whether a design is worth carrying forward: the target must be unchanged
    (otherwise the interface is against a structure that does not exist), and
    the binder must actually contact the hotspots.
    """
    target_xyz, target_res = _atoms(design_pdb, target_chain)
    binder_xyz, binder_res = _atoms(design_pdb, binder_chain)
    if not len(binder_xyz):
        raise ValueError(f"{design_pdb}: no chain {binder_chain}; is this a binder design?")

    shared = [(target_chain, int(r)) for r in sorted(set(target_res))]
    target_rmsd = kabsch_rmsd(
        backbone_coords(reference_pdb, shared), backbone_coords(design_pdb, shared)
    )

    distances = np.linalg.norm(binder_xyz[:, None, :] - target_xyz[None, :, :], axis=2)
    contacts = {}
    for chain, num in parse_hotspots(hotspot_res):
        if chain != target_chain:
            continue
        columns = target_res == num
        if not columns.any():
            raise ValueError(f"{design_pdb}: hotspot {chain}{num} not in chain {target_chain}")
        contacts[f"{chain}{num}"] = round(float(distances[:, columns].min()), 2)

    buried = int((distances < contact_cutoff).any(axis=1).sum())
    return {
        "design": Path(design_pdb).stem,
        "binder_residues": len(set(binder_res)),
        "target_backbone_rmsd": round(target_rmsd, 4),
        "hotspot_min_distance": contacts,
        "hotspots_contacted": sorted(k for k, v in contacts.items() if v < contact_cutoff),
        "interface_atoms": buried,
        "interface_fraction": round(buried / len(binder_xyz), 4),
    }
