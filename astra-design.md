# Endpoint-driven protein design experiments

Design by Astra, 2026-09-16. Implementation delegated to Sol and reviewed against
the acceptance checks below.

## Outcome and scope

A researcher describes an RFdiffusion experiment in natural language. A model
at a configurable OpenAI-compatible Chat Completions endpoint can inspect the
available inputs and example specs, save a validated experiment, preview the
exact command, submit it over SSH, check its state, retrieve its outputs, and
report the existing structural checks. OpenRouter is the first provider, not
an architectural dependency. The selected model must support function tools;
"any endpoint" means this documented protocol, not every proprietary API.

This increment automates the already demonstrated backbone pipeline. It does
not implement ProteinMPNN or refolding, invent scientific acceptance thresholds,
or describe generated backbones as validated candidates. Multi-agent scientific
debate, a web UI, literature search, and automatic hypothesis optimization are
out of scope. The system can record a hypothesis and evaluation plan without
pretending that those missing scientific stages exist.

## Evidence from the repository

The local runner, YAML-to-Hydra translation, TRB summaries, motif RMSD, and binder
geometry checks already exist. The MCP server executes synchronously and uses
CWD-relative paths for inspection. `backend` is configured but ignored. GPU
checks happen locally even though the desired execution host is remote. The
runner overwrites `run.log` and treats an empty successful subprocess as success.
The handoff's uncommitted-work warning is stale: the starting tree is clean and
contains three commits. No `project.env` is present in this checkout.

## Architecture

```text
researcher -> agent CLI -> Chat Completions endpoint
                  |            function calls
                  v
          validated tool registry <--- MCP adapter
                  |
        experiment store + job service
                  |
        SSH transport / scheduler
                  |
     isolated remote job directory + worker
                  |
       existing pure command builder -> RFdiffusion
                  |
       TRB + PDB + logs + result manifest
```

The agent has named tools, never an arbitrary shell. Transport, credentials,
installation paths, and scheduler resources come from operator configuration,
not model arguments. Both MCP and the endpoint driver call the same service.
The legacy YAML CLI remains useful and retains its local execution mode.

## Provider boundary

Use a small synchronous Chat Completions client with configurable base URL,
model, API-key environment variable, timeout, and optional provider parameters.
OpenRouter base URL is `https://openrouter.ai/api/v1`, with
`OPENROUTER_API_KEY`. The initial user-selected model is `openai/gpt-5.6-sol`.
OpenRouter requests use `provider.only: [openai]`, `allow_fallbacks: false`,
and `require_parameters: true`. Both endpoint and model remain configurable;
provider routing fields are omitted for other compatible endpoints. Standard function schemas, assistant
`tool_calls`, and correlated `tool` responses form the common contract.
Preserve provider reasoning metadata required to continue tool conversations.
Do not depend on Responses, hosted agents, or hosted MCP support.

Bound requests, tool calls, and transcript size. Validate tool arguments on the
application side even when a provider supports strict schemas. Return useful
structured tool errors to the model; unknown tools and malformed arguments must
not become shell commands. Save an audit transcript without credentials. Stop
on exhaustion or provider error with an actionable message. Transport retries
must not replay job submissions. A persisted job ID is the recovery handle.

## Experiment and job records

An experiment has a stable ID, description/hypothesis, RFdiffusion spec, and an
optional evaluation description. Save a normalized YAML/JSON snapshot and digest
so a job always refers to the exact submitted definition. Scientific narrative
must never accidentally become Hydra overrides. Existing run YAML remains an
accepted RFdiffusion spec format, including nested denoiser/diffuser blocks.

Validate names, types, positive integer counts, required contigs, supported
input paths, and reserved overrides. Reject attempts to override output paths,
input paths, device/backend, run counts, or Hydra working directories through
`extra`. Model-accessible inputs are confined to the configured input directory;
listing inputs gives the model valid choices. Do not silently coerce invalid
specs or silently drop fields. Operator-configured limits cap designs per run
and submission count during an agent session.

Each submission creates a unique run ID and directory. A job manifest records
the spec, command, timestamps, backend, scheduler ID/PID, output paths, and state.
Use atomic writes. Identical retries with the same submission handle must not
launch another job; submitting a new replicate is explicit. A disconnect during
submission is ambiguous, not evidence of failure: reconcile by job ID before
resubmitting. Preserve old logs and outputs. Never reuse a run directory for a
different experiment or truncate its log.

States distinguish prepared, submitted/queued, running, completed, failed, and
unknown/lost. A successful scheduler exit alone cannot establish completion.
Completion requires the worker's result manifest and the expected fresh TRB/PDB
pairs, with zero cautious-mode skips. Missing/malformed outputs fail clearly.
Geometry checks are separate scientific evidence, not scheduler success.

## SSH and scheduler boundary

Use OpenSSH with key authentication, batch mode, host-key verification, connection
and command timeouts, and shell quoting at the one remote-shell boundary. Do
not read stale SSH aliases as configuration. Operator configuration gives host,
key path, remote root, remote Python, RFdiffusion root, and explicit device.
GPU checking runs in the remote worker; CPU remains an explicit opt-in.

