"""A compromised household.

This is the whole of the attacker's code. It subclasses the honest client and
overrides one method; the honest client, fl_common, and the server are untouched.
That is the point of keeping it in a separate file: the diff against an honest
participant is this file, and it is countable.

KNOWLEDGE, HONESTLY. The simulation hands the malicious update function the other
clients' updates. A single compromised household cannot see those -- Flower delivers
only the global model. So the white-box attacks are given an ESTIMATOR that a real
client actually has: under FedAvg the client observes theta^{t+1} and theta^t, so
the aggregate update is their difference, and knowing its own contribution it can
solve for the honest mean. Round 1 has no trajectory yet, so the estimator falls
back to the client's own update, which is the weakest an attacker could do.
"""
from __future__ import annotations
import argparse, os
import numpy as np, torch
import flwr as fl
import fl_common as C
from fl_client import HouseholdClient

BLACK_BOX = {"label_flip", "gaussian"}      # own data only
GRAY_BOX = {"sign_flip"}                    # + the global model
WHITE_BOX = {"ipm", "alie"}                 # + an estimate of the honest aggregate


class MaliciousHousehold(HouseholdClient):
    def __init__(self, root: str, cid: int, attack: str, scale: float, n_mal: int, N: int):
        super().__init__(root, cid)
        self.attack, self.scale, self.n_mal, self.N = attack, scale, n_mal, N
        self._prev_global: list[np.ndarray] | None = None
        self._prev_sent: list[np.ndarray] | None = None

    def _estimate_honest_mean(self, theta: list[np.ndarray]) -> list[np.ndarray]:
        """Solve the previous round's FedAvg for the honest mean. With the aggregate
        a = (n_mal*sent + (N-n_mal)*honest)/N observed as theta_t - theta_{t-1}."""
        if self._prev_global is None or self._prev_sent is None:
            return theta
        out = []
        for cur, prev, sent in zip(theta, self._prev_global, self._prev_sent):
            agg = cur - prev
            honest = (self.N * agg - self.n_mal * (sent - prev)) / max(self.N - self.n_mal, 1)
            out.append(prev + honest)
        return out

    def fit(self, parameters, config):
        theta = [np.array(p, copy=True) for p in parameters]

        if self.attack == "label_flip":                     # poison data, train honestly
            saved = self.y
            self.y = 1 - self.y
            params, n, meta = super().fit(parameters, config)
            self.y = saved
        else:
            params, n, meta = super().fit(parameters, config)

        mu = self._estimate_honest_mean(theta) if self.attack in WHITE_BOX else params
        rng = np.random.default_rng(abs(hash((self.cid, int(config.get("server_round", 0))))) % 2**32)

        if self.attack in ("sign_flip", "ipm"):
            params = [t - self.scale * (m - t) for t, m in zip(theta, mu)]
        elif self.attack == "gaussian":
            params = [p + self.scale * rng.standard_normal(p.shape).astype(p.dtype) * (np.std(p) + 1e-12)
                      for p in params]
        elif self.attack == "alie":
            params = [m - self.scale * (np.std(m) + 1e-12) for m in mu]

        self._prev_global, self._prev_sent = theta, [np.array(p, copy=True) for p in params]
        meta.update(malicious=True, attack=self.attack)
        return params, n, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", type=int, required=True)
    ap.add_argument("--root", default=os.environ.get("HH_ROOT", "/data"))
    ap.add_argument("--server", default=os.environ.get("FL_SERVER", "server:8080"))
    ap.add_argument("--attack", default=os.environ.get("ATTACK", "sign_flip"))
    ap.add_argument("--scale", type=float, default=float(os.environ.get("SCALE", "1.0")))
    ap.add_argument("--n-mal", type=int, default=int(os.environ.get("N_MAL", "1")))
    ap.add_argument("--N", type=int, default=int(os.environ.get("N_CLIENTS", "20")))
    a = ap.parse_args()
    fl.client.start_client(
        server_address=a.server,
        client=MaliciousHousehold(a.root, a.cid, a.attack, a.scale, a.n_mal, a.N).to_client())


if __name__ == "__main__":
    main()
