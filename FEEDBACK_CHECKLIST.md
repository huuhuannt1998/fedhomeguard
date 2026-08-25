# Feedback compliance checklist

Source: `manuscripts/feedback/FedHomeGuard_SandP2027_Comprehensive_Review_and_Revision_Plan.md`
Numbering follows the review's own sections. Last verified: 2026-08-25.

Legend: **[x]** done and verified · **[~]** in progress · **[ ]** not started ·
**[–]** deliberately not doing, with the reason stated.

---

## The critical gate (review §50 step 4)

- [x] **Same-predictor experiment reproduces the IID-vs-skew relationship.** Slack
  ≤ 0.0037 IID, up to 0.22 median under device skew. The relationship survives; the
  *mechanism* changed twice under measurement and the paper follows the data both
  times (see §12 and §14 below).

---

## P0 — mandatory

- [x] **§3.1 Gap compared different predictors.** `src/fedhomeguard/ensemble.py`
  builds the attacked version of the *same* ensemble; only members whose subset meets
  `B` are retrained. `G_cert` is defined on one predictor.
- [x] **§4 Finite-attack inequality was reversed.** §IV-F now states
  `CA ≤ R_true ≤ EA_finite`, so measured slack is an **upper** bound and a stronger
  attack tightens it. Limitations updated to match.
- [x] **§5 Internal numerical contradiction.** One canonical schema
  (`results/canonical/*.jsonl`); `scripts/aggregate.py` + `gen_paper_numbers.py`
  generate every number, macro, table and figure and **refuse to emit** unless 9
  assertions pass. Prose reaches values through `\csname`-indexed macros, so a number
  cannot drift between abstract and conclusion.
- [x] **§6 Probabilistic certificate unspecified.** Obviated rather than formalised:
  Proposition 1 certifies the *realised* ensemble exactly. No confidence interval
  anywhere in the paper. `scripts/exp_e1_validate.py` validates by brute force over
  every malicious set (1181 certified points, 0 violations).
- [x] **§7 Enumerate k=2 exactly.** k=1 (K=20) and k=2 (K=190) are full enumerations,
  so realised and population certificates coincide there.
- [x] **§8 Malicious-set identity as a factor.** 3 random sets per cell plus
  high-influence sets by data volume and by rare-device coverage
  (`e4_highinf_*.jsonl`, 60 rows). Variance decomposed in §VIII-C.
- [x] **§9 Three seeds insufficient.** 60 independent partition draws at k=1,2
  (`e5_*.jsonl`). Main k=3 grid remains at 3 draws, stated in Limitations.
- [x] **§10 Bimodality as a statistical result.** Predeclared criterion
  `CA ≤ τ_triv`; counts, proportions, Wilson intervals and both cluster medians.
- [x] **§11 Accuracy alone insufficient.** Every canonical row carries `TPR`, `FNR`,
  `FPR`, `precision`, `balanced_acc`, `macro_F1`, `coverage`, `CTR_mal`, `CTR_ben`.
- [x] **§24 Literature audit.** Protocol, inclusion/exclusion criteria and two
  predeclared coding rules in `literature/`. **Resolved by scope change**: the
  systematisation was removed from the contribution list, so no result depends on the
  n=3 sample. See "Known limits" below.
- [x] **§25 Distinguish types of theory.** Four-shape taxonomy (convergence /
  privacy / Byzantine-statistical / certified-prediction) in §III.
- [x] **§26 Frame the ceiling as a corollary.** §IV says plainly that Eq. (1) follows
  in two lines from `cao2021provably`, and locates the contribution in the consequence.
- [x] **§27 Formal theorem presentation.** Proposition 1 (realised-ensemble
  certificate, with proof), Proposition 2 (geometric impossibility), Corollary 1
  (large-N). Strict-vs-non-strict inequalities stated explicitly.
- [x] **§28 Clarify certified accuracy.** `CA`, `Cov`, `CertWrong` defined separately
  with `CA = Cov − CertWrong`.
- [x] **§29 Certification failure decomposition.** Four exhaustive classes, asserted
  to sum to 1, shown as a stacked figure.
- [x] **§30 Realism language.** "synthetic household construction over real per-device
  captures" throughout; a Limitations paragraph states the ownership model is ours.
- [x] **§31 L2 framing.** §IX no longer claims a household federation cannot have
  clean server data; it makes the narrower representativeness/drift claim.
- [x] **§32 Label best-defence as an oracle envelope.** Named
  `EA_oracle-defence` / "best-in-hindsight envelope" wherever it appears.
