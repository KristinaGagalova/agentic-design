#!/usr/bin/env bash
# CPU-only install of RFdiffusion into a venv on a large disk.
# Override the location with:  SRC=/mnt/src bash env/install.sh
set -euo pipefail

SRC="${SRC:-/mnt/src}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ">> using SRC=$SRC"
sudo mkdir -p "$SRC"/{tmp,models,rfdiff-venv}
sudo chown -R "$USER:$USER" "$SRC"

export TMPDIR="$SRC/tmp"
export PIP_CACHE_DIR="$SRC/pip-cache"

# --- RFdiffusion source ---
if [ ! -d "$SRC/RFdiffusion" ]; then
  git clone https://github.com/RosettaCommons/RFdiffusion.git "$SRC/RFdiffusion"
fi

# --- venv ---
python3 -m venv "$SRC/rfdiff-venv"
# shellcheck disable=SC1091
source "$SRC/rfdiff-venv/bin/activate"
pip install --upgrade pip

# --- deps (CPU builds) ---
pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu
pip install --no-cache-dir dgl==1.1.2 -f https://data.dgl.ai/wheels/repo.html
pip install --no-cache-dir -r "$REPO_ROOT/env/requirements-cpu.txt"

cd "$SRC/RFdiffusion"
pip install --no-deps -e env/SE3Transformer
pip install --no-deps -e .

# --- this repo, editable ---
pip install --no-deps -e "$REPO_ROOT"

# --- weights ---
rm -rf "$SRC/RFdiffusion/models"
ln -s "$SRC/models" "$SRC/RFdiffusion/models"
bash "$REPO_ROOT/env/fetch_weights.sh"

echo ">> done. activate with: source $SRC/rfdiff-venv/bin/activate"
