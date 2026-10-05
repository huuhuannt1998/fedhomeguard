#!/usr/bin/env bash
# Review W9(d) / E10 / Question 5: Table 6 reported beta*=0.100 for device-derived
# at N=20 while Table 1 reported 0.050 for the same quantity, and its IID column
# was right-censored by a grid stopping at 0.40. Re-run N=10 and N=50 on the fine
# grid; N=20 comes from the 30-draw e5f arm so the two tables cannot disagree.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/fedsize.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
log "=== N sweep on the fine grid ==="
for N in 10 50; do
  for P in iid device_derived; do
    $PY scripts/exp_e2.py --partition $P --tag FS_N${N} --pseed 0 1 2 --k 1 \
        --betas $B --N $N --clean-only --k-caps "1:$N" \
        --out results/canonical/e10b_N${N}_${P}.jsonl >>$L 2>&1 \
      && log "  ok N=$N $P ($(grep -c '^{' results/canonical/e10b_N${N}_${P}.jsonl) rows)" \
      || log "  FAILED N=$N $P"
  done
done
log "=== complete ==="
