#!/usr/bin/env python3
"""Render literature/inventory.yaml into the manuscript's inventory table and the
counts the prose quotes. Keeps the systematization claims tied to the audit."""
import json, os, sys, yaml

OUT = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"
CITE = {"fedmade2024": "fedmade2024", "nguyen2020poison": "nguyen2020poison",
        "weidetect2025": "weidetect2025", "li2022iotpoison": "li2022iotpoison"}


def esc(s):
    return (str(s).replace("&", "\\&").replace("_", "\\_").replace("%", "\\%"))


def main():
    d = yaml.safe_load(open("literature/inventory.yaml"))
    inc = d["included"]
    os.makedirs(OUT, exist_ok=True)

    rows = ["% GENERATED from literature/inventory.yaml -- do not edit",
            "\\begin{tabular}{lllccl}", "\\toprule",
            "Defence & Dataset & Partition & Skew & $\\beta$ & Obs. \\\\",
            " & & & meas. & range & / thm. \\\\", "\\midrule"]
    for r in inc:
        if r.get("role") == "attack":
            continue
        key = r["key"]
        cite = f"\\cite{{{CITE[key]}}}" if key in CITE else ""
        ds = r["datasets"][0] if r["datasets"] else "---"
        part = (r["partition"] or "---").split("(")[0].strip()
        sk = {True: "yes", False: "no", None: "---"}[r["skew_measured"]]
        bb = r["beta_evaluated"] or "---"
        obs = r["observability"] or "---"
        thm = "none" if r["guarantee_type"] == "none" else esc(r["guarantee_type"])
        rows.append(f"{esc(key)}{cite} & {esc(ds)} & {esc(part)} & {sk} & "
                    f"{esc(bb)} & {obs} / {thm} \\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_inventory.tex"), "w").write("\n".join(rows) + "\n")

    det_obs = [r for r in inc if r["observability"] not in (None, "n/a")]
    det_sk = [r for r in inc if r["skew_measured"] is not None]
    n_def = len([r for r in inc if r.get("role") != "attack"])
    counts = dict(
        nInventory=n_def,
        nFullText=len([r for r in inc if r["source_level"] == "full_text"]),
        nObsDeterminable=len(det_obs),
        nRequireLtwo=len([r for r in det_obs if r["observability"] == "L2"]),
        nSkewDeterminable=len(det_sk),
        nSkewMeasured=len([r for r in det_sk if r["skew_measured"]]),
        nCertifiedGuarantee=len([r for r in inc
                                 if r["guarantee_type"] == "certified_prediction"]),
        nExcluded=len(d["excluded"]),
    )
    tex = ["% GENERATED from literature/inventory.yaml -- do not edit"]
    for k, v in counts.items():
        tex.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    open(os.path.join(OUT, "inventory_counts.tex"), "w").write("\n".join(tex) + "\n")
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
