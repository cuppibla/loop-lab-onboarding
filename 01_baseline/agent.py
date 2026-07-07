"""L0 — baseline onboarding agent.

One process, no persistence, no human pause. request_access auto-approves so the
5 steps run end to end. Kill it mid-run and everything is lost — that's the
motivation for L1.
"""
import fake_systems
from google.adk.agents import Agent

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


def create_account(employee: str) -> dict:
    """Create the new hire's accounts."""
    fake_systems.create_account(employee)
    return {"status": "ok"}


def order_laptop(employee: str) -> dict:
    """Order a laptop for the new hire."""
    return {"status": "ok", "order_id": fake_systems.order_laptop(employee)}


def request_access(employee: str, system: str) -> dict:
    """Request access. L0 has no human in the loop yet, so auto-approve."""
    return {"status": "approved"}


def grant_access(employee: str, system: str) -> dict:
    """Grant the access."""
    fake_systems.grant_access(employee, system)
    return {"status": "ok"}


def send_welcome(employee: str) -> dict:
    """Send the welcome note."""
    fake_systems.welcome(employee)
    return {"status": "ok"}


root_agent = Agent(
    name="onboarding",
    model=MODEL,
    instruction=INSTRUCTION,
    tools=[create_account, order_laptop, request_access, grant_access, send_welcome],
)
