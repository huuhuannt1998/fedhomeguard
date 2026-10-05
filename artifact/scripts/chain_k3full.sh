#!/bin/bash
cd "$(dirname "$0")/.."
until grep -q 'FOLLOWUP COMPLETE' logs/followup.log 2>/dev/null; do sleep 60; done
bash scripts/run_k3_full.sh
