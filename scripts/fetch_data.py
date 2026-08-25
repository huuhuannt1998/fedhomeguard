#!/usr/bin/env python3
"""Dataset acquisition. All routes are unauthenticated; none needs an application.

iot-23      : per-scenario conn.log.labeled from Stratosphere. VERIFIED per-device.
n-baiot     : UCI streams its archive without Content-Length or range support and
              truncates; this retries with integrity checks and reports honestly.
ciciot2023  : the CIC site now gates behind a registration form. We do NOT submit
              personal data. Use the unauthenticated Hugging Face mirror instead.
              ATTACK-CLASS COVERAGE ONLY -- it carries no device identifier.
"""
from __future__ import annotations
import argparse, os, subprocess, sys, zipfile

IOT23_BASE = ("https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/IndividualScenarios")
IOT23_SCENARIOS = [
    "CTU-Honeypot-Capture-4-1", "CTU-Honeypot-Capture-5-1",
    "CTU-IoT-Malware-Capture-1-1", "CTU-IoT-Malware-Capture-3-1",
    "CTU-IoT-Malware-Capture-8-1", "CTU-IoT-Malware-Capture-20-1",
    "CTU-IoT-Malware-Capture-21-1", "CTU-IoT-Malware-Capture-34-1",
    "CTU-IoT-Malware-Capture-42-1", "CTU-IoT-Malware-Capture-44-1",
]
NBAIOT_URL = ("https://archive.ics.uci.edu/static/public/442/"
              "detection+of+iot+botnet+attacks+n+baiot.zip")
CICIOT_HF = "bencorn/CIC-IoT-2023"


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, **kw)


def fetch_iot23(root="data/raw/iot23"):
    os.makedirs(root, exist_ok=True)
    ok = 0
    for s in IOT23_SCENARIOS:
        dst = os.path.join(root, f"{s}.conn.log.labeled")
        if os.path.exists(dst) and os.path.getsize(dst) > 1000:
            print(f"  have {s}"); ok += 1; continue
        sh(f'curl -sL --max-time 1800 -o "{dst}" "{IOT23_BASE}/{s}/bro/conn.log.labeled"')
        n = os.path.getsize(dst) if os.path.exists(dst) else 0
        if n < 1000:
            print(f"  MISSING/empty {s} ({n} B) -- removing"); os.path.exists(dst) and os.remove(dst)
        else:
            print(f"  got {s} ({n/1e6:.1f} MB)"); ok += 1
    print(f"iot-23: {ok}/{len(IOT23_SCENARIOS)} captures present in {root}")
    return ok > 0


def fetch_nbaiot(root="data/raw/nbaiot", attempts=8):
    os.makedirs(root, exist_ok=True)
    zp = os.path.join(root, "nbaiot.zip")
    for i in range(1, attempts + 1):
        if os.path.exists(zp): os.remove(zp)
        sh(f'curl -sL --speed-limit 10000 --speed-time 120 -o "{zp}" "{NBAIOT_URL}"')
        try:
            with zipfile.ZipFile(zp) as z:
                z.extractall(root)
            print(f"n-baiot: OK on attempt {i}; extracted to {root}")
            return True
        except zipfile.BadZipFile:
            n = os.path.getsize(zp) if os.path.exists(zp) else 0
            print(f"  attempt {i}: truncated at {n/1e6:.0f} MB (UCI streams without "
                  f"Content-Length/ranges, so resume is impossible)")
    print("n-baiot: FAILED. Fallbacks: (a) a Kaggle mirror with credentials in "
          "~/.kaggle/kaggle.json, (b) download the per-device CSVs manually in a "
          "browser into data/raw/nbaiot/<Device>/. This is logistics, not science.")
    return False


def fetch_ciciot(root="data/raw/ciciot2023", subdir="CSV/CSV"):
    """ATTACK-CLASS COVERAGE ONLY. CICIoT2023 has no device identifier -- it must
    never drive a device_derived partition (see fedhomeguard.data.ciciot_device_ids)."""
    os.makedirs(root, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("pip install huggingface_hub, then re-run"); return False
    print(f"CICIoT2023 <- unauthenticated HF mirror {CICIOT_HF} (no registration form).")
    p = snapshot_download(repo_id=CICIOT_HF, repo_type="dataset", local_dir=root,
                          allow_patterns=[f"{subdir}/**/*.csv"])
    print(f"ciciot2023: {p}\nNOTE: attack-class coverage only; no per-device attribution.")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["iot-23", "n-baiot", "ciciot2023", "all"],
                    default="iot-23")
    a = ap.parse_args()
    which = ["iot-23", "n-baiot", "ciciot2023"] if a.dataset == "all" else [a.dataset]
    res = {}
    if "iot-23" in which: res["iot-23"] = fetch_iot23()
    if "n-baiot" in which: res["n-baiot"] = fetch_nbaiot()
    if "ciciot2023" in which: res["ciciot2023"] = fetch_ciciot()
    print("\nsummary:", res)
    sys.exit(0 if all(res.values()) else 1)
