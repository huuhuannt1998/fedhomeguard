#!/usr/bin/env bash
# M8: the cross-dataset claim rests on 5 partition draws with no interval, against
# IoT-23's 30. Re-run the N-BaIoT certified arm at 30 draws so the two arms are
# comparably powered and the collapse rate can carry a Wilson interval.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/rerun_m8.log; : > $L
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
SEEDS=$(seq 0 29 | tr '\n' ' ')
# identical to rerun_all.sh BF -- 11 values. Using a shorter grid here would
# silently change the experiment while still producing a plausible file.
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
guarded(){ local tgt="$1"; shift; local sc="results/scratch/$tgt.jsonl"; rm -f "$sc"
  "$@" >>"$L" 2>&1 || { log "  FAILED $tgt (target untouched)"; return 1; }
  local n; n=$(grep -c '^{' "$sc" 2>/dev/null || echo 0)
  [ "$n" -ge 600 ] || { log "  SHORT $tgt ($n rows, expected ~660)"; return 1; }
  mv "$sc" "results/canonical/$tgt.jsonl"; log "  ok $tgt ($n rows)"; }
run_p(){ local P=$1
  guarded "nb9_cert_$P" $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml \
    --partition $P --pseed $SEEDS --k 1 2 --betas $BF --clean-only \
    --k-caps "1:20,2:190" --dph 1 2 --tag NBAIOT9_CERT \
    --out results/scratch/nb9_cert_$P.jsonl; }
log "=== rerun_m8 start: N-BaIoT certified arm at 30 partition draws ==="
run_p iid & run_p device_derived & wait
log "=== rerun_m8 complete ==="
