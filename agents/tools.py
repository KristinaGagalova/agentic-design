"""MCP adapter over the same validated service used by the endpoint agent."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mcp.server.fastmcp import FastMCP

from agentic_design.config import load_orchestrator
from agentic_design.jobs import JobService
from agentic_design.tools import ToolRegistry

cfg = load_orchestrator()
registry = ToolRegistry(JobService(cfg), cfg["limits"].get("max_agent_submissions", 1))
mcp = FastMCP("agentic-design")


def call(name, arguments):
    try:
        return json.dumps(
            {"ok": True, "result": registry.dispatch(name, arguments)},
            indent=2,
            default=str,
        )
    except Exception as exc:
        return json.dumps(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)}, indent=2
        )


@mcp.tool()
def list_inputs() -> str:
    return call("list_inputs", {})


@mcp.tool()
def list_examples() -> str:
    return call("list_examples", {})


@mcp.tool()
def list_experiments() -> str:
    return call("list_experiments", {})


@mcp.tool()
def save_experiment(spec: dict, description: str = "", evaluation: str = "") -> str:
    return call(
        "save_experiment",
        {"spec": spec, "description": description, "evaluation": evaluation},
    )


@mcp.tool()
def preview_experiment(experiment_id: str) -> str:
    return call("preview_experiment", {"experiment_id": experiment_id})


@mcp.tool()
def submit_experiment(experiment_id: str, submission_key: str) -> str:
    return call(
        "submit_experiment",
        {"experiment_id": experiment_id, "submission_key": submission_key},
    )


@mcp.tool()
def job_status(run_id: str) -> str:
    return call("job_status", {"run_id": run_id})


@mcp.tool()
def collect_job(run_id: str) -> str:
    return call("collect_job", {"run_id": run_id})


@mcp.tool()
def inspect_results(run_id: str) -> str:
    return call("inspect_results", {"run_id": run_id})


@mcp.tool()
def validate_motif(run_id: str, reference_pdb: str) -> str:
    return call("validate_motif", {"run_id": run_id, "reference_pdb": reference_pdb})


@mcp.tool()
def validate_binder(run_id: str, reference_pdb: str, hotspot_res: str) -> str:
    return call(
        "validate_binder",
        {"run_id": run_id, "reference_pdb": reference_pdb, "hotspot_res": hotspot_res},
    )


if __name__ == "__main__":
    mcp.run()
