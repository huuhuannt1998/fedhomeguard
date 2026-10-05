import sys, os
import numpy as np, pytest, torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import defenses as D, attacks as A, config as CFG
from fedhomeguard.models import MLP, get_flat, set_flat, n_params


def _upd(vals):
    return {i: torch.tensor(v, dtype=torch.float32) for i, v in enumerate(vals)}


def test_fedavg_is_the_mean():
    out = D.fedavg(_upd([[0.0, 0.0], [2.0, 4.0]]))
    assert torch.allclose(out, torch.tensor([1.0, 2.0]))


def test_trimmed_mean_rejects_a_gross_outlier():
    u = _upd([[1.0], [1.1], [0.9], [1.0], [1000.0]])
    assert abs(D.trimmed_mean(u, trim_frac=0.2).item() - 1.0) < 0.2
    assert D.fedavg(u).item() > 100              # the mean is destroyed


def test_median_rejects_outliers():
    u = _upd([[1.0], [1.1], [0.9], [1.0], [1e6]])
    assert abs(D.median(u).item() - 1.0) < 0.2


def test_krum_picks_a_point_in_the_honest_cluster():
    u = _upd([[0.0, 0.0], [0.1, 0.1], [0.0, 0.1], [50.0, 50.0]])
    assert D.krum(u, n_mal=1).norm().item() < 1.0


def test_norm_clip_bounds_contribution():
    u = _upd([[100.0, 0.0], [0.0, 0.0]])
    assert D.norm_clip(u, clip_norm=1.0).norm().item() <= 1.0 + 1e-5


def test_oracle_is_labelled_upper_bound_and_drops_true_malicious():
    u = _upd([[1.0], [1.0], [999.0]])
    assert D.oracle_trimmed(u, malicious_ids=(2,)).item() == pytest.approx(1.0)
    assert "oracle_trimmed" in D.IS_UPPER_BOUND


def test_fltrust_refuses_without_server_root_data():
    with pytest.raises(ValueError, match="L2"):
        D.fltrust(_upd([[1.0]]))
    assert "fltrust" in D.REQUIRES_CLEAN_SERVER_DATA and D.LEVEL["fltrust"] == "L2"


def test_observability_lattice_is_enforced():
    D.check_observability("fedavg", "L0")
    D.check_observability("krum", "L1")
    with pytest.raises(ValueError, match="consumes"):
        D.check_observability("fltrust", "L1")      # L2 defense declared as L1
    with pytest.raises(ValueError):
        D.check_observability("oracle_trimmed", "L1")


def test_attack_capability_gate_is_enforced():
    A.check_capability("label_flip", "black_box")
    with pytest.raises(ValueError, match="needs F3"):
        A.check_capability("ipm", "gray_box")       # IPM needs honest updates
    with pytest.raises(ValueError, match="needs F3"):
        A.check_capability("alie", "black_box")


def test_l2_ball_projection_enforces_F2():
    u = torch.tensor([3.0, 4.0])                    # norm 5
    assert A.project(u, "l2_ball", 1.0).norm().item() == pytest.approx(1.0)
    assert A.project(u, "byzantine_unbounded", None).norm().item() == pytest.approx(5.0)
    with pytest.raises(ValueError):
        A.project(u, "l2_ball", None)


def test_select_malicious_size_and_determinism():
    assert A.select_malicious(20, 0.0, 0) == []
    assert len(A.select_malicious(20, 0.20, 0)) == 4
    assert A.select_malicious(20, 0.20, 3) == A.select_malicious(20, 0.20, 3)


def test_label_flip_flips_binary_labels():
    y = torch.tensor([0, 1, 1, 0])
    assert torch.equal(A.poison_labels(y), torch.tensor([1, 0, 0, 1]))


def test_flat_roundtrip_preserves_parameters():
    m = MLP(6, (5, 4))
    v = get_flat(m).clone()
    set_flat(m, torch.zeros_like(v)); set_flat(m, v)
    assert torch.allclose(get_flat(m), v) and n_params(m) == v.numel()


# --- review r6: the single-honest-update NaN in alie/gaussian and its correction ---
def _honest(n, d=7, seed=0):
    g = torch.Generator(); g.manual_seed(seed)
    return [torch.randn(d, generator=g) for _ in range(n)]


@pytest.mark.parametrize("attack", ["alie", "gaussian"])
def test_single_honest_update_is_finite_by_default_and_nan_only_in_legacy_mode(attack):
    theta = torch.zeros(7); h = _honest(1)
    ok = A.malicious_update(attack, theta, h, 1.0, torch.Generator().manual_seed(1))
    assert torch.isfinite(ok).all()
    assert torch.allclose(ok, h[0], atol=1e-9)   # sd = 0: the attack returns the peer
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bad = A.malicious_update(attack, theta, h, 1.0, torch.Generator().manual_seed(1),
                                 single_honest_zero_sd=False)
    assert torch.isnan(bad).all()            # the frozen pre-correction behaviour


@pytest.mark.parametrize("attack", ["alie", "gaussian"])
@pytest.mark.parametrize("n", [2, 3, 5])
def test_correction_is_bit_identical_with_two_or_more_honest_updates(attack, n):
    theta = torch.zeros(7); h = _honest(n, seed=n)
    a = A.malicious_update(attack, theta, h, 1.0, torch.Generator().manual_seed(3),
                           single_honest_zero_sd=False)
    b = A.malicious_update(attack, theta, h, 1.0, torch.Generator().manual_seed(3))
    assert torch.equal(a, b)


def test_population_std_arm_also_gives_zero_spread_for_one_update():
    h = _honest(1, d=3)
    out = A.malicious_update("alie", torch.zeros(3), h, 1.0, pop_std=True)
    assert torch.allclose(out, h[0], atol=1e-9)


@pytest.mark.parametrize("legacy", [False, True])
def test_one_honest_one_malicious_member_end_to_end(legacy):
    """fl_run with one honest and one alie client: finite by default, non-finite only
    when the config asks for the frozen legacy behaviour."""
    import warnings
    from fedhomeguard import fl as FL
    cfg = CFG.load(os.path.join(os.path.dirname(__file__), "..", "configs",
                                "stage3_certification.yaml"))
    cfg.device = "cpu"; cfg.fl.rounds_T = 2
    cfg.adversary.F3_knowledge = "white_box"
    cfg.adversary.legacy_nan_std = legacy
    g = torch.Generator().manual_seed(0)
    X = torch.randn(80, 5, generator=g); y = (X[:, 0] > 0).long()
    parts = {0: torch.arange(0, 40), 1: torch.arange(40, 80)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = FL.fl_run(cfg, [0, 1], X, y, parts, malicious_ids=(1,), attack="alie")
    finite = all(torch.isfinite(p).all() for p in m.parameters())
    assert finite is (not legacy)
