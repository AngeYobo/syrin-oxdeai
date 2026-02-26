"""Hooks Example — Agent lifecycle events.

Demonstrates:
- agent.events.on_complete(), on_response(), on_tool()
- Tracking cost across requests
- Event-driven observability

Run: python -m examples.07_observability.hooks
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


total_cost = {"value": 0.0}

def track_cost(ctx):
    total_cost["value"] += ctx.get("cost", 0)

agent = Agent(model=almock, system_prompt="You are helpful.")
agent.events.on_response(track_cost)
agent.events.on_complete(lambda ctx: print(f"  Done. Cost: ${ctx.get('cost', 0):.6f}"))
agent.response("Hello")
agent.response("How are you?")
print(f"Total cost: ${total_cost['value']:.6f}")
