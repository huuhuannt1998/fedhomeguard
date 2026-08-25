# FedHomeGuard — Detailed Technical Research Design

**Project:** `prj_01M0EE73RTCAK0JNGD4SY4A1Y2` (FEDHOMEGUARD)
**Author:** Executor, on PI direction · **Date:** 2026-08-19
**Target venue (inferred):** IEEE S&P / USENIX Security systematization track; fallback ACM CCS, NDSS; journal fallback IEEE TIFS.
Inferred from RKA `jrn_01M0EE94ZGPQNFR1DR90JAEPD0` ("Auditing what the thirty actually guarantee is an S&P paper").

---

## Status and discipline

**Read this paragraph before any number in this document.**

- **Thrust A is a measurement study.** It measures what published FL-IoT-IDS defenses provably guarantee, and measures certified accuracy for federated IoT anomaly detection under device-derived partitions. It is the paper's **floor**. It produces a result whether the numbers are good or catastrophic.
- **Thrust B is a hypothesis under test.** It asserts that certification remains non-vacuous at deployment-relevant adversary fractions and that its decay is a predictable function of a *measured* heterogeneity statistic. It is the paper's **ceiling**. It may fail.
- **Gate G1** decides between them. **Build nothing below Stage 3 until G1 resolves.**
- **Every number in this document is a target to be measured, never a result being reported.** No experiment in this design has produced a value yet. Where prior/scoped observations exist they are marked *directional*.
- **Predeclaration.** The property catalog (§9), the severity classes, the statistical contrasts, and the success thresholds are all fixed *before* any run, so "vacuous", "collapse", and "gap" are never defined after seeing the data.

### Spine (one line)

> The federated IoT intrusion-detection literature demonstrates robustness it cannot prove; FedHomeGuard measures the **certification gap** — the distance between demonstrated and provable robustness — under *device-derived* smart-home heterogeneity, and maps the region where the field makes claims no certificate supports.

### Spine (thesis)

FedHomeGuard claims, jointly:

- **(A) A negative systematization result.** Across the published FL-IoT-IDS defense wall, the set of statements of the form *"given at most a β fraction of malicious clients, accuracy at least α survives **any** attack in threat class T"* is **empty**. Every defense reports accuracy under a *chosen* attack set at *chosen* β. We make this precise by writing each defense's actual guarantee in a common template and showing the quantifier structure is ∃-over-attacks, not ∀-over-attacks.
- **(B) A transfer result.** Certified-robustness machinery developed for generic FL — ensemble/subsampling certification (FLCert / Cao et al.) and parameter smoothing-and-clipping certification (CRFL) — can be transferred to federated IoT anomaly detection, and yields the field's first *sound lower bound* on worst-case accuracy in this setting.
- **(C) A gap-and-frontier result.** The quantity Γ(β, S) = (empirical robustness) − (certified robustness) is large, and there exists a heterogeneity level beyond which certification is **vacuous** while the literature continues to assert robustness. The region where the field claims and the certificate is silent is the paper's headline object.

**Structural analogy, used for shape only.** The relationship of (A) to (B) mirrors the *"attack papers vs. proof papers"* split that preceded certified adversarial-example defenses: a decade of empirical defenses, each broken by adaptive attacks, until certification reframed the question from *"does it resist my attack?"* to *"what survives every attack in the class?"*. **We are not claiming** that FL-IoT-IDS defenses are broken, nor that we break them, nor that certification supersedes them. We claim only that the *quantifier structure* of the field's claims is the same one that historically preceded a correction, and that nobody has yet measured what certification yields here.

---

## 1. Problem statement and formal model

### 1.1 Informal problem

A smart home runs an intrusion detector. Because raw household traffic is private, the detector is trained federatedly: each home trains locally on its own device traffic and sends model updates to a server that aggregates them. Some homes are compromised and send adversarial updates. A dense literature of robust aggregation rules exists to handle this, and each reports high accuracy under the attacks its authors chose, at malicious fractions its authors chose. None of them answers the question a deployer actually asks: *if up to β of my participants are hostile and I do not know what they will do, what accuracy am I guaranteed?* Separately, smart-home federations are not merely non-IID — the partition is induced by **which physical devices a household owns**, which makes the label and feature distributions across clients differ structurally, not just statistically. Certification machinery generally assumes bounded heterogeneity. This design measures what happens when it does not hold.

### 1.2 Formal model

**Clients and data.** Let `N` be the number of participating households, indexed `i ∈ [N]`. Let `𝒟` be the space of labelled flow records `(x, y)`, `x ∈ ℝ^d`, `y ∈ 𝒴 = {benign, attack}` (binary; the multi-class variant `𝒴_m` is used only in Stage 6).

Let `𝔇 = {δ_1, …, δ_M}` be the **device catalog**: `M` distinct physical device types, each with a conditional traffic law `P_δ(x, y)`.

A **household composition** is a multiset `h_i ⊆ 𝔇` — the devices household `i` owns. The client's data law is the mixture

  `P_i(x, y) = Σ_{δ ∈ h_i} w_{i,δ} · P_δ(x, y)`,  `Σ_δ w_{i,δ} = 1`, `w_{i,δ} ≥ 0`.

The local dataset is `D_i ~ P_i^{n_i}`. **This mixture is the object D1 insists must come from data, not from a Dirichlet knob**: `h_i` and `w_{i,δ}` are read off real per-device captures (§2.4), not sampled from `Dir(α)`.

**The learner.** A federated algorithm `𝒜` maps a client-update profile to a global model. Round `t`: each client returns `u_i^t ∈ ℝ^p`; the server computes `θ^{t+1} = Agg(θ^t, u_1^t, …, u_N^t)`. Write `𝒜(C)` for the global model obtained by running `𝒜` on the client subset `C ⊆ [N]`.

**The adversary as a constrained function.** Let `B ⊆ [N]` be the malicious set, `|B| ≤ m`, `β := m/N`. The adversary is a function

  `𝔄 : (knowledge K, budget 𝔅, round t) ↦ {u_i^t}_{i ∈ B}`

subject to the **feasibility constraints**, all of which must be declared per experiment in the capability record (§2.3):

- **F1 (count)** `|B| ≤ m`. The adversary controls at most `m` clients and cannot create more (no unbounded sybils).
- **F2 (update space)** `u_i^t ∈ 𝒰`. For the **Byzantine** class `𝒰 = ℝ^p` (arbitrary). For the **bounded-backdoor** class `‖u_i^t‖_2 ≤ ρ`.
- **F3 (knowledge)** `K ∈ {black-box, gray-box, white-box}` — respectively: no access to honest updates; access to the global model each round; access to the global model *and* honest clients' updates and the aggregation rule's internals.
- **F4 (seed)** whether the adversary knows the server's subsampling randomness. **Default: NO.** Certification by subsampling is unsound if the adversary can predict the seed; this must be stated, not assumed away.
- **F5 (persistence)** the malicious set is fixed across rounds (static) or may change (adaptive membership).
- **F6 (data)** whether the adversary may also poison its local *data* in addition to its updates.

**Reachable set.** For a test point `x`, define the set of global models the adversary can force:

  `ℛ(x; m, 𝒰, K) = { 𝒜(u_1,…,u_N) : ∃ B, |B| ≤ m, {u_i}_{i∈B} ∈ 𝒰^{|B|}, {u_i}_{i∉B} honest }`.

**Worst-case accuracy** is `WCA(m) = E_{(x,y)} [ inf_{θ ∈ ℛ(x;m,𝒰,K)} 1{f_θ(x) = y} ]`. This is the quantity the field implicitly claims and never computes.

### 1.3 The distinguishing formal device — the vacuity frontier

Certification supplies a **sound lower bound** `CA(m) ≤ WCA(m)` ("certified accuracy") without enumerating attacks. Define the **trivial certificate**: the constant predictor `f_triv(x) = argmax_y Pr[y]`, which ignores all client data and is therefore certifiably robust to *every* `m`. Its accuracy is the majority-class rate

  `τ_triv := max_y Pr_{(x,y) ~ P_test}[y = ŷ]`.

**Definition (Vacuity).** A certificate is **vacuous** at `(m, S)` iff `CA(m, S) ≤ τ_triv`. Indicator `V(m,S) = 1{CA(m,S) ≤ τ_triv}`.

> This is the definition that makes the novel claim *checkable*. A certified accuracy of 63% sounds like a result; if the benign class is 63% of test flows, it is **nothing** — the constant predictor achieves it with no learning and no data. Predeclaring `τ_triv` as the floor forbids the most common way this kind of paper cheats.

**Definition (Certified breakdown point).** `β*(S) := max { β : CA(βN, S) > τ_triv }`, with `β*(S) := 0` if the set is empty.

**Definition (Claim region and honest region).**
- `R_lit := { (β, S) : some published FL-IoT-IDS defense asserts robustness at malicious fraction β and heterogeneity S }` — extracted in Thrust A from each paper's own evaluation grid.
- `R_hon := { (β, S) : CA(βN, S) > τ_triv }` — measured in Thrust B.

**The headline object is the set difference `R_lit \ R_hon`**: the region of the deployment plane where the field makes robustness claims and no certificate currently supports any. This set is what the paper's flagship figure draws.

### 1.4 The novel mechanism, formalized

**Heterogeneity-Induced Certification Collapse (HICC).**

> **∃-statement.** ∃ `S₀ < S_real` such that for all `S > S₀`: `β*(S) = 0`, while for the same partitions and the same model there exist published-style defenses `𝒜_def` and evaluated attack sets `𝒜tk` with empirical accuracy `EA(𝒜_def, 𝒜tk, β = 0.2, S) > 0.9`.
>
> Here `S_real` is the *measured* skew of device-derived partitions from real captures (§2.4), not a chosen constant.

In words: there is a heterogeneity level, **below the one real smart homes exhibit**, past which certification says nothing at all, while empirical evaluation continues to report >90% accuracy at 20% malicious clients. HICC is falsified if `β*(S_real) > 0`.

