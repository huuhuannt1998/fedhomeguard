# Supplementary material: code, result rows and generators

Anonymized artifact for the submission "When Client-Count Certificates Leave Alarms Uncovered: Competence Ceilings and
a Max-Flow Certified Decoder for Federated IoT Intrusion Detection". Every number, table and figure in the paper is
written by a generator in `artifact/scripts/` from the result rows in `artifact/results/`. Nothing here identifies the
authors; absolute paths were replaced by `<artifact-root>` or repository-relative paths.

## Where to look

Section, table and figure numbers are those of the submitted paper. Run every command from `artifact/` with
`PYTHONPATH="$PWD/src"`; the generators write to `out/` (or `$FHG_OUT`, `$FHG_GENERATED`, `$FHG_FIGURES`).

| Paper | Finding | Result rows | Generator |
|---|---|---|---|
| Section 1, Section 7 | at four of 20 households, plurality certifies a median 0.925 of benign flows and no attack flow on 21 of the 30 IoT-23 draws of the decoder set | `results/novelty/maxflow_decoder_iot23.jsonl` (per-class rates in `maxflow_decoder_iot23_r3.jsonl`) | `scripts/gen_isj_decoder_table.py` |
| Section 2, Figure 1 | the setting: households, members, the vote and the certificate | (schematic) | `scripts/gen_isj_fig_system.py` (needs pdflatex and TikZ) |
| Section 3, Figure 2; Table A1 | the plurality limit and its exact values | `results/canonical/`, `results/beta_geo.json` | `scripts/gen_teaser.py`, `scripts/gen_stagec_tables.py` |
| Section 4, Figure 3; Appendix A | the competence ceiling, exact by bipartite max-flow, against plurality and abstention | `results/novelty/competence_ceiling_*.jsonl` | `scripts/novelty/competence_ceiling.py` (runs), `scripts/gen_isj_ceiling_fig.py` |
| Section 5, Section 7, Table 2 | the max-flow certified decoder on IoT-23, N-BaIoT and CIC IoT-IDAD 2024, server sets of 0.5% to 10% | `results/novelty/maxflow_decoder_*.jsonl` | `scripts/novelty/maxflow_decoder.py` (runs), `scripts/gen_isj_decoder_table.py` |
| Section 6, Table 1 | every predeclared run: corpus, households, draws, seeds, rows evaluated, trivial floor, budgets | `results/novelty/*.jsonl` | `scripts/gen_isj_runs_table.py` |
| Appendix B, Table B1 | the alternatives that failed their success criteria: abstention, anomaly votes, certified anomaly-based ensemble | `results/novelty/abstain_feasibility.json`, `anomaly_vote_*`, `certified_anomaly_*` | `scripts/novelty/{abstain_feasibility,anomaly_vote,certified_anomaly}.py`, `scripts/gen_isj_alternatives_table.py` |
| Appendix C, Figure C1, Table C1 | coverage of the certificate against the share of nearly one-class households; the device- against label-Dirichlet runs and the clustered regression | `results/analysis/instruments.jsonl`, `results/canonical/e7_volskew.jsonl`, `results/tmlr_rev/pb13_15_rows.jsonl`, `pb19_decomposition.json` | `scripts/gen_fig_coverage.py`, `scripts/gen_e7.py` |
| Appendix C, Figure C2 | tightness: certified against attacked accuracy of the same ensemble; the exact worst case over malicious sets | `results/r6_nan_fix/corrected/` (through `scripts/aggregate.py`), `results/tmlr_rev/pb10/`, `pb10_worstcase.json` | `scripts/make_fig_main.py` |
| Appendix C, Table C2 | the cross-dataset comparison | `results/canonical/e5f_*.jsonl`, `nb9_cert_*.jsonl`, `results/analysis/instruments.jsonl` | `scripts/gen_crossdataset.py` (needs the raw corpora) |
| Data availability | the six predeclarations of the runs above, with the SHA-256 prefixes the paper prints | `predeclarations/*_2026-11-03.md`, `predeclarations/PREDECLARATION_HASHES_ISJGP.md` | `shasum -a 256` |

The table generators (`gen_isj_decoder_table.py`, `gen_isj_alternatives_table.py`, `gen_isj_runs_table.py`) and the
numbers file of `gen_isj_ceiling_fig.py` reproduce the paper's files byte for byte. The sections after "Contents"
document how the earlier versions of the project added files; their appendix letters refer to those versions, not to
the submitted paper. File names keep the internal round labels (`jisa_*`, `tmlr_*`) under which they were recorded,
because their hashes are listed in `results/MANIFEST.json` and in the predeclarations.

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