- [x] **§33 Three gaps.** `G_cert`, `G_method`, `G_useful` defined in §IV-D, never added.
- [x] **§37 Title.** *The Limits of Client-Count Certification for Federated IoT
  Intrusion Detection.*
- [x] **§38–41 Claim rewrites.** Core claim, heterogeneity claim, literature claim and
  the §XI section name all rewritten to the review's suggested forms.
- [x] **§42 Keep and expand limitations.** 9 paragraphs, updated as results landed.
- [x] **§43 Clean the bibliography.** Three internal artifacts removed
  ("existence confirmed via OpenAlex", a PI override ID, "Validation status
  VERIFIED"); shortDOI `url` fields dropped; four entries corrected from arXiv
  preprint DOIs to their real ICML/UAI venues.

---

## P1 — strongly recommended

- [x] **§12 Separate components of heterogeneity (E7).** All three experiments done.
  **A vs B:** at matched skew the device family holds **+0.131** more vote margin
  (95% CI [0.044, 0.235], Cohen's d_z 0.65, Wilcoxon p 0.0025, 16 full-enumeration
  pairs). The paper's device-diversity mechanism was retracted; device identity
  predicts the label in IoT-23 (I = 0.319 bits, 37% of label entropy), so device
  assignment *induces* label skew.
  **C (data-volume):** costs β\* 0.450 → 0.300 at S_JS = **0.008** — essentially zero
  measured skew. **S_JS is therefore not a sufficient statistic for certifiability**,
  which is a limitation of an instrument this paper introduces and must be stated as
  one. Damage per unit of measured skew ranks volume ≫ label ≫ device-support. **This changed a claim.** At matched skew, label skew costs ~10× more
  vote margin than device-support skew. The paper's device-diversity mechanism was
  **retracted**; the corrected mechanism is that device identity predicts the label in
  IoT-23 (I = 0.319 bits, 37% of label entropy), so device assignment *induces* label
  skew. Experiment C (data-volume skew) not run — see "Remaining".
- [x] **§13 Frontier with uncertainty (E8).** `fig_frontier.pdf` rebuilt from 108
  partition draws per subsample size pooled over four partition families; per-draw
  markers, binned median, no phase boundary drawn.
- [x] **§14 Deployable k-selection rule.** **This changed a claim.** The mean-margin
  rule I first wrote was measured and found unsafe (2 selections below the floor) and
  its stated behaviour was wrong. Replaced with a label-free *coverage* screen, which
  soundly bounds CA. Measured over 36 cells: 0 unsafe selections, 0 missed
  opportunities, 9 correct refusals, mean regret 0.003, max 0.069.
- [x] **§15 Expand Table I across partitions and attacker sets (E12).** Rebuilt over
  3 draws × 3 attacker sets with full observed ranges.
- [x] **§16 Second lightweight model (E9).** Logistic regression. Mechanism
  replicates; **magnitude does not**, and the paper now says so: the 64-parameter
  model holds a 0.838 device margin against the perceptron's 0.446.
- [x] **§17 Federation-size sensitivity (E10).** N ∈ {10, 20, 50}, reported in
  Appendix A.1. Enlarging the federation does not rescue competence under skew and
  mildly hurts it: margin 0.372 (N=10), 0.446 (N=20), 0.314 (N=50).
- [x] **§18 Household device-count sensitivity (E11).** 1, 1–3 and 2–5 devices per
  household, reported in Appendix A.2. **This is the sharpest confirmation of the
  corrected mechanism**: richer households raise the margin from 0.408 to 0.853 and
  β\* from 0.000 to 0.400, while S_JS *falls* — the mechanism operating in the
  direction the ablation predicts. It is also the one actionable lever the paper can
  offer a deployer.
- [x] **§19 Certification overhead (E14).** k=1 costs 1.0× FedAvg, k=2 19×, exact k=3
  171×; wall-clock and stored parameters reported.
- [x] **§20 Attack-strength sensitivity (E13).** λ ∈ {0.5, 1, 5}, reported in
  Appendix A.3. The answer to the review's question is yes, strongly, for one rule:
  norm clipping falls from 0.955 at λ=0.5 to 0.270 (the minority-class rate) at λ=5
  under both partitions, while multi-Krum and median are nearly flat. This cuts in the
  paper's conservative direction — a stronger attack lowers EA and *tightens* reported
  slack.

---

## P2 — optional

- [–] **§21 Defense-aware adaptive attack (E16).** Not run. The certificate is a
  counting argument that never reads update values, so no adaptive attack can move
  `CA`; adaptivity only lowers `EA_finite`, which *tightens* our reported slack. The
  paper makes that argument explicitly rather than leaving it as future work.
- [–] **§22 FLTrust root-set quality (E15).** Not run. L2 is no longer a contribution
  and no result depends on it.
- [–] **§23 Second dataset (E17).** Not run. The review says not to add a
  semantically inappropriate dataset for its own sake; CICIoT2023 cannot supply
  per-device attribution and N-BaIoT could not be retrieved intact, both documented.

---

## Experiment set (review §35)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| E1 | Certification implementation validation — MANDATORY | **[x]** | `e1_validation.json`, 4/4 PASS |
| E2 | Same-predictor gap — MANDATORY | **[x]** | 288 rows, k ∈ {1,2,3} × 2 partitions × 3 draws × 3 attacker sets |
| E3 | Empirical-defence vs certifiable-method gap — MANDATORY | **[x]** | 3,648 rows, 8 defences × 6 attacks |
| E4 | Malicious-set sensitivity — MANDATORY | **[x]** | 3 random + 2 high-influence modes |
| E5 | Small-k replication / collapse probability — MANDATORY | **[x]** | 60 draws, Wilson intervals |
| E6 | Certified IDS metrics — MANDATORY | **[x]** | 9 class-conditional metrics per row |
| E7 | Device- vs label-skew ablation — MANDATORY FOR STRONG | **[x]** | 504 rows; retracted a claim |
| E8 | Frontier with uncertainty — STRONGLY RECOMMENDED | **[x]** | 108 draws per k |
| E9 | Second lightweight classifier — STRONGLY RECOMMENDED | **[x]** | logistic regression |
| E10 | Federation-size sensitivity — RECOMMENDED | **[x]** | N ∈ {10,20,50} |
| E11 | Household device-count — RECOMMENDED | **[x]** | 3 richness settings |
| E12 | Observability sensitivity — RECOMMENDED | **[x]** | across draws and attacker sets |
| E13 | Attack-strength sweep — RECOMMENDED | **[x]** | λ ∈ {0.5,1,5} |
| E14 | Runtime and resource overhead — RECOMMENDED | **[x]** | client-rounds, wall-clock, storage |
| E15 | L2 reference-data quality — OPTIONAL | **[–]** | not a contribution |
| E16 | Adaptive attack — OPTIONAL | **[–]** | argued, not needed |
| E17 | Second dataset — OPTIONAL | **[–]** | no valid candidate |

---

## Presentation (review §44–47)

- [x] **§45 New paper structure.** Sections reordered exactly as specified, plus an
  appendix carrying the sensitivity analyses and the observability measurement, which
  IEEE S&P excludes from the page limit.
- [x] **§46 Figures.** fig_main (same-predictor), fig_pincer (both constraints in
  vote-margin units), fig_decomp (failure decomposition), fig_frontier (β* vs skew
  with uncertainty). Analytic-ceiling figure is a table instead (Table II) — it has
  six values and reads better as one.
- [x] **§47 Statistical reporting.** Medians with full observed ranges; Wilson
  intervals for collapse; measured points never interpolated. Paired effect size and
  bootstrap CI now reported for the device-vs-label comparison
  (`scripts/gen_e7_stats.py`): +0.2521 margin at matched skew, 95% CI
  [0.134, 0.380], Cohen's d_z = 0.84, Wilcoxon p = 2.3e-4 over 21 pairs.
- [x] **§48 Reproducibility.** `Makefile` (`make data|test|experiments|paper|verify`),
  `environment.yml`, `scripts/manifest.py` (SHA-256 over raw data and every canonical
  result file, 48 entries), and `scripts/verify_paper_claims.py`, which fails the
  build on any hand-typed numeric literal in the abstract, introduction or conclusion
  that is not generated or a declared constant. Currently **0 unverified literals**.

---

## Remaining work

| # | Item | Why it matters | Effort |
|---|---|---|---|
| ~~R1~~ | ~~β grid right-censors β\* at 0.40~~ | | **done** — decensored to 0.05 steps through 0.50. IID now hits β_geo **exactly on 30/30 draws** at both k, confirming the plateau was a grid artifact. Device-derived: β\* 0.067 (k=1) → **0.152 (k=2)** — under skew, going k=1→2 *helps*, because margin recovery beats the ceiling drop 0.450→0.250. The pincer, quantified. |
| ~~R2~~ | ~~Paired effect size + CI for device-vs-label skew (§47)~~ | | **done** |
| ~~R3~~ | ~~Reproducibility package (§48)~~ | | **done** |
| ~~R4~~ | ~~Experiment C, data-volume skew~~ | | **done** — 330 rows; result above. Draws that lost starved members (22 at α=0.5, 33 at α=0.2) excluded and disclosed. |
| ~~R11~~ | ~~Second dataset (N-BaIoT)~~ | | **done, and it became a natural experiment.** 5 of 9 devices recovered intact. In N-BaIoT device identity carries almost no label information (I = 0.0042 bits, 0.9% of label entropy) against IoT-23's 0.319 bits (37.4%), so it directly tests the corrected mechanism. Prediction predeclared before running; **P2/P3/P4 confirmed, P1 weakly supported at best** (my reasoning there was wrong — S_JS is a *joint* device×label divergence, so it stays high regardless of label coupling). **ALL NINE DEVICES NOW RECOVERED** (UCI's legacy per-file tree serves each 50–190 MB archive individually; all six missing ones downloaded first try in 26 s — the 2 GB bundle was never the right endpoint). Full dataset: 1,333,113 rows, I(label;device) = **0.0050 bits, 1.07%** of a 0.4685-bit label entropy, per-device malicious rate spanning only 0.833–0.920. **Nine-device certified arm COMPLETE and it tightened the contrast**: completing the dataset raised device-derived S_JS from 0.732 to **0.8550**, within **0.005** of IoT-23's 0.8503 — yet β\* stays at the ceiling on **5/5 draws at both k** (margin 0.9968) against IoT-23's β\* 0.050 and margin 0.4456. Adding skew as S_JS measures it cost nothing. Five-device arm retained as a subsample check: **5 device-derived + 5 IID draws, both k, both fully enumerated.** β\* equals β_geo **exactly on 20 of 20 draws** — zero variance. Device-derived on N-BaIoT: S_JS 0.732, margin 0.998, collapse 0.00 — against IoT-23's 0.845 / 0.446 / β\* 0.050 / collapse 0.84. Same construction, comparable skew, opposite outcome. |
| ~~R13a~~ | ~~Audit S_JS as an instrument~~ | | **done** — `scripts/gen_instruments.py`, 109 partition draws rebuilt through the runner path, joined to measured β\*, 218 cells. Four new partition-side instruments added to `measure_skew` (S_lab, min_minority, frac_degenerate, min_size_share) so all future runs record them. Artifact: `results/canonical/instruments.jsonl`. |
| ~~R13~~ | ~~S_JS fails as a cross-family predictor~~ | | **done.** §VII gained two subsections — the N-BaIoT natural experiment (Table IX, matched contrast) and the seven-instrument audit (Table X) — placed after the mechanism subsection they confirm, before the frontier. §XI gained an *On our own instrument* paragraph and its skew-statistic recommendation now says label-side, correcting our own advice. **fig_frontier now carries both counterexamples** (open diamonds at S_JS≈0, open triangles at S_JS≈0.855 sitting at the ceiling), so β\* visibly fails to be a function of S_JS in both directions. All numbers via `gen_crossdataset.py`, wired into `make numbers` and the chain. Provenance 0 BLOCK, texlint 0, 0 `??` markers. |
| ~~R15~~ | ~~Nothing predicts within `iot23 device_derived`~~ | | **resolved — and my earlier "nothing predicts" was my own grouping error.** Pooling k=1 and k=2 drove ρ→0 because β\*/β_geo still has different ranges per k (0.000–0.556 vs 0.200–0.800) while the instruments are k-independent. Grouped correctly by (family, k), **`min_class_support`** gives **+0.817 (k=1)** and **+0.637 (k=2)** vs S_JS's −0.699/−0.605, and **+0.763 out-of-sample at k=3** (12 held-out draws, pseed 40–51, never used in derivation) vs S_JS's −0.461. Wins 4 of 8 cells overall and **both** device_derived cells. Caveats kept: q is a fitted parameter (sweep printed, not just the peak), and out-of-sample it ties S_lab (−0.768) at n=12 — the defensible claim is *label-side instruments beat device-side ones within a family*, not that this exact form is right. |
| ~~R14~~ | N-BaIoT substrate bug | No timestamps, so the time-ordered split gave a 100% malicious test set and CA 0.769 below a 0.90 floor | **done** — splitter blocks on device × traffic type; IoT-23 verified bit-identical |
| ~~R12~~ | ~~Full enumeration at k=3~~ | | **done, and it produced a methodological result.** Full C(20,3)=1140 vs the realised K=500 sample, matched on seed: sampling **understates β\* by a full grid step in 2 of 3 device-derived draws, 0 of 3 IID draws**. Every delta ≥ 0 — the bias is **conservative, not unsound**. Mechanism visible in the margins: IID member spread 0.0012 (which 44% you draw is irrelevant), device-derived spread 0.215. **Consequence: the k=5,8 cells sample 1.3% and 0.16% and must be reported as lower bounds, not estimates.** |
| ~~R10~~ | ~~k=3 uses only 3 partition draws~~ | | **done** — 12 replication draws added (pseed 40–51), so k=3 now has 18 draws total, and 3 of them are full enumerations. Doubled as the held-out set for the R15 instrument test. |
| ~~R9~~ | ~~§V claimed `k ∈ {5,8}` configurations with no data~~ | | **done** — the claim is now backed. Result confirms E1/V4 on real data: at K=200 the *realised* ensemble certifies only to β=0.05 at both k, where the population certificate would allow 0.100 at k=5. Sampling costs a grid step of certifiable fraction. Device-derived margin rises to 0.968 (k=5) and 0.991 (k=8) — the competence arm — while the ceiling collapses to 0.05. |
| R6 | **`verify_citations.py` BLOCK** — now diagnosed precisely | Was recorded vaguely as "authorize RKA image fix or PI override". It is neither. **What I fixed:** the RKA manifest was *stale*, not missing — it carried `diot2019`/`fltrust2021` and lacked the two keys the draft cites. Created the two missing `lit_` records, rebuilt the manifest (rev 23→24, 17 keys matching the draft exactly). Also found a real **attribution defect**: the paper implements, evaluates and tabulates FLTrust but never cited it — `\cite{fltrust2021}` added, plus Krum and trimmed-mean in the same table. **What remains, and needs you:** (a) 14 of 17 refs have `validation.status="error"` because RKA holds no DOI for them — mostly NeurIPS/ICML/PMLR/UAI-era papers that genuinely have none; (b) `approved_citation_keys` is **empty**, so every key counts as unapproved. (b) is the PI ratification and cannot be self-served. | **PI** — ratify the 17 keys, or record an override for the no-DOI venues. I deliberately did **not** hand-enter DOIs from memory; that is the exact fabrication risk the gate exists to catch. |
| ~~R8~~ | ~~Body over the page limit~~ | | **done, and the CFP revealed a worse problem first.** `sp2027.ieee-security.org/cfpapers.html` mandates `\documentclass[conference,compsoc,letterpaper]{IEEEtran}` v1.8b — ours was `[conference]`, no `compsoc`, and the CFP says such papers are *"subject to rejection without review."* Switched (which itself cost a page). Real limit is **"up to 13 pages of text and up to 5 pages for references and appendices, totaling no more than 18"** — so this was relocation, not amputation. Final: **text pp1–13, appendix+refs pp14–18, total 18.** All three constraints met exactly, US letter (612×792). |
| ~~R7~~ | ~~Confirm CFP page-limit exclusions~~ | | **done** — read from the CFP directly. Also captured: double-blind required; Ethics Considerations and Generative-AI usage are **submission-form fields**, and camera-ready ethics sections do not count toward the limit; cycle-1 abstract **2026-06-04**, paper **2026-06-11**; cycle-2 **2026-11-10 / 2026-11-17**. |
| ~~R5~~ | ~~Regenerate figures/tables after R1 and R4 land~~ | | **done** — full regenerate + rebuild ran clean. `check_completeness` 0 duplicates across all lanes, `verify_paper_claims` **0 unverified numeric literals**, no undefined references (the one `main.log` "undefined" is a font-shape warning). Chain's render step fixed: it called a `render.sh` that does not exist in this workspace; now uses the same pdflatex/bibtex sequence as `finish_all.sh`. |

## Known limits stated in the paper

- Literature inventory is a documented sample of 3 defences, not a systematisation.
  No result depends on it; it motivates the observability lattice and skew instrument.
- ~~One dataset~~ — **resolved.** N-BaIoT recovered in full (9/9 devices) and run as a natural experiment (R11). CICIoT2023 remains unusable: its CSVs carry no device identifier, so it cannot serve as a partition substrate at all.
  for partitioning: no device identifier in the tabular release, and recovering one
  means re-extracting from ~0.5 TB of pcaps in which attack captures are dominated by
  the attacker rather than the victim. That is a property of the published artifact.
- ~~k ≥ 3 sampled~~ — full enumeration queued (R12).
- **New limit, found by Experiment C:** S_JS does not capture data-volume skew, which
  is the most damaging component per unit of measured divergence. The paper's own
  instrument is necessary but not sufficient, and its recommendation that authors
  report a skew statistic must be qualified to include the client-size distribution.
