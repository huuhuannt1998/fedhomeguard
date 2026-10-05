#!/usr/bin/env bash
# N-BaIoT on the COMPLETE nine-device catalogue.
#
# The first N-BaIoT arm ran on the five devices the truncated 2 GB bundle happened
# to deliver. scripts/fetch_nbaiot_missing.sh recovered the remaining four from
# UCI's legacy per-file tree, so the natural experiment can now be run on the whole
# dataset: 1,333,113 rows, I(label; device) = 0.0050 bits (1.07% of a 0.4685-bit
# label entropy) against IoT-23's 0.3189 bits (37.4%). The five-device results stay
# on disk as a subsample robustness check rather than being overwritten.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
M=logs/nbaiot9.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"

log "=== certified arm, 9 devices ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
    --pseed 0 1 2 3 4 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" --dph 1 2 \
    --tag NBAIOT9_CERT --out results/canonical/nb9_cert_${P}.jsonl >> $M 2>&1 &
done
wait
log "cert rows: $(cat results/canonical/nb9_cert_*.jsonl 2>/dev/null | grep -c '^{')"

log "=== same-predictor arm, 9 devices ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
    --pseed 0 1 2 --k 1 2 --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 \
    --k-caps "1:20,2:190" --dph 1 2 --tag NBAIOT9_SAMEPRED \
    --out results/canonical/nb9_${P}.jsonl >> $M 2>&1 &
done
wait
log "samepred rows: $(cat results/canonical/nb9_*.jsonl 2>/dev/null | grep -c '^{')"
log "NBAIOT9 COMPLETE"