**Why this is a mechanism and not a complaint.** The proposed mechanism is specific: subsampling certification (FLCert) certifies by requiring that a *majority of subsample-trained global models agree* on a test point. Under device-derived skew, a subsample of clients that omits the devices generating a given flow type produces a model with no competence on it, so the ensemble's vote margin on that flow collapses — independently of any adversary. Certified accuracy is bounded by the *margin*, so heterogeneity consumes the certificate's budget before the adversary spends any of it. §4-I2 states this as an insight and §5-Alg 6 makes it measurable by decomposing margin loss into heterogeneity-caused and adversary-caused parts.

### 1.5 The metric instrument

All metrics are defined here and are the only metrics used in §10 and §11.

| Symbol | Name | Definition |
|---|---|---|
| `EA(𝒜_def, a, β)` | empirical accuracy | test accuracy of the global model under concrete attack `a` at fraction `β` |
| `EA_min(𝒜_def, β)` | empirical robustness | `min_{a ∈ 𝒜tk} EA(𝒜_def, a, β)` — the *best case for the defense*, since `𝒜tk` is finite |
| `CA(β, S)` | certified accuracy | sound lower bound on `WCA`; fraction of test points whose prediction provably cannot be changed by any `≤ βN` malicious clients |
| `τ_triv` | trivial floor | majority-class rate on the test set |
| `V(β,S)` | vacuity | `1{CA(β,S) ≤ τ_triv}` |
| `β*(S)` | certified breakdown point | largest `β` with `CA > τ_triv` |
| **`Γ(β,S)`** | **certification gap** | **`EA_min(β,S) − CA(β,S)`** — the headline scalar |
| `S` | skew | measured heterogeneity (below) |
| `A(x)` | abstain-adjusted | fraction of test points where the certificate abstains (margin too small) |
| `MC_het` | heterogeneity margin cost | vote-margin loss attributable to partition, measured at `β = 0` |
| `MC_adv` | adversary margin cost | additional vote-margin loss at `β > 0` |

**The skew statistic `S` (measured, never a knob).** Two components, both reported:

- `S_JS := (2 / (N(N−1))) · Σ_{i<j} JSD(P̂_i ‖ P̂_j)` — mean pairwise Jensen–Shannon divergence between clients' empirical joint label×device-class histograms. Bounded in [0,1], symmetric, defined for disjoint supports (which is exactly the smart-home case, and is why JSD is used rather than KL).
- `S_dev := 1 − (mean pairwise Jaccard similarity of household device sets h_i)` — structural device-overlap skew.

**Conditionals that localize a failure.** These are the diagnostic core: a low `CA` alone does not say *why*.

1. If `CA(β=0, S) ≤ τ_triv` → **the certificate died on heterogeneity alone**, before any adversary. Failure is in the partition, not the threat model. (`MC_het` dominant.)
2. If `CA(β=0,S) ≫ τ_triv` but `CA(β=0.1,S) ≤ τ_triv` → **the certificate is real but the breakdown point is below deployment relevance.** (`MC_adv` dominant.)
3. If `CA` is healthy but `Γ` is large → **certification is sound but loose**; the honest claim is "we cannot prove what the defenses demonstrate", which is a weaker and more careful statement than "the defenses are wrong".
4. If `Γ ≤ 0` → **measurement error or an unsound certificate.** `Γ < 0` means the certified bound exceeds observed worst-case accuracy, which is impossible if the certificate is sound and `𝒜tk` is within the threat class. Treated as a **bug signal**, not a finding.

**Breakdown of misses into meaningfully different kinds.** A test point that is not certified is classified as exactly one of:
- **ABSTAIN-het** — ensemble vote margin insufficient, and `β = 0` also fails to certify it (heterogeneity-limited).
- **ABSTAIN-adv** — certified at `β = 0`, not certified at the target `β` (adversary-budget-limited).
- **WRONG** — certified but certified *to the wrong label* (a certified error; the model is confidently and provably wrong).
This three-way split is the difference between "the certificate is weak" and "the model is bad", and the literature's aggregate accuracy numbers cannot distinguish them.

### 1.6 Tractability — named honestly, then bounded

**The hard problem.** Computing `WCA(m)` exactly requires evaluating `inf` over `ℛ(x; m, ℝ^p, ·)`: an optimization over an unbounded continuous update space, composed through `T` rounds of a nonlinear aggregation rule, for every test point, and additionally a combinatorial choice of `B` over `C(N,m)` subsets. **This is intractable.** Even the restricted question "does there exist a `≤ m`-client update profile flipping the prediction on `x`?" is, for a general nonlinear aggregator and a ReLU network, at least NP-hard — it embeds the standard NP-hard ReLU-network verification problem as the special case `N = m = 1` with the aggregator equal to the identity. We do **not** attempt it.

**Proposition (what makes the bounded version well defined).** Subsampling certification replaces the `inf` over `ℛ` with a *counting* argument that never mentions the adversary's update values. Under **F1** (`|B| ≤ m`) and **F4** (adversary does not know the seed), if `K` global models are each trained on a uniformly random client subset of size `k`, then a global model is *corrupted* only if its subset intersects `B`. The number of subsets disjoint from `B` is `C(N−m, k)`, so the fraction of uncorrupted models is at least `p_clean = C(N−m,k)/C(N,k)`. If the ensemble's top-label vote count exceeds the runner-up by more than `2(1 − p_clean)K`, the prediction is invariant to **every** choice of malicious update values. This converts an intractable `inf over ℝ^p` into an exactly computable combinatorial margin condition. **The bound is sound and loose by construction**; its looseness is precisely the quantity `Γ` this project measures.

**Exact at small scale, sampled at large scale.**
- For `N ≤ 20` and `k ≤ 6`, `C(N,k) ≤ 38,760`. Where the ensemble size `K` can equal `C(N,k)` we compute the certificate by **exact enumeration** — no sampling, no confidence interval, no statistical test needed.
- For larger `N`, `K` is a Monte-Carlo sample of subsets. The vote proportions become estimates and require **Clopper–Pearson** one-sided intervals at level `α = 0.001`, and the reported `CA` uses the conservative interval endpoint. This distinction is enforced in §11: **exact arms are reported without error bars because they have no sampling error; sampled arms are never reported as point estimates.**

### 1.7 Notation summary

| Symbol | Meaning |
|---|---|
| `N`, `i` | number of client households; client index |
| `𝔇`, `δ`, `M` | device catalog, a device type, catalog size |
| `h_i`, `w_{i,δ}` | household `i`'s device set and traffic mixture weights |
| `P_i`, `D_i`, `n_i` | client `i`'s data law, dataset, sample count |
| `m`, `β`, `B` | malicious client count, fraction `m/N`, malicious set |
| `𝒰`, `ρ` | adversarial update space; backdoor magnitude bound |
| `K`, `k` | ensemble size; subsample size per ensemble member |
| `p_clean` | `C(N−m,k)/C(N,k)`, min fraction of uncorrupted ensemble members |
| `T`, `p`, `d` | FL rounds; model parameter count; feature dimension |
| `CA`, `EA_min`, `Γ` | certified accuracy, empirical robustness, certification gap |
| `τ_triv`, `V`, `β*` | trivial floor, vacuity indicator, certified breakdown point |
| `S_JS`, `S_dev` | distributional and structural skew statistics |
| `R_lit`, `R_hon` | literature claim region; certifiably honest region |

---

## 2. System model in the notation

### 2.1 Components

- **Clients** `i ∈ [N]`: household gateways. Hold `D_i`, run `E` local epochs of SGD on a small MLP or autoencoder, emit `u_i^t`.
- **Server**: runs `Agg`; in the certified variants runs `K` parallel FL instances over sampled client subsets.
- **Adversary**: controls `B`, `|B| ≤ m`, with capabilities fixed by the record in §2.3.
- **Evaluator (ours, not part of the deployment)**: holds the global test set, computes `CA`, `EA_min`, `Γ`, `S`. Has powers no real deployment has; **this is explicitly outside the trust model** and is used only for measurement.

### 2.2 Observability lattice

Each algorithm consumes only what its level authorizes. Levels are nested `L0 ⊂ L1 ⊂ L2 ⊂ L3`.

| Level | Server observes | Realistic? | Used by |
|---|---|---|---|
| **L0** | nothing beyond the aggregate | yes | FedAvg, plain aggregation |
| **L1** | individual client updates `u_i^t` each round | yes | Krum, trimmed-mean, median, norm-clipping, CRFL, FLCert |
| **L2** | L1 **+ a clean, correctly-labelled server-side validation set** | **often not** — this is *the recurring deployment assumption* the systematization targets | FLTrust, P4P probe vectors, trust-scoring defenses |
| **L3** | L1 + ground-truth identity of `B` | **no — upper bound only** | oracle-β trimmed mean (§11 baseline, labelled UPPER BOUND) |

> **L2 is the crux of Thrust A.** A defense that needs a clean labelled validation set at the server has assumed away a large part of the federated problem: if the operator already possessed representative labelled smart-home attack traffic, the motivation for federating is materially weakened. The systematization records, per defense, whether it requires L2 and whether the paper acknowledges it.
>
> **L3 results are never reported as achievable.** They are printed in every table as a ceiling so the reader can see how much of a defense's headline number comes from knowledge no deployment has.

### 2.3 Capability record schema (shipped with every result)

**Anything not in this record was not assumed.** Every measurement in the artifact carries one.

