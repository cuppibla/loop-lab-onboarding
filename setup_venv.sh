#!/usr/bin/env bash
# One-time setup (pip flavor — mirrors the other ADK tutorials).
# uv users can just run `uv sync` instead.
set -e
echo "Creating virtual environment (.venv)…"
python3 -m venv .venv
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
