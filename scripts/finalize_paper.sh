#!/usr/bin/env bash
# Regenerate every derived artifact from the canonical results, verify, rebuild.
# Runs only after run_experiments.sh reports complete. Cheap -- no training.
set -u
cd "$(dirname "$0")/.."
PY=/Users/huanbui/miniconda3/bin/python3
export PATH="/Users/huanbui/miniconda3/bin:/Library/TeX/texbin:/opt/homebrew/bin:$PATH"
MAN=manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP
M=logs/finalize.log; : > $M
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $M; }
FAIL=0

log "=== audit ==="
$PY scripts/check_completeness.py  >> $M 2>&1
$PY scripts/manifest.py            >> $M 2>&1
log "=== regenerate ==="
$PY scripts/gen_instruments.py > logs/instruments.log 2>&1
for g in gen_paper_numbers gen_e3 gen_e7 gen_e7_stats gen_e8 gen_e9 gen_e12 \
         gen_e14_deployable gen_crossdataset gen_realstack_macros gen_teaser \
         gen_appendix gen_inventory_table; do
  [ -f scripts/$g.py ] && { $PY scripts/$g.py >> $M 2>&1 || log "  $g FAILED"; }
done
$PY $MAN/charts/make_figures_v2.py >> $M 2>&1 || log "  figures FAILED"
log "=== verify ==="
$PY scripts/verify_paper_claims.py 2>&1 | tail -2 | tee -a $M
ASSERT=$($PY scripts/aggregate.py 2>&1 | grep -c PASS)
log "  canonical assertions passing: ${ASSERT}/10"
[ "$ASSERT" -eq 10 ] || { log "  BLOCK: assertions ${ASSERT}/10"; FAIL=1; }
$PY -m pytest -q 2>&1 | tail -1 | tee -a $M
( cd $MAN && $PY charts/texlint.py 'sections/*.tex' 2>&1 | tail -1 ) | tee -a $M
( cd $MAN && $PY /Users/huanbui/rka/plugin/skills/writer/scripts/verify_provenance.py \
    sections/*.tex --project prj_01M0EE73RTCAK0JNGD4SY4A1Y2 2>&1 \
  | $PY -c "import json,sys;print('  provenance:',json.load(sys.stdin)['summary'])" ) | tee -a $M
log "=== rebuild ==="
( cd $MAN
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  bibtex main >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 )
( cd $MAN && pdftotext -layout main.pdf - | $PY -c "
import sys,re
pg=sys.stdin.read().split('\f'); n=len([p for p in pg if p.strip()])
app=next(i for i,p in enumerate(pg,1) if re.search(r'(?m)^\s*A\.\d\.',p))
t,a,tot = app-1, n-app+1, n
print(f'  TEXT {t}/13   APP+REFS {a}/5   TOTAL {tot}/18')
bad=[x for x,lim,nm in ((t,13,'TEXT'),(a,5,'APP+REFS'),(tot,18,'TOTAL')) if x>lim]
sys.exit(3 if bad else 0)" ) | tee -a $M
[ ${PIPESTATUS[0]:-0} -eq 0 ] || { log "  BLOCK: over IEEE S&P page limit"; FAIL=1; }
log "=== delta against pre-fix ==="
$PY scripts/compare_rerun.py 2>&1 | tail -6 | tee -a $M
if [ "${FAIL:-0}" -ne 0 ]; then log "FINALIZE COMPLETE WITH BLOCKERS"; exit 1; else log "FINALIZE COMPLETE"; fi
