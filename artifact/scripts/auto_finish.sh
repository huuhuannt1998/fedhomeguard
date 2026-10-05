#!/bin/bash
# Waits for every experiment lane to drain, then regenerates every derived artifact
# and rebuilds the paper. Safe to run repeatedly; all generators are idempotent.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
log(){ echo "[$(date +%H:%M:%S)] $*" >> logs/autofinish.log; }

log "waiting for lanes"
while pgrep -f 'decensor_sweep.sh|run_volume.sh|run_k58.sh|chain_remaining.sh' >/dev/null; do
  sleep 60
done
log "lanes drained"

python3 scripts/check_completeness.py            >> logs/autofinish.log 2>&1
python3 scripts/manifest.py                      >> logs/autofinish.log 2>&1
for g in gen_paper_numbers gen_inventory_table gen_e3 gen_e7 gen_e7_stats \
         gen_e9 gen_e12 gen_e14_deployable gen_e8 gen_appendix; do
  log "generator: $g"
  python3 scripts/$g.py >> logs/autofinish.log 2>&1 || log "  FAILED: $g"
done
python3 manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/charts/make_figures_v2.py \
  >> logs/autofinish.log 2>&1
python3 scripts/annotate_provenance.py           >> logs/autofinish.log 2>&1

cd manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
bibtex main >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
cd ../../..
log "rebuilt: $(pdfinfo manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/main.pdf | awk '/^Pages/{print $2}') pages"
log "AUTO-FINISH COMPLETE"
