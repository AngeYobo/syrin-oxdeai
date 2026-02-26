"""Tracing Example — Debug mode and manual spans.

Demonstrates:
- Agent(debug=True) for automatic tracing
- Manual span creation with syrin.observability
- Console output for trace visibility

Run: python -m examples.07_observability.tracing
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


agent = Agent(
    model=almock,
    system_prompt="You are helpful.",
    debug=True,
)
result = agent.response("What is AI?")
print(f"Response: {result.content[:80]}...")
