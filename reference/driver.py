"""The DRIVER — the durable harness around the agent (this is 'the loop').

Commands (each is a SEPARATE process, like a real restart):
  reset
  start   <name>   # kick off; runs until it pauses at approval (or crashes/finishes)
  approve <name>   # resume a paused run by sending the manager's approval
  resume  <name>   # re-drive an unfinished invocation after a crash
  status  <name>
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

from onboarding import fake_systems
from onboarding.agent import app

DB = "sqlite+aiosqlite:///./onboarding.db"
APP = "onboarding"


def _ss():
    return DatabaseSessionService(db_url=DB)


async def _drive(runner, sid, new_message=None, invocation_id=None):
    pending = None
    async for ev in runner.run_async(
        user_id="u", session_id=sid, new_message=new_message, invocation_id=invocation_id
    ):
        for f in ev.get_function_calls() or []:
            lr = ev.long_running_tool_ids and f.id in ev.long_running_tool_ids
            print(f"    -> {f.name}({dict(f.args)}){' [LONG-RUNNING/pause]' if lr else ''}")
            if lr:
                pending = (f.id, f.name)
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if p.text and p.text.strip():
                    print(f"    <agent> {p.text.strip()}")
    return pending


async def _peek(ss, sid):
    s = await ss.get_session(app_name=APP, user_id="u", session_id=sid)
    stage = s.state.get("stage") if s else None
    inv = s.events[-1].invocation_id if s and s.events else None
    return stage, inv


async def cmd_start(name):
    ss = _ss()
    runner = Runner(app=app, session_service=ss)
    sid = f"s-{name}"
    await ss.create_session(app_name=APP, user_id="u", session_id=sid)
    print(f"[start] onboarding {name}  (IDEMPOTENT={os.environ.get('IDEMPOTENT','1')} "
          f"CRASH_AFTER_ORDER={os.environ.get('CRASH_AFTER_ORDER','0')})")
    await _drive(runner, sid,
                 new_message=types.Content(role="user",
                                           parts=[types.Part(text=f"Onboard {name}.")]))
    stage, _ = await _peek(ss, sid)
    print(f"[start] stage={stage}  laptops={fake_systems.laptop_count(name)}")


async def cmd_approve(name):
    ss = _ss()
    runner = Runner(app=app, session_service=ss)
    sid = f"s-{name}"
    s = await ss.get_session(app_name=APP, user_id="u", session_id=sid)
    fid = fname = None
    for ev in s.events:
        if ev.long_running_tool_ids:
            for f in ev.get_function_calls() or []:
                if f.id in ev.long_running_tool_ids:
                    fid, fname = f.id, f.name
    print(f"[approve] manager approves -> resume {name} via function_response {fname}({fid})")
    resume = types.Content(role="user", parts=[types.Part(
        function_response=types.FunctionResponse(id=fid, name=fname,
                                                 response={"approved": True}))])
    await _drive(runner, sid, new_message=resume)
    stage, _ = await _peek(ss, sid)
    print(f"[approve] stage={stage}  laptops={fake_systems.laptop_count(name)}  "
          f"summary={fake_systems.summary()}")


async def cmd_resume(name):
    ss = _ss()
    runner = Runner(app=app, session_service=ss)
    sid = f"s-{name}"
    stage, inv = await _peek(ss, sid)
    print(f"[resume] re-drive unfinished invocation={inv}  (stage before={stage})")
    await _drive(runner, sid, invocation_id=inv)
    stage, _ = await _peek(ss, sid)
    print(f"[resume] stage={stage}  laptops={fake_systems.laptop_count(name)}")


async def cmd_status(name):
    ss = _ss()
    stage, inv = await _peek(ss, f"s-{name}")
    print(f"[status] {name}: stage={stage}  laptops={fake_systems.laptop_count(name)}  "
          f"summary={fake_systems.summary()}")


def main():
    cmd = sys.argv[1]
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
