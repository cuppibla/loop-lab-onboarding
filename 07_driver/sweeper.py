"""Step 7 — the sweeper: the slow path that notices what crashed.

A crash leaves no error, no exception, no process — just a session whose last
invocation never finished. NOTHING will notice it for you: the process that
knew about the work is dead. The sweeper is the thing that notices. It scans
the session store, classifies every session, and re-drives only the wrecks.

The load-bearing part is the DISCRIMINATOR:

    ENDED  (last event is final agent text)  -> skip
    PAUSED (open long-running call)          -> skip — that wake-up belongs to
             the doorbell (a function_response). Re-driving a paused invocation
             SKIPS THE HUMAN APPROVAL (verified on ADK 2.5.0): the model just
             barrels on to grant_access. A sweeper that can't tell pause from
             crash silently bypasses your human gate.
    CRASHED (anything else)                  -> re-drive the unfinished invocation

Run:  python sweeper.py            one pass
      python sweeper.py --watch    scan every 10s (Ctrl-C to stop)

In production this exact loop is a scheduled job (Cloud Run job + Cloud
Scheduler). Same scan, same discriminator, same drive() call.
"""
import asyncio
import sys

from drive import APP, USER, drive, last_long_running_call, session_service


async def classify(service, sid):
    """-> ('EMPTY'|'ENDED'|'PAUSED'|'CRASHED', detail)

    The discriminator reads the explicit state enum from Step 2 — this is
    exactly what `state["stage"]` exists for. (Step 5 taught you not to trust
    state for SIDE-EFFECT dedup; for FLOW classification it is the source of
    truth you built.)
    """
    s = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
    if not s or not s.events:
        return "EMPTY", None
    stage = s.state.get("stage")
    if stage == "AWAITING_APPROVAL":                     # doorbell's job, not ours
        call = await last_long_running_call(service, sid)
        return "PAUSED", call[1] if call else "?"
    if stage == "DONE":
        return "ENDED", stage
    last = s.events[-1]
    final_text = (last.content and last.content.parts
                  and any(p.text and p.text.strip() for p in last.content.parts)
                  and not last.partial)
    if final_text:
        return "ENDED", stage                            # turn finished cleanly
    return "CRASHED", last.invocation_id                 # mid-run wreck: re-drive


async def sweep_once():
    service = session_service()
    listing = await service.list_sessions(app_name=APP, user_id=USER)
    print(f"[sweeper] scanning {len(listing.sessions)} session(s)")
    for meta in listing.sessions:
        verdict, detail = await classify(service, meta.id)
        if verdict == "CRASHED":
            print(f"  {meta.id}: CRASHED mid-run -> re-driving invocation {detail}")
            out = await drive(meta.id, invocation_id=detail, service=service)
            print(f"  {meta.id}: re-driven -> {out}")
        elif verdict == "PAUSED":
            print(f"  {meta.id}: PAUSED awaiting human ({detail}) -> not my job (doorbell)")
        else:
            print(f"  {meta.id}: {verdict} ({detail}) -> nothing to do")


async def watch(interval=10):
    while True:
        await sweep_once()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        asyncio.run(watch())
    else:
        asyncio.run(sweep_once())
