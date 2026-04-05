#!/usr/bin/env bash
# Bootstrap DC Pulse on Debian (or similar). Run once on the VM after cloning or from a fresh directory.
# Usage: ./scripts/setup-vm.sh [REPO_URL] [TARGET_DIR]
# Example: ./scripts/setup-vm.sh git@github.com:you/DCPulse.git ~/DCPulse
set -euo pipefail

REPO_URL="${1:-}"
TARGET_DIR="${2:-$HOME/DCPulse}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ -n "$REPO_URL" ]]; then
  if [[ -e "$TARGET_DIR" ]]; then
    echo "Target $TARGET_DIR already exists; remove it or omit clone URL to configure an existing tree." >&2
    exit 1
  fi
  git clone "$REPO_URL" "$TARGET_DIR"
elif [[ ! -d "$TARGET_DIR" ]]; then
  echo "Directory $TARGET_DIR does not exist. Pass a git URL as the first argument to clone, or clone manually." >&2
  exit 1
fi

cd "$TARGET_DIR"

if ! command -v "$PYTHON_BIN" &>/dev/null; then
  echo "Python not found: $PYTHON_BIN" >&2
  echo "Install 3.12 (e.g. apt install python3.12 python3.12-venv) or set PYTHON_BIN to an available interpreter." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp -n .env.example .env 2>/dev/null || true
  echo "Edit .env with your secrets, then: chmod 600 .env" >&2
fi

echo "Setup complete. Configure .env, then test: ./.venv/bin/python -m src.main --print --dry-run"
