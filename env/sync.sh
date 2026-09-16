#!/usr/bin/env bash
# Move the repo to the execution VM and results back.
#
#     bash env/sync.sh push    # local repo  -> VM (excludes .git, results)
#     bash env/sync.sh pull    # VM results  -> local
#     bash env/sync.sh run config/runs/smoke.yaml [--dry-run]
#     bash env/sync.sh watch smoke        # follow a running job's log
#     bash env/sync.sh progress smoke     # one-line status of a running job
#     bash env/sync.sh test               # run the test suite on the VM
#
# Connection details come from project.env at the repo root (gitignored).
# Copy project.env.example and fill it in. Environment variables still win.
#
# tar-over-ssh rather than rsync: rsync needs to exist on both ends, and the
# Git Bash environment on Windows has no rsync.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$REPO_ROOT/project.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    . "$REPO_ROOT/project.env"
    set +a
fi

: "${REMOTE:?not set. Copy project.env.example to project.env and fill it in.}"
: "${SSH_KEY:?not set. Copy project.env.example to project.env and fill it in.}"
REMOTE_ROOT="${REMOTE_ROOT:-/mnt/src/agentic-design}"
REMOTE_PYTHON="${REMOTE_PYTHON:-/mnt/src/rfdiff-venv/bin/python}"

SSH=(ssh -o BatchMode=yes -i "$SSH_KEY" "$REMOTE")

case "${1:-}" in
push)
    "${SSH[@]}" "mkdir -p '$REMOTE_ROOT'"
    tar czf - -C "$REPO_ROOT" \
        --exclude=.git --exclude=results --exclude=__pycache__ \
        --exclude='*.pyc' --exclude=.pytest_cache . \
    | "${SSH[@]}" "tar xzf - -C '$REMOTE_ROOT'"
    echo "pushed $REPO_ROOT -> $REMOTE:$REMOTE_ROOT"
    ;;
pull)
    mkdir -p "$REPO_ROOT/results"
    # Guard the empty case: tar on a missing directory would abort the pipe.
    "${SSH[@]}" "[ -d '$REMOTE_ROOT/results' ] && tar czf - -C '$REMOTE_ROOT' results || true" \
    | tar xzf - -C "$REPO_ROOT"
    echo "pulled $REMOTE:$REMOTE_ROOT/results -> $REPO_ROOT/results"
    ;;
run)
    shift
    "${SSH[@]}" "cd '$REMOTE_ROOT' && PYTHONPATH=src '$REMOTE_PYTHON' -m agentic_design.cli $*"
    ;;
test)
    "${SSH[@]}" "cd '$REMOTE_ROOT' && PYTHONPATH=src '$REMOTE_PYTHON' -m pytest tests/ -q"
    ;;
watch)
    "${SSH[@]}" -t "tail -f '$REMOTE_ROOT/results/${2:?run name required}/run.log'"
    ;;
progress)
    # RFdiffusion counts timesteps down to 1 per design, so the last one seen
    # is the position within the design currently being built.
    "${SSH[@]}" "
        log='$REMOTE_ROOT/results/${2:?run name required}/run.log'
        [ -f \"\$log\" ] || { echo 'no log yet'; exit 0; }
        echo \"designs started: \$(grep -c 'Making design' \"\$log\")\"
        echo \"last line: \$(grep -oE 'Timestep [0-9]+|Finished design in .*' \"\$log\" | tail -1)\"
        echo \"updated: \$(( \$(date +%s) - \$(stat -c %Y \"\$log\") ))s ago\"
    "
    ;;
*)
    echo "usage: $0 {push|pull|run <spec> [args]|watch <name>|progress <name>|test}" >&2
    exit 2
    ;;
esac
