"""An honest household. This file is what every honest participant runs, and it is
byte-identical across honest and compromised households -- the compromised ones run
fl_client_malicious.py, which imports this class and overrides one method.
"""
from __future__ import annotations
import argparse, os, sys, time
import flwr as fl
import fl_common as C


class HouseholdClient(fl.client.NumPyClient):
    def __init__(self, root: str, cid: int):
        self.cid = cid
        self.meta = C.load_meta(root)
        self.model = C.build_model(self.meta)
        self.X, self.y = C.load_household(root, cid)

    def get_parameters(self, config):
        return C.get_params(self.model)

    def fit(self, parameters, config):
        C.set_params(self.model, parameters)
        t0 = time.time()
        n = C.local_train(self.model, self.X, self.y,
                          epochs=int(self.meta["local_epochs_E"]),
                          lr=float(self.meta["lr"]),
                          momentum=float(self.meta["momentum"]),
                          bs=int(self.meta["batch_size"]),
                          seed=int(config.get("server_round", 0)) * 1000 + self.cid)
        return C.get_params(self.model), n, {"cid": self.cid,
                                             "train_secs": round(time.time() - t0, 4)}

    def evaluate(self, parameters, config):
        return 0.0, 1, {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", type=int, required=True)
    ap.add_argument("--root", default=os.environ.get("HH_ROOT", "/data"))
    ap.add_argument("--server", default=os.environ.get("FL_SERVER", "server:8080"))
    a = ap.parse_args()
    fl.client.start_client(server_address=a.server,
                           client=HouseholdClient(a.root, a.cid).to_client())


if __name__ == "__main__":
    main()
