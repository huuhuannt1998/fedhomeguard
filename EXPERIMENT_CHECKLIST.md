# FedHomeGuard — Experiment Checklist

Verified against artifacts in `results/`, not from memory. Last updated 2026-08-21.

> **2026-08-22:** gap-fill round complete. A4, A5, A8 and the L2/L3 defenses all ran.
> Findings in `jrn_01M0M1Y2DET9B8JTG0RM4MF4S3`. Two results require manuscript edits
> (see "Manuscript corrections owed" at the bottom).

Legend: **[x]** done · **[~]** partial · **[ ]** not run

---

## A. Staged evaluation pathway (design §11.1)

- [x] **Stage 0 — Substrate.** Device-derived partition on IoT-23, N=20.
      Measured S_JS=0.8445, S_dev=0.8823, 0 starved clients. → `stage0_*.json`
- [x] **Stage 1 — Baseline competence.** FedAvg 0.9805 vs τ_triv=0.7300; passes the
      predeclared "within 5 points of centralized" exit. → `stage1_*.json`
- [x] **Stage 2 — Empirical robustness.** 5 defenses × 5 attacks × 6 β × 2 partitions
      × 3 seeds = 520+ records. → `stage2_main/iid/seeds.json`
- [x] **Stage 3 — Certification (GATE G1).** k ∈ {1,2,3,5,8} × 3 seeds × 2 partitions.
      → `ksweep_seeds.json`, `stage3_*.json`
- [x] **Stage 4 — Gap.** Both partitions, seed-matched. → `gap_seedmatched.json`
- [x] **Stage 5 — Skew sweep + necessity + LODO.** 23 arms incl. 10 leave-one-device-out.
      → `stage5_main.json`, `necessity*.json`
- [x] **Stage 6 — Systematization overlay.** `β*(S)` measured at **22 skew levels**
      (best k per level, fine β grid, exact enumeration at k≤2), `R_lit` reconstructed
      with provenance in `results/r_lit.json`, `R_lit \ R_hon` rendered as
      `fig_region.pdf` and wired into §9. **Result: β\* holds at the ceiling 0.450 up to
      S_JS≈0.39, then steps down to 0.325–0.350, 0.225–0.250, and 0.050–0.150 at real
      device skew 0.845.** The certifiable region *contains* the whole literature band
      below S_JS≈0.41 and separates from it above.

## B. Predeclared ablations (design §11.5)

- [x] **A1 — matched-skew Dirichlet.** Alg 4 confirmatory: k∈{1,2,3} × 3 seeds,
      device vs matched control vs IID. Result: inconclusive, 99% CI [−0.412,+0.440].
- [x] **A2 — leave-one-device-out.** 10 arms; no single device >50% of effect.
- [x] **A3 — k sweep.** k ∈ {1,2,3,5,8}. (Design listed {3,4,5,6,8}; I ran small-k
      instead because that is where the ceiling is generous — deviation, not omission.)
- [x] **A4 — K sweep incl. exact enumeration.** **66 of 72 arms fully enumerated** — those
      carry no Clopper–Pearson penalty at all. Only N=20,k=3 (C=1140) stayed sampled. Exact used **only at k=1** (C(20,1)=20);
      k∈{2,3,5,8} all sampled at K=100. Design says exact is *cheaper and stronger*
      (no Clopper–Pearson penalty), so current numbers are needlessly conservative.
- [x] **A5 — N sweep {10,12,16,20}.** β\* flat in N at fixed k, as the closed form predicts.
      C2's N-independence claim now rests on four N values, not one.
- [x] **A5b — β-grid decensoring** (added; not in the original design). The coarse grid
      right-censored β\* at its 0.40 maximum. Re-run to 0.500 in steps of 0.025 with exact
      enumeration at k≤2: **IID β\* = β_geo exactly in 9/9 arms** (0.450/0.250/0.150);
      device-derived reaches it in **2/9**, max **0.225**. Departure is at **k≤2**, not k≤3. **Only N=20 was ever run.** This underwrites C2's
      N-independence claim, currently supported by arithmetic + a single N.
- [ ] **A6 — model capacity** {MLP small, MLP large, autoencoder}. Only MLP[32,16].
- [~] **A7 — binary vs multi-class 𝒴.** Balanced-test variant exists in the M1 probe
      only; the multi-class τ_triv shift was never run.
