"""Step 7 — THE driver, extracted. One function, three entrances.

Steps 1–6 hid the driver inside per-command scripts. This step gives it a name:

    drive(session_id, new_message=..., invocation_id=...)

  1. new work          drive(sid, new_message=<user text>)
  2. doorbell rings    drive(sid, new_message=<function_response>)   # human/webhook
  3. crash recovery    drive(sid, invocation_id=<unfinished id>)     # see sweeper.py

Locally YOU call it (CLI below). In production something else calls the same
contract: a webhook endpoint, a queue consumer, a scheduler, Agent Engine.
What changes is who calls drive() — never what drive() is.

Commands: reset | start <name> | approve <name> | status <name>
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()
os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

import fake_systems
from agent import app

DB = "sqlite+aiosqlite:///./onboarding.db"
APP = "onboarding"
USER = "u"


def session_service():
    return DatabaseSessionService(db_url=DB)


async def drive(session_id, *, new_message=None, invocation_id=None, service=None):
    """One run against a durable session. Returns 'PAUSED' or 'ENDED'."""
    service = service or session_service()
    runner = Runner(app=app, session_service=service)
    outcome = "ENDED"
    async for ev in runner.run_async(user_id=USER, session_id=session_id,
                                     new_message=new_message, invocation_id=invocation_id):
        for f in ev.get_function_calls() or []:
            lr = ev.long_running_tool_ids and f.id in ev.long_running_tool_ids
            print(f"    -> {f.name}({dict(f.args)}){' [PAUSE: awaiting human]' if lr else ''}")
            if lr:
                outcome = "PAUSED"
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if p.text and p.text.strip():
                    print(f"    <agent> {p.text.strip()}")
    return outcome


async def last_long_running_call(service, session_id):
    """The most recent long-running call in this session, or None.

    Note we do NOT try to infer 'still open' from function_response events:
    when a long-running tool returns its interim {'status': 'pending'} dict,
    that interim result is itself logged as a function_response — so counting
    responses is a trap. Whether the session is WAITING is what the explicit
    state enum from Step 2 is for: stage == AWAITING_APPROVAL.
    """
    s = await service.get_session(app_name=APP, user_id=USER, session_id=session_id)
    if not s:
        return None
    found = None
    for ev in s.events:
        if ev.long_running_tool_ids:
            for f in ev.get_function_calls() or []:
                if f.id in ev.long_running_tool_ids:
                    found = (f.id, f.name)
    return found


# ---- CLI: the three entrances, spelled out ---------------------------------

async def cmd_start(name):
    service = session_service()
    sid = f"s-{name}"
    await service.create_session(app_name=APP, user_id="u", session_id=sid)
    print(f"[start] onboarding {name}")
    out = await drive(sid, new_message=types.Content(
        role="user", parts=[types.Part(text=f"Onboard {name}.")]), service=service)
    print(f"[drive] -> {out}")
    await cmd_status(name)


async def cmd_approve(name):
    service = session_service()
    sid = f"s-{name}"
    s = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
    if not s or s.state.get("stage") != "AWAITING_APPROVAL":
        print(f"[approve] nothing awaiting approval for {name}")
        return
    fid, fname = await last_long_running_call(service, sid)
    print(f"[approve] doorbell rings → function_response {fname}({fid})")
    out = await drive(sid, new_message=types.Content(role="user", parts=[types.Part(
        function_response=types.FunctionResponse(id=fid, name=fname,
                                                 response={"approved": True}))]),
        service=service)
    print(f"[drive] -> {out}")
    await cmd_status(name)


async def cmd_status(name):
    s = await session_service().get_session(app_name=APP, user_id=USER, session_id=f"s-{name}")
    stage = s.state.get("stage") if s else None
    print(f"[status] {name}: stage={stage}  {fake_systems.summary()}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "reset":
        for f in ["onboarding.db", "fake_systems.json"]:
            if os.path.exists(f):
                os.remove(f)
        fake_systems.reset()
        print("[reset] clean slate")
        return
    asyncio.run({"start": cmd_start, "approve": cmd_approve,
                 "status": cmd_status}[cmd](sys.argv[2]))


if __name__ == "__main__":
    main()
