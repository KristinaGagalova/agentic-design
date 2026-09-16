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

## Device selection

`config/paths.yaml` defaults to `device: cuda`, and a run aborts if no GPU is
visible rather than falling back silently -- a silent fallback turns a
20-minute job into a multi-hour one. A CPU-only host must opt in:

```bash
echo 'device: cpu' >> config/paths.local.yaml
```

That also enables `agentic_design.cpu_shim`, which is required on CPU: see
*CPU-only hosts* in the README for why.

## Moving to a GPU

Point `config/paths.local.yaml` at the GPU machine's install, and remove any
`device: cpu` line so the `cuda` default applies. Nothing in `src/` changes.
