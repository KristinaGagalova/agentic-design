"""Small staged worker executed inside one isolated remote job directory."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

import yaml

from .cli import build_request
from .experiments import atomic_json, now
from .runner import build_command, run_design


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    args = parser.parse_args(argv)
    job = Path(args.job_dir).resolve()
    atomic_json(job / "worker-status.json", {"pid": os.getpid(), "started_at": now()})
    command = []
    try:
        spec = yaml.safe_load((job / "experiment.yaml").read_text())
        worker = json.loads((job / "worker.json").read_text())
        request = build_request(spec)
        cfg = {
            "rfdiffusion_root": worker["rfdiffusion_root"],
            "python_bin": worker["python_bin"],
            "device": worker["device"],
        }
        input_pdb = job / "input" / request.input_pdb if request.input_pdb else None
        command = build_command(request, job / "outputs", cfg=cfg, input_pdb=input_pdb)
        atomic_json(
            job / "result.json",
            {"state": "running", "started_at": now(), "command": command},
        )
        result = run_design(
            request, outdir=job / "outputs", cfg=cfg, input_pdb=input_pdb
        )
        result.update(
            {
                "state": "completed" if result["success"] else "failed",
                "finished_at": now(),
                "command": command,
            }
        )
        atomic_json(job / "result.json", result)
        return 0 if result["success"] else 1
    except Exception as exc:
        atomic_json(
            job / "result.json",
            {
                "state": "failed",
                "finished_at": now(),
                "command": command,
                "error": str(exc),
                "traceback": traceback.format_exc()[-4000:],
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
