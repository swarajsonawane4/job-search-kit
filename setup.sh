#!/usr/bin/env bash
# One-time setup. Run from this folder:  bash setup.sh
set -e
cd "$(dirname "$0")"

echo "== Python environment"
if ! command -v python3 >/dev/null; then
  echo "  python3 not found. Install it from https://www.python.org/downloads/ and rerun."; exit 1
fi
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "  ok: .venv with PyYAML and pypdf"

echo "== LaTeX (builds the PDFs)"
if command -v pdflatex >/dev/null || [ -x "$HOME/Library/TinyTeX/bin/universal-darwin/pdflatex" ]; then
  echo "  ok: pdflatex found"
else
  echo "  MISSING: pdflatex. Install one of:"
  echo "    macOS:   curl -sL https://yihui.org/tinytex/install-bin-unix.sh | sh"
  echo "             (then: tlmgr install titlesec enumitem helvetic)"
  echo "    Linux:   sudo apt install texlive-latex-extra texlive-fonts-recommended"
  echo "    Windows: install MiKTeX from https://miktex.org/download"
fi

echo "== Your personal files (git-ignored, never pushed)"
.venv/bin/python tools/init_workspace.py

echo "== Tracker check"
.venv/bin/python tools/state.py >/dev/null && echo "  ok: tools/state.py runs"

echo
echo "Done. Next: open Claude Code here with Chrome (type: claude --chrome) and say"
echo '  "Setup is new. Follow CLAUDE.md, first session."'
