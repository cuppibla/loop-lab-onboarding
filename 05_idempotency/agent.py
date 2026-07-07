"""L4 — idempotency. Same as L3, but order_laptop now guards its side effect.

Why it matters: on a crash-resume (L3), an unfinished step RE-RUNS. Without a
guard, order_laptop fires twice → two laptops. The guard checks 'did we already
order for this employee?' in an INDEPENDENT store (fake_systems, not session
state — state also rides the event log and may not be flushed in the crash window).

POC env flags:
  IDEMPOTENT=0        -> disable the guard (to SHOW the double-order bug)
  CRASH_AFTER_ORDER=1 -> order_laptop fires its side effect then hard-crashes the
                         process (simulates a crash mid-step, before it is logged)
"""
import os

import fake_systems
from google.adk.agents import Agent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools import LongRunningFunctionTool, ToolContext

MODEL = "gemini-3-flash-preview"

INSTRUCTION = (
    "You onboard a new hire. Given a NAME, perform these steps IN ORDER, one tool "
    "call at a time, and never skip or repeat a step:\n"
    "1. create_account(employee=NAME)\n"
    "2. order_laptop(employee=NAME)\n"
    "3. request_access(employee=NAME, system='prod')  # needs human approval; call ONCE\n"
    "4. When you receive an approval result with approved=true, "
    "grant_access(employee=NAME, system='prod')\n"
    "5. send_welcome(employee=NAME)\n"
    "Then reply exactly 'ONBOARDING COMPLETE'."
)


def create_account(employee: str, tool_context: ToolContext) -> dict:
    """Create the new hire's accounts."""
    fake_systems.create_account(employee)
    tool_context.state["stage"] = "ACCOUNT_CREATED"
    return {"status": "ok"}


def order_laptop(employee: str, tool_context: ToolContext) -> dict:
    """Order a laptop. Dangerous + costs money: never order twice."""
    if os.environ.get("IDEMPOTENT", "1") == "1" and fake_systems.has_laptop_order(employee):
        return {"status": "already_ordered"}          # <-- the idempotency guard
    order_id = fake_systems.order_laptop(employee)     # the real side effect
    if os.environ.get("CRASH_AFTER_ORDER") == "1":
        print("    [SIMULATED CRASH] laptop ordered; process dying before it is logged...")
        os._exit(1)                                    # hard crash, no clean shutdown
    tool_context.state["stage"] = "LAPTOP_ORDERED"
    return {"status": "ok", "order_id": order_id}


def request_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Request sensitive access — pauses for a human manager's approval."""
    tool_context.state["stage"] = "AWAITING_APPROVAL"
    return {"status": "pending", "message": f"awaiting manager approval for {system}"}


def grant_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Grant the access once approved."""
    fake_systems.grant_access(employee, system)
    tool_context.state["stage"] = "ACCESS_GRANTED"
    return {"status": "ok"}


def send_welcome(employee: str, tool_context: ToolContext) -> dict:
    """Send the welcome note."""
    fake_systems.welcome(employee)
    tool_context.state["stage"] = "DONE"
    return {"status": "ok"}


root_agent = Agent(
    name="onboarding",
    model=MODEL,
    instruction=INSTRUCTION,
    tools=[
        create_account,
        order_laptop,
        LongRunningFunctionTool(request_access),
        grant_access,
        send_welcome,
    ],
)

app = App(name="onboarding", root_agent=root_agent,
          resumability_config=ResumabilityConfig(is_resumable=True))
