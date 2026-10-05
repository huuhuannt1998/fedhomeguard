"""Shared pieces for the real-stack arm: the model, the household's data, and the
parameter (de)serialisation Flower moves over the wire.

The model must be bit-comparable with the simulation arm or the cross-validation
compares two different experiments, so MLP here mirrors fedhomeguard.models.MLP.
"""
from __future__ import annotations
import json, os
from collections import OrderedDict
import numpy as np, torch, torch.nn as nn


class MLP(nn.Module):
    def __init__(self, d: int, hidden=(32, 16), n_class: int = 2):
        super().__init__()
        layers, prev = [], d
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU()]; prev = h
        layers.append(nn.Linear(prev, n_class))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def load_meta(root: str) -> dict:
    with open(os.path.join(root, "meta.json")) as fh:
        return json.load(fh)


def build_model(meta: dict) -> nn.Module:
    hidden = () if meta.get("arch") == "logreg" else tuple(meta.get("hidden", (32, 16)))
    return MLP(int(meta["dim"]), hidden)


def load_household(root: str, cid: int):
    z = np.load(os.path.join(root, f"household_{cid:02d}.npz"))
    return torch.tensor(z["X"]), torch.tensor(z["y"])


def load_test(root: str):
    z = np.load(os.path.join(root, "test.npz"))
    return torch.tensor(z["X"]), z["y"]


def get_params(model: nn.Module) -> list[np.ndarray]:
    return [p.detach().cpu().numpy() for p in model.state_dict().values()]


def set_params(model: nn.Module, params: list[np.ndarray]) -> None:
    sd = OrderedDict((k, torch.tensor(v))
                     for k, v in zip(model.state_dict().keys(), params))
    model.load_state_dict(sd, strict=True)


def local_train(model: nn.Module, X, y, *, epochs: int, lr: float, momentum: float,
                bs: int, seed: int = 0) -> int:
    """One household's local training. Identical in form to the simulation's
    fl.local_train so a like-for-like comparison is meaningful."""
    torch.manual_seed(seed)
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum)
    lossf = nn.CrossEntropyLoss()
    n = len(y)
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            opt.zero_grad()
            lossf(model(X[idx]), y[idx]).backward()
            opt.step()
    return n
