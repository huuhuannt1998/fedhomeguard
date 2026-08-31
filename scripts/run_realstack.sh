#!/usr/bin/env bash
# Real-stack arm: the same partitions the simulation uses, run through a real Flower
# server and one container per household, so the attack is delivered over gRPC by a
# process the attacker controls rather than written into a tensor by the harness.
set -u
cd "$(dirname "$0")/.."
M=logs/realstack.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M
ROUNDS=15
mkdir -p results/realstack

for PART in device_derived iid; do
  ROOT=data/households/${PART}_s0_N20
  [ -d "$ROOT" ] || { log "MISSING $ROOT"; continue; }
  for SPEC in "none:0" "label_flip:2" "label_flip:4" "label_flip:8" \
              "sign_flip:2" "sign_flip:4" "sign_flip:8" \
              "gaussian:2" "gaussian:4" "gaussian:8" \
              "ipm:2" "ipm:4" "ipm:8" "alie:2" "alie:4" "alie:8"; do
    ATK=${SPEC%%:*}; M_N=${SPEC##*:}
    TAG="${PART}_${ATK}_m${M_N}"
    [ -f "results/realstack/${TAG}.json" ] && { log "skip $TAG"; continue; }
    # a fixed malicious set per size, so runs differ only in the attack
    case $M_N in 0) MAL="";; 2) MAL="3 7";; 4) MAL="3 7 11 15";; 8) MAL="1 3 5 7 9 11 13 15";; esac
    log "run $TAG (m=$M_N)"
    python3 scripts/gen_compose.py --root "$ROOT" --N 20 --mal $MAL \
      --attack "$ATK" --rounds $ROUNDS --tag "$TAG" \
      --out docker/compose.run.yml >> $M 2>&1
    docker compose -p rs -f docker/compose.run.yml up \
      --abort-on-container-exit --exit-code-from server >> $M 2>&1
    docker compose -p rs -f docker/compose.run.yml down -v >> $M 2>&1
    python3 - "$TAG" <<'PYCHK' >> $M 2>&1
import json, os, sys, collections
f = f"results/realstack/{sys.argv[1]}.json"
if os.path.exists(f):
    d = json.load(open(f)); per = collections.Counter(r["round"] for r in d["contributions"])
    if len(per) != d["rounds"] or set(per.values()) != {d["clients"]}:
        os.remove(f); print(f"DISCARDED incomplete {sys.argv[1]}")
PYCHK
  done
done
log "REALSTACK COMPLETE"