Stage only the small Python worker/package, normalized spec, and required PDB
into an isolated job directory. Never copy the full checkout or local secrets.
Stage code per job so later edits cannot change queued jobs. No manual sync step
is required. Checkpoints and RFdiffusion installations remain on the cluster.
Resolve remote input/output paths before building the command. Keep
`build_command()` free of subprocesses and transport operations.

Support direct execution through a detached worker for the demonstrated VM.
The user confirmed direct commands for this increment. Slurm, PBS, and
site-specific launch wrappers are deferred until their contract is supplied.
Do not run RFdiffusion on a cluster login node in direct mode accidentally:
the execution mode is explicit. Status queries are short;
neither SSH nor an LLM request is held for a multi-hour experiment.

Collect outputs only from the recorded job directory, with path-safe transfer.
Parse and validate collected TRB metadata from the trusted execution host;
TRB is pickle and must not be accepted from arbitrary untrusted uploads. Inspect
and validate tools use the configured result root, independent of CWD.

## Researcher controls

The user selected approval before submission. Approval is a human CLI action
bound to an immutable experiment digest, never an agent tool or a blanket
autonomy flag. The researcher may explicitly submit a reviewed experiment through
the CLI; otherwise an agent may submit only a previously approved snapshot.
Enforce configured limits in code. Approval applies to the service/MCP boundary
as well as the endpoint conversation. Changing a spec requires new approval.

The conversation can end while a job runs. Job CLI commands remain usable
without an LLM key. Start a later agent invocation with the job ID to inspect or
collect it. The first version uses explicit polling by CLI/tool calls rather than
a background daemon or repeated LLM calls while waiting in a scheduler queue.

## Implementation work packages

1. Harden the existing request builder and local runner: preserve logs, report
   empty/skipped output failure, use the same paths for preview and execution.
2. Add experiment persistence, job service, remote worker, SSH/direct
   transport, and result collection. Preserve the pure command boundary.
3. Add shared tool schemas/dispatch, endpoint conversation loop, configurable
   provider client, CLI commands, and MCP adapter over that service.
4. Add config examples, setup/usage documentation, and regression tests with
   mocked providers/SSH plus an executable worker integration fixture.
5. Verify on the configured VM, and separately exercise OpenRouter when a key
   and selected model are available. Report live checks as pending otherwise.

## Acceptance checks

- Existing run specs still translate correctly, including nested overrides and
  contigs with spaces/brackets; preview exactly matches the worker invocation.
- No GPU/torch check runs on the orchestration host for remote submissions.
- A fake endpoint can request multiple tools, receive correlated outputs, recover
  from invalid arguments, and hit configured limits without unintended effects.
- Proposal-only mode cannot launch jobs through either endpoint or MCP tools.
- Each job snapshots its spec, survives client exit, preserves logs, and exposes
  recoverable state after failed/ambiguous SSH responses.
- SSH commands quote paths correctly, reject invalid configuration,
  and stage no secrets. Unsupported schedulers are an explicit error.
- Collection rejects unsafe paths and incomplete/corrupt output sets; a zero exit
  with no TRBs or cautious skips never yields completed success.
- Existing geometry tests pass. New tests exercise lifecycle, provider errors,
  validation, command quoting, duplicate submissions, transport failure, and
  collection rather than simply mirroring implementation.
- Documentation distinguishes mocked tests, live transport checks, actual
  RFdiffusion runs, and biological validation. No new backbone is a candidate.

## Confirmed choices and pending live configuration

The initial client is Windows cmd with WSL2 available. Native Windows commands,
a portable Python demo fetcher, prompt-file input, and POSIX remote path handling
are required; WSL is documented as a separate environment, not silently assumed.
The user confirmed direct SSH, per-experiment approval before submission, and
OpenRouter `openai/gpt-5.6-sol` restricted to the OpenAI provider. The user also
authorized mocked/unit tests locally and chose to configure the cluster later,
overriding the repository’s VM-only test instruction for this work. Actual SSH
credentials and provider keys stay local and gitignored. Live provider/cluster
verification remains pending until those settings are supplied.

## Protocol references

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenRouter API contract](https://openrouter.ai/docs/api/reference/overview)
- [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [OpenRouter provider restrictions](https://openrouter.ai/docs/guides/routing/provider-selection)

The endpoint provides structured tool requests; this application remains
responsible for argument validation, execution, and returning tool results.

## Delivered implementation and verification

The selected scope is implemented by Sol in `app.py`, `config.py`,
`experiments.py`, `jobs.py`, `transport.py`, `remote_worker.py`, `provider.py`,
and `tools.py`, with the MCP adapter and hardened legacy runner. SSH dispatch
lives in the durable job service rather than the synchronous `run_design()`;
the latter is the execution-machine worker primitive. The legacy CLI explicitly
rejects a non-local backend so it cannot accidentally execute remote jobs locally.

`demo-api/README.md` is the numbered Windows cmd walkthrough, with WSL2 as an
alternative. It reuses the existing ubiquitin motif experiment and includes a
portable fetcher and prompt file. The upstream fetch-script update was integrated.

Final local verification: **33 tests passed**, including localhost HTTP tool
calls and an isolated staged worker with fake inference. Compilation and diff
checks passed. CI has been configured for Windows and Linux; those hosted runs,
a native Windows acceptance run, real OpenRouter requests, and real SSH/RFdiffusion
execution remain unverified pending the operator setup. No new validated protein
candidate is claimed.
