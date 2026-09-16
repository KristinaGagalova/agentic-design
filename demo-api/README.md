# Run the ubiquitin demo through the API

For the shorter command-by-command version, start with [Getting started](GETTING_STARTED.md).

This is a step-by-step walkthrough for **Windows Command Prompt (`cmd`)**.
WSL2 instructions are at the end. Run commands from the repository root.

The experiment copies the existing ubiquitin motif demo: preserve residues
A72-76, generate 20-30 residues on each side, and produce two backbones. The API
prepares a saved experiment; you review and approve it; the job runs on your
SSH compute machine. The initial model is OpenRouter’s `openai/gpt-5.6-sol`,
restricted to the OpenAI provider.

You can complete preparation before configuring the compute machine. Running
the actual experiment requires an SSH host with RFdiffusion installed.

## 1. Open the repository and install the client

Prerequisites: Python 3.10 or newer, Git, and an OpenSSH client. Substitute your
checkout location below:

```bat
cd /d C:\path\to\agentic-design
py -3 --version
ssh -V
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -e ".[test]"
agentic-design --help
```

The client does not need PyTorch, a GPU, or RFdiffusion installed locally.
When opening a new Command Prompt, return to this folder and run
`call .venv\Scripts\activate.bat` again.

## 2. Configure the model and execution machine

Create your local configuration once:

```bat
copy config\orchestrator.yaml config\orchestrator.local.yaml
notepad config\orchestrator.local.yaml
```

Keep the default `provider` section for OpenRouter/Sol. In the `ssh` section,
replace the host and key path and check all remote paths. Example:

```yaml
ssh:
  execution_mode: direct
  host: your-user@your-compute-host
  key_path: C:/Users/your-name/.ssh/id_ed25519
  remote_root: /mnt/src/agentic-design-jobs
  python_bin: /mnt/src/rfdiff-venv/bin/python
  rfdiffusion_root: /mnt/src/RFdiffusion
  device: cuda
  connect_timeout: 15
  command_timeout: 60
```

Use **Windows paths for the local SSH key** and **Linux paths for remote files**.
Forward slashes in the YAML key path avoid backslash escaping. The remote
interpreter must already have RFdiffusion’s dependencies, and checkpoints must
be installed as described in [INSTALL.md](../docs/INSTALL.md). For an explicitly
CPU-only machine, set `device: cpu`; the default `cuda` fails if no GPU is visible.

This version executes direct commands on the SSH machine. Do not point it at a
login node that requires Slurm/PBS submission.

