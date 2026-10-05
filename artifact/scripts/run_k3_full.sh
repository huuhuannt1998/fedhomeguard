#!/bin/bash
# Full enumeration at k=3: all C(20,3)=1140 subsets, certified arm.
#
# The same-predictor analysis keeps K=500 at k=3, because both of its arms must
# describe ONE predictor and attacking a 1140-member ensemble over the full attack
# and malicious-set grid is ~14 h per configuration. This run answers the separate
# question the sampling raises: how far is the realised K=500 certificate from the
# population one on real data? That is the E1/V4 check applied to the actual
# partitions rather than to synthetic draws.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
M=logs/k3full.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
for P in iid device_derived; do
  for S in 0 1 2; do
    log "k=3 full enumeration: $P seed $S"
    python3 scripts/exp_e2.py --partition $P --pseed $S --k 3 --betas $BF \
      --clean-only --k-caps "3:1140" --tag K3_FULL_ENUM \
      --out results/canonical/e2k3full_${P}_s${S}.jsonl >> $M 2>&1 || log "  FAILED"
  done
done
log "K3FULL COMPLETE"
