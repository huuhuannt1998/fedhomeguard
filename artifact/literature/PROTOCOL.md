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

---

## Round 2 (2026-09-03): wider screen for the negative claim

Round 1 coded three defences in full against the codebook above. That is enough
to motivate two design choices, but not enough to support the manuscript's
*negative* claim that no guarantee quantifying over a threat class has been
carried into this application. Round 2 widens the base for that claim only.

**What round 2 is.** A screen, not a full coding. Every record is coded on one
field -- whether its abstract asserts a guarantee holding for every attack in a
stated threat class -- plus the inclusion decision. All other codebook fields
are null at this source level and are not guessed. The manuscript states it as a
screen.

**Why one field is defensible at abstract level.** A certified-robustness result
is a headline contribution; when a paper has one, it appears in the abstract.
The screen therefore establishes the narrower claim that the guarantee is not
being advertised, which is what the manuscript asserts.

**Retrieval.** arXiv API, four queries combining `"federated learning"` with
`"intrusion detection"` / IoT / `"network intrusion"` and one of
`poisoning` / `"malicious clients"` / `Byzantine` / `backdoor`.
Retrieved 50 distinct records. Records are generated into
`inventory_r2.yaml` directly from the API response by
`scripts/build_inventory_r2.py` and are never hand-typed, so no entry can be
invented and the screen re-runs.

**Screening.** 24 of the 50 match federated learning, intrusion detection and
client poisoning together. 6 are then excluded under the criteria above, each
with the deciding phrase recorded: four fail I3 because the matched term names
the threat being *detected* (a backdoor intrusion, a compromised device) rather
than a threat to training, and two fail E3 as a survey or SoK. 18 remain; merged
with round 1 (one overlap, WeiDetect) that is **20 distinct records**.

**Result.** 2 of the 18 abstracts use the language of guarantees at all. In
`arXiv:2512.23809` it attaches to Byzantine *detection* ("SHAP-weighted
aggregation providing explainable Byzantine detection ... with theoretical
guarantees"); in `arXiv:2601.01053` it is differential privacy ("excludes
Byzantine participants while maintaining differential privacy guarantees").
**0 assert a property holding for every attack in a stated threat class.**

**Known limits of round 2.**
- arXiv only. Records that appear solely in publisher-indexed venues
  (ScienceDirect, Springer, IEEE Xplore) are not covered. One such record,
  "Federated Learning with Provable Security Against Malicious Clients in IoT
  Networks" (IEEE Xplore 10474836), was surfaced by web search and is
  **retrieval-blocked** at every reachable source, as `fedidsdp2025` was in
  round 1. Its title asserts provable security; the description reachable
  outside the paywall attributes it to a kernel-density detection-and-threshold
  method, which would code as detection rather than certified prediction, but
  that is an inference from a secondary source and is **not counted** either way.
- Abstract-level only, so a paper proving a certificate but not advertising it
  would be missed.
- Inclusion is coded, but from abstracts; a full-text reading could move records
  either way.
