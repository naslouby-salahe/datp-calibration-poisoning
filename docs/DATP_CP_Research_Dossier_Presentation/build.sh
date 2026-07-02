#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/dossier.html"
FINAL="$DIR/DATP_CP_Research_Dossier_Presentation.pdf"

echo "Building PDF from $SRC..."
python3 - "$SRC" "$FINAL" <<'PYEOF'
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
assert src.exists(), f"Source not found: {src}"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{src.resolve()}", wait_until="networkidle")
    page.pdf(
        path=str(dst),
        format="A4",
        landscape=True,
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    browser.close()

print(f"PDF written: {dst}  ({dst.stat().st_size/1024:.0f} KB)")
PYEOF

echo "Running automated checks..."
pdfinfo "$FINAL" | grep -E "^(Pages|File size|Creator|Producer):"
echo "Text extraction check..."
pdftotext "$FINAL" - | wc -c | xargs echo "Text characters:"

echo "Checking for forbidden phrases..."
FORBIDDEN=(
  "training poisoning" "model poisoning" "aggregation poisoning"
  "privacy guarantee" "deployment ready" "raw traffic attack"
  "universal vulnerability" "secure federated learning solution"
  "complete defense" "proves robustness"
)
ISSUES=0
for phrase in "${FORBIDDEN[@]}"; do
  if pdftotext "$FINAL" - | grep -qi "$phrase"; then
    echo "  WARNING: Found forbidden phrase: '$phrase'"
    ISSUES=$((ISSUES+1))
  fi
done
if [ "$ISSUES" -eq 0 ]; then
  echo "  No forbidden phrases detected."
fi

echo ""
echo "Build complete."
echo "  PDF: $FINAL"
