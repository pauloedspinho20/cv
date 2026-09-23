#!/usr/bin/env bash
#
# Regenerate the ATS-friendly PDFs from the HTML sources using headless Chrome.
# No dependencies beyond Chrome. Works on macOS/Linux (set $CHROME to override).
#
# Usage:
#   scripts/build-pdfs.sh          # build all
#   scripts/build-pdfs.sh cv       # full-stack CV only
#   scripts/build-pdfs.sh cover    # cover letter only
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

if [ ! -x "$CHROME" ] && ! command -v "$CHROME" >/dev/null 2>&1; then
  echo "Chrome not found. Set CHROME=/path/to/chrome and retry." >&2
  exit 1
fi

render() { # $1 = output pdf, $2 = source html (absolute)
  local out="$1" src="$2"
  rm -f "$out"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --user-data-dir="$(mktemp -d)" --no-pdf-header-footer \
    --print-to-pdf="$out" "file://$src" >/dev/null 2>&1 &
  local pid=$!
  for _ in $(seq 1 40); do
    [ -f "$out" ] && sleep 1 && break
    sleep 1
  done
  kill "$pid" 2>/dev/null || true
  if [ -f "$out" ]; then
    printf '  built %s\n' "${out#$ROOT/}"
  else
    printf '  FAILED %s\n' "${out#$ROOT/}" >&2
    return 1
  fi
}

target="${1:-all}"

case "$target" in
  cv)
    render "$ROOT/assets/Paulo-Pinho-Senior-FullStack-Developer-CV.pdf" "$ROOT/index.html"
    ;;
  cover)
    render "$ROOT/cover-letter/Paulo-Pinho-Cover-Letter.pdf" "$ROOT/cover-letter/index.html"
    ;;
  all)
    render "$ROOT/assets/Paulo-Pinho-Senior-FullStack-Developer-CV.pdf" "$ROOT/index.html"
    render "$ROOT/cover-letter/Paulo-Pinho-Cover-Letter.pdf" "$ROOT/cover-letter/index.html"
    ;;
  *)
    echo "Unknown target: $target (use: cv | cover | all)" >&2
    exit 1
    ;;
esac

echo "Done."
