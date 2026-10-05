#!/usr/bin/env bash
# C1 fix re-run: regenerate the only files whose G_cert reaches the paper,
# so the slack compares the final-round predictor against itself.
set -u
cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/rerun_c1.log
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
guarded(){ local tgt="$1"; shift; local sc="results/scratch/$tgt.jsonl"; rm -f "$sc"
  "$@" >>"$L" 2>&1 || { log "  FAILED $tgt (target untouched)"; return 1; }
  local n; n=$(grep -c '^{' "$sc" 2>/dev/null || echo 0)
  local o; o=$(grep -c '^{' "results/canonical/$tgt.jsonl" 2>/dev/null || echo 0)
  [ "$n" -eq "$o" ] || { log "  ROWMISMATCH $tgt new=$n old=$o (target untouched)"; return 1; }
  mv "$sc" "results/canonical/$tgt.jsonl"; log "  ok $tgt ($n rows)"; }
run_e2(){ local P=$1 S=$2
  guarded "e2_${P}_s${S}" $PY scripts/exp_e2.py --partition $P --pseed $S --k 1 2 3 \
    --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 --k-caps "1:20,2:190,3:500" \
    --out results/scratch/e2_${P}_s${S}.jsonl; }
run_e9(){ local P=$1
  guarded "e9_logreg_$P" $PY scripts/exp_e2.py --partition $P --arch logreg --tag E9_logreg \
    --pseed 0 1 2 --k 1 2 --betas 0 0.05 0.1 0.2 0.3 0.4 --k-caps "1:20,2:190" \
    --out results/scratch/e9_logreg_$P.jsonl; }
log "=== rerun_c1 start ==="
for S in 0 1 2; do run_e2 iid $S & run_e2 device_derived $S & wait; done
run_e9 iid & run_e9 device_derived & wait
log "=== rerun_c1 complete ==="
