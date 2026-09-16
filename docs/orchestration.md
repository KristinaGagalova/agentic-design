# Endpoint-driven experiments

## Install and configure

Use Python 3.10 or newer and an OpenSSH client on the orchestration host.
The primary setup is native Windows `cmd` (WSL2 is an alternative):

```bat
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -e ".[test]"
copy config\orchestrator.yaml config\orchestrator.local.yaml
ssh -V
```

Within WSL2 instead:

```bash
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
python -m pip install -e '.[test]'
cp config/orchestrator.yaml config/orchestrator.local.yaml
```

Do not share a virtual environment between Windows and WSL. Windows key paths
look like `C:/Users/you/.ssh/id_ed25519`; WSL paths look like
`/home/you/.ssh/id_ed25519`. Remote paths always use Linux syntax, for example
`/mnt/src/RFdiffusion`. The SSH key and known-hosts entry must be available to the
SSH client in the environment you choose. Verify the host fingerprint through
your cluster operator and establish the connection with that SSH client before
submitting a job; the service uses strict host-key checking.

The shared config is the field reference. Put machine-specific settings in the
gitignored local config. The execution host needs the existing RFdiffusion
installation and its Python environment; see [INSTALL.md](INSTALL.md). The client
does not need RFdiffusion or torch to orchestrate remote experiments.

The backend uses direct detached SSH execution. Configure a compute machine
that permits this, not a scheduler-managed login node. Slurm/PBS adapters are
outside this increment. Credentials and host details stay in local config;
do not use the stale SSH aliases described in AGENTS.md.

## Endpoint and provider

The default is OpenRouter with `openai/gpt-5.6-sol`. Set the key in the process
environment:

Windows `cmd`:

```bat
set "OPENROUTER_API_KEY=your-key"
```

In WSL, use `export OPENROUTER_API_KEY='your-key'` instead.

Never put the key in an experiment, prompt, or committed YAML. OpenRouter
requests restrict `provider.only` to `openai`, disable provider fallbacks, and
require support for the supplied parameters, using the documented
[provider restrictions](https://openrouter.ai/docs/guides/routing/provider-selection).

For another endpoint, copy the full shared config to a separate file, change
its base URL, model, and key environment variable, and remove OpenRouter-specific
request fields. Pass that complete file as `agentic-design --config PATH ...`.
Local override files are merged into the shared defaults, so merely omitting a
field in a local override does not remove it. The endpoint/model must support
Chat Completions function tools. See the
[OpenRouter tool contract](https://openrouter.ai/docs/guides/features/tool-calling)
and [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).

## Prepare, review, approve

Put target PDBs under the configured input directory. The agent can list those
inputs and example specs, but cannot upload arbitrary local files.

```bash
agentic-design agent "List available inputs and prepare an experiment for review."
agentic-design experiment list
agentic-design experiment show EXPERIMENT_ID
agentic-design experiment preview EXPERIMENT_ID
```

Alternatively, import YAML without an endpoint key:

```bash
agentic-design experiment create config/runs/smoke.yaml --description "Check the execution environment."
```

Review the saved spec, design count, input, and command. A human CLI action
records approval against the experiment digest; the model has no approval tool.
Changing the spec requires new approval.

```bash
agentic-design experiment approve EXPERIMENT_ID
agentic-design job submit EXPERIMENT_ID
```

Submission starts remote work. An agent can submit an already approved
experiment within configured limits. Jobs use isolated directories to preserve
previous logs and outputs.

## Monitor and recover

```bash
agentic-design job list
agentic-design job status JOB_ID
agentic-design job collect JOB_ID
agentic-design agent --resume-job JOB_ID "Summarize the results and applicable structural checks."
```

No LLM key is needed for job commands. After an ambiguous submission failure,
inspect the recorded job before trying again: the worker may have started even
if its reply was lost. Reusing a submission key recovers the same submission;
a new key requests another run deliberately.

Completion requires the expected TRB/PDB outputs and a successful worker result.
A zero exit or cautious-mode skip does not establish success. Motif RMSD and
binder geometry are separate evidence; they do not replace sequence design and
refolding. Generated backbones must not be reported as validated candidates.

## MCP

```bash
python -m pip install -e ".[mcp]"
python agents/tools.py
```

Configure your MCP client to launch that command with the appropriate Python
interpreter and environment. MCP uses the same service and approval rules as
the endpoint agent. It exposes neither a shell nor an approval tool.

## Tests

The researcher authorized mocked/unit tests locally for this implementation:

```bash
python -m pytest tests -q
```

Tests exercise provider responses, tool errors, approval enforcement, SSH
commands, durable state, and output validation without paid model calls or real
RFdiffusion runs. Live endpoint/SSH checks require credentials and are separate.
The cluster is being configured later. See [handoff.md](handoff.md) for actual
verification results.
