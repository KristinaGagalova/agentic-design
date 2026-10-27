"""Research records and seeded repetition, without a provider or compute host."""

import asyncio
import json
import os
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from agentic_design.cli import build_request
from agentic_design.jobs import JobService
from agentic_design.notebook import Notebook
from agentic_design.research import ResearchService
from agentic_design.runner import build_command
from test_orchestration import config, copy_package, FakeTransport


def research(tmp_path):
    copy_package(tmp_path)
    cfg = config(tmp_path)
    cfg["limits"]["max_agent_submissions"] = 2
    return ResearchService(cfg, JobService(cfg, FakeTransport)), cfg


def test_repetition_preserves_seed_input_and_notebook_after_restart(tmp_path):
    service, cfg = research(tmp_path)
    inputs = tmp_path / "inputs"
    inputs.mkdir(exist_ok=True)
    (inputs / "target.pdb").write_bytes(b"original input")
    service.start_campaign("pilot", "Pilot", "Does the motif survive?")
    spec = {"name": "motif", "contigs": "[A1-2/0 4-4]", "input_pdb": "target.pdb", "seed": 42, "num_designs": 2}
    record = service.save_experiment("pilot", spec, "Test preservation", "Measure motif RMSD")
    command = service.preview_experiment("pilot", "motif")["command"]
    assert "inference.deterministic=true" in command
    assert "inference.design_startnum=42" in command
    assert "seed=42" not in command
    with pytest.raises(PermissionError):
        service.submit_experiment("pilot", "motif", "first")
    service.service.store.approve("motif")  # external human action in this fixture
    (inputs / "target.pdb").write_bytes(b"changed original")
    first = service.submit_experiment("pilot", "motif", "first")
    second = service.submit_experiment("pilot", "motif", "repeat")
    assert first["run_id"] != second["run_id"]
    # Retrying a returned key is permitted even at the session limit.
    assert service.submit_experiment("pilot", "motif", "first")["run_id"] == first["run_id"]
    assert "ssh" not in first
    for run in (first, second):
        with tarfile.open(service.service._manifest_path(run["run_id"]).with_name("execution-bundle.tar.gz")) as archive:
            assert archive.extractfile("input/target.pdb").read() == b"original input"
            assert yaml.safe_load(archive.extractfile("experiment.yaml"))["seed"] == 42
    resumed = ResearchService(cfg, JobService(cfg, FakeTransport))
    assert len(resumed.list_jobs("pilot")) == 2
    notebook = resumed.read_notebook("pilot")
    saved = next(e for e in notebook["entries"] if e["kind"] == "experiment_saved")
    assert saved["data"]["experiment"]["digest"] == record["digest"]
    assert saved["data"]["design_seeds"] == [42, 43]
    assert any(e["kind"] == "tool_failed" for e in notebook["entries"])
    assert "Test preservation" in Path(notebook["notebook"]).read_text()


def test_default_seed_corrections_and_campaign_boundaries(tmp_path):
    service, cfg = research(tmp_path)
    service.start_campaign("one", "One", "Question one")
    service.start_campaign("two", "Two", "Question two")
    record = service.save_experiment("one", {"name": "x", "contigs": "[4-4]"}, "Pilot", "Check outputs")
    assert record["spec"]["seed"] == 0
    before = service.read_notebook("one")["entries"]
    service.add_note("one", "Earlier interpretation was inconclusive.", "correction")
    assert service.read_notebook("one")["entries"][:-1] == before
    with pytest.raises(ValueError, match="not recorded"):
        service.preview_experiment("two", "x")
    with pytest.raises(ValueError, match="new experiment ID"):
        service.save_experiment("one", {"name": "x", "contigs": "[4-4]"}, "Changed purpose", "Check outputs")
    with pytest.raises(ValueError):
        service.start_campaign("../outside", "No", "No")
    with pytest.raises(ValueError):
        service.add_note("one", "Invented number", "tool_result")


