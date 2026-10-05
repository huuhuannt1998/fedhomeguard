#!/usr/bin/env bash
# Backfill the two clean-baseline cells that the empty --mal bug killed. Uses a
# separate compose project name so it cannot collide with the sweep still running.
set -u
cd "$(dirname "$0")/.."
M=logs/realstack_baseline.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
for PART in device_derived iid; do
  TAG="${PART}_none_m0"
  [ -f "results/realstack/${TAG}.json" ] && { log "skip $TAG"; continue; }
  log "run $TAG"
  python3 scripts/gen_compose.py --root data/households/${PART}_s0_N20 --N 20 \
    --attack none --rounds 15 --tag "$TAG" --out docker/compose.base.yml >> $M 2>&1
  docker compose -p rsbase -f docker/compose.base.yml up \
    --abort-on-container-exit --exit-code-from server >> $M 2>&1
  docker compose -p rsbase -f docker/compose.base.yml down -v >> $M 2>&1
done
log "BASELINE COMPLETE"
