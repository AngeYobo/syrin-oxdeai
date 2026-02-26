"""Recall Example — Using recall with query.

Demonstrates:
- Storing multiple memories
- recall(query=...) to retrieve relevant memories
- Listing all memories with recall()

Run: python -m examples.04_memory.recall
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Memory

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Assistant(Agent):
    model = almock
    system_prompt = "You are a helpful assistant."

assistant = Assistant(memory=Memory())
assistant.remember("User likes Python programming")
assistant.remember("User works at a startup")
assistant.remember("User prefers afternoon meetings")
results = assistant.recall(query="programming work")
print("Recall results for 'programming work':")
for r in results:
    print(f"  - {r.content[:50]}...")
