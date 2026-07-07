# L4 · Idempotency (the load-bearing lesson)

Crash-resume **re-runs** the unfinished step. If that step already ordered a laptop, you order **two**.

**See the bug** (guard off, crash right after ordering):
```bash
uv run python driver.py reset
IDEMPOTENT=0 CRASH_AFTER_ORDER=1 uv run python driver.py start Bob   # crashes after ordering
IDEMPOTENT=0 uv run python driver.py resume Bob                      # re-runs order_laptop
# -> laptops = 2   (the bug)
```

**The fix** (a check-before-act guard, in an INDEPENDENT store — not session state, which also rides the event log and may not be flushed in the crash window):
```bash
uv run python driver.py reset
CRASH_AFTER_ORDER=1 uv run python driver.py start Carol
uv run python driver.py resume Carol
# -> laptops = 1   (fixed)
```

**Lesson:** recovery re-runs steps, so every side effect must be idempotent. *A loop that recovers but doesn't guard its side effects is just a bug that runs twice.*
