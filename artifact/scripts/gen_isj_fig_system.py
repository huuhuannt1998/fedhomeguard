#!/usr/bin/env python3
"""Figure fig:system of the ISJ-GP manuscript (round isj4, 2026-11-04): the setting at k = 1, the member-output vector,
an arbitrary aggregation rule g, the adversary's Hamming ball and the certificate.

Written for the ISJ-GP paper, whose subject is the aggregation rule: scripts/gen_fig_system.py (k = 2, plurality vote and
plurality margin certificate) stays unchanged so that it still reproduces the figure of the earlier versions.
A diagram, not data: it carries no measured value. Every element restates Sections 2-5 of the paper (households holding
per-device flow records; at k = 1 one FedAvg member per household; the member-output vector v(x); an aggregation rule g
such as plurality, abstention or the max-flow certified decoder learned on a labeled server set; a malicious set B of at
most m clients that changes at most c(m) = m coordinates of v(x); certification on the Hamming ball; the competence
ceiling over every g). Indices are symbolic.

  FHG_FIGURES=<dir> python3 scripts/gen_isj_fig_system.py

Writes <dir>/fig_system.pdf (TikZ, pdflatex, Latin Modern T1, 6.5in wide; reproducible byte for byte).
Round isj3 r1 (2026-11-07, review r1 issue 31): text at \\small (was \\footnotesize), 'trained on h_i' (local training
at k = 1) instead of 'FedAvg on h_i', and the member-output-vector label moved clear of the member boxes.
Round isj3b (2026-11-07, review r4 #26): the column header reads 'one input x' (the unit differs by corpus).
"""
import os
import shutil
import subprocess
import sys
import tempfile

from _manuscript import FIGURES as FIG  # ISJGP figures/ (FHG_FIGURES overrides)

