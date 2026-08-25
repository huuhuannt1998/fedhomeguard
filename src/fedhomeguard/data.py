"""Dataset loading and featurization.

Per-device attribution is the load-bearing property (design D1):
  iot-23     : one physical device per capture  -- VERIFIED
  n-baiot    : one device per file family       -- structural
  ciciot2023 : NO device identifier in the CSVs -- attack-class coverage ONLY.
               Attempting to use it as a partition substrate raises.
"""
from __future__ import annotations
import glob, hashlib, os
import numpy as np, pandas as pd

IOT23_COLS = ["ts", "uid", "orig_h", "orig_p", "resp_h", "resp_p", "proto", "service",
              "duration", "orig_bytes", "resp_bytes", "conn_state", "local_orig",
              "local_resp", "missed_bytes", "history", "orig_pkts", "orig_ip_bytes",
              "resp_pkts", "resp_ip_bytes", "tunnel_parents", "label", "detailed"]
IOT23_NUM = ["resp_p", "duration", "orig_bytes", "resp_bytes", "missed_bytes",
             "orig_pkts", "orig_ip_bytes", "resp_pkts", "resp_ip_bytes"]
IOT23_CAT = (("proto", 4), ("conn_state", 12), ("service", 8))

# Physical device identity per IoT-23 capture (from each scenario's README).
IOT23_DEVICE_NAME = {
    "CTU-Honeypot-Capture-4-1": "Philips-Hue-Bridge",
    "CTU-Honeypot-Capture-5-1": "Amazon-Echo",
    "CTU-Honeypot-Capture-7-1": "Somfy-Door-Lock",
}


class AttributionError(RuntimeError):
    """Raised when a dataset cannot supply per-device attribution."""


# --------------------------------------------------------------------------- IoT-23
def load_iot23(root: str = "data/raw/iot23", max_rows_per_device: int = 60_000,
               verbose: bool = True) -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(root, "*.conn.log.labeled"))):
        dev = os.path.basename(path).split(".conn")[0]
        df = pd.read_csv(path, sep=r"\s+", comment="#", names=IOT23_COLS, header=None,
                         engine="python", on_bad_lines="skip", dtype=str, nrows=400_000)
        df = df[df["label"].notna()]
        df["label"] = df["label"].str.lower()
        df = df[df["label"].isin(["benign", "malicious"])]
        if df.empty:
            continue
        if len(df) > max_rows_per_device:          # subsample preserving time order
            df = df.iloc[np.linspace(0, len(df) - 1, max_rows_per_device).astype(int)]
        df["device"] = dev
        df["device_name"] = IOT23_DEVICE_NAME.get(dev, dev)
        frames.append(df)
        if verbose:
            print(f"  {dev:34s} rows={len(df):7d} mal={(df.label=='malicious').mean():.3f}")
    if not frames:
        raise FileNotFoundError(f"no IoT-23 captures under {root}; run scripts/fetch_data.py")
    return pd.concat(frames, ignore_index=True)


