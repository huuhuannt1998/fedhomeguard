# Supplementary material: code, result rows and generators

Anonymized artifact for the submission "When Client-Count Certification Informs Federated IoT Intrusion Detection: A Case Study on IoT-23". It is built locally from the code and the result rows after both corrections
described in Appendix B (the determinism re-run and the NaN correction). Nothing here identifies
the authors; absolute paths were replaced by `<artifact-root>` or repository-relative paths.

## Contents (`artifact/`)
- `src/fedhomeguard/`: partitions, members, the deployed-ensemble certificate, attacks.
- `scripts/`: experiment drivers and every generator that turns result rows into the paper's
  numbers, tables and figures (`gen_paper_numbers.py`, `gen_richness.py`, `gen_teaser.py`,
  `gen_stagec_tables.py`, `bstar.py` for the one definition of the certified breakdown point, ...).
- `results/`: the result rows the paper reads. `results/canonical/` holds the main arms;
  `results/r6_nan_fix/corrected/` the same-ensemble grid after the NaN correction (read through
  `scripts/aggregate.py`); `results/r9_mc_nanfix/` the corrected 8-class control;
  `results/analysis/instruments.jsonl` the 318-cell statistic audit;
  `results/analysis/richness_instruments.jsonl` the same statistics for every device-type-sweep
  partition (written by `scripts/gen_richness_instruments.py`, which rebuilds the partitions without
  training and needs the raw corpora); `results/beta_geo.json` the
  exact ceiling. Superseded pre-correction folders are not included.
- `logs/`: the six same-ensemble run logs whose clean passes gave the original timings; Appendix A now
  reports the re-measurement in `results/tmlr_rev/pb09_timing.json` (round tmlr3).
