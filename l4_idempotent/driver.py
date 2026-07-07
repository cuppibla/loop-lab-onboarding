"""L3 driver — adds `resume` for crash recovery.
Commands: reset | start <name> | approve <name> | resume <name> | status <name>

Demo: `start Alice`, kill it (Ctrl-C) between steps, then `resume Alice` → it
re-drives the unfinished invocation and continues.
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


async def _drive(runner, sid, new_message=None, invocation_id=None):
    pending = None
    async for ev in runner.run_async(user_id="u", session_id=sid,
                                     new_message=new_message, invocation_id=invocation_id):
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


async def _peek(service, sid):
    s = await service.get_session(app_name=APP, user_id="u", session_id=sid)
    stage = s.state.get("stage") if s else None
    inv = s.events[-1].invocation_id if s and s.events else None
    return stage, inv


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


async def cmd_resume(name):
    service = ss()
    runner = Runner(app=app, session_service=service)
    sid = f"s-{name}"
    stage, inv = await _peek(service, sid)
    print(f"[resume] re-drive unfinished invocation={inv} (stage before={stage})")
    await _drive(runner, sid, invocation_id=inv)
    await cmd_status(name)


async def cmd_status(name):
    stage, _ = await _peek(ss(), f"s-{name}")
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
    asyncio.run({"start": cmd_start, "approve": cmd_approve,
                 "resume": cmd_resume, "status": cmd_status}[cmd](sys.argv[2]))


if __name__ == "__main__":
    main()
