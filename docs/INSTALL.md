# Installation

CPU-only, with everything on a large disk (`/mnt/src` by default).

```bash
git clone https://github.com/KristinaGagalova/agentic-design.git
cd agentic-design
SRC=/mnt/src bash env/install.sh
source /mnt/src/rfdiff-venv/bin/activate
python -m agentic_design.cli config/runs/smoke.yaml
```

## Notes

- `env/install.sh` keeps pip's temp and cache directories on `$SRC` so a
  small root filesystem does not run out of space mid-install.
- Checkpoints total ~5 GB. `MINIMAL=1 bash env/fetch_weights.sh` fetches
  only the two most-used ones.
- Python 3.12+ has no DGL wheel. Install 3.10 alongside if needed:
  `sudo apt install python3.10-venv` and point the venv at it.
- CPU inference is roughly 50-100x slower than an A100. Treat this install
  as a development environment and rent a GPU for production runs.

## Moving to a GPU

Edit `config/paths.local.yaml` to point at the GPU machine's install and set
`device: cuda`. Nothing in `src/` should need to change.
