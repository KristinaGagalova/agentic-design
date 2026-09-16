#!/usr/bin/env bash
# =============================================================================
# Fetch and clean a small demo target for RFdiffusion testing.
#
# Default: 1UBQ (ubiquitin) -- 76 residues, single chain, 1.8 A, no ligands,
# no chain breaks. Small enough to run on CPU, and its Ile44 hydrophobic patch
# (L8 / I44 / V70) is a real, well-characterised binding surface, so binder
# hotspots are meaningful rather than arbitrary.
#
# Alternatives:
#   PDB_ID=1CRN  crambin, 46 res -- even smaller, but very hydrophobic and
#                disulfide-rich, so a poor binder target. Fine for motif tests.
#   PDB_ID=1L2Y  Trp-cage, 20 res -- NMR miniprotein, fastest possible check.
#
# Usage:
#   bash fetch_demo_target.sh
#   PDB_ID=1CRN CHAIN=A bash fetch_demo_target.sh
# =============================================================================

set -euo pipefail

SRC="${SRC:-/mnt/src}"
PDB_ID="${PDB_ID:-1UBQ}"
CHAIN="${CHAIN:-A}"
TARGET_DIR="${TARGET_DIR:-${SRC}/data/targets}"

mkdir -p "${TARGET_DIR}"
cd "${TARGET_DIR}"

RAW="${PDB_ID}.pdb"
CLEAN="${PDB_ID}_clean.pdb"

# ---- Download ---------------------------------------------------------------
if [ ! -s "${RAW}" ]; then
  echo "==> Downloading ${PDB_ID} from RCSB"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "https://files.rcsb.org/download/${PDB_ID}.pdb" -o "${RAW}" \
      || { echo "ERROR: download failed. Check the PDB ID." >&2; rm -f "${RAW}"; exit 1; }
  else
    wget -q "https://files.rcsb.org/download/${PDB_ID}.pdb" -O "${RAW}" \
    || { echo "ERROR: download failed. Check the PDB ID." >&2; rm -f "${RAW}"; exit 1; }
  fi
fi

# ---- Clean ------------------------------------------------------------------
# RFdiffusion wants protein atoms only: no waters, no hetero-atoms, no
# alternate locations, one chain. Waters in particular will be read as
# residues and silently corrupt the contig numbering.
echo "==> Cleaning: keeping chain ${CHAIN}, protein atoms only"
awk -v ch="${CHAIN}" '
  /^ATOM/ {
    altloc = substr($0, 17, 1)
    chain  = substr($0, 22, 1)
    if (chain == ch && (altloc == " " || altloc == "A")) print
  }
  /^TER/ { print }
' "${RAW}" > "${CLEAN}"
echo "END" >> "${CLEAN}"

# ---- Report -----------------------------------------------------------------
N_ATOMS=$(grep -c '^ATOM' "${CLEAN}" || true)
if [ "${N_ATOMS}" -eq 0 ]; then
  echo "ERROR: no protein atoms for chain ${CHAIN} in ${RAW}" >&2
  rm -f "${CLEAN}"
  exit 1
fi
N_RES=$(awk '/^ATOM/ {print substr($0,23,4)}' "${CLEAN}" | sort -un | wc -l)
FIRST_RES=$(awk '/^ATOM/ {print substr($0,23,4)}' "${CLEAN}" | head -1 | tr -d ' ')
LAST_RES=$(awk '/^ATOM/ {print substr($0,23,4)}' "${CLEAN}" | tail -1 | tr -d ' ')

cat <<EOF

==> Done: ${TARGET_DIR}/${CLEAN}
    chain:     ${CHAIN}
    atoms:     ${N_ATOMS}
    residues:  ${N_RES}  (numbered ${FIRST_RES}-${LAST_RES})

    Contig range for this target:  ${CHAIN}${FIRST_RES}-${LAST_RES}

    Check for gaps before trusting a contig -- RFdiffusion treats missing
    residues as chain breaks:
      python3 -c "
import sys
n=[int(l[22:26]) for l in open('${CLEAN}') if l.startswith('ATOM')]
u=sorted(set(n)); g=[(a,b) for a,b in zip(u,u[1:]) if b-a>1]
print('gaps:', g if g else 'none')"

EOF
