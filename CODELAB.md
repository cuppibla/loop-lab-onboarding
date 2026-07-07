author: Annie Wang (cuppibla)
summary: Build a long-running AI agent with Google's ADK — one that survives crashes, pauses for a human, and never double-acts.
id: lab1-long-running-agent
categories: ai,adk,agents
environments: Web
status: Draft
feedback link: https://github.com/cuppibla/loop-lab-onboarding/issues

# Lab 1: The Long-Running Agent

## Overview

Most agents you build are a single, blocking request → response: everything lives in memory
for a few seconds and then it's done. Real work isn't like that. An onboarding flow, a
deployment, a booking — these span **minutes to days**, **wait on humans**, and **crash**.

In this codelab you'll build an **onboarding agent** step by step and turn it into a proper
**long-running agent**. By the end it will:

- **survive a crash** and resume from the exact step,
- **pause for a manager's approval** and continue when it arrives,
- and **never order the new hire two laptops**, even when a crash re-runs a step.

**The big idea:** a long-running agent isn't a process that stays alive — it's a **durable
session** that short-lived runs read and write, plus a **driver** that re-drives a run
whenever there's something to do. You engineer the driver; ADK gives you the durable pieces.

Each step lives in its own folder (`01_baseline` → `06_cloud`) and adds exactly one idea.

## Setup

Clone the repo once and set up your environment.

💻 Clone and enter the repo:
```bash
git clone https://github.com/cuppibla/loop-lab-onboarding.git
cd loop-lab-onboarding
```

💻 Create the environment (pip flavor):
```bash
./setup_venv.sh          # Windows: setup_venv.bat
source .venv/bin/activate
```
> Prefer uv? Just run `uv sync` instead, and use `uv run python …` in place of `python …`.

