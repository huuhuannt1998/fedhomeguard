#!/usr/bin/env bash
# JISA training round (PI go-ahead 2026-10-20). Predeclarations: predeclarations/jisa_X1_X2_X4_seeds_budget_multiclass.md,
# jisa_JS02_JS03_size_capacity.md (JS01 runs separately, after its loader exists). At most 4 processes at a time,
# niced: HOMEPROV shares the machine. Every step is restart-safe (rows already written are skipped).
set -u
cd "$(dirname "$0")/.."
PY=${PY:-python3}
L=logs/jisa_train.log
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$L"; }
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
SEEDS=$(seq -s' ' 10 39)
mkdir -p results/jisa logs

log "=== phase 1: X1 coverage-repair seeds 1-4 and X2 step-budget arms (jisa_x_runs.py, 4 workers) ==="
nice -n 10 $PY scripts/jisa_x_runs.py --workers 4 >> logs/jisa_x_runs.log 2>&1 && log "  ok x_runs" || log "  FAILED x_runs"

log "=== phase 2: X1 main-grid member seeds, JS02 federation size, JS03 member capacity (4 at a time) ==="
CMDS=logs/jisa_train_cmds.txt; : > "$CMDS"
for S in 1 2 3 4; do
  for P in device_derived iid; do
    echo "$PY scripts/exp_e2.py --partition $P --pseed $SEEDS --k 1 2 --betas $B --clean-only --k-caps 1:20,2:190 --tag JISA_X1_S$S --member-seed $S --out results/jisa/x1_main_${P}_s$S.jsonl" >> "$CMDS"
  done
done
for P in device_derived iid; do
  echo "$PY scripts/exp_e2.py --partition $P --pseed $SEEDS --k 1 2 --betas $B --N 10 --clean-only --k-caps 1:10,2:45 --tag JISA_JS02_N10 --out results/jisa/js02_N10_$P.jsonl" >> "$CMDS"
  echo "$PY scripts/exp_e2.py --partition $P --pseed $SEEDS --k 1 --betas $B --N 50 --clean-only --k-caps 1:50 --tag JISA_JS02_N50 --out results/jisa/js02_N50_$P.jsonl" >> "$CMDS"
  echo "$PY scripts/exp_e2.py --partition $P --pseed $SEEDS --k 1 --betas $B --arch mlp_large --clean-only --k-caps 1:20 --tag JISA_JS03_LARGE --out results/jisa/js03_large_$P.jsonl" >> "$CMDS"
done
# X4 (deviation of 2026-10-20 in the predeclaration): the 8-class arms at k = 1 with the fixed per-family metric
for P in device_derived iid; do
  echo "$PY scripts/exp_e2.py --multiclass --partition $P --pseed $SEEDS --k 1 --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 --clean-only --k-caps 1:20,2:190 --tag JISA_X4 --out results/jisa/x4_multiclass_k1_$P.jsonl" >> "$CMDS"
done
log "  $(wc -l < "$CMDS") runs queued"
# macOS xargs -I caps the substituted command at 255 bytes, so each run becomes its own small script
RUNS=logs/jisa_train_runs; rm -rf "$RUNS"; mkdir -p "$RUNS"; i=0
while IFS= read -r c; do
  i=$((i + 1)); out=$(echo "$c" | sed -E 's/.*--out ([^ ]+).*/\1/'); name=$(basename "$out" .jsonl)
  printf '#!/usr/bin/env bash\ncd "%s"\nif nice -n 10 %s > logs/%s.log 2>&1; then echo "[$(date "+%%F %%T")]   ok %s" >> %s; else echo "[$(date "+%%F %%T")]   FAILED %s" >> %s; fi\n' \
    "$PWD" "$c" "$name" "$out" "$L" "$out" "$L" > "$RUNS/$(printf %02d $i)_$name.sh"
done < "$CMDS"
ls "$RUNS"/*.sh | xargs -P 4 -n 1 bash
log "=== complete ==="
