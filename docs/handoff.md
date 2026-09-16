# Status

What is true right now. Everything durable — goals, environment, commands,
architecture, invariants, and the failure modes that present as success — lives
in [../AGENTS.md](../AGENTS.md) and is deliberately not repeated here.

> **None of this work is committed.** `git log` shows a single commit,
> `Scaffold agentic design repo around RFdiffusion`, with ~21 uncommitted paths.
> A fresh clone gets *none* of it. **Committing is the highest-priority action.**

## Progress against the three goals

| Horizon | State |
|---|---|
| Test the framework, run one experiment end to end | **Done** |
| Extract what is reusable from that run | **Mostly done** |
| Drivable by any AI over an OpenAI-compatible endpoint | Not started |

## Works, verified

- Full pipeline: YAML spec → RFdiffusion on the VM → parsed `.trb` → motif RMSD.
- Runs completed, all CPU: `smoke` (23.5 s), `ubq_motif` (2 designs, ~57-60 s
  each), `ubq_monomer` (2 designs, ~78-80 s each), `ubq_binder` (2 designs,
  ~2.6-2.9 min each).
- `ubq_motif` motif preservation: **0.73 Å** and **1.13 Å** backbone RMSD over
  A72-76. Design 0 good, design 1 marginal.
- `ubq_binder` target preservation: **0.117 Å** and **0.114 Å** over all 76
  target residues — the chain-break contig and `denoiser` overrides work.
- 14 tests pass, none needing a GPU, weights, or RFdiffusion installed.
- 9 run configs in `config/runs/`.

See [first-run.md](first-run.md) for the full run report.

## Does not exist yet

- ProteinMPNN, refolding, and filtering — `workflows/design_campaign.py` raises
  `NotImplementedError` for all three. "Validation" today means motif RMSD only.
- The `remote` SSH backend.
- Anything for the OpenAI-compatible-endpoint goal beyond the existing MCP server.
- **No binder worth testing.** Both `ubq_binder` designs contact only A8; A44
  and A70 — the Ile44 patch that is the real interaction surface — sit 6.5-7.3 Å
  away, and interfaces are small (7-11% of binder atoms). Hotspots bias
  RFdiffusion, they do not constrain it, and 2 designs is not a sample.

## Known defects

- **A re-run truncates `run.log`**, destroying the record of the original run.
  Combined with cautious-mode skipping, a careless repeat wipes your only log.
- `--dry-run` prints a relative `output_prefix` while a real run uses an absolute
  one. Cosmetic, but the printed command is not exactly what executes.

## Next steps, in order

1. **Generate a real batch of binders.** At ~2.75 min/design, 100 designs is
   ~4.5 h on CPU — practical. Two designs told us the mechanism works; only a
   batch will produce something worth carrying forward. Rank with `check_binder`
   on hotspots contacted and interface fraction.
2. **Fix the `run.log` truncation** before a long batch gets clobbered.
3. **Wire up ProteinMPNN** (`stage_sequence`). Without sequence design and
   refolding, "high-quality binder" is unfalsifiable.
4. **Then** the `remote` SSH backend — traps listed in AGENTS.md.
5. **Consider a GPU** once binder runs are routine. Nothing in `src/` should
   change: point `paths.local.yaml` at the GPU install and drop `device: cpu`.
