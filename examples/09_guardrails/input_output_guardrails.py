"""Input/Output Guardrails Example.

Demonstrates:
- ContentFilter for blocked words
- GuardrailChain combining multiple guardrails
- Agent with guardrails= parameter

Run: python -m examples.06_guardrails.input_output_guardrails
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.enums import GuardrailStage
from syrin.guardrails import ContentFilter, GuardrailChain

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


chain = GuardrailChain(
    [
        ContentFilter(blocked_words=["spam", "scam"], name="NoSpam"),
    ]
)
result = chain.check("Hello, legitimate message", GuardrailStage.INPUT)
print(f"Clean text: passed={result.passed}")
result = chain.check("This is spam", GuardrailStage.INPUT)
print(f"Blocked text: passed={result.passed}, reason={result.reason}")

agent = Agent(
    model=almock,
    system_prompt="You are helpful.",
    guardrails=chain,
)
r = agent.response("Hello")
print(f"Agent response: {r.content[:50]}...")
