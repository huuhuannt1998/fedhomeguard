# Supplementary material: code, result rows and generators

Anonymized artifact for the submission "When Client-Count Certification Holds for Federated IoT
Intrusion Detection". It is built locally from the code and the result rows after both corrections
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
- `logs/`: the six same-ensemble run logs whose clean passes give the timings in Appendix A.
- `predeclarations/`: the three device-type-sweep predeclarations of Section 7 and Appendix C, each
  byte-identical to the file as committed; `COMMIT_LOG.md`, an anonymized log of the commit that added
  each one and of the commit that added its results; and `nbaiot_2026-08-25_record.md`, an export of
  the internal project-log record holding the earlier N-BaIoT outcome prediction. All timestamps are
  internal: no external registry dated any of them.
- `literature/`: the screen protocol and inventories behind Appendix D.
- `configs/`, `tests/`, `docker/`, `environment.yml`, `pyproject.toml`, `Makefile`.

## Reproducing the numbers
```
conda env create -f environment.yml && conda activate fedhomeguard
python -m pytest tests -q
mkdir -p out/floats
FHG_GENERATED=out python scripts/gen_paper_numbers.py     # numbers.tex and tables
FHG_GENERATED=out python scripts/gen_richness.py
FHG_GENERATED=out python scripts/gen_e7.py                # ablation table (with fracDegen)
FHG_GENERATED=out python scripts/gen_crossdataset.py      # needs the raw corpora (mutual information)
FHG_GENERATED=out python scripts/gen_stagec_tables.py
FHG_GENERATED=out FHG_FIGURES=out python scripts/gen_teaser.py
```
Every number in the paper is a macro written by these scripts from the rows above. The raw
corpora (IoT-23, N-BaIoT; about 10 GB) are not included; `scripts/fetch_data.py` downloads them
from their public sources, and re-running the experiments themselves takes hours
(`make experiments`).
