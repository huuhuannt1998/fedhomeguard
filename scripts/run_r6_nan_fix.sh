#!/usr/bin/env bash
# Review r6 (MINIMAL fix): alie and gaussian compute sd = H.std(0), whose default unbiased form is NaN
# for a single honest update, so a member holding exactly one honest client receives a
# non-finite malicious update. Re-runs ONLY those two attacks with --single-honest-zero-sd
# (sd = 0 only in that case, the committed std everywhere else) on every canonical e2 row
# where the path can fire: k in {2,3}, both partitions, all beta, the canonical partition
# seeds, malicious-set seeds, subset samples and ensemble sizes. The other three
# attacks' canonical values are reused by scripts/gen_r5_std_fix.py --rerun-dir results/r6_nan_fix --pattern "e2fix_*.jsonl" --check-unaffected.
# Writes only to results/r6_nan_fix/; results/canonical is not touched.
set -u; cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=${PY:-python3}; OUT=results/r6_nan_fix; L=logs/r6_nan_fix.log; W=${WORKERS:-4}
mkdir -p $OUT; echo "[$(date +%H:%M:%S)] start, $W workers" >> $L
job(){ P=$1; S=$2
  $PY scripts/exp_e2.py --partition $P --pseed $S --k 2 3 \
    --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 --k-caps "1:20,2:190,3:500" \
    --attacks alie gaussian --single-honest-zero-sd --tag R6_NANFIX \
    --out $OUT/e2fix_${P}_s${S}.jsonl >> $OUT/e2fix_${P}_s${S}.log 2>&1 \
    && echo "[$(date +%H:%M:%S)] ok $P s$S" >> $L || echo "[$(date +%H:%M:%S)] FAILED $P s$S" >> $L; }
export -f job; export PY OUT L
printf "%s\n" "iid 0" "iid 1" "iid 2" "device_derived 0" "device_derived 1" "device_derived 2" \
  | xargs -P "$W" -L 1 bash -c 'job $0 $1'
echo "[$(date +%H:%M:%S)] done" >> $L
