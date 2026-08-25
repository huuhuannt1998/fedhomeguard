#!/bin/bash
cd /Users/huanbui/Research/FedHomeGuard-P10
echo "=== L2/L3 START ==="   # cheapest first, closes the biggest argument gap
python3 scripts/exp_l2_l3.py
echo "=== L2/L3 DONE ==="
echo "=== A8 START ==="
python3 scripts/exp_a8_budget.py
echo "=== A8 DONE ==="
echo "=== A5/A4 START ==="   # longest last
python3 scripts/exp_a5_a4.py
echo "=== A5/A4 DONE ==="
echo "ALL GAPFILL COMPLETE"
