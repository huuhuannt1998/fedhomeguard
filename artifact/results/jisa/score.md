# JISA training round: predeclared predictions scored

## X1: member seeds 0-4 (seed 0 = the paper)

| seed | main collapse | repair collapse | McNemar (main only / repair only, p) | IID at ceiling k=1, k=2 | dd median beta* k=1, k=2 | dd median margin k=1 |
|---|---|---|---|---|---|---|
| 0 | 27/30 | 1/30 | 26 / 0, 2.98e-08 | 30, 30 | 0.050, 0.150 | 0.3457 |
| 1 | 27/30 | 0/30 | 27 / 0, 1.49e-08 | 30, 30 | 0.050, 0.150 | 0.3650 |
| 2 | 27/30 | 0/30 | 27 / 0, 1.49e-08 | 30, 30 | 0.050, 0.150 | 0.3735 |
| 3 | 27/30 | 1/30 | 26 / 0, 2.98e-08 | 30, 30 | 0.000, 0.150 | 0.3415 |
| 4 | 27/30 | 4/30 | 24 / 1, 1.55e-06 | 30, 30 | 0.000, 0.150 | 0.3381 |

- Same collapse status at all five seeds: 30 of 30 device-derived draws.
- Main-grid collapse range over seeds: [27, 27]; repair: [0, 4].
- X1a: HOLDS
- X1b: HOLDS
- X1c: HOLDS
- X1d: HOLDS

## X2: step-budget-scaled main grid and repair (member seed 0, k = 1)

- Collapse at beta = 0.20: main_budget 30/30, repair_budget 2/30; McNemar 28 / 0, p = 7.45e-09.
- Median beta*: 0.000 and 0.250; median margin 0.3706 and 0.7313.
- Households under 1,000 rows: main 0.283, repair 0.067; max epochs per round 14 and 14.
- X2a: HOLDS
- X2a_falsifier_fired: False
- X2b: HOLDS
- X2c: HOLDS

## X4: 8-class grid (stored rows; per-family detection from the k = 1 re-run)

- Re-run control: max |CA difference| against the stored rows 0.00e+00 (must be 0).
- Median beta* at k = 1: IID 0.400, device-derived 0.000; device-derived collapse at beta = 0.20: 30/30 (IID 0/30).
- Median certified detection per family at k = 1, beta = 0 (IID / device-derived): Attack 0.996 / 0.000; C&C 0.999 / 0.000; C&C-Torii 0.000 / 0.000; DDoS 1.000 / 0.000; PartOfAHorizontalPortScan 0.994 / 0.000
- X4a: HOLDS
- X4b: HOLDS
- X4c: FAILS

## JS02: federation size (k = 1)

| N | IID at ceiling (grid value) | dd median beta* | dd median margin | dd collapse at 0.20 |
|---|---|---|---|---|
| 10 | 30 (0.45) | 0.000 | 0.4004 | 28/30 |
| 20 | - (-) | 0.050 | 0.3457 | 27/30 |
| 50 | 30 (0.45) | 0.100 | 0.3318 | 29/30 |

- J2a: HOLDS
- J2b: HOLDS
- J2c: FAILS

## JS03: member capacity (128-64-32 against 32-16, k = 1, paired by draw)

- Device-derived beta* unchanged on 22/30 draws; median paired gain in clean ensemble accuracy +0.0000, in vote margin +0.0062; IID at the ceiling 29/30.
- J3a: FAILS
- J3b: FAILS
- J3c: HOLDS