```json
{
  "record_version": "1.0",
  "run_id": "string",
  "federation": {
    "N": 20, "clients_per_round": 20, "rounds_T": 30,
    "local_epochs_E": 2, "batch_size": 64, "optimizer": "sgd", "lr": 0.01,
    "model": {"arch": "mlp", "hidden": [64, 32], "params_p": 0}
  },
  "partition": {
    "source": "device_derived | dirichlet_matched | iid",
    "dataset": "n-baiot | iot-23 | ciciot2023",
    "device_catalog_M": 9,
    "household_compositions": [["Danmini_Doorbell", "Ecobee_Thermostat"]],
    "S_JS": null, "S_dev": null,
    "note": "S_* are MEASURED from the realized partition, never set"
  },
  "adversary": {
    "m": 2, "beta": 0.10,
    "F1_count_bound": 2,
    "F2_update_space": "byzantine_unbounded | l2_ball",
    "F2_rho": null,
    "F3_knowledge": "black_box | gray_box | white_box",
    "F4_knows_subsample_seed": false,
    "F5_membership": "static | adaptive",
    "F6_may_poison_data": false,
    "attack_ids": ["label_flip", "sign_flip", "gaussian", "ipm", "alie", "backdoor_trigger"]
  },
  "defense": {"name": "fedavg", "observability_level": "L0|L1|L2|L3",
              "requires_clean_server_data": false, "knows_true_beta": false},
  "certification": {
    "family": "flcert_subsample | crfl_smoothing | none",
    "K": 100, "k": 5, "exact_enumeration": false,
    "p_clean": null, "confidence": 0.999, "interval": "clopper_pearson"
  },
  "budget": {
    "headline": "equal_total_gradient_steps",
    "total_gradient_steps": 0, "wall_clock_s": 0, "peak_rss_gb": 0,
    "device": "apple_m4_mps", "note": "single laptop; no cluster; no GPU tier"
  },
  "metrics": {"EA_min": null, "CA": null, "Gamma": null,
              "tau_triv": null, "V": null, "abstain_het": null,
              "abstain_adv": null, "certified_wrong": null},
  "seeds": {"partition_seed": 0, "train_seed": 0, "subsample_seed": 0}
}
```

### 2.4 Trust assumptions, and what is *not* silently included

**Assumed.** Server executes the protocol honestly and does not collude with `B`. Client count is enforced (no free sybils). Subsampling randomness is private (F4). Honest clients' data is correctly labelled locally. Communication is authenticated.

**NOT assumed, and therefore not covered by any guarantee produced here.** Server compromise. Sybil creation beyond `m`. Adversary knowledge of the subsample seed. Cross-round adaptive membership unless F5 says so. Privacy of updates (this project makes **no** privacy claim; see §7-C6). Availability/DoS on the aggregation. Concept drift across time. Any device type absent from the catalog `𝔇`.

---

## 3. Motivation, state of the art, and the gap

### 3.1 Lines of prior work

**Line 1 — Robust aggregation for FL-IoT-IDS (the defense wall; ~30 papers, still growing in 2026).**
P4P (probe-guided anti-poisoning, 2026), FedMADE (dynamic aggregation), trust-aware federated IDS with validation-based trust scoring, WeiDetect, FLTrust, FedCC, FLARE, ShieldFL, DeepSight, DART, FedAware, Fed-FeRe, PenTiDef, plus Krum / trimmed-mean / median as inherited baselines.
*What they do:* propose an aggregation or filtering rule and demonstrate high accuracy under a chosen attack set at chosen malicious fractions (commonly 10–40%), on CICIDS2017/CSE-CIC-IDS2018/ToN-IoT/N-BaIoT/ACI-IoT/IoTDIAD.
*What they do not do:* state any ∀-over-attacks guarantee. Their claims are of the form "resists the attacks we ran". Several additionally require **L2** (a clean labelled server validation set / probe or root dataset) without flagging it as a deployment obstacle. Recent surveys independently note "a significant gap between idealized experimental assumptions and the practical realities of IoT networks".

**Line 2 — Theory in FL-IoT that is about a different thing.**
HADA-FL and similar prove **non-IID convergence** bounds. Related 2025–2026 work proves privacy guarantees via **differential privacy** / LDP.
*What they do:* prove training converges under heterogeneity, or that updates leak boundedly.
*What they do not do:* bound accuracy under adversarial clients. **Convergence ≠ robustness; privacy ≠ robustness.** §3.3 makes this classification mandatory and auditable, because conflating them is the single most likely reviewer error and the single most likely way this project's novelty claim gets wrongly dismissed.

**Line 3 — Certified robustness in generic FL.**
CRFL (Xie, Chen, Chen, Li; ICML 2021) — clipping + parameter smoothing giving a sample-wise certificate against *bounded-magnitude* backdoors. Cao, Jia, Gong — *Provably Secure FL against Malicious Clients* (AAAI 2021) and **FLCert** (TIFS 2022) — ensemble over client subsets with majority vote, certifying invariance to a bounded number of malicious clients (reported e.g. 88% certified accuracy on MNIST at 20/1000 malicious).
*What they do:* supply exactly the machinery this project needs.
*What they do not do:* apply it to intrusion detection, to IoT traffic features, or to the extreme structural heterogeneity of device-derived partitions. Their evaluations are image benchmarks with mild, synthetic heterogeneity and very favourable `m/N` (2%). **The malicious fractions the IoT-IDS literature routinely evaluates are 5–20× larger.**

**Line 4 — Poisoning attacks on FL-IoT-IDS.**
NDSS DISS'20 poisoning of FL-based IoT IDS; IPM, ALIE, sign-flip, label-flip, backdoor construction.
*What they do:* supply the attack set `𝒜tk`.
*What they do not do:* bound anything; an attack paper establishes an upper bound on robustness, never a lower bound.

### 3.2 The N-dimension intersection

FedHomeGuard is the only work holding all five jointly:

1. **Federated** learning, **2. IoT intrusion detection** as the task, **3. certified** (∀-over-attacks, sound lower bound) rather than empirical robustness, **4. under partitions derived from *real device populations* rather than a Dirichlet knob**, and **5. reported as a gap against the empirical literature's own operating points** rather than as a standalone number.

Line 1 has {1,2,4-ish} and lacks 3. Line 3 has {1,3} and lacks {2,4}. Line 2 has neither 3 nor 5. Nobody holds 3∧4, and 5 exists nowhere.

### 3.3 Mandatory classification of every theoretical hit

Every paper entering related work is tagged exactly one of **CONVERGENCE / PRIVACY / ROBUSTNESS**, and only ROBUSTNESS hits can threaten novelty. The tag, the quantifier structure of the paper's main theorem, and the reason for the tag are recorded per paper in the artifact.

*Directional (M1 sweep, 2026-08-19; not yet exhaustive):* no ROBUSTNESS-class certified result for FL-IoT-IDS was found; CRFL and FLCert remain generic-FL; CRFL's authors show no move into intrusion detection. This is a scoop-gate observation, **pending completion of the T1 sweep**, not a proven absence.

---

## 4. Insight

**I1 — The field's claims and the field's evidence have different quantifiers.** Every FL-IoT-IDS defense paper's evidence is `∃ attacks a ∈ 𝒜tk : accuracy high`, while its abstract reads as `∀ attacks`. This is not misconduct; it is the normal state of an empirical field. But it means the literature's robustness numbers are **upper bounds on what is provable**, and nobody has computed the lower bound to compare against. The gap between them is a measurable, previously unmeasured quantity.

**I2 — Heterogeneity spends the certificate's budget before the adversary does.** Subsampling certification certifies via ensemble vote margin. A subsample that omits the devices generating a flow type yields a member with no competence on it, shrinking the margin at `β = 0`. The adversary then only has to consume what heterogeneity left. Therefore certified accuracy under device-derived partitions should degrade **super-linearly** in `β`, and the `β = 0` margin is the resource being depleted. This makes `MC_het` vs `MC_adv` the right decomposition, and predicts the collapse is *not* an adversary-strength story.

**I3 — The trivial certificate is the only honest floor.** A constant predictor is certifiably robust to any `β`. Any certified accuracy at or below the majority-class rate conveys zero information. Because IoT-IDS test sets are frequently class-imbalanced (benign-heavy or attack-heavy depending on assembly), a paper can report "certified accuracy 0.72" that is strictly worse than predicting one label. Predeclaring `τ_triv` closes this.

**I4 — Deployment assumptions are a robustness parameter, not a footnote.** A defense requiring L2 (clean server validation data) is solving a materially different problem. Placing every defense on the observability lattice converts a qualitative "assumptions vary" remark into a comparable axis, and reveals that part of the wall's reported robustness is purchased with knowledge deployments do not have.

**I5 — Device-derived partitioning must be shown to matter, or it should not be claimed.** The premise "smart homes are a harsher non-IID regime" is only earned if a Dirichlet partition **matched on the measured skew statistic** fails to reproduce the effect. If it reproduces it, the honest conclusion is that skew magnitude — not device structure — drives the result, and the paper says so. §5-Alg 4 and §11-Stage 5 make this a required experiment, not an optional ablation.

---

## 5. Proposed system and algorithms

### 5.1 Components

`C1` device-derived partitioner · `C2` FL trainer (the deterministic primitive) · `C3` attack suite · `C4` defense suite on the observability lattice · `C5` certification engines (subsample-ensemble; smoothing) · `C6` gap-and-frontier analyzer · `C7` necessity/anti-triviality harness · `C8` capability-record emitter.

### 5.2 Algorithms

---

**Algorithm 1 — `FLRun` (the deterministic execution primitive everything else calls).**

```
INPUT : client subset C ⊆ [N]; datasets {D_i}; rounds T; local epochs E;
        aggregation Agg; adversary spec 𝔄 (may be null); seeds σ
OUTPUT: global model θ_T ; trace τ
 1  θ_0 ← init(σ.train)                       # deterministic given σ
 2  for t = 0 … T−1:
 3      for i ∈ C in fixed sorted order:      # order fixed ⇒ reproducible
 4          if 𝔄 ≠ null and i ∈ 𝔄.B:
 5              u_i ← 𝔄.emit(i, t, view(𝔄.F3))    # honours F2/F3/F4/F5/F6
 6          else:
 7              u_i ← LocalTrain(θ_t, D_i, E)     # SGD, seeded by σ.train
 8      θ_{t+1} ← Agg(θ_t, {u_i}_{i∈C})
 9      τ.append(round_stats(t))
10  return θ_T, τ
```
*Determinism is a requirement, not a nicety:* Algorithm 2 calls `FLRun` `K` times and the certificate's soundness argument assumes each member differs only through its client subset.

