"""Strict OpenSSH transport with one quoted remote-shell boundary."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


class SSHTransport:
    def __init__(self, cfg: dict):
        required = ("host", "key_path", "remote_root", "python_bin", "rfdiffusion_root")
        missing = [key for key in required if not cfg.get(key)]
        if missing:
            raise ValueError(f"missing SSH configuration: {', '.join(missing)}")
        self.cfg = cfg
        key = Path(cfg["key_path"]).expanduser()
        if not key.is_file():
            raise ValueError(f"SSH key does not exist: {key}")
        self.base = [
            "ssh",
            "-i",
            str(key),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"ConnectTimeout={int(cfg.get('connect_timeout', 15))}",
            cfg["host"],
        ]

    def run(
        self,
        argv: list[str],
        timeout: int | None = None,
        check: bool = True,
        stdout=None,
    ):
        command = " ".join(shlex.quote(str(item)) for item in argv)
        return subprocess.run(
            self.base + [command],
            check=check,
            text=stdout is None,
            capture_output=stdout is None,
            stdout=stdout,
            timeout=timeout or int(self.cfg.get("command_timeout", 60)),
        )

    def upload(self, local: Path, remote: str) -> None:
        command = "cat > " + shlex.quote(remote)
        with local.open("rb") as source:
            subprocess.run(
                self.base + [command],
                check=True,
                stdin=source,
                capture_output=True,
                timeout=int(self.cfg.get("command_timeout", 60)),
            )
