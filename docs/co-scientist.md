# Protein-design co-scientist with OpenCode

This first version combines OpenCode, the existing RFdiffusion experiment tools,
and a file-based research notebook. You discuss a question, review an experiment,
let it run, and ask the co-scientist to interpret the results.

## Start on this machine

OpenCode is installed locally under `harness/`; Python dependencies are in
`.venv-research/`. From the repository root:

```bash
export OPENROUTER_API_KEY='your-key'
./co-scientist
```

The launcher reads the model, endpoint, and key-environment-variable name from
`config/orchestrator.yaml` and the optional `config/orchestrator.local.yaml`.
Credentials are passed through the environment, not written into the notebook.
Use OpenCode's model selector or `--model provider/model` to choose another
configured OpenCode provider. Do not paste API keys into the chat.

Try:

> Start a campaign called ubq-pilot. Use the existing ubiquitin motif example to
> prepare two backbones with starting seed 42. Record why we are running it and
> how we will check motif preservation. Stop after the command preview.

Inputs must already be in `data/inputs/`. The existing public demo fetcher is:

```bash
.venv-research/bin/python demo-api/fetch_demo_target.py
```

The co-scientist can prepare a notebook and experiment before compute is
configured. To execute it, configure the SSH host, key, installation paths, and
device in `config/orchestrator.local.yaml`; see [orchestration](orchestration.md).
There is no host or model API key shipped with the project.

## Review and run

Approve inside OpenCode. Ask the co-scientist to approve the experiment and
OpenCode shows a confirmation prompt naming the tool and experiment ID; accept
or deny it there. The agent cannot approve silently: `research_approve_experiment`
is configured with permission `ask`, so a denial leaves the experiment
unapproved. Review the spec, seed, and command preview the agent shows you before
accepting; the prompt itself is a confirmation, not a substitute for reading what
you are approving. Approvals granted this way are recorded with
`"approved_via": "opencode_confirmed"`.

The equivalent CLI path still works if you prefer a separate terminal:

```bash
source .venv-research/bin/activate
agentic-design experiment show EXPERIMENT_ID
agentic-design experiment preview EXPERIMENT_ID
agentic-design experiment approve EXPERIMENT_ID
```

Either way the approval binds to the exact spec digest, and a changed spec needs
a new experiment and a new approval.

**The research profile has a shell, file editing, and arbitrary Python** (enabled
2026-10-27), with `bash`, `edit`, `write`, and `apply_patch` set to `ask` so each
command or write reaches you as a confirmation prompt. Agent delegation stays
denied, because a subagent's calls would not reach you.

Understand what that means for approval. A shell can run
`agentic-design experiment approve`, write `approval.json`, or edit these
permission files, so **approval is now a convention the agent is instructed to
keep, not a boundary the system enforces.** Its prompt forbids self-approval,
widening its own permissions, and rewriting the append-only records, and
`tests/test_research.py` fails if any capability permission is changed to
`allow`. None of that is an operating-system sandbox. If you need approval
enforced rather than conventional, run the client as a separate user or in a
container with no write access to `.agentic-design/`, or revert the capability
permissions to `deny`.

Read each confirmation prompt rather than accepting reflexively; on a long
debugging session that is the weak point in this arrangement.

The existing `limits.max_agent_submissions` defaults to one new submission per
MCP process. Set it deliberately in local configuration if a session needs more
runs. Retrying an existing recorded submission key retrieves that job without
launching another. Failed or ambiguous new submissions consume the allowance.

## Notebook and resuming

Open `research/campaigns/<campaign-id>/notebook.md` whenever you want to read the
record. The tools automatically record saved specs, command previews, submission
requests, returned job IDs, status checks, output locations, and measured checks.
The agent separately appends hypotheses, interpretations, decisions, and corrections.

The saved spec includes the starting seed. The existing input snapshot and its
SHA-256 identify the actual PDB bytes. Each remote submission also retains its
small worker/input archive at `.agentic-design/jobs/<run-id>/execution-bundle.tar.gz`.