---

**Algorithm 2 — `CertifySubsample` (FLCert-style; exact for small `N`).**

```
INPUT : N; datasets; subsample size k; ensemble size K; adversary bound m;
        test set 𝒯; confidence 1−α
OUTPUT: per-point certificate; CA(m); abstain breakdown
 1  if C(N,k) ≤ K_max and K = C(N,k):
 2      𝒮 ← all k-subsets of [N];  exact ← true          # NO sampling error
 3  else:
 4      𝒮 ← K subsets ~ Uniform(k-subsets), seed σ.subsample (PRIVATE, F4)
 5      exact ← false
 6  for each C ∈ 𝒮:  θ_C ← FLRun(C, …, 𝔄 = null)          # honest training
 7  p_clean ← C(N−m, k) / C(N, k)                          # exact rational
 8  for each (x,y) ∈ 𝒯:
 9      votes ← histogram over labels of { f_{θ_C}(x) : C ∈ 𝒮 }
10      ŷ, n1 ← top label and its count ;  n2 ← runner-up count
11      if exact:  margin ← (n1 − n2)/K
12      else:      margin ← lower_CP(n1,K,α) − upper_CP(n2,K,α)   # Clopper–Pearson
13      certified ← margin > 2·(1 − p_clean)
14      classify point: CERT-CORRECT if certified ∧ ŷ=y
15                      CERT-WRONG   if certified ∧ ŷ≠y
16                      ABSTAIN-het  if ¬certified ∧ ¬certified_at(m=0)
17                      ABSTAIN-adv  if ¬certified ∧  certified_at(m=0)
18  CA(m) ← |CERT-CORRECT| / |𝒯|
19  return CA(m), breakdown, exact
```
*Line 13 is the whole certificate:* it never mentions the adversary's update values, which is why it holds for **all** `𝒰 = ℝ^p`.

---

**Algorithm 3 — `CertifySmoothing` (CRFL-style, bounded-magnitude class).**

```
INPUT : rounds T; clip norm ρ_c; noise σ_n; smoothing samples Ns; test 𝒯
OUTPUT: per-point certified radius in backdoor-magnitude
 1  θ ← FLRun(...) with per-round: θ ← Clip(θ, ρ_c); θ ← θ + N(0, σ_n² I)
 2  for (x,y) ∈ 𝒯:
 3      draw Ns parameter samples θ^(j) ~ N(θ, σ_n² I)
 4      p̂_top ← lower_CP( #{j : f_{θ^(j)}(x) = ŷ}, Ns, α )
 5      radius(x) ← σ_n · Φ⁻¹(p̂_top)          # 0 if p̂_top ≤ 0.5
 6  CA_ρ ← fraction with ŷ = y ∧ radius(x) ≥ ρ
 7  return CA_ρ, radius distribution
```
*Reported separately and never merged with Algorithm 2:* the two certify **different threat classes** (`|B| ≤ m` with arbitrary updates vs bounded-magnitude perturbation). Merging them into one "certified accuracy" column would be dishonest, and §11 forbids it.

---

**Algorithm 4 — `MatchedDirichletControl` (the necessity / anti-triviality test).**

```
INPUT : realized device-derived partition Π_dev with measured skew S* = (S_JS*, S_dev*)
OUTPUT: Π_dir with S_JS(Π_dir) ≈ S_JS*, and the paired comparison
 1  measure S* ← Skew(Π_dev)
 2  binary-search α over Dirichlet(α) label partitions:
 3      Π_dir(α) ← dirichlet_partition(N, α, seed)
 4      until |S_JS(Π_dir(α)) − S_JS*| ≤ ε        # ε = 0.01, predeclared
 5  for R independent seeds: run Stage-3 certification on BOTH Π_dev and Π_dir
 6  report paired Δ = CA(Π_dev) − CA(Π_dir) with CI
 7  NECESSITY HOLDS iff Δ is significantly negative
     (device structure hurts BEYOND matched skew magnitude)
 8  else: REPORT that skew magnitude, not device structure, drives the effect
```
*Line 8 is binding.* If necessity fails, the paper's D1 premise is reported as **not supported**, and the claim is downgraded in the abstract. This is predeclared precisely so it cannot be quietly dropped.

---

**Algorithm 5 — `LeaveOneDeviceOut` (counterfactual necessity over components).**

```
INPUT : device catalog 𝔇, partition Π_dev, target metric μ ∈ {CA, β*, Γ}
OUTPUT: per-device contribution to the effect
 1  μ_full ← μ(Π_dev)
 2  for each δ ∈ 𝔇:
 3      Π_{−δ} ← partition rebuilt with device δ removed from all households
 4      μ_{−δ} ← μ(Π_{−δ})
 5      contribution(δ) ← μ_full − μ_{−δ}
 6  COLLAPSE IS STRUCTURAL if no single δ accounts for > 50% of the effect
 7  COLLAPSE IS AN ARTIFACT of one device otherwise — and must be reported as such
```

---

**Algorithm 6 — `MarginDecomposition` (the HICC detector).**

```
INPUT : ensemble 𝒮, test 𝒯, target m
OUTPUT: MC_het, MC_adv, and the HICC verdict
 1  margin_0(x) ← vote margin at m = 0 (heterogeneity only, no adversary)
 2  thresh(m)  ← 2·(1 − C(N−m,k)/C(N,k))          # budget the adversary consumes
 3  MC_het ← 1 − E_x[ margin_0(x) ]                # margin already lost to skew
 4  MC_adv ← E_x[ thresh(m) ]                      # margin the adversary demands
 5  HICC HOLDS at (m,S) iff  MC_het + MC_adv > 1  while EA_min(m,S) > 0.9
 6  return MC_het, MC_adv, verdict
```
*This is the measurement that distinguishes "certification is weak here" from "heterogeneity, not the adversary, killed it" — the mechanism claim in §1.4.*

---

**Algorithm 7 — `GapAndFrontier` (the metric estimator producing the flagship figure).**

```
INPUT : β-grid Β = {0,.05,.10,.20,.30,.40}; skew grid from Stage 5; defenses; attacks
OUTPUT: Γ(β,S) surface, R_hon, R_lit \ R_hon
 1  τ_triv ← majority-class rate of 𝒯                      # predeclared
 2  for (β,S): CA ← Alg2 ; EA_min ← min over 𝒜tk × defenses of EA
 3            Γ(β,S) ← EA_min − CA
 4            if Γ < 0: RAISE BUG  (unsound certificate or out-of-class attack)
 5  R_hon ← {(β,S) : CA > τ_triv}
 6  R_lit ← extracted operating points from Thrust-A inventory
 7  return Γ surface, β*(S) curve, R_lit \ R_hon
```

---

**Algorithm 8 — `DefenseSuite` (the intervention, on the lattice).**

```
INPUT : level L ∈ {L0,L1,L2,L3}
 L0: FedAvg
 L1: Krum, coordinate-wise trimmed-mean(β̂), median, norm-clipping
 L2: FLTrust-style (server root dataset), probe-vector/trust-score (P4P-style)
 L3: trimmed-mean with TRUE B known                    # UPPER BOUND, never achievable
```

**Informal guarantee (Algorithm 2).** *If* at most `m` of `N` clients are malicious (**F1**), *and* the server's subsample seed is private (**F4**), *and* honest training is deterministic given its seed, *then* for every test point marked CERT-CORRECT, the ensemble's predicted label is identical to the label it would predict with **no** malicious clients — **regardless of what the `m` malicious clients send**, including updates chosen with full knowledge of the model, the data, the defense, and the other clients' updates.

**Non-guarantees (what the above explicitly does NOT cover).**
1. **Nothing if `|B| > m`.** The bound is a cliff, not a slope; at `m+1` malicious clients the certificate is void, not degraded.
2. **Nothing if the adversary learns the subsample seed** (F4 violated) — the counting argument collapses entirely.
3. **Nothing about sybils.** `m` bounds *clients*, not *humans*; unmetered client registration voids it.
4. **Nothing about the server.** Server compromise or server–adversary collusion is outside the model.
5. **Nothing about privacy.** No DP claim, no leakage claim, no membership-inference claim is made or implied.
6. **Nothing about availability.** A malicious client that stalls or floods aggregation is out of class.
7. **Nothing about test points that abstain.** Abstention is not safety; an abstaining point is simply uncertified, and in deployment it is still classified — possibly wrongly.
8. **Nothing about CERT-WRONG points.** These are provably stable *and provably wrong*; certification protects the prediction, not its correctness.
9. **Nothing across time.** Concept drift, new device firmware, new attack families are all outside `𝔇` and `𝒴`.
10. **Nothing about devices outside `𝔇`.** The catalog is the model's world.
11. **Algorithm 3's guarantee is a different one** — bounded-magnitude `ρ` on a *sample-wise* basis; it does not bound the number of malicious clients, and the two must never be added.

---

## 6. Methods by thrust

**Thrust A — Systematization (MEASUREMENT; the floor).** Uses no algorithm above except §2.2's lattice and the §9 template. For each defense: extract threat model, attack set `𝒜tk`, evaluated `β` grid, datasets, whether L2 is required, and the quantifier structure of its strongest stated claim; write the claim into the common template; place its operating points into `R_lit`. **Output:** the defense-wall inventory table and `R_lit`.

**Thrust B — Certification and the gap (HYPOTHESIS; the ceiling).** Algorithms 1→2→3 produce `CA`; the attack suite `C3` with Algorithm 1 produces `EA_min`; Algorithm 7 produces `Γ`, `β*(S)`, and `R_lit \ R_hon`; Algorithm 6 produces the HICC verdict; Algorithms 4 and 5 supply necessity. **Output:** the gap surface and the vacuity frontier.

