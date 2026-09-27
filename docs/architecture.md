# Architecture

The endpoint-driven path, as exercised end to end on 2026-09-16.

```mermaid
flowchart TB
    subgraph client["Local client (no GPU, no torch, no rsync)"]
        direction TB
        APP["app.py<br/><i>researcher CLI</i>"]
        PROV["provider.py<br/><i>bounded chat loop</i><br/>12 turns / 8 calls / 200 KB"]
        REG["tools.py — ToolRegistry<br/><i>11 schema-validated tools</i>"]
        MCP["agents/tools.py<br/><i>MCP adapter</i>"]
        STORE["experiments.py — ExperimentStore<br/><i>immutable snapshots</i>"]
        JOBS["jobs.py — JobService<br/><i>submit / status / collect</i>"]
        TRANS["transport.py — SSHTransport<br/><i>one quoted shell boundary</i>"]
    end

    LLM["OpenRouter<br/>openai/gpt-5.6-sol"]
    HUMAN{{"HUMAN ONLY<br/>experiment approve<br/><i>no tool exists for this</i>"}}

    subgraph vm["Execution VM — 146.118.121.141, 32 cores, CPU-only"]
        direction TB
        STAGE["job dir<br/><i>staged tarball: worker + spec + input</i>"]
        WORKER["remote_worker.py<br/><i>nohup, detached</i>"]
        RF["RFdiffusion<br/>run_inference.py"]
        RESULT["result.json<br/><i>authoritative state</i>"]
    end

    RESULTS["results/&lt;run-id&gt;/outputs<br/><i>TRB + PDB pairs</i>"]
    CHECK["trb.py + validate.py<br/><i>Kabsch motif RMSD</i>"]

    APP --> PROV
    PROV <-->|"tool calls"| LLM
    PROV --> REG
    MCP --> REG
    REG -->|"save_experiment"| STORE
    STORE -->|"SHA-256 digest<br/>over spec + input"| STORE
    REG -.->|"submit_experiment<br/><b>requires approval</b>"| JOBS
    APP ==>|"CLI only"| HUMAN
    HUMAN ==>|"approval.json<br/>bound to digest"| STORE
    STORE -->|"require_approval<br/>digest must match"| JOBS
    JOBS --> TRANS
    TRANS -->|"tar + ssh"| STAGE
    STAGE --> WORKER
    WORKER -->|"build_command PURE"| RF
    RF --> RESULT
    RESULT -.->|"status: cat result.json<br/>+ kill -0 pid"| JOBS
    RESULT -.->|"collect: tar back"| RESULTS
    RESULTS --> CHECK
    CHECK -->|"inspect_results<br/>validate_motif"| REG

    classDef gate fill:#7c2d12,stroke:#ea580c,stroke-width:3px,color:#fff
    classDef ext fill:#1e3a5f,stroke:#3b82f6,color:#fff
    class HUMAN gate
    class LLM ext
```

## What the shape enforces

| Property | Mechanism |
|---|---|
| The model cannot self-approve | `approve()` is reachable only from `app.py` argparse; no tool schema exposes it |
| Approval cannot be transplanted | `approval.json` stores the SHA-256 over `{spec, input_sha256}`; `require_approval` re-checks it |
| The model cannot flood the VM | `ToolRegistry` counts against `max_agent_submissions: 1` |
| Execution target is swappable | `build_command()` is pure; the worker passes explicit `cfg` and POSIX paths |
| Ambiguity is never success | SSH exit 255 maps to `unknown`, not `failed`; `collect` demands fresh named TRB/PDB pairs and zero skips |

## Sequence

```mermaid
sequenceDiagram
    autonumber
    actor R as Researcher
    participant C as Client
    participant M as Model
    participant V as Execution VM

    R->>C: agent --prompt-file
    C->>M: prompt + tool schemas
    M->>C: save_experiment(spec)
    C->>C: snapshot + SHA-256 digest
    M->>C: preview_experiment
    C-->>R: experiment id + exact command

    Note over M: the model stops here —<br/>no approval tool exists

    R->>C: experiment approve
    C->>C: approval.json bound to digest
    R->>C: job submit
    C->>V: upload tarball, nohup worker
    V-->>C: run_id + pid

    loop until completed or failed
        C->>V: cat result.json, kill -0 pid
        V-->>C: running
    end

    V->>V: RFdiffusion writes TRB + PDB
    R->>C: job collect
    C->>V: tar outputs back
    V-->>C: TRB/PDB pairs
    C->>C: verify fresh named pairs, zero skips
    C-->>R: motif backbone RMSD
```
