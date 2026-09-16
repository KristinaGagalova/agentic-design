# First end-to-end run — 2026-09-16

Bringing the framework from "scaffolded but never executed" to a verified
RFdiffusion run driven entirely through the CLI, on the CPU VM.

## Starting state

The repo described a working pipeline that had never run. The target PDB
existed on the VM but the script that produced it did not exist in git, and
`/mnt/src/outputs` was absent — so no design had ever completed. Four gaps
stood between `demo/demo_configs.yaml` and the code meant to consume it:

- `demo/fetch_demo_target.sh` was referenced but missing.
- `demo_configs.yaml` is a six-document YAML stream; `cli.py` used single-document
  `yaml.safe_load` and could not read it.
- `DesignRequest.extra` existed but nothing populated it, so nested config blocks
  were silently discarded.
- No `.gitignore`, despite the README claiming outputs were ignored.

## Environment

| | |
|---|---|
| Host | Nectar VM, 32 cores, 125 GB RAM, 2.4 TB on `/mnt` |
| Device | **CPU only** — `torch 2.0.1+cpu`, no `nvidia-smi` |
| Stack | Python 3.10.12, RFdiffusion + SE3Transformer + DGL at `/mnt/src` |
| Weights | ~3.7 GB of checkpoints, complete |
| Execution | Repo edited locally, shipped with `env/sync.sh`, run on the VM |

## Defects found and fixed

**1. CPU-only hosts could not run at all.** SE3Transformer imports
`torch.cuda.nvtx.range` unguarded at module scope in four files. On a CPU build
this raises `NVTX functions not installed` *partway through the first forward
pass*, so the job looks healthy until it dies inside the model. Fixed with
`agentic_design.cpu_shim`, which replaces the NVTX push/pop primitives with
no-ops — they are profiling markers with no effect on results — then hands off
to the real entrypoint. It lives in this repo rather than patching the
RFdiffusion checkout, so the workaround survives a reinstall.

A full audit of the inference path found this is the *only* genuine
GPU-hardcoding. `model_runners.py` selects its device correctly, the three
`torch.cuda.*` calls in `run_inference.py` are guarded, and `basis.py`'s
`.half()` cast is gated on autocast. The hardcoded `device='cuda'` strings
elsewhere in SE3Transformer belong to its training harness, which RFdiffusion
inference never imports.

**2. Nested config blocks were silently dropped.** `cli.py` read six flat keys
and ignored everything else, so `ubq_binder`'s `noise_scale_ca: 0` and
`ubq_partial`'s `partial_T: 10` never reached the command — with no error.
Runs would have completed with settings the config said were applied. Specs now
flatten to Hydra overrides, so any RFdiffusion key is reachable without adding
a branch per option.

**3. Progress was invisible.** `run_design()` used `capture_output=True`,
buffering in memory until exit, so `run.log` did not exist while a job ran.
Output now streams to the log. RFdiffusion logs every timestep, so
`env/sync.sh progress <name>` and `watch <name>` give fine-grained status.

**4. Re-running a config silently does nothing.** RFdiffusion's cautious mode
skips any design whose output PDB already exists, logging
`(cautious mode) Skipping this design` and exiting 0. A repeat run reports the
stale designs as though freshly generated. Confirmed directly: re-running
`ubq_monomer` returned `returncode: 0` with 2 designs reported and
`skipped_existing: 2`. The result dict now carries that count.

This one produced a false positive during development — a run "completed"
instantly and was briefly taken as proof that log streaming worked.

## Results

All runs CPU, `device: CPU` recorded in every `.trb`.

| Run | Contig | Designs | Time/design |
|---|---|---|---|
| `smoke` | `[40-40]`, T=20 | 1 | 23.5 s |
| `ubq_motif` | `[20-30/A72-76/20-30]`, T=50 | 2 | 56.5 s, 59.6 s |
| `ubq_monomer` | `[76-76]`, T=50 | 2 | 79.8 s, 77.9 s |

### Motif scaffolding verification

The point of `ubq_motif` is holding the C-terminal LRGG motif fixed while
building new protein around it. Sampled contigs were `25-25/A72-76/24-24`
(54 residues) and `29-29/A72-76/21-21` (55 residues) — lengths consistent with
the masks, 5 motif residues each.

Reported geometry is not verified geometry, so `agentic_design.validate`
compares backbone N/CA/C coordinates of the motif as supplied against the motif
as built, superimposed with Kabsch:

| Design | Motif placement | Backbone RMSD |
|---|---|---|
| `ubq_motif_0` | A72-76 → A26-30 | **0.73 Å** |
| `ubq_motif_1` | A72-76 → A30-34 | **1.13 Å** |

Design 0 is comfortably within the sub-ångström range usually treated as
success. Design 1 is marginal. Neither is surprising: residues 72-76 are a
flexible extended tail rather than a rigid secondary-structure element, so the
reference conformation is one of many accessible ones, and these were
CPU-grade settings.

## Conclusions

- **The pipeline works end to end through the framework**, not by hand. Config
  in, verified designs out.
- **CPU is viable for development, and much faster than documented.**
  `demo_configs.yaml` estimates assume ~12 cores; on 32 the runs came in roughly
  20x faster than stated. The "4-8 h" estimate for `ubq_binder` is likely closer
  to half an hour, which makes the binder design — the actual goal — cheap to
  attempt before renting a GPU.
- **Three of the four defects failed silently.** Only the NVTX crash announced
  itself. Dropped config blocks, an empty log, and skipped re-runs all present
  as success, which is why the `.trb`-based verification matters more than the
  exit code.
- **GPU is now the default and failures are loud.** `paths.yaml` specifies
  `device: cuda` and a run aborts if no GPU is visible, rather than falling back
  and taking 50-100x longer. CPU is an explicit opt-in in `paths.local.yaml`.

## Known issues

- **A re-run truncates `run.log`**, so a skipped re-run destroys the record of
  the real one. The two ubq logs pulled locally are from re-runs for this reason.
- `env/sync.sh` is scaffolding. The intended architecture is a `remote` backend
  inside `runner.py` dispatching over SSH with no sync step. Known traps for that
  migration: `runner.py` resolves `input_pdb` against the *local* `REPO_ROOT`;
  `summarize_dir()` reads `.trb` from a local path and would silently return `[]`,
  reporting success with zero designs; contig strings contain spaces and brackets
  and need `shlex.quote` once a remote shell re-parses them; and multi-hour runs
  need tmux or nohup rather than a held connection.
- `workflows/design_campaign.py` stages beyond diffusion remain stubs, so
  "validation is not optional" currently means motif RMSD only — no ProteinMPNN,
  no refolding.

## Next step

Run `ubq_binder` (`[A1-76/0 50-65]`, hotspots A8/A44/A70) — binder design against
the Ile44 patch is the problem this framework exists to solve, and the timings
above suggest it is affordable on CPU.
