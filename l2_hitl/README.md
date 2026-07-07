# L2 · Human in the loop (durable pause)

**Adds:** `request_access` becomes a `LongRunningFunctionTool` — it returns a *pending* status and the run **ends**, handing control back.

```bash
uv run python driver.py reset
uv run python driver.py start Alice       # pauses at AWAITING_APPROVAL, process exits
#   <-- kill the terminal here; nothing is lost -->
uv run python driver.py approve Alice     # a NEW process resumes and finishes
```
The pause survives the process because the pending call is in the durable session. **No `ResumabilityConfig` needed** — this is the long-running-tool mechanism (resume = send a `function_response`). → **L3**
