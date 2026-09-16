"""Thin CLI so runs are reproducible from a shell and from an agent.

    python -m agentic_design.cli config/runs/smoke.yaml
"""
import argparse
import json
import sys
import yaml

from .runner import DesignRequest, run_design


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run an RFdiffusion job from a YAML spec.")
    ap.add_argument("spec", help="path to a config/runs/*.yaml file")
    ap.add_argument("--dry-run", action="store_true", help="print the command only")
    args = ap.parse_args(argv)

    spec = yaml.safe_load(open(args.spec))
    req = DesignRequest(
        name=spec["name"],
        contigs=spec["contigs"],
        num_designs=spec.get("num_designs", 1),
        diffuser_T=spec.get("diffuser_T", 50),
        input_pdb=spec.get("input_pdb"),
        hotspot_res=spec.get("hotspot_res"),
    )

    if args.dry_run:
        from pathlib import Path
        from .runner import build_command
        print(" ".join(build_command(req, Path("results") / req.name)))
        return 0

    result = run_design(req)
    json.dump(result, sys.stdout, indent=2)
    print()
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
