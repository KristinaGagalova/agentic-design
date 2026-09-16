\# Quickstart: run the demo with your OpenRouter key



Use \*\*Windows Command Prompt (`cmd`)\*\*. Run these commands from a checkout of

the `agentic-design-api` branch. You need Python 3.10+, OpenSSH, your OpenRouter

key, and SSH access to a machine with RFdiffusion and its weights installed.



\## 1. Install the client



Open Command Prompt in the repository directory:



```bat

py -3 -m venv .venv

call .venv\\Scripts\\activate.bat

python -m pip install -e .

```



If you already installed it, just activate the environment:



```bat

call .venv\\Scripts\\activate.bat

```



\## 2. Configure SSH



Create the local configuration \*\*only if it does not already exist\*\*:



```bat

if not exist config\\orchestrator.local.yaml copy config\\orchestrator.yaml config\\orchestrator.local.yaml

notepad config\\orchestrator.local.yaml

```



Edit its `ssh` section using your actual host and paths:



```yaml

ssh:

&#x20; execution\_mode: direct

&#x20; host: your-user@your-server

&#x20; key\_path: C:/Users/your-name/.ssh/id\_ed25519

&#x20; remote\_root: /mnt/src/agentic-design-jobs

&#x20; python\_bin: /mnt/src/rfdiff-venv/bin/python

&#x20; rfdiffusion\_root: /mnt/src/RFdiffusion

&#x20; device: cpu

&#x20; connect\_timeout: 15

&#x20; command\_timeout: 60

```



Use `device: cuda` for a remote environment with a working GPU. The Python and

RFdiffusion paths must match the remote installation; `remote\_root` must be

writable. This version runs direct commands, not Slurm/PBS jobs.



Test the same key and host:



```bat

ssh -o BatchMode=yes -i "C:\\Users\\your-name\\.ssh\\id\_ed25519" your-user@your-server "echo connected"

```



Continue once it prints `connected`. For a new host, establish its known-hosts

entry with an interactive SSH connection after verifying its fingerprint. A

passphrase-protected key must be loaded into your SSH agent for batch access.



\## 3. Set your OpenRouter key



In the same Command Prompt, replace the placeholder with your key:



```bat

set "OPENROUTER\_API\_KEY=your-key"

```



Keep the default provider settings: `openai/gpt-5.6-sol` through OpenRouter,

restricted to the OpenAI provider. The key is read locally; do not put it in

the experiment prompt or committed files. API requests consume provider credits.



\## 4. Download the demo target



```bat

python demo-api\\fetch\_demo\_target.py

```



Expect `data\\inputs\\1UBQ\_clean.pdb`: ubiquitin chain A, residues 1–76.



\## 5. Ask the API to prepare the experiment



```bat

agentic-design agent --prompt-file demo-api\\prepare-prompt.txt

```



Expect a saved experiment named `api\_ubq\_motif`. This prepares the experiment;

it does not submit a job. If the agent reports an error, resolve it before

continuing. Use the actual experiment ID if it reports a different name.



\## 6. Review, approve, and launch



```bat

agentic-design experiment show api\_ubq\_motif

agentic-design experiment preview api\_ubq\_motif

```



Check that the input is `1UBQ\_clean.pdb`, the contig is

`\[20-30/A72-76/20-30]`, and the request is for two designs with `diffuser\_T: 50`.

Then approve and submit:



```bat

agentic-design experiment approve api\_ubq\_motif

agentic-design job submit api\_ubq\_motif --submission-key first-api-demo

```



Approval is a human action. The submitted worker runs on the SSH machine and

continues after the command exits.



\## 7. Monitor and collect



Copy the returned `run\_id` into this command:



```bat

set "JOB\_ID=paste-the-returned-run-id"

agentic-design job status %JOB\_ID%

```



Repeat the status command until it reports `completed` or `failed`. When

completed:



```bat

agentic-design job collect %JOB\_ID%

```



Expect two TRB/PDB pairs and `run.log` under `results\\%JOB\_ID%\\outputs`.

If the job failed, inspect the returned error before submitting again. If a

submission reply was lost, reuse the same submission key to recover that

submission; a new key requests a new run.



\## 8. Ask the API to inspect the result



```bat

agentic-design agent --resume-job %JOB\_ID% "Inspect the results and validate motif preservation against the saved input. Report both motif RMSDs and any missing evidence. Do not submit another experiment."

```



This checks motif geometry. It does not establish a validated protein candidate;

sequence design and refolding are not part of this demo.



If you open a new terminal, activate `.venv` and set the API key again.

`agentic-design job list` shows saved job IDs. Status and collection do not need

an API key.



For WSL2 instructions and more troubleshooting, see \[the full demo guide](README.md).

