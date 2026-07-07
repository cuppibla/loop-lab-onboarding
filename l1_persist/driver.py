"""L1 driver — persists the session to SQLite. Commands: reset | start <name> | status <name>

Try: `python driver.py start Alice` then `python driver.py status Alice` — the
stage is on disk. But kill it mid-run and there's no way to *continue* yet (L2/L3).
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
from agent import root_agent

DB = "sqlite+aiosqlite:///./onboarding.db"
APP = "onboarding"


def ss():
    return DatabaseSessionService(db_url=DB)


async def cmd_start(name):
    service = ss()
    runner = Runner(agent=root_agent, app_name=APP, session_service=service)
    await service.create_session(app_name=APP, user_id="u", session_id=f"s-{name}")
    print(f"[start] onboarding {name} (persisted to {DB})")
    async for ev in runner.run_async(
        user_id="u", session_id=f"s-{name}",
        new_message=types.Content(role="user", parts=[types.Part(text=f"Onboard {name}.")]),
    ):
        for f in ev.get_function_calls() or []:
            print(f"    -> {f.name}({dict(f.args)})")
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if p.text and p.text.strip():
                    print(f"    <agent> {p.text.strip()}")
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
    asyncio.run({"start": cmd_start, "status": cmd_status}[cmd](sys.argv[2]))


if __name__ == "__main__":
    main()
