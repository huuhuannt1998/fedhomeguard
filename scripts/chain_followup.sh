#!/bin/bash
# Waits on the COMPLETION MARKER in the log rather than on pgrep, which previously
# matched the waiter shells themselves and deadlocked the whole chain.
cd "$(dirname "$0")/.."
until grep -q 'FINISH_ALL COMPLETE' logs/finish_all.log 2>/dev/null; do sleep 60; done
bash scripts/run_followup.sh
