#!/usr/bin/env bash
# Fetch and clean the demo target (1UBQ, ubiquitin) for the runs in
# demo/demo_configs.yaml.
#
#     bash demo/fetch_demo_target.sh
#
# Override with env vars: PDB_ID, CHAIN, TARGETS_DIR.
set -euo pipefail

PDB_ID="${PDB_ID:-1UBQ}"
CHAIN="${CHAIN:-A}"
TARGETS_DIR="${TARGETS_DIR:-/mnt/src/data/targets}"

raw="${TARGETS_DIR}/${PDB_ID}.pdb"
clean="${TARGETS_DIR}/${PDB_ID}_clean.pdb"

mkdir -p "$TARGETS_DIR"

if [[ ! -s "$raw" ]]; then
    curl -fsSL "https://files.rcsb.org/download/${PDB_ID}.pdb" -o "$raw"
fi

# Keep protein backbone/side-chain atoms for one chain only. HETATM records
# (waters, ligands) are dropped: RFdiffusion models protein, and leaving
# solvent in shifts the residue numbering the contig string depends on.
# Alternate conformations beyond the first would double-count a residue.
awk -v chain="$CHAIN" '
    /^ATOM/ && substr($0,22,1) == chain {
        altloc = substr($0,17,1)
        if (altloc == " " || altloc == "A") print
    }
' "$raw" > "$clean"

if [[ ! -s "$clean" ]]; then
    echo "error: no ATOM records for chain ${CHAIN} in ${raw}" >&2
    exit 1
fi

# TER/END close the chain. Padded to the 80-column PDB convention so the
# output matches what standard tools emit.
last=$(tail -1 "$clean")
printf 'TER   %5d      %3s %s%4d%54s\nEND%77s\n' \
    $(( $(awk 'END{print substr($0,7,5)+0}' "$clean") + 1 )) \
    "$(echo "$last" | cut -c18-20)" "$CHAIN" \
    "$(echo "$last" | cut -c23-26)" "" "" >> "$clean"

printf 'wrote %s (%d atoms, chain %s, residues %s-%s)\n' \
    "$clean" \
    "$(grep -c '^ATOM' "$clean")" \
    "$CHAIN" \
    "$(awk '/^ATOM/{print substr($0,23,4)+0}' "$clean" | head -1)" \
    "$(awk '/^ATOM/{print substr($0,23,4)+0}' "$clean" | tail -1)"
