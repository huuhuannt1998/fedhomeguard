#!/usr/bin/env bash
#
# Single entry point for the remaining experiment re-runs.
#
# DESIGNED FOR A SHARED MACHINE. This laptop runs several projects at once and a
# previous attempt contributed to a crash, so every stage here is sequential, niced
# to the lowest priority, and pinned to one BLAS thread. Nothing runs in parallel
# with anything else, and no Docker container is started.
#
# CRASH-SAFE BY CONSTRUCTION. The earlier runner deleted a target and then
# regenerated it, so an interruption left nine files deleted and three half-written.
# Here each stage writes to a scratch file and only moves it into place after it
# passes a grid check against the pre-fix backup. An interrupted stage therefore
# leaves the existing result untouched.
#
# RESUMABLE. A stage whose target already differs from the backup is considered
# done and is skipped, so re-invoking this after an interruption continues rather
# than restarting.
#
#   bash scripts/run_experiments.sh --plan     # print what would run, run nothing
#   bash scripts/run_experiments.sh            # run the remaining stages
#   bash scripts/run_experiments.sh -j 3       # up to three stages at once
#   bash scripts/run_experiments.sh e9 e3      # run only the named stages
set -u
cd "$(dirname "$0")/.."
PY=/Users/huanbui/miniconda3/bin/python3
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PATH="/Users/huanbui/miniconda3/bin:$PATH"
NICE="nice -n 19"
BK=results/pre_determinism_fix
CAN=results/canonical
M=logs/experiments.log
mkdir -p logs "$CAN" results/scratch
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$M"; }

B="0 0.05 0.1 0.2 0.3 0.4"
BF="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
KC12="1:20,2:190"

# stage name | target files (space separated) | estimated minutes
STAGES="e9:e9_logreg_iid e9_logreg_device_derived:12
e11:e11_dph1_1 e11_dph2_5:6
e10:e10_N10_iid e10_N10_device_derived e10_N50_iid e10_N50_device_derived:14
e4:e4_highinf_iid e4_highinf_device_derived:10
e13:e13_iid e13_device_derived:9
e3:e3_iid e3_device_derived:45
nb9samepred:nb9_iid nb9_device_derived:70
nbcert:nb_cert_iid nb_cert_device_derived:25
nbsamepred:nb_iid nb_device_derived:65"

done_already(){  # a target is done when it differs from the pre-fix backup
  for f in $1; do
    [ -f "$CAN/$f.jsonl" ] || return 1
    [ -f "$BK/$f.jsonl" ]  || continue
    cmp -s "$CAN/$f.jsonl" "$BK/$f.jsonl" && return 1
  done
  return 0
}

# Run one experiment into scratch, then swap it in only if it looks complete.
# $1 target basename, rest = command
guarded(){
  local tgt="$1"; shift
  local scratch="results/scratch/$tgt.jsonl"
  rm -f "$scratch"
  "$@" || { log "    FAILED $tgt (target left untouched)"; return 1; }
  local n; n=$(grep -c '^{' "$scratch" 2>/dev/null || echo 0)
  if [ "$n" -lt 1 ]; then log "    EMPTY $tgt (target left untouched)"; return 1; fi
  local ref=$BK/$tgt.jsonl
  if [ -f "$ref" ]; then
    local want; want=$(grep -c '^{' "$ref")
    if [ "$n" -lt "$want" ]; then
      log "    SHORT $tgt ($n < $want rows) -- target left untouched"; return 1
    fi
  fi
  mv "$scratch" "$CAN/$tgt.jsonl"; log "    ok $tgt ($n rows)"
}

stage_e9(){ for P in iid device_derived; do
  guarded "e9_logreg_$P" $NICE $PY scripts/exp_e2.py --partition $P --arch logreg \
    --tag E9_logreg --pseed 0 1 2 --k 1 2 --betas $B --k-caps "$KC12" \
    --out results/scratch/e9_logreg_$P.jsonl; done; }

