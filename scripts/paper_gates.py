#!/usr/bin/env python3
"""Three gates for defect classes that shipped in the round-1 draft.

1. An undefined \ref renders as "??" in the PDF. One shipped.
2. A four-decimal literal in prose is a number that cannot go stale-proof: nine
   of them had drifted away from the macros that were supposed to carry them.
3. CA is the final-round predictor and EA_ensemble is a window minimum, so their
   difference mixed estimators and went negative next to a proof that it cannot.
"""
import glob, json, os, re, sys

MAN = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP"
fail = []

# ---- gate 1: undefined references
log = os.path.join(MAN, "main.log")
if os.path.exists(log):
    txt = open(log, errors="ignore").read()
    und = re.findall(r"Reference `([^']+)' on page (\d+) undefined", txt)
    for name, pg in und:
        fail.append(f"undefined reference '{name}' on page {pg} -> renders as ?? in the PDF")
    # A missing macro is WORSE than a missing \ref: \ref prints "??", but an
    # undefined control sequence prints nothing, leaving a fluent sentence with the
    # number silently removed. latexmk in nonstopmode still emits a PDF.
    bang = [l for l in txt.split("\n") if l.startswith("! ")]
    for l in bang[:10]:
        fail.append(f"hard TeX error: {l.strip()}")
    print(f"  gate1 undefined refs : {len(und)} {'FAIL' if und else 'pass'}")
    print(f"  gate1b TeX errors    : {len(bang)} {'FAIL' if bang else 'pass'}")

# ---- gate 2: four-decimal literals in prose
#      \newcommand bodies and provenance comments are exempt; so are the analytic
#      ceilings in Table 1, which are algebra rather than measurements.
EXEMPT = {"0.450", "0.250", "0.150", "0.100", "0.050", "0.293", "0.206",
          "0.120", "0.129", "0.500", "0.083", "0.034",  # analytic ceilings, Table 1
          "0.002"}   # a stated upper bound in Sec. VIII, not a table reading
hits = []
# A generator rewrites its own paragraph from the corpus on every run, so a literal
# there IS the computed value and cannot go stale. Hand-authored prose is the risk,
# wherever it lives -- C6 was a stale number inside a GENERATED file's template, which
# is why the generator SOURCE is linted separately rather than its output.
GENERATED = {"e3_paragraph.tex", "e7_paragraph.tex", "e8_paragraph.tex",
             "e9_paragraph.tex", "e12_paragraph.tex", "deployable_paragraph.tex",
             "e7_stats.tex",
             "appendix.tex", "inventory_appendix.tex"}
SCAN = [f for f in sorted(glob.glob(os.path.join(MAN, "sections", "*.tex"))) +
                  sorted(glob.glob(os.path.join(MAN, "generated", "*.tex")))
        if os.path.basename(f) not in GENERATED
        and not os.path.basename(f).startswith(("tab_", "fig_", "numbers",
                                                "config_table", "ensemble_size"))
        and not os.path.basename(f).endswith("_macros.tex")]
for f in SCAN:
    for i, line in enumerate(open(f), 1):
        if line.lstrip().startswith("%"):
            continue
        for m in re.finditer(r"(?<![\d.])0\.\d{3,4}(?![\d])", line):
            if m.group(0) not in EXEMPT:
                hits.append(f"{os.path.basename(f)}:{i}: literal {m.group(0)} "
                            f"-- use a macro from generated/")
print(f"  gate2 prose literals : {len(hits)} {'FAIL' if hits else 'pass'}")
fail += hits

# ---- gate 3: the slack inequality, per row
neg = tot = 0
# Two tiers. G_cert reaches the paper only from e2_* (gen_paper_numbers, aggregate)
# and e9_logreg_* (gen_e9); those must be clean or the paper prints a negative slack
# beside a proof that it cannot be negative -- BLOCK. Every other file carries G_cert
# as an unconsumed derived column computed before the C1 fix; that is stale rather
# than wrong, so it is reported but does not block. Re-running them would cost hours
# and change nothing the paper prints.
CONSUMED = sorted(glob.glob("results/canonical/e2_*.jsonl")) + \
           sorted(glob.glob("results/r6_nan_fix/corrected/*.jsonl")) + \
           sorted(glob.glob("results/canonical/e9_logreg_*.jsonl"))
