#!/usr/bin/env bash
# F10 port (2026-09-26): the multi-class control (results/canonical/e25_multiclass_*.jsonl,
# run 2026-09-08) predates the r6 alie/gaussian correction. At k=2 a member holding one
# honest and one malicious client took the NaN spread path, so those two attacks' EA
# values are pre-correction. Re-runs ONLY alie and gaussian at k=2 with the now-default
# corrected code (sd = 0 for a single honest update), on the e25 grid exactly: both
# partitions, partition seeds 10..39, the six betas, malicious-set seed 0, full
# enumeration (K = 190). k=1 cannot hit the path (a touched member has no honest client).
# The other three attacks' canonical values are reused by scripts/gen_r9_multiclass_fix.py.
#
#   MODE=legacy  re-runs seed 10 of each partition with --legacy-nan-std into
#                results/r9_mc_nanfix/legacy/, which must reproduce the canonical values
#                bit for bit (the determinism check).
# Writes only under results/r9_mc_nanfix/; results/canonical is not touched.
set -u; cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=${PY:-python3}; OUT=results/r9_mc_nanfix; L=logs/r9_mc_nanfix.log; W=${WORKERS:-4}
MODE=${MODE:-fix}
mkdir -p $OUT $OUT/legacy logs; echo "[$(date +%H:%M:%S)] start $MODE, $W workers" >> $L
job(){ P=$1; S=$2
  if [ "$MODE" = legacy ]; then
    O=$OUT/legacy/e25legacy_${P}_s${S}.jsonl; X=--legacy-nan-std
  else
    O=$OUT/e25fix_${P}_s${S}.jsonl; X=""
  fi
  $PY scripts/exp_e2.py --multiclass --partition $P --pseed $S --k 2 \
    --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 --k-caps "1:20,2:190" \
    --attacks alie gaussian $X --tag R9_MC_NANFIX \
    --out $O >> ${O%.jsonl}.log 2>&1 \
    && echo "[$(date +%H:%M:%S)] ok $MODE $P s$S" >> $L || echo "[$(date +%H:%M:%S)] FAILED $MODE $P s$S" >> $L; }
export -f job; export PY OUT L MODE
if [ "$MODE" = legacy ]; then
  printf "%s\n" "iid 10" "device_derived 10"
else
  for P in iid device_derived; do for S in $(seq 10 39); do echo "$P $S"; done; done
fi | xargs -P "$W" -L 1 bash -c 'job $0 $1'
echo "[$(date +%H:%M:%S)] done $MODE" >> $L
