"""Machine-readable capability record. Anything not in the record was not assumed."""
from __future__ import annotations
import json, os, platform, subprocess, time
from typing import Any

RECORD_VERSION = "1.0"


def _git_rev() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def build_record(cfg, *, run_id: str, partition_meta: dict, n_params: int,
                 metrics: dict | None = None, budget: dict | None = None,
                 malicious_ids=(), attacks_run=()) -> dict[str, Any]:
    from . import defenses as D
    return {
        "record_version": RECORD_VERSION,
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_rev": _git_rev(),
        "federation": {
            "N": cfg.partition.N, "rounds_T": cfg.fl.rounds_T,
            "local_epochs_E": cfg.fl.local_epochs_E, "batch_size": cfg.fl.batch_size,
            "optimizer": "sgd", "lr": cfg.fl.lr, "momentum": cfg.fl.momentum,
            "model": {"arch": cfg.model.arch, "hidden": list(cfg.model.hidden),
                      "params_p": int(n_params)},
        },
        "partition": {"dataset": cfg.data.dataset, "split": cfg.data.split,
                      **partition_meta,
                      "note": "S_JS / S_dev are MEASURED from the realized partition, never set"},
        "adversary": {
            "beta": cfg.adversary.beta, "m": len(malicious_ids),
            "malicious_ids": list(malicious_ids),
            "F1_count_bound": len(malicious_ids),
            "F2_update_space": cfg.adversary.F2_update_space, "F2_rho": cfg.adversary.F2_rho,
            "F3_knowledge": cfg.adversary.F3_knowledge,
            "F4_knows_subsample_seed": cfg.adversary.F4_knows_subsample_seed,
            "F5_membership": cfg.adversary.F5_membership,
            "F6_may_poison_data": cfg.adversary.F6_may_poison_data,
            "attack_ids": list(attacks_run),
        },
        "defense": {
            "name": cfg.defense.name,
            "observability_level": cfg.defense.observability,
            "declared_level_required": D.LEVEL[cfg.defense.name],
            "requires_clean_server_data": cfg.defense.name in D.REQUIRES_CLEAN_SERVER_DATA,
            "is_upper_bound_not_achievable": cfg.defense.name in D.IS_UPPER_BOUND,
            "knows_true_beta": cfg.defense.knows_true_beta,
        },
        "certification": {
            "family": cfg.cert.family, "K": cfg.cert.K, "k": cfg.cert.k,
            "prefer_exact": cfg.cert.prefer_exact, "confidence": cfg.cert.confidence,
            "interval": "clopper_pearson_when_sampled_none_when_exact",
        },
        "budget": {**(budget or {}), "headline": "equal_total_gradient_steps",
                   "device": platform.platform(), "note": "single laptop; no cluster; no GPU tier"},
        "metrics": metrics or {},
        "seeds": {"partition_seed": cfg.partition.seed, "train_seed": cfg.fl.seed,
                  "adversary_seed": cfg.adversary.seed},
        "non_guarantees": [
            "nothing if |B| > m (cliff, not a slope)",
            "nothing if the adversary learns the subsample seed (F4 violated)",
            "nothing about sybils: m bounds clients, not humans",
            "nothing about server compromise or server-adversary collusion",
            "no privacy claim of any kind",
            "nothing about availability / DoS on aggregation",
            "abstention is not safety; abstaining points are still classified in deployment",
            "CERT-WRONG points are provably stable AND wrong",
            "nothing across time: drift, new firmware, new attack families",
            "nothing about devices outside the catalog",
            "the smoothing certificate bounds MAGNITUDE, not client count; never add them",
        ],
    }


def save(record: dict, out_dir: str, run_id: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{run_id}.capability.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=2, default=str)
    return path
