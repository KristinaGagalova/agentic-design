# agentic-design

A reusable framework for automating protein binder design against a target PDB,
built on RFdiffusion. Experiments execute on a remote CPU VM.

**For current status, open tasks, and next steps, read [docs/handoff.md](docs/handoff.md).**
This file holds only what stays true between sessions.

## Goals

Build a **reusable framework that automates designing high-quality proteins that
bind to a given target PDB**, with experiments executing on a remote VM.

Three horizons, deliberately ordered:

1. **Test the framework** — prove it runs end to end.
2. **Extract what is reusable** from that run.
3. **Make it drivable by any AI** over an OpenAI-compatible endpoint. Claude is
   the first driver; `agents/tools.py` (an MCP server) is the intended seam.

The reusable framework is the deliverable; an experiment is the forcing function
that proves it.

**Ordering matters.** Extraction comes *after* a working run, never before. Do
not build the generic multi-backend abstraction ahead of evidence — three of the
four defects found so far were invisible until something actually ran.

## Environment

Jobs run on the VM, not locally. There is no `rsync`, `pytest`, or GPU on the
Windows host.

**Connection details live in `project.env` at the repo root — gitignored, never
committed.** Copy `project.env.example` and fill it in; `env/sync.sh` sources it
and every command below reads from it, so no host or key path is written down in
this repo. Authentication is SSH key only; there is no password.

Do not take connection details from `~/.ssh/config`. Its entries for this
project are stale: one is a rebuilt host that fails key verification, another
times out, and the correct host is not listed there at all.

RFdiffusion, its venv (Python 3.10.12), and ~3.7 GB of checkpoints live under
`/mnt/src/`. The repo deploys to `$REMOTE_ROOT`.

## Commands

```bash
bash env/sync.sh push                                  # local tree -> VM
bash env/sync.sh run config/runs/<spec>.yaml           # execute on the VM
bash env/sync.sh run config/runs/<spec>.yaml --dry-run # print command only
bash env/sync.sh progress <run>                        # status of a running job
bash env/sync.sh watch <run>                           # follow its log
bash env/sync.sh pull                                  # results -> ./results
bash env/sync.sh test                                  # run the test suite on the VM
```

Tests run on the VM too — `push` first so the VM has your changes.

## Architecture

```
config/runs/*.yaml   declarative run specs, one per job type
      |
   cli.py            build_request(): named fields + nested blocks -> Hydra overrides
      |
 runner.py           build_command()  PURE, testable, no execution
                     run_design()     executes, streams log, summarizes
      |
   trb.py            parse .trb — the authoritative record of what was designed
validate.py          motif backbone RMSD (Kabsch) — verification, not reporting
      |
agents/tools.py      MCP server: diffuse / inspect_results / validate_motif
```

**Execution model — current vs intended.** Today `env/sync.sh` ships the tree to
the VM and runs `backend: local` there. This was chosen over cloning the repo on
the VM (blinds local tooling, creates two drifting copies) and over building the
SSH backend immediately (a day of work with silent-failure risk, spent before any
run had been proven). **The agreed long-term architecture is a `remote` SSH
backend inside `runner.py`**, dispatching from the local repo with no sync step.
`sync.sh` is scaffolding, not the design.

Known traps for that migration: `runner.py` resolves `input_pdb` against the
*local* `REPO_ROOT`; `summarize_dir()` reads `.trb` from a local path and would
silently return `[]`; contig strings contain spaces and brackets
(`[A1-76/0 50-65]`) and need `shlex.quote` once a remote shell re-parses them;
multi-hour runs need tmux or nohup, not a held connection.

## Invariants

- **`build_command()` stays pure.** It constructs the RFdiffusion invocation;
  `run_design()` executes it. That separation is what keeps the execution target
  swappable — the planned `remote` SSH backend depends on it. Keep execution
  concerns out.
- **Workarounds live in this repo, never as edits to the RFdiffusion checkout
  under `/mnt/src`.** A previous session hand-ran a target-prep step that was
  never captured; it had to be reconstructed from the output file. Anything done
  to make a run work belongs in version control.
- **GPU is the default and failures are loud.** `config/paths.yaml` sets
  `device: cuda` and a run aborts if no GPU is visible, rather than silently
  running 50-100x slower. CPU is an explicit opt-in in `config/paths.local.yaml`
  (gitignored), which also enables `cpu_shim`.
- **Trust the `.trb`, not the PDB text and not the exit code.** The `.trb` is the
  authoritative record of what was designed.
- **A backbone that has not been refolded and checked is not a candidate.**

## Failure modes that present as success

Exit code 0 means little here. Of the four defects found so far, three looked
like success:

1. **Cautious mode silently skips.** RFdiffusion refuses to overwrite an existing
   output PDB — it logs `(cautious mode) Skipping this design`, exits 0, and the
   stale designs get reported as fresh. Check `skipped_existing` in the result
   dict; delete the run directory to force regeneration. A run that finishes
   suspiciously fast is a red flag, not good news.
2. **Nested config blocks were dropped without error**, so runs completed with
   settings the YAML claimed were applied. Fixed, but confirm with `--dry-run`
   that a spec produces the overrides you expect.
3. **`summarize_dir()` reads `.trb` from a local path.** If execution ever moves
   remote without fixing this, it returns `[]` — reporting success with zero
   designs.
4. **CPU-only hosts crash inside the forward pass**, not at import:
   SE3Transformer imports `torch.cuda.nvtx.range` unguarded, raising
   `NVTX functions not installed` partway through inference, which reads like a
   model bug. `cpu_shim.py` handles it. This is the only genuine GPU-hardcoding
   in the inference path; everything else is properly guarded.

## Gotchas

- Runtime estimates in `demo/demo_configs.yaml` assume ~12 cores and are roughly
  20x pessimistic on this 32-core VM. Do not size decisions off them.
- A re-run truncates `run.log`, destroying the record of the original run.
  Unfixed.
