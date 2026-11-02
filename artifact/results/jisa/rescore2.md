# JISA re-scoring, round jisa4 (no training)

## C5: count rule per device-type level (IoT-23 device-derived; each (level, seed) draw counted once)

- k = 1: 135 of 160 within one step overall
  - 1-1 types: 28 of 30 within one step, 24 exact, mean error +0.33 steps, 24 with predicted and observed beta* both 0
  - 1-3 types: 26 of 40 within one step, 11 exact, mean error +1.20 steps, 6 with predicted and observed beta* both 0
  - 2-5 types: 24 of 30 within one step, 17 exact, mean error +0.70 steps, 0 with predicted and observed beta* both 0
  - 3-8 types: 27 of 30 within one step, 16 exact, mean error +0.57 steps, 0 with predicted and observed beta* both 0
  - 5-10 types: 30 of 30 within one step, 25 exact, mean error +0.17 steps, 0 with predicted and observed beta* both 0
- k = 2: 156 of 160 within one step overall
  - 1-1 types: 29 of 30 within one step, 8 exact, mean error +0.77 steps, 6 with predicted and observed beta* both 0
  - 1-3 types: 37 of 40 within one step, 15 exact, mean error +0.70 steps, 0 with predicted and observed beta* both 0
  - 2-5 types: 30 of 30 within one step, 25 exact, mean error +0.17 steps, 0 with predicted and observed beta* both 0
  - 3-8 types: 30 of 30 within one step, 30 exact, mean error +0.00 steps, 0 with predicted and observed beta* both 0
  - 5-10 types: 30 of 30 within one step, 30 exact, mean error +0.00 steps, 0 with predicted and observed beta* both 0

## C10: smallest attack prior at which a cell's median re-weighted certified accuracy beats 1 - pi

- 36 cells (26 with median certified accuracy above 0); 23 beat the constant benign predictor at some prior up to 0.5; the smallest such prior is 0.0544 (0.0555 at k <= 2)
- IID, k = 1: 0.056 at beta = 0, 0.0619 at beta = 0.4

  - device_derived, k = 1, beta = 0.0: 0.0662
  - device_derived, k = 1, beta = 0.05: 0.072
  - device_derived, k = 1, beta = 0.1: 0.0963
  - device_derived, k = 1, beta = 0.2: None
  - device_derived, k = 1, beta = 0.3: None
  - device_derived, k = 1, beta = 0.4: None
  - device_derived, k = 2, beta = 0.0: 0.0638
  - device_derived, k = 2, beta = 0.05: 0.0713
  - device_derived, k = 2, beta = 0.1: 0.0776
  - device_derived, k = 2, beta = 0.2: 0.3423
  - device_derived, k = 2, beta = 0.3: None
  - device_derived, k = 2, beta = 0.4: None
  - device_derived, k = 3, beta = 0.0: 0.0551
  - device_derived, k = 3, beta = 0.05: 0.0735
  - device_derived, k = 3, beta = 0.1: 0.1121
  - device_derived, k = 3, beta = 0.2: None
  - device_derived, k = 3, beta = 0.3: None
  - device_derived, k = 3, beta = 0.4: None
  - iid, k = 1, beta = 0.0: 0.056
  - iid, k = 1, beta = 0.05: 0.056
  - iid, k = 1, beta = 0.1: 0.0562
  - iid, k = 1, beta = 0.2: 0.0579
  - iid, k = 1, beta = 0.3: 0.0608
  - iid, k = 1, beta = 0.4: 0.0619
  - iid, k = 2, beta = 0.0: 0.0555
  - iid, k = 2, beta = 0.05: 0.0557
  - iid, k = 2, beta = 0.1: 0.056
  - iid, k = 2, beta = 0.2: 0.0608
  - iid, k = 2, beta = 0.3: None
  - iid, k = 2, beta = 0.4: None
  - iid, k = 3, beta = 0.0: 0.0544
  - iid, k = 3, beta = 0.05: 0.0557
  - iid, k = 3, beta = 0.1: 0.0571
  - iid, k = 3, beta = 0.2: None
  - iid, k = 3, beta = 0.3: None
  - iid, k = 3, beta = 0.4: None

## C10 on the 30-draw main grid (k = 1 and 2)

- smallest attack prior at which any cell's median beats 1 - pi: 0.0545
  - iid|k=1: beta 0.0: 0.0559, beta 0.05: 0.056, beta 0.1: 0.0561, beta 0.15: 0.0567, beta 0.2: 0.0583, beta 0.25: 0.0603, beta 0.3: 0.0609, beta 0.35: 0.0617, beta 0.4: 0.062, beta 0.45: 0.0624, beta 0.5: None
  - iid|k=2: beta 0.0: 0.0545, beta 0.05: 0.0557, beta 0.1: 0.056, beta 0.15: 0.0576, beta 0.2: 0.0606, beta 0.25: 0.062, beta 0.3: None, beta 0.35: None, beta 0.4: None, beta 0.45: None, beta 0.5: None
  - device_derived|k=1: beta 0.0: 0.0605, beta 0.05: 0.0793, beta 0.1: 0.3639, beta 0.15: None, beta 0.2: None, beta 0.25: None, beta 0.3: None, beta 0.35: None, beta 0.4: None, beta 0.45: None, beta 0.5: None
  - device_derived|k=2: beta 0.0: 0.0592, beta 0.05: 0.0724, beta 0.1: 0.0818, beta 0.15: 0.1174, beta 0.2: None, beta 0.25: None, beta 0.3: None, beta 0.35: None, beta 0.4: None, beta 0.45: None, beta 0.5: None

## A4: prior-free beta* (certified balanced accuracy above 0.5) on the 30-draw main grid

- iid|k=1: beta* median 0.450 (mean 0.450); balanced median 0.450 (mean 0.450)
- iid|k=2: beta* median 0.250 (mean 0.250); balanced median 0.250 (mean 0.250)
- device_derived|k=1: beta* median 0.050 (mean 0.063); balanced median 0.075 (mean 0.083)
- device_derived|k=2: beta* median 0.150 (mean 0.137); balanced median 0.150 (mean 0.170)

## A4: IoT-23 against N-BaIoT, mean beta* on the paper's floors and on a common prior-free floor

- N-BaIoT device_derived|k=1: 30 draws, mean beta* 0.450 (tau floor), 0.450 (balanced accuracy above 0.5)
- N-BaIoT device_derived|k=2: 30 draws, mean beta* 0.250 (tau floor), 0.250 (balanced accuracy above 0.5)
- N-BaIoT iid|k=1: 30 draws, mean beta* 0.450 (tau floor), 0.450 (balanced accuracy above 0.5)
- N-BaIoT iid|k=2: 30 draws, mean beta* 0.250 (tau floor), 0.250 (balanced accuracy above 0.5)
- IoT-23 device_derived|k=1: 30 draws, mean beta* 0.063 (tau floor), 0.083 (balanced accuracy above 0.5)
- IoT-23 device_derived|k=2: 30 draws, mean beta* 0.137 (tau floor), 0.170 (balanced accuracy above 0.5)
- IoT-23 iid|k=1: 30 draws, mean beta* 0.450 (tau floor), 0.450 (balanced accuracy above 0.5)
- IoT-23 iid|k=2: 30 draws, mean beta* 0.250 (tau floor), 0.250 (balanced accuracy above 0.5)
