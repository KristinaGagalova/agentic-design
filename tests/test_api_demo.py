"""Exercise the API demo through real HTTP, without a paid endpoint or SSH."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

import yaml

from agentic_design.config import load_orchestrator
from agentic_design.jobs import JobService
from agentic_design.provider import run_agent
from agentic_design.tools import TOOL_SCHEMAS, ToolRegistry


def tool_call(identifier, name, arguments):
    return {
        "id": identifier,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def test_demo_preparation_over_http_cannot_approve_or_submit(tmp_path, monkeypatch):
    """A tool-capable endpoint can prepare the real example but cannot self-approve."""
    repository = Path(__file__).resolve().parents[1]
    cfg = deepcopy(load_orchestrator(repository / "config" / "orchestrator.yaml"))
    cfg["repo_root"] = str(tmp_path)
    cfg["state"]["examples_dir"] = str(repository / "demo-api")
    inputs = tmp_path / cfg["state"]["inputs_dir"]
    inputs.mkdir(parents=True)
    # Input bytes are snapshotted here, not executed or geometrically validated.
    (inputs / "1UBQ_clean.pdb").write_text("REMARK offline transport test fixture\nEND\n")
    spec = yaml.safe_load((repository / "demo-api" / "ubq_motif.yaml").read_text())
    spec["name"] = "api_ubq_motif"
    replies = [
        {"role": "assistant", "content": None, "tool_calls": [
            tool_call("inputs", "list_inputs", {}),
            tool_call("examples", "list_examples", {}),
        ]},
        {"role": "assistant", "content": None,
         "reasoning_details": [{"type": "reasoning.text", "text": "Inspect the demo."}],
         "tool_calls": [tool_call("save", "save_experiment", {
             "spec": spec, "description": "Existing demo through the endpoint.",
             "evaluation": "Check motif RMSD after collection; no candidate claim.",
         })]},
        {"role": "assistant", "content": None, "tool_calls": [
            tool_call("preview", "preview_experiment", {"experiment_id": spec["name"]}),
            tool_call("self-approve", "approve_experiment", {"experiment_id": spec["name"]}),
            tool_call("submit", "submit_experiment", {
                "experiment_id": spec["name"], "submission_key": "demo-first-run",
            }),
        ]},
        {"role": "assistant", "content": "Experiment prepared. Human approval is required."},
    ]
    requests = []
    headers = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            headers.append(dict(self.headers))
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            reply = {"choices": [{"message": replies[len(requests) - 1]}]}
            body = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cfg["provider"]["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
    cfg["provider"]["api_key_env"] = "DEMO_TEST_API_KEY"
    monkeypatch.setenv("DEMO_TEST_API_KEY", "offline-secret-sentinel")

    def forbidden_transport(_):
        raise AssertionError("An unapproved experiment must never contact SSH")

    service = JobService(cfg, transport_factory=forbidden_transport)
    try:
        result = run_agent(cfg, ToolRegistry(service),
                           (repository / "demo-api" / "prepare-prompt.txt").read_text())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert len(requests) == 4
    assert all(request["model"] == "openai/gpt-5.6-sol" for request in requests)
    assert requests[0]["provider"] == {
        "only": ["openai"], "allow_fallbacks": False, "require_parameters": True,
    }
    assert headers[0]["Authorization"] == "Bearer offline-secret-sentinel"
    assert any(message.get("reasoning_details") for message in requests[-1]["messages"])
    outputs = {message["tool_call_id"]: json.loads(message["content"])
               for message in requests[-1]["messages"] if message["role"] == "tool"}
    assert outputs["save"]["ok"] is True
    assert outputs["preview"]["ok"] is True
    assert outputs["self-approve"]["ok"] is False
    assert outputs["submit"]["ok"] is False
    assert outputs["submit"]["error"] == "PermissionError"
    assert not service.list()
    assert all("approve" not in tool["function"]["name"] for tool in TOOL_SCHEMAS)
    saved = service.store.load("api_ubq_motif")
    assert saved["spec"]["contigs"] == "[20-30/A72-76/20-30]"
    assert saved["input_sha256"]
    audit = Path(result["audit"]).read_text()
    assert "offline-secret-sentinel" not in audit
    assert "Human approval" in result["content"]
