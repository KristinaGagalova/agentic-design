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

## Running against the execution VM

Jobs run where the weights and cores are. Edit here, ship the tree, execute there:

```bash
bash env/sync.sh push                            # local tree -> VM
bash env/sync.sh run config/runs/smoke.yaml      # execute on the VM
bash env/sync.sh pull                            # results -> ./results
```

Override the destination with `REMOTE`, `SSH_KEY`, `REMOTE_ROOT`. This is
deliberately a thin shim, not the end state -- see *Execution model* below.

## Watching a run

RFdiffusion logs every diffusion timestep, counting down to 1 per design, and
`results/<name>/run.log` is written as the job runs rather than on exit:

```bash
bash env/sync.sh progress ubq_binder   # designs started, last timestep, staleness
bash env/sync.sh watch ubq_binder      # follow the log
```

Two things to know about long runs:

- **Re-running a config does not redo work.** RFdiffusion's cautious mode skips
  any design whose output PDB already exists, so a repeat run exits 0 having
  generated nothing. `run_design()` reports this as `skipped_existing`; delete
  the run directory to force regeneration.
- A binder run is hours. Launch it under `tmux` or `nohup` on the VM rather
  than holding an SSH connection open for the duration.

## Design notes

- **Nothing large is committed.** Weights, PDB outputs, and `.trb` files are
  gitignored; the repo stays clonable.
- **Paths live in config, not code.** Moving from a CPU VM to a rented GPU is
  a one-file edit.
- **Agents read `.trb`, not PDB text.** The `.trb` is the authoritative
  record of what was designed.
- **Validation is not optional.** A backbone that has not been refolded and
  checked is not a candidate.
- **Workarounds live in this repo, not in the RFdiffusion checkout.** CPU-only
  boxes need one patch (see below); it ships as `cpu_shim.py` so the upstream
  install stays pristine and the fix survives a rebuild.

## Execution model

`build_command()` constructs the RFdiffusion invocation; `run_design()` executes
it. Keeping those separate is what makes the execution target swappable. Today
`env/sync.sh` ships the tree to a VM and runs `backend: local` there. The
intended end state is a `remote` backend that dispatches over SSH from the local
repo, with no sync step.

## CPU-only hosts

SE3Transformer annotates its hot paths with `torch.cuda.nvtx.range`. On a
CPU-only torch build those raise `NVTX functions not installed` partway through
the first forward pass. `agentic_design.cpu_shim` replaces the NVTX push/pop
primitives with no-ops -- they are profiling markers and do not affect results --
then hands off to the real entrypoint. It is injected only when
`config/paths.yaml` says `device: cpu`, so a GPU host runs unshimmed.

## Status

The diffusion stage is wired up and verified end to end on CPU. ProteinMPNN and
structure-prediction stages in `workflows/design_campaign.py` are still stubs,
and no binder has been designed yet.

- **[docs/handoff.md](docs/handoff.md)** -- start here: goals, architecture,
  current status, next steps, and the failure modes that present as success.
- [docs/first-run.md](docs/first-run.md) -- the first end-to-end run: timings,
  motif verification, and the four defects it exposed.