- `predeclarations/`: the three device-type-sweep predeclarations of Section 7 and Appendix C (the
  revision's protocols `tmlr_PB01`-`tmlr_PB18` are described below; rounds tmlr6 and tmlr7 added no protocol), each
  byte-identical to the file as committed; `COMMIT_LOG.md`, an anonymized log of the commit that added
  each one and of the commit that added its results; and `nbaiot_2026-08-25_record.md`, an export of
  the internal project-log record holding the earlier N-BaIoT outcome prediction. All timestamps are
  internal: no external registry dated any of them.
- `literature/`: the screen protocol and inventories behind Appendix D.
- `configs/`, `tests/`, `docker/`, `environment.yml`, `pyproject.toml`, `Makefile`.

## Reproducing the numbers
```
conda env create -f environment.yml && conda activate fedhomeguard
export PYTHONPATH="$PWD/src"                               # use this artifact's package
python -m pytest tests -q
mkdir -p out/floats
FHG_GENERATED=out python scripts/gen_paper_numbers.py     # numbers.tex and tables
FHG_GENERATED=out python scripts/gen_richness.py
FHG_GENERATED=out python scripts/gen_e7.py                # ablation table (with fracDegen)
FHG_GENERATED=out python scripts/gen_crossdataset.py      # needs the raw corpora (mutual information)
FHG_GENERATED=out python scripts/gen_stagec_tables.py
FHG_GENERATED=out FHG_FIGURES=out python scripts/gen_teaser.py
FHG_FIGURES=out python scripts/gen_fig_system.py         # the setting schematic (needs pdflatex, TikZ)
FHG_FIGURES=out python scripts/gen_fig_coverage.py       # beta* at k=1 against S_JS and fracDegen (needs pdflatex)
```
Without `FHG_GENERATED` / `FHG_FIGURES` the generators write into `out/` (`scripts/_manuscript.py`).
Every number in the paper is a macro written by these scripts from the rows above. The raw
corpora (IoT-23, N-BaIoT; about 10 GB) are not included; `scripts/fetch_data.py` downloads them
from their public sources, and re-running the experiments themselves takes hours
(`make experiments`).

## Revision analyses (round tmlr2)
The revision's analyses add, without changing any earlier file except the four generators named here:
- `results/tmlr_rev/`: their result files, among them the exact worst case per deployed ensemble
  (`pb10/`, summary `pb10_worstcase.json`), the coverage-vote count per draw (`pb03_cvm_draws.jsonl`),
  the controlled partitions (`pb04_rows.jsonl`), the screen baselines (`pb08_screen.json`), the
  matched pairs (`pb01_pairs.json`), the out-of-sample association (`pb02_association.json`), the
  prior analysis (`pb06_prior.json`, post hoc), the deduplicated test subset (`pb07a_dedup.json`)
  and the brute-force check on trained ensembles (`p0_vote_bound.json`). The trained member
  predictions they were computed from (about 10 MB) are in `results/tmlr_rev/member_bank/` (round tmlr4);
  `scripts/tmlr_rev/build_member_bank.py` rebuilds them from the corpora.
- `scripts/tmlr_rev/`: the analysis scripts. Paths are written `<artifact-root>`; set them to this
  folder before running.
- `scripts/gen_tmlr2_tables.py` writes the tables of the exact worst case, the screen baselines and
  the coverage count; `gen_e7.py` now prints the ensemble size $K$, `gen_paper_numbers.py` reads the
  30-draw grid for the detection-metric table, and `gen_fig_system.py` labels what the adversary
  manipulates and what the vote classifies:
  `FHG_GENERATED=out python scripts/gen_tmlr2_tables.py`.
- `predeclarations/tmlr_PB*.md`: the analysis protocols, written before the runs; no external
  registry dated them, and post hoc analyses are marked as such in them and in the paper.
- `results/tmlr_rev/pb09_timing.json` (5 repeats of the PB09 protocol on one core, `scripts/tmlr_rev/pb09_timing_repeat.py`) and `pb09_cert_timing.json` (certification time, post hoc, `scripts/tmlr_rev/pb09_cert_timing.py`) give Appendix A's training times; `gen_paper_numbers.py` prints them in the cost table.

## Revision analyses (round tmlr4)
- `results/tmlr_rev/pb13_15_rows.jsonl` and `pb13_15_summary.json` (`scripts/tmlr_rev/pb13_15_runs.py`): the
  predeclared runs PB13 (device- against label-Dirichlet, 30 draws per concentration), PB14 (coverage dial on
  N-BaIoT) and PB15 (pairing by class shares at k = 2); protocols in `predeclarations/tmlr_PB13..15_*.md`.
- `results/tmlr_rev/pb16_slack_split.json` (`scripts/tmlr_rev/pb16_slack_split.py`, post hoc): the same-ensemble
  slack split into attack strength, set selection and the certificate's own slack.
- `results/tmlr_rev/member_bank/`: the clean member predictions of every banked ensemble (one `.npz` of packed
  votes and one `.json` of metadata per ensemble), from which the exact worst case and the count were computed.
- `scripts/gen_stagec_tables.py` now prints Table 1 from the 30-draw grid at k <= 2; `gen_e7.py` prints the
  device and label rows of Table 2 from PB13; `gen_tmlr2_tables.py` adds the PB13 and PB14 rows and the mean
  signed error to the coverage-count table.

## Revision analyses (round tmlr5)
- `results/tmlr_rev/pb17_18_rows.jsonl` and `pb17_18_summary.json` (`scripts/tmlr_rev/pb17_18_runs.py`): PB17,
  the predeclared standardization rerun (pooled control, per-member statistics, a 5% reference sample; variant
  `Rf`, the floored reference sample, is post hoc), and PB18, the predeclared volume dial with budget-scaled local
  epochs; protocols in `predeclarations/tmlr_PB17_*.md` and `tmlr_PB18_*.md`.
- `results/tmlr_rev/pb19_decomposition.json` (`scripts/tmlr_rev/pb19_decomposition_clustered.py`, post hoc): the
  PB13 regression with errors clustered by concentration level and other covariate sets.
- `results/tmlr_rev/pb20_oos_threshold.json` (`scripts/tmlr_rev/pb20_oos_threshold.py`, post hoc): minClassSup with
  its threshold chosen inside each cross-validation fold.
- `scripts/gen_tmlr2_tables.py` now also prints the deduplicated-test table (Appendix C).
- The two pre-correction folders `results/.superseded_preC1/` and `results/.backup_precC1/`, which earlier copies
  of this folder held despite the note above, are removed.

## Removed files (2026-10-10)
- `scripts/prism_README.txt`, `scripts/verify_paper_claims.py`, `scripts/gen_appendix.py` and
  `scripts/paper_gates.py` read, checked or bundled an earlier layout of the manuscript that no longer exists.
  They are removed, with the `Makefile` targets that bundled that layout (`prism`, `prism-check`) and the
  claims-checker call in `make verify`. None of them is needed to reproduce the paper.
- `scripts/run_chain.sh`, `auto_finish.sh`, `finish_all.sh` and `regen_all.sh` stay as the record of how the
  runs were chained. Their last steps call `gen_appendix.py` or `verify_paper_claims.py` (skipped, or logged
  as failed, when absent) or build a `manuscript/` folder that this artifact does not hold; the experiments and
  generators they call do not depend on those steps. `scripts/tmlr_rev/build_claim_evidence.py` still names `scripts/gen_appendix.py`
  as the source of one historical table row.

## Revision analyses (round tmlr6)
No new training run; all three files are post hoc descriptions of existing rows and of the corpus files.
- `results/tmlr_rev/pb21_capture_table.json` (`scripts/tmlr_rev/pb21_capture_table.py`): the ten IoT-23 captures as
  the loader uses them (Table in Appendix D): labelled rows in full and read, rows kept, benign and malicious rows, test
  rows.
- `results/tmlr_rev/pb21_oneclass_classes.json` (`scripts/tmlr_rev/pb21_oneclass_classes.py`): which class the
  one-class households hold, per device-derived level, from `pb03_cvm_draws.jsonl`.
- `results/tmlr_rev/pb21_facts.json` (`scripts/tmlr_rev/pb21_facts.py`): the 1% re-weighting's denominator and the
  detector's benign error, the per-member standardization's beta* and collapse, the coverage repair's baseline, the
  deduplicated subset over the 30 draws of Table 1, and the strict rule's tie case.
- `scripts/gen_tmlr2_tables.py` now also prints the capture table and the table of every draw set (Appendix D).

## Revision analyses (round tmlr7)
The PB11 audit of CIC IoT-IDAD 2024 (Appendix D), run on a sample of the corpus (the first file of each of its 28
packet-feature traffic types) with no training; the corpus itself is not included and enters no other result.
- `results/tmlr_rev/pb11_idad_audit.json` (`scripts/tmlr_rev/pb11_idad_audit.py`, predeclared in
  `predeclarations/tmlr_PB11_second_dataset.md`): the predeclared check on the sample; it stops at per-record labels.
- `results/tmlr_rev/pb11b_idad_extended.json` (`scripts/tmlr_rev/pb11b_idad_extended.py`, post hoc, not
  predeclared): labels taken from the file names; device counts, I(device; label)/H(label), devices holding both
  classes.
- `results/tmlr_rev/pb11c_idad_roles.json` (`scripts/tmlr_rev/pb11c_idad_roles.py`, post hoc, not predeclared): the
  rule that a packet touches a Raspberry Pi when either Ethernet vendor column is Raspberry Pi; attack hosts and
  victims per traffic type; the coupling without the Raspberry Pi and virtual-machine hosts.
