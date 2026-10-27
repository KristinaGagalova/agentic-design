"""OpenCode MCP entry point. No shell or arbitrary file-write tool.

Approval is exposed here only because OpenCode is configured to ask the
researcher to confirm each `approve_experiment` call (see the agent profile in
.opencode/agents/co-scientist.md). The endpoint/API tool loop in tools.py still
has no approval action at all.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mcp.server.fastmcp import FastMCP

from agentic_design.config import load_orchestrator
from agentic_design.research import ResearchService


def create_server(config_path=None):
    service = ResearchService(load_orchestrator(config_path))
    mcp = FastMCP("protein-research")
    for name in (
        "list_campaigns", "start_campaign", "read_notebook", "add_note",
        "list_inputs", "list_examples", "save_experiment", "preview_experiment",
        "approve_experiment", "submit_experiment", "list_jobs", "job_status",
        "job_progress", "collect_job",
        "inspect_results", "validate_motif", "validate_binder",
    ):
        mcp.add_tool(getattr(service, name))
    return mcp


if __name__ == "__main__":
    create_server(os.environ.get("AGENTIC_DESIGN_CONFIG")).run()
