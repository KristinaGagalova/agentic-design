"""Run RFdiffusion as a subprocess and return structured results.

Backends are swappable: `local` shells out to the venv on this machine,
`remote` is a stub for when you move to a rented GPU. Agent-facing code
calls run_design() and should not care which is active.
"""
from dataclasses import dataclass, field
from pathlib import Path
import subprocess

from .paths import load_paths, results_dir, REPO_ROOT
from .trb import summarize_dir


@dataclass
class DesignRequest:
    name: str
    contigs: str
    num_designs: int = 1
    diffuser_T: int = 50
    input_pdb: str | None = None
    hotspot_res: str | None = None
    extra: dict = field(default_factory=dict)


def build_command(req: DesignRequest, outdir: Path) -> list[str]:
    cfg = load_paths()
    root = Path(cfg["rfdiffusion_root"])
    cmd = [
        cfg["python_bin"],
        str(root / "scripts" / "run_inference.py"),
        f"inference.output_prefix={outdir}/{req.name}",
        f"contigmap.contigs={req.contigs}",
        f"inference.num_designs={req.num_designs}",
        f"diffuser.T={req.diffuser_T}",
    ]
    if req.input_pdb:
        cmd.append(f"inference.input_pdb={REPO_ROOT / req.input_pdb}")
    if req.hotspot_res:
        cmd.append(f"ppi.hotspot_res={req.hotspot_res}")
    for k, v in req.extra.items():
        cmd.append(f"{k}={v}")
    return cmd


def run_design(req: DesignRequest) -> dict:
    """Execute a design job. Returns a JSON-safe result dict."""
    outdir = results_dir() / req.name
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = build_command(req, outdir)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = outdir / "run.log"
    log.write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr)

    return {
        "name": req.name,
        "returncode": proc.returncode,
        "outdir": str(outdir),
        "log": str(log),
        "designs": summarize_dir(outdir) if proc.returncode == 0 else [],
        "error": proc.stderr[-2000:] if proc.returncode != 0 else None,
    }
