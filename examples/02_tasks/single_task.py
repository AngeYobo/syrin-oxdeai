"""Single Task Example — @syrin.task for named entry points.

Demonstrates:
- Using @syrin.task to define a named task method
- Researcher agent with research(topic: str) task
- Invoking tasks via agent.task_name(args)

Run: python -m examples.02_tasks.single_task
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, task

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Researcher(Agent):
    """Agent that researches topics. Uses @syrin.task for a named API."""

    model = almock
    system_prompt = "You are a research assistant. Provide concise, factual summaries."

    @task
    def research(self, topic: str) -> str:
        """Research a topic and return a summary."""
        response = self.response(f"Research the following topic and summarize: {topic}")
        return response.content or ""


researcher = Researcher()
result = researcher.research("AI in healthcare")
print("Topic: AI in healthcare")
print(f"Summary: {result[:200]}...")
