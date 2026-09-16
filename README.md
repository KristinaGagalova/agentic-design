# agentic-design

Agentic orchestration of protein design workflows built on
[RFdiffusion](https://github.com/RosettaCommons/RFdiffusion).

RFdiffusion generates backbones. Turning those into candidates worth testing
means sequence design, structure prediction, and filtering -- a loop with
enough judgement in it to be worth handing to an agent. This repo wraps that
loop behind a stable interface so the orchestration logic stays independent
of where the models actually run.

## Layout

| Path | Purpose |
|------|---------|
| `env/` | Install scripts and pinned dependencies |
| `config/paths.yaml` | Machine-specific paths; override with `paths.local.yaml` |
| `config/runs/` | Declarative run specs, one YAML per job type |
| `src/agentic_design/` | Library: runner, `.trb` parsing, CLI |
| `agents/` | MCP server exposing the pipeline as tools, plus agent briefs |
| `workflows/` | Multi-stage campaign scripts |
| `data/` | Input PDBs and scaffold sets (committed) |
| `results/` | Run outputs (gitignored) |
| `tests/` | Tests that pass without GPU or weights |

## Quickstart

See [docs/INSTALL.md](docs/INSTALL.md). Once installed:

```bash
python -m agentic_design.cli config/runs/smoke.yaml --dry-run   # inspect
python -m agentic_design.cli config/runs/smoke.yaml             # run
```

## Design notes

- **Nothing large is committed.** Weights, PDB outputs, and `.trb` files are
  gitignored; the repo stays clonable.
- **Paths live in config, not code.** Moving from a CPU VM to a rented GPU is
  a one-file edit.
- **Agents read `.trb`, not PDB text.** The `.trb` is the authoritative
  record of what was designed.
- **Validation is not optional.** A backbone that has not been refolded and
  checked is not a candidate.

## Status

Early. The diffusion stage is wired up; ProteinMPNN and structure-prediction
stages in `workflows/design_campaign.py` are stubs.
