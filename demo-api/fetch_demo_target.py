"""Portable counterpart to demo/fetch_demo_target.sh for Windows cmd and WSL.

    python demo-api/fetch_demo_target.py

Uses only the standard library. Scientific defaults match the shared demo.
"""
import argparse
import os
from pathlib import Path
import re
import urllib.request


def clean_chain(text: str, chain: str) -> tuple[str, list[int]]:
    atoms = []
    seen = set()
    for line in text.splitlines():
        if line.startswith("ENDMDL"):
            break  # NMR structures: use the first model only.
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        if line[21] != chain or line[16] not in (" ", "A"):
            continue
        identity = (line[22:27], line[12:16])
        if identity not in seen:
            seen.add(identity)
            atoms.append(line[:16] + " " + line[17:])
    if not atoms:
        raise ValueError(f"no protein atoms for chain {chain}")
    residues = sorted({int(line[22:26]) for line in atoms})
    for residue in residues:
        names = {line[12:16].strip() for line in atoms if int(line[22:26]) == residue}
        if not {"N", "CA", "C"}.issubset(names):
            raise ValueError(f"residue {chain}{residue} lacks N/CA/C backbone atoms")
    return "\n".join(atoms) + "\nTER\nEND\n", residues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdb-id", default=os.environ.get("PDB_ID", "1UBQ"))
    parser.add_argument("--chain", default=os.environ.get("CHAIN", "A"))
    parser.add_argument("--output-dir", type=Path, default=Path(os.environ.get(
        "TARGET_DIR", str(Path(__file__).resolve().parents[1] / "data" / "inputs"))))
    args = parser.parse_args(argv)
    pdb_id = args.pdb_id.upper()
    if not re.fullmatch(r"[A-Z0-9]{4}", pdb_id) or not re.fullmatch(r"[A-Za-z0-9]", args.chain):
        parser.error("use a four-character PDB ID and a one-character chain ID")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = args.output_dir / f"{pdb_id}.pdb"
    if raw.exists() and raw.stat().st_size:
        text = raw.read_text()
    else:
        with urllib.request.urlopen(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=60) as response:
            text = response.read().decode("utf-8")
    cleaned, residues = clean_chain(text, args.chain)
    if pdb_id == "1UBQ" and args.chain == "A" and residues != list(range(1, 77)):
        raise ValueError("the ubiquitin demo requires contiguous chain A residues 1-76")
    raw.write_text(text)
    destination = args.output_dir / f"{pdb_id}_clean.pdb"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(cleaned)
    temporary.replace(destination)
    gaps = [(a, b) for a, b in zip(residues, residues[1:]) if b != a + 1]
    print(f"Wrote {destination.resolve()}")
    print(f"Chain {args.chain}: {len(residues)} residues, {residues[0]}-{residues[-1]}; gaps: {gaps or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
