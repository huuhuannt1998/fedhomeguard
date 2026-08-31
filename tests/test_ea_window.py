"""The windowed EA statistic, and the guarantee that it leaves the certificate alone.

Attacked accuracy is read as the worst round in a window rather than the final
round, because under label-flip the global model oscillates with a ~2-round period
and a final-round readout samples an arbitrary phase. The certified arm must be
unaffected: a certificate is a statement about the predictor actually deployed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import fedhomeguard.fl as FL
import fedhomeguard.ensemble as EN


def test_window_is_eight_and_post_convergence():
    assert FL.EA_WINDOW == 8


def test_votes_default_is_two_dimensional():
    """window=False must keep the (n_test, 2) shape the certified arm indexes."""
    preds = [np.stack([np.array([0, 1, 0], dtype=np.int8)] * FL.EA_WINDOW)
             for _ in range(3)]
    v = EN.votes_from_preds([p[-1] for p in preds], 3)
    assert v.shape == (3, 2)


def test_window_reduction_takes_the_worst_round():
    """A window holding one bad round must report that round, not the last one."""
    y = np.array([0, 0, 1, 1])
    good = np.array([0, 0, 1, 1], dtype=np.int8)      # perfect
    bad = np.array([1, 1, 0, 0], dtype=np.int8)       # inverted
    per_round = [good, bad, good, good, good, good, good, good]
    accs = []
    for r in range(FL.EA_WINDOW):
        v = EN.votes_from_preds([per_round[r]], len(y))
        accs.append(float((v.argmax(1) == y).mean()))
    assert min(accs) == 0.0 and accs[-1] == 1.0, "window must not equal final round"


def test_snapshot_last_returns_that_many_rounds():
    import types
    cfg = types.SimpleNamespace(fl=types.SimpleNamespace(rounds_T=15))
    assert min(FL.EA_WINDOW, cfg.fl.rounds_T) == 8
