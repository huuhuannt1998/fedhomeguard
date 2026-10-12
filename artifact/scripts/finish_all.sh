#!/bin/bash
# Sequential runner. Uses a marker file rather than pgrep for completion, because
# pgrep patterns matched the waiter shells themselves and deadlocked the chain.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
M=logs/finish_all.log
log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }
: > $M

log "=== 1/4 volume skew (Experiment C) ==="
bash scripts/run_volume.sh >> logs/volume.log 2>&1 || log "volume FAILED"
log "volume rows: $(wc -l < results/canonical/e7_volskew.jsonl 2>/dev/null || echo 0)"

log "=== 2/4 k=5,8 ==="
bash scripts/run_k58.sh >> logs/k58.log 2>&1 || log "k58 FAILED"
log "k58 files: $(ls results/canonical/ | grep -c k58 || echo 0)"

log "=== 3/4 regenerate ==="
python3 scripts/check_completeness.py >> $M 2>&1
python3 scripts/manifest.py           >> $M 2>&1
for g in gen_paper_numbers gen_inventory_table gen_e3 gen_e7 gen_e7_stats \
         gen_e9 gen_e12 gen_e14_deployable gen_e8 gen_appendix; do
  python3 scripts/$g.py >> $M 2>&1 || log "generator FAILED: $g"
done
python3 manuscript/charts/make_figures_v2.py >> $M 2>&1
python3 scripts/annotate_provenance.py >> $M 2>&1

log "=== 4/4 rebuild ==="
cd manuscript
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
bibtex main >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
cd ../../..
log "pages: $(pdfinfo manuscript/main.pdf | awk '/^Pages/{print $2}')"
log "FINISH_ALL COMPLETE"