The config is gitignored. Leave the host blank for now if you only want to
prepare the experiment. To change provider/model later, see
[endpoint configuration](../docs/orchestration.md#endpoint-and-provider).

## 3. Set your OpenRouter key

In the same Command Prompt:

```bat
set "OPENROUTER_API_KEY=your-openrouter-key"
```

Replace the placeholder with your key. Do not paste the key into the experiment
prompt or YAML. This command sets it for the current terminal session.
Preparation through the API consumes provider credits; the deterministic YAML
alternative in step 5 does not.

## 4. Download the demo target

```bat
python demo-api\fetch_demo_target.py
agentic-design experiment inputs
```

The Python fetcher is a portable counterpart to the updated
`demo/fetch_demo_target.sh`. It downloads public PDB **1UBQ**, keeps protein
atoms for chain A, verifies complete backbone atoms and residues 1-76, and
writes `data/inputs/1UBQ_clean.pdb`. The input listing should include that filename.
Use `--output-dir PATH` if you changed `state.inputs_dir` in the configuration.

## 5. Ask the API to prepare the experiment

```bat
agentic-design agent --prompt-file demo-api\prepare-prompt.txt
```

The prompt asks the model to inspect inputs and examples, save `api_ubq_motif`,
and preview the command. It stops before submission. Expect an experiment ID,
a description of the intended checks, and instructions for approval. If the
model reports a missing input or invalid spec, resolve that before proceeding.

You can prepare the identical experiment without an API request instead:

```bat
agentic-design experiment create demo-api\ubq_motif.yaml --description "Ubiquitin motif demo" --evaluation "Inspect TRB records and measure motif RMSD; no refolding or candidate claim."
```

**That alternative creates `ubq_motif`, not `api_ubq_motif`.** Substitute
`ubq_motif` in subsequent commands if you used it. To see saved experiments:

```bat
agentic-design experiment list
```

## 6. Review and approve the saved experiment

```bat
agentic-design experiment show api_ubq_motif
agentic-design experiment preview api_ubq_motif
```

Check these fields before approving:

| Field | Expected value |
|-------|----------------|
| `input_pdb` | `1UBQ_clean.pdb` |
| `contigs` | `[20-30/A72-76/20-30]` |
| `num_designs` | `2` |
| `diffuser_T` | `50` |

The preview has a `<run-id>` placeholder; submission assigns the actual isolated
remote directory. The saved experiment includes a digest of the spec and input
contents. Once satisfied:

```bat
agentic-design experiment approve api_ubq_motif
```

Approval alone does not launch anything. The AI has no tool to grant approval.
Changing the scientific spec requires a new saved experiment and approval.

## 7. Verify SSH and submit

If you have not configured the compute machine yet, stop here and return when
it is ready. First test SSH, substituting your actual key and host:

```bat
ssh -i "C:\Users\your-name\.ssh\id_ed25519" your-user@your-compute-host
```

For a new host, verify its fingerprint with the machine’s operator before
accepting it. Exit the remote shell with `exit` to return to Windows. The service
uses strict host-key checking and non-interactive key authentication. If your
key has a passphrase, load it into your SSH agent before submission.

Now launch the approved experiment:

```bat
agentic-design job submit api_ubq_motif --submission-key api-ubq-motif-first-run
```

Save the `run_id` printed in the JSON response. To avoid repeating it manually:

```bat
set "DEMO_JOB_ID=PASTE_THE_RETURNED_RUN_ID_HERE"
```

The worker continues on the compute machine after this command exits. Do not
create another submission merely because the job takes time. Reuse the same
submission key when recovering a lost submission reply; a new key means a new
intentional run.

## 8. Check progress and collect results

```bat
agentic-design job status %DEMO_JOB_ID%
```

Repeat when useful until the state is `completed` or `failed`. These checks do
not call the LLM. Runtime depends on the configured CPU/GPU and environment.
When completed:

```bat
agentic-design job collect %DEMO_JOB_ID%
```

Expect two TRB/PDB pairs under `results\%DEMO_JOB_ID%\outputs`, plus the log and
result record. Collection checks completeness; a zero process exit or skipped
old output does not count as a successful experiment. If you close the terminal,
reactivate the virtual environment and use `agentic-design job list` to find
the durable job ID.

## 9. Ask the API to inspect and validate the motif

```bat
agentic-design agent --resume-job %DEMO_JOB_ID% "Inspect the collected TRB records and run the motif-preservation check against the saved input. Report both backbones and their motif RMSDs. Explain missing evidence. Do not submit another experiment."
```

This is a new API request, so set the key again if using a new terminal. The
agent should report what was generated and the per-design motif RMSD. A completed
run is **not** a validated binder candidate: sequence design, refolding, and
experimental testing are outside this demo.

## Troubleshooting

| Symptom | Next step |
|---------|-----------|
| `agentic-design` is not recognized | Activate `.venv`, or use `python -m agentic_design.app` in its place. |
| Missing provider key | Set `OPENROUTER_API_KEY` in the current terminal. |
| Provider HTTP error | Check key, credits, model access, and the OpenAI-only provider restriction. |
| Missing input | Run the Python fetcher and check `state.inputs_dir`. |
| Experiment already exists with different contents | Use a new experiment name; saved specs are immutable. |
| Experiment not approved | Review it, then run the human `experiment approve` command. |
| SSH or host-key failure | Test the same host/key with Windows `ssh`; check the verified known-hosts entry and key permissions. |
| State is `unknown` | Inspect the recorded job and remote directory before requesting another run. |
| Failed job | Read the error returned by `job status` and remote `worker-bootstrap.log` / `outputs/run.log`. |
| No GPU visible | Correct the remote GPU environment, or explicitly choose `device: cpu` for an intended CPU run. |

## WSL2 alternative

Use WSL consistently for Python and SSH; do not reuse the Windows virtual
environment. From the checkout inside WSL:

```bash
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
python -m pip install -e '.[test]'
cp config/orchestrator.yaml config/orchestrator.local.yaml
export OPENROUTER_API_KEY='your-key'
python demo-api/fetch_demo_target.py
agentic-design agent --prompt-file demo-api/prepare-prompt.txt
```

Set `ssh.key_path` to a Linux path available to WSL, and establish the host-key
entry using WSL’s SSH client. Follow steps 6-9 with the same CLI commands, using
`export DEMO_JOB_ID='returned-id'` and `$DEMO_JOB_ID` instead of the Windows
`set` command and `%DEMO_JOB_ID%`. The original Bash data fetcher remains available
through `bash demo-api/fetch_demo_target.sh`.

## Other examples

The folder also copies `smoke`, `ubq_monomer`, `ubq_binder_fast`, `ubq_binder`, and
`ubq_partial` from the existing demo with portable input paths. The scientific
parameters are unchanged. `smoke.yaml` requires no target and is useful as an
installation check. Binder examples are pipeline demonstrations, not a search
for validated binders.
