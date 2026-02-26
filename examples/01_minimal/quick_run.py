"""Quick Run Example.

Demonstrates:
- syrin.run() one-liner for quick LLM calls
- syrin.configure() for global settings
- Using run() with system prompt and budget

Run: python -m examples.01_minimal.quick_run
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

import syrin
from examples.models.models import almock

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 1. Simplest usage: one-liner
print("--- 1. One-liner ---")
result = syrin.run("What is 2 + 2?", model=almock)
print(f"Answer: {result.content}")
print(f"Cost: ${result.cost:.6f}")
print(f"Tokens: {result.tokens.total_tokens}")

# 2. With system prompt
print("\n--- 2. With system prompt ---")
result = syrin.run(
    "What is Python?",
    model=almock,
    system_prompt="Explain like I'm five years old.",
)
print(f"Answer: {result.content[:80]}...")

# 3. With budget control
print("\n--- 3. With budget ---")
budget = syrin.Budget(
    run=0.10,
    on_exceeded=syrin.warn_on_exceeded,
)
result = syrin.run("Hello!", model=almock, budget=budget)
print(f"Answer: {result.content[:80]}...")
print(f"Budget used: ${result.cost:.6f}")

# 4. configure() global settings
print("\n--- 4. Global configure() ---")
syrin.configure(trace=True)
config = syrin.get_config()
print(f"Trace enabled: {config.trace}")
syrin.configure(trace=False)
print(f"Trace disabled: {config.trace}")
