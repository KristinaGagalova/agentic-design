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
  each), `ubq_monomer` (2 designs, ~78-80 s each).
- `ubq_motif` motif preservation: **0.73 Å** and **1.13 Å** backbone RMSD over
  A72-76. Design 0 good, design 1 marginal.
- 10 tests pass, none needing a GPU, weights, or RFdiffusion installed.
- 9 run configs in `config/runs/`.

See [first-run.md](first-run.md) for the full run report.

## Does not exist yet

- ProteinMPNN, refolding, and filtering — `workflows/design_campaign.py` raises
  `NotImplementedError` for all three. "Validation" today means motif RMSD only.
- The `remote` SSH backend.
- Anything for the OpenAI-compatible-endpoint goal beyond the existing MCP server.
- **No binder has ever been designed.** Every run so far is a monomer or motif
  scaffold, so the actual goal is untouched.

## Known defects

- **A re-run truncates `run.log`**, destroying the record of the original run.
  Combined with cautious-mode skipping, a careless repeat wipes your only log.
- `--dry-run` prints a relative `output_prefix` while a real run uses an absolute
  one. Cosmetic, but the printed command is not exactly what executes.

## Next steps, in order

1. **Commit.** Nothing else should happen first.
2. **Run `ubq_binder`** (`[A1-76/0 50-65]`, hotspots A8/A44/A70) — the problem
   this framework exists to solve, never yet attempted. Documented estimate is
   4-8 h; measured runs came in ~20x faster, so expect closer to 30 min. Note the
   binder case has **no fixed motif**, so `validate_motif` does not apply and
   acceptance criteria still need defining.
3. **Fix the `run.log` truncation** before a long binder run gets clobbered.
4. **Wire up ProteinMPNN** (`stage_sequence`). Without sequence design and
   refolding, "high-quality binder" is unfalsifiable.
5. **Then** the `remote` SSH backend — traps listed in AGENTS.md.
6. **Consider a GPU** once binder runs are routine. Nothing in `src/` should
   change: point `paths.local.yaml` at the GPU install and drop `device: cpu`.
