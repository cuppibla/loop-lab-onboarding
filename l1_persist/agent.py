"""L1 — persistence. Same 5-step flow, but every step writes an explicit
`state["stage"]` and the driver stores the session in a database. Now progress
survives the process... but it can't yet be *resumed* (that's L2/L3).
"""
import fake_systems
from google.adk.agents import Agent
from google.adk.tools import ToolContext

MODEL = "gemini-3-flash-preview"

INSTRUCTION = (
    "You onboard a new hire. Given a NAME, perform these steps IN ORDER, one tool "
    "call at a time, and never skip or repeat a step:\n"
    "1. create_account(employee=NAME)\n"
    "2. order_laptop(employee=NAME)\n"
    "3. request_access(employee=NAME, system='prod')\n"
    "4. When access is approved, grant_access(employee=NAME, system='prod')\n"
    "5. send_welcome(employee=NAME)\n"
    "Then reply exactly 'ONBOARDING COMPLETE'."
)


def create_account(employee: str, tool_context: ToolContext) -> dict:
    """Create the new hire's accounts."""
    fake_systems.create_account(employee)
    tool_context.state["stage"] = "ACCOUNT_CREATED"
    return {"status": "ok"}


def order_laptop(employee: str, tool_context: ToolContext) -> dict:
    """Order a laptop for the new hire."""
    oid = fake_systems.order_laptop(employee)
    tool_context.state["stage"] = "LAPTOP_ORDERED"
    return {"status": "ok", "order_id": oid}


def request_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Request access. L1 still auto-approves (human pause arrives in L2)."""
    tool_context.state["stage"] = "ACCESS_APPROVED"
    return {"status": "approved"}


def grant_access(employee: str, system: str, tool_context: ToolContext) -> dict:
    """Grant the access."""
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
    tools=[create_account, order_laptop, request_access, grant_access, send_welcome],
)
