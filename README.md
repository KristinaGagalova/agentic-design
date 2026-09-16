# agentic-design

Describe, review, and run RFdiffusion experiments using an AI at an
OpenAI-compatible Chat Completions endpoint. The AI prepares experiment specs;
you approve a saved spec before it can submit a job. Jobs run over SSH and
continue after the conversation ends.

The initial configuration uses OpenRouter’s `openai/gpt-5.6-sol`, restricted to
the OpenAI provider. Endpoint, model, and provider settings are configurable.

RFdiffusion produces **backbones, not validated binder candidates**. The repo
inspects authoritative `.trb` records and checks motif preservation and binder
geometry. ProteinMPNN and refolding are not implemented.

## Start here

- [API demo using the existing ubiquitin experiments](demo-api/README.md)
- [Setup and usage](docs/orchestration.md)
- [Astra’s design](astra-design.md)
- [Current status and verification](docs/handoff.md)
- [RFdiffusion installation](docs/INSTALL.md)
- [Original CPU experiment report](docs/first-run.md)

The client needs Python 3.10+, OpenSSH, and lightweight package dependencies.
RFdiffusion, PyTorch, and weights belong on the execution machine. The current
remote backend runs direct commands; Slurm/PBS are deferred.

Windows `cmd`:

```bat
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -e ".[test]"
copy config\orchestrator.yaml config\orchestrator.local.yaml
rem Edit the local config for your endpoint and execution host.
set "OPENROUTER_API_KEY=your-key"
python demo-api\fetch_demo_target.py
agentic-design agent --prompt-file demo-api\prepare-prompt.txt
```

WSL2 also works; use a separate Linux virtual environment and Linux SSH key paths.
See [setup](docs/orchestration.md) for both options.

Review and approve the experiment ID printed by the agent:

```bash
agentic-design experiment show EXPERIMENT_ID
agentic-design experiment preview EXPERIMENT_ID
agentic-design experiment approve EXPERIMENT_ID
agentic-design job submit EXPERIMENT_ID
agentic-design job status JOB_ID
agentic-design job collect JOB_ID
agentic-design agent --resume-job JOB_ID "Inspect the outputs and explain what is and is not validated."
```

Approval and submission are separate actions. The model has no approval tool.
Job commands work without an LLM key.

## Existing YAML workflow

Import an existing run into the reviewed remote workflow:

```bash
agentic-design experiment create config/runs/smoke.yaml
```

The original CLI remains available on the execution machine:

```bash
python -m agentic_design.cli config/runs/smoke.yaml --dry-run
python -m agentic_design.cli config/runs/smoke.yaml
```

`env/sync.sh` is retained for the legacy VM workflow. The new service stages each
job’s worker and inputs automatically, with no manual sync step.

## Layout

| Path | Purpose |
|------|---------|
| `astra-design.md` | Architecture and acceptance checks |
| `config/orchestrator.yaml` | Endpoint, limits, state, and SSH configuration |
| `config/paths.yaml` | Legacy local RFdiffusion installation paths |
| `config/runs/` | RFdiffusion run specs |
| `demo-api/` | Worked API example adapted from `demo/` |
| `src/agentic_design/` | Agent, job service, worker, runner, and validation |
| `agents/tools.py` | MCP adapter over the shared tools |
| `data/inputs/` | Researcher-supplied input structures |
| `tests/` | Provider/transport fixtures and regression tests |

Machine settings, credentials, outputs, and transcripts belong in gitignored
locations. `.trb` files use pickle: only inspect outputs from the trusted
execution environment.
