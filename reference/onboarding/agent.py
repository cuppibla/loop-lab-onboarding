"""The onboarding agent: a long-running, durable, human-in-the-loop agent.

Env flags (for the POC scenarios):
  IDEMPOTENT=0   -> disable the order_laptop guard (to show the double-order bug)
  CRASH_AFTER_ORDER=1 -> order_laptop fires its side effect then HARD-CRASHES the
                         process (simulates a crash mid-step, before the step is logged)
"""
import os

from google.adk.agents import Agent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools import LongRunningFunctionTool, ToolContext

from . import fake_systems

MODEL = "gemini-3-flash-preview"


def create_account(employee: str, tool_context: ToolContext) -> dict:
    """Create the new hire's accounts (email, chat)."""
    fake_systems.create_account(employee)
    tool_context.state["stage"] = "ACCOUNT_CREATED"
    return {"status": "ok"}


def order_laptop(employee: str, tool_context: ToolContext) -> dict:
    """Order a laptop for the new hire. Dangerous + costs money: never order twice."""
    if os.environ.get("IDEMPOTENT", "1") == "1" and fake_systems.has_laptop_order(employee):
        return {"status": "already_ordered"}          # idempotency guard
    order_id = fake_systems.order_laptop(employee)     # <-- the real side effect
    if os.environ.get("CRASH_AFTER_ORDER") == "1":
        print("    [SIMULATED CRASH] laptop ordered, process dying before logging...")
        os._exit(1)                                    # hard crash: no clean shutdown
    tool_context.state["stage"] = "LAPTOP_ORDERED"
    return {"status": "ok", "order_id": order_id}


def request_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Request sensitive access. Requires a human manager's approval (long-running)."""
    tool_context.state["stage"] = "AWAITING_APPROVAL"
    return {"status": "pending", "message": f"awaiting manager approval for {system}"}


def grant_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Grant the access once approved."""
    fake_systems.grant_access(employee, system)
    tool_context.state["stage"] = "ACCESS_GRANTED"
    return {"status": "ok"}


def send_welcome(employee: str, tool_context: ToolContext) -> dict:
    """Send the welcome note. Final step."""
    fake_systems.welcome(employee)
    tool_context.state["stage"] = "DONE"
    return {"status": "ok"}


root_agent = Agent(
    name="onboarding",
    model=MODEL,
    instruction=(
        "You onboard a new hire. Given a NAME, perform these steps IN ORDER, "
        "one tool call at a time, and never skip or repeat a step:\n"
        "1. create_account(employee=NAME)\n"
        "2. order_laptop(employee=NAME)\n"
        "3. request_access(employee=NAME, system='prod')  # needs human approval; call ONCE\n"
        "4. When you receive an approval result with approved=true, "
        "grant_access(employee=NAME, system='prod')\n"
        "5. send_welcome(employee=NAME)\n"
        "Then reply exactly 'ONBOARDING COMPLETE'."
    ),
    tools=[
        create_account,
        order_laptop,
        LongRunningFunctionTool(request_access),
        grant_access,
        send_welcome,
    ],
)

app = App(
    name="onboarding",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
