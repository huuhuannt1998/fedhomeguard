#!/bin/bash
cd "$(dirname "$0")/.."
log(){ echo "[$(date +%H:%M:%S)] $*" >> logs/chain.log; }
while pgrep -f 'decensor_sweep.sh|run_volume.sh' >/dev/null; do sleep 60; done
log "decensor + volume drained"
log "starting k=5,8"
bash scripts/run_k58.sh >> logs/k58.log 2>&1
log "k58 done"
log "ALL REMAINING LANES COMPLETE"