stale_neg = stale_tot = 0
for f in sorted(glob.glob("results/canonical/*.jsonl")):
    if f in CONSUMED:
        continue
    for l in open(f):
        if l.startswith("{"):
            g = json.loads(l).get("G_cert")
            if g is not None:
                stale_tot += 1
                stale_neg += g < -1e-9
for f in CONSUMED:
    for l in open(f):
        if not l.startswith("{"):
            continue
        r = json.loads(l)
        g = r.get("G_cert")
        if g is None:
            continue
        tot += 1
        if g < -1e-9:
            neg += 1
            if neg <= 5:
                fail.append(f"{os.path.basename(f)}: G_cert={g:+.6f} < 0 at "
                            f"k={r.get('k')} beta={r.get('beta')} "
                            f"seed={r.get('partition_seed')} -- CA exceeds EA")
print(f"  gate3 CA<=EA         : {neg}/{tot} negative in consumed files "
      f"{'FAIL' if neg else 'pass'}")
print(f"  gate3b stale column  : {stale_neg}/{stale_tot} negative in unconsumed files "
      f"(pre-C1-fix, not printed by the paper)")

# ---- gate 4: page budget
# Measured wrong for several rounds: TEXT was computed as (first appendix page - 1),
# but the appendix starts MID-PAGE, so body text and Appendix A share a page and that
# page counts against the text limit. Anchor on the last page carrying body content.
import subprocess
pdf = os.path.join(MAN, "main.pdf")
if os.path.exists(pdf):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                         capture_output=True, text=True).stdout
    pages = [q for q in txt.split("\f") if q.strip()]
    # Subsection numbering does not always survive extraction; anchor on the first
    # appendix SECTION title instead.
    first_app = next((i for i, q in enumerate(pages, 1)
                      if re.search(r"S\s*ENSITIVITY\s*A\s*NALYSES|Sensitivity Analyses", q)),
                     None)
    if first_app is None:
        first_app = next((i for i, q in enumerate(pages, 1)
                          if re.search(r"(?m)^\s*A\.1\.", q)), None)
    # Anchor on the LAST page carrying a body section heading. The heading can wrap
    # across a column break ("13." on one line, "Conclusion" on the next), so match the
    # word anywhere on the page rather than at line start.
    # IEEEtran renders section headings in spaced small caps ("C ONCLUSION"), and a
    # plain "Conclusion" search can instead match the word in body prose on an earlier
    # page -- which silently under-reports TEXT. Match the heading form first.
    concl = next((i for i, q in reversed(list(enumerate(pages, 1)))
                  if re.search(r"C\s*ONCLUSION", q)), None)
    if concl is None:
        concl = next((i for i, q in reversed(list(enumerate(pages, 1)))
                      if re.search(r"[Cc]\s*onclusion", q)), None)
    if concl is None or first_app is None:
        # Never fall back to (first_app - 1): that IS the bug this gate exists to
        # catch, and a silent fallback would hide it again.
        fail.append("gate4 could not locate the conclusion or the appendix start; "
                    "page budget UNVERIFIED")
        text_pages = total = app_refs = -1
    else:
        # a page shared by body text and Appendix A counts against the text limit
        text_pages = concl
    total = len(pages)
    app_refs = total - text_pages
    print(f"  gate4 page budget    : TEXT {text_pages}/13  APP+REFS {app_refs}/5  "
          f"TOTAL {total}/18 "
          f"{'FAIL' if (text_pages > 13 or app_refs > 5 or total > 18) else 'pass'}")
    if text_pages > 13:
        fail.append(f"TEXT is {text_pages}/13 -- the conclusion lands on page {concl}")
    if app_refs > 5:
        fail.append(f"APP+REFS is {app_refs}/5")
    if total > 18:
        fail.append(f"TOTAL is {total}/18")

