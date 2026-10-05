#!/usr/bin/env bash
# Full re-run under the corrected substrate.
#
# Two changes force this. (1) fl_run now seeds its initial weights from fl.seed, so
# it is reproducible -- previously two identical calls disagreed, and the resulting
# run-to-run spread reached 0.70 on a bimodal cell. That touches every trained
# model, certified and empirical alike. (2) Attacked accuracy is read as the worst
# round in an eight-round post-convergence window rather than the final round.
#
# Ordered by how much the paper leans on each family, so the headline results land
# first if this is interrupted. Pre-change results are preserved under
# results/pre_determinism_fix/ so the correction can be reported as a measured delta.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=${PY:-python3}
M=logs/rerun.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
run(){ log "  -> $1"; shift; "$@" >> $M 2>&1 || log "     FAILED"; }

log "=== TIER 1a: main fine grid (frontier, pincer, beta*) ==="
for P in iid device_derived; do
  rm -f results/canonical/e5f_${P}.jsonl
  run "e5f_$P" $PY scripts/exp_e2.py --partition $P --pseed $(seq -s' ' 10 39) --k 1 2 \
    --betas $BF --clean-only --k-caps "1:20,2:190" --tag DECENSOR \
    --out results/canonical/e5f_${P}.jsonl
done

log "=== TIER 1b: cross-dataset natural experiment (N-BaIoT, 9 devices) ==="
for P in iid device_derived; do
  rm -f results/canonical/nb9_cert_${P}.jsonl
  run "nb9_cert_$P" $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml --partition $P \
    --pseed 0 1 2 3 4 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" --dph 1 2 \
    --tag NBAIOT9_CERT --out results/canonical/nb9_cert_${P}.jsonl
done

log "=== TIER 1c: main same-predictor grid (gap, G_cert) ==="
for P in iid device_derived; do
  for S in 0 1 2; do
    rm -f results/canonical/e2_${P}_s${S}.jsonl
    run "e2_${P}_s${S}" $PY scripts/exp_e2.py --partition $P --pseed $S --k 1 2 3 \
      --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 --k-caps "1:20,2:190,3:500" \
      --out results/canonical/e2_${P}_s${S}.jsonl
  done
done

log "=== TIER 2a: skew families (mechanism, ablation) ==="
for P in dirichlet_device:devskew dirichlet:labelskew; do
  KIND=${P%%:*}; TAG=${P##*:}
  rm -f results/canonical/e7f_${TAG}.jsonl
  for A in 1 0.5 0.2 0.1; do
    run "e7f_${TAG}_a$A" $PY scripts/exp_e2.py --partition $KIND --alpha $A \
      --pseed 0 1 2 --k 1 2 --betas $BF --clean-only --k-caps "1:20,2:190" \
      --tag DECENSOR_$TAG --out results/canonical/e7f_${TAG}.jsonl
  done
done

log "=== TIER 2b: k=3 full enumeration ==="
for P in iid device_derived; do
  for S in 0 1 2; do
    rm -f results/canonical/e2k3full_${P}_s${S}.jsonl
    run "e2k3full_${P}_s${S}" $PY scripts/exp_e2.py --partition $P --pseed $S --k 3 \
      --betas $BF --clean-only --k-caps "3:1140" --tag K3_FULL_ENUM \
      --out results/canonical/e2k3full_${P}_s${S}.jsonl
  done
done

log "=== TIER 2c: k=5,8 ==="
rm -f results/canonical/e2k58_*.jsonl
run "k58" bash scripts/run_k58.sh

log "=== TIER 3: volume skew, followup, N-BaIoT same-predictor ==="
rm -f results/canonical/e7_volskew.jsonl; run "volume" bash scripts/run_volume.sh
rm -f results/canonical/e2f_*.jsonl results/canonical/e3rep_*.jsonl; run "followup" bash scripts/run_followup.sh
rm -f results/canonical/nb9_iid.jsonl results/canonical/nb9_device_derived.jsonl
run "nbaiot9" bash scripts/run_nbaiot9.sh
log "RERUN COMPLETE"
