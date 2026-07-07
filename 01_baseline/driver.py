"""L0 driver — in-memory, one shot. `uv run python driver.py [Name]`"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()
os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import fake_systems
from agent import root_agent

APP = "onboarding"


async def main(name):
    fake_systems.reset()
    ss = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP, session_service=ss)
    await ss.create_session(app_name=APP, user_id="u", session_id="s")
    print(f"[start] onboarding {name} (in memory, no persistence)")
    async for ev in runner.run_async(
        user_id="u", session_id="s",
        new_message=types.Content(role="user", parts=[types.Part(text=f"Onboard {name}.")]),
    ):
        for f in ev.get_function_calls() or []:
            print(f"    -> {f.name}({dict(f.args)})")
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if p.text and p.text.strip():
                    print(f"    <agent> {p.text.strip()}")
    print(f"[done] {fake_systems.summary()}  (all in RAM — kill mid-run and it's gone)")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "Alice"))
