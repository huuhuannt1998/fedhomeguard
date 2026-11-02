# JS02 (federation size) and JS03 (member capacity): 30-draw extensions of E10 and E2

Predeclared 2026-10-16 (UTC), before either run. Round: JISA preparation (feedback item M4; triage F14).

## Why

- **E10 (`results/canonical/e10b_N{10,50}_*.jsonl`, 2026-09-03):** 3 partition draws each at N = 10 and N = 50
  (seeds 0-2). N = 20 has 30 draws (e5f, seeds 10-39).
- **E2 (`results/canonical/e19_large_*.jsonl`, 2026-09-03):** 3 draws of the 128-64-32 member (9.1x the
  parameters).
- **Gap:** both are too thin to report as a sensitivity analysis in a journal.

JS02 and JS03 rerun them on the same 30 seeds as e5f, with nothing else changed.

## JS02: federation size

- **Command:**
  `exp_e2.py --partition {iid, device_derived} --pseed 10..39 --k 1 [2 at N=10] --betas 0 0.05 ... 0.50
  --N {10, 50} --clean-only --k-caps "1:N,2:C(N,2) at N=10"`.
- **Outputs:** `results/jisa/js02_N{10,50}_{iid,device_derived}.jsonl`.
- **Predictions:**
  - J2a: IID beta* equals the exact ceiling beta_geo(N,1) on at least 28 of 30 draws at each N. The ceiling is
    0.45 at N = 10 and 0.48 at N = 50, read on the grid as the largest grid value below the ceiling.
  - J2b: the device-derived median beta* at k = 1 lies within one grid step of N = 20's 0.050 at both N; median
    vote margin does not rise with N. Federation size does not rescue device-derived certification.
  - J2c: the device-derived collapse count at beta = 0.20 (k = 1) is within the 95% Wilson interval of N = 20's
    27 of 30 at both N.

## JS03: member capacity

- **Command:**
  `exp_e2.py --partition {device_derived, iid} --pseed 10..39 --k 1 --arch mlp_large --betas 0 0.05 ... 0.50
  --clean-only --k-caps "1:20"`.
- **Outputs:** `results/jisa/js03_large_{device_derived,iid}.jsonl`. Compared draw by draw with
  e5f (MLP 32-16) on the same seeds.
- **Predictions:**
  - J3a: per-draw beta* (k = 1) is unchanged on at least 25 of 30 device-derived draws.
  - J3b: median clean ensemble accuracy rises (paired), while median vote margin does not rise by more than 0.05.
    Capacity buys accuracy, not margin.
  - J3c: IID beta* stays at the ceiling on at least 28 of 30 draws.

Each prediction that fails is reported as failed. No threshold changes after the first run.
