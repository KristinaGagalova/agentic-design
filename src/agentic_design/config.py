"""Operator-owned orchestration configuration."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from .paths import REPO_ROOT


def _merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_orchestrator(path: str | Path | None = None) -> dict:
    base_path = Path(path) if path else REPO_ROOT / "config" / "orchestrator.yaml"
    cfg = yaml.safe_load(base_path.read_text()) or {}
    local = base_path.with_name("orchestrator.local.yaml")
    if path is None and local.exists():
        cfg = _merge(cfg, yaml.safe_load(local.read_text()) or {})
    cfg["repo_root"] = str(REPO_ROOT)
    return cfg


def api_key(cfg: dict) -> str:
    variable = cfg["provider"].get("api_key_env", "OPENROUTER_API_KEY")
    value = os.environ.get(variable)
    if not value:
        raise RuntimeError(f"provider API key is missing; set {variable}")
    return value
