# JISA re-scoring (no training; post hoc)

## X3: device- vs label-Dirichlet, restricted to K = 20 (PB13 rows, k = 1)

K per draw (family|alpha: {K: draws}): {"dirichlet_device|1.0": {"20": 30}, "dirichlet_device|0.5": {"20": 30}, "dirichlet_device|0.2": {"20": 30}, "dirichlet_device|0.1": {"20": 28, "19": 2}, "dirichlet|1.0": {"20": 30}, "dirichlet|0.5": {"20": 30}, "dirichlet|0.2": {"17": 2, "19": 10, "20": 15, "18": 3}, "dirichlet|0.1": {"12": 2, "15": 6, "16": 8, "14": 4, "17": 3, "9": 1, "18": 3, "19": 2, "8": 1}}

- primary (device 0.5 vs label 0.2), all draws: n = 30 vs 30; mean margin difference +0.5928 (p = 0.00001); beta* difference +0.3683 (p = 0.00001)
- primary (device 0.5 vs label 0.2), K = 20 only: n = 30 vs 15; mean margin difference +0.6235 (p = 0.00001); beta* difference +0.3800 (p = 0.00001)
- S2 (device 0.1 vs label 0.2), all draws: n = 30 vs 30; mean margin difference +0.1595 (p = 0.00001); beta* difference +0.1267 (p = 0.00001)
- S2 (device 0.1 vs label 0.2), K = 20 only: n = 28 vs 15; mean margin difference +0.1908 (p = 0.00001); beta* difference +0.1363 (p = 0.00001)

## R4: coverage repair vs main grid, collapse at beta = 0.20, k = 1, paired on seeds

- 30 paired seeds (10-39); collapse 27 (main) vs 1 (repair); discordant pairs 26 (main only) and 0 (repair only); exact two-sided McNemar p = 2.98e-08

## B2: household row counts, main device-derived grid (seeds 10-39, 1-3 types, N = 20; rebuilt, no training)

- 600 households; row-count percentiles (0/10/25/50/75/90/100): [31.0, 267.0, 864.0, 4096.0, 9975.0, 16430.0, 74080.0]; 28.3% below 1,000 rows
- one-class households (>95% one class): 240 in total, 151 below 1,000 rows and 89 at or above; collapse at beta = 0.20 on 27 of 30 draws
- collapsed draws with at least one one-class household of >= 1,000 rows: 27 of 27
- Spearman, collapse vs number of small households 0.3862898156482066; vs number of one-class households 0.4393806328503669

## R8: tie-aware ceiling at N = 20

- k = 1: strict 0.450, tie-aware 0.500; k = 2: strict 0.250, tie-aware 0.250; k = 3: strict 0.150, tie-aware 0.150
- At k = 1 and m = 10 only a unanimous vote for the tie-winning class certifies; ties break to benign, so certified accuracy is at most the benign share 1 - tau_triv = 0.2700 < tau_triv = 0.7300: the tie-aware rule cannot raise beta* above 0.45 here.

## R9: benign false alarms at IoT-23's honeypot flow rates (IID ensemble, k = 1, no adversary)

- benign error 0.0589 (1 - median certified benign rate at beta = 0, which at m = 0 is the benign accuracy)
- CTU-Honeypot-Capture-4-1: 452 flows over 0.91 days = 496 flows/day -> 29.2 false alarms/day for that one device
- CTU-Honeypot-Capture-5-1: 1374 flows over 0.23 days = 6011 flows/day -> 354.2 false alarms/day for that one device

## R2: device-derived draws behind the count rule's IoT-23 row (k = 1)

- 160 unique (devices-per-household level, seed) draws; by level: {(1, 3): 40, (1, 1): 30, (2, 5): 30, (3, 8): 30, (5, 10): 30}