def featurize_iot23(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    cols, names = [], []
    for c in IOT23_NUM:
        v = pd.to_numeric(df[c].replace("-", np.nan), errors="coerce").fillna(0.0).to_numpy(float)
        cols.append(np.log1p(np.abs(v)) * np.sign(v)); names.append(f"log_{c}")
    for col, k in IOT23_CAT:
        for val in df[col].value_counts().index[:k].tolist():
            cols.append((df[col] == val).to_numpy(float)); names.append(f"{col}={val}")
    X = np.stack(cols, 1).astype(np.float32)
    y = (df["label"] == "malicious").to_numpy().astype(np.int64)
    return X, y, names


# -------------------------------------------------------------------------- N-BaIoT
NBAIOT_DEVICES = ["Danmini_Doorbell", "Ecobee_Thermostat", "Ennio_Doorbell",
                  "Philips_B120N10_Baby_Monitor", "Provision_PT_737E_Security_Camera",
                  "Provision_PT_838_Security_Camera", "Samsung_SNH_1011_N_Webcam",
                  "SimpleHome_XCS7_1002_WHT_Security_Camera",
                  "SimpleHome_XCS7_1003_WHT_Security_Camera"]


def load_nbaiot(root: str = "data/raw/nbaiot", max_rows_per_device: int = 60_000,
                verbose: bool = True, cache: bool = True) -> pd.DataFrame:
    """N-BaIoT: <Device>/benign_traffic.csv and <Device>/{gafgyt,mirai}_attacks/*.csv.

    Parsing all 89 source CSVs costs minutes, and every experiment configuration
    reloads the same frame, so the result is cached to Parquet. The cache key
    covers the row cap and the completeness manifest, which are the only two
    inputs that change what gets loaded."""
    # Only devices whose benign AND attack partitions were retrieved intact. A device
    # holding benign traffic alone would enter the catalogue as an all-benign class and
    # silently distort the device-to-label coupling the analysis is about, so it is
    # excluded rather than half-used. COMPLETE_DEVICES.txt is written by
    # scripts/fetch_nbaiot_robust.py and records what was actually recovered.
    manifest = os.path.join(root, "COMPLETE_DEVICES.txt")
    if os.path.exists(manifest):
        keep = {l.strip() for l in open(manifest) if l.strip()}
    else:
        keep = set(NBAIOT_DEVICES)
    ckey = f"{max_rows_per_device}_{'-'.join(sorted(keep))}"
    cpath = os.path.join(root, f".cache_{hashlib.sha1(ckey.encode()).hexdigest()[:12]}.parquet")
    if cache and os.path.exists(cpath):
        df = pd.read_parquet(cpath)
        if verbose:
            print(f"  n-baiot rows={len(df)} devices={df.device.nunique()} (cached)")
        return df
    frames, used = [], []
    for dev in NBAIOT_DEVICES:
        ddir = os.path.join(root, dev)
        if not os.path.isdir(ddir) or dev not in keep:
            continue
        used.append(dev)
        for path in sorted(glob.glob(os.path.join(ddir, "**", "*.csv"), recursive=True)):
            lab = "benign" if "benign" in os.path.basename(path).lower() else "malicious"
            df = pd.read_csv(path)
            if len(df) > max_rows_per_device // 4:
                df = df.iloc[np.linspace(0, len(df) - 1, max_rows_per_device // 4).astype(int)]
            # the traffic type is the source file: benign, or one attack family and
            # command. N-BaIoT carries no timestamp, so this is what the split must be
            # stratified on -- see time_split_within_device.
            fam = os.path.basename(os.path.dirname(path))
            ttype = (f"{fam}/{os.path.basename(path)[:-4]}"
                     if fam not in (dev, "") else os.path.basename(path)[:-4])
            # assign() builds one new block instead of four separate inserts, which
            # is what made a 1.3M-row concat of 89 frames pathologically slow.
            frames.append(df.assign(label=lab, device=dev, device_name=dev,
                                    traffic_type=ttype))
    if not frames:
        raise FileNotFoundError(
            f"no N-BaIoT data under {root}. UCI's archive endpoint streams without "
            f"Content-Length/ranges and truncates; see scripts/fetch_data.py --dataset n-baiot")
    df = pd.concat(frames, ignore_index=True, copy=False)
    if verbose:
        print(f"  n-baiot rows={len(df)} devices={df.device.nunique()} "
              f"(complete only: {', '.join(used)})")
    if cache:
        try:
            df.to_parquet(cpath, index=False)
        except Exception as e:  # a missing parquet engine must not fail the load
            if verbose:
                print(f"  n-baiot cache skipped: {e}")
    return df


def featurize_nbaiot(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    drop = {"label", "device", "device_name", "traffic_type"}
    names = [c for c in df.columns if c not in drop]
    X = np.log1p(np.abs(df[names].to_numpy(float))).astype(np.float32)
    y = (df["label"] == "malicious").to_numpy().astype(np.int64)
    return X, y, names


# ----------------------------------------------------------------------- CICIoT2023
def load_ciciot(root: str = "data/raw/ciciot2023", max_rows: int = 400_000,
                verbose: bool = True) -> pd.DataFrame:
    """Attack-class coverage ONLY. Has no device column -- see AttributionError below."""
    files = sorted(glob.glob(os.path.join(root, "**", "*.csv"), recursive=True))
    if not files:
        raise FileNotFoundError(f"no CICIoT2023 CSVs under {root}; run scripts/fetch_data.py")
    per = max(1, max_rows // len(files))
    frames = []
    for p in files:
        d = pd.read_csv(p, nrows=per)
        d["attack_class"] = os.path.basename(os.path.dirname(p))
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    lab = df.get("label", df.get("Label"))
    df["label"] = np.where(
        lab.astype(str).str.lower().isin(["benign", "benigntraffic"]), "benign", "malicious"
    ) if lab is not None else np.where(
        df["attack_class"].str.lower().str.contains("benign"), "benign", "malicious")
    if verbose:
        print(f"  ciciot2023 rows={len(df)} classes={df.attack_class.nunique()}")
    return df


def ciciot_device_ids(_df: pd.DataFrame):
    raise AttributionError(
        "CICIoT2023 carries NO device identifier: its published CSV schema is 39 aggregate "
        "features (Header_Length..Variance) with no MAC, no source IP, no device label, and "
        "rows aggregate 10-packet windows. The authors' Feature_extraction.py tracks src_ips "
        "internally but never emits them, and the tree is organised by attack type. Recovering "
        "attribution needs re-extraction from ~0.5TB of PCAP, which violates D3's compute "
        "envelope. Use CICIoT2023 for attack-class coverage only. See RKA checkpoint "
        "chk_01M0EH65WGYNBDK9H4MWQQT2JA.")


# ------------------------------------------------------------------------- dispatch
LOADERS = {"iot-23": (load_iot23, featurize_iot23),
           "n-baiot": (load_nbaiot, featurize_nbaiot),
           "ciciot2023": (load_ciciot, None)}
SUPPORTS_DEVICE_PARTITION = {"iot-23": True, "n-baiot": True, "ciciot2023": False}


def load_dataset(cfg, verbose: bool = True) -> dict:
    name = cfg.data.dataset
    if name not in LOADERS:
        raise ValueError(f"unknown dataset {name!r}; choose from {sorted(LOADERS)}")
    loader, feat = LOADERS[name]
    root = os.path.join(cfg.data.root, {"iot-23": "iot23", "n-baiot": "nbaiot",
                                        "ciciot2023": "ciciot2023"}[name])
    if name == "ciciot2023":
        if cfg.partition.kind == "device_derived":
            ciciot_device_ids(None)
        raise NotImplementedError(
            "CICIoT2023 featurization is Stage-6 attack-class coverage; wire it when that "
            "stage runs. It must never drive a device_derived partition.")
    df = loader(root, cfg.data.max_rows_per_device, verbose)
    X, y, names = feat(df)
    dev_codes = pd.Categorical(df["device"]).codes.astype(int)
    dev_names = list(pd.Categorical(df["device"]).categories)
    # traffic_type exists only for datasets whose row order is file order rather than
    # time; the splitter blocks on it when present.
    block = (df["traffic_type"].astype(str).to_numpy(dtype=object)
             if "traffic_type" in df.columns else None)
    return dict(X=X, y=y, device=dev_codes, device_names=dev_names,
                feature_names=names, block=block, df=df)


def time_split_within_device(y: np.ndarray, device: np.ndarray, train_frac: float = 0.8,
                             block: np.ndarray | None = None):
    """Order-preserving split within each device, and within each traffic type when one
    is supplied.

    Taking the tail of each block rather than a random sample is what keeps
    within-burst correlation out of the test set (design 11.4). IoT-23 rows carry a
    real temporal order within a capture, so the device alone is the right block.

    N-BaIoT carries no timestamp: row order there is the order its per-attack CSVs were
    concatenated, so splitting on the device tail alone hands the test set whichever
    attack file happens to come last. Measured, that produced a test set which was
    100% malicious against a 87.5% malicious training set. Passing `block` (device
    crossed with traffic type) takes the tail of each file instead, which preserves the
    ordering property and keeps the class mix representative.
    """
    tr = np.zeros(len(y), bool)
    keys = device if block is None else np.array(
        [f"{d}|{b}" for d, b in zip(device, block)])
    for d in np.unique(keys):
        ix = np.where(keys == d)[0]
        tr[ix[: int(train_frac * len(ix))]] = True
    return tr, ~tr


def standardize(Xtr: np.ndarray, Xte: np.ndarray):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    return (Xtr - mu) / sd, (Xte - mu) / sd, mu, sd
