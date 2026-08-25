#!/bin/bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
# beta grid extended through the k=1 ceiling (0.450) to 0.500. At N=20 only multiples
# of 0.05 give an integer malicious count, so 0.05 is the finest meaningful step; the
# review's 0.025 suggestion applies at larger federations.
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
for P in iid device_derived; do
  python3 scripts/exp_e2.py --partition $P --pseed $(seq -s' ' 10 39) --k 1 2 \
    --betas $BF --clean-only --k-caps "1:20,2:190" --tag DECENSOR \
    --out results/canonical/e5f_${P}.jsonl
done
for A in 1 0.5 0.2 0.1; do
  for KIND in dirichlet_device:devskew dirichlet:labelskew; do
    P=${KIND%%:*}; TAG=${KIND##*:}
    python3 scripts/exp_e2.py --partition $P --alpha $A --tag DECENSOR_$TAG \
      --pseed 0 1 2 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" \
      --out results/canonical/e7f_${TAG}.jsonl
  done
done
echo DECENSOR COMPLETE
