"""Tests that run without a GPU, weights, or RFdiffusion installed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
