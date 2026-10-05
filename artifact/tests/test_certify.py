"""Certification math is the critical correctness surface: if it is wrong, every
number in the paper is wrong. These tests pin the invariants."""
import math, sys, os
import numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import certify as C


def test_p_clean_endpoints():
    assert C.p_clean(20, 0, 5) == 1.0
    assert C.p_clean(20, 16, 5) == 0.0            # N-m < k
    assert C.p_clean(20, 2, 5) == pytest.approx(math.comb(18, 5) / math.comb(20, 5))


def test_p_clean_monotone_decreasing_in_m():
    v = [C.p_clean(50, m, 5) for m in range(0, 20)]
    assert all(a >= b for a, b in zip(v, v[1:]))


def test_threshold_matches_measured_m1_cliff():
    """M1 measured CA=0.9794 at beta=0.10 and EXACTLY 0.0 at beta=0.20, N=20,k=5."""
    assert C.cert_threshold(20, 2, 5) == pytest.approx(0.8947, abs=1e-4)
    assert C.cert_threshold(20, 4, 5) == pytest.approx(1.4365, abs=1e-4)
    assert C.is_certifiable(20, 2, 5)
    assert not C.is_certifiable(20, 4, 5)         # threshold > 1 >= margin


def test_beta_geo_matches_asymptotic_ceiling():
    for k in (1, 2, 3, 5, 8, 10, 20):
        assert C.beta_geo(1000, k) == pytest.approx(C.beta_geo_asymptotic(k), abs=0.01)


def test_beta_geo_independent_of_N_for_large_N():
    """THE headline structural fact: more clients does NOT raise the ceiling."""
    assert C.beta_geo(200, 5) == pytest.approx(C.beta_geo(1000, 5), abs=0.005)


def test_ceiling_blocks_literature_range():
    """k=5 can never certify past ~12.9%, yet the field evaluates 20-40%."""
    assert C.beta_geo_asymptotic(5) < 0.20
    assert C.beta_geo_asymptotic(2) < 0.30
    assert C.beta_geo_asymptotic(1) == pytest.approx(0.5)


def test_certify_unanimous_votes_certified_up_to_geo_ceiling():
    n, K, N, k = 200, 100, 20, 5
    y = np.zeros(n, int)
    votes = np.zeros((n, 2), int); votes[:, 0] = K          # unanimous & correct
    r = C.certify_from_votes(votes, y, N, k, [0.0, 0.10, 0.20], exact=True, tau_triv=0.5)
    g = {x["beta"]: x for x in r["grid"]}
    assert g[0.0]["CA"] == 1.0
    assert g[0.10]["CA"] == 1.0                              # thr=0.8947 < margin=1
    assert g[0.20]["CA"] == 0.0                              # thr=1.4365 > 1: impossible
    assert g[0.20]["combinatorially_possible"] is False
    assert r["beta_star"] == 0.10


def test_certified_wrong_is_flagged_not_counted_as_success():
    n, K = 100, 50
    y = np.ones(n, int)
    votes = np.zeros((n, 2), int); votes[:, 0] = K           # unanimous but WRONG
    r = C.certify_from_votes(votes, y, 20, 5, [0.0], exact=True, tau_triv=0.5)
    g = r["grid"][0]
    assert g["CA"] == 0.0 and g["cert_wrong"] == 1.0
    assert g["severity"] == "S4_certified_wrong"


def test_severity_classes_are_predeclared_and_ordered():
    assert C.severity(0.95, 0.73, 0.0, 0.1, 0.95) == "S0_informative"
    assert C.severity(0.78, 0.73, 0.0, 0.1, 0.95) == "S1_marginal"
    assert C.severity(0.70, 0.73, 0.0, 0.1, 0.95) == "S2_vacuous"
    assert C.severity(0.70, 0.73, 0.0, 0.0, 0.70) == "S3_collapsed"


def test_sampled_arm_is_conservative_vs_exact():
    """Clopper-Pearson must never certify MORE than exact counting."""
    n, K = 300, 100
    y = np.zeros(n, int)
    votes = np.zeros((n, 2), int); votes[:, 0] = 80; votes[:, 1] = 20
    ex = C.certify_from_votes(votes, y, 20, 5, [0.05], exact=True, tau_triv=0.5)
    sa = C.certify_from_votes(votes, y, 20, 5, [0.05], exact=False, tau_triv=0.5)
    assert sa["grid"][0]["CA"] <= ex["grid"][0]["CA"] + 1e-9
    assert sa["mean_margin"] <= ex["mean_margin"] + 1e-9


def test_choose_subsets_prefers_exact_when_affordable():
    subs, exact, total = C.choose_subsets(8, 2, K=100, prefer_exact=True)
    assert exact and total == 28 and len(subs) == 28
    subs, exact, total = C.choose_subsets(20, 5, K=100, prefer_exact=True)
    assert not exact and len(subs) == 100 and total == 15504


def test_hicc_verdict_requires_both_conditions():
    assert C.hicc_verdict(0.604, 1.4365, EA_min=0.93)["hicc_holds"] is True
    assert C.hicc_verdict(0.604, 1.4365, EA_min=0.50)["hicc_holds"] is False   # EA too low
    assert C.hicc_verdict(0.002, 0.5, EA_min=0.93)["hicc_holds"] is False      # budget ok


# --- c_max at federation sizes where enumerating every B is infeasible ----------
def test_c_max_upper_bound_is_sound_and_matches_exact_where_both_run():
    """The degree-sum bound must never UNDERSTATE c_max, or the certificate would be
    unsound. Checked against exact enumeration wherever the exact path is affordable."""
    from itertools import combinations
    import numpy as np
    from fedhomeguard.exactcert import (subset_masks, c_max_exact, c_max_upper)
    rng = np.random.default_rng(0)
    for N, k, K in ((12, 2, 40), (14, 3, 60), (20, 2, 190)):
        allc = list(combinations(range(N), k))
        sel = rng.choice(len(allc), size=min(K, len(allc)), replace=False)
        masks = subset_masks([allc[j] for j in sorted(sel)], N)
        for m in range(0, min(6, N)):
            exact, _ = c_max_exact(masks, N, m)
            ub = c_max_upper(masks, N, m)
            assert ub >= exact, (N, k, m, ub, exact)
            assert ub <= len(masks)


def test_c_max_bounded_never_hangs_at_large_N():
    """The case that hung the N=50 sweep: C(50,20) is ~4.7e13 and must not enumerate."""
    from itertools import combinations
    import numpy as np
    from fedhomeguard.exactcert import subset_masks, c_max_bounded
    rng = np.random.default_rng(0)
    allc = list(combinations(range(50), 3))
    masks = subset_masks([allc[j] for j in rng.choice(len(allc), 200, replace=False)], 50)
    c, mode, _ = c_max_bounded(masks, 50, 20)
    assert mode == "degree_upper_bound"
    assert 0 <= c <= 200


def test_certify_exact_records_which_c_max_path_was_used():
    import numpy as np
    from itertools import combinations
    from fedhomeguard.exactcert import certify_exact
    subs = list(combinations(range(20), 2))
    votes = np.tile(np.array([[len(subs), 0]]), (50, 1))
    y = np.zeros(50, dtype=int)
    out = certify_exact(votes, y, subs, 20, 2, [0.0, 0.1], tau_triv=0.5)
    assert all("c_max_mode" in g for g in out["grid"])
    assert out["grid"][0]["c_max_mode"] == "exact"
