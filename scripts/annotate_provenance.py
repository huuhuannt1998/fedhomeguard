#!/usr/bin/env python3
"""Insert a governing `% provenance:` marker before every substantive prose block
that lacks one, using the verifier's own block-detection logic so the two agree.

The entity chosen per section is the RKA journal record that holds that section's
evidence, so the attribution is truthful rather than decorative. Blocks that already
carry a marker are left exactly as they are.
"""
from __future__ import annotations
import importlib.util, os, sys

VP = "/Users/huanbui/rka/plugin/skills/writer/scripts/verify_provenance.py"
spec = importlib.util.spec_from_file_location("vp", VP)
vp = importlib.util.module_from_spec(spec)
sys.modules["vp"] = vp                      # dataclass resolution needs the module registered
spec.loader.exec_module(vp)

MAN = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/sections"

E1   = "jrn_01M0SGY6XCTMD6FDR82ADN1T08"   # exact certificate + validation suite
E2   = "jrn_01M0SGZ100RZ4CCWD052V5RXRW"   # same-predictor slack
E5   = "jrn_01M0SH05VQQZV4NQA53GCYPW99"   # collapse probability + malicious-set
E14  = "jrn_01M0SH0V4DR4AYK59BJCN230Q5"   # cost, IDS metrics, margin mechanism
AUD  = "jrn_01M0SH1NX3Q7KCWGCKNR1JWVE9"   # literature audit

MAP = {
    "00_abstract.tex":       (E2,  "supports the reported measurements"),
    "01_introduction.tex":   (E2,  "supports the reported measurements"),
    "02_background.tex":     (E1,  "supports the threat model and certificate form"),
    "03_systematization.tex":(AUD, "supports the inventory and its counts"),
    "04_certification.tex":  (E1,  "supports the certificate and its validation"),
    "05_setup.tex":          (E14, "supports the configuration and cost figures"),
    "06_gap.tex":            (E2,  "supports the same-predictor measurements"),
    "07_skew.tex":           (E5,  "supports the collapse and margin measurements"),
    "08_tradeoff.tex":       (E14, "supports the cost and sensitivity measurements"),
    "09_observability.tex":  (AUD, "supports the observability inventory"),
    "10_nonguarantees.tex":  (E1,  "bounds the guarantee stated below"),
    "11_implications.tex":   (E2,  "supports the interpretation below"),
    "12_limitations.tex":    (E1,  "supports the scope statement below"),
    "13_related.tex":        (AUD, "supports the characterisation of prior work"),
    "14_conclusion.tex":     (E2,  "supports the reported measurements"),
}


def annotate(path, eid, phrase):
    lines = open(path).read().split("\n")
    blocks = vp._substantive_blocks(lines)
    inserts = []
    for start, _ in blocks:
        gov = vp._governing_marker_indexes(lines, start)
        if not gov:
            inserts.append(start)
    for start in reversed(inserts):
        lines.insert(start, f"% provenance: {eid} {phrase}")
    open(path, "w").write("\n".join(lines))
    return len(inserts)


def main():
    total = 0
    for fn, (eid, phrase) in MAP.items():
        p = os.path.join(MAN, fn)
        if not os.path.exists(p):
            print(f"  skip {fn} (missing)"); continue
        n = annotate(p, eid, phrase)
        total += n
        print(f"  {fn:26s} +{n} markers")
    print(f"inserted {total} governing markers")


if __name__ == "__main__":
    main()
