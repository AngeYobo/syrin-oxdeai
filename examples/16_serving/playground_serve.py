"""Playground Serving Example.

Demonstrates:
- agent.serve(enable_playground=True, debug=True)
- Visit http://localhost:8000/playground for chat UI, cost, budget, observability

Requires: uv pip install syrin[serve]

Run: python -m examples.serving.playground_serve
Visit: http://localhost:8000/playground
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Budget, RateLimit

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Assistant(Agent):
    name = "assistant"
    description = "Helpful assistant — playground demo"
    model = almock
    system_prompt = "You are a helpful assistant. Be concise."
    budget = Budget(run=0.5, per=RateLimit(hour=10, day=100, week=700))


if __name__ == "__main__":
    agent = Assistant()
    # enable_playground=True: serves GET /playground
    # debug=True: observability panel shows hook events
    agent.serve(port=8000, enable_playground=True, debug=True)
