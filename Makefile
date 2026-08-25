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
# and refuse to emit unless all consistency assertions pass.

PY      ?= python3
MAN     := manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP
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

figures:
	$(PY) $(MAN)/charts/make_figures_v2.py
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
	$(PY) scripts/verify_paper_claims.py

clean-derived:
	rm -f $(MAN)/generated/*.tex $(MAN)/generated/floats/*.tex $(MAN)/figures/*.pdf
