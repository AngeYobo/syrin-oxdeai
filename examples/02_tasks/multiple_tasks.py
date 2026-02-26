"""Multiple Tasks Example — Writer with research + write tasks.

Demonstrates:
- Agent with multiple @syrin.task methods
- Chaining tasks: research then write
- Named entry points for different capabilities

Run: python -m examples.02_tasks.multiple_tasks
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, task

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Writer(Agent):
    """Agent with research and write tasks. Uses @syrin.task for named APIs."""

    model = almock
    system_prompt = "You are a professional writer. Research thoroughly and write clearly."

    @task
    def research(self, topic: str) -> str:
        """Research a topic and return key points."""
        r = self.response(f"Research {topic}. List 3–5 key points.")
        return r.content or ""

    @task
    def write(self, topic: str, style: str = "professional") -> str:
        """Write about a topic in the given style."""
        r = self.response(f"Write a short paragraph about {topic} in a {style} style.")
        return r.content or ""


writer = Writer()
topic = "renewable energy"
research = writer.research(topic)
print(f"Research ({topic}): {research[:100]}...")
article = writer.write(topic, style="concise")
print(f"Article: {article[:150]}...")