- [x] **A8 — budget: equal-total vs equal-per-model.** **PASSES.** 25× budget (T=15→375,
      matching the certified arm's 7,500 client-rounds) moves EA_min by **+0.0012** at
      β=0.20 and +0.0105 at β=0.30, against a gap of 0.2959. The gap is not a budget artifact. **Never run.** This is design
      §C3's own anti-triviality guard ("is the effect merely budget?").
- [ ] **A9 — F4 on/off (adversary knows subsample seed).** Never run. Quantifies how
      much of the certificate rests on seed privacy.

## C. Certification families (design §5)

- [x] **Algorithm 2 — subsample certification (FLCert-style).** Fully exercised.
- [ ] **Algorithm 3 — smoothing certification (CRFL-style).** **Never run.** Disclosed
      in Limitations; C2 is scoped to the subsampling family. Open question: does the
      ceiling β_cert < 1−2^(−1/k) even apply to smoothing? Currently unknown.

## D. Defense suite / observability lattice (design §11.2)

- [x] L0 FedAvg · L1 Krum, trimmed-mean, median, norm-clip
- [x] **multi-Krum** (L1) — 0.9793 @ β=0.10, 0.7982 @ β=0.20 vs Krum's 0.8877 / 0.2698.
      **Qualifies the Krum finding**: the failure is single-selection Krum, not the family.
- [~] **FLTrust (L2)** — RUNNING. Smoke-tested OK (acc 0.7927 at beta=0.10/IPM). **This is the paper's own thesis:**
      §3 argues L2 defenses buy accuracy with knowledge deployments lack, and
      Scenario 3 in the design quantifies it. Currently argued, not measured.
- [~] **oracle_trimmed (L3)** — RUNNING. Smoke-tested OK (acc 0.9778 at beta=0.10/IPM). Was to be the printed ceiling.
- [x] **f_triv (τ_triv floor)** — the mandatory hardest baseline, applied throughout.

## E. Attack suite (design §11.1 Stage 2)

- [x] label_flip · sign_flip · gaussian · IPM · ALIE
- [ ] **backdoor / trigger** — implemented in `attacks.py`, never run. Needed if
      Algorithm 3 is ever run, since smoothing certifies the backdoor threat class.

## F. Statistical requirements (design §11.4)

- [x] Paired comparisons on matched seeds (necessity test)
- [x] Bootstrap CI + sign test + Wilcoxon on the necessity contrast
- [x] Time-ordered splits within device (never random row shuffle)
- [x] Exact arms reported without intervals; sampled arms via Clopper–Pearson
- [~] **R = 10 seeds.** Design raised this from 3 to 10 for any reported small-k number
      after bimodality was found. **Everything currently uses 3.**

## G. Datasets (D1, as narrowed by chk_01M0EH65WGYNBDK9H4MWQQT2JA)

- [x] **IoT-23** — attribution verified; carried every experiment.
- [~] **N-BaIoT** — benign traffic for all 9 devices obtained; **attack partitions never
      retrieved** (UCI endpoint truncates). No experiment uses it.
- [x] **CICIoT2023** — audited and correctly demoted to attack-class coverage only.
      Confirmed unusable for device partitioning.

---

## Priority for closing the gaps

**High — these are load-bearing for claims already in the manuscript:**
1. **A5 (N sweep)** — C2 claims N-independence; one N is thin evidence. Cheap.
2. **A8 (matched budget)** — the design's designated anti-triviality guard, and the
   first thing a reviewer will ask. Cheap; largely reuses existing runs.
3. **FLTrust at L2** — §3's central argument about deployment assumptions is currently
   asserted rather than measured.
4. **A4 (exact enumeration)** — strengthens existing numbers rather than merely checking
   them; removes an unnecessary statistical penalty. Cheap.

**Medium — completes the design as written:**
5. ~~Stage 6 overlay~~ — **done**.
6. ~~oracle_trimmed L3 ceiling + multi-Krum~~ — **done**.

**Lower — scope decisions rather than omissions:**
7. A6, A7, A9 — legitimate to document as not-run.
8. Algorithm 3 (smoothing) — a second paper's worth of work; already disclosed.
9. N-BaIoT attack data — needs Kaggle credentials or a manual download.


---

## Manuscript corrections owed (from the 2026-08-22 gap-fill)

1. **β\* = 0.40 is right-censored, not observed.** 0.40 is the grid maximum while
   β_geo(k=1)→0.5. Every "IID reaches 0.40" must become "β\* ≥ 0.40", or the β grid
   must be extended past 0.40. **This affects text already in §7 and the abstract.**
2. **Qualify the Krum claim** in §6 — multi-Krum does not collapse the same way.
3. **§3's L2 argument needs narrowing** — L2 buys robustness where L1 rules collapse
   (β ≥ 0.30), not uniformly; at β=0.20 FLTrust underperforms norm-clipping.
4. **Add the L3 oracle ceiling** — it is the cleanest statement of the real problem
   (identification), and it was in the design as Scenario 3 but never measured.
5. **Note the degenerate-defense case**: FLTrust at β=0.40 scores exactly τ_triv=0.7300,
   i.e. it has become the majority-class predictor while still "scoring 0.73".

**All five applied 2026-08-22.** Ratified claims C1–C4 were superseded through
`supersede_decision` and re-ratified at v2; the outline checkpoint was rebuilt after
RKA's staleness cascade auto-superseded it; provenance markers were repointed to the
current decision heads. Readiness PASS, 8pp/13, 0 undefined, provenance 0 blocks,
AI-tic 13/13, texlint 0, layout 12/12 (one underfull-hbox WARN).

### Caught while applying them
- **§7 overclaim, self-inflicted.** My first correction said IID "equals the ceiling at
  every subsample size". False at k=5: the IID margin is 0.8638 against a required
  0.8947, missing by 0.031. Scoped to k≤3 and the near-miss is now explained in text.
- **A `\cite` inserted inside a number** — `$0~\cite{krum2017}.2698$`. LaTeX rendered it
  silently. Found by reading, not by any gate. All 12 citation sites audited; one other
  had wrong *placement* (defense cites landed on the oracle sentence).
