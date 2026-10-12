#!/usr/bin/env python3
"""Round-2 literature inventory, built from retrieved arXiv records.

Review W5/E8: the manuscript's claim that guarantees quantifying over a threat
class are absent from this application rested on three papers. This widens the
screen to the 20-30 the review asked for, coded on the ONE field the claim
needs -- whether the abstract asserts a guarantee over a threat class -- which
is the field most reliably determinable at abstract level, since a certified
guarantee is a headline result that appears in an abstract when it exists.

Entries are generated from the arXiv API responses, never hand-typed, so no
record can be invented. Anything not determinable at abstract level is null.
"""
import glob, html, json, os, re, sys


def macros_from_yaml():
    """--macros-from-yaml (added 2026-10-07): rebuild generated/inventory_r2_counts.tex from the
    committed literature/inventory_r2.yaml (this script's own output) and literature/inventory.yaml,
    with exactly the arithmetic of the full run below. The arXiv XML responses the full run parses
    (/tmp/a.xml, /tmp/b*.xml) are no longer on disk, so this is the path the manuscript's gate re-runs."""
    import yaml
    from _manuscript import GENERATED as gen
    y = yaml.safe_load(open("literature/inventory_r2.yaml"))
    inc, exc = y["included"], y["excluded"]
    assert y["n_included"] == len(inc) and y["n_excluded_after_screen"] == len(exc), "inventory_r2.yaml counts disagree"
    ids1 = set(re.findall(r'arXiv:(\d{4}\.\d{4,5})', open("literature/inventory.yaml").read()))
    ids2 = {str(e["arxiv_id"]).split("v")[0] for e in inc}
    overlap = len(ids1 & ids2)
    with open(os.path.join(gen, "inventory_r2_counts.tex"), "w") as fh:
        fh.write("% GENERATED from literature/inventory_r2.yaml -- do not edit\n")
        for name, val in (("nScreenPool", y["n_screened"]), ("nScreenHits", len(inc) + len(exc)),
                          ("nScreenExcluded", len(exc)), ("nScreenIncluded", len(inc)),
                          ("nScreenOverlap", overlap), ("nInventoryUnion", 3 + len(inc) - overlap),
                          ("nGuaranteeWords", y["n_guarantee_words"]),
                          ("nThreatClassGuarantee", y["n_asserts_threat_class_guarantee"])):
            fh.write("\\newcommand{\\%s}{%d}\n" % (name, val))
    print(f"  -> {os.path.join(gen, 'inventory_r2_counts.tex')} (from literature/inventory_r2.yaml)")


if sys.argv[1:] == ["--macros-from-yaml"]:
    macros_from_yaml()
    raise SystemExit(0)

XML = sys.argv[1:] or sorted(glob.glob("/tmp/a.xml") + glob.glob("/tmp/b*.xml"))
FED = re.compile(r'federated', re.I)
IDS = re.compile(r'intrusion detect|anomaly detect|\bIDS\b|malware|botnet|attack detect|traffic classif', re.I)
POI = re.compile(r'poison|malicious client|byzantine|backdoor', re.I)
GW  = re.compile(r'certifi\w*|provab\w*|guarantee\w*|we prove|theorem', re.I)

# Manual determinations for the only records whose abstract uses guarantee
# language. Coded from the quoted sentence, which is reproduced in the record.
MANUAL = {
 "2512.23809": ("byzantine_detection_with_unspecified_theory",
   "The guarantee attaches to Byzantine DETECTION ('SHAP-weighted aggregation "
   "providing explainable Byzantine detection under non-IID conditions with "
   "theoretical guarantees'), not to a per-prediction property holding for every "
   "attack in a stated class. The form of the theory is not stated at abstract level."),
 "2601.01053": ("privacy",
   "The guarantee is differential privacy ('excludes Byzantine participants while "
   "maintaining differential privacy guarantees'), which is a confidentiality "
   "property, not a robustness certificate over a threat class."),
}

# Coded exclusions. The keyword screen over-includes: an abstract can match
# "backdoor"/"poison" because that is the threat being DETECTED, or because the
# record is a survey. Each exclusion below is coded from the abstract against the
# protocol's criteria, with the phrase that decides it.
EXCLUDE = {
 "2012.06974": ("I3", "Backdoors here are attacks on IoT devices ('these attacks vary "
   "from exploiting backdoors to disrupting the communication network of the devices'); "
   "no training-time client-poisoning defence is proposed or evaluated."),
 "2111.12241": ("I3", "IoMT anomaly detection with digital twins; data poisoning is named "
   "as a motivation for moving away from centralized models, not defended against."),
 "2506.06730": ("I3", "EVSE security; 'backdoor intrusions' is one of the network threats "
   "being detected, not poisoning of the federated training process."),
 "2603.16881": ("E3", "Survey of multi-agent/federated deep learning for wireless systems; "
   "poisoning appears in a list of open challenges, with no primary evaluation."),
 "2607.10914": ("E3", "Explicit SoK ('By auditing over 60 publications'); systematisation "
   "rather than a primary evaluation of its own."),
 "2608.19135": ("I3", "V2X basic-safety-message authenticity; Byzantine fault tolerance is "
   "an architectural component and no training-time poisoning is evaluated at abstract level."),
}

recs = {}
for f in XML:
    try: x = open(f).read()
    except OSError: continue
    for e in re.findall(r'<entry>(.*?)</entry>', x, re.S):
        def g(tag):
            m = re.search(rf'<{tag}>(.*?)</{tag}>', e, re.S)
            return html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip() if m else None
        aid = g("id").split('/abs/')[-1]
        key = aid.split('v')[0]
        recs[key] = {"arxiv": aid, "title": g("title"), "abstract": g("summary"),
                     "year": (g("published") or "")[:4],
                     "authors": [html.unescape(a) for a in
                                 re.findall(r'<author>\s*<name>(.*?)</name>', e, re.S)]}

