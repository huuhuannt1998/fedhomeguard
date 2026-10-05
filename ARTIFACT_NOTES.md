# Artifact notes

## The `G_cert` column in five result files is superseded

`results/canonical/` holds every run the paper draws on, plus arms it does not.
Five files carry a **superseded** `G_cert` column that can read negative:

    e2k58_iid_s1.jsonl
    e4_highinf_device_derived.jsonl
    e4_highinf_iid.jsonl
    nb9_iid.jsonl
    nb_iid.jsonl

**Why it can be negative.** `G_cert` was originally `EA_ensemble - CA`, where `CA`
is a final-round quantity but `EA_ensemble` was the *minimum over a window* of
rounds. The two therefore describe different predictors, and their difference is
not a certificate slack: it can come out below zero without anything being
unsound. The current definition is

    G_cert = min_over_attacks(EA_final_round) - CA

which compares the same predictor to itself. Every row in the five files above
now carries `"G_cert_estimator": "superseded_pre_C1"` and a `G_cert_note`, so the
column cannot be mistaken for the current one.

**Why they are not regenerated.** Those runs predate the `EA_final_round` field,
so the corrected value cannot be recomputed from what was recorded — only by
re-running the arms. None of the five is consumed by the paper.

**What the paper consumes.** The same-predictor results are `e2_*.jsonl` and
`e9_logreg_*.jsonl`. Across those, `scripts/paper_gates.py` (gate3) asserts
`G_cert >= 0` on every row and blocks the build otherwise; it currently reports
0 negatives in 360 rows. Gate3b reports the superseded rows separately without
blocking, so the distinction stays visible rather than silently tolerated.

Originals are preserved unmodified in `results/.backup_precC1/`.

## Reproducing the numbers in the paper

    ./scripts/regen_all.sh      # every generated/*.tex from results/canonical
    python3 scripts/paper_gates.py

`regen_all.sh` needs two interpreters and selects them per generator: the number
generators use PEP 701 f-strings (Python >= 3.12), while the plotting and
instrument generators import matplotlib/torch/numpy, which on the authors'
machine are installed under the system Python 3.9. It fails loudly if no
interpreter can run a generator.

## The one definition of beta*

`scripts/bstar.py` is the single definition of the certified breakdown point:

    beta*(draw) = max{ beta : median over malicious sets of CA(draw, beta) > tau_triv }
    beta*       = median over draws of beta*(draw)

Two generators previously computed this two different ways -- per-draw-then-median
versus median-then-per-draw -- and the paper printed both. Gate5 now asserts that
every table reporting the same quantity agrees.
