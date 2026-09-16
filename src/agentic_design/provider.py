"""Bounded OpenAI-compatible Chat Completions agent loop."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .config import api_key
from .experiments import atomic_json, now
from .tools import TOOL_SCHEMAS, ToolRegistry

SYSTEM_PROMPT = """You help a researcher define RFdiffusion backbone experiments. Use tools to inspect inputs and save a precise experiment. A saved experiment is not approved. Only a human CLI action can approve its exact digest. Never claim a backbone is a validated protein candidate; report structural checks separately."""


class ChatCompletionsClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        provider = self.cfg["provider"]
        parameters = dict(provider.get("parameters", {}))
        for reserved in ("model", "messages", "tools", "tool_choice"):
            parameters.pop(reserved, None)
        payload = {
            **parameters,
            "model": provider["model"],
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        request = urllib.request.Request(
            provider["base_url"].rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {api_key(self.cfg)}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=int(provider.get("timeout", 120))
            ) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"provider returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"provider request failed: {exc.reason}") from exc
        try:
            return result["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("provider response has no assistant message") from exc


def run_agent(cfg: dict, registry: ToolRegistry, prompt: str, client=None) -> dict:
    limits = cfg["limits"]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    client = client or ChatCompletionsClient(cfg)
    audit = {
        "started_at": now(),
        "model": cfg["provider"]["model"],
        "messages": messages,
    }
    audit_path = (
        Path(cfg["repo_root"])
        / cfg["state"]["audit_dir"]
        / f"agent-{now().replace(':', '-')}.json"
    )
    max_bytes = int(limits.get("max_transcript_bytes", 200000))
    try:
        for _ in range(int(limits.get("max_agent_turns", 12))):
            if len(json.dumps(messages)) > max_bytes:
                raise RuntimeError("agent transcript limit reached")
            assistant = client.complete(messages, TOOL_SCHEMAS)
            if not isinstance(assistant, dict) or assistant.get("role") not in (
                None,
                "assistant",
            ):
                raise RuntimeError("provider returned a malformed assistant message")
            calls = assistant.get("tool_calls") or []
            if not isinstance(calls, list):
                raise RuntimeError("provider returned malformed tool calls")
            ids = [call.get("id") for call in calls if isinstance(call, dict)]
            if (
                len(ids) != len(calls)
                or any(not isinstance(i, str) or not i for i in ids)
                or len(set(ids)) != len(ids)
            ):
                raise RuntimeError(
                    "provider returned missing or duplicate tool-call IDs"
                )
            messages.append(assistant)  # preserves provider-specific reasoning metadata
            if len(json.dumps(messages)) > max_bytes:
                raise RuntimeError("agent transcript limit reached")
            if not calls:
                return {
                    "content": assistant.get("content", ""),
                    "audit": str(audit_path),
                }
            if len(calls) > int(limits.get("max_tool_calls_per_turn", 8)):
                raise RuntimeError("provider exceeded tool-call limit")
            for call in calls:
                function = call.get("function")
                if (
                    not isinstance(function, dict)
                    or not isinstance(function.get("name"), str)
                    or not isinstance(function.get("arguments", "{}"), str)
                ):
                    raise RuntimeError("provider returned a malformed function call")
            for call in calls:
                function = call["function"]
                output = registry.safe_dispatch(
                    function["name"], function.get("arguments", "{}")
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call["id"], "content": output}
                )
        raise RuntimeError("agent turn limit reached")
    except Exception as exc:
        audit["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        audit.update({"finished_at": now(), "messages": messages})
        atomic_json(audit_path, audit)