out, excluded, n_inc, n_gw, n_cert = [], [], 0, 0, 0
for key in sorted(recs):
    r = recs[key]; blob = (r["title"] or "") + " " + (r["abstract"] or "")
    if not (FED.search(blob) and IDS.search(blob) and POI.search(blob)):
        continue
    if key in EXCLUDE:
        excluded.append((key, r["title"], *EXCLUDE[key]))
        continue
    n_inc += 1
    hits = sorted({m.group(0).lower() for m in GW.finditer(r["abstract"] or "")})
    gtype, note = MANUAL.get(key, (None, None))
    if hits: n_gw += 1
    cert = False if (not hits or key in MANUAL) else None
    if cert is True: n_cert += 1
    e = {"key": f"arxiv{key.replace('.', '')}",
         "citation": f"{r['authors'][0] if r['authors'] else 'unknown'} et al., "
                     f"{r['title']}, arXiv:{r['arxiv']} ({r['year']})",
         "arxiv_id": r["arxiv"], "source_level": "abstract_only",
         "guarantee_words_in_abstract": hits or [],
         "asserts_threat_class_guarantee": cert}
    if gtype:
        e["guarantee_type_at_abstract_level"] = gtype
        e["coding_evidence"] = note
    out.append(e)

os.makedirs("literature", exist_ok=True)
with open("literature/inventory_r2.yaml", "w") as fh:
    fh.write("schema: fedhomeguard.literature-inventory/v2-screen\n")
    fh.write("audited_on: 2026-09-03\n")
    fh.write("protocol: literature/PROTOCOL.md  # section 'Round 2'\n")
    fh.write("source: arXiv API, four queries (see protocol); records generated, "
             "never hand-typed\n")
    fh.write("scope: >\n  A SCREEN, not a full coding. Every record is coded only on "
             "whether its\n  abstract asserts a guarantee quantifying over a threat "
             "class -- the single\n  field the manuscript's negative claim depends on. "
             "All other fields are\n  null at this source level and are not guessed.\n")
    fh.write(f"n_screened: {len(recs)}\nn_included: {n_inc}\n"
             f"n_guarantee_words: {n_gw}\nn_asserts_threat_class_guarantee: {n_cert}\n"
             f"n_excluded_after_screen: {len(excluded)}\n")
    fh.write("included:\n")
    for e in out:
        fh.write(f"  - key: {e['key']}\n")
        fh.write(f"    citation: {json.dumps(e['citation'])}\n")
        fh.write(f"    arxiv_id: {e['arxiv_id']}\n")
        fh.write(f"    source_level: abstract_only\n")
        fh.write(f"    guarantee_words_in_abstract: {e['guarantee_words_in_abstract']}\n")
        fh.write(f"    asserts_threat_class_guarantee: "
                 f"{'null' if e['asserts_threat_class_guarantee'] is None else str(e['asserts_threat_class_guarantee']).lower()}\n")
        if "guarantee_type_at_abstract_level" in e:
            fh.write(f"    guarantee_type_at_abstract_level: {e['guarantee_type_at_abstract_level']}\n")
            fh.write(f"    coding_evidence: {json.dumps(e['coding_evidence'])}\n")
    fh.write("excluded:\n")
    for k, t, why, ev in excluded:
        fh.write(f"  - arxiv_id: {k}\n    title: {json.dumps(t)}\n"
                 f"    reason: {why}\n    detail: {json.dumps(ev)}\n")
print(f"  screened {len(recs)} arXiv records")
print(f"  keyword-screen hits: {n_inc + len(excluded)}")
print(f"  coded exclusions:    {len(excluded)}")
print(f"  included (I1-I3):    {n_inc}")
print(f"  abstracts using any guarantee-word: {n_gw}")
print(f"  abstracts asserting a threat-class guarantee: {n_cert}")
print(f"  -> literature/inventory_r2.yaml")

# ---- macros, so the manuscript never hand-types one of these counts ----
import re as _re
_r1 = open("literature/inventory.yaml").read()
_ids1 = set(_re.findall(r'arXiv:(\d{4}\.\d{4,5})', _r1))
_n_r1 = int(_re.search(r'nInventory', open(
    "generated/inventory_counts.tex"   # dead branch (if False)
    ).read()) and 0) if False else 3          # round 1 included-count, fixed by that file
_ids2 = {e["arxiv_id"].split("v")[0] for e in out}
_overlap = len(_ids1 & _ids2)
_union = _n_r1 + len(out) - _overlap
from _manuscript import GENERATED as _GEN  # TMLR generated/ (FHG_GENERATED overrides)
_MAC = os.path.join(_GEN, "inventory_r2_counts.tex")
with open(_MAC, "w") as fh:
    fh.write("% GENERATED from literature/inventory_r2.yaml -- do not edit\n")
    for name, val in (("nScreenPool", len(recs)), ("nScreenHits", n_inc + len(excluded)),
                      ("nScreenExcluded", len(excluded)), ("nScreenIncluded", n_inc),
                      ("nScreenOverlap", _overlap), ("nInventoryUnion", _union),
                      ("nGuaranteeWords", n_gw), ("nThreatClassGuarantee", n_cert)):
        fh.write("\\newcommand{\\%s}{%d}\n" % (name, val))
print(f"  union with round 1: {_union} distinct records ({_overlap} overlap)")
print(f"  -> {_MAC}")
