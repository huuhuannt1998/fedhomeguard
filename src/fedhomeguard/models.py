"""Small models sized for a single M4 laptop (design D3 / 11.6)."""
from __future__ import annotations
import torch, torch.nn as nn


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


class AutoEncoderClassifier(nn.Module):
    """Reconstruction-error anomaly detector exposed as a 2-logit classifier so the
    certification and voting machinery is identical across model families."""
    def __init__(self, d: int, hidden=(32, 16)):
        super().__init__()
        h1, h2 = (hidden + (16,))[:2]
        self.enc = nn.Sequential(nn.Linear(d, h1), nn.ReLU(), nn.Linear(h1, h2), nn.ReLU())
        self.dec = nn.Sequential(nn.Linear(h2, h1), nn.ReLU(), nn.Linear(h1, d))
        self.register_buffer("thresh", torch.tensor(1.0))

    def recon_error(self, x):
        return ((self.dec(self.enc(x)) - x) ** 2).mean(1)

    def forward(self, x):
        e = self.recon_error(x)
        return torch.stack([self.thresh - e, e - self.thresh], 1)


def build_model(cfg, d: int) -> nn.Module:
    arch = cfg.model.arch
    hidden = tuple(cfg.model.hidden)
    # Defaults to 2, so every binary configuration builds exactly the model it did
    # before. The multi-class control (E2) sets it from the label space.
    nc = int(getattr(cfg.model, "n_class", 2) or 2)
    if arch == "mlp":
        return MLP(d, hidden, n_class=nc)
    if arch == "logreg":
        return MLP(d, (), n_class=nc)   # no hidden layer: multinomial logistic regression
    if arch == "mlp_large":
        return MLP(d, (128, 64, 32), n_class=nc)
    if arch == "autoencoder":
        if nc != 2:
            raise ValueError("the autoencoder head is a 2-logit reconstruction "
                             "detector and has no multi-class form")
        return AutoEncoderClassifier(d, hidden)
    raise ValueError(f"unknown arch {arch!r}")


def get_flat(m: nn.Module) -> torch.Tensor:
    return torch.cat([p.data.flatten() for p in m.parameters()])


def set_flat(m: nn.Module, v: torch.Tensor) -> None:
    i = 0
    for p in m.parameters():
        n = p.numel(); p.data.copy_(v[i:i + n].view_as(p)); i += n


def n_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


def resolve_device(spec: str = "auto") -> str:
    if spec != "auto":
        return spec
    return "mps" if torch.backends.mps.is_available() else "cpu"