## Competence ceiling and max-flow certified decoder (added 2026-11-04, generators updated 2026-11-10)
Everything new in the submitted paper; nothing listed under the earlier rounds was changed except the generators named here.
- `predeclarations/*_2026-11-03.md`: the six predeclarations of the paper's new runs (competence ceiling, max-flow
  certified decoder, decoder follow-up runs, abstention, anomaly votes, certified anomaly-based ensemble with its
  dated deviation), byte-identical to the files as hashed; `PREDECLARATION_HASHES_ISJGP.md` lists the full SHA-256
  digests whose first 16 hex digits the paper prints.
- `scripts/novelty/`: `competence_ceiling.py` (the exact aggregator-agnostic ceiling by max-flow),
  `maxflow_decoder.py` (decoder learning on the labelled server set and exact certification),
  `abstain_feasibility.py`, `anomaly_vote.py`, `certified_anomaly.py` (the failed alternatives of Appendix B).
- `results/novelty/`: their result rows, one JSON line per partition draw (hashes in `results/MANIFEST.json`):
  `competence_ceiling_*`, `maxflow_decoder_*` (IoT-23 primary; server-set fractions 0.5%, 1%, 2%; per-class rates in
  `_r3`; N-BaIoT; CIC IoT-IDAD 2024), `abstain_feasibility.json`, `anomaly_vote_*`, `certified_anomaly_*`.
- Generators: `scripts/gen_isj_decoder_table.py`, `gen_isj_alternatives_table.py`, `gen_isj_runs_table.py`, `gen_isj_ceiling_fig.py` (read
  only `results/novelty/`; write `out/generated/` and `out/figures/`, or `$FHG_OUT`) and `gen_isj_fig_system.py`
  (the setting schematic; needs pdflatex and TikZ; writes to `FHG_FIGURES`, default `out/figures`). On 2026-11-10 the
  decoder table gained its per-class panel and the four rules' collapse counts, the runs table was added, and the
  figure scripts (`gen_isj_ceiling_fig.py`, `gen_isj_fig_system.py`, `gen_teaser.py`, `gen_fig_coverage.py`,
  `make_fig_main.py`) were set to the journal's text width and its terms; they read the same result rows.

```
python3 scripts/gen_isj_decoder_table.py         # decoder table and its numbers (out/generated/)
python3 scripts/gen_isj_alternatives_table.py    # the failed alternatives table
python3 scripts/gen_isj_runs_table.py            # the table of runs (Table 1)
python3 scripts/gen_isj_ceiling_fig.py           # ceiling figure and its numbers
shasum -a 256 predeclarations/*_2026-11-03.md    # compare with PREDECLARATION_HASHES_ISJGP.md
# re-running the experiments needs the raw corpora (scripts/fetch_data.py) and the member bank:
python3 scripts/novelty/maxflow_decoder.py --set iot23 [--frac 0.10]
```
Run from `artifact/` with `PYTHONPATH="$PWD/src"`. The table generators reproduce the paper's tables byte for byte
from the rows above.

## Training runs of an earlier revision (files `jisa_*`, added 2026-11-01)
- `predeclarations/jisa_*.md`: the three predeclarations of the runs added in that revision, and
  `PREDECLARATION_HASHES.md`, their SHA-256 hashes as recorded before any run, with how to recompute them.
- `results/jisa/`: member seeds 1-4 (`x1_*`), the equal-step-budget and repair runs (`x_runs.jsonl`), the 8-class
  re-run at k = 1 (`x4_*`), federation size (`js02_*`), member capacity (`js03_*`), the CIC IoT-IDAD 2024
  victim-side runs (`js01_*`), and the scorings against the predeclarations (`score.json`, `score.md`,
  `js01_cvm.json`, `js01_summary.md`); re-scorings of stored rows (`rescore*.json`). Their hashes are in
  `results/MANIFEST.json`.
- `scripts/`: `exp_e2.py --member-seed`, `jisa_x_runs.py`, `run_jisa_train.sh`, `run_jisa_js01.sh`,
  `jisa_score.py`, `jisa_js01_describe.py`, `jisa_js01_cvm.py`, `jisa_rescore*.py`, and the table generators
  (`gen_jisa_tables.py` with its YAML files, `gen_tmlr2_tables.py`).
- `src/fedhomeguard/cic_victim.py` and `configs/jisa_cic_victim.yaml`: the victim-side reading of CIC IoT-IDAD 2024
  (needs the corpus's packet-feature CSVs under `data/raw/cic-iot-idad-2024/`). `exactcert.py` carries the
  per-family detection fix of Appendix C.

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

## Earlier revision analyses (round tmlr2, files `tmlr_*`)
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

## Earlier revision analyses (round tmlr4, files `tmlr_*`)
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

## Earlier revision analyses (round tmlr5, files `tmlr_*`)
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

## Earlier revision analyses (round tmlr6, files `tmlr_*`)
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

## Earlier revision analyses (round tmlr7, files `tmlr_*`)
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