👉 Put your Gemini API key in `.env` (get one at https://aistudio.google.com/apikey):
```
GOOGLE_API_KEY=your-key-here
GOOGLE_GENAI_USE_VERTEXAI=False
```

You're ready.

## 1 · Run the baseline (and lose it)

💻
```bash
cd 01_baseline
python driver.py Alice
```

Expected output:
```
    -> create_account({'employee': 'Alice'})
    -> order_laptop({'employee': 'Alice'})
    -> request_access({'employee': 'Alice', 'system': 'prod'})
    -> grant_access({'employee': 'Alice', 'system': 'prod'})
    -> send_welcome({'employee': 'Alice'})
    <agent> ONBOARDING COMPLETE
```

The agent runs all five onboarding steps in one process, in memory.

👉 Now imagine the process dies halfway. There's no `onboarding.db`, no saved progress —
**everything is gone.** A real onboarding takes days and *will* be interrupted. We need
durability. `cd ..`

## 2 · Make it survive (persistence)

L1 swaps the in-memory session for a database and writes an explicit `state["stage"]`.

💻
```bash
cd 02_persistence
python driver.py reset
python driver.py start Alice
python driver.py status Alice      # a FRESH process reads the stage from disk
```

Expected (the status line comes from a brand-new process):
```
[status] Alice: stage=DONE  {'accounts': 1, 'laptop_orders': 1, 'access_grants': 1, 'welcomes': 1}
```

**What changed:** one line — `DatabaseSessionService(db_url="sqlite+aiosqlite:///./onboarding.db")`.
Progress now lives on disk.

👉 But there's still no way to *continue* an interrupted run — you can read the saved stage,
not resume it. **Persisted ≠ resumable.** `cd ..`

## 3 · Pause for a human (the first "kill the server")

Some actions you never let an agent do alone. In L2, `request_access` becomes a
**`LongRunningFunctionTool`**: it returns a *pending* status and the run **ends**, handing
control back. A manager approves later and the run resumes.

💻 Start it — it pauses at the approval step:
```bash
cd 03_human_approval
python driver.py reset
python driver.py start Alice
```
```
    -> request_access({'employee': 'Alice', 'system': 'prod'}) [PAUSE: awaiting human]
[status] Alice: stage=AWAITING_APPROVAL  {'accounts': 1, 'laptop_orders': 1, 'access_grants': 0, ...}
```

👉 The process has **exited** and it's waiting on a human. Close the terminal — kill it
entirely. Nothing is lost. Now, in a **fresh** terminal, approve:

💻
```bash
python driver.py approve Alice
```
```
    -> grant_access(...)
    -> send_welcome(...)
    <agent> ONBOARDING COMPLETE
[status] Alice: stage=DONE  ...
```

**Why it works:** the pending approval lives in the durable session, so a completely
separate process resumes it. Notice we didn't even need crash-recovery machinery for this —
it's the long-running-tool mechanism (resume = send a `function_response`). `cd ..`

## 4 · Survive a crash

L2 handled a *clean* pause. What about a real crash mid-run? L3 adds
**`ResumabilityConfig(is_resumable=True)`** to the `App` and a `resume` command. Now an
**unfinished** invocation can be re-driven — ADK replays completed steps and re-runs only the
unfinished one.

💻
```bash
cd 04_crash_recovery
python driver.py reset
python driver.py start Alice
```
👉 While it's running, press **Ctrl-C** between steps to kill it. Then re-drive it:
```bash
python driver.py resume Alice
```
It picks up from where it died and continues.

👉 But here's the question that makes or breaks a long-running agent: *what if the crash
lands **inside** a step that already did something — like ordering a laptop?* `cd ..`

## 5 · Don't order two laptops (idempotency)

This is the most important step. Crash-resume **re-runs** the unfinished step. If that step
already ordered a laptop, you order **two**.

💻 See the bug (guard off, crash right after ordering):
```bash
cd 05_idempotency
python driver.py reset
IDEMPOTENT=0 CRASH_AFTER_ORDER=1 python driver.py start Bob    # crashes after ordering
IDEMPOTENT=0 python driver.py resume Bob
```
```
[status] Bob: stage=AWAITING_APPROVAL  {'accounts': 1, 'laptop_orders': 2, ...}   <-- TWO laptops
```

💻 Now the fix — a check-before-act guard, stored **independently** of session state:
```bash
python driver.py reset
CRASH_AFTER_ORDER=1 python driver.py start Carol
python driver.py resume Carol
```
```
[status] Carol: stage=AWAITING_APPROVAL  {'accounts': 1, 'laptop_orders': 1, ...}   <-- ONE laptop
```

**The guard** (in `agent.py`):
```python
def order_laptop(employee, tool_context):
    if fake_systems.has_laptop_order(employee):     # ask first
        return {"status": "already_ordered"}
    ...
```
It lives in `fake_systems` (an independent store), **not** in session state — because state
also rides the event log and might not be flushed in the crash window.

**The lesson:** recovery re-runs steps, so every side effect must be idempotent. *A loop that
recovers but doesn't guard its side effects is just a bug that runs twice.* `cd ..`

## 6 · Take it to Google Cloud

Nothing about the agent changes — only the *connection*. "Durability is a connection string,
not a rewrite."

- **Cloud SQL for PostgreSQL:** set `DB_URL="postgresql+asyncpg://"` and wire the Cloud SQL
  Python Connector (async `asyncpg`, **not** the sync `pg8000`) — see
  `06_cloud/cloudsql_engine.py`.
- **Agent Runtime:** `adk deploy` gives you **managed sessions** (no database to run) and
  **Cloud Trace** across every real user. The paused-approval invocation lives in the managed
  runtime.

💻 It still runs locally on SQLite, so you can try it without a GCP project:
```bash
cd 06_cloud
python driver.py reset && python driver.py start Alice && python driver.py approve Alice
```

⚠ If you provision Cloud SQL, remember to **tear it down** afterward — it bills while running.

## Recap

You built a long-running agent one idea at a time:

| Level | Idea | ADK piece |
|---|---|---|
| L0 | baseline | `Agent` + tools |
| L1 | persistence | `DatabaseSessionService` |
| L2 | pause for a human | `LongRunningFunctionTool` |
| L3 | survive a crash | `ResumabilityConfig` |
| L4 | never double-act | your idempotency guard |
| L5 | same code, managed | Cloud SQL / Agent Runtime |

**The four pieces that make it real:** a durable session (1), resumable runs (2), pause/resume
via function-response (3), and **the driver + idempotency** (4) — which is the part *you*
engineer. That driver is "the loop" in loop engineering.

**Next:** Lab 2 (a self-evolving agent that rewrites its own instructions — and learns to
cheat) and Lab 3 (an agent that turns yesterday's tickets into lessons via a nightly "dream").