stage_e11(){ for SPEC in "1 1:1_1" "2 5:2_5"; do D=${SPEC%%:*}; T=${SPEC##*:}
  guarded "e11_dph$T" $NICE $PY scripts/exp_e2.py --partition device_derived --dph $D \
    --tag E11_dph${T} --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "$KC12" \
    --out results/scratch/e11_dph$T.jsonl; done; }

stage_e10(){ for NN in 10 50; do for P in iid device_derived; do
  guarded "e10_N${NN}_$P" $NICE $PY scripts/exp_e2.py --partition $P --N $NN \
    --tag E10_N${NN} --pseed 0 1 2 --k 1 2 3 --betas $B --clean-only \
    --k-caps "1:$NN,2:200,3:200" --out results/scratch/e10_N${NN}_$P.jsonl; done; done; }

stage_e4(){ for P in iid device_derived; do
  guarded "e4_highinf_$P" $NICE $PY scripts/exp_e2.py --partition $P --pseed 0 1 2 \
    --k 1 2 --betas 0.05 0.1 0.2 0.3 0.4 --mal-mode high_volume rare_device \
    --k-caps "$KC12" --out results/scratch/e4_highinf_$P.jsonl; done; }

stage_e13(){ for P in iid device_derived; do
  guarded "e13_$P" $NICE $PY scripts/exp_e3_defenses.py --partition $P --pseed 0 1 2 \
    --betas 0.1 0.2 --mal-seeds 0 --scales 0.5 1.0 5.0 \
    --defenses norm_clip median multikrum --out results/scratch/e13_$P.jsonl; done; }

stage_e3(){ for P in iid device_derived; do
  guarded "e3_$P" $NICE $PY scripts/exp_e3_defenses.py --partition $P --pseed 0 1 2 \
    --betas $B --mal-seeds 0 1 2 --scales 0.5 1.0 5.0 \
    --out results/scratch/e3_$P.jsonl; done; }

stage_nb9samepred(){ for P in iid device_derived; do
  guarded "nb9_$P" $NICE $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml \
    --partition $P --pseed 0 1 2 --k 1 2 --betas $B --mal-seeds 0 1 2 \
    --k-caps "$KC12" --dph 1 2 --tag NBAIOT9_SAMEPRED \
    --out results/scratch/nb9_$P.jsonl; done; }

# nb_* is the five-device N-BaIoT subsample, retained as a robustness check
stage_nbcert(){ for P in iid device_derived; do
  guarded "nb_cert_$P" $NICE $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml \
    --partition $P --pseed 0 1 2 3 4 --k 1 2 --betas $BF --clean-only \
    --k-caps "$KC12" --dph 1 2 --tag NBAIOT_CERT \
    --out results/scratch/nb_cert_$P.jsonl; done; }

stage_nbsamepred(){ for P in iid device_derived; do
  guarded "nb_$P" $NICE $PY scripts/exp_e2.py --config configs/stage0_nbaiot.yaml \
    --partition $P --pseed 0 1 2 --k 1 2 --betas $B --mal-seeds 0 1 2 \
    --k-caps "$KC12" --dph 1 2 --tag NBAIOT_SAMEPRED \
    --out results/scratch/nb_$P.jsonl; done; }

PLAN=0; JOBS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --plan) PLAN=1; shift ;;
    -j)     JOBS="$2"; shift 2 ;;
    *)      break ;;
  esac
done
WANT="$*"
total=0
echo "stage         targets                                        est  status"
while IFS= read -r line; do
  name=${line%%:*}; rest=${line#*:}; files=${rest%:*}; mins=${rest##*:}
  [ -n "$WANT" ] && ! echo " $WANT " | grep -q " $name " && continue
  if done_already "$files"; then st="done (skip)"; else st="TO RUN"; total=$((total+mins)); fi
  printf "  %-12s %-46s %3sm  %s\n" "$name" "$(echo $files | cut -c1-46)" "$mins" "$st"
done <<< "$STAGES"
echo "  estimated remaining: ${total} min (sequential, nice -n 19, one BLAS thread)"
[ "$PLAN" = 1 ] && { echo; echo "--plan: nothing was run."; exit 0; }

log "=== run_experiments start (concurrency $JOBS) ==="
# Batches of $JOBS. bash 3.2 here has no `wait -n`, so each batch is launched and
# waited on as a group -- less optimal than a rolling pool but correct, and stages
# never contend because each writes only its own scratch file.
PEND=""
for_each_pending(){
  while IFS= read -r line; do
    name=${line%%:*}; rest=${line#*:}; files=${rest%:*}
    [ -n "$WANT" ] && ! echo " $WANT " | grep -q " $name " && continue
    if done_already "$files"; then log "skip $name (already re-run)"; continue; fi
    PEND="$PEND $name"
  done <<< "$STAGES"
}
for_each_pending
n=0
for name in $PEND; do
  log "stage $name (started)"
  ( "stage_$name" ) &
  n=$((n+1))
  if [ $((n % JOBS)) -eq 0 ]; then wait; log "  -- batch of $JOBS finished --"; fi
done
wait
log "=== run_experiments complete ==="
$PY scripts/compare_rerun.py 2>&1 | tail -6 | tee -a "$M"
