FedHomeGuard — "When Client-Count Certification Holds for Federated IoT
Intrusion Detection".  IEEE S&P 2027, Cycle 2.

Upload this folder as a .zip.  Everything the document needs is inside it.

HOW TO COMPILE
  Main document : main.tex
  Compiler      : pdfLaTeX
  Sequence      : pdflatex -> bibtex -> pdflatex -> pdflatex
                  (most services run this automatically; if yours does not,
                  run it in that order, since the citation numbers only settle
                  on the third pass)

EXPECTED OUTPUT — check this after the first successful compile
  18 pages total.  Body text ends on page 13.  Appendix A opens on page 14.
  References and appendices occupy pages 14-18.
  These are hard venue limits: 13 pages of text, 5 further pages for references
  and appendices, 18 total, and over-length is rejected without review.  If the
  service reports a different page count, something in its environment differs
  from the one this was measured on — do not submit until it reads 18.

WHY IEEEtran.cls AND IEEEtran.bst ARE IN THIS FOLDER
  This is the fix for the compile failure.  The previous bundle shipped neither,
  so the build died at \documentclass on any service whose TeX installation
  does not carry the IEEE class, and could silently pick a different version on
  one that does.  LaTeX searches the project directory before the system tree,
  so keeping these two files beside main.tex pins the build regardless of which
  TeX Live the service runs.
  IEEEtran.cls is V1.8b (2015/08/26) and IEEEtran.bst is v1.14 — the exact files
  the 18-page layout was measured under.  The call for papers requires V1.8b
  with options "conference,compsoc" and rejects without review any submission
  that alters margins, font or line spacing.  Do not delete these files and do
  not change the \documentclass line.

WHAT IS IN HERE
  main.tex           entry point; \input's everything below
  refs.bib           bibliography source
  main.bbl           pre-built bibliography, so the document still typesets its
                     references on a service that will not run bibtex
  sections/          the body, one file per section
  generated/         numbers, macros, tables and appendix text produced by the
                     analysis scripts.  DO NOT HAND-EDIT THESE.  Every figure in
                     the paper traces to a result file through them; editing one
                     here silently decouples the paper from its evidence.  Fix
                     the generator in the repository instead and re-export.
  generated/floats/  table and figure float wrappers
  figures/           the three plots, as PDF
  IEEEtran.cls/.bst  pinned class and bibliography style (see above)

WHAT IS DELIBERATELY NOT IN HERE
  No .git directory, no .aux/.log/.out/.fls/.fdb_latexmk build products, and no
  .DS_Store.  The earlier bundle carried an entire .git tree, which is junk in a
  compile service and leaks the repository's history.

IF IT STILL FAILS
  Read the first error in the log, not the last.  The common ones:
    "File `IEEEtran.cls' not found"  -> the two class files did not survive the
        upload; re-upload with them at the top level, beside main.tex.
    "File `generated/numbers.tex' not found" -> the folder structure was
        flattened on upload; sections/, generated/, generated/floats/ and
        figures/ must keep their paths.
    Citations rendering as [?] -> bibtex did not run; one more pdflatex pass
        after a bibtex pass fixes it, and main.bbl is bundled as a fallback.
