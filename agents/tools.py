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


if __name__ == "__main__":
    mcp.run()
