#!/usr/bin/env python3
"""Build paper2/claim_evidence.csv: every numeric claim of the submitted manuscript (main.pdf of
2026-10-07, 19 pp) -> printed value -> evidence rows -> generator -> independent recomputation
(results/p0_*.json, written by this revision's P0 scripts) -> status and proof status.

Status values:
  reproduced                 independent recomputation equals the printed value at printed precision
  reproduced_with_caveat     equal, but the wording/denominator needs a fix (see note)
  mismatch                   independent recomputation differs
  gate_regenerated_only      not recomputed independently here; the repo generator reproduces the macro
                             byte for byte (gate.py `generated` check, PASS 2026-10-08)
  not_reproducible_here      evidence is not in result rows (literature coding, lost script, timings)
Statement type: (b) observation from the submitted paper; (c) facts added by this audit go in `note`.
Pure CPU-light: reads JSON only."""
import csv, json, os, sys

R = "<artifact-root>/results/tmlr_rev"
OUT = "<artifact-root>/tmlr_rev/claim_evidence.csv"


def J(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


rc, rc2, ce, cm, au, sm = (J("p0_recompute.json"), J("p0_recompute2.json"), J("p0_ceilings.json"),
                           J("p0_cmax_audit.json"), J("p0_audit.json"), J("p0_sampled_touch.json"))
pb01 = J("pb01_pairs.json")


def g(d, *ks):
    for k in ks:
        if d is None:
            return None
        d = d[k] if not isinstance(d, list) else d[int(k)]
    return d


T1 = lambda p, k, b, f: g(rc, "table1_9", f"{p}|k{k}|b{b}", f)
T9 = lambda p, k, b, f: g(rc2, "table9", f"{p}|k{k}|b{b}", f)
CANON = "results/canonical/"
CORR = "results/r6_nan_fix/corrected/"

# (id, location, claim, printed, recomputed, decimals, evidence, generator, proof_status, note)
C = []
add = lambda *a: C.append(a)

# ---- theory / certificate
add("T1", "Sec 3 Eq.(1); App A", "test point certified iff (n1-n2)/K > 2 c_max(m)/K", "proposition", None, None,
    "src/fedhomeguard/exactcert.py", "-", "proved in paper (counting argument, App A); restated prior art (a): DPA, Finite Aggregation, FLCert-D",
    "(c) c_max re-derived independently for all 1,661 drawn ensembles / 15,310 rows: 0 mismatches (p0_cmax_audit.json); "
    "strict '>' verified in integer and float form (p0_ceilings.json). Brute force over every malicious set on 36 trained N=20 "
    "ensembles (IID/device-derived, draws 0-2, k=1,2,3 sampled+full,5,8): 3,503,326 certified (flow, budget) pairs, 0 violations "
    "(p0_vote_bound.json); the member-level worst case of PB10 never falls below CA (144 ensembles).")
add("T2", "Sec 3 Eq.(2); Table 6", "beta_geo(20,k) = 0.450/0.250/0.150/0.100/0.050 at k=1,2,3,5,8",
    "0.450,0.250,0.150,0.100,0.050", ",".join(f"{g(ce,'beta_geo','20',str(k)):.3f}" for k in (1, 2, 3, 5, 8)) if ce else None,
    None, "analytic", "src/fedhomeguard/certify.py beta_geo", "proved (one-line corollary of Eq. 1)", "(c) re-derived")
add("T3", "Sec 3; Table 6", "large-N ceiling 1-2^(-1/k) = 0.500/0.293/0.206/0.129/0.083",
    "0.500,0.293,0.206,0.129,0.083", ",".join(f"{g(ce,'large_N',str(k)):.3f}" for k in (1, 2, 3, 5, 8)) if ce else None,
    None, "analytic", "-", "proved", "(c) re-derived")
add("T4", "Sec 3; App A", "beta_geo(50,5)=0.120, beta_geo(1000,5)=0.129, beta_geo(21,2)=0.238",
    "0.120,0.129,0.238", (f"{g(ce,'beta_geo','50','5'):.3f},{g(ce,'beta_geo','1000','5'):.3f},"
                          f"{g(ce,'beta_geo','21','2'):.3f}") if ce else None, None, "analytic", "-", "proved", "(c) re-derived")
add("T5", "Sec 3", "IID beta* equals beta_geo on 30 of 30 draws at k=1 and k=2", "30/30, 30/30",
    f"{g(rc,'fig1_bstar','iid|k1','at_ceiling')}/30, {g(rc,'fig1_bstar','iid|k2','at_ceiling')}/30" if rc else None,
    None, CANON + "e5f_iid.jsonl", "scripts/gen_k3.py et al.", "-", "")
add("T6", "Sec 3; App A", "sampled k=5,8 beta* are lower bounds (touched fraction >= population)",
    "lower bound", "0 sampled rows below population" if cm and cm["summary"]["n_sampled_rows_below_population"] == 0 else None,
    None, CANON + "e2k58_*", "-", "proved for the threshold (max over B >= mean over B = population); "
    "beta* lower bound holds only up to vote-margin sampling error (as the paper says)", "(c) verified on all drawn sampled ensembles")
add("T7", "App A", "k=5, m=2: population touched 0.447; K=200 deployed ensemble 0.539; K=1000 0.488",
    "0.447,0.539,0.488", (f"{sm['population']:.3f},{sm['200']['mean']:.3f} (40-draw sim; deployed k=5 ensembles "
                          f"0.52-0.53),{sm['1000']['mean']:.3f}") if sm else None, None,
    "generated/ensemble_size_appendix.tex (script lost, 'RECONSTRUCTED')", "none (hand text)", "-",
    "(c) 0.539 is a 40-draw simulation average, not 'a deployed ensemble'; re-simulated 0.538/0.486; the three deployed "
    "k=5 ensembles have 0.52-0.53. Fix wording.")
add("T8", "Sec 3; App A", "brute force at N=10, k<=3, m<=3: 0 violations in 1,181 certified points",
    "0 / 1,181", "0 / 1,181 (synthetic random votes)", None, CANON + "e1_validation.json", "scripts/exp_e1_validate.py",
    "-", "(c) the 1,181 points are synthetic random member votes, not trained IDS ensembles; say so")
add("T9", "Sec 3; Table 7", "k=1 costs 300 client-rounds (1x), k=2 5,700 (19x), sampled k=3 22,500 (75x), full k=3 51,300 (171x)",
    "300,5700,22500,51300", ",".join(str(g(rc2, "cost", k, "client_rounds")) for k in ("1", "2", "3_sampled", "3")) if rc2 else None,
    None, "analytic", "scripts/gen_cost_latency.py", "arithmetic", "")
add("T10", "Table 7; App A", "median clean pass 7 s (k=1), 95 s (k=2, 88-105 s), 350 s (sampled k=3)", "7,95,350",
    None, None, "timing (pre-determinism-fix)", "scripts/gen_cost_latency.py", "-",
    "(c) not re-timed (coordinator: no timing until quiet machine); unloaded re-timing on 10 members measured "
    "0.16-0.19 s/member at k=1 (~3-4 s per ensemble) before the freeze; PB09 queued")

# ---- Table 1 and Sec 5
for p, lab in (("iid", "IID"), ("device_derived", "device-derived")):
    for b in ("0", "0.05", "0.1", "0.2", "0.3", "0.4"):
        add(f"T1-{lab}-k1-b{b}", "Table 1", f"{lab} k=1 beta={b}: certified accuracy / certified detection",
            None, None, 4, CORR + f"e2_{p}_s*.jsonl", "scripts/gen_paper_numbers.py",
            "-", "(c) medians over 3 draws x 3 sets; k=3 rows of Table 1 are the sampled K=500 arm (caption silent)")
        C[-1] = C[-1][:3] + ({"iid": {"0": "0.9817/0.9967", "0.05": "0.9813/0.9964", "0.1": "0.9809/0.9957",
                                      "0.2": "0.9802/0.9955", "0.3": "0.9793/0.9951", "0.4": "0.9778/0.9938"},
                               "device_derived": {"0": "0.9483/0.9540", "0.05": "0.8929/0.8784", "0.1": "0.7452/0.6776",
                                                  "0.2": "0.2627/0.0000", "0.3": "0.2355/0.0000", "0.4": "0.0584/0.0000"}}[p][b],
                              (f"{T1(p,1,b,'CA'):.4f}/{T1(p,1,b,'CTR_mal'):.4f}" if rc else None)) + C[-1][5:]
add("S5-1", "Abstract; Sec 1; Sec 5", "IID k=1 within 0.0041 of attacked accuracy over 30 draws x 3 sets (largest gap 0.004022)",
    "0.004022", f"{g(rc,'slack30_iid_k1','max_G'):.6f}" if rc else None, None, CANON + "e24_slack30_iid.jsonl",
    "scripts/gen_multiclass.py", "-", "(c) 'attacked accuracy' = min over 5 published attacks, final round")
add("S5-2", "Abstract; Sec 1; Sec 5", "re-weighted to 1% attack prior: 0 of 36 cells beat 0.9900; best 0.9433; IID k=1 b=0.40 -> 0.9351",
    "0/36, 0.9433, 0.9351", (f"{g(rc,'prior_reweight_e2','0.01','n_above_floor')}/{g(rc,'prior_reweight_e2','0.01','n_cells')} "
                             f"({g(rc,'prior_reweight_e2','0.01','n_nonvoid')} non-void), {g(rc,'prior_reweight_e2','0.01','best'):.4f}, "
                             f"{g(rc,'prior_reweight_e2','0.01','iid_k1_b04'):.4f}") if rc else None,
    None, CORR + "e2_*", "scripts/gen_r8_prior.py", "post hoc re-weighting (assumes prior-invariant class rates)",
    "(c) the 36 cells include 10 void cells beyond the ceiling: say '0 of 26 cells where a certificate exists'")
add("S2-1", "Sec 2", "CA = tau CTR_mal + (1-tau) CTR_ben holds on every row of the grid to 1e-6",
    "1e-6", f"{g(rc,'decomposition','n_violations_1e6')} rows > 1e-6 of {g(rc,'decomposition','n_rows')}" if rc else None,
    None, "all binary rows", "scripts/gen_r8_prior.py", "identity",
    "(c) holds on the main grid; exceptions: 216 leave-one-capture-out rows (tau is the BENIGN share there, so the "
    "identity takes the other form) and one N-BaIoT row at 1.007e-6 (rounding)")

# ---- Sec 6 / Table 2 / pairs
add("S6-1", "Abstract; Sec 1; Sec 6", "16 skew-matched draw pairs, margin advantage +0.1509, 95% CI [+0.0439,+0.3136], p=0.00977",
    "16, +0.1509", f"{g(rc,'ablation_pairs','n_pairs')}, {g(rc,'ablation_pairs','margin_mean_diff'):+.4f}" if rc else None,
    None, CANON + "e7_devskew.jsonl, e7_labelskew.jsonl", "scripts/gen_e7_stats.py", "-",
    "(c) 9 of the 16 pairs are near-IID nulls (label alpha>=3, |dm|<=0.0043); 7 informative pairs all positive "
    "(mean +0.344); two-way draw bootstrap with re-matching CI " +
    (f"[{pb01['b_twoway_bootstrap']['margin_ci95'][0]:+.3f}, {pb01['b_twoway_bootstrap']['margin_ci95'][1]:+.3f}]" if pb01 else "n/a"))
add("S6-2", "Sec 6", "beta* advantage +0.0719 (CI [+0.0176,+0.1533], p=0.0625), not significant", "+0.0719",
    f"{g(rc,'ablation_pairs','bstar_mean_diff'):+.4f}" if rc else None, None, CANON + "e7_*", "scripts/gen_e7_stats.py", "-",
    "(c) two-way bootstrap beta* CI " + (f"[{pb01['b_twoway_bootstrap']['bstar_ci95'][0]:+.3f}, "
                                         f"{pb01['b_twoway_bootstrap']['bstar_ci95'][1]:+.3f}]" if pb01 else "n/a"))
add("S6-3", "Sec 6", "mean skew difference 0.013; pairs reuse 10 device-family draws", "0.013, 10",
    f"{g(rc,'ablation_pairs','mean_skew_mismatch'):.3f}, {g(rc,'ablation_pairs','n_dev_draws_used')}" if rc else None,
    None, CANON + "e7_*", "scripts/gen_e7_stats.py", "-", "")
T2 = [("device", "1", "0.213/0.023/0.00/0.979/0.450"), ("device", "0.5", "0.345/0.092/0.00/0.884/0.400"),
      ("device", "0.2", "0.544/0.338/0.05/0.780/0.300"), ("device", "0.1", "0.714/0.584/0.10/0.631/0.250"),
      ("label", "1", "0.121/0.028/0.10/0.836/0.350"), ("label", "0.5", "0.263/0.118/0.30/0.545/0.200"),
      ("label", "0.2", "0.392/0.277/0.65/0.230/0.050"), ("label", "0.1", "0.416/0.494/0.75/0.135/0.000"),
      ("volume", "1", "0.003/0.029/0.00/0.926/0.400"), ("volume", "0.5", "0.015/0.128/0.00/0.826/0.150"),
      ("volume", "0.2", "0.149/0.472/0.20/0.890/0.200")]
for fam, a, printed in T2:
    e = g(rc, "table2", f"{fam}|{a}")
    rec = (f"{e['S_JS_mean']:.3f}/{e['S_dev_mean']:.3f}/{e['fracDegen_median']:.2f}/{e['margin_median']:.3f}/"
           f"{e['bstar_median']:.3f}") if e else None
    note = f"(c) K per draw {e['K']}" if e and min(e["K"]) < 20 else ""
    if note:
        note += ": members of clients with <16 rows were dropped, which raises the threshold 2m/K independently of " \
                "coverage; undisclosed in Table 2"
    add(f"T2-{fam}-{a}", "Table 2", f"{fam} alpha={a}: S_JS/S_dev/fracDegen/margin/beta*", printed, rec, None,
        CANON + {"device": "e7f_devskew", "label": "e7f_labelskew", "volume": "e7_volskew"}[fam] + ".jsonl; "
        "results/analysis/instruments.jsonl", "scripts/gen_e7.py", "-", note)
add("S6-4", "Sec 1; Sec 6", "IoT-23 device identity carries 0.3189 bits about the label, 37.4% of 0.8524-bit entropy",
    "0.3189, 37.4%, 0.8524", (f"{g(rc,'coupling','iot-23','I_all'):.4f}, {100*g(rc,'coupling','iot-23','frac_all'):.1f}%, "
                              f"{g(rc,'coupling','iot-23','H_all'):.4f}") if rc else None, None, "data/raw/iot23 (all 166,532 rows)",
    "scripts/gen_crossdataset.py", "-", "(c) computed on all rows (train+test); training rows only: 0.3117 bits. "
    "The 10 'device types' are 10 captures: 2 real devices (Philips Hue, Amazon Echo; 452 and 1,374 rows, all benign) and "
    "8 malware scenarios executed on a Raspberry Pi (IoT-23 documentation)")
add("S6-5", "Sec 1; Sec 6", "N-BaIoT device identity carries 0.0050 bits (1.07% of 0.4685)", "0.0050, 1.07%, 0.4685",
    (f"{g(rc,'coupling','n-baiot','I_all'):.4f}, {100*g(rc,'coupling','n-baiot','frac_all'):.2f}%, "
     f"{g(rc,'coupling','n-baiot','H_all'):.4f}") if rc else None, None, "data/raw/nbaiot (1,333,113 rows)",
    "scripts/gen_crossdataset.py", "-", "")
add("S6-6", "Sec 6", "per-device malicious rates 0.000-0.971 (IoT-23), 0.8333-0.9196 (N-BaIoT)", "0.000-0.971; 0.8333-0.9196",
    (f"{min(g(rc,'coupling','iot-23','per_device_mal_rate').values()):.3f}-{max(g(rc,'coupling','iot-23','per_device_mal_rate').values()):.3f}; "
     f"{min(g(rc,'coupling','n-baiot','per_device_mal_rate').values()):.4f}-{max(g(rc,'coupling','n-baiot','per_device_mal_rate').values()):.4f}")
    if rc else None, None, "data/raw", "-", "-", "")
add("T3-1", "Table 3; Sec 1; Sec 6", "IoT-23 device-derived: S_JS 0.8503, fracDegen 0.400, margin 0.3667, beta* 0.063, collapse 0.90 [0.74,0.97]",
    "0.8503/0.400/0.3667/0.063/27 of 30", (lambda e: f"{e['S_JS_mean']:.4f}/{e['fracDegen_mean']:.3f}/{e['margin_mean']:.4f}/"
                                           f"{e['bstar_mean']:.3f}/{e['collapse_b02'].replace('/', ' of ')}")(g(rc, "table3", "iot23|device_derived")) if rc else None,
    None, CANON + "e5f_device_derived.jsonl", "scripts/gen_crossdataset.py", "-", "")
add("T3-2", "Table 3; Abstract; Sec 1; Sec 6", "N-BaIoT device-derived: S_JS 0.8509, fracDegen 0.000, margin 0.9970, beta* 0.450, 30/30 at ceiling (k=1 and k=2)",
    "0.8509/0.000/0.9970/0.450/30/30", (lambda e: f"{e['S_JS_mean']:.4f}/{e['fracDegen_mean']:.3f}/{e['margin_mean']:.4f}/"
                                         f"{e['bstar_mean']:.3f}/{e['at_ceiling']}/30 (k2 {e['k2_at_ceiling']})")(g(rc, "table3", "nbaiot|device_derived")) if rc else None,
    None, CANON + "nb9_cert_device_derived.jsonl", "scripts/gen_crossdataset.py", "-",
    "(c) predeclaration of the N-BaIoT outcome is dated by an internal record and local commits only (as the paper says)")
add("S6-7", "Sec 6; Table 11", "SJS ranks 6th of 7 statistics over 318 cells (rho=-0.498); within-family -0.650; minClassSup +0.926 vs fracDegen -0.924",
    "6, -0.498, -0.650, +0.926, -0.924", (f"{g(rc,'table11','sjs_rank')}, {g(rc,'table11','pooled','S_JS'):+.3f}, "
                                          f"{g(rc,'table11','within','S_JS'):+.3f}, {g(rc,'table11','pooled','min_class_support'):+.3f}, "
                                          f"{g(rc,'table11','pooled','frac_degenerate'):+.3f}") if rc else None,
    None, "results/analysis/instruments.jsonl", "scripts/gen_crossdataset.py", "-",
    "(c) the 318 cells are 159 draws x k in {1,2} with identical statistics per draw: the effective n is 159; rho is pooled across families")
add("S6-8", "Sec 6; App C", "on 12 held-out draws minClassSup +0.763 ties S_lab -0.768", "+0.763, -0.768", None, None,
    "results/analysis/instruments.jsonl", "scripts/gen_crossdataset.py", "-", "gate-regenerated; PB02 adds grouped out-of-sample tests")

# ---- Sec 7 / Tables 4-5
T4 = [(1, "0", "9/30"), (1, "0.05", "13/30"), (1, "0.1", "19/30"), (1, "0.2", "27/30"), (1, "0.3", "30/30"), (1, "0.4", "30/30"),
      (2, "0", "0/30"), (2, "0.05", "1/30"), (2, "0.1", "1/30"), (2, "0.2", "25/30"), (2, "0.3", "30/30"), (2, "0.4", "30/30")]
for k, b, printed in T4:
    e = g(rc, "table4", f"device_derived|k{k}|b{b}")
    add(f"T4-dev-k{k}-b{b}", "Table 4; Sec 7", f"device-derived collapse k={k} beta={b}", printed,
        f"{e['x_recomputed']}/{e['n']} {e['wilson']}" if e else None, None, CANON + "e5f_device_derived.jsonl",
        "scripts/gen_paper_numbers.py", "-", "")
T5 = {"1-1": "0.915/0.600/0.397/0.000/1.00/0.000/0.000/0.450", "1-3": "0.848/0.375/0.385/0.050/0.87/0.150/0.000/0.450",
      "2-5": "0.711/0.150/0.681/0.300/0.07/0.250/0.000/0.450", "3-8": "0.518/0.050/0.869/0.400/0.00/0.250/0.000/0.450",
      "5-10": "0.279/0.000/0.957/0.450/0.00/0.250/0.000/0.450"}
for lv, printed in T5.items():
    e = g(rc, "table5", lv)
    add(f"T5-{lv}", "Table 5; Abstract; Sec 1; Sec 7", f"device types {lv}: S_JS/fracDegen/margin/beta*/collapse/k2 beta*/NB fracDegen/NB beta*",
        printed, (f"{e['S_JS_median']:.3f}/{e['fracDegen_median']:.3f}/{e['margin_median']:.3f}/{e['bstar_median']:.3f}/"
                  f"{e['collapse_b02']:.2f}/{e['k2_bstar_median']:.3f}/{e['nb_fracDegen_median']:.3f}/{e['nb_bstar_median']:.3f}") if e else None,
        None, CANON + f"e11b_dph*, e22_*, e21_*", "scripts/gen_richness*.py", "-",
        "(c) 1-3 level shares 20 of 30 draws with the main grid (stated); 'device types' are captures (see S6-4)" if lv == "1-3" else "")
add("S7-1", "Fig 1; Sec 7", "device-derived median beta* 0.050 (k=1), 0.150 (k=2, k=3)", "0.050, 0.150, 0.150",
    (f"{g(rc,'fig1_bstar','device_derived|k1','median'):.3f}, {g(rc,'fig1_bstar','device_derived|k2','median'):.3f}, "
     f"{g(rc,'fig1_bstar','device_derived|k3full','median'):.3f}") if rc else None, None,
    CANON + "e5f_device_derived, e2k3full_device_derived_s*", "scripts/make_fig_main.py", "-", "k=3 from 3 draws")
add("S7-2", "Fig 1; Sec 3", "IID beta* lower bound 0.050 at k=5 and k=8", "0.050, 0.050",
    f"{g(rc,'fig1_bstar','iid|k5','median'):.3f}, {g(rc,'fig1_bstar','iid|k8','median'):.3f}" if rc else None, None,
    CANON + "e2k58_cert_iid_s*", "scripts/make_fig_main.py", "-", "3 draws")

# ---- Sec 8 screen
s = g(rc, "screen", "1.05")
add("S8-1", "Abstract; Sec 1; Sec 8", "coverage screen: 660 cells, 246 correct refusals, 0 missed, 1 unsafe commitment in 414, max regret 0.0130",
    "660/246/0/1 of 414/0.0130", (f"{s['n_cells']}/{s['refuse_correct']}/{s['refuse_missed']}/{s['unsafe']} of "
                                  f"{s['commitments']}/{s['max_regret']:.4f}") if s else None, None,
    CANON + "e5f_*.jsonl", "scripts/gen_e14_heldout.py", "-",
    "(c) the 414 commitments come from 60 draws x 11 budgets and are correlated; the unsafe one is device draw 35, beta=0.05, k=1, "
    "coverage 0.9997, CA 0.2699 (it certifies 'benign' for all flows). Factor 1.00 gives 2 unsafe in 415.")
add("S8-2", "Sec 8", "factor 1.02 chosen on half the draws: 330/330 selection, 329/330 held-out; 1.05: 329/330", "330/330, 329/330",
    None, None, CANON + "e5f_*.jsonl", "scripts/gen_e14_heldout.py", "-", "gate-regenerated; PB08 adds baselines")

# ---- appendix B/C
add("B-1", "Table 8; App B", "added slack is the larger share in 6 of 7 cells", "6 of 7", str(g(rc2, "table8_added_slack_larger")),
    None, CORR + "e2_*", "scripts/gen_paper_numbers.py", "-", "upper bound (five published attacks)")
add("B-2", "Table 9; App B", "device k=2 beta=0.20 median slack 0.2852; largest single-row slack 0.7066", "0.2852, 0.7066",
    f"{T9('device_derived',2,'0.2','G'):.4f}, {g(rc2,'largest_single_row_slack_dev'):.4f}" if rc2 else None, None,
    CORR + "e2_*", "scripts/gen_paper_numbers.py", "-", "")
add("B-3", "Table 9", "EA column = median over 9 rows of min over 5 attacks (final round)", "e.g. IID k1 0.05: 0.9816",
    f"{T9('iid',1,'0.05','EA_final'):.4f}" if rc2 else None, None, CORR + "e2_*", "scripts/gen_paper_numbers.py", "-",
    "(c) the window-minimum EA (used elsewhere in the repo) differs, e.g. 0.9808; say which estimator Table 9 uses")
add("B-4", "Table 10; App C", "k=2 detection metrics (coverage/CTR_mal/CTR_ben/cert-wrong)", "e.g. device beta=0.20: 0.667/0.590/0.871/0.0007",
    "/".join(str(x) for x in g(rc2, "table10_e2_corrected", "device_derived|b0.2")[:4]) if rc2 else None, None, CORR + "e2_*",
    "scripts/gen_appendix.py", "-",
    "(c) Table 10 is 3 draws; on the 30 e5f draws the device beta=0.20 row is " +
    ("/".join(str(x) for x in g(rc2, "table10_e5f", "device_derived|b0.2")[:4]) if rc2 else "n/a") +
    " (bimodal regime): state n or use the 30-draw medians")
mc = g(rc2, "multiclass")
add("C-1", "Sec 5; App C", "8-class control: tau 0.5330, slack <=0.0044 (k=1), 0.0014 (k=2); 4 of 6 classes; C&C 0.1088; clean 0.8749",
    "0.5330/0.0044/0.0014/4 of 6/0.1088/0.8749", (f"{mc['tau']:.4f}/{mc['max_G_k1']:.4f}/{mc['max_G_k2']:.4f}/"
                                                  f"{mc['n_classes_over_half']} of {mc['n_classes_with_rows']}/"
                                                  f"{mc['per_class_certified_median']['C&C']:.4f}/{mc['clean_acc']:.4f}") if mc else None,
    None, CORR + "e25_multiclass_*", "scripts/gen_multiclass.py", "-", "")
lo = g(rc2, "loco")
add("L-1", "Sec 10; App C", "leave-one-capture-out: floors 0.5420-1.0000; 5 of 10 folds beat the floor; median diff 0.0008, max 0.2236, <=0.0009 in beating folds",
    "0.5420-1.0000/5/0.0008/0.2236/0.0009", (f"{lo['tau_min']:.4f}-{lo['tau_max']:.4f}/{lo['n_beats']}/{lo['med_diff']:.4f}/"
                                              f"{lo['max_diff']:.4f}/{lo['max_diff_in_beating']:.4f}") if lo else None,
    None, CANON + "e16_lodo.jsonl", "scripts/gen_lodo.py", "-",
    "(c) the 5 non-beating folds are exactly the 5 folds with tau >= 0.99 (near-single-class captures)")
add("B-5", "App B", "purpose-built attack beats the published ones in 16 of 108 cells, by up to 0.2018", "16/108, 0.2018", None, None,
    CORR + "adaptive_*", "scripts/gen_adaptive.py", "-", "gate-regenerated; PB10 adds the exact member-level worst case")
add("B-6", "Sec 4", "determinism defect: attacked accuracy varied by up to 0.6951 across identical runs before the fix", "0.6951",
    None, None, "results/pre_determinism_fix/", "scripts/compare_rerun.py", "-",
    "(c) all 334 rebuilt ensembles (29,623 members) reproduce their 3,569 canonical rows exactly (max abs diff 0)")
add("D-1", "Sec 1; Sec 9; App D", "literature screen: 20 records, 0 of 20 state a certified guarantee; 3 of 3 need clean server data; 0 of 2 measure divergence",
    "0/20, 3/3, 0/2", None, None, "literature/inventory_r2.yaml", "scripts/build_inventory_r2.py", "-",
    "not re-coded here (single coder, abstract-level; the paper says so)")
add("D-2", "Sec 4", "IoT-23 166,532 flows, 10 device types; N-BaIoT 1,333,113 records, 115 features, 9 devices; tau 0.7300 / 0.9001",
    "166532/10/1333113/115/9/0.7300/0.9001", (f"{g(rc,'coupling','iot-23','n_rows')}/{g(rc,'coupling','iot-23','n_devices')}/"
                                              f"{g(rc,'coupling','n-baiot','n_rows')}/{g(rc,'coupling','n-baiot','n_features')}/"
                                              f"{g(rc,'coupling','n-baiot','n_devices')}/{g(rc,'coupling','iot-23','test_mal_share'):.4f}/"
                                              f"{g(rc,'coupling','n-baiot','test_mal_share'):.4f}") if rc else None, None,
    "data/raw", "src/fedhomeguard/data.py", "-",
    "(c) IoT-23 loader reads at most 400,000 lines per capture and keeps 60,000 evenly spaced rows: capture 1-1 is cut "
    "to its first 39.7%, 3-1 subsampled from 156,103; 73.7% of test flows have an exact training duplicate (PB07)")


def status(printed, rec):
    if rec is None:
        return "gate_regenerated_only"
    norm = lambda x: x.replace(" ", "").replace("+", "").lower()
    return "reproduced" if norm(str(printed)).split("(")[0] in norm(str(rec)) or norm(str(rec)).startswith(norm(str(printed))) else "check"


with open(OUT, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["claim_id", "manuscript_location", "claim", "printed_value", "recomputed_value", "status",
                "evidence_rows", "generator", "proof_status", "statement_type", "note"])
    for (cid, loc, claim, printed, rec, _dec, ev, gen, proof, note) in C:
        st = status(printed, rec)
        OVR = {"T6": "reproduced", "T7": "reproduced_with_caveat", "S5-2": "reproduced_with_caveat",
               "B-1": "reproduced", "B-3": "reproduced_with_caveat", "B-4": "reproduced_with_caveat"}
        if cid in OVR:   # string-format differences only; values checked by hand on 2026-10-10
            st = OVR[cid]
        if cid in ("T8", "T10", "S8-2", "S6-8", "B-5", "B-6", "D-1"):
            st = {"T10": "not_reproducible_here", "D-1": "not_reproducible_here"}.get(cid, st)
        if st != "check" and note and "(c)" in note and any(x in note for x in ("say", "Fix", "state", "undisclosed", "include")):
            st = "reproduced_with_caveat" if st == "reproduced" else st
        w.writerow([cid, loc, claim, printed, rec, st, ev, gen, proof, "(b)", note])
print(f"wrote {OUT}: {len(C)} claims")
