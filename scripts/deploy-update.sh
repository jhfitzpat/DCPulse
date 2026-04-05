#!/usr/bin/env bash
# Manually sync local repo to the VM (Git Bash / WSL / Linux / macOS).
# Environment: DC_PULSE_VM_HOST, DC_PULSE_VM_PATH (required); optional DC_PULSE_SSH_USER,
# DC_PULSE_DEPLOY_MODE (git|rsync, default git), DC_PULSE_GIT_BRANCH (default main).
set -euo pipefail

MODE="${DC_PULSE_DEPLOY_MODE:-git}"
BRANCH="${DC_PULSE_GIT_BRANCH:-main}"
VM_HOST="${DC_PULSE_VM_HOST:-}"
REMOTE_PATH="${DC_PULSE_VM_PATH:-}"
SSH_USER="${DC_PULSE_SSH_USER:-}"

if [[ -z "$VM_HOST" || -z "$REMOTE_PATH" ]]; then
  echo "Set DC_PULSE_VM_HOST and DC_PULSE_VM_PATH" >&2
  exit 1
fi

SSH_TARGET="${SSH_USER:+$SSH_USER@}$VM_HOST"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$MODE" == "git" ]]; then
  echo "Remote: git pull on $SSH_TARGET:$REMOTE_PATH (push from this machine first)"
  ssh "$SSH_TARGET" "set -e; cd '$REMOTE_PATH'; git fetch origin; git checkout '$BRANCH'; git pull --ff-only; .venv/bin/pip install -q -r requirements.txt"
  echo "Done."
  exit 0
fi

if [[ "$MODE" == "rsync" ]]; then
  echo "rsync $REPO_ROOT/ -> $SSH_TARGET:$REMOTE_PATH/"
  rsync -avz \
    --exclude=.git/ --exclude=.venv/ --exclude=.env \
    --exclude=__pycache__/ --exclude=.cursor/ --exclude=last_digest.txt \
    --exclude=logs/ --exclude=archive/ --exclude=.pytest_cache/ \
    --exclude=.mypy_cache/ --exclude=.ruff_cache/ --exclude='*.egg-info/' \
    "$REPO_ROOT/" "$SSH_TARGET:$REMOTE_PATH/"
  ssh "$SSH_TARGET" "set -e; cd '$REMOTE_PATH'; .venv/bin/pip install -q -r requirements.txt"
  echo "Done."
  exit 0
fi

echo "Unknown DC_PULSE_DEPLOY_MODE: $MODE (use git or rsync)" >&2
exit 1
