#!/usr/bin/env bash
# Portable entry point; resolve project-relative paths from any caller directory.
cd "$(dirname "$0")/.." || exit 2
if ! command -v flock >/dev/null 2>&1; then
    echo "Required command 'flock' is unavailable; cannot safely prevent overlapping Mininet runs." >&2
    exit 2
fi
lock_path="${TMPDIR:-/tmp}/medroute-fresh-run-demo.lock"
exec 9>"$lock_path"
if ! flock -n 9; then
    echo "Another MedRoute experiment is already running; refusing to start a second Mininet network." >&2
    exit 2
fi
node scripts/run_demo.js
