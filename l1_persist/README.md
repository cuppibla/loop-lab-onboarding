# L1 · Persistence

**Adds:** `DatabaseSessionService` (SQLite via `sqlite+aiosqlite`) + an explicit `state["stage"]`.

```bash
uv run python driver.py reset
uv run python driver.py start Alice
uv run python driver.py status Alice      # a FRESH process reads the stage from disk
```
The progress now lives in `onboarding.db`.

**The catch:** you can see the saved stage, but there's still no way to *continue* an interrupted run. **Persisted ≠ resumable.** → **L2 / L3**
