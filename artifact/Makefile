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
MAN     := manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP
PRISM   := manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/prism
PRISMZIP := FedHomeGuard-prism.zip
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

# Self-contained upload bundle for a hosted LaTeX service (Prism, Overleaf).
# The previous bundle omitted IEEEtran.cls/.bst and shipped a whole .git tree,
# so it died at \documentclass on any service whose TeX tree lacks the IEEE
# class. LaTeX searches the project directory first, so pinning both files
# beside main.tex fixes the build wherever it runs. Rebuilt from the CURRENT
# manuscript every time, because the stale bundle was the other half of the bug.
#
# Deliberately NOT dependent on `paper`: the bundle ships SOURCE and the service
# compiles it, so what matters is that the tree on disk is current, not that it
# was just rebuilt here. Coupling the two would also make the bundle unbuildable
# whenever the data pipeline is red, which is exactly when you still need to send
# someone the paper. `prism-check` is what proves the bundle actually compiles.
prism:
	rm -rf $(PRISM) $(PRISMZIP)
	mkdir -p $(PRISM)
	cp $(MAN)/main.tex $(MAN)/refs.bib $(MAN)/main.bbl $(PRISM)/
	cp -R $(MAN)/sections $(MAN)/generated $(MAN)/figures $(PRISM)/
	find $(PRISM) -type f ! -name '*.tex' ! -name '*.pdf' ! -name '*.bib' \
	     ! -name '*.bbl' -delete
	cp "$$(kpsewhich IEEEtran.cls)" "$$(kpsewhich IEEEtran.bst)" $(PRISM)/
	cp scripts/prism_README.txt $(PRISM)/README-prism.txt
	find $(PRISM) -name '.DS_Store' -delete
	cd $(PRISM) && zip -qr ../../../$(PRISMZIP) . -x '.*'
	@echo "built $(PRISMZIP) -- verify it with: make prism-check"

# Builds the bundle the way a service does, in a throwaway directory, and fails
# if the result is not the 18-page document with the body ending on page 13.
# Testing the zip rather than the working tree is the point: the working tree
# has the system TeX and every build product to fall back on, and the zip does not.
# NOTE: every grep -c below needs `|| true`. grep exits 1 when the count is
# zero, so without it a bundle with ZERO errors fails the chain and reports
# FAILED -- the check inverts on exactly the good case.
prism-check: prism
	@rm -rf /tmp/fhg-prism-check && mkdir -p /tmp/fhg-prism-check
	@cd /tmp/fhg-prism-check && unzip -q $(CURDIR)/$(PRISMZIP) \
	  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 \
	  && bibtex main >/dev/null 2>&1 \
	  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 \
	  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 \
	  && n=$$(pdfinfo main.pdf | awk '/Pages/{print $$2}') \
	  && err=$$(grep -c '^!' main.log || true) \
	  && cls=$$(grep -c '(\./IEEEtran\.cls' main.log || true) \
	  && app=$$(pdftotext -layout main.pdf - | awk -v RS='\f' '/^Appendix A/{print NR; exit}') \
	  && echo "  pages $$n (want 18), errors $$err (want 0), bundled class used $$cls (want 1), appendix starts p$$app (want 14)" \
	  && [ "$$n" = 18 ] && [ "$$err" = 0 ] && [ "$$cls" -ge 1 ] && [ "$$app" = 14 ] \
	  && echo "  PRISM BUNDLE OK" || { echo "  PRISM BUNDLE FAILED"; exit 1; }

verify:
	$(PY) scripts/check_completeness.py
	$(PY) scripts/aggregate.py | grep -q FAIL && { echo "ASSERTION FAILURE"; exit 1; } || true
	$(PY) scripts/verify_paper_claims.py

clean-derived:
	rm -f $(MAN)/generated/*.tex $(MAN)/generated/floats/*.tex $(MAN)/figures/*.pdf
