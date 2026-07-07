#!/usr/bin/env bash
# Phase-0 POC for Lab 1 (Long-Running Agent). Each `driver.py` call is a SEPARATE
# process — that's the whole point (proving durability across restarts).
set -e
cd "$(dirname "$0")"
F='FutureWarning|NotOpenSSL|warnings.warn|past its end|EXPERIMENTAL|resumability_config|build_function_declaration|greenlet library|Failed to inspect'
run() { uv run python driver.py "$@" 2>&1 | grep -viE "$F" || true; }

echo "############ PROOF A: pause at approval, resume in a FRESH process ############"
run reset
echo "--- process 1: start Alice (pauses at approval) ---";      run start Alice
echo "--- process 2 (fresh): approve Alice (resumes, finishes) ---"; run approve Alice

echo; echo "############ PROOF B1: crash mid-order, resume, guard OFF -> DOUBLE order (bug) ############"
run reset
echo "--- process 1: crash right after ordering ---"; IDEMPOTENT=0 CRASH_AFTER_ORDER=1 uv run python driver.py start Bob 2>&1 | grep -viE "$F" || true
run status Bob
echo "--- process 2 (fresh): resume, guard OFF ---"; IDEMPOTENT=0 run resume Bob   # -> laptops=2

echo; echo "############ PROOF B2: same crash, guard ON -> SINGLE order (fixed) ############"
run reset
echo "--- process 1: crash right after ordering ---"; CRASH_AFTER_ORDER=1 uv run python driver.py start Carol 2>&1 | grep -viE "$F" || true
run status Carol
echo "--- process 2 (fresh): resume, guard ON ---"; run resume Carol               # -> laptops=1