While a job runs, ask the co-scientist how far along it is and it reports the
written/expected design counts, which indices are finished, which are still
being written, and the last log line. Those are written files, not results:
nothing is collected or checked until the job state is `completed`, and a
nonzero `skipped_existing` means RFdiffusion reused existing outputs and the run
is not fresh. There is no automatic polling; it checks when you ask.

You can inspect the notebook and a running job without an LLM:

```bash
agentic-design notebook list
agentic-design notebook show ubq-pilot
agentic-design job progress JOB_ID
```

Close OpenCode whenever needed. Remote jobs continue. Open a new session and say:

> Resume ubq-pilot. Read the notebook, find its jobs, collect completed outputs,
> perform the motif check, and record what the results do and do not establish.

There is no always-running agent or automatic wakeup in this version. Actions
performed outside the research tools are not automatically notebook entries;
`list_jobs` discovers CLI-submitted jobs belonging to recorded experiments.

## Result images and comparison plots

Save generated result images under `results/`, in the corresponding collected
run's output folder: `results/<run-id>/`. Do not use `/tmp/` as the delivery
location for result figures.

- For a single-run figure, use a new, descriptively named file or versioned
  plotting subfolder within `results/<run-id>/`.
- For a comparison spanning multiple runs, save it in a new versioned subfolder
  of the latest contributing run's output folder, such as
  `results/<latest-run-id>/comparison-<version>/`. Identify every contributing
  run in the accompanying data and record the location in the campaign notebook.
- Preserve append-only evidence: never overwrite or delete existing figures,
  collected structures, logs, validation records, or input snapshots. Generate a
  new filename/subfolder for each update.
- Save PNG and, where practical, SVG versions together with the plotted data
  (including source run IDs). Link the actual result-folder files in the reply.
  Display the image when permissions permit; otherwise report that limitation.
- Plot measured validation outputs only. Clearly label pending/unmeasured
  conditions, thresholds, and failures; do not invent or silently omit results.

The ubiquitin screening plotter accepts a new output directory, for example:

```bash
python3 scripts/plot_ubq_screen.py research/campaigns/ubq-pilot \
  results/<latest-run-id>/comparison-v1
```

It reads recorded measurements without rerunning structural validation. Its
Python interpreter must have Matplotlib installed.

## Repeating an experiment

Every experiment saved through the co-scientist has an explicit integer `seed`
(default `0`). For `seed: 42` and `num_designs: 2`, the command enables
`inference.deterministic=true` and `inference.design_startnum=42`; RFdiffusion
uses seeds 42 and 43, and outputs are named `<experiment>_42` and `_43`.
The [upstream inference code](https://github.com/RosettaCommons/RFdiffusion/blob/main/scripts/run_inference.py)
seeds Python, NumPy, and torch by design index in deterministic mode.

To repeat, ask:

> Repeat experiment EXPERIMENT_ID using its saved input and seed. Use a new
> submission key and record that this is a replication of RUN_ID.

Reuse the **same experiment ID** with a **new submission key** for an intentional
repeat. Reuse the same key only to recover a submission whose reply was lost.
To explore different randomness or settings, save and approve a new experiment
with a different seed or spec. Legacy CLI/YAML experiments without `seed` keep
their previous behavior and are not automatically deterministic.

These records preserve inputs, parameters, and seeds. Matching outputs also
requires matching RFdiffusion code, checkpoint weights, dependencies, and hardware.
This first version does not capture those entire environments or promise bitwise
reproducibility. Keep the execution environment fixed when assessing replication.
The retained worker bundle is evidence of the submitted code/input; automatic
execution of historical bundles and automatic comparison of repeats are not implemented.

RFdiffusion backbones and geometric checks are the current scientific scope.
ProteinMPNN, refolding, and candidate filtering are not implemented. A successful
run does not establish a validated binder.

## Install on another machine

Follow the [main README](../README.md) for the complete fresh-machine setup:
source version, prerequisites, macOS/Linux/WSL and Windows commands, pinned
OpenCode installation, model credentials, SSH configuration, acceptance tests,
and transferring experiment records. It is the canonical installation guide.
