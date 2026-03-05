"""Remote config: full-featured agent (guardrails, prompt_vars, tools, budget) for testing overrides.

Run:
  PYTHONPATH=. python examples/12_remote_config/serve_full_features.py

Then test overrides (see TESTING_REMOTE_CONFIG.md):
  GET  /config        — schema + current values (guardrails, prompt_vars, tools, budget, agent)
  PATCH /config       — apply overrides
  POST /chat          — verify behavior (e.g. disabled tool not offered, prompt_vars in prompt)
"""

from __future__ import annotations

import os

import syrin
from syrin import Agent, Budget, Model
from syrin.guardrails.built_in import PIIScanner
from syrin.tool import tool

if os.getenv("SYRIN_API_KEY"):
    syrin.init()


@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: sunny, 72°F"


@tool
def get_time() -> str:
    """Get current time."""
    return "12:00 PM UTC"


# Agent with most remote-configurable sections for manual and automated testing
agent = Agent(
    model=Model.Almock(),
    name="full_features_agent",
    budget=Budget(run=5.0),
    system_prompt="You are a helpful assistant. Environment: {env}. Limit: {limit}.",
    tools=[get_weather, get_time],
    guardrails=[PIIScanner()],
    prompt_vars={"env": "staging", "limit": "10"},
)

if __name__ == "__main__":
    from syrin.serve.config import ServeConfig

    print("Serving at http://localhost:8000")
    print("  GET  /config        — schema + current values")
    print("  PATCH /config       — apply overrides (guardrails.*.enabled, prompt_vars.*, tools.*.enabled)")
    print("  POST /chat          — verify (e.g. after disabling a tool, it won't be used)")
    agent.serve(port=8000, config=ServeConfig(enable_discovery=True))
