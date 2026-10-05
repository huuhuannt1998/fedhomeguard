#!/bin/bash
# k=5 and k=8: the paper's Setup section describes these configurations, so the data
# must exist. The certified arm is swept in full; the same-predictor arm is run only
# where certification is geometrically possible (beta_geo(20,5)=0.100,
# beta_geo(20,8)=0.050), because above that CA is identically zero and the difference
# is not slack. One malicious set, since malicious-set sensitivity is established at
# k=1,2 where the certificate is alive across the whole grid.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"

for P in iid device_derived; do
  for S in 0 1 2; do
    # certified arm across the full grid
    python3 scripts/exp_e2.py --partition $P --pseed $S --k 5 8 --betas $BF \
      --clean-only --k-caps "5:200,8:200" --tag K58_CERT \
      --out results/canonical/e2k58_cert_${P}_s${S}.jsonl || true
    # same-predictor arm where the certificate is alive
    python3 scripts/exp_e2.py --partition $P --pseed $S --k 5 8 --betas 0 0.05 0.1 \
      --mal-seeds 0 --k-caps "5:200,8:200" --tag K58_SAMEPRED \
      --out results/canonical/e2k58_${P}_s${S}.jsonl || true
  done
done
echo "K58 COMPLETE"
