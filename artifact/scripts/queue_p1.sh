#!/bin/bash
# P1 experiment queue (review sections 12-18). Runs sequentially inside each lane so
# the machine stays busy without oversubscribing; lanes run in parallel.
cd "$(dirname "$0")/.."
mkdir -p logs results/canonical
KC12="1:20,2:190"
B="0 0.05 0.1 0.2 0.3 0.4"

lane_e7() {   # device-support skew vs label skew, at matched realised S_JS
  for A in 100 10 1 0.5 0.1 0.01; do
    python3 scripts/exp_e2.py --partition dirichlet_device --alpha $A --tag E7_device_skew \
      --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "$KC12" \
      --out results/canonical/e7_devskew.jsonl
    python3 scripts/exp_e2.py --partition dirichlet --alpha $A --tag E7_label_skew \
      --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "$KC12" \
      --out results/canonical/e7_labelskew.jsonl
  done
}

lane_e9() {   # second lightweight model: logistic regression
  for P in iid device_derived; do
    python3 scripts/exp_e2.py --partition $P --arch logreg --tag E9_logreg \
      --pseed 0 1 2 --k 1 2 --betas $B --k-caps "$KC12" \
      --out results/canonical/e9_logreg_${P}.jsonl
  done
}

lane_e10() {  # federation size
  for NN in 10 50; do
    for P in iid device_derived; do
      python3 scripts/exp_e2.py --partition $P --N $NN --tag E10_N${NN} \
        --pseed 0 1 2 --k 1 2 3 --betas $B --clean-only \
        --k-caps "1:$NN,2:200,3:200" \
        --out results/canonical/e10_N${NN}_${P}.jsonl
    done
  done
}

lane_e11() {  # household device richness
  for D in "1 1" "2 5"; do
    T=$(echo $D | tr ' ' '_')
    python3 scripts/exp_e2.py --partition device_derived --dph $D --tag E11_dph${T} \
      --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "$KC12" \
      --out results/canonical/e11_dph${T}.jsonl
  done
}

lane_e3() {   # method gap + observability across draws + attack strength
  for P in device_derived iid; do
    python3 scripts/exp_e3_defenses.py --partition $P --pseed 0 1 2 \
      --betas $B --mal-seeds 0 1 2 --scales 0.5 1.0 5.0 \
      --out results/canonical/e3_${P}.jsonl
  done
}

case "$1" in
  e7) lane_e7 ;; e9) lane_e9 ;; e10) lane_e10 ;; e11) lane_e11 ;; e3) lane_e3 ;;
  *) echo "usage: $0 {e3|e7|e9|e10|e11}"; exit 1 ;;
esac
