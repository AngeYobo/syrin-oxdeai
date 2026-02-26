"""Custom Model Example.

Demonstrates:
- Creating a custom Model subclass
- Overriding complete() for any LLM API
- ModelPricing for cost calculation
- with_fallback() for reliability chains
- Using Almock for testing

Run: python -m examples.13_models.custom_model
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Model

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 1. Custom Model subclass
class MyCustomModel(Model):
    """Custom model for any LLM API."""

    def complete(self, messages: list, **kwargs: object) -> object:
        print(f"  Custom complete() called with {len(messages)} messages")
        return None

model = MyCustomModel("my-model")
print(f"Custom model: {model}, provider: {model.provider}")

# 2. Almock for testing
mock_model = Model.Almock(latency_seconds=0.01, lorem_length=50)
agent = Agent(model=mock_model, system_prompt="You are helpful.")
result = agent.response("Hello!")
print(f"Response: {result.content[:60]}..., cost: ${result.cost:.6f}")

# 3. Almock with latency range
mock_model = Model.Almock(latency_min=0, latency_max=0, lorem_length=80)
agent = Agent(model=mock_model)
result = agent.response("Fast response")

# 4. Fallback chains
primary = Model.Almock(latency_seconds=0.01)
model = primary.with_fallback(Model.Almock(latency_seconds=0.01), Model.Almock(latency_seconds=0.01))
agent = Agent(model=model)
result = agent.response("Hello with fallback!")

# 5. Class-level model
class MyAgent(Agent):
    model = almock
    system_prompt = "You are a specialized assistant."

agent = MyAgent()
result = agent.response("Hello specialized!")
