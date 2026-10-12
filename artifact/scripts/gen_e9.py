#!/usr/bin/env python3
"""E9 second-model sensitivity paragraph, generated from the canonical rows."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load, gap_table, src

from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)


def main():
    lg = gap_table(load("results/canonical/e9_logreg_*.jsonl"))
    mlp = gap_table(load(src("e2_*.jsonl")))
    if not lg:
        print("no e9 rows"); return

    def g(t, p, k, b, f):
        e = t.get((p, k, round(b, 4)))
        return None if e is None else (e[f]["median"] if isinstance(e[f], dict) else e[f])

    vals = dict(
        mMLP=g(mlp, "device_derived", 1, 0.0, "margin"),
        mLR=g(lg, "device_derived", 1, 0.0, "margin"),
        caMLP=g(mlp, "device_derived", 1, 0.40, "CA"),
        caLR=g(lg, "device_derived", 1, 0.40, "CA"),
        collMLP=g(mlp, "device_derived", 1, 0.40, "collapse_rate"),
        collLR=g(lg, "device_derived", 1, 0.40, "collapse_rate"),
        slackLR=max(v["G_cert"]["median"] for kk, v in lg.items()
                    if kk[0] == "iid" and v["possible"] and v["G_cert"]["n"]),
        tau=[r for r in load("results/canonical/e9_logreg_*.jsonl")][0]["tau_triv"],
    )
    para = (
        "%% GENERATED -- do not edit\n"
        "\\paragraph{The ceiling is model-independent; the competence collapse is not}\n"
        "Corollary~\\ref{cor:ceiling} is a counting argument and holds for any model. The\n"
        "competence arm of the tension is empirical, so we repeated the central cells with a\n"
        "second, lower-capacity classifier: multinomial logistic regression, $64$ parameters\n"
        "against the multilayer perceptron's $1{,}586$. The qualitative result replicates.\n"
        "Under IID the certificate stays nearly exact, with slack at most $%.4f$ and no\n"
        "collapse; under device-derived skew the members disagree, slack grows with the\n"
        "malicious fraction, and certification eventually fails.\n"
        "\n"
        "%% provenance: jrn_01M0SH0V4DR4AYK59BJCN230Q5 supports the cost and sensitivity measurements\n"
        "The \\emph{magnitude} does not replicate, and that is informative. The linear model\n"
        "generalises better from a single household, so its mean vote margin under\n"
        "device-derived skew at $k=1$ is $%.4f$ against the perceptron's $%.4f$. At\n"
        "$\\beta = 0.40$ it certifies $%.4f$, still below the trivial floor of $%.4f$, where\n"
        "the perceptron certifies $%.4f$, and it collapses on a fraction $%.2f$ of partition\n"
        "draws against $%.2f$: the simpler model delays collapse but does not avert it at the\n"
        "fraction $k=1$ exists to reach. Ensemble agreement, not accuracy, is what\n"
        "certification consumes, and a model that agrees with itself across households under\n"
        "skew shifts the collapse boundary outward without removing it. We therefore state the competence arm as a property of\n"
        "the model family as well as of the partition, and the tension between the two\n"
        "constraints as one whose severity a deployer can influence by choosing a simpler\n"
        "detector.\n"
    ) % (vals["slackLR"], vals["mLR"], vals["mMLP"], vals["caLR"], vals["tau"],
         vals["caMLP"], vals["collLR"], vals["collMLP"])
    open(os.path.join(OUT, "e9_paragraph.tex"), "w").write(para)
    print("wrote e9_paragraph.tex")
    for k, v in vals.items():
        print(f"  {k:9s} {v}")


if __name__ == "__main__":
    main()
