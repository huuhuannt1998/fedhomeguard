"""Experiment configuration. Every run is fully described by a Config."""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field, asdict
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class DataCfg:
    dataset: str = "iot-23"              # iot-23 | n-baiot | ciciot2023
    root: str = "data/raw"
    max_rows_per_device: int = 60_000
    train_frac: float = 0.8
    split: str = "time_within_device"    # never random row shuffle (design 11.4)
    binary: bool = True
    lodo_device: str | None = None   # W7: hold this device out of training



@dataclass
class PartitionCfg:
    kind: str = "device_derived"         # device_derived | dirichlet | dirichlet_matched | iid
    N: int = 20
    devices_per_household: tuple[int, int] = (1, 3)
    dirichlet_alpha: float | None = None
    match_target_S_JS: float | None = None   # for dirichlet_matched (Algorithm 4)
    match_tol: float = 0.01
    match_mode: str = "device"   # device | label (see partition.dirichlet_matched)
    min_client_rows: int = 16    # a client that cannot train is not a participant
    drop_device: str | None = None           # for leave-one-device-out (Algorithm 5)
    seed: int = 0


@dataclass
class ModelCfg:
    arch: str = "mlp"                    # mlp | mlp_large | autoencoder
    hidden: tuple[int, ...] = (32, 16)
    # Output width. Stays 2 for the binary detector; load_dataset raises it to the
    # number of IoT-23 attack families when data.binary is False (E2 multi-class
    # control). Carried on the config rather than inferred at each call site so that
    # every member of an ensemble is built with the same head.
    n_class: int = 2


@dataclass
class FLCfg:
    rounds_T: int = 15
    local_epochs_E: int = 1
    class_balanced: bool = False   # inverse-frequency local loss (review W3/E2)
    lr: float = 0.05
    momentum: float = 0.9
    batch_size: int = 512
    seed: int = 0


@dataclass
class AdversaryCfg:
    beta: float = 0.0
    attack: str | None = None            # see attacks.REGISTRY
    F2_update_space: str = "byzantine_unbounded"   # | l2_ball
    F2_rho: float | None = None
    F3_knowledge: str = "gray_box"       # black_box | gray_box | white_box
    F4_knows_subsample_seed: bool = False
    F5_membership: str = "static"
    F6_may_poison_data: bool = False
    scale: float = 1.0
    vote_shape_frac: float = 0.5   # share of local labels the
                                   # vote_shape attack flips
    seed: int = 0


@dataclass
class DefenseCfg:
    name: str = "fedavg"                 # see defenses.REGISTRY
    observability: str = "L0"            # L0 | L1 | L2 | L3
    trim_frac: float | None = None
    clip_norm: float | None = None
    knows_true_beta: bool = False
    root_size: int = 100                 # FLTrust server root set (L2)
    noise_sigma: float = 0.0   # CRFL: Gaussian noise added to the aggregate



@dataclass
class CertCfg:
    family: str = "flcert_subsample"     # flcert_subsample | crfl_smoothing | none
    k: int = 5
    K: int = 100
    prefer_exact: bool = True
    confidence: float = 0.999
    # CRFL
    smooth_sigma: float = 0.01
    clip_norm: float = 5.0
    n_smooth: int = 200


@dataclass
class Config:
    name: str = "unnamed"
    stage: int = 0
    device: str = "auto"                 # auto | mps | cpu
    out_dir: str = "results"
    betas: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40)
    seeds: tuple[int, ...] = (0,)
    data: DataCfg = field(default_factory=DataCfg)
    partition: PartitionCfg = field(default_factory=PartitionCfg)
    model: ModelCfg = field(default_factory=ModelCfg)
    fl: FLCfg = field(default_factory=FLCfg)
    adversary: AdversaryCfg = field(default_factory=AdversaryCfg)
    defense: DefenseCfg = field(default_factory=DefenseCfg)
    cert: CertCfg = field(default_factory=CertCfg)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


_SUB = {"data": DataCfg, "partition": PartitionCfg, "model": ModelCfg, "fl": FLCfg,
        "adversary": AdversaryCfg, "defense": DefenseCfg, "cert": CertCfg}


def from_dict(d: dict[str, Any]) -> Config:
    d = dict(d)
    kw = {k: _SUB[k](**d.pop(k)) for k in list(d) if k in _SUB}
    for key in ("betas", "seeds"):
        if key in d and d[key] is not None:
            d[key] = tuple(d[key])
    return Config(**d, **kw)


def load(path: str) -> Config:
    with open(path) as f:
        if path.endswith((".yaml", ".yml")):
            if yaml is None:
                raise RuntimeError("pyyaml not installed; use a .json config")
            return from_dict(yaml.safe_load(f))
        return from_dict(json.load(f))