# ---------------------------------------------------------------- gate1c
# Undefined GENERATED macros. Every \RICH*/\BSTAR*/\GM*/... macro is defined as
# \ifcsname ...\else\textbf{??}\fi, so a missing csname renders "??" in the PDF
# and raises NO TeX error and NO undefined-reference warning -- gate1 and gate1b
# both pass. This actually shipped: suppressing a degenerate table cell removed
# the macro a sentence still cited, and the PDF read "peaking at ??".
_pdf = os.path.join(MAN, "main.pdf")
_qq = 0
if os.path.exists(_pdf):
    import subprocess as _sp
    try:
        _txt = _sp.run(["pdftotext", "-layout", _pdf, "-"],
                       capture_output=True, text=True, timeout=120).stdout
    except Exception:
        _txt = ""
    for _i, _pg in enumerate(_txt.split("\f"), 1):
        for _ln in _pg.split("\n"):
            if "??" in _ln:
                _qq += 1
                fail.append(f"gate1c '??' on page {_i}: {_ln.strip()[:90]!r} "
                            f"-- an undefined generated macro fell back to \\textbf{{??}}")
print(f"  gate1c macro fallback: {_qq} '??' in the PDF {'FAIL' if _qq else 'pass'}")

# ---------------------------------------------------------------- gate6
# A tabular rendered outside a float. generated/tab_*.tex hold a bare tabular and
# must be \input INSIDE a \begin{table}; generated/floats/*.tex carry their own
# float and may appear anywhere. Emitting a bare tabular in the text flow renders
# the table a second time with no caption -- LaTeX reports no error, no undefined
# reference and no duplicate label, and it silently costs a page. That shipped
# here (\end{table}\input{generated/tab_lattice}) and sent me chasing the page
# budget through half the appendix. Caption-counting cannot see it, because the
# stray copy has no caption; the source can.
_stray = 0
for _f in sorted(glob.glob(os.path.join(MAN, "sections", "*.tex"))
                 + glob.glob(os.path.join(MAN, "generated", "*.tex"))):
    _t = open(_f, encoding="utf-8", errors="replace").read()
    # character spans covered by a table/figure environment
    _spans = [(m.start(), m.end()) for m in
              re.finditer(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", _t, re.S)]
    for _m in re.finditer(r"\\input\{([^}]*)\}", _t):
        _tgt = os.path.join(MAN, _m.group(1) + ".tex")
        if not os.path.exists(_tgt):
            continue
        _body = open(_tgt, encoding="utf-8", errors="replace").read()
        _self_float = re.search(r"\\begin\{(table|figure)\*?\}", _body) is not None
        _has_tabular = re.search(r"\\begin\{tabular\}", _body) is not None
        if _self_float or not _has_tabular:
            continue                      # brings its own float, or is not a table
        if not any(a <= _m.start() < b for a, b in _spans):
            _stray += 1
            fail.append(f"gate6 {os.path.basename(_f)}: \\input{{{_m.group(1)}}} is a bare "
                        f"tabular outside any float -- it renders an extra, captionless "
                        f"copy of the table and costs a page silently")
print(f"  gate6 stray tabulars : {_stray} tabular \\input outside a float "
      f"{'FAIL' if _stray else 'pass'}")

# ---------------------------------------------------------------- gate5
# Cross-source agreement. The paper printed THREE different values for one
# quantity -- device-derived beta* at N=20, k=1 -- because Table 1 took a
# median over 30 partition draws while the federation-size and richness
# sweeps took a median over 3, and nothing compared them. A reviewer who
# finds two values for one number stops reading. Every pair below names the
# same physical quantity and must agree exactly.
import re as _re5

def _macro(name, arg=None):
    """Resolve \\csname-defined generated macros to their literal value."""
    for f in glob.glob(os.path.join(MAN, "generated", "*.tex")):
        t = open(f, encoding="utf-8", errors="replace").read()
        key = name if arg is None else name + arg
        m = _re5.search(r"\\csname\s+" + _re5.escape(key) + r"\\endcsname\{([^}]*)\}", t)
        if m:
            return m.group(1).strip()
        m = _re5.search(r"\\newcommand\{\\" + _re5.escape(key) + r"\}\{([^}]*)\}", t)
        if m:
            return m.group(1).strip()
    return None

# (label, macro-A, macro-B) -- both name device-derived beta* at N=20, k=1
PAIRS = [("device-derived beta* at k=1 (main table vs richness sweep)",
          ("BSTARDEVk1", None), ("RICHBSTARd13k1", None))]

# The federation-size table prints beta* at N=20 as a table cell, not a macro, and
# it disagreed with the ceiling table for two rounds of review because nothing
# compared them: one took a median over 3 partition draws, the other over 30.
# Parse the N=20 rows and hold them to the same value.
_nchecked = _nbad = 0
_fs = os.path.join(MAN, "generated", "tab_fedsize.tex")
if os.path.exists(_fs):
    for _ln in open(_fs, encoding="utf-8", errors="replace"):
        _c = [x.strip() for x in _ln.split("&")]
        if len(_c) < 7 or _c[1].strip() != "20":
            continue
        _cell = _c[-1].replace("\\\\", "").strip()
        _mac = "BSTARDEVk1" if _c[0].startswith("device") else "BSTARIIDk1"
        _want = _macro(_mac)
        if _want is None:
            continue
        _nchecked += 1
        if _cell != _want:
            _nbad += 1
            fail.append(f"gate5 tab_fedsize {_c[0]} N=20 prints beta*={_cell} but "
                        f"{_mac}={_want} -- the same quantity in two tables")
        print(f"    (checked tab_fedsize {_c[0]} N=20: {_cell} vs {_mac}={_want})")
bad5 = 0
for label, (na, aa), (nb, ab) in PAIRS:
    va, vb = _macro(na, aa), _macro(nb, ab)
    if va is None or vb is None:
        continue                      # macro not built in this configuration
    if va != vb:
        bad5 += 1
        fail.append(f"gate5 {label}: {na}={va} but {nb}={vb} -- "
                    f"the same quantity printed two ways")
_tot = len(PAIRS) + _nchecked
_bad = bad5 + _nbad
print(f"  gate5 cross-source   : {_tot - _bad}/{_tot} quantities agree "
      f"{'FAIL' if _bad else 'pass'}")

# ---- gate 7: a prose percentage that restates an indexed macro's own beta argument
#      gate2's regex only sees 0.XXX, so every percentage in the paper sits outside
#      it. Most are stable by construction: cited literature (88% on MNIST) or
#      analytic ceilings (25%, 30%, 40% against beta_geo), which are algebra rather
#      than measurements. The one drift-capable shape is a percentage restating the
#      beta argument of the macro beside it -- \CAIID{1}{40} ... "against 40%
#      malicious clients". If the grid moved, the macro would follow the data and
#      the sentence next to it would not. Negative-controlled: seeding 40->30 in
#      the conclusion makes this fire, and only this.
_P7 = re.compile(r"\\([A-Za-z]+)\{(\d+)\}\{(\d+)\}(.{0,120}?)(\d{1,3})\\%", re.S)
_h7 = []
for _f in sorted(glob.glob(os.path.join(MAN, "sections", "*.tex"))):
    for _i, _line in enumerate(open(_f), 1):
        if _line.lstrip().startswith("%"):
            continue
        for _m in _P7.finditer(_line):
            _mac, _k, _b, _gap, _pct = _m.groups()
            if "%" in _gap or _pct == _b:
                continue
            _h7.append(f"{os.path.basename(_f)}:{_i}: \\{_mac}{{{_k}}}{{{_b}}} but "
                       f"prose says {_pct}% -- beta argument and prose disagree")
print(f"  gate7 macro/prose pct : {len(_h7)} {'FAIL' if _h7 else 'pass'}")
fail += _h7


if fail:
    print("\n  BLOCKERS:")
    for x in fail[:20]:
        print(f"    {x}")
    if len(fail) > 20:
        print(f"    ... and {len(fail)-20} more")
    sys.exit(1)
print("  all gates pass")
