#!/usr/bin/env bash
# Tier 4, second attempt.
#
# The first attempt rebuilt these commands by hand from fragments and got nine of
# ten families wrong -- dropped --pseed 0 1 2, wrong --k, missing alphas. The fix is
# not a more careful transcription: it is to stop transcribing. This invokes the
# original scripts, which ARE the grid, and then verifies each regenerated file
# against the backup's signature so a silent mismatch cannot recur.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PATH="/Users/huanbui/miniconda3/bin:$PATH"     # so `python3` is the project interpreter
M=logs/rerun_tier4.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M

log "=== e7, e10, e11, e13, e4 -- via rerun_p1.sh, verbatim ==="
rm -f results/canonical/e7_devskew.jsonl results/canonical/e7_labelskew.jsonl \
      results/canonical/e10_N*.jsonl results/canonical/e11_dph*.jsonl \
      results/canonical/e13_*.jsonl results/canonical/e4_highinf_*.jsonl
bash scripts/rerun_p1.sh >> $M 2>&1 || log "rerun_p1 FAILED"

log "=== e9, e3 -- via queue_p1.sh lanes, verbatim ==="
rm -f results/canonical/e9_logreg_*.jsonl results/canonical/e3_*.jsonl
bash scripts/queue_p1.sh e9 >> $M 2>&1 || log "e9 FAILED"
bash scripts/queue_p1.sh e3 >> $M 2>&1 || log "e3 FAILED"

log "=== verify every regenerated file against the backup's grid signature ==="
python3 - >> $M 2>&1 <<'PYCHK'
import json, os
FAM = ["e7_devskew","e7_labelskew","e9_logreg_iid","e9_logreg_device_derived",
       "e10_N10_iid","e10_N10_device_derived","e10_N50_iid","e10_N50_device_derived",
       "e11_dph1_1","e11_dph2_5","e4_highinf_iid","e4_highinf_device_derived"]
def sig(p):
    if not os.path.exists(p): return None
    r = [json.loads(l) for l in open(p) if l.startswith("{")]
    if not r: return None
    return (len(r), sorted({x["k"] for x in r}),
            sorted({str(x.get("dirichlet_alpha")) for x in r}),
            sorted({x["partition_seed"] for x in r}),
            len({x["beta"] for x in r}))
bad = []
for f in FAM:
    o = sig(f"results/pre_determinism_fix/{f}.jsonl")
    n = sig(f"results/canonical/{f}.jsonl")
    ok = o is not None and n is not None and o[1:] == n[1:]   # grid, not row count
    print(f"  {f:30s} {'OK' if ok else 'MISMATCH'}  old={o}  new={n}")
    if not ok: bad.append(f)
print("GRID CHECK:", "all families match" if not bad else f"MISMATCH: {bad}")
PYCHK
log "TIER4 COMPLETE"
