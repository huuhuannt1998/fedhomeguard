#!/usr/bin/env bash
set -u; cd "$(dirname "$0")/.."
L=logs/adaptive_scale.log; : > $L
for sc in 0.5 1.0 2.0 5.0 20.0; do
  python3 scripts/exp_e2.py --partition device_derived --pseed 0 1 2 --k 2 --betas 0.2 \
    --mal-seeds 0 --k-caps "2:190" --attacks alie adaptive --scale $sc \
    --tag ADAPTIVE_SCALE --out results/scratch/adaptive/sc_$sc.jsonl >>$L 2>&1
  echo "[$(date +%H:%M:%S)] done scale=$sc" | tee -a $L
done
echo "[$(date +%H:%M:%S)] scale sweep complete" | tee -a $L
