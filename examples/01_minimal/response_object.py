"""Response Object Example.

Demonstrates:
- All Response object attributes: content, raw, cost, tokens, model, duration
- Trace steps (execution log)
- Budget information (budget_remaining, budget_used)
- Structured output (result.data, result.structured)
- Boolean check

Run: python -m examples.01_minimal.response_object
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

import syrin
from examples.models.models import almock
from syrin import Agent, Budget

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 1. Basic Response attributes
result = syrin.run("What is 2+2?", model=almock)
print("1. content (main response):", repr(result.content))
print("2. raw:", repr(result.raw))
print(f"3. cost (USD): ${result.cost:.6f}")
print("4. tokens:", result.tokens.input_tokens, result.tokens.output_tokens, result.tokens.total_tokens)
print(f"5. model: {result.model}")
print(f"6. duration: {result.duration:.3f}s")
print(f"7. stop_reason: {result.stop_reason}")
print(f"8. budget_remaining: {result.budget_remaining}")
print(f"9. budget_used: {result.budget_used}")
print("10. trace (execution steps):", len(result.trace))
print(f"11. tool_calls: {result.tool_calls}")
print(f"12. bool(response): {bool(result)}")
print(f"13. response.budget: {result.budget}")

# 2. With budget
budget = Budget(run=0.10, on_exceeded=syrin.raise_on_exceeded)
result_with_budget = syrin.run("Hello!", model=almock, budget=budget)
print(f"Content: {result_with_budget.content[:60]}...")
print(f"Cost: ${result_with_budget.cost:.6f}")
print(f"Budget remaining: {result_with_budget.budget_remaining}")
print(f"Budget used: {result_with_budget.budget_used}")

# 3. With structured output
@syrin.structured
class MathResult:
    expression: str
    result: int
    verified: bool

model_with_output = syrin.Model.Almock(
    latency_seconds=0.01, output=MathResult
)
result_structured = syrin.run("What is 15 + 27?", model=model_with_output)
print(f"Content: {result_structured.content[:80]}...")
print(f"Tokens: {result_structured.tokens.total_tokens}")
print(f"Cost: ${result_structured.cost:.6f}")
print(f"result.data: {result_structured.data}")
print(f"result.structured: {result_structured.structured}")
