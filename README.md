# Lab 1 · The Long-Running Agent

A hands-on ADK codelab: how to make an agent that **survives time** — it spans a long
process, pauses for a human, survives crashes, and never double-acts. Built as a graded
ladder you run in your terminal, one idea per level.

> **Concept:** a long-running agent isn't a process that stays alive — it's a **durable
> session** that short-lived runs read and write, plus a **driver** that re-drives a run
> whenever there's something to do. You engineer the driver; ADK gives you the durable
> pieces. *(That driver is "the loop" in loop engineering.)*

**Scenario:** onboarding a new hire — `create_account → order_laptop → [manager approval] →
grant_access → send_welcome`. External systems are local stubs ([any level's
`fake_systems.py`](01_baseline/fake_systems.py)); progress is an explicit `state["stage"]`.

> **📖 Following the guided codelab?** See **[CODELAB.md](CODELAB.md)** — the step-by-step,
> clone-and-run walkthrough (claat-ready for codelabs.developers.google.com).

## Setup
```bash
# pip flavor (mirrors the other ADK tutorials):
./setup_venv.sh            # Windows: setup_venv.bat
source .venv/bin/activate
# — or — uv flavor:
uv sync                    # then use `uv run python …`

cp .env.example .env       # then put your GOOGLE_API_KEY in .env   (Gemini)
```

## The ladder (run each in its own folder)
Each level adds exactly one idea. `diff` two neighbours to see the lesson.

| Level | Adds | Key ADK piece | Try it |
|---|---|---|---|
| **[01_baseline](01_baseline)** | 5 steps, no durability | `Agent` + `FunctionTool`s | `python driver.py Alice` |
| **[02_persistence](02_persistence)** | progress saved to a DB | `DatabaseSessionService` (SQLite) | `start` / `status` |
| **[03_human_approval](03_human_approval)** | pause for a human | `LongRunningFunctionTool` | `start` → `approve` |
| **[04_crash_recovery](04_crash_recovery)** | survive a crash | `ResumabilityConfig` | `start` → Ctrl-C → `resume` |
| **[05_idempotency](05_idempotency)** | don't order two laptops | your own guard | crash → `resume` → bug → fix |
| **[06_cloud](06_cloud)** | same code, managed | Cloud SQL / Agent Runtime | `DB_URL` swap / `adk deploy` |

```bash
cd 03_human_approval
uv run python driver.py reset
uv run python driver.py start Alice     # pauses at approval; the process exits
uv run python driver.py approve Alice   # a fresh process resumes and finishes
```

## The two "kill the server" moments (why this lab exists)
- **L2 — kill while waiting for a human:** the run already ended cleanly; a fresh process
  resumes from the durable session. Nothing lost.
- **L4 — crash *inside* a step:** resume re-runs the unfinished step → it orders a **second
  laptop**. The fix is an **idempotency guard**. *A loop that recovers but doesn't guard its
  side effects is just a bug that runs twice.*

## How it really works (the 4 pieces)
| # | What | Who provides it |
|---|---|---|
| 1 | Durable session (state in the DB, not memory) | ADK `DatabaseSessionService` → Cloud SQL |
| 2 | Resumable runs (replay done, re-run unfinished) | ADK `ResumabilityConfig` *(experimental in 2.3)* |
| 3 | Pause/resume via function-response | ADK `LongRunningFunctionTool` |
| 4 | The driver + idempotency (event-driven harness) | **you** (or Agent Runtime) |

## Notes / gotchas (verified on ADK 2.3.0)
- `DatabaseSessionService` uses an **async** engine → `sqlite+aiosqlite://` locally,
  `postgresql+asyncpg://` for Cloud SQL (**not** the sync `pg8000`). Deps: `google-adk[db]`,
  `aiosqlite`, `greenlet`.
- **Resume after an approval pause:** send a `function_response` (no `invocation_id`).
  **Resume after a crash:** `run_async(invocation_id=<last event>, new_message=None)`.
- Detect the pause via `event.long_running_tool_ids`.

## `reference/`
The Phase-0 proof-of-concept (all mechanics in one place) + `run_poc.sh`. The graded levels
above were forward-authored from it.
