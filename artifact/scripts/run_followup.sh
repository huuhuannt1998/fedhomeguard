#!/bin/bash
# Follow-on experiments after finish_all:
#  (a) main-grid certified arm on the corrected beta grid, so the body's beta* values
#      are measurements rather than grid artifacts;
#  (b) k=3 replication, raising the draw count from 3 to 15 per partition type
#      (review sec 34 asks for 15-20 at k=3).
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
M=logs/followup.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"

log "=== (a) main-grid certified arm, corrected beta grid, k=1,2,3 ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --partition $P --pseed 0 1 2 --k 1 2 3 --betas $BF \
    --clean-only --k-caps "1:20,2:190,3:500" --tag MAIN_FINEGRID \
    --out results/canonical/e2f_${P}.jsonl >> $M 2>&1 || log "  FAILED $P"
done
log "(a) rows: $(cat results/canonical/e2f_*.jsonl 2>/dev/null | wc -l)"

log "=== (b) k=3 replication, 12 additional draws per partition type ==="
for P in iid device_derived; do
  python3 scripts/exp_e2.py --partition $P --pseed $(seq -s' ' 40 51) --k 3 --betas $BF \
    --clean-only --k-caps "3:500" --tag K3_REPLICATION \
    --out results/canonical/e3rep_${P}.jsonl >> $M 2>&1 || log "  FAILED $P"
done
log "(b) rows: $(cat results/canonical/e3rep_*.jsonl 2>/dev/null | wc -l)"
log "FOLLOWUP COMPLETE"
