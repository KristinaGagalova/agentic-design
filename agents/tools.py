"""MCP server exposing the design pipeline as agent tools.

Run with:  python agents/tools.py
Requires:  pip install "mcp[cli]"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from agentic_design.runner import DesignRequest, run_design  # noqa: E402
from agentic_design.trb import summarize_dir  # noqa: E402
from agentic_design.validate import check_binder, check_motif  # noqa: E402

mcp = FastMCP("agentic-design")


@mcp.tool()
def diffuse(name: str, contigs: str, num_designs: int = 1,
            diffuser_T: int = 50, input_pdb: str = "",
            hotspot_res: str = "") -> str:
    """Generate backbones with RFdiffusion.

    contigs: RFdiffusion contig string, e.g. "[100-100]" for a 100-mer,
             or "[A1-150/0 70-100]" for a binder against chain A.
    Returns JSON with per-design summaries parsed from the .trb files.
    """
    req = DesignRequest(
        name=name, contigs=contigs, num_designs=num_designs,
        diffuser_T=diffuser_T,
        input_pdb=input_pdb or None,
        hotspot_res=hotspot_res or None,
    )
    return json.dumps(run_design(req), indent=2)


@mcp.tool()
def inspect_results(run_name: str) -> str:
    """Summarize the designs produced by a previous run."""
    return json.dumps(summarize_dir(Path("results") / run_name), indent=2)


@mcp.tool()
def validate_motif(run_name: str, reference_pdb: str) -> str:
    """Check that a motif-scaffolding run preserved the motif it was given.

    reference_pdb: the input_pdb the run was conditioned on.
    Returns per-design backbone RMSD between the motif as supplied and as
    built. A run can exit cleanly and still have moved the motif, so treat
    this as the acceptance check rather than the exit code.
    """
    outdir = Path("results") / run_name
    return json.dumps([
        check_motif(trb, trb.with_suffix(".pdb"), reference_pdb)
        for trb in sorted(outdir.glob("*.trb"))
    ], indent=2)


@mcp.tool()
def validate_binder(run_name: str, reference_pdb: str, hotspot_res: str) -> str:
    """Score a binder run: was the target held, and did the binder hit the hotspots?

    hotspot_res: the same string the run spec used, e.g. "[A8,A44,A70]".
    Hotspots bias RFdiffusion rather than constraining it, so a clean exit does
    not mean the binder engaged the intended surface. Rank designs by how many
    hotspots they contact and how large the interface is.
    """
    outdir = Path("results") / run_name
    return json.dumps([
        check_binder(pdb, reference_pdb, hotspot_res)
        for pdb in sorted(outdir.glob("*.pdb"))
    ], indent=2)


if __name__ == "__main__":
    mcp.run()
