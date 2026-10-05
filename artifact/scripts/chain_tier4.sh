#!/usr/bin/env bash
# Wait for rerun_all.sh, then close the coverage gap. Sequential, never concurrent:
# two sweeps at once is what caused the container OOM earlier in this session.
set -u
cd "$(dirname "$0")/.."
until grep -q "RERUN COMPLETE" logs/rerun.log 2>/dev/null; do sleep 30; done
bash scripts/rerun_tier4.sh
