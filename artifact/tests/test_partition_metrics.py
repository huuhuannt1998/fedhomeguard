import sys, os
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import partition as P, metrics as M


def _toy(n=1200, n_dev=6, seed=0):
    rng = np.random.default_rng(seed)
    device = rng.integers(0, n_dev, n)
    y = (rng.random(n) < 0.3 + 0.1 * device).astype(int)
    return y, device


def test_iid_partition_has_near_zero_skew():
    y, d = _toy()
    p = P.iid_partition(len(y), 10, seed=0)
    assert P.skew_js(p, y, d) < 0.05


def test_device_derived_partition_has_high_skew():
    y, d = _toy()
    p = P.device_derived_partition(d, 10, seed=0)
    assert P.skew_js(p, y, d) > 0.3
    assert P.skew_device(p, d) > 0.3


def test_partition_is_a_true_partition_no_overlap_no_loss():
    y, d = _toy()
    for p in (P.iid_partition(len(y), 8, 0), P.device_derived_partition(d, 8, 0),
              P.dirichlet_partition(y, 8, 0.5, 0)):
        allidx = np.concatenate([p[i] for i in p])
        assert len(allidx) == len(np.unique(allidx))       # disjoint
        assert len(allidx) == len(y)                        # exhaustive


def test_partition_is_deterministic_given_seed():
    y, d = _toy()
    a = P.device_derived_partition(d, 10, seed=7)
    b = P.device_derived_partition(d, 10, seed=7)
    assert all(np.array_equal(a[i], b[i]) for i in a)


def test_dirichlet_skew_decreases_with_alpha():
    y, d = _toy()
    s = [P.skew_js(P.dirichlet_partition(y, 10, a, 0), y, d) for a in (0.05, 0.5, 5.0, 100.0)]
    assert all(x >= z - 1e-6 for x, z in zip(s, s[1:]))


def test_device_dirichlet_is_the_better_matched_control():
    """ALGORITHM 4. Label-Dirichlet leaves every device visible to every client, so it
    matches a device-derived partition worse on BOTH skew axes. The control must move
    the device axis or the necessity test compares two different kinds of skew."""
    y, d = _toy()
    dev = P.device_derived_partition(d, 10, seed=0)
    t_js, t_dev = P.skew_js(dev, y, d), P.skew_device(dev, d)
    pd_, _, s_dev_mode = P.dirichlet_matched(y, d, 10, t_js, seed=0, tol=0.02, mode="device")
    pl_, _, s_lab_mode = P.dirichlet_matched(y, d, 10, t_js, seed=0, tol=0.02, mode="label")
    assert abs(s_dev_mode - t_js) <= abs(s_lab_mode - t_js)
    assert abs(P.skew_device(pd_, d) - t_dev) < abs(P.skew_device(pl_, d) - t_dev)


def test_matched_control_never_starves_a_client():
    """A partition with empty clients is degenerate AND makes S_JS non-monotone in
    alpha. The matcher must reject such partitions rather than score them."""
    y, d = _toy()
    t = P.skew_js(P.device_derived_partition(d, 10, seed=0), y, d)
    p, _a, _s = P.dirichlet_matched(y, d, 10, t, seed=0, tol=0.02, mode="device",
                                    min_client_rows=1)
    assert P.count_empty(p, 1) == 0


def test_skew_js_is_monotone_in_alpha_once_empty_clients_excluded():
    y, d = _toy()
    vals = [P.skew_js(P.dirichlet_device_partition(d, 10, a, 0), y, d)
            for a in (0.1, 1.0, 10.0, 100.0)]
    assert all(x >= z - 1e-9 for x, z in zip(vals, vals[1:])), vals


def test_device_dirichlet_spans_the_skew_range():
    y, d = _toy()
    lo = P.skew_js(P.dirichlet_device_partition(d, 10, 1000.0, 0), y, d)
    hi = P.skew_js(P.dirichlet_device_partition(d, 10, 0.1, 0), y, d)
    assert lo < 0.1 < hi


def test_leave_one_device_out_removes_that_device():
    y, d = _toy()
    p = P.leave_one_device_out(d, 10, drop=2, seed=0)
    present = np.unique(np.concatenate([d[p[i]] for i in p if len(p[i])]))
    assert 2 not in present


def test_tau_triv_is_the_majority_class_rate():
    assert M.tau_triv(np.array([1, 1, 1, 0])) == pytest.approx(0.75)
    assert M.tau_triv(np.array([0, 1])) == pytest.approx(0.5)


def test_balanced_index_is_balanced():
    y = np.array([1] * 900 + [0] * 100)
    b = M.balanced_index(y, 0)
    assert y[b].mean() == pytest.approx(0.5)


def test_gap_flags_negative_gamma_as_bug():
    assert M.gap(0.93, 0.09)["Gamma"] == pytest.approx(0.84)
    assert M.gap(0.50, 0.80)["bug"] is True     # certified > empirical worst case
    assert M.gap(0.93, 0.09)["bug"] is False


def test_ea_min_is_max_over_defenses_of_min_over_attacks():
    """The literature claims per-defense robustness and an operator picks one defense,
    so a plain min over all (defense, attack) pairs would compare the certificate
    against the weakest defense and manufacture spurious Gamma < 0."""
    recs = [
        {"defense": "fedavg", "attack": "ipm", "EA": 0.10},
        {"defense": "fedavg", "attack": "alie", "EA": 0.40},
        {"defense": "trimmed_mean", "attack": "ipm", "EA": 0.88},
        {"defense": "trimmed_mean", "attack": "alie", "EA": 0.93},
    ]
    r = M.ea_min(recs)
    assert r["EA_min"] == pytest.approx(0.88)          # trimmed_mean's worst case
    assert r["best_defense"] == "trimmed_mean" and r["argmin_attack"] == "ipm"
    assert r["per_defense"]["fedavg"]["EA_min"] == pytest.approx(0.10)


def test_ea_min_excludes_the_L3_oracle_upper_bound():
    recs = [{"defense": "trimmed_mean", "attack": "ipm", "EA": 0.88},
            {"defense": "oracle_trimmed", "attack": "ipm", "EA": 0.99}]
    assert M.ea_min(recs)["best_defense"] == "trimmed_mean"
