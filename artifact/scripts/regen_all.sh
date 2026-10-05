#!/usr/bin/env bash
# Regenerate every derived .tex from results/canonical.
#
# This repo genuinely needs TWO interpreters and nothing said so:
#   * gen_paper_numbers / gen_richness / ... use PEP 701 nested quotes in
#     f-strings, so they REQUIRE Python >= 3.12;
#   * gen_teaser / gen_e8 / gen_instruments / gen_inventory_table import
#     matplotlib / torch / numpy, which are installed only under the system
#     Python 3.9.
# The previous version called bare `python3`, so which generators ran at all
# depended on PATH -- and it logged "FAILED" and exited 0, so a stale
# numbers.tex could survive a regen silently. Try each interpreter per
# generator; fail loudly only when none can run it.
set -u; cd "$(dirname "$0")/.."
L=logs/regen.log; : > $L
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }

CANDS=()
for c in "${PY:-}" python3.14 python3.13 python3.12 /opt/homebrew/bin/python3 \
         /usr/bin/python3 python3; do
  [ -n "$c" ] || continue
  command -v "$c" >/dev/null 2>&1 || continue
  case " ${CANDS[*]:-} " in *" $c "*) continue;; esac
  CANDS+=("$c")
done
[ ${#CANDS[@]} -gt 0 ] || { log "FATAL: no python found"; exit 2; }
log "=== regen start (candidates: ${CANDS[*]}) ==="

rc=0
for g in gen_paper_numbers gen_e3 gen_e7 gen_e7_stats gen_e8 gen_e9 gen_e12 \
         gen_e14_deployable gen_crossdataset gen_realstack_macros gen_teaser \
         gen_richness gen_instruments gen_appendix gen_inventory_table; do
  [ -f scripts/$g.py ] || continue
  ok=""
  for PYBIN in "${CANDS[@]}"; do
    if "$PYBIN" scripts/$g.py >>$L 2>&1; then ok="$PYBIN"; break; fi
  done
  if [ -n "$ok" ]; then log "  ok $g  [$ok]"; else log "  FAILED $g (no interpreter could run it)"; rc=1; fi
done
if [ $rc -ne 0 ]; then
  log "=== regen INCOMPLETE -- generated/ may be stale; see $L ==="
  exit 1
fi
log "=== regen complete ==="
