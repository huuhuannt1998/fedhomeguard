#!/usr/bin/env bash
# W7/E5: leave-one-device-out. The default protocol takes a time-ordered tail
# within each device, so every test device is also a training device -- it
# measures generalisation across time, not across devices, which is what a
# federated IDS is deployed to do. Ten folds, one per IoT-23 capture.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/lodo.log; : > $L
B="0 0.05 0.1 0.2 0.3 0.4"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
: > results/canonical/e16_lodo.jsonl
log "=== leave-one-device-out, 10 folds ==="
for d in 0 1 2 3 4 5 6 7 8 9; do
  for P in iid device_derived; do
    $PY scripts/exp_e2.py --partition $P --tag LODO_d${d} --pseed 0 1 2 --k 1 \
        --betas $B --lodo $d --k-caps "1:20" \
        --out results/scratch/lodo_${P}_${d}.jsonl >>$L 2>&1 \
      && cat results/scratch/lodo_${P}_${d}.jsonl >> results/canonical/e16_lodo.jsonl \
      || log "  FAILED fold=$d $P"
  done
  log "  fold $d done ($(grep -c '^{' results/canonical/e16_lodo.jsonl) rows)"
done
log "=== complete ==="
