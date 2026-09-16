"""Run an RFdiffusion entrypoint on a CPU-only torch build.

    python -m agentic_design.cpu_shim /path/to/run_inference.py <hydra args>

SE3Transformer annotates its hot paths with `torch.cuda.nvtx.range`, imported
directly at module scope in four files under `env/SE3Transformer/`. On a
CPU-only torch build those calls raise "NVTX functions not installed", so
inference dies inside the first forward pass rather than at import.

The annotations are profiling markers with no effect on results. Replacing the
push/pop primitives with no-ops is enough: `range` resolves them from module
globals when the context manager is entered, so this works even though the
importing modules already hold a reference to `range` itself.

Patching here rather than editing the RFdiffusion checkout keeps the workaround
in version control and leaves the upstream install pristine.
"""
import runpy
import sys

import torch

torch.cuda.nvtx.range_push = lambda *args, **kwargs: None
torch.cuda.nvtx.range_pop = lambda *args, **kwargs: None

if len(sys.argv) < 2:
    raise SystemExit("usage: python -m agentic_design.cpu_shim <script.py> [args]")

# Hand the target script the argv it would have seen if invoked directly;
# Hydra reads sys.argv for overrides and uses argv[0] as the job name.
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
