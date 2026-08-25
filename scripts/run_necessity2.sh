#!/bin/bash
cd /Users/huanbui/Research/FedHomeGuard-P10
until grep -q "ALL TAIL DONE" results/run_tail.log 2>/dev/null; do sleep 30; done
echo "=== TAIL DONE, starting necessity rerun ==="
python3 scripts/run_necessity.py
echo "=== NECESSITY2 DONE ==="
