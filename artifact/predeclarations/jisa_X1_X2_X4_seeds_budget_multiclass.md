# X1 (member seeds), X2 (step-budget-scaled coverage repair), X4 (8-class device-derived grid)

Predeclared 2026-10-20, before any X1 or X2 run and before the X4 quantities below are computed. Round: JISA
preparation, the experiments the AutoResearchClaw reviews (runs/fedhomeguard-jisa/review-r1, f1-f3) call necessary
(editor items (b)1, (b)2, (b)4; referee items C1, B2, B3, B5). PI go-ahead 2026-10-20 ("Homeprov is waiting now. We
can start this"); scope fixed by the PI on 2026-10-16 ("Necessary + CIC + size/capacity").

Fixed throughout: IoT-23, N = 20, member MLP 32-16, FedAvg 15 rounds of one local epoch (unless X2 says otherwise),
SGD lr 0.05, momentum 0.9, batch 512, exact certification, beta grid 0, 0.05, ..., 0.50, tau_triv = 0.7300,
partition seeds 10-39 (the main grid's). Collapse at (k, beta) = certified accuracy at or below tau_triv.

## X1: member-seed replication

**Why.** Every result uses member seed 0, so training-seed variance is unmeasured (referee C1; editor: "I will not
accept the paper without it").

**Runs.** Member seeds 1, 2, 3 and 4 (seed 0 is the paper's):
- main grid, IID and device-derived (1-3 types), k = 1 and 2: `scripts/exp_e2.py` exactly as for
  `results/canonical/e5f_*.jsonl` (`--pseed 10..39 --k 1 2 --clean-only --k-caps "1:20,2:190"`), plus
  `--member-seed s`, which sets `cfg.fl.seed` (the only change to exp_e2.py; default 0 reproduces e5f). Outputs
  `results/jisa/x1_main_{iid,device_derived}_s{1..4}.jsonl`.
- coverage repair (PB04 arm a, `coverage_repaired_device`, the same partitions), k = 1:
  `scripts/jisa_x_runs.py --arm repair --member-seed s`. Output `results/jisa/x_runs.jsonl`.
- Control, before the seed runs are read: `jisa_x_runs.py` at member seed 0 must reproduce PB04 arm a's per-draw
  beta* on the first 3 repair seeds, and exp_e2.py at `--member-seed 0` must reproduce e5f's on 2 draws. If either
  differs, the runs stop and the deviation is recorded here.

**Predictions** (each at each of the four new seeds):
- **X1a.** Device-derived collapse at beta = 0.20, k = 1: at least 23 of 30 draws (seed 0: 27).
- **X1b.** Coverage-repair collapse at beta = 0.20, k = 1: at most 4 of 30 draws (seed 0: 1); paired on partition
  seeds, the exact McNemar test of main grid against repair gives p < 0.001.
- **X1c.** IID beta* at the ceiling (0.45 at k = 1, 0.25 at k = 2) on at least 28 of 30 draws.
- **X1d.** Device-derived median beta* within one grid step of seed 0's (0.050 at k = 1, 0.150 at k = 2).

**Reported regardless:** the range over the five seeds of the two collapse counts (the member-seed error bar of
27 -> 1); the share of device-derived draws whose collapse status at beta = 0.20, k = 1, is the same at all five
seeds; per-seed median beta* and margin.

## X2: step-budget-scaled coverage repair

**Why.** On the main grid, small households are entangled with one-class ones (151 of 240 one-class households
hold fewer than 1,000 rows), and the volume dial (PB18) showed that small clients lower beta* through their step
budget. The 27 -> 1 repair result could therefore be partly a size or step-budget effect (referee B2; editor (b)2).
Step budgets are equalized rather than sizes, because PB18 found the cause of the small-client effect to be the
step budget, and subsampling households to equal sizes would change their class coverage, the factor under test.

**Runs** (member seed 0, k = 1), `scripts/jisa_x_runs.py`:
- `main_budget`: the 30 main-grid device-derived partitions (P.build, as exp_e2.py);
- `repair_budget`: the 30 coverage-repaired partitions.
- Rule (PB18): client i trains E_i = ceil(14 / b_i) local epochs per round, b_i = ceil(n_i / 512); 14 is the
  number of batches of an equal-size client. Clients of at least 6,657 rows keep E = 1.

**Predictions:**
- **X2a.** Main-grid collapse at beta = 0.20 stays at 20 or more of 30 draws under budget scaling (the coverage
  reading). **Falsifier:** 10 or fewer of 30, in which case the step budget explains most of the main grid's
  collapse and the paper says so.
- **X2b.** Repair collapse at beta = 0.20 at most 4 of 30 under budget scaling.
- **X2c.** Paired on partition seeds, the exact McNemar test of main_budget against repair_budget gives p < 0.001.

**Reported regardless:** the households' row-count distribution in both arms (share under 1,000 rows), the epochs
assigned, the median beta* and margin.

## X4: the 8-class device-derived grid (re-scoring, no training)

**What exists.** `results/canonical/e25_multiclass_{iid,device_derived}.jsonl` (corrected copies via
`aggregate.src`): 30 draws (seeds 10-39), k = 1 and 2, beta in {0, 0.05, 0.1, 0.2, 0.3, 0.4}, one malicious set
each, written 2026-09. The paper prints, from these rows, the IID figures (tau_triv 0.5330, clean accuracy 0.8749,
certified accuracy 0.8714, per-class results) and one device-derived figure (slack 0.7217). **Not computed or read
before this predeclaration:** the device-derived beta*, collapse, and per-family certified detection.

**Computed** by `scripts/jisa_x4_multiclass.py` (writes `results/jisa/x4_multiclass.json`): per draw, beta* (largest
grid beta with certified accuracy above that draw's tau_triv) and collapse at beta = 0.20; per attack family with
test rows, certified detection at k = 1, beta = 0 (`CTR_mal_by_family`).

**Predictions:**
- **X4a.** Device-derived median beta* at k = 1 is at least one grid step below the IID median.
- **X4b.** Device-derived collapse at beta = 0.20, k = 1, on at least 20 of 30 draws.
- **X4c.** For every attack family with test rows, median certified detection at k = 1, beta = 0, is lower under
  device-derived than under IID partitions.

## Rules

Every prediction that fails is reported as failed. No threshold, rule or arm changes after the first run; a rule
that cannot be applied as written is recorded here with its date before results are read. Runs use at most 4
worker processes at reduced priority (HOMEPROV shares the machine).

## Deviation recorded 2026-10-20, before any X4 quantity was computed

`CTR_mal_by_family` in the 8-class rows is wrong: in `exactcert._ids_panel` it counts a row as detected only when
the predicted class equals `mal_label` (1, PartOfAHorizontalPortScan), not when it is any attack class, as the
multi-class branch's own `pred_mal` defines detection. Binary rows are unaffected (there the two coincide), and the
paper uses only `per_class_certified` from the 8-class rows. Fix: the per-family rate uses `pred_mal` in both
branches. Because the stored field cannot be repaired from the rows, X4c is computed from a re-run of the two 8-class
arms at k = 1 (seeds 10-39, the e25 command plus `--k 1`, output `results/jisa/x4_multiclass_k1_{iid,device_derived}.jsonl`)
with the fixed metric. Members are deterministic given their seeds, so the re-run must reproduce the stored rows'
certified accuracy on every (draw, beta); if it does not, X4 stops and this is recorded. X4a and X4b are computed
from the stored rows as predeclared.
