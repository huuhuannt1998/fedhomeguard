#!/bin/bash
# E17: the second dataset. N-BaIoT is nine real commercial devices with per-device
# attribution and labelled Gafgyt/Mirai partitions -- the same semantics IoT-23
# supplies, which is the condition the review sets for adding a dataset at all.
#
# Runs the central cells only: certified arm across the corrected beta grid, and the
# same-predictor arm at the main fractions, for IID and device-derived partitions at
# k=1,2 (both fully enumerated).
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
M=logs/nbaiot_exp.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"

log "=== certified arm ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
    --pseed 0 1 2 3 4 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" --dph 1 2 \
    --tag NBAIOT_CERT --out results/canonical/nb_cert_${P}.jsonl >> $M 2>&1 || log " FAILED $P"
done
log "=== same-predictor arm ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
    --pseed 0 1 2 --k 1 2 --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 \
    --k-caps "1:20,2:190" --dph 1 2 --tag NBAIOT_SAMEPRED \
    --out results/canonical/nb_${P}.jsonl >> $M 2>&1 || log " FAILED $P"
done
log "NBAIOT COMPLETE"