**Thrust C — Substrate realism (ENABLING; not a claim by itself).** Algorithm-free: build `Π_dev` from real per-device captures, measure `S_JS`, `S_dev`, and publish the partition so the skew is auditable. **This thrust makes no scientific claim on its own** and is reported in the artifact, not the contributions, unless Algorithm 4 establishes necessity.

---

## 7. Challenges and mitigations

**C1 — CICIoT2023 does not support device-derived partitioning.** *(Established 2026-08-19, not speculative.)* The published CICIoT2023 CSVs carry 39 aggregate features (`Header_Length … Variance`) and **no device identifier** — no MAC, no source IP, no device label; `Feature_extraction.py` tracks source IPs internally but does not emit them, and rows aggregate 10-packet windows. Directory structure is by **attack type**, not device. Attribution is therefore recoverable only by re-extracting from the PCAPs (~0.5 TB, and attack captures are dominated by the attacker, not the victim device) against `README_Victims_List.pdf`. **Mitigation:** demote CICIoT2023 from partition substrate to *attack-class coverage* only, and build `Π_dev` from N-BaIoT (9 named commercial devices, per-device files) and IoT-23 (per-capture single device, model named in README, source IP consistent — verified). **This invalidates the literal wording of decision D1 and is raised as a blocking checkpoint, not absorbed silently.**

**C2 — The certificate is trivially satisfiable.** *Mitigation:* `τ_triv` predeclared (§1.3, I3); every `CA` reported against it; `V(β,S)` printed in every table; class balance of `𝒯` reported alongside.

**C3 — "The strong result is just a bigger budget."** *Mitigation:* matched-budget comparison (§11). Ensemble certification inherently costs `K×`. **Headline budget = equal total gradient steps**, because that is the resource a deployer actually pays; equal-per-model is reported as a secondary column. Chosen and stated in advance so the framing cannot be picked after seeing which one flatters the result.

**C4 — Device-derived partitioning is decorative.** *Mitigation:* Algorithm 4's matched-skew Dirichlet control, with the negative outcome (line 8) predeclared as publishable.

**C5 — Adaptive attacks make `EA_min` an overestimate.** `𝒜tk` is finite, so `EA_min` is an upper bound on true empirical robustness, which makes `Γ` a **lower bound** on the true gap. *Mitigation:* state this direction explicitly — it is conservative and therefore safe for the paper's claim. Never describe `EA_min` as "robustness".

**C6 — Reviewers conflate convergence/privacy with robustness.** *Mitigation:* §3.3's mandatory tag, a dedicated related-work subsection stating the distinction, and a table column for quantifier structure.

**C7 — Single-laptop compute.** No cluster, no GPU tier, no testbed, no data collection. `K = 100` ensemble members × `T = 30` rounds × `N = 20` clients is 60,000 client-rounds per certification cell, and the design has many cells. *Mitigation:* the compute envelope in §11.6 is a **design constraint that shapes `N`, `k`, `K`, `T`, model size, and sample budget**, not an afterthought; small MLP/autoencoder on flow-level features; exact enumeration preferred over large `K` precisely because it is cheaper *and* stronger; per-cell wall-clock budget enforced and recorded in the capability record.

**C8 — `Γ < 0`.** *Mitigation:* treated as a bug signal (Alg 7 line 4), triggering an audit of certificate soundness and whether the attack violated the declared class — never reported as a finding.

**C9 — N-BaIoT bulk download is unreliable.** UCI serves the archive as a dynamically-generated stream with no `Content-Length` and no range support; observed truncation at varying sizes (402/518/602/753 MB). *Mitigation:* retry loop with integrity check; per-device file retrieval or an alternate mirror as fallback. Logistics only — no bearing on the science, recorded so it is not rediscovered.

---

## 8. Contributions

| ID | Contribution | Survives gate outcome? |
|---|---|---|
| **C-A** | Systematization of the FL-IoT-IDS defense wall by threat model, attack set, evaluated β, datasets, and position on the observability lattice; the common claim template exposing ∃-over-attacks quantifier structure; the finding that the set of certified guarantees in this field is empty. | **YES — unconditional.** Independent of every measurement. |
| **C-B** | First transfer of subsampling and smoothing certification to federated IoT anomaly detection, with `τ_triv`-anchored certified accuracy and the ABSTAIN-het / ABSTAIN-adv / CERT-WRONG decomposition. | **YES.** A measured certificate is a result at any value, including zero. |
| **C-C** | The certification gap `Γ(β,S)` and the vacuity frontier `β*(S)`; the map of `R_lit \ R_hon`. | **YES.** A large or total gap is the finding (D2). |
| **C-D** | HICC — heterogeneity-induced certification collapse, named, formalized as an ∃-statement, and detected by margin decomposition. | **NO — conditional on gate.** Falsified if `β*(S_real) > 0`. |
| **C-E** | Device-derived partition substrate with measured skew, plus the matched-skew Dirichlet necessity test. | **Conditional.** Claimed as a contribution only if Algorithm 4 establishes necessity; otherwise reported as a negative methodological result. |
| **C-F** | Artifact: partitions, capability records, certification engines, and the full inventory, released. | **YES.** |

---

## 9. Predeclared catalog

**Declared before any run so "damage" is never defined after the fact.**

### 9.1 Claim template (Thrust A — one filled instance per defense)

```
DEFENSE          : <name, venue, year>
TASK             : <FL-IoT-IDS / generic FL>
THREAT CLASS T   : <byzantine-unbounded | bounded-norm | data-poisoning | backdoor>
QUANTIFIER       : <∃-over-attacks (empirical) | ∀-over-attacks (certified)>
ATTACK SET 𝒜tk   : <enumerated>
β GRID EVALUATED : <values>
DATASETS         : <list>
OBSERVABILITY    : <L0 | L1 | L2 | L3>
REQUIRES CLEAN SERVER DATA : <yes/no>   ACKNOWLEDGED BY PAPER : <yes/no>
STRONGEST STATED CLAIM     : <verbatim quote>
WHAT IT PROVABLY GUARANTEES: <formal statement, or "none">
DEPLOYMENT ASSUMPTION A REAL FEDERATION WOULD VIOLATE : <text>
CLASSIFICATION (theory only): <CONVERGENCE | PRIVACY | ROBUSTNESS>
```

### 9.2 Outcome severity classes (Thrust B)

| Class | Condition | Meaning |
|---|---|---|
| **S0 — Informative** | `CA(β,S) > τ_triv + 0.10` | certificate carries real information |
| **S1 — Marginal** | `τ_triv < CA ≤ τ_triv + 0.10` | technically non-vacuous, deployment-irrelevant |
| **S2 — Vacuous** | `CA ≤ τ_triv` | certificate says nothing |
| **S3 — Collapsed** | `CA ≤ τ_triv` **at `β = 0`** | heterogeneity alone killed it, no adversary needed |
| **S4 — Certified-wrong** | `CERT-WRONG > 0.05` | provably stable, provably wrong predictions exist |

### 9.3 Success thresholds (fixed now)

- **Gate G1 passes** iff `CA(β = 0.10, S_real) > τ_triv + 0.10` (class S0) on at least one dataset with `N = 20`.
- **HICC confirmed** iff `∃ S₀ < S_real : β*(S) = 0 ∀ S > S₀` **and** `EA_min(0.20, S_real) > 0.90`.
- **Necessity confirmed** iff Algorithm 4's paired `Δ < 0` with 99% CI excluding 0.
- **Structural (not artifact)** iff Algorithm 5 finds no single device contributing > 50%.

### 9.4 Predeclared statistical contrast set (the only confirmatory tests)

1. `CA(β=0.10, Π_dev)` vs `τ_triv` — one-sided, exact where enumeration is exact.
2. `CA(Π_dev)` vs `CA(Π_dir-matched)` at `β=0.10` — paired across seeds (Algorithm 4).
3. `Γ(β)` monotonicity in `β` — trend test across the predeclared β-grid.
4. `β*(S)` monotone decreasing in `S_JS` — trend test across the Stage-5 skew sweep.
5. `CA(N-BaIoT)` vs `CA(IoT-23)` — dataset transfer, paired by seed.

Everything else is exploratory and labelled as such. No confirmatory claim is made from an unlisted contrast.

---

## 10. Scenarios

### Scenario 1 (flagship) — Certification collapses on a realistic household mix while empirical robustness looks excellent

- **Mechanism path:** device-derived partition → subsample members miss whole device classes → vote margin at `β=0` already small (`MC_het` high) → adversary budget `2(1−p_clean)` exceeds the remaining margin → `CA ≤ τ_triv` → meanwhile a trimmed-mean defense under the standard attack set still reports >0.90.
- **Parameter (how many steps):** 3 — (i) partition induces margin loss, (ii) `β` consumes the remainder, (iii) the literature's operating point sits inside the resulting vacuous region.
- **Property violated:** the implicit claim `R_lit ⊆ R_hon`.
- **Setup:** N-BaIoT, `N = 20` households drawn from the 9-device catalog, `k = 5`, `K = C(20,5)` exact where budget permits else `K = 500`, `T = 30`, MLP[64,32], `β = 0.20`.
- **Capability required:** F1 `m = 4`; F2 byzantine-unbounded; F3 gray-box; F4 seed private; F5 static; F6 no data poisoning.

