#!/bin/bash
cd "$(dirname "$0")/.."
until ! pgrep -f run_necessity.py >/dev/null; do sleep 30; done
echo "=== NECESSITY DONE ==="
# IID empirical arm: needed so Gamma can be computed WITHIN the IID partition.
# Comparing IID certification against the device-derived empirical arm is invalid.
python3 -m fedhomeguard.runner --stage 2 --config configs/stage2_iid.yaml --name iid
echo "=== STAGE2_IID DONE ==="
python3 -m fedhomeguard.runner --stage 3 --config configs/stage3_iid.yaml --name iid
echo "=== STAGE3_IID DONE ==="
python3 -m fedhomeguard.runner --stage 4 --config configs/stage3_iid.yaml --name iid
echo "=== ALL TAIL DONE ==="
