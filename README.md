# FedHomeGuard

Certified robustness, and the **certification gap**, for federated IoT intrusion detection.

The FL-IoT-IDS literature *demonstrates* robustness it cannot *prove*. This repo measures
the distance between the two under **device-derived** smart-home heterogeneity, and maps the
region where the field claims robustness and no certificate can currently support any.

Design: [`research_design_detailed.md`](research_design_detailed.md) — read it first; every
module below implements a numbered algorithm from it.

RKA project `prj_01M0EE73RTCAK0JNGD4SY4A1Y2`.

---

## Status

- **M1 (scoop gate + feasibility probe): complete.**
- **M2/M3 experiments: complete** (k-sweep across seeds, empirical arm, certification, gap, skew sweep). Necessity rerun in progress.
- **Two blocking checkpoints open:**
  - `chk_01M0EH65WGYNBDK9H4MWQQT2JA` — D1 / CICIoT2023 attribution.
  - `chk_01M0GCM8V8F9GJJSDHJ2Z0C8WC` — gate G1 is degenerate as pre-registered (see below).

### The central result

Certification gap `Γ = EA_min − CA`, computed **within** each partition. `EA_min` = max over
5 defenses of min over 5 attacks; `CA` = best certified accuracy over `k ∈ {1,2,3,5,8}`, median
across seeds 0/1/2. IoT-23, N=20, `τ_triv = 0.7300`.

| β | IID `EA_min` | IID `CA` | **Γ_IID** | dev `EA_min` | dev `CA` | **Γ_dev** |
|---|---|---|---|---|---|---|
| 0.00 | 0.9825 | 0.9825 | **0.0000** | 0.9826 | 0.9786 | **0.0040** |
| 0.05 | 0.9820 | 0.9820 | **0.0000** | 0.9801 | 0.9517 | **0.0284** |
| 0.10 | 0.9815 | 0.9820 | **−0.0005** | 0.9808 | 0.8319 | **0.1489** |
| 0.20 | 0.9819 | 0.9809 | **0.0010** | 0.9788 | 0.6829 | **0.2959** |
| 0.30 | 0.9817 | 0.9790 | **0.0027** | 0.9258 | 0.2351 | **0.6907** |
| 0.40 | 0.9808 | 0.9776 | **0.0033** | 0.4517 | 0.0617 | **0.3900** |

**Under IID the certificate is tight — the gap never exceeds 0.0033 anywhere, including β=0.40.
Under device-derived skew the same certificate, model, budget and attack set gives a gap of
0.296 at β=0.20 and 0.691 at β=0.30. The gap is a heterogeneity phenomenon, not a property of
the certification method.**

(`Γ = −0.0005` at IID β=0.10 is within noise: the empirical arm is single-seed while `CA` is a
median over three. Not a soundness violation; the seed mismatch should be removed before
publication.)

### The combinatorial ceiling

Certification requires `margin > 2(1 − p_clean)` while `margin ≤ 1` always, so it is impossible
once `p_clean ≤ ½`:

> **β_cert < 1 − 2^(−1/k)**, *independent of N, the data, and the model.*

`k=1 → 0.500 · k=2 → 0.293 · k=3 → 0.206 · k=5 → 0.129 · k=8 → 0.083 · k=20 → 0.034`

Under IID, `β*` tracks this ceiling exactly at every k (0.40/0.20/0.10/0.05/0.05 vs β_geo
0.45/0.25/0.15/0.10/0.05) — only combinatorics binds. Under device-derived skew `β*` stops
tracking it at `k ≤ 3`: heterogeneity binds first. Max device-derived `β*` over all k and
seeds is **0.20**; IID reaches **0.40**.

### Why gate G1 as written is degenerate

G1 pinned `k=5`, where `β_geo(20,5) = 0.10` exactly — so the gate's target β sits *on* the
ceiling and demands margin > 0.8947. IID's margin is 0.864, so **the easy case fails the gate
too, 0/3 seeds**. The literal verdict is PIVOT; evaluated over k (which ablation A3 already
required) device-derived clears τ at `k ≤ 3` on 2/3 seeds → NARROW. Escalated rather than
resolved unilaterally.

### Other results worth reporting

- Under IID, robust aggregation genuinely works where the field claims it: `median` holds
  0.9808–0.9825 at **every** β including 0.40. The literature's empirical claims are not wrong
  in the regime they are usually tested in — they are untested in the regime that matters.
- **Krum, the canonical Byzantine-robust rule, is the worst performer under device-derived
  skew**, collapsing to 0.2698 for β ≥ 0.20 (worst cell Krum/IPM).
- The best `k` shifts with β under device skew (8 → 3 → 1 as β grows): as the adversary budget
  grows, the certifiable configuration is forced toward small k, where heterogeneity costs most.
- M1's reported k=1 collapse (acc 0.270, below `τ_triv`) **did not replicate**: across seeds it
  is 0.888 / 0.270 / 0.952. At k=1 each ensemble member trains on one household, so a point
  estimate at `k ≤ 2` is uninterpretable. Seed count raised to 10 for any reported small-k number.

---

## Install

```bash
pip install -e .            # editable; adds the `fedhomeguard` console script
pip install -e '.[dev]'     # + pytest
pytest -q                   # 43 tests, ~2s
```

Hardware assumption (decision D3): **one MacBook Pro M4, 24 GB, PyTorch MPS.**
No cluster, no GPU tier, no testbed, no data collection.

