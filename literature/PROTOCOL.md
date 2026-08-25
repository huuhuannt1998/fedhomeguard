# Systematic inventory of federated IoT/network intrusion-detection robustness claims

Review requirement: section 24. The manuscript's claims about what this literature
does and does not guarantee are only as good as a documented, reproducible audit.
This file is that audit's protocol; `inventory.yaml` is its result.

## Search

- **Search dates:** 2026-08-24.
- **Engines:** Anthropic web search (Google-backed index); arXiv listing search;
  publisher sites (ScienceDirect, Springer, IEEE Xplore, PeerJ, MDPI) for records
  surfaced by those queries.
- **Queries** (verbatim):
  1. `federated learning IoT intrusion detection poisoning attack robust aggregation
     defense evaluation malicious clients`
  2. `"federated learning" IoT intrusion detection Byzantine robust aggregation Krum
     trimmed mean non-IID survey 2023 2024 2025`
  3. `arxiv federated learning intrusion detection IoT poisoning defense label
     flipping malicious clients percentage evaluated` (restricted to arxiv.org)
  4. `federated learning network intrusion detection certified robustness guarantee
     provable malicious clients`
- **Date range:** no lower bound; the field's first FL-IoT-IDS systems appear in 2019.

## Inclusion criteria

A record is INCLUDED when all of the following hold.

- I1. It trains an intrusion / anomaly detector for network or IoT traffic.
- I2. Training is federated across multiple clients.
- I3. It proposes, evaluates, or defends against **training-time poisoning by
  malicious clients** (label flipping, model poisoning, backdoor, Byzantine
  updates). Test-time evasion alone does not qualify.

## Exclusion criteria

- E1. Federated IDS with no adversarial-client component (privacy or accuracy only).
- E2. Poisoning work with no intrusion-detection application.
- E3. Surveys and position papers with no primary evaluation of their own.
- E4. Records not retrievable at at least abstract level.

## Coding rules

Two rules decide most of the contested cells and are stated before coding.

**`skew_measured`.** YES only when the paper reports a *numerical statistic of the
realised client distributions* (e.g. a Jensen-Shannon or KL divergence, an earth
mover's distance, a Gini/entropy over client histograms). A Dirichlet concentration
parameter, a "non-IID" label, a shards-per-client count, or a per-class sample table
is a **generative knob or a raw tabulation, not a measurement of realised divergence**,
and is coded NO with the knob recorded in `skew_knob`. This distinction is the one the
manuscript relies on, so it is fixed in advance.

**`observability`.** The highest level the *defence as proposed* requires.
- `L0` — server sees only the aggregate.
- `L1` — server sees individual client updates.
- `L2` — server additionally requires a **clean, correctly labelled server-side
  dataset** (called a root set, validation set, probe set, auxiliary set, or trusted
  test set). Any such requirement forces L2 regardless of how small the set is.
- `L3` — server is told which clients are malicious (oracle; upper bound only).

**`guarantee_type`.** `none` | `convergence` | `privacy` | `byzantine_statistical`
(an estimation-error or convergence bound under a bounded-Byzantine assumption) |
`certified_prediction` (for every adversarial behaviour in a stated threat class, a
stated prediction or accuracy property provably holds).

**`source_level`.** `full_text` when the evaluation section was read;
`abstract_only` when only the abstract was retrievable. Fields that could not be
determined at the available level are recorded as `null`, never guessed. Any claim
the manuscript makes must be restricted to records where the relevant field is
non-null, and the denominator must be stated.

## Status

This inventory is **not exhaustive** and the manuscript must not describe it as
such. It is a documented, reproducible sample. Every universal statement in the
paper is scoped to it explicitly, with the denominator given.
