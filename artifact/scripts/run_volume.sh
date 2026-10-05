#!/bin/bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
for A in 100 10 1 0.5 0.2; do
  python3 scripts/exp_e2.py --partition volume --alpha $A --tag E7C_volume \
    --pseed 0 1 2 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" \
    --out results/canonical/e7_volskew.jsonl || true
done
echo VOLUME COMPLETE
