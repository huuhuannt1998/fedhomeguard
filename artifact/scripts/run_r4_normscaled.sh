#!/usr/bin/env bash
# Review r4, A-W1 / meta-review item 1: do the k=3 void cells of Table 2 survive an
# attack that is not diluted by FedAvg? Re-runs the same-predictor grid of
# results/canonical/e2_* (same partition seeds, malicious-set seeds, subset samples and
# ensemble sizes) with two attacks the canonical five do not include:
#   replace_invert  model replacement: the malicious client scales its update by the
#                   inverse of its aggregation weight so the member's aggregate equals
#                   the round's clean aggregate with its output inverted (attacks.py)
#   sign_flip       at scale 100: the malicious update is the honest step reversed and
#                   multiplied by 100 (the canonical grid runs it at scale 1)
# Writes only to results/r4_normscaled/; results/canonical is not touched.
set -u; cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=${PY:-python3}; OUT=results/r4_normscaled; L=logs/r4_normscaled.log
mkdir -p $OUT; : > $L
run(){ local P=$1 S=$2
  $PY scripts/exp_e2.py --partition $P --pseed $S --k 1 2 3 \
    --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 --k-caps "1:20,2:190,3:500" \
    --attacks replace_invert sign_flip --scale 100 --tag R4_NORMSCALED_x100 \
    --out $OUT/e2ns_${P}_s${S}.jsonl >> $OUT/e2ns_${P}_s${S}.log 2>&1 \
    && echo "[$(date +%H:%M:%S)] ok $P s$S" >> $L || echo "[$(date +%H:%M:%S)] FAILED $P s$S" >> $L; }
echo "[$(date +%H:%M:%S)] start" >> $L
for P in iid device_derived; do for S in 0 1 2; do run $P $S & done; done; wait
echo "[$(date +%H:%M:%S)] done" >> $L
