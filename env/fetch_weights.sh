#!/usr/bin/env bash
# Download RFdiffusion checkpoints. Resumable; safe to rerun.
# MINIMAL=1 fetches only the two checkpoints most runs need (~1.5 GB).
set -euo pipefail

SRC="${SRC:-/mnt/src}"
MODELS="$SRC/models"
BASE="http://files.ipd.uw.edu/pub/RFdiffusion"
mkdir -p "$MODELS" && cd "$MODELS"

CORE=(
  "6f5902ac237024bdd0c176cb93063dc4/Base_ckpt.pt"
  "e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt"
)
EXTRA=(
  "60f09a193fb5e5ccdc4980417708dbab/Complex_Fold_base_ckpt.pt"
  "74f51cfb8b440f50d70878e05361d8f0/InpaintSeq_ckpt.pt"
  "76d00716416567174cdb7ca96e208296/InpaintSeq_Fold_ckpt.pt"
  "5532d2e1f3a4738decd58b19d633b3c3/ActiveSite_ckpt.pt"
  "12fc204edeae5b57713c5ad7dcb97d39/Base_epoch8_ckpt.pt"
)

FILES=("${CORE[@]}")
[ "${MINIMAL:-0}" = "1" ] || FILES+=("${EXTRA[@]}")

for f in "${FILES[@]}"; do
  wget -c "$BASE/$f"
done

echo ">> checkpoints in $MODELS:"
ls -lh "$MODELS"
echo ">> any file under ~50M is a failed download; rerun to resume."
