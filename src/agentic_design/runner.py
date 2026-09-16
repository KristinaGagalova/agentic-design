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
    cmd = [cfg["python_bin"]]
    if cfg.get("device") == "cpu":
        # SE3Transformer's CUDA-only NVTX profiling calls crash a CPU build.
        cmd += ["-m", "agentic_design.cpu_shim"]
    cmd += [
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


def require_device(cfg: dict) -> None:
    """Fail fast when a GPU run lands on a machine without one.

    Silently falling back to CPU turns a 20-minute job into a multi-hour one,
    so CPU has to be asked for explicitly rather than inferred.
    """
    device = cfg.get("device", "cuda")
    if device == "cpu":
        return
    import torch  # deferred: the test suite runs without torch installed

    if not torch.cuda.is_available():
        raise RuntimeError(
            f"config requests device: {device}, but no GPU is visible. "
            "Set 'device: cpu' in config/paths.local.yaml to run on CPU."
        )


def run_design(req: DesignRequest) -> dict:
    """Execute a design job. Returns a JSON-safe result dict."""
    require_device(load_paths())
    outdir = results_dir() / req.name
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = build_command(req, outdir)

    # Stream to the log rather than buffering: RFdiffusion logs every timestep,
    # and a job that only reveals its output on exit cannot be monitored.
    log = outdir / "run.log"
    with log.open("w") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True)

    text = log.read_text()
    return {
        "name": req.name,
        "returncode": proc.returncode,
        "outdir": str(outdir),
        "log": str(log),
        "designs": summarize_dir(outdir) if proc.returncode == 0 else [],
        # RFdiffusion's cautious mode skips designs whose output already
        # exists, so a re-run can exit 0 having generated nothing new.
        "skipped_existing": text.count("Skipping this design"),
        "error": text[-2000:] if proc.returncode != 0 else None,
    }
