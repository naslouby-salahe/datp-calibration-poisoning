#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== DATP-CP Research Dossier — LaTeX build ==="

# Clean previous auxiliary files
echo "Cleaning auxiliary files..."
rm -f main.aux main.log main.out main.toc main.fls main.fdb_latexmk texput.log
rm -f sections/*.aux

# Prefer latexmk if available; fall back to two pdflatex passes
if command -v latexmk &>/dev/null; then
  echo "Using latexmk..."
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
  mv -f main.pdf DATP_CP_Research_Dossier.pdf
else
  echo "latexmk not found; using pdflatex (2 passes)..."
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
  if [ ! -f main.pdf ]; then
    echo "ERROR: Compilation failed — main.pdf not produced." >&2
    exit 1
  fi
  mv -f main.pdf DATP_CP_Research_Dossier.pdf
fi

FINAL="$DIR/DATP_CP_Research_Dossier.pdf"

if [ ! -f "$FINAL" ]; then
  echo "ERROR: $FINAL not found after build." >&2
  exit 1
fi

echo ""
echo "--- Build summary ---"
pdfinfo "$FINAL" | grep -E "^(Pages|File size|Creator|Producer):" || true

PAGES=$(pdfinfo "$FINAL" 2>/dev/null | grep "^Pages:" | awk '{print $2}')
echo "Pages: $PAGES"

if [ "${PAGES:-0}" -gt 7 ]; then
  echo "WARNING: Page count $PAGES exceeds maximum of 7." >&2
fi

echo ""
echo "--- Forbidden-term audit ---"
FORBIDDEN=(
  "DATP_CP_Roadmap"
  "July 2026"
  "Salaheddine"
  "Lachgar"
  "Hrimech"
  "LAMSAD"
  "ENSA"
  "UCA"
  "roadmap.md"
)
ISSUES=0
for phrase in "${FORBIDDEN[@]}"; do
  if pdftotext "$FINAL" - 2>/dev/null | grep -qi "$phrase"; then
    echo "  WARNING: Found forbidden term: '$phrase'" >&2
    ISSUES=$((ISSUES + 1))
  fi
done
if [ "$ISSUES" -eq 0 ]; then
  echo "  No forbidden terms detected."
fi

echo ""
echo "=== Build complete ==="
echo "  PDF: $FINAL"
echo "  Pages: $PAGES"
