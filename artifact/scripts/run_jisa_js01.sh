#!/usr/bin/env bash
# JS01 (predeclarations/jisa_JS01_cic_victim_replication.md): arms A (IID), B (device-derived 1-3), C (device-derived
# 1-1) on CIC IoT-IDAD 2024 read on the victim side, seeds 10-39, k in {1, 2}. Waits for run_jisa_train.sh so that at
# most 4 training processes run at once (HOMEPROV shares the machine), then scores with jisa_js01_cvm.py.
set -u
cd "$(dirname "$0")/.."
L=logs/jisa_train.log
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$L"; }
while pgrep -f run_jisa_train.sh > /dev/null; do sleep 60; done
log "=== JS01: CIC victim side, arms A, B, C (3 processes) ==="
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
SEEDS=$(seq -s' ' 10 39)
run(){ name=$1; shift
  if nice -n 10 python3 scripts/exp_e2.py --config configs/jisa_cic_victim.yaml --pseed $SEEDS --k 1 2 --betas $B \
      --clean-only --k-caps 1:20,2:190 "$@" --out results/jisa/$name.jsonl > logs/$name.log 2>&1; then
    log "  ok $name"; else log "  FAILED $name"; fi; }
run js01_cic_victim_iid  --partition iid            --tag JISA_JS01_A &
run js01_cic_victim_dd13 --partition device_derived --tag JISA_JS01_B --dph 1 3 &
run js01_cic_victim_dd11 --partition device_derived --tag JISA_JS01_C --dph 1 1 &
wait
nice -n 10 python3 scripts/jisa_js01_cvm.py > logs/jisa_js01_cvm.log 2>&1 && log "  ok js01 scoring" || log "  FAILED js01 scoring"
log "=== JS01 complete ==="
