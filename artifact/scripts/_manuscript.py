"""Where the paper generators write (retargeted 2026-10-07).

In the authors' repository the paper's manuscript folder sits beside scripts/ and is the single
source of truth for its generated/ (number macros, tables, paragraphs) and figures/ (figure PDFs);
the generators write there directly. Where that folder is absent, as in the released artifact, they
write into out/ at the repository root. FHG_GENERATED and FHG_FIGURES override both targets (the
manuscript's gate uses them to regenerate every file into a temporary directory and compare).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUSCRIPT = os.path.join(ROOT, "manuscript")  # the paper's folder in the authors' repository; absent here
_HOME = MANUSCRIPT if os.path.isdir(MANUSCRIPT) else None
GENERATED = os.environ.get("FHG_GENERATED") or (os.path.join(_HOME, "generated") if _HOME
                                                else os.path.join(ROOT, "out"))
FIGURES = os.environ.get("FHG_FIGURES") or (os.path.join(_HOME, "figures") if _HOME
                                            else os.path.join(ROOT, "out"))
# generated/ inside a scratch mirror of the repository (scripts/gen_r5_std_fix.py builds mirrors and
# passes FHG_GENERATED explicitly, so any relative path works).
GENERATED_REL = os.path.join("out", "generated")
