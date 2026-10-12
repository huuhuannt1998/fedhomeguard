#!/usr/bin/env python3
"""Figure: the setting, the deployed ensemble, the adversary and the certificate (schematic).

Figure fig:system of the TMLR manuscript (added 2026-10-07; round tmlr2, 2026-10-10: the malicious set
manipulates training updates only, and the vote labels one flow x).
A diagram, not data: it carries no measured value. Every element restates Sections 2-3 of the
paper (households holding per-device captures under a device-derived or IID partition; K subsets
of k households, one FedAvg member each; plurality vote; a malicious set B of at most m clients;
touched members; the certificate's margin condition and the ceiling). Indices are symbolic
(h_1..h_N, S_1..S_K); the subsets drawn are an illustration at k=2, not a run.

  FHG_FIGURES=<dir> python3 scripts/gen_fig_system.py

Writes <dir>/fig_system.pdf: TikZ compiled by pdflatex in Latin Modern (T1), the paper's font,
6.5in wide so that \\includegraphics[width=\\textwidth] sets it at scale 1. The PDF is
reproducible byte for byte (no dates, empty trailer id).
"""
import os
import shutil
import subprocess
import sys
import tempfile

from _manuscript import FIGURES as FIG  # TMLR figures/ (FHG_FIGURES overrides)

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
\definecolor{rule}{HTML}{C3C2B7}
\definecolor{panel}{HTML}{F4F3EF}
\definecolor{adv}{HTML}{C8302F}
\definecolor{advfill}{HTML}{FBE9E7}
\begin{document}
\begin{tikzpicture}[x=1in,y=1in,font=\footnotesize,
  box/.style={draw=ink2,line width=0.5pt,rounded corners=1.5pt,fill=white,minimum height=0.22in,inner xsep=3pt},
  hh/.style={box,minimum width=0.80in},
  mem/.style={box,minimum width=0.95in},
  advbox/.style={draw=adv,fill=advfill,line width=0.8pt},
  touched/.style={draw=adv,line width=0.8pt,dash pattern=on 2.2pt off 1.4pt},
  sub/.style={draw=muted,line width=0.55pt},
  subadv/.style={draw=adv,line width=0.75pt},
  flow/.style={-{Stealth[length=1.5mm]},draw=ink2,line width=0.55pt},
  hdr/.style={font=\footnotesize\bfseries,text=ink,anchor=south,inner sep=0pt},
  note/.style={font=\footnotesize,text=ink2,align=center,anchor=north,inner sep=0pt,
               execute at begin node={\hyphenpenalty=10000\exhyphenpenalty=10000}},
  dev/.style={draw=ink2,fill=white,line width=0.45pt,inner sep=0pt,minimum size=4.2pt},
]
\useasboundingbox (0,0.19) rectangle (6.5,1.86);
% device-type glyphs (identity by shape only)
\newcommand{\dA}[1]{\node[dev,circle] at (#1) {};}
\newcommand{\dB}[1]{\node[dev,rectangle] at (#1) {};}
\newcommand{\dC}[1]{\node[dev,regular polygon,regular polygon sides=3,minimum size=5.6pt] at (#1) {};}
\newcommand{\dD}[1]{\node[dev,diamond,minimum size=5.6pt] at (#1) {};}
\def\yH{1.72} \def\yA{1.54} \def\yB{1.30} \def\yC{1.06} \def\yD{0.86} \def\yN{0.66}

% ---------------------------------------------------------------- device types
\node[hdr,anchor=south west] at (0.0,\yH) {device types};
\foreach \y in {\yA,\yB,\yC,\yN} { \node[box,minimum width=0.30in] at (0.17,\y) {}; }
\dA{0.17,\yA} \dB{0.17,\yB} \dC{0.17,\yC} \dD{0.17,\yN}
\node[text=ink2] at (0.17,\yD) {$\vdots$};
\draw[flow] (0.36,1.18) -- node[above,text=ink2] {partition} (0.80,1.18);

% ---------------------------------------------------------------- households
\node[hdr] at (1.24,\yH) {$N$ households};
\node[hh] (h1) at (1.24,\yA) {}; \node[anchor=west] at (h1.west) {$h_1$};
\node[hh,advbox] (h2) at (1.24,\yB) {}; \node[anchor=west,text=adv] at (h2.west) {$h_2$};
\node[hh] (h3) at (1.24,\yC) {}; \node[anchor=west] at (h3.west) {$h_3$};
\node[text=ink2] at (1.24,\yD) {$\vdots$};
\node[hh] (hN) at (1.24,\yN) {}; \node[anchor=west] at (hN.west) {$h_N$};
\dA{1.40,\yA} \dB{1.52,\yA}
\dC{1.46,\yB}
\dB{1.40,\yC} \dD{1.52,\yC}
\dA{1.34,\yN} \dC{1.46,\yN} \dD{1.58,\yN}
\node[note,text width=1.95in,anchor=north west,align=left] at (0.02,0.47)
  {\textcolor{adv}{red}: in the malicious set $B$, which sends arbitrary training updates};

% ---------------------------------------------------------------- members
\node[hdr] at (2.68,\yH) {$K$ members};
\node[mem] (f1) at (2.68,\yA) {$f_1$: FedAvg on $S_1$};
\node[mem,touched] (f2) at (2.68,\yB) {$f_2$: FedAvg on $S_2$};
\node[mem,touched] (f3) at (2.68,\yC) {$f_3$: FedAvg on $S_3$};
\node[text=ink2] at (2.68,\yD) {$\vdots$};
\node[mem] (fK) at (2.68,\yN) {$f_K$: FedAvg on $S_K$};
% subsets S_j of k=2 households (illustration only): S_1={h1,h3}, S_2={h1,h2}, S_3={h2,h3}, S_K={h3,hN}
\draw[sub] (h1.east) -- (f1.west); \draw[sub] (h3.east) -- (f1.west);
\draw[sub] (h1.east) -- (f2.west); \draw[subadv] (h2.east) -- (f2.west);
\draw[subadv] (h2.east) -- (f3.west); \draw[sub] (h3.east) -- (f3.west);
\draw[sub] (h3.east) -- (fK.west); \draw[sub] (hN.east) -- (fK.west);
\node[note,text width=1.6in] at (2.84,0.47)
  {\textcolor{adv}{dashed}: touched ($k{=}2$ shown)};

% ---------------------------------------------------------------- vote and certificate
\node[box,minimum width=0.52in,minimum height=0.46in,align=center,fill=panel] (vote) at (3.58,1.10)
  {plurality\\[-1pt]vote on\\[-1pt]one flow $x$};
\foreach \f in {f1,f2,f3,fK} { \draw[flow] (\f.east) -- (vote.west); }
\node[note,text width=0.62in] at (3.58,0.80) {deployed ensemble};
\node[box,align=left,fill=panel,inner sep=4.5pt,text width=2.38in,anchor=west,
      execute at begin node={\hyphenpenalty=10000\exhyphenpenalty=10000}] (cert) at (3.98,1.215)
  {$x$ is certified at budget $m$ when\\[1pt]
   \hspace*{0.34in}$\dfrac{n_1(x)-n_2(x)}{K} > \dfrac{2\,c_{\max}(m)}{K}$,\\[2pt]
   with $n_1,n_2$ its two largest vote counts and $c_{\max}(m)$ the most members any $m$ clients can touch.};
\node[note,text width=2.5in] at (cert.south |- 0,0.735)
  {nothing is certified once the $m$ clients touch at least half the members; for members a single client controls, certification needs $\beta<1-2^{-1/k}$};
\draw[flow] (vote.east) -- (vote.east -| cert.west);
\node[hdr] at (cert.north |- 0,\yH) {certificate};
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
