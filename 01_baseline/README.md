# L0 · Baseline (no durability)

The onboarding agent runs all 5 steps in **one process, in memory**.

```bash
uv run python driver.py Alice
```
You'll see `create_account → order_laptop → request_access → grant_access → send_welcome → ONBOARDING COMPLETE`.

**The point:** it's all in RAM. Kill it mid-run and everything is lost. A real onboarding spans hours and *will* be interrupted — so we need durability. → **L1**
