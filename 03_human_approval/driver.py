"""L2 driver — the harness with a human approval step.
Commands: reset | start <name> | approve <name> | status <name>

Demo: `start Alice` (pauses at approval) → kill the terminal → in a NEW terminal
`approve Alice` (resumes on the same durable session → finishes).
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


def ss():
    return DatabaseSessionService(db_url=DB)


async def _drive(runner, sid, new_message=None):
    pending = None
    async for ev in runner.run_async(user_id="u", session_id=sid, new_message=new_message):
        for f in ev.get_function_calls() or []:
            lr = ev.long_running_tool_ids and f.id in ev.long_running_tool_ids
            print(f"    -> {f.name}({dict(f.args)}){' [PAUSE: awaiting human]' if lr else ''}")
            if lr:
                pending = (f.id, f.name)
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if p.text and p.text.strip():
                    print(f"    <agent> {p.text.strip()}")
    return pending


async def cmd_start(name):
    service = ss()
    runner = Runner(app=app, session_service=service)
    sid = f"s-{name}"
    await service.create_session(app_name=APP, user_id="u", session_id=sid)
    print(f"[start] onboarding {name}")
    await _drive(runner, sid,
                 types.Content(role="user", parts=[types.Part(text=f"Onboard {name}.")]))
    await cmd_status(name)


async def cmd_approve(name):
    service = ss()
    runner = Runner(app=app, session_service=service)
    sid = f"s-{name}"
    s = await service.get_session(app_name=APP, user_id="u", session_id=sid)
    fid = fname = None
    for ev in s.events:
        if ev.long_running_tool_ids:
            for f in ev.get_function_calls() or []:
                if f.id in ev.long_running_tool_ids:
                    fid, fname = f.id, f.name
    print(f"[approve] manager approves → resume via function_response {fname}({fid})")
    resume = types.Content(role="user", parts=[types.Part(
        function_response=types.FunctionResponse(id=fid, name=fname,
                                                 response={"approved": True}))])
    await _drive(runner, sid, resume)
    await cmd_status(name)


async def cmd_status(name):
    s = await ss().get_session(app_name=APP, user_id="u", session_id=f"s-{name}")
    stage = s.state.get("stage") if s else None
    print(f"[status] {name}: stage={stage}  {fake_systems.summary()}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "reset":
        for f in ["onboarding.db", "fake_systems.json"]:
            if os.path.exists(f):
                os.remove(f)
        fake_systems.reset()
        print("[reset] clean slate")
        return
    asyncio.run({"start": cmd_start, "approve": cmd_approve, "status": cmd_status}[cmd](sys.argv[2]))


if __name__ == "__main__":
    main()
