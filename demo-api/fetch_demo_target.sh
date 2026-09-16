#!/usr/bin/env bash
# Use the shared demo fetcher, with an input location portable across SSH hosts.
set -euo pipefail
demo_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TARGET_DIR="${TARGET_DIR:-${demo_repo_root}/data/inputs}"
exec bash "${demo_repo_root}/demo/fetch_demo_target.sh"
