#!/usr/bin/env bash
# W8/E6: an attack on the axis the certificate actually binds.
#
# Every attack in the evaluated set competes on parameter displacement and
# Appendix B.8 shows they saturate at ALIE. A plurality certificate is bound by
# ensemble AGREEMENT: a certified point cannot be flipped by construction, so the
# reachable damage is in the uncertified region and in the certified-but-wrong
# fraction. vote_shape spends its label budget on the lowest-margin samples under
# the broadcast model; rand_flip is the budget-matched control that flips the same
# NUMBER of labels at random, so any difference is attributable to placement.
# Run under IID, where certification is live and the question is meaningful.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/voteshape.log; : > $L
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
B="0 0.05 0.1 0.2 0.3 0.4"
A="vote_shape rand_flip label_flip alie"
log "=== vote-shaping vs budget-matched control ==="
$PY scripts/exp_e2.py --partition iid --tag VS_iid --pseed 0 1 2 --k 1 2 \
    --betas $B --attacks $A --k-caps "1:20,2:190" \
    --out results/canonical/e15_voteshape_iid.jsonl >>$L 2>&1 \
  && log "  ok iid ($(grep -c '^{' results/canonical/e15_voteshape_iid.jsonl) rows)" || log "  FAILED iid"
$PY scripts/exp_e2.py --partition device_derived --tag VS_dev --pseed 0 1 2 --k 1 \
    --betas $B --attacks $A --k-caps "1:20" \
    --out results/canonical/e15_voteshape_dev.jsonl >>$L 2>&1 \
  && log "  ok dev ($(grep -c '^{' results/canonical/e15_voteshape_dev.jsonl) rows)" || log "  FAILED dev"
log "=== complete ==="