## Data

```bash
python scripts/fetch_data.py --dataset iot-23        # WORKS: verified per-device
python scripts/fetch_data.py --dataset n-baiot       # flaky upstream, see below
python scripts/fetch_data.py --dataset ciciot2023    # HF mirror, attack-class coverage ONLY
```

| dataset | access | per-device attribution | role |
|---|---|---|---|
| **IoT-23** | direct, no form | **CONFIRMED** — one device per capture, model named in README, single dominant source IP | partition substrate |
| **N-BaIoT** | UCI stream is unreliable* | structural (9 named devices) | partition substrate (pending) |
| **CICIoT2023** | CIC now gates behind a registration form; use the unauthenticated HF mirror `bencorn/CIC-IoT-2023` | **NOT RECOVERABLE** | attack-class coverage **only** |

\* UCI serves the archive as a dynamically generated stream with no `Content-Length` and no
range support, so resume is impossible; six attempts truncated at 402–753 MB. Logistics, not
science. Fallbacks: a Kaggle mirror with `~/.kaggle/kaggle.json`, or download the per-device
CSVs by hand into `data/raw/nbaiot/<Device>/`.

**CICIoT2023 cannot drive a device partition.** Its published CSVs are 39 aggregate features
with no MAC, no IP, no device label; the authors' own `Feature_extraction.py` tracks source
IPs but never emits them. `fedhomeguard.data.ciciot_device_ids` raises rather than letting a
run silently proceed on a fiction.

## Running

Add `--smoke` to any stage for a seconds-long wiring check (N=8, K=12, T=2) —
**smoke output is not a result.**

```bash
fedhomeguard --stage 0 --config configs/stage0_substrate.yaml      # partitions + skew
fedhomeguard --stage 1 --config configs/stage1_baseline.yaml       # competence, tau_triv
fedhomeguard --stage 2 --config configs/stage2_empirical.yaml      # attacks x defenses -> EA_min
fedhomeguard --stage 3 --config configs/stage3_certification.yaml  # GATE G1 -> CA
fedhomeguard --stage 4 --config configs/stage3_certification.yaml  # gap: Gamma, R_lit \ R_hon
fedhomeguard --stage 5 --config configs/stage5_skew.yaml           # skew sweep + necessity
```

**Stage 3 is gate G1. Build nothing below it until it resolves.** The runner prints one of
`EXIT_1_GO` / `EXIT_2_NARROW` / `EXIT_3_PIVOT`, decided by thresholds fixed in the design
*before* any run.

### Estimated wall clock (M4, IoT-23, N=20)

| stage | config | ≈ FL runs | ≈ time |
|---|---|---|---|
| 0 | substrate | 0 | seconds |
| 1 | baseline | 1 | ~10 s |
| 2 | empirical | ~130 | ~10–15 min |
| 3 | certification (per k) | 100 | ~2 min |
| 3 | k-sweep `stage3_k{1,2,3,5,8}` | 500 | ~10 min |
| 5 | skew + necessity + LODO | ~1500 | **~1.5–3 h** |

Stage 5 is the expensive one; run it last and overnight.

## Layout

```
research_design_detailed.md   the design: formal model, algorithms, gate, predeclared catalog
configs/                      one YAML per experiment arm
src/fedhomeguard/
  config.py       typed config; every run fully described by a Config
  data.py         loaders + featurization; CICIoT2023 attribution guard
  partition.py    device-derived / IID / Dirichlet; skew instrument; Alg 4, Alg 5
  models.py       MLP, autoencoder-as-classifier
  fl.py           Alg 1 FLRun (deterministic), attacks+defenses wired in
  attacks.py      label_flip, sign_flip, gaussian, IPM, ALIE, backdoor + F2/F3 gates
  defenses.py     FedAvg, Krum, trimmed-mean, median, norm-clip, FLTrust(L2), oracle(L3)
  certify.py      Alg 2 subsample, Alg 3 smoothing, beta_geo, severity classes
  metrics.py      tau_triv, EA_min, Gamma, honest/claim regions
  capability.py   machine-readable capability record + the 11 non-guarantees
  runner.py       stage orchestration + CLI + gate verdict
scripts/fetch_data.py         dataset acquisition
tests/                        43 tests; the certification math is pinned hardest
```

## Invariants the code enforces (so a run cannot quietly cheat)

- **`τ_triv` is the mandatory floor.** A constant predictor is certifiably robust to *every*
  β. Any `CA ≤ τ_triv` is reported `S2_vacuous`, and `CA` is always shown against it.
- **Class balance can't fake it.** Every certified result is also reported on a balanced test
  subsample (`τ=0.5`), so a vacuity verdict is never an artifact of imbalance.
- **The observability lattice is checked.** Declaring FLTrust as L1 raises; `oracle_trimmed`
  is tagged `is_upper_bound_not_achievable` and excluded from `EA_min`.
- **Attack capability is checked.** IPM/ALIE need honest updates and raise under `black_box`.
- **`Γ < 0` is a bug signal, never a finding** — it means an unsound certificate or an attack
  outside the declared class.
- **`EA_min` = max over defenses of min over attacks** — the literature's own claim shape.
- **Empty clients are rejected, not scored** — they made `S_JS` non-monotone in α and would
  have broken Algorithm 4's search.
- **Every result ships a capability record** listing powers, budget, seeds, and the 11
  explicit non-guarantees. Anything not in the record was not assumed.
