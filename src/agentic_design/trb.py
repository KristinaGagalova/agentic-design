"""Parse RFdiffusion .trb outputs.

The .trb is the machine-readable record of what was actually designed --
contig mapping, sampled length, per-residue masks. Agents should read this
rather than scraping the PDB.
"""
from pathlib import Path
import pickle


def read_trb(path: str | Path) -> dict:
    with open(path, "rb") as fh:
        return pickle.load(fh)


def summarize(path: str | Path) -> dict:
    """Flatten a .trb into JSON-safe fields an agent can reason over."""
    trb = read_trb(path)
    mask = trb.get("mask_1d", [])
    return {
        "design": Path(path).stem,
        "length": len(mask) if len(mask) else None,
        "contigs": trb.get("config", {}).get("contigmap", {}).get("contigs"),
        "n_motif_residues": int(sum(bool(m) for m in mask)) if len(mask) else None,
        "sampled_mask": trb.get("sampled_mask"),
    }


def summarize_dir(directory: str | Path) -> list[dict]:
    return [summarize(p) for p in sorted(Path(directory).glob("*.trb"))]
