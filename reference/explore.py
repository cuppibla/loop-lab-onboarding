"""Phase-0 exploration: prove the LongRunningFunctionTool pause -> resume round-trip
against a durable DatabaseSessionService, and learn the exact resume API."""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

from google.adk.agents import Agent
from google.adk.tools import LongRunningFunctionTool
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types

DB = "sqlite+aiosqlite:///./explore.db"
MODEL = "gemini-3-flash-preview"

def request_approval(reason: str) -> dict:
    """Ask a human to approve an action. Returns a pending status; the real
    decision arrives later."""
    print(f"    [tool] request_approval called, reason={reason!r} -> pending")
    return {"status": "pending", "message": "waiting for human approval"}

approval_tool = LongRunningFunctionTool(request_approval)

agent = Agent(
    name="app",
    model=MODEL,
    instruction=(
        "You grant access. When the user asks to grant access, call "
        "request_approval EXACTLY ONCE with a short reason. Do not call it again "
        "while pending. When you later receive an approval result with approved=true, "
        "reply exactly 'ACCESS GRANTED'. If approved=false reply 'DENIED'."
    ),
    tools=[approval_tool],
)

app = App(name="app", root_agent=agent,
          resumability_config=ResumabilityConfig(is_resumable=True))

async def dump(gen, label):
    """Iterate a run, print events, capture any long-running pending call."""
    pending = None
    async for ev in gen:
        fcs = ev.get_function_calls() if hasattr(ev, "get_function_calls") else []
        print(f"  [{label}] author={ev.author} lrt_ids={ev.long_running_tool_ids} "
              f"fcs={[(f.name, f.id) for f in fcs]} "
              f"final={ev.is_final_response()} "
              f"text={(ev.content.parts[0].text if ev.content and ev.content.parts and ev.content.parts[0].text else '')!r}")
        if ev.long_running_tool_ids:
            for f in fcs:
                if f.id in ev.long_running_tool_ids:
                    pending = (f.id, f.name)
    return pending

async def main():
    if os.path.exists("explore.db"):
        os.remove("explore.db")
    ss = DatabaseSessionService(db_url=DB)
    runner = Runner(app=app, session_service=ss)
    await ss.create_session(app_name="app", user_id="u", session_id="s1")

    print("== RUN 1: kick off; expect pause at request_approval ==")
    g = runner.run_async(user_id="u", session_id="s1",
        new_message=types.Content(role="user",
            parts=[types.Part(text="Grant Alice access to the prod database.")]))
    pending = await dump(g, "run1")
    print("  -> pending long-running call:", pending)

    print("== simulate a FRESH process: new session_service + runner on same DB ==")
    ss2 = DatabaseSessionService(db_url=DB)
    runner2 = Runner(app=app, session_service=ss2)
    sess = await ss2.get_session(app_name="app", user_id="u", session_id="s1")
    print("  reloaded session events:", len(sess.events),
          "| state:", dict(sess.state))

    print("== RUN 2: resume by sending a function_response for the pending call ==")
    fid, fname = pending
    resume = types.Content(role="user", parts=[types.Part(
        function_response=types.FunctionResponse(
            id=fid, name=fname, response={"approved": True}))])
    g2 = runner2.run_async(user_id="u", session_id="s1", new_message=resume)
    await dump(g2, "run2")

if __name__ == "__main__":
    asyncio.run(main())
