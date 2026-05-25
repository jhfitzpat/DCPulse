#!/usr/bin/env bash
# Deprecated wrapper — use scripts/run-monthly.sh. Kept for existing cron/systemd paths.
exec "$(cd "$(dirname "$0")" && pwd)/run-monthly.sh" "$@"
