# Status

Updated 2026-09-16 for the endpoint-driven orchestration implementation.
Start with [the demo walkthrough](../demo-api/README.md) and
[Astra’s design](../astra-design.md).

## Current work

Astra designed the system and Sol implemented the agent/job service. The
researcher selected direct SSH execution, human approval before submission,
configurable endpoint/model settings, and OpenRouter `openai/gpt-5.6-sol`
restricted to the OpenAI provider. The initial client is Windows `cmd`, with
WSL2 available as an alternative.

- A Chat Completions tool loop prepares immutable experiment specs and records
  conversation audits. Endpoint, model, key environment variable, and request
  parameters are operator-configurable.
- Approval is a human CLI action tied to the saved spec and input bytes. Models
  can submit approved experiments but cannot approve them.
- The job service stages a small worker and input snapshot automatically over
  SSH, starts detached jobs, records durable IDs, and retrieves checked outputs.
- MCP shares the same tool service and approval rules.
- Original YAML runs remain supported on the execution machine. The new
  orchestrator is the SSH path; the legacy CLI rejects non-local backends.
- `demo-api/` adapts the existing ubiquitin examples with portable input paths,
  a prompt file, data-fetch scripts, and a numbered Windows/WSL walkthrough.
- The upstream demo fetch update (`dcaf416`) was fast-forwarded into this checkout
  before integrating the API demo. No existing work was discarded.

The API implementation is on the `agentic-design-api` branch for review against
`main`. The earlier warning about all historical work being uncommitted was
stale; that work was already in Git.

## Verification

The researcher explicitly authorized mocked/unit tests locally and chose to
configure the cluster later. See the final verification entry below for the
suite result. No live OpenRouter request, real SSH submission, or new RFdiffusion
experiment has been run in this implementation session.

The updated fetcher downloaded public 1UBQ. The cleaned target was checked:
602 protein atoms, chain A, contiguous residues 1-76, and complete N/CA/C backbone
atoms. Generated target files are gitignored and reproducible with the fetcher.

The HTTP integration fixture exercises the API demo using a local fake endpoint:
input/example discovery, saving a motif experiment, command preview, rejection
of model self-approval and unapproved submission, tool-result correlation,
reasoning metadata preservation, and a key-free saved audit.

## Still required for a live demonstration

1. Follow `demo-api/README.md` on the Windows client (or entirely within WSL).
2. Set the local OpenRouter key; no key is present in source control.
3. Configure `config/orchestrator.local.yaml` with the SSH host/key and remote
   installation paths, then establish the verified host-key entry.
4. Review the saved motif experiment, approve it, submit it, and collect outputs.
5. Check motif RMSD. This is geometric verification, not candidate validation.

The native Windows commands and POSIX remote paths are implemented, but this
session runs on macOS; a native Windows/real-host acceptance run remains pending.
Slurm/PBS adapters are deferred because the researcher selected direct commands.

## Scientific scope and historical evidence

The historical CPU runs remain documented in [first-run.md](first-run.md):
`smoke`, `ubq_motif`, `ubq_monomer`, and `ubq_binder` ran end to end. Motif RMSDs
were 0.73 and 1.13 Å; binder target-preservation RMSDs were 0.117 and 0.114 Å.
Those binders contacted only A8, not the full intended patch.

ProteinMPNN, refolding, and downstream filtering are still explicit stubs in
`workflows/design_campaign.py`. No validated binder candidate has been produced.
The framework reports backbones and structural checks without claiming otherwise.

## Final verification (2026-09-16)

- Full local suite: **33 passed** (`.venv-sol/bin/python -m pytest tests -q`).
- Python compilation and `git diff --check`: passed.
- Console entry point, input/example discovery, demo import, and command preview:
  exercised successfully. The saved local demo remains unapproved and unsubmitted.
- Real localhost HTTP fixture: passed, with no paid provider request.
- Isolated staged worker: executed against fake inference/torch fixtures; no
  real protein design or GPU computation was performed.
- Regression coverage includes immutable input approval, protected overrides,
  job idempotency, output freshness, partial collection recovery, remote quoting,
  SSH failure handling, completion/PID race handling, and bounded submissions.
- CI configuration added for Windows/Linux with Python 3.10/3.12. It has not
  been run on GitHub in this session; native Windows acceptance is still pending.
