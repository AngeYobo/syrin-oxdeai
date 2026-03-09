"""Routing observability — ROUTING_DECISION hook for logging and metrics.

Log every routing decision to console, file, or metrics backend.

Run: python -m examples.17_routing.routing_observability
Run with traces: python -m examples.17_routing.routing_observability --trace
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from syrin import Agent, Hook
from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RouterConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    m1 = Model.Almock(latency_min=0, latency_max=0)
    m2 = Model.Almock(latency_min=0, latency_max=0)

    profiles = [
        ModelProfile(model=m1, name="general", strengths=[TaskType.GENERAL], priority=90),
        ModelProfile(model=m2, name="code", strengths=[TaskType.CODE], priority=100),
    ]
    router = ModelRouter(profiles=profiles, routing_mode=RoutingMode.AUTO)

    use_trace = "--trace" in sys.argv
    agent = Agent(
        model=[m1, m2],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
        debug=use_trace,
    )

    log_path = Path(__file__).parent / "routing_log.jsonl"

    def log_routing(ctx: dict) -> None:
        reason = ctx.get("routing_reason")
        record = {
            "model": ctx.get("model"),
            "task_type": ctx.get("task_type"),
            "reason": reason.reason if reason else None,
            "selected_model": reason.selected_model if reason else None,
        }
        print(f"[ROUTING] {json.dumps(record)}")
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    agent.events.on(Hook.ROUTING_DECISION, log_routing)

    agent.response("hello", task_type=TaskType.GENERAL)
    agent.response("write a function", task_type=TaskType.CODE)

    print(f"\nLogged to {log_path}")


if __name__ == "__main__":
    main()
