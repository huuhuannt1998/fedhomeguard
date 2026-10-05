#!/usr/bin/env bash
# Fetch the per-device attack archives that the 2 GB bundle never delivered.
#
# UCI's /static/public/442/ endpoint serves only the whole ~2 GB zip, with no
# Content-Length and no range support, and it drops between 500 MB and 1.2 GB.
# The LEGACY /ml/machine-learning-databases/00442/ tree still serves each device
# archive individually (~50-190 MB), which is small enough to retry to success.
# Ranges are still unsupported there, so a partial file is discarded, not resumed.
set -u
ROOT=data/raw/nbaiot
BASE=https://archive.ics.uci.edu/ml/machine-learning-databases/00442
# Ennio_Doorbell and Samsung_SNH_1011_N_Webcam were never infected with Mirai in
# the source study, so gafgyt alone makes them complete.
TARGETS="
Provision_PT_838_Security_Camera/mirai_attacks
Samsung_SNH_1011_N_Webcam/gafgyt_attacks
SimpleHome_XCS7_1002_WHT_Security_Camera/gafgyt_attacks
SimpleHome_XCS7_1002_WHT_Security_Camera/mirai_attacks
SimpleHome_XCS7_1003_WHT_Security_Camera/gafgyt_attacks
SimpleHome_XCS7_1003_WHT_Security_Camera/mirai_attacks
"
for t in $TARGETS; do
  dev=${t%/*}; kind=${t#*/}; out="$ROOT/$dev/$kind.rar"
  if [ -d "$ROOT/$dev/$kind" ] && [ "$(ls "$ROOT/$dev/$kind"/*.csv 2>/dev/null | wc -l)" -ge 5 ]; then
    echo "[skip] $t already extracted"; continue
  fi
  for attempt in $(seq 1 12); do
    echo "[$(date +%H:%M:%S)] $t attempt $attempt"
    curl -sS -L --max-time 1800 --connect-timeout 30 -o "$out.part" "$BASE/$t.rar" && mv "$out.part" "$out" || { rm -f "$out.part"; sleep 20; continue; }
    # A truncated RAR still opens; the test is whether every member decodes.
    if unar -q -f -o "$ROOT/$dev" "$out" >/dev/null 2>&1 \
       && [ "$(ls "$ROOT/$dev/$kind"/*.csv 2>/dev/null | wc -l)" -ge 5 ]; then
      echo "[ok] $t -> $(ls "$ROOT/$dev/$kind"/*.csv | wc -l) csv"; break
    fi
    echo "[bad] $t truncated or undecodable, retrying"; rm -f "$out"; sleep 20
  done
done
# Recompute the completeness manifest the loader filters on.
python3 - <<'PY'
import os, glob
root = "data/raw/nbaiot"
NO_MIRAI = {"Ennio_Doorbell", "Samsung_SNH_1011_N_Webcam"}
ok = []
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        continue
    g = len(glob.glob(f"{p}/gafgyt_attacks/*.csv"))
    m = len(glob.glob(f"{p}/mirai_attacks/*.csv"))
    need_m = 0 if d in NO_MIRAI else 5
    if os.path.exists(f"{p}/benign_traffic.csv") and g >= 5 and m >= need_m:
        ok.append(d)
open(f"{root}/COMPLETE_DEVICES.txt", "w").write("\n".join(ok) + "\n")
print(f"COMPLETE_DEVICES: {len(ok)}")
for d in ok:
    print(" ", d)
PY
