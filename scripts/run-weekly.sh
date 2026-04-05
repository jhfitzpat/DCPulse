#!/usr/bin/env bash
# Weekly DC Pulse runner for cron/systemd. Copy to repo root as run-dc-pulse.sh if you prefer a single path.
# Logs to logs/dc-pulse.log and optionally archives last_digest.txt under archive/ (YYYY-MM-DD.txt).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="${DC_PULSE_LOG_DIR:-$REPO_ROOT/logs}"
ARCHIVE_DIR="${DC_PULSE_ARCHIVE_DIR:-$REPO_ROOT/archive}"
LOG_FILE="${DC_PULSE_LOG_FILE:-$LOG_DIR/dc-pulse.log}"
PYTHON="${DC_PULSE_PYTHON:-$REPO_ROOT/.venv/bin/python}"

mkdir -p "$LOG_DIR" "$ARCHIVE_DIR"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

exec >>"$LOG_FILE" 2>&1
echo "===== $(ts) DC Pulse start ====="
if [[ ! -f "$PYTHON" ]]; then
  echo "Python not found: $PYTHON" >&2
  exit 1
fi
set +e
"$PYTHON" -m src.main
ec=$?
set -e
echo "===== $(ts) DC Pulse exit $ec ====="
if [[ "$ec" -eq 0 ]] && [[ -f "$REPO_ROOT/last_digest.txt" ]]; then
  cp -f "$REPO_ROOT/last_digest.txt" "$ARCHIVE_DIR/$(date -u +%F).txt" || true
fi
exit "$ec"
