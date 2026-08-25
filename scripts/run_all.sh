#!/bin/bash
# Full experiment suite. Runs sequentially to avoid CPU contention on one laptop,
# which would also distort the wall-clock budget recorded in each capability record.
cd /Users/huanbui/Research/FedHomeGuard-P10
set -x

# 0) wait for the multi-seed k-sweep to finish
until [ "$(python3 -c "import json;print(len(json.load(open('results/ksweep_seeds.json'))['rows']))" 2>/dev/null)" = "30" ]; do sleep 20; done
echo "=== KSWEEP DONE ==="

# 1) canonical certified arm (device-derived, k=5) -- GATE G1
python3 -m fedhomeguard.runner --stage 3 --config configs/stage3_certification.yaml --name main
echo "=== STAGE3 DONE ==="

# 2) empirical arm: attacks x defenses x beta  -> EA_min
python3 -m fedhomeguard.runner --stage 2 --config configs/stage2_empirical.yaml --name main
echo "=== STAGE2 DONE ==="

# 3) the gap: Gamma, R_lit \ R_hon
python3 -m fedhomeguard.runner --stage 4 --config configs/stage3_certification.yaml --name main
echo "=== STAGE4 DONE ==="

# 4) skew sweep + Algorithm 4 necessity + Algorithm 5 leave-one-device-out
python3 -m fedhomeguard.runner --stage 5 --config configs/stage5_skew.yaml --name main
echo "=== STAGE5 DONE ==="
echo "ALL EXPERIMENTS COMPLETE"
