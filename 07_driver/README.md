# Step 7 · Who presses Continue?

**Adds:** nothing to the agent — `diff agent.py ../05_idempotency/agent.py` shows only a docstring. This step extracts **the driver** into a named contract (`drive.py`), then builds the piece Steps 1–6 quietly left to you-at-a-keyboard: **`sweeper.py`, the thing that *notices* a crash**.

```
drive(session_id, ...)        one function, three entrances:
  new_message=<user text>       1. new work
  new_message=<function_resp>   2. the doorbell (human/webhook approval)
  invocation_id=<unfinished>    3. crash recovery (the sweeper's entrance)
```

## The demo — hands off the keyboard

```bash
uv run python drive.py reset
CRASH_AFTER_ORDER=1 uv run python drive.py start Alice   # dies mid-order
uv run python sweeper.py     # CRASHED -> re-drives; guard refuses laptop #2; parks at approval
uv run python sweeper.py     # PAUSED  -> "not my job" — the discriminator
uv run python drive.py approve Alice                     # the doorbell
uv run python sweeper.py     # ENDED (DONE) -> all quiet
```

## The discriminator (the load-bearing part)

| Session looks like | Verdict | Sweeper does |
|---|---|---|
| `stage == DONE` / final agent text | ENDED | nothing |
| `stage == AWAITING_APPROVAL` | PAUSED | **nothing — that wake-up belongs to the doorbell** |
| anything else mid-run | CRASHED | re-drive the unfinished invocation |

**⚠ Why the PAUSED row matters:** re-driving an invocation that is parked at a
clean pause **skips the human approval** (verified on ADK 2.5.0 — the model
just proceeds to `grant_access`). A sweeper that can't tell *pause* from
*crash* silently bypasses your human gate. The two resumes from Steps 3 and 4
each have their own wake-up path; the sweeper owns only the crash one.

**In production:** this exact loop is a scheduled job (Cloud Run job + Cloud
Scheduler); the doorbell is a webhook endpoint. Same `drive()`, same rules —
**what changes is who calls `drive()`, never what `drive()` is.**
The doorbell side of the story gets its own lab (fan-out, joins, and the
machine-callback doorbell) — see the series README.
