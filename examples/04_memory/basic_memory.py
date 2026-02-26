"""Basic Memory Example.

Demonstrates:
- Creating an agent with Memory (4-type persistent memory)
- remember() and recall() operations
- Memory types: CORE, EPISODIC, SEMANTIC, PROCEDURAL

Run: python -m examples.04_memory.basic_memory
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Memory, MemoryType

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Assistant(Agent):
    model = almock
    system_prompt = "You are a helpful assistant that remembers user preferences."


assistant = Assistant(memory=Memory())
assistant.remember("The user's name is Alice.", memory_type=MemoryType.CORE, importance=1.0)
assistant.remember("User asked about machine learning", memory_type=MemoryType.EPISODIC)
result = assistant.response("What's my name?")
print(f"Response: {result.content}")
