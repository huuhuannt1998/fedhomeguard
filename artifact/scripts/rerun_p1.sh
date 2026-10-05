#!/bin/bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
log(){ echo "[$(date +%H:%M:%S)] $*" >> logs/p1_rerun.log; }
B="0 0.05 0.1 0.2 0.3 0.4"

log "E7 device-skew vs label-skew"
for A in 100 10 3 1 0.5 0.2 0.1; do
  for KIND in dirichlet_device:devskew dirichlet:labelskew; do
    P=${KIND%%:*}; TAG=${KIND##*:}
    python3 scripts/exp_e2.py --partition $P --alpha $A --tag E7_$TAG \
      --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "1:20,2:190" \
      --out results/canonical/e7_${TAG}.jsonl >> logs/e7_rerun.log 2>&1 || true
  done
done
log "E7 done"

log "E10 federation size"
for NN in 10 50; do
  for P in iid device_derived; do
    python3 scripts/exp_e2.py --partition $P --N $NN --tag E10_N${NN} \
      --pseed 0 1 2 --k 1 2 3 --betas $B --clean-only \
      --k-caps "1:$NN,2:200,3:200" \
      --out results/canonical/e10_N${NN}_${P}.jsonl >> logs/e10.log 2>&1 || true
  done
done
log "E10 done"

log "E11 household device richness"
bash scripts/queue_p1.sh e11 >> logs/e11.log 2>&1 || true
log "E11 done"

log "E13 attack strength"
for P in device_derived iid; do
  python3 scripts/exp_e3_defenses.py --partition $P --pseed 0 1 2 \
    --betas 0.1 0.2 --mal-seeds 0 --scales 0.5 1.0 5.0 \
    --defenses norm_clip median multikrum \
    --out results/canonical/e13_${P}.jsonl >> logs/e13.log 2>&1 || true
done
log "E13 done"

log "E4 high-influence malicious sets"
for P in device_derived iid; do
  python3 scripts/exp_e2.py --partition $P --pseed 0 1 2 --k 1 2 \
    --betas 0.05 0.1 0.2 0.3 0.4 --mal-mode high_volume rare_device \
    --k-caps "1:20,2:190" --out results/canonical/e4_highinf_${P}.jsonl \
    >> logs/e4_highinf.log 2>&1 || true
done
log "ALL P1 LANES COMPLETE"
