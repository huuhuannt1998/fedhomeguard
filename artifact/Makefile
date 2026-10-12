# One-command reproduction (review sec 48).
#
#   make data      fetch IoT-23 and verify checksums
#   make test      run the unit and certification-validation suites
#   make experiments   run every canonical experiment lane (hours)
#   make paper     regenerate every number, table and figure, then build the PDF
#   make verify    re-run every gate and fail loudly
#   make all       test -> paper -> verify
#
# `make paper` never invents numbers: the generators read results/canonical/*.jsonl
# and refuse to emit unless all consistency assertions pass. The same-predictor grid
# (e2_*), the adaptive arm and the multi-class control (e25_multiclass_*, corrected by
# scripts/gen_r9_multiclass_fix.py) are read from results/r6_nan_fix/corrected/, the rows
# with the alie/gaussian single-honest-update NaN corrected (scripts/aggregate.py:src);
# FHG_FROZEN=1 reads the frozen pre-correction rows instead.

PY      ?= python3
MAN     := manuscript
CANON   := results/canonical

.PHONY: all data test experiments paper verify figures numbers clean-derived

all: test paper verify

data:
	$(PY) scripts/fetch_data.py
	$(PY) scripts/manifest.py --verify

test:
	$(PY) -m pytest tests -q
	$(PY) scripts/exp_e1_validate.py

experiments:
	$(PY) scripts/exp_e1_validate.py
	bash scripts/rerun_p1.sh
	bash scripts/decensor_sweep.sh
	bash scripts/run_volume.sh

numbers:
	$(PY) scripts/check_completeness.py
	$(PY) scripts/gen_paper_numbers.py
	$(PY) scripts/gen_inventory_table.py
	$(PY) scripts/gen_e3.py
	$(PY) scripts/gen_e7.py
	$(PY) scripts/gen_e7_stats.py
	$(PY) scripts/gen_e9.py
	$(PY) scripts/gen_e12.py
	$(PY) scripts/gen_e14_deployable.py
	$(PY) scripts/gen_instruments.py > logs/instruments.log
	$(PY) scripts/gen_crossdataset.py
	$(PY) scripts/gen_gapspread.py
	$(PY) scripts/gen_multiclass.py

figures:
	$(PY) scripts/make_fig_main.py --out $(MAN)/figures/fig_main.pdf   # replaces the lost charts/make_figures_v2.py
	$(PY) scripts/gen_e8.py
	$(PY) scripts/gen_teaser.py

paper: numbers figures
	cd $(MAN) && pdflatex -interaction=nonstopmode main.tex >/dev/null \
	  && bibtex main >/dev/null \
	  && pdflatex -interaction=nonstopmode main.tex >/dev/null \
	  && pdflatex -interaction=nonstopmode main.tex >/dev/null
	@echo "built $(MAN)/main.pdf"

verify:
	$(PY) scripts/check_completeness.py
	$(PY) scripts/aggregate.py | grep -q FAIL && { echo "ASSERTION FAILURE"; exit 1; } || true

clean-derived:
	rm -f $(MAN)/generated/*.tex $(MAN)/generated/floats/*.tex $(MAN)/figures/*.pdf
