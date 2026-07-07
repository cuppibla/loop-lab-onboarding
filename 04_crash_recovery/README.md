# L3 · Crash recovery

**Adds:** `ResumabilityConfig(is_resumable=True)` on the `App` + a `resume` command.

Now an **unfinished** invocation (the process died mid-run, not at a clean pause) can be re-driven — ADK replays completed steps and re-runs only the unfinished one:

```bash
uv run python driver.py reset
uv run python driver.py start Alice
#   <-- Ctrl-C it BETWEEN steps -->
uv run python driver.py resume Alice      # re-drives the unfinished invocation
```

**⚠ But** — what if the crash lands *inside* a side-effecting step, after it fired but before it was logged? → **L4**
