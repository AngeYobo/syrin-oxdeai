"""Agent with Tools Example.

Demonstrates:
- Creating an Agent with tools
- Tool execution during response
- Multiple tools working together

Run: python -m examples.01_minimal.agent_with_tools
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, tool

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic. operation: add, subtract, multiply, divide."""
    if operation == "add":
        return str(a + b)
    if operation == "subtract":
        return str(a - b)
    if operation == "multiply":
        return str(a * b)
    if operation == "divide":
        return str(a / b) if b != 0 else "Error: division by zero"
    return "Unknown operation"


@tool
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get weather for a city. unit: celsius or fahrenheit."""
    return f"The weather in {city} is 22°{unit[0].upper()}"


class MathAssistant(Agent):
    model = almock
    system_prompt = "You are a helpful assistant. Use tools for calculations."
    tools = [calculate, get_weather]


assistant = MathAssistant()
result = assistant.response("What is 15 times 7?")
print("Question: What is 15 times 7?")
print(f"Answer: {result.content}")
print(f"Tool calls: {len(result.tool_calls)}")
