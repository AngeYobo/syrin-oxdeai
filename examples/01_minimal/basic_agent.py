"""Basic Agent Example.

Demonstrates:
- Creating an Agent with a model
- Making a simple response call
- Accessing response properties (content, cost, tokens)

Run: python -m examples.01_minimal.basic_agent
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Assistant(Agent):
    model = almock
    system_prompt = "You are a helpful assistant."


assistant = Assistant()
result = assistant.response("What is 2 + 2?")
print("Question: What is 2 + 2?")
print(f"Answer: {result.content}")
print(f"Cost: ${result.cost:.6f}")
print(f"Tokens: {result.tokens.total_tokens}")
