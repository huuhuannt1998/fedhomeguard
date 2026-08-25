#!/usr/bin/env python3
"""Automated validation of every numerical claim in the abstract and conclusion
(review sec 48, final bullet).

The prose reaches results through generated \\csname macros, so a value cannot drift
between sections by construction. What this checks is the residual risk: a numeric
literal typed directly into the prose, which the generator would never see and no
assertion would catch. Every such literal must either be a declared constant (a
subsample size, a percentage from the surveyed literature, a value defined in the
theory) or it is flagged.
"""
import json, os, re, sys

MAN = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP"
WATCH = ["sections/00_abstract.tex", "sections/14_conclusion.tex",
         "sections/01_introduction.tex"]

# Literals that are definitional rather than measured, with the reason each is allowed.
ALLOWED = {
    "0.02": "cao2021provably's published operating point, cited",
    "88": "cao2021provably's published certified accuracy, cited",
    "1": "subsample size / algebraic constant",
    "2": "subsample size / algebraic constant",
    "3": "subsample size",
    "5": "subsample size, and k=5 in the ceiling example",
    "10": "percentage bound of the surveyed literature's evaluated range",
    "20": "federation size, also stated via \\Nclients",
    "25": "percentage form of beta_geo(20,2)=0.250",
    "40": "percentage bound of the surveyed literature's evaluated range",
    "50": "N=50 in the federation-size statement",
    "0.120": "beta_cert at k=5, N=50, from Corollary 1",
    "0.129": "beta_cert at k=5, large N, from Corollary 1",
    "0.250": "beta_geo(20,2), from Proposition 2",
    "0.20": "a malicious fraction on the evaluation grid",
    "0.40": "a malicious fraction on the evaluation grid",
    "1000": "federation size in the ceiling example",
}


def main():
    nums = json.load(open(os.path.join(MAN, "generated/numbers.json")))
    known = set()
    for v in nums["numbers"].values():
        if isinstance(v, (int, float)):
            known.add(f"{v:.4f}"); known.add(f"{v:g}")
    for v in nums["numbers"].get("indexed", {}).values():
        known.add(str(v))

    bad = []
    for rel in WATCH:
        p = os.path.join(MAN, rel)
        for n, line in enumerate(open(p), 1):
            s = line.strip()
            if s.startswith("%"):
                continue
            # a literal is anything numeric not immediately preceded by a backslash
            for m in re.finditer(r"(?<![\\A-Za-z0-9._^{-])(\d+\.\d+|\d+)(?![}0-9])", s):
                lit = m.group(1)
                if lit in ALLOWED or lit in known:
                    continue
                bad.append((rel, n, lit, s[:74]))

    for rel, n, lit, ctx in bad:
        print(f"  UNVERIFIED {rel}:{n}  {lit!r}  in: {ctx}")
    print(f"\nverify_paper_claims: {len(bad)} unverified numeric literals in "
          f"{len(WATCH)} front-matter sections")
    if bad:
        print("Each must come from generated/numbers.tex or be added to ALLOWED with "
              "a stated reason.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
