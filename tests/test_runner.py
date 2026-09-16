"""Tests that run without a GPU, weights, or RFdiffusion installed."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_design import runner
from agentic_design.cli import build_request
from agentic_design.runner import DesignRequest, build_command


def test_command_contains_core_flags(tmp_path):
    req = DesignRequest(name="t", contigs="[40-40]", num_designs=2)
    cmd = " ".join(build_command(req, tmp_path))
    assert "run_inference.py" in cmd
    assert "contigmap.contigs=[40-40]" in cmd
    assert "inference.num_designs=2" in cmd


def test_hotspots_only_when_given(tmp_path):
    plain = " ".join(build_command(
        DesignRequest(name="t", contigs="[40-40]"), tmp_path))
    assert "hotspot_res" not in plain

    ppi = " ".join(build_command(
        DesignRequest(name="t", contigs="[A1-50/0 30-40]",
                      hotspot_res="[A10,A12]"), tmp_path))
    assert "ppi.hotspot_res=[A10,A12]" in ppi


def test_cpu_shim_is_gated_on_device(tmp_path, monkeypatch):
    """The shim fixes a CPU-only crash; on a GPU box it must not be injected."""
    req = DesignRequest(name="t", contigs="[40-40]")

    monkeypatch.setattr(runner, "load_paths", lambda: {
        "rfdiffusion_root": "/rf", "python_bin": "py", "device": "cpu"})
    assert build_command(req, tmp_path)[:3] == ["py", "-m", "agentic_design.cpu_shim"]

    monkeypatch.setattr(runner, "load_paths", lambda: {
        "rfdiffusion_root": "/rf", "python_bin": "py", "device": "cuda"})
    assert build_command(req, tmp_path)[1] == "/rf/scripts/run_inference.py"


def test_cpu_must_be_opted_into_explicitly():
    """A GPU-targeted config must abort, not quietly run 50-100x slower."""
    runner.require_device({"device": "cpu"})  # explicit opt-in, no GPU needed

    import torch

    if not torch.cuda.is_available():
        with pytest.raises(RuntimeError, match="no GPU is visible"):
            runner.require_device({"device": "cuda"})
        with pytest.raises(RuntimeError, match="no GPU is visible"):
            runner.require_device({})  # default is GPU


def test_nested_spec_blocks_reach_the_command(tmp_path):
    """Nested YAML blocks used to be dropped silently, losing run settings."""
    req = build_request({
        "name": "t", "contigs": "[40-40]",
        "denoiser": {"noise_scale_ca": 0, "noise_scale_frame": 0},
        "diffuser": {"partial_T": 10},
    })
    cmd = " ".join(build_command(req, tmp_path))
    assert "denoiser.noise_scale_ca=0" in cmd
    assert "denoiser.noise_scale_frame=0" in cmd
    assert "diffuser.partial_T=10" in cmd
