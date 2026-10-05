#!/usr/bin/env bash
# Chain the remaining queue behind the jobs already in flight.
#
# Waits on MARKER STRINGS in each job's log, not on pgrep: a pgrep pattern for
# "the experiment driver" also matches the waiting shell's own command line, so
# the wait never returns. Learned the hard way.
set -u
cd "$(dirname "$0")/.."
M=logs/chain.log; log(){ echo "[$(date +%H:%M:%S)] $*" >> $M; }; : > $M

wait_for() {  # wait_for <logfile> <marker> <label>
  log "waiting on $3"
  local n=0
  until grep -q "$2" "$1" 2>/dev/null; do
    sleep 30; n=$((n+1))
    [ $((n % 60)) -eq 0 ] && log "  still waiting on $3 ($((n/2)) min)"
    [ $n -gt 2880 ] && { log "  TIMEOUT on $3 after 24h"; return 1; }
  done
  log "  $3 done"
}

wait_for logs/nbaiot9.log  "NBAIOT9 COMPLETE"  "nbaiot9"
wait_for logs/followup.log "FOLLOWUP COMPLETE" "followup"

log "=== k=3 full enumeration ==="
bash scripts/run_k3_full.sh || log "k3full FAILED"

log "=== audit + regenerate ==="
python3 scripts/check_completeness.py >> $M 2>&1 || log "completeness FAILED"
python3 scripts/manifest.py          >> $M 2>&1 || log "manifest FAILED"
# gen_instruments must run AFTER nb9 lands so the matched contrast uses the
# nine-device numbers rather than the five-device subsample.
python3 -W ignore scripts/gen_instruments.py > logs/instruments.log 2>&1 || log "instruments FAILED"
# gen_crossdataset must follow gen_instruments: it reads instruments.jsonl.
for g in gen_paper_numbers gen_e3 gen_e7 gen_e7_stats gen_e8 gen_e9 gen_e12 \
         gen_e14_deployable gen_crossdataset gen_teaser gen_appendix gen_inventory_table; do
  [ -f "scripts/$g.py" ] && { python3 scripts/$g.py >> $M 2>&1 || log "  $g FAILED"; }
done
python3 manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/charts/make_figures_v2.py >> $M 2>&1 || log "figures FAILED"
python3 scripts/verify_paper_claims.py >> $M 2>&1 || log "verify_paper_claims FAILED"

log "=== rebuild ==="
# Same sequence finish_all.sh uses; there is no render.sh in this workspace.
( cd manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  bibtex main >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 ) || log "render FAILED"
log "pages: $(pdfinfo manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/main.pdf 2>/dev/null | awk '/^Pages/{print $2}')"
log "CHAIN COMPLETE"
