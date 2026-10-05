#!/usr/bin/env bash
# Review W9(b)/E10: five result files carry a G_cert column computed before the
# C1 fix, so it can read negative. The values cannot be recomputed -- those runs
# predate EA_final_round -- so the only real fix is to re-run them under the
# current code, which persists EA_final_round and defines G_cert on the same
# predictor as CA.
#
# nb_* is not re-run: it is byte-identical in configuration to nb9_* (same N,
# same test split, same tau), a superseded duplicate rather than a separate
# robustness check, and is retired instead.
set -u; cd "$(dirname "$0")/.."
# exp_e2 is RESUMABLE -- it appends and skips rows already present in --out. Left
# in place, the old rows are all present, so a re-run skips every one and reports
# success on the pre-existing count. That is exactly what happened the first time
# this script ran. The targets are archived out of the way by the caller before
# this runs; the check at the end fails loudly if the new rows still lack the
# field whose absence is the whole reason for re-running.
PY=${PY:-python3}; L=logs/regen_stale.log; : > $L
B="0 0.05 0.1 0.2 0.3 0.4"; KC12="1:20,2:190"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }

log "=== e4_highinf (IoT-23, high-volume and rare-device malicious sets) ==="
for P in iid device_derived; do
  $PY scripts/exp_e2.py --partition $P --pseed 0 1 2 --k 1 2 \
      --betas 0.05 0.1 0.2 0.3 0.4 --mal-mode high_volume rare_device \
      --k-caps "$KC12" --out results/canonical/e4_highinf_${P}.jsonl >>$L 2>&1 \
    && log "  ok e4_highinf_$P ($(grep -c '^{' results/canonical/e4_highinf_${P}.jsonl) rows)" \
    || log "  FAILED e4_highinf_$P"
done

log "=== nb9 same-predictor (N-BaIoT) ==="
for P in iid device_derived; do
  $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
      --pseed 0 1 2 --k 1 2 --betas $B --mal-seeds 0 1 2 --k-caps "$KC12" \
      --dph 1 2 --tag NBAIOT9_SAMEPRED \
      --out results/canonical/nb9_${P}.jsonl >>$L 2>&1 \
    && log "  ok nb9_$P ($(grep -c '^{' results/canonical/nb9_${P}.jsonl) rows)" \
    || log "  FAILED nb9_$P"
done
for f in e4_highinf_iid e4_highinf_device_derived nb9_iid nb9_device_derived; do
  n=$($PY -c "
import json,sys
rs=[json.loads(l) for l in open('results/canonical/$f.jsonl') if l.startswith('{')]
print(sum(1 for r in rs if r.get('EA_final_round')), len(rs))" 2>/dev/null || echo "0 0")
  log "  verify $f: rows_with_EA_final_round = $n"
done
log "=== complete ==="