```
CLEAN TRACE  (β = 0, device-derived partition)
  round 30  global acc = 0.964
  ensemble  K = 500, k = 5
  point x* (Mirai C&C flow from a device in 3/20 households)
      votes: attack 271 | benign 229      margin = 0.084
      p_clean(m=0) = 1.000  threshold = 0.000
      -> CERTIFIED (correct)          [margin survives: no adversary budget]
  CA(0)   = 0.71     tau_triv = 0.63    class S0 (barely)
  MC_het  = 0.916                        <-- heterogeneity already ate 92% of margin

ATTACK TRACE (β = 0.20, m = 4, byzantine-unbounded, gray-box)
  point x* (same flow)
      votes: attack 271 | benign 229      margin = 0.084   [unchanged: votes are
                                                            from HONEST training]
      p_clean(m=4) = C(16,5)/C(20,5) = 4368/15504 = 0.2817
      threshold    = 2*(1 - 0.2817)      = 1.4366
      margin 0.084 > 1.4366 ?  NO
      -> ABSTAIN-adv                   [certificate void; prediction unprotected]
  CA(0.20) = 0.09  <=  tau_triv = 0.63   -> V = 1, class S2 VACUOUS
  MC_het + MC_adv = 0.916 + 1.437 = 2.353 > 1     -> HICC HOLDS

  SAME PARTITION, SAME beta, empirical defense (trimmed-mean, L1):
      EA_min(0.20) = 0.93        <-- the literature's reported regime
  GAP  Gamma(0.20, S_real) = 0.93 - 0.09 = 0.84
```

- **Why no simpler version reaches it.** A single-step version — "certified accuracy is low at high β" — is already known generically and is uninteresting. A two-step version — "certified accuracy is low under non-IID" — is confounded with skew magnitude and is exactly what Algorithm 4 is built to exclude. Only the three-step composition is new: it requires (a) a partition whose skew is *measured from real devices* rather than chosen, (b) a decomposition showing the loss is heterogeneity-caused **before** the adversary acts, and (c) the literature's own operating points overlaid to show the vacuous region is where the field publishes.
- **Necessity argument.** Remove step (a) → matched-Dirichlet control (Alg 4); if `Δ ≈ 0` the device structure was decorative and the claim reduces to "high skew hurts", which is weaker and must be stated as such. Remove step (b) → without `MC_het`/`MC_adv` one cannot distinguish "our adversary was strong" from "heterogeneity killed it", and the mechanism claim is unsupported. Remove step (c) → the result is a number about our own setup with no bearing on the field's claims, and `R_lit \ R_hon` is empty by construction.

### Scenario 2 — Certified-wrong predictions (severity S4)

- **Mechanism path:** a device class present in a large majority of households dominates the ensemble vote on flows it does not generate → high-margin, stable, incorrect prediction.
- **Parameter:** 2 steps. **Property violated:** the reader's assumption that "certified" implies "safe".
- **Setup:** IoT-23, `N = 12` (per-capture devices), `k = 4`, exact enumeration `K = C(12,4) = 495`, `β = 0`.
- **Capability required:** none — this occurs with **no adversary at all**.

```
CLEAN TRACE (beta = 0, NO adversary)
  point x' (C&C flow, device present in 2/12 households)
      votes: benign 441 | attack 54     margin = 0.782
      threshold(m=0) = 0                -> CERTIFIED
      true label = attack               -> CERT-WRONG
  certified_wrong_rate = 0.061 > 0.05   -> class S4
  Reading: the certificate is SOUND (prediction is provably stable)
           and the prediction is WRONG. Stability is not correctness.
```

### Scenario 3 — L2 advantage is knowledge, not robustness

- **Mechanism path:** a defense granted a clean labelled server validation set (L2) reports high `EA_min`; the same defense at L1 loses most of it; the L3 oracle bounds how much is knowledge.
- **Parameter:** 1 step. **Property violated:** comparability of published numbers across defenses at different lattice levels.
- **Setup:** N-BaIoT, `N = 20`, `β = 0.20`, defenses {FedAvg L0, trimmed-mean L1, FLTrust-style L2, oracle-β trimmed-mean L3}.
- **Capability required:** F1 `m=4`, F2 byzantine, F3 gray-box.

```
ATTACK TRACE (beta = 0.20, sign-flip + IPM)
  L0 FedAvg               EA_min = 0.41
  L1 trimmed-mean         EA_min = 0.88
  L2 FLTrust-style        EA_min = 0.95   <-- requires clean server labels
  L3 oracle-beta trimmed  EA_min = 0.97   <-- UPPER BOUND, not achievable
  Certified (Alg 2, L1)   CA     = 0.09
  Reading: the 0.95 headline is purchased with L2 knowledge; the honest
           deployable comparison is L1 = 0.88; and NONE of these is a
           guarantee -- the only guarantee available is 0.09.
```

### 10.4 Scenario → instrument map

| Scenario | Primary metrics | Algorithms | Severity class tested | Contrast |
|---|---|---|---|---|
| 1 (flagship) | `CA`, `EA_min`, `Γ`, `MC_het`, `MC_adv`, `β*` | 1,2,4,6,7 | S2, S3 | #1, #2, #3 |
| 2 | `CERT-WRONG`, margin distribution | 1,2 | S4 | exploratory |
| 3 | `EA_min` by lattice level | 1,8 | — | exploratory + Thrust A |

---

## 11. Evaluation design

### 11.1 Staged pathway

- **Stage 0 — Substrate.** Acquire N-BaIoT (per-device files) and IoT-23 (per-capture, device named in README); CICIoT2023 for attack-class coverage only (C1). Build `𝔇`, household compositions, `Π_dev`. **Measure** `S_JS`, `S_dev`. Publish partitions. *Exit:* partitions reproducible from a seed + the raw captures.
- **Stage 1 — Baseline competence.** Centralized and FedAvg accuracy at `β = 0` on `Π_dev` and on IID. Establish `τ_triv` per dataset. *Exit:* FL accuracy within a predeclared 5 points of centralized, else the substrate is too hard and the certification question is moot.
- **Stage 2 — Empirical robustness.** `𝒜tk` = {label-flip, sign-flip, Gaussian, IPM, ALIE, backdoor-trigger} × defenses (Alg 8) × `β ∈ {0,.05,.10,.20,.30,.40}`. Produces `EA_min`.
- **Stage 3 — Certification. ⟵ GATE G1 EVALUATED HERE.** Algorithm 2 (exact where possible) and Algorithm 3. Produces `CA`, the abstain breakdown, `MC_het`, `MC_adv`.
- **Stage 4 — Gap and frontier.** Algorithm 7: `Γ(β,S)`, `β*(S)`, `R_lit \ R_hon`.
- **Stage 5 — Skew sweep and necessity.** Sweep near-IID → `S_real`; Algorithm 4 matched-Dirichlet control; Algorithm 5 leave-one-device-out.
- **Stage 6 — Systematization overlay.** Place `R_lit` from Thrust A onto the `(β,S)` plane; produce the flagship figure.

### 11.2 Baselines

| Baseline | Level | Role |
|---|---|---|
| FedAvg | L0 | no-defense reference |
| Krum, coord-trimmed-mean, median, norm-clipping | L1 | standard deployable robust aggregation |
| FLTrust-style, probe/trust-score | L2 | the literature's strong-but-assumption-heavy regime |
| oracle-β trimmed-mean | L3 | **UPPER BOUND**, labelled as unachievable in every table |
| **`f_triv` — the constant majority-class predictor** | — | **THE MANDATORY HARDEST BASELINE** |

> **Why `f_triv` is the hardest baseline and not a joke.** It is **certifiably robust to every β**, requires no federation, no defense, and no data. Any certified result that does not beat it is strictly worse than doing nothing. Every certified number in this paper must clear `τ_triv`, and the paper reports `CA − τ_triv`, never `CA` alone. Most of the risk of this project producing a hollow-looking positive result is eliminated by this single baseline.

### 11.3 Metrics

Exactly those in §1.5. `CA` and `Γ` always reported against `τ_triv`; severity class (§9.2) printed per cell; abstain three-way breakdown per cell; capability record attached per cell.

### 11.4 Statistics

