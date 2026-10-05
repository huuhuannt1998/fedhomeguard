#!/bin/bash
# Waits for the P0 lanes to drain, then runs the remaining P1 lanes one at a time so
# the machine is never oversubscribed. Every lane is resumable, so a kill is safe.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
log() { echo "[$(date +%H:%M:%S)] $*" >> logs/supervisor.log; }

log "waiting for e2/e3/e7 to drain"
while pgrep -f 'exp_e2.py|exp_e3_defenses.py|queue_p1.sh' >/dev/null; do sleep 60; done
log "P0 lanes done"

for lane in e9 e10 e11; do
  log "starting $lane"
  bash scripts/queue_p1.sh $lane >> logs/${lane}.log 2>&1
  log "finished $lane"
done

log "E13 attack-strength sweep"
for P in device_derived iid; do
  python3 scripts/exp_e3_defenses.py --partition $P --pseed 0 1 2 \
    --betas 0.1 0.2 --mal-seeds 0 --scales 0.5 1.0 5.0 \
    --defenses norm_clip median multikrum \
    --out results/canonical/e13_${P}.jsonl >> logs/e13.log 2>&1
done
log "E13 done"

log "E4 high-influence malicious sets"
for P in device_derived iid; do
  python3 scripts/exp_e2.py --partition $P --pseed 0 1 2 --k 1 2 \
    --betas 0.05 0.1 0.2 0.3 0.4 --mal-mode high_volume rare_device \
    --k-caps "1:20,2:190" --out results/canonical/e4_highinf_${P}.jsonl \
    >> logs/e4_highinf.log 2>&1
done
log "ALL P1 LANES COMPLETE"
