#!/bin/bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
B="0 0.05 0.1 0.2 0.3 0.4"
for A in 100 10 3 1 0.5 0.2 0.1; do
  for KIND in dirichlet_device:devskew dirichlet:labelskew; do
    P=${KIND%%:*}; TAG=${KIND##*:}
    python3 scripts/exp_e2.py --partition $P --alpha $A --tag E7_$TAG \
      --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "1:20,2:190" \
      --out results/canonical/e7_${TAG}.jsonl || true
  done
done
echo "E7 RERUN COMPLETE"
