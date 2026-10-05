#!/usr/bin/env bash
# E2 (W3): does a STRONGER local learner rescue competence at k=1? The paper's
# second family (logistic, 64 params) is weaker than the perceptron; the review
# asks the other direction. mlp_large is 128-64-32.
# E7: full enumeration at k=3 -- all 1,140 subsets rather than the sampled 500,
# so the realised and population certificates coincide and beta* is not
# understated by the sampling gap Appendix C.1 measures.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/e2e7.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }

log "=== E2: stronger local learner at k=1 ==="
for P in device_derived iid; do
  $PY scripts/exp_e2.py --partition $P --tag E2_large --pseed 0 1 2 --k 1 \
      --betas $B --arch mlp_large --clean-only --k-caps "1:20" \
      --out results/canonical/e19_large_${P}.jsonl >>$L 2>&1 \
    && log "  ok E2 $P ($(grep -c '^{' results/canonical/e19_large_${P}.jsonl) rows)" \
    || log "  FAILED E2 $P"
done

log "=== E7: full enumeration at k=3 (1,140 subsets) ==="
for P in device_derived iid; do
  $PY scripts/exp_e2.py --partition $P --tag E7_k3full --pseed 0 1 2 --k 3 \
      --betas $B --clean-only --k-caps "3:1140" \
      --out results/canonical/e20_k3full_${P}.jsonl >>$L 2>&1 \
    && log "  ok E7 $P ($(grep -c '^{' results/canonical/e20_k3full_${P}.jsonl) rows)" \
    || log "  FAILED E7 $P"
done
log "=== complete ==="
