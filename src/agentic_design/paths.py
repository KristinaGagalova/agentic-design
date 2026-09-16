"""Resolve machine-specific paths from config, never hardcoded."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_paths() -> dict:
    """paths.local.yaml wins over paths.yaml when present."""
    local = REPO_ROOT / "config" / "paths.local.yaml"
    shared = REPO_ROOT / "config" / "paths.yaml"
    cfg = yaml.safe_load(shared.read_text())
    if local.exists():
        cfg.update(yaml.safe_load(local.read_text()) or {})
    return cfg


def results_dir() -> Path:
    d = REPO_ROOT / load_paths()["results_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d