TEX = r"""
\pdfinfoomitdate=1
\pdftrailerid{}
\pdfsuppressptexinfo=-1
\documentclass[10pt,border=0pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,calc,positioning,fit,backgrounds,shapes.geometric}
\definecolor{ink}{HTML}{0B0B0B}
\definecolor{ink2}{HTML}{52514E}
\definecolor{muted}{HTML}{898781}
\definecolor{panel}{HTML}{F4F3EF}
\definecolor{adv}{HTML}{C8302F}
\definecolor{advfill}{HTML}{FBE9E7}
\begin{document}
\begin{tikzpicture}[x=1in,y=1in,font=\small,
  box/.style={draw=ink2,line width=0.5pt,rounded corners=1.5pt,fill=white,minimum height=0.22in,inner xsep=3pt},
  hh/.style={box,minimum width=0.70in},
  mem/.style={box,minimum width=0.95in},
  advbox/.style={draw=adv,fill=advfill,line width=0.8pt},
  touched/.style={draw=adv,line width=0.8pt,dash pattern=on 2.2pt off 1.4pt},
  flow/.style={-{Stealth[length=1.5mm]},draw=ink2,line width=0.55pt},
  hdr/.style={font=\small\bfseries,text=ink,anchor=south,inner sep=0pt},
  note/.style={font=\small,text=ink2,align=center,anchor=north,inner sep=0pt,
               execute at begin node={\hyphenpenalty=10000\exhyphenpenalty=10000}},
  dev/.style={draw=ink2,fill=white,line width=0.45pt,inner sep=0pt,minimum size=4.2pt},
]
\useasboundingbox (0,-0.04) rectangle (6.5,1.86);
\newcommand{\dA}[1]{\node[dev,circle] at (#1) {};}
\newcommand{\dB}[1]{\node[dev,rectangle] at (#1) {};}
\newcommand{\dC}[1]{\node[dev,regular polygon,regular polygon sides=3,minimum size=5.6pt] at (#1) {};}
\newcommand{\dD}[1]{\node[dev,diamond,minimum size=5.6pt] at (#1) {};}
\def\yH{1.72} \def\yA{1.54} \def\yB{1.30} \def\yC{1.06} \def\yD{0.86} \def\yN{0.66}

% device types
\node[hdr,anchor=south west] at (0.0,\yH) {devices};
\foreach \y in {\yA,\yB,\yC,\yN} { \node[box,minimum width=0.30in] at (0.17,\y) {}; }
\dA{0.17,\yA} \dB{0.17,\yB} \dC{0.17,\yC} \dD{0.17,\yN}
\node[text=ink2] at (0.17,\yD) {$\vdots$};
\draw[flow] (0.36,1.18) -- node[above,text=ink2] {partition} (0.86,1.18);

% households
\node[hdr] at (1.25,\yH) {$N$ households};
\node[hh] (h1) at (1.25,\yA) {}; \node[anchor=west] at (h1.west) {$h_1$};
\node[hh,advbox] (h2) at (1.25,\yB) {}; \node[anchor=west,text=adv] at (h2.west) {$h_2$};
\node[hh] (h3) at (1.25,\yC) {}; \node[anchor=west] at (h3.west) {$h_3$};
\node[text=ink2] at (1.25,\yD) {$\vdots$};
\node[hh] (hN) at (1.25,\yN) {}; \node[anchor=west] at (hN.west) {$h_N$};
\dA{1.37,\yA} \dB{1.48,\yA}
\dC{1.43,\yB}
\dB{1.37,\yC} \dD{1.48,\yC}
\dA{1.32,\yN} \dC{1.43,\yN} \dD{1.54,\yN}

% members, one per household (k = 1)
\node[hdr] at (2.50,\yH) {$K=N$ members};
\node[mem] (f1) at (2.50,\yA) {$f_1$: trained on $h_1$};
\node[mem,touched] (f2) at (2.50,\yB) {$f_2$: trained on $h_2$};
\node[mem] (f3) at (2.50,\yC) {$f_3$: trained on $h_3$};
\node[text=ink2] at (2.50,\yD) {$\vdots$};
\node[mem] (fN) at (2.50,\yN) {$f_N$: trained on $h_N$};
\foreach \h/\f in {h1/f1,h3/f3,hN/fN} { \draw[flow] (\h.east) -- (\f.west); }
\draw[flow,draw=adv] (h2.east) -- (f2.west);
\node[note,text width=2.85in,anchor=north west,align=left] at (0.02,0.46)
  {\textcolor{adv}{red}: the malicious set $B$ of at most $m$ clients, which sends arbitrary training updates; its members' votes (\textcolor{adv}{dashed}) can take any value};

% member-output vector
\node[box,fill=panel,align=center,minimum width=0.58in,minimum height=0.86in] (vec) at (3.42,1.12)
  {$v(x)$\\[2pt]$f_1(x)$\\[-1pt]\textcolor{adv}{$f_2(x)$}\\[-1pt]$\vdots$\\[-1pt]$f_N(x)$};
\foreach \f in {f1,f2,f3,fN} { \draw[flow] (\f.east) -- (vec.west); }
\node[hdr] at (3.42,\yH) {one input $x$};
\node[note,text width=0.66in] at (3.42,0.62) {member-\\output\\vector};

% aggregation rule
\node[box,fill=panel,align=center,text width=1.02in,minimum height=0.60in,execute at begin node={\hyphenpenalty=10000\exhyphenpenalty=10000}] (g) at (4.40,1.24)
  {aggregation rule $g$:\\[1pt]plurality, abstention or max-flow certified decoder};
\draw[flow] (vec.east) -- (vec.east -| g.west);
\node[hdr] at (4.40,\yH) {label $g(v(x))$};
\node[box,align=center,text width=1.02in] (srv) at (4.40,0.48) {labeled server set\\[-1pt](decoder only)};
\draw[flow] (srv.north) -- (g.south);

% certificate
\node[box,align=left,fill=panel,inner sep=4.5pt,text width=1.30in,anchor=west,
      execute at begin node={\hyphenpenalty=10000\exhyphenpenalty=10000}] (cert) at (5.06,1.22)
  {$x$ is certified at budget $m$ when $g$ returns $y(x)$ on every vector within Hamming distance $c(m)=m$ of $v(x)$.};
\draw[flow] (g.east) -- (cert.west);
\node[hdr] at (cert.north |- 0,\yH) {certificate};
\node[note,text width=1.40in] at (cert.south |- 0,0.70)
  {competence ceiling: the most inputs any $g$ certifies, by one max-flow (Section 4)};
\end{tikzpicture}
\end{document}
"""


def main():
    os.makedirs(FIG, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="fig_system_")
    try:
        with open(os.path.join(tmp, "fig_system.tex"), "w") as fh:
            fh.write(TEX)
        env = dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "fig_system.tex"],
                           cwd=tmp, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            sys.stderr.write(r.stdout[-3000:])
            sys.exit("pdflatex failed")
        shutil.copyfile(os.path.join(tmp, "fig_system.pdf"), os.path.join(FIG, "fig_system.pdf"))
        print(f"wrote {os.path.join(FIG, 'fig_system.pdf')}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
