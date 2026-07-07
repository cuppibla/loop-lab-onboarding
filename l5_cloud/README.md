# L5 · Cloud (same code, managed)

Point the **same** agent at Google Cloud. Only the *connection* changes — "durability is a connection string, not a rewrite."

- **Cloud SQL for PostgreSQL:** set `DB_URL="postgresql+asyncpg://"` and wire the Cloud SQL Python Connector (async `asyncpg`, **not** the sync `pg8000`). See [cloudsql_engine.py](cloudsql_engine.py).
- **Agent Runtime:** `adk deploy` gives **managed sessions** (no DB to run) + **Cloud Trace** across every real user. The paused-approval invocation lives in the managed runtime.
- **Teardown:** Cloud SQL bills while running — tear it down after the lab.

Locally this level still runs on SQLite (default `DB_URL`), so it's not broken without a GCP project:
```bash
uv run python driver.py reset && uv run python driver.py start Alice && uv run python driver.py approve Alice
```
