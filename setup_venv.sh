#!/usr/bin/env bash
# One-time setup (pip flavor — mirrors the other ADK tutorials).
# uv users can just run `uv sync` instead.
set -e

# ADK needs Python 3.10+ — pick a good interpreter (avoid an old system python).
PY=""
for c in python3.13 python3.12 python3.11 python3.10; do
  command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
done
if [ -z "$PY" ]; then
  echo "ERROR: need Python 3.10+ (ADK requirement). Install one, e.g. 'brew install python@3.12'." >&2
  exit 1
fi

echo "Using $($PY --version). Creating .venv…"
"$PY" -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
echo "Installing dependencies…"
pip install --quiet -r requirements.txt
[ -f .env ] || cp .env.example .env
echo ""
echo "Done. Next:"
echo "  1) put your GOOGLE_API_KEY in .env  (get one at https://aistudio.google.com/apikey)"
echo "  2) source .venv/bin/activate"
echo "  3) cd l0_baseline && python driver.py Alice"
