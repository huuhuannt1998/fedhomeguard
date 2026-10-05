# Reading guide — FedHomeGuard, IEEE S&P

Written for the one check the paper does not have: an independent reader. Every
gate, detector and predeclaration in this project was authored by the same agent
that wrote the prose, so none of them is independent of it. What follows is not
a summary. It is the list of **decisions** that were made on your behalf and the
**places the evidence is thinnest**, so your read goes where it is worth going.

Read the PDF first, without this open. Then use this to check what you noticed
against what I already know is soft.

---

## 1. Decisions made on your behalf — ratify or overturn

These were judgment calls, not derivations. Each changes what the paper claims.

| # | Decision | Where | If you disagree |
|---|---|---|---|
| D1 | **Title** reframed to what holds, not what fails: *"When Client-Count Certification Holds for Federated IoT Intrusion Detection"* | title | Reverting is a one-line change; the abstract and §I follow the same positive-first order and would need re-ordering too. |
| D2 | **Headline is the mechanism, not the curve.** The paper leads on *why* certification holds (class coverage per member), with the two corpora as evidence, rather than on the IoT-23 numbers. | abstract, §I, §XIII | The alternative is a measurement paper on one corpus. Weaker claim, less reviewer risk. |
| D3 | **Abstract says "holds outside one regime"** rather than naming the regime immediately. | abstract ¶2 | The regime is named in ¶3. Moving it earlier costs the positive-first order D1 buys. |
| D4 | **τ_triv = 0.7300** (IoT-23 majority-class rate) as the collapse criterion. | §V | Any other floor changes every collapse count and β*. This is the single most load-bearing constant in the paper. |
| D5 | **β\* estimator**: per-draw first (median over malicious sets), aggregate last. | `scripts/bstar.py` | Reversing the order changes β* materially. An earlier draft had both and produced three different numbers for one quantity. |
| D6 | **`nb_*` retired** as a configuration-identical duplicate of `nb9_*` rather than re-run. | `results/.superseded_preC1/` | Archived, not deleted. Recoverable. |

---

## 2. Where the evidence is thinnest — a reviewer will find these

Listed worst-first. All are disclosed in the paper; none is hidden. The question
is whether the disclosure is *enough*.

**T0. Prior work is anchored on its weakest fraction, and the appendix contradicts it.**
The abstract, §III and §XIII all characterise certified FL prediction by Cao et
al.'s 88%-at-2% point; §III calls the distance to the 10-40% band "five- to
twentyfold". But Appendix A.7 cites and *reproduces against* FLCert 2022 at
β = 0.10 with certified accuracy 0.81 -- the bottom edge of that band. The 10%
point is never stated in the main text. A reviewer who reads A.7 will find it,
and the "five- to twentyfold" arithmetic is then wrong by construction (2% vs
10% is fivefold; 10% vs 10% is none). The negative claim itself survives -- it
is about the 20 IDS defences, not FLCert -- but the framing of how far prior
certification reaches does not. Found by the reviewer pass, missed by the
18-mode audit, which checked that 88% was *cited* and not that it was the
*fair* operating point to cite. **Decide:** see the review's proposed rewrite.

**T1. The deployment-assumption inventory is n = 3 — but correctly scoped.**
Appendix A.6 rests on 3 coded papers, with denominators of 3 and 2. I first
flagged this as a thin evidential base. Reading the body sentence, it is not
used as one: "A 3-paper coded sample supports *two design choices and no
result* ... hence the lattice of Section 2 and the skew instrument of Section 5.
The negative claim rests on a wider screen." So n=3 motivates two instruments
and carries no finding, and the abstract's negative claim runs on the 20-record
screen instead. **Decide:** whether a reviewer skimming Appendix A.6 will see
that separation as fast as the body states it, or whether the "no result"
scoping should be repeated at the appendix table. That is a presentation call,
not an evidence gap. (I record this because my first pass on it was wrong, and
a guide that overstates a risk is as costly to your read as one that misses it.)

**T2. Two corpora.** IoT-23 and N-BaIoT. The mechanism claim ("device identity
carries label information, or it does not") rests on a 2-point contrast. It is a
strong contrast — span 0.450 vs 0.000 on an identical grid at matched skew — but
it is two points. §XI states this.

**T3. The k = 2 richness result is hours old.** It changed §VII and added a
deployment recommendation (raise k when homes are device-poor, pay in headroom).
No human has read that subsection. It is the newest and least-reviewed prose in
the paper.

**T4. One model family.** Everything is the same architecture. §XI carries the
model-dependence caveat; a reviewer may want a second family.

**T5. Single laptop, no accelerator.** Disclosed in §VI as a compute envelope.
Constrains N and K, which constrains which cells could be enumerated exactly.

---

## 3. What is predeclared — and what failed

Two predeclarations were committed **before** the runs, in `predeclarations/`.

- `richness_nbaiot.md` (commit `bafca46`) — prediction confirmed. β\* flat at the
  ceiling across the whole grid; span 0.000 against IoT-23's 0.450.
- `richness_k2.md` (commit `98895d7`) — **P1 and P3 passed, P2 FAILED.** I
  predicted both k would sit at ≥0.8 of their ceiling from 2–5 device types
  upward. k=1 is at 0.67. They do not converge until 3–8.

**The P2 failure is deliberately left in the record.** The paper claims the
k-dependence, which the data shows — not the convergence I predicted and did not
get. If a reviewer asks whether the richness analysis was post hoc, that file is
the answer, and it is more credible for containing a miss.

Check that §VII claims only the k-dependence and does not quietly claim the
convergence. That is the single most important sentence-level check in the paper.

I checked it and it passes: §VII reads "reaches its own ceiling by 2-5 types
*where k = 1 needs 5-10*", which states the divergence rather than the
convergence P2 predicted. Verify it anyway -- I am the one who both made the
prediction and wrote the sentence that reports it.

---

## 4. What is verified mechanically (so you can skip it)

Do not spend your read re-checking these. They are gated on every build:

- numbers agree across macros, tables and prose (gates 2, 5, 7)
- no undefined references, no unresolved macros in the PDF (gates 1, 1c)
- certified accuracy never exceeds attacked accuracy in any consumed row (gate 3)
- page budget 13 text / 5 refs+appendix / 18 total (gate 4)
- no duplicated floats (gate 6) — this one caught a table rendered twice
- 22 bib entries, 22 cited, no dangling keys
- artifact carries zero rows with the superseded `G_cert` column (was 122)

---

## 5. Known open items

- N-BaIoT at k=2 — DONE. Predeclared in `7f41a65`, P1/P2/P3 all pass: β\* = 0.250
  on all 150 draws (min = max at every level), span 0.000 against IoT-23's 0.250
  at the same k. Numbers are in `generated/nbk2rich_macros.tex` and NOT YET in
  the prose; that is the one piece of new evidence the paper does not yet state.
- `generated/limitations_appendix.tex` is `\input` by nothing, marked SUPERSEDED.
  Safe to delete; kept so the earlier wording stays recoverable.
- `manuscripts/` is gitignored by your directive, so the prose has no version
  history. The export folder and zip are the only backup.
