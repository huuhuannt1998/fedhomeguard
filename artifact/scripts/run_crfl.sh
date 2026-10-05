#!/usr/bin/env bash
# W6/E3: does the OTHER certification family survive device-derived skew?
# Sweep the smoothing scale. R = sigma * Phi^{-1}(p_A) grows with sigma, but so
# does the damage the noise does to the predictor, and the adversary's reach
# Delta(m) = 2*m*rho/N does not move. If no sigma puts R above Delta while the
# smoothed model still beats trivial, the family does not reach this operating
# point either -- for a reason unrelated to the plurality ceiling.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/crfl.log; : > $L
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
log "=== CRFL sigma sweep, device-derived and IID ==="
for P in device_derived iid; do
  $PY scripts/exp_crfl.py --partition $P --pseed 0 1 2 \
      --betas 0 0.05 0.1 0.2 --sigma 0.02 0.05 0.1 0.2 0.4 0.8 \
      --nsmooth 200 --out results/canonical/e18_crfl_$P.jsonl >>$L 2>&1 \
    && log "  ok $P ($(grep -c '^{' results/canonical/e18_crfl_$P.jsonl) rows)" || log "  FAILED $P"
done
log "=== complete ==="
