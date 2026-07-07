"""L2 — human in the loop. request_access becomes a LongRunningFunctionTool: it
returns a *pending* status and the run ENDS, handing control back to the driver.
A manager approves later and the driver resumes the run. Killing the process
while it waits loses nothing — the pending call is in the durable session.
"""
import fake_systems
from google.adk.agents import Agent
from google.adk.apps.app import App
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
    """Order a laptop for the new hire."""
    oid = fake_systems.order_laptop(employee)
    tool_context.state["stage"] = "LAPTOP_ORDERED"
    return {"status": "ok", "order_id": oid}


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

app = App(name="onboarding", root_agent=root_agent)
