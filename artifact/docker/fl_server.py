"""The server. Stock FedAvg aggregation, plus instrumentation.

The strategy subclass adds NO defence and changes NO aggregation -- it records what
an L1 server (one that sees individual updates, Section IX of the paper) could
observe about each contribution. Whether those observables separate the compromised
households from the honest ones is a measurement, not an assumption.
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np, torch
import flwr as fl
from flwr.common import parameters_to_ndarrays, ndarrays_to_parameters
import fl_common as C

LOG: list[dict] = []


def _flat(nds): return np.concatenate([np.asarray(a).ravel() for a in nds])


class InstrumentedFedAvg(fl.server.strategy.FedAvg):
    """FedAvg, unmodified in its aggregation, with per-contribution observables."""

    def __init__(self, *a, root: str, mal_ids: set[int], **kw):
        super().__init__(*a, **kw)
        self.root, self.mal_ids = root, mal_ids
        self.meta = C.load_meta(root)
        self.model = C.build_model(self.meta)
        self.Xte, self.yte = C.load_test(root)
        self.prev_global: np.ndarray | None = None

    def aggregate_fit(self, server_round, results, failures):
        vecs, rows = {}, []
        for cp, fitres in results:
            nds = parameters_to_ndarrays(fitres.parameters)
            cid = int(fitres.metrics.get("cid", -1))
            vecs[cid] = _flat(nds)
            rows.append(dict(cid=cid, n=fitres.num_examples,
                             bytes=sum(len(t) for t in fitres.parameters.tensors),
                             dtypes=sorted({str(np.asarray(a).dtype) for a in nds}),
                             shapes_ok=[tuple(np.asarray(a).shape) for a in nds]
                                       == [tuple(p.shape) for p in self.model.state_dict().values()],
                             finite=bool(np.all(np.isfinite(_flat(nds)))),
                             train_secs=fitres.metrics.get("train_secs")))
        if vecs:
            M = np.stack([vecs[c] for c in sorted(vecs)])
            mean = M.mean(0)
            for r in rows:
                v = vecs[r["cid"]]
                d = v - self.prev_global if self.prev_global is not None else v
                r.update(l2=float(np.linalg.norm(v)),
                         update_l2=float(np.linalg.norm(d)),
                         cos_to_mean=float(v @ mean / (np.linalg.norm(v) * np.linalg.norm(mean) + 1e-12)),
                         malicious=r["cid"] in self.mal_ids, round=server_round)
            LOG.extend(rows)

        agg, metrics = super().aggregate_fit(server_round, results, failures)
        if agg is not None:
            nds = parameters_to_ndarrays(agg)
            self.prev_global = _flat(nds)
            C.set_params(self.model, nds)
            self.model.eval()
            with torch.no_grad():
                pred = self.model(self.Xte).argmax(1).cpu().numpy()
            acc = float((pred == self.yte).mean())
            metrics = dict(metrics or {}, accuracy=acc)
            print(f"[round {server_round}] acc={acc:.4f} clients={len(results)} "
                  f"failures={len(failures)}", flush=True)
        return agg, metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("HH_ROOT", "/data"))
    ap.add_argument("--rounds", type=int, default=int(os.environ.get("ROUNDS", "15")))
    ap.add_argument("--clients", type=int, default=int(os.environ.get("N_CLIENTS", "20")))
    ap.add_argument("--mal", default=os.environ.get("MAL_IDS", ""))
    ap.add_argument("--out", default=os.environ.get("OUT", "/out/realstack.json"))
    a = ap.parse_args()
    mal = {int(x) for x in a.mal.split(",") if x.strip() != ""}

    strat = InstrumentedFedAvg(
        root=a.root, mal_ids=mal,
        fraction_fit=1.0, fraction_evaluate=0.0,
        min_fit_clients=a.clients, min_available_clients=a.clients,
        on_fit_config_fn=lambda r: {"server_round": r})

    t0 = time.time()
    hist = fl.server.start_server(server_address="0.0.0.0:8080",
                                  config=fl.server.ServerConfig(num_rounds=a.rounds),
                                  strategy=strat)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    accs = {int(r): float(v) for r, v in hist.metrics_distributed_fit.get("accuracy", [])} \
        if hasattr(hist, "metrics_distributed_fit") else {}
    with open(a.out, "w") as fh:
        json.dump(dict(rounds=a.rounds, clients=a.clients, malicious=sorted(mal),
                       wall_secs=round(time.time() - t0, 2),
                       accuracy_by_round=accs, contributions=LOG,
                       meta=strat.meta), fh)
    print(f"wrote {a.out}: {len(LOG)} contribution records", flush=True)


if __name__ == "__main__":
    main()