- **Exact arms** (`K = C(N,k)` full enumeration): the certificate is a deterministic combinatorial fact. **Reported with no interval and no test** — there is no sampling error to quantify. Stated explicitly in captions so a reviewer does not read missing error bars as sloppiness.
- **Sampled arms** (`K < C(N,k)`): Clopper–Pearson one-sided bounds at `α = 0.001` inside Algorithm 2; `CA` reported at the conservative endpoint. **Never a bare point estimate.**
- **Paired comparisons** (contrast #2, #5): same partition seed, same train seed, same subsample seed across arms; paired test across `R = 10` seeds; report the paired difference with a 99% CI.
- **Mixed-effects model** for the skew sweep (contrast #4): `CA ~ β * S_JS + (1 | partition_draw) + (1 | train_seed)`. Random effects on **partition draw** and **training seed** because both are resampled and neither is of interest — treating partition draws as fixed would understate uncertainty in exactly the direction that flatters the headline.
- **Held-out splits:** test flows are held out **by time within device** where timestamps exist (IoT-23 `ts`, N-BaIoT file order), never by random row shuffle — random splits leak within-burst correlation and inflate every number in this design.
- **Preregistered contrast set:** §9.4. Exploratory findings are labelled exploratory in the text, not merely in a footnote.

### 11.5 Key ablations

| # | Ablation | Question it answers |
|---|---|---|
| A1 | matched-skew Dirichlet (Alg 4) | is device structure necessary, or just skew magnitude? |
| A2 | leave-one-device-out (Alg 5) | is the collapse structural or one device's artifact? |
| A3 | `k` sweep {3,4,5,6,8} | is collapse an artifact of subsample size? |
| A4 | `K` sweep incl. exact | is it a Monte-Carlo artifact? |
| A5 | `N` sweep {10,12,16,20} | how does `p_clean` geometry drive `β*`? |
| A6 | model capacity {MLP small, MLP large, autoencoder} | is it a capacity artifact? |
| A7 | binary vs multi-class `𝒴` | does `τ_triv` shift change the vacuity verdict? |
| A8 | budget: equal-total vs equal-per-model | is any effect merely budget (C3)? |
| A9 | F4 on/off (seed known) | how much of the certificate rests on seed privacy? |

### 11.6 Compute envelope — a design constraint, not a footnote

**Hardware: one MacBook Pro M4, 24 GB unified memory, PyTorch MPS. No cluster, no GPU tier, no testbed, no data collection.** Every parameter above was chosen to fit this.

| Item | Setting | Why |
|---|---|---|
| features | flow-level CSV, `d ≈ 20–46` | no packet-level processing; no PCAP re-extraction (C1) |
| model | MLP[64,32] ≈ 5–8k params; small AE | seconds per client-round on MPS |
| `N`, `k` | 20, 5 | `C(20,5)=15,504` — exact enumeration reachable |
| `K` | 500 sampled / exact where affordable | exact preferred: cheaper *and* stronger (§1.6) |
| `T`, `E` | 30, 2 | converges on flow features |
| rows | ≤ 2M subsampled, stratified | fits memory with pandas/polars |
| per-cell budget | wall-clock cap recorded in capability record | prevents silent budget inflation (C3) |
| storage | ≤ 54 GB free — **CICIoT2023 PCAPs (~0.5 TB) are out of reach**, reinforcing C1 | |

Sequencing rule: **Stages 0–3 on N-BaIoT first** (smallest, cleanest device attribution). Only after G1 resolves does IoT-23 and the Stage-5 sweep run.

---

## 12. Detailed paper outline

Written for the strongest ceiling (Exit 1). **Gate exit re-centers §5 of the paper**, as noted.

| § | Title | Thrust | Driving question | Primary figure/table |
|---|---|---|---|---|
| 1 | Introduction | — | What does a robust federated IDS actually guarantee? | Fig 1: `R_lit \ R_hon` teaser |
| 2 | Background: federated IDS and its threat model | — | What is the threat class, and what is `WCA`? | Tab 1: notation + threat classes |
| 3 | What the defenses guarantee: a systematization | A | What is the quantifier structure of the field's claims? | **Tab 2: defense-wall inventory** (threat model, `𝒜tk`, β grid, datasets, lattice level, provable guarantee) |
| 4 | Device-derived non-IID partitions | C | Is smart-home skew structurally different, and is that necessary? | Fig 2: measured `S_JS`/`S_dev`, device-derived vs matched Dirichlet |
| 5 | Transferring certification to federated anomaly detection | B | What bound can be stated at all here? | Alg 2/3 + Fig 3: `CA` vs `β` against `τ_triv` — **this section re-centers on the gate exit** |
| 6 | Certified accuracy and the certification gap | B | How far is provable from demonstrated? | **Fig 4 (flagship): `Γ(β,S)` surface with `R_lit` overlaid** |
| 7 | How the bound degrades with skew | B | Is there a collapse threshold below real-world skew? | Fig 5: `β*(S)` curve + HICC decomposition (`MC_het` vs `MC_adv`) |
| 8 | What certification does not cover | — | What are we *not* claiming? | Tab 3: the 11 non-guarantees (§5) |
| 9 | Discussion: what the field can honestly claim | A+B | What should a deployer and a reviewer take away? | Tab 4: claim template, filled |
| 10 | Related work | — | Convergence vs privacy vs robustness | Tab 5: classification of every theoretical hit |
| 11 | Limitations and artifact | — | | capability-record schema |

---

## 13. The arc and the gate

### The acts

- **Act I (floor, measurement):** the systematization (C-A) + the first certified numbers in this setting (C-B) + the gap (C-C). **Act I is the paper's floor.** It stands whatever the certificate says, because a certificate of zero is a measurement, and "the field's certified-guarantee set is empty" is a fact about the literature, not about our experiment.
- **Act II (ceiling, hypothesis):** HICC (C-D) and device-structure necessity (C-E). These can fail.

### Gate G1

> **G1 — Certified accuracy at deployment-relevant β on a real device-derived partition.**
> Run Stages 0–3 on N-BaIoT, `N = 20`, `k = 5`, exact-or-`K=500`, `β = 0.10`, `Π_dev` at measured `S_real`. Compute `CA(0.10, S_real)` against `τ_triv`.
>
> **Build nothing below Stage 3 until G1 resolves.** No skew sweep, no full attack grid, no manuscript figures.

| Exit | Condition | Which paper gets written | Which section re-centers | Claim ceiling |
|---|---|---|---|---|
| **Exit 1 — GO** | `CA(0.10, S_real) > τ_triv + 0.10` (S0) | The **full paper**: systematization + transfer + gap + skew-degradation law. Act II is live; HICC is tested, not assumed. | §5 presents a *working* certificate; §7 carries the headline. | "Here is what provably survives, here is where it stops, here is the region the field claims beyond it." |
| **Exit 2 — NARROW** | `τ_triv < CA(0.10) ≤ τ_triv + 0.10` (S1), **or** S0 only at `β ≤ 0.05` | The **frontier paper**: certification works, but only in a regime far below where the field publishes. Headline becomes `β*(S)` and the `R_lit \ R_hon` map. C-D survives in weakened form. | §5 re-centers on *the boundary of applicability*; §7 becomes the main result; §6's gap is reported but is no longer the sole headline. | "Certification is possible here but only at adversary fractions an order of magnitude below what is evaluated." |
| **Exit 3 — PIVOT** | `CA(0.10) ≤ τ_triv` (S2), **or** `CA(0, S_real) ≤ τ_triv` (S3, collapse with no adversary) | The **negative-result / measurement paper**, per decision **D2**: the field makes robustness claims in a regime where no current certification technique can provide any guarantee. C-A, C-B, C-C carry the paper; C-D becomes the *explanation* (via `MC_het`) rather than a hypothesis under test. **Do not manufacture a positive result.** | §5 re-centers on *why* certification fails here (margin decomposition), and §7 becomes a negative characterization: the vacuity frontier lies below realistic skew. | "No existing certification technique yields a non-trivial guarantee at the operating points this field publishes — and here is the mechanism." |

**Where the current evidence leans.** The pre-registered expectation (RKA `jrn_01M0EE7W6CMRCZF7CQDCGEP2N3`, F6) is that bounds under realistic household skew are far weaker than empirical robustness and **possibly vacuous at 10–40% malicious**. Read against FLCert's own reported regime — certified accuracy demonstrated at `m/N = 2%` on a homogeneous image benchmark — while this field routinely evaluates 10–40% under structural heterogeneity, the geometry of `p_clean = C(N−m,k)/C(N,k)` alone leans toward **Exit 2 or Exit 3**. That expectation is recorded *before* the run so the framing cannot be retrofitted, and Exits 2 and 3 both produce a publishable paper by construction.

### Floor / ceiling / which paper gets written

- **Floor:** a systematization proving the field's certified-guarantee set is empty, plus the first measured certified accuracy and certification gap for federated IoT intrusion detection. Publishable at Exit 2 or 3.
- **Ceiling:** a skew-degradation law — `β*(S)` — that tells a deployer, from a measurable property of their federation, the largest adversary fraction they can certify against. Publishable only at Exit 1.
- **Which paper gets written:** decided by G1, in advance, by the table above — not after seeing the numbers.

---

## Appendix A — Single most likely reason this design fails

**The load-bearing assumption is that a subsampling certificate can be non-vacuous at all when `k` clients must jointly cover a device catalog of size `M`.** If `k < M` and household device sets are near-disjoint, then *every* ensemble member is structurally blind to some device class, `MC_het → 1` at `β = 0`, and `CA ≤ τ_triv` before the adversary acts — Exit 3 by geometry rather than by any property of smart homes, adversaries, or the literature. In that case the "certification gap" would be an artifact of the certification *method* rather than a finding about the *field*, and C-C would be substantially weakened.

**Detection:** this is exactly what Algorithm 6 measures (`MC_het` at `β = 0`) and what severity class **S3** names, and it is why S3 is a distinct exit condition rather than being folded into S2.
**Mitigation if it occurs:** ablation A3 (`k` sweep) and A5 (`N` sweep) determine whether any `(N,k)` admits a non-vacuous certificate; if none does, the honest claim becomes a statement about *subsampling certification's applicability limit under structural heterogeneity* — still a real result, but a narrower one, and it must be titled as such rather than as a claim about FL-IoT-IDS in general.

---

## Appendix B — M1 feasibility-probe results (measured 2026-08-19)

**These are MEASURED values from the M1 gate probe, not targets** — the one place in this
document where numbers are observations. They are also **not paper results**: the probe used
`K=100` *sampled* (not exact enumeration), one seed, one dataset, no attack suite, and no
matched-skew control. They are a go/no-go signal. Stage 3 and Stage 5 must re-derive them
under the full design before anything is claimed.

Substrate: IoT-23, 10 real device captures, 166,532 flows, 31 features, `N=20`, MLP[32,16],
PyTorch MPS, single M4. Time-ordered 80/20 split within device. **`τ_triv = 0.7300`.**

### B.1 The combinatorial ceiling (analytic, exact)

Certification requires `margin > 2(1 − p_clean)` while `margin ≤ 1` always, so it is
**impossible** whenever `p_clean ≤ ½`:

> **`β_cert < 1 − 2^(−1/k)`, independent of `N`, the data, and the model.**

| k | 1 | 2 | 3 | 5 | 8 | 10 | 20 |
|---|---|---|---|---|---|---|---|
| ceiling | 0.500 | 0.293 | 0.206 | 0.129 | 0.083 | 0.067 | 0.034 |

`β_geo(N,k)` is flat in `N`: 0.120 at `N=50`, 0.129 at `N=1000` for `k=5`. **More clients
does not help.** Verified against the probe: at `N=20, k=5`, `CA = 0.9794` at `β=0.10`
(threshold 0.8947) and **exactly 0** at `β=0.20` (threshold 1.4365 > 1).

This upgrades §1.4's HICC claim: at high `β` the limit is not looseness but a **provable
impossibility** for this certification family. It is the sharpest statement in the project.

### B.2 The pincer (measured)

> **SUPERSEDED IN PART — read B.4b first.** The `k=1` device-derived collapse below was a
> single-seed artifact and did not replicate across seeds 0/1/2.

| k | β_geo | IID acc / margin / β\* | device-derived acc / margin / β\* |
|---|---|---|---|
| 1 | 0.450 | 0.9827 / 0.9970 / **0.40** | 0.2700 / 0.3958 / **0.00** |
| 2 | 0.250 | 0.9826 / 0.9973 / 0.20 | 0.9243 / 0.5362 / 0.05 |
| 3 | 0.150 | 0.9827 / 0.9980 / 0.10 | 0.9245 / 0.6872 / 0.05 |
| 5 | 0.100 | 0.9826 / 0.9982 / 0.10 | 0.9681 / 0.8936 / **0.10** |
| 8 | 0.050 | 0.9828 / 0.9981 / 0.05 | 0.9806 / 0.9269 / 0.05 |

`S_JS`: IID 0.0009, device-derived 0.8456.

- **Upper jaw (analytic):** certifying at β = 0.30–0.40 *requires* `k ≤ 2`.
- **Lower jaw (empirical):** at `k=1` under device skew the ensemble scores **0.2700**,
  *below* `τ_triv = 0.7300` — worse than the constant predictor. At `k=2`, mean margin has
  already fallen 0.997 → 0.536.
- Under mild/IID skew small `k` is **free** (margin ≈ 0.997 at every `k`), so `β*` is set
  purely by the geometric ceiling and reaches 0.40. Under device-derived skew the best `β*`
  across **all** `k` is **0.10**.

**Device-derived heterogeneity cuts the certifiable malicious fraction 4× (0.40 → 0.10), and
no `k` reaches the 20–40% band the literature routinely evaluates.** HICC is supported in the
small-`k` regime: `MC_het = 0.604` at `k=1`, i.e. 60% of the margin is consumed by
heterogeneity *before any adversary acts*.

**Not yet established:** this contrasts device-derived against **IID**, not against a
Dirichlet control **matched on `S_JS`**. Necessity (Algorithm 4) remains open — see B.3.

### B.3 Gate G1 outcome and two design corrections

**G1 → Exit 2 (NARROW).** Not PIVOT: certification is non-vacuous in the easy case
(`CA(0.10) = 0.9823` vs `τ_triv = 0.7300`, and `β*=0.40` at `k=1`), so RQ2 is answerable. Not
unqualified GO: under device-derived skew `β*` tops out at 0.10, below where the field
publishes. The headline becomes the **frontier** — `β*(S)` and `R_lit \ R_hon`.

Two corrections were forced by building the pipeline, both affecting load-bearing machinery:

**(i) Algorithm 4's control was wrong as specified.** Label-Dirichlet skews only the *label*
marginal — every client still sees every device — so it reaches high `(device × label)` `S_JS`
by concentrating labels, a structurally different kind of skew, and it matches a
device-derived partition poorly on `S_dev` (0.43 vs 0.82 target). The control must be a
**device-Dirichlet** (`dirichlet_device_partition`), allocating each *device's* rows by
Dirichlet, which moves the device axis directly. Label-Dirichlet is retained only as a
secondary control. Had this not been caught, M3 would have produced a broken necessity test
and the D1 claim would have rested on a confounded comparison.

**(ii) The skew instrument was non-monotone.** `S_JS` counted empty clients via an artificial
uniform histogram, which *lowered* mean divergence — so `S_JS` was **not** monotone in `α`
(α=1e-3 scored below α=1e-1), and any monotone search over `α` would have silently converged
to the wrong control. Fixed: empty clients are excluded from the pairwise average, partitions
that starve a client are **rejected rather than scored**, and Algorithm 4 uses a log-grid scan
with local refinement instead of a binary search. `S_JS` is now monotone in `α`.

**A residual limitation, reported rather than hidden.** Under the no-starved-client
constraint, Dirichlet cannot always reach device-derived `S_JS` exactly (toy: 0.686 vs 0.757).
Real households own *few* devices while each device contributes *plenty* of traffic, so
device-derived partitions achieve higher skew without starving anyone than Dirichlet can. The
runner therefore emits `control_valid = |S_JS(dev) − S_JS(matched)| ≤ 0.05` and **necessity
must not be reported when it is false** — the comparison would be confounded by skew
magnitude, which is precisely what Algorithm 4 exists to rule out.

### B.4 Dataset verdict (T6)

| dataset | access | per-device attribution | role |
|---|---|---|---|
| IoT-23 | direct, no form | **CONFIRMED** — one device/capture, model named in README, single dominant source IP | partition substrate |
| N-BaIoT | UCI stream unreliable (no `Content-Length`, no ranges; 6 truncations at 402–753 MB) | structural (9 named devices) | partition substrate, pending a mirror |
| CICIoT2023 | CIC now gates behind a registration form; unauthenticated HF mirror `bencorn/CIC-IoT-2023` exists | **NOT RECOVERABLE** from the published CSVs | attack-class coverage **only** |

CICIoT2023's 39 published features carry no MAC, no IP, no device label; the authors'
`Feature_extraction.py` tracks source IPs internally but never emits them, and the tree is
organised by attack type. Recovery needs re-extraction from ~0.5 TB of PCAP against
`README_Victims_List.pdf` — infeasible under D3 (54 GB free), and attack captures are
dominated by attacker rather than victim-device traffic. **This invalidates D1 as literally
worded** and is raised as blocking checkpoint `chk_01M0EH65WGYNBDK9H4MWQQT2JA`. It does *not*
force a synthetic partition: IoT-23 attribution is confirmed and carried the entire probe.
Recommended narrowing is to build device-derived partitions from IoT-23 + N-BaIoT and demote
CICIoT2023 to attack-class coverage — the premise requires *real* device-derived partitions,
not specifically CICIoT2023's 105 devices.

### B.4b CORRECTION (2026-08-20): the k=1 collapse did not replicate

The M1 probe used a **single partition seed**. A multi-seed rerun (seeds 0/1/2, full
133,222-row training set, `tau_triv = 0.729961`) retracts B.2's sharpest empirical claim.

| kind | k | β_geo | ens_acc (s0/s1/s2) | margin (s0/s1/s2) | β\* (s0/s1/s2) |
|---|---|---|---|---|---|
| device-derived | 1 | 0.450 | 0.888 / **0.270** / 0.952 | 0.433 / 0.403 / 0.506 | 0.10 / 0.00 / 0.20 |
| device-derived | 2 | 0.250 | 0.980 / 0.924 / 0.981 | 0.571 / 0.249 / 0.586 | 0.10 / 0.00 / 0.10 |
| device-derived | 3 | 0.150 | 0.979 / 0.925 / 0.980 | 0.724 / 0.424 / 0.683 | 0.10 / 0.00 / 0.10 |
| device-derived | 5 | 0.100 | 0.979 / 0.968 / 0.983 | 0.812 / 0.638 / 0.781 | 0.05 / 0.05 / 0.05 |
| device-derived | 8 | 0.050 | 0.980 / 0.981 / 0.980 | 0.844 / 0.770 / 0.824 | 0.05 / 0.00 / 0.05 |
| IID | 1 | 0.450 | 0.983 / 0.983 / 0.982 | 0.996 / 0.996 / 0.997 | 0.40 / 0.40 / 0.40 |

**The 0.2700 figure in B.2 was seed 1** — one draw of three. The median is 0.888 and seed 2
reaches 0.952 with `β* = 0.20`. **"k=1 under device skew is worse than the constant
predictor" DOES NOT REPLICATE and must not appear in the paper.**

**Why the variance is structural, not noise.** At `k=1` each ensemble member trains on
exactly *one* household, so competence depends entirely on which device mixtures the draw
produced. This is a real property of small-`k` subsample certification under device-derived
partitioning. **A point estimate at `k ≤ 2` is uninterpretable**; every small-`k` result needs
multiple partition draws with an interval. §11.4's paired-seed requirement is therefore
promoted from good practice to a correctness condition, and `R = 10` seeds (not 3) is the
target for any reported small-`k` number.

**What survives and is the claim to carry forward:**

1. The ceiling `β_cert < 1 − 2^(−1/k)` is **analytic** and untouched.
2. Device-derived skew reduces certifiable β relative to IID at **every** k. Sharpest
   contrast: IID `k=1` gives `β* = 0.40` on all three seeds; device-derived `k=1` gives
   0.10 / 0.00 / 0.20.
3. **No device-derived seed at any k reached the 0.30–0.40 band the literature evaluates.**
   Maximum observed device-derived `β* = 0.20`, on one seed at `k=1`.
4. Mean vote margin is far lower under device-derived skew (0.25–0.84) than IID (~0.996) at
   matched k, so heterogeneity does consume most of the certification budget before any
   adversary acts — **the HICC *direction* holds even though the specific k=1 collapse does
   not.**

Still open: this contrasts device-derived against **IID**, not against a skew-**matched**
Dirichlet control. Necessity (Algorithm 4) is required before attributing any of (2)–(4) to
device *structure* rather than skew *magnitude*.

### B.5 What this changes in the design above

- §1.4 (HICC) gains a **provable** upper jaw: `β_cert < 1 − 2^(−1/k)`. HICC is now a
  *tradeoff frontier* between `k` and certifiable `β`, not only a collapse.
- §11.5 ablation **A3 (`k` sweep) is promoted from ablation to primary experiment** — it *is*
  the tension.
- §13's gate resolves to **Exit 2**, so §5 of the paper re-centers on the boundary of
  applicability and §7 (`β*(S)`) becomes the main result, exactly as the exit table specified
  in advance.
- Appendix A's predicted failure mode — "`k < M` with near-disjoint household device sets
  drives `MC_het → 1` at `β = 0`" — is **partially observed** at `k=1` (`MC_het = 0.604`,
  accuracy below `τ_triv`). Ablations A3/A5 must therefore determine whether *any* `(N,k)`
  admits a non-vacuous certificate at deployment-relevant β. On current evidence the answer
  is no for `β ≥ 0.20`, which is a result about **subsample certification's applicability
  limit under structural heterogeneity** and must be titled as such rather than as a claim
  about FL-IoT-IDS in general.
