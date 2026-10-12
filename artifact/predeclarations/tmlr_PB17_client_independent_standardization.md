# Predeclaration PB17: client-independent standardization (sensitivity rerun)

Written 2026-10-10T16:34:24-0400 BEFORE the runs, for the TMLR revision (round tmlr5; mock review round 2, M3; coordinator priority 1). Not committed (commits are forbidden); dated by its RKA journal entry and SHA-256.

## Why
Every certified number in the paper comes from features standardized with the mean and standard deviation of the pooled training rows (runner.prepare -> data.standardize). That statistic depends on every client's rows, so in a deployment an untouched member would not be independent of a malicious client's raw data. In the experiments no attack alters any client's features (label flip changes labels; sign flip, Gaussian, IPM, ALIE and the purpose-built attack change updates), so the pooled statistic is the clean one; this rerun measures how much the results depend on it.

## Protocol, fixed in advance
- IoT-23, N = 20, the repository's members (fl_run, 15 rounds, seed 0), beta grid 0 to 0.50 in steps of 0.05, tau_triv = 0.7300, exact certification (exactcert.certify_exact) over full enumeration at k = 1 (K = 20) and k = 2 (K = 190).
- Partitions: IID and device-derived (1-3 device types) seeds 10-19; label-Dirichlet alpha = 0.5 seeds 100-109. k in {1, 2}. 3 x 10 x 2 = 60 ensembles per variant.
- Variants (same partitions, same member seeds):
  - P (control): pooled standardization, as in the paper. Must reproduce the paper's rows where they exist (e5f seeds 10-19; PB13 label alpha = 0.5 at k = 1).
  - M (per member): each member's features are standardized with the mean and standard deviation of its own k clients' training rows, applied to its training rows and to the test set; a column whose standard deviation on those rows is below 0.01 is centred but not scaled.
  - R (reference sample): a fixed 5% of training rows drawn uniformly at random (seed 0) is removed from every client and used only to compute the mean and standard deviation; no member trains or is tested on it.
- The one-hot vocabulary is unchanged in all variants: it covers all 3 protocol and all 7 service values and 12 of the 13 connection states, so a client can at most change which of the rarest connection states is dropped.
- Per draw and variant: beta*, certified accuracy, CTR_mal and CTR_ben at every beta, mean vote margin, K.
- Report per partition, k and variant: median and range of the change in beta* (variant minus P), the number of draws whose beta* changes, and the median change in certified accuracy at beta = 0, 0.10, 0.20 (and 0.40 at k = 1).
- **Material change (fixed now):** in any partition and k, a median change in beta* of at least one grid step (0.05), or beta* changing on more than 3 of 10 draws, or a median change in certified accuracy of at least 0.01 at any beta at or below the control's median beta*. A material change is reported in the abstract.
- Runtime: about 180 ensembles (60 per variant), under 30 min on 4 workers.