def test_parallel_notebook_notes_do_not_overwrite_entries(tmp_path):
    notebook = Notebook(tmp_path / "notes")
    notebook.create("pilot", "Pilot", "Question")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: notebook.append("pilot", "interpretation", f"Note {i}"), range(12)))
    assert len(notebook.read("pilot")["entries"]) == 12


@pytest.mark.parametrize("seed", [-1, True, 0.5, "42", 2**32])
def test_invalid_seed_fails_before_submission(seed):
    with pytest.raises(ValueError, match="seed"):
        build_request({"name": "x", "contigs": "[4-4]", "seed": seed})


def test_seed_range_and_conflicting_overrides():
    with pytest.raises(ValueError, match="seed"):
        build_request({"name": "x", "contigs": "[4-4]", "seed": 2**32-1, "num_designs": 2})
    for key in ("inference.deterministic", "+inference.deterministic"):
        with pytest.raises(ValueError, match="conflicting"):
            build_request({"name": "x", "contigs": "[4-4]", "seed": 1, key: False})
    req = build_request({"name": "x", "contigs": "[4-4]", "seed": 7,
                         "inference": {"deterministic": True}})
    assert build_command(req, Path("/tmp/x")).count("inference.deterministic=true") == 1


def test_research_mcp_stdio_roundtrip(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    repo = Path(__file__).resolve().parents[1]
    cfg = config(tmp_path)
    # Absolute paths keep all fixture state out of the real research notebook.
    cfg["state"] = {key: str(tmp_path / value) for key, value in cfg["state"].items()}
    cfg["state"]["notebook_dir"] = str(tmp_path / "notebook")
    path = tmp_path / "orchestrator.yaml"
    path.write_text(yaml.safe_dump(cfg))

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(repo / "agents/research.py")],
                                       env={**os.environ, "AGENTIC_DESIGN_CONFIG": str(path)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                listing = await session.list_tools()
                names = {t.name for t in listing.tools}
                assert "save_experiment" in names and "submit_experiment" in names
                # Approval is reachable from OpenCode, but only behind an "ask"
                # confirmation; test_approval_permission_stays_ask guards that.
                assert "approve_experiment" in names
                started = await session.call_tool("start_campaign", {"campaign_id": "mcp-pilot", "title": "Pilot", "question": "Question"})
                assert not started.isError
                saved = await session.call_tool("save_experiment", {
                    "campaign_id": "mcp-pilot", "spec": {"name": "x", "contigs": "[4-4]", "seed": 73},
                    "purpose": "Transport test", "evaluation": "No scientific claim",
                })
                assert not saved.isError
                denied = await session.call_tool("submit_experiment", {
                    "campaign_id": "mcp-pilot", "experiment_id": "x", "submission_key": "unapproved",
                })
                assert denied.isError
                notebook = await session.call_tool("read_notebook", {"campaign_id": "mcp-pilot"})
                assert not notebook.isError
    asyncio.run(exercise())
    experiment = json.loads((tmp_path / "state/experiments/x/experiment.json").read_text())
    assert experiment["spec"]["seed"] == 73
    assert not (tmp_path / "state/experiments/x/approval.json").exists()


class ProgressTransport:
    """A running job that has written one of two designs."""

    def __init__(self, cfg, written=("motif_42",), partial=("motif_43",), skipped=0):
        self.cfg = cfg
        self.written, self.partial, self.skipped = written, partial, skipped

    def upload(self, local, remote):
        pass

    def run(self, argv, **kwargs):
        joined = " ".join(argv)
        if argv[0] == "ls":
            names = [f"{s}.trb" for s in self.written]
            names += [f"{s}.pdb" for s in (*self.written, *self.partial)]
            return SimpleNamespace(returncode=0, stdout="run.log\n" + "\n".join(names), stderr="")
        if argv[0] == "grep":
            return SimpleNamespace(returncode=0 if self.skipped else 1,
                                   stdout=f"{self.skipped}\n", stderr="")
        if argv[0] == "tail":
            return SimpleNamespace(returncode=0, stdout="  50/50 timesteps\n", stderr="")
        if argv[0] == "cat" and "result.json" in joined:
            # Still running: no terminal result manifest yet.
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if argv[0] == "cat" and "worker-status.json" in joined:
            return SimpleNamespace(returncode=0, stdout='{"pid": 4242}', stderr="")
        # `kill -0` succeeds: the worker is alive, so the state stays "running".
        return SimpleNamespace(returncode=0, stdout="4242\n", stderr="")


def progress_job(tmp_path, transport):
    service, _ = research(tmp_path)
    service.service.transport_factory = transport
    inputs = tmp_path / "inputs"
    inputs.mkdir(exist_ok=True)
    (inputs / "target.pdb").write_bytes(b"input")
    service.start_campaign("prog", "Progress", "How far along is it?")
    service.save_experiment("prog", {"name": "motif", "contigs": "[4-4]",
                                     "input_pdb": "target.pdb", "seed": 42, "num_designs": 2},
                            "Progress test", "No scientific claim")
    service.service.store.approve("motif")
    return service, service.submit_experiment("prog", "motif", "k1")["run_id"]


def test_progress_counts_written_designs_without_collecting(tmp_path):
    service, run_id = progress_job(tmp_path, ProgressTransport)
    report = service.job_progress("prog", run_id)
    assert report["designs_expected"] == 2
    assert report["designs_written"] == 1
    assert report["written_indices"] == [42]
    assert report["in_progress_indices"] == [43]
    assert report["pending_indices"] == []
    assert report["collected"] is False
    assert "50/50 timesteps" in report["last_log_line"]
    # Progress must never stand in for verified results.
    assert not (Path(service.service.results_root) / run_id).exists()
    kinds = [(e["kind"], e["text"]) for e in service.notebook.read("prog")["entries"]]
    assert ("tool_result", "job_progress") in kinds


def test_progress_surfaces_cautious_mode_skips(tmp_path):
    """RFdiffusion skipping existing designs exits 0 and must not read as progress."""
    def skipping(cfg):
        return ProgressTransport(cfg, written=("motif_42", "motif_43"), partial=(), skipped=2)
    service, run_id = progress_job(tmp_path, skipping)
    report = service.job_progress("prog", run_id)
    assert report["designs_written"] == 2
    assert report["skipped_existing"] == 2


def _permission_sources():
    """Both places that govern the co-scientist profile's permissions."""
    repo = Path(__file__).resolve().parents[1]
    project = json.loads((repo / "opencode.json").read_text())["permission"]
    front = (repo / ".opencode/agents/co-scientist.md").read_text().split("---")[1]
    return project, yaml.safe_load(front)["permission"]


def test_approval_permission_stays_ask():
    """The researcher must see a confirmation; `allow` would be silent self-approval."""
    for permission in _permission_sources():
        assert permission["research_approve_experiment"] == "ask"


def test_capability_tools_stay_ask():
    """The profile has a shell, so these confirmations are what protects approval.

    With `bash` set to `allow` the agent could run the approve CLI, write
    approval.json, or edit these permission files, and every other control in
    this project would become advisory.
    """
    for permission in _permission_sources():
        for tool in ("bash", "edit", "write", "patch", "apply_patch"):
            assert permission[tool] == "ask", tool
        assert permission["*"] == "deny"
        # Delegation would run tool calls that never reach the researcher.
        assert permission.get("task", "deny") == "deny"


def test_approval_records_the_surface_that_granted_it(tmp_path):
    """An approval carries how it was granted, and still binds to the spec digest."""
    service, _ = research(tmp_path)
    service.start_campaign("surface", "Surface", "Which surface approved it?")
    service.save_experiment("surface", {"name": "s", "contigs": "[4-4]", "seed": 5},
                            "Approval surface test", "No scientific claim")
    approval = service.approve_experiment("surface", "s")
    assert approval["approved_via"] == "opencode_confirmed"
    record = service.service.store.load("s")
    assert approval["digest"] == record["digest"]
    # The notebook keeps the approval as a recorded tool result, not a silent write.
    kinds = [(e["kind"], e["text"]) for e in service.notebook.read("surface")["entries"]]
    assert ("tool_result", "approve_experiment") in kinds
