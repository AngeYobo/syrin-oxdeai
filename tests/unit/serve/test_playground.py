"""Tests for serve.playground module."""

from __future__ import annotations

from syrin.serve.playground import (
    _attach_event_collector,
    _collect_events,
    get_playground_html,
)


def test_get_playground_html_single_agent() -> None:
    """get_playground_html returns valid HTML for single agent."""
    html = get_playground_html(
        base_path="/playground",
        api_base="",
        agents=[{"name": "test", "description": "Test agent"}],
    )
    assert "<!DOCTYPE html>" in html
    assert "Syrin Playground" in html
    assert "/stream" in html
    assert "/chat" in html
    assert "/budget" in html
    assert "Powered by Syrin" in html
    assert 'id="agent-select"' not in html


def test_get_playground_html_multi_agent() -> None:
    """get_playground_html includes agent selector for multiple agents."""
    html = get_playground_html(
        base_path="/playground",
        api_base="/agent",
        agents=[
            {"name": "a", "description": "Agent A"},
            {"name": "b", "description": "Agent B"},
        ],
    )
    assert "agent-select" in html
    assert 'value="a"' in html
    assert 'value="b"' in html


def test_get_playground_html_debug_mode() -> None:
    """get_playground_html includes observability panel when debug=True."""
    html = get_playground_html(
        base_path="/playground",
        api_base="",
        agents=[{"name": "test", "description": "Test"}],
        debug=True,
    )
    assert "observability-panel" in html
    assert "events-display" in html


def test_collect_events_context_manager() -> None:
    """_collect_events yields and returns events list."""
    with _collect_events() as events:
        assert events == []
        events.append(("hook1", {"key": "val"}))
    assert events == [("hook1", {"key": "val"})]


def test_attach_event_collector_captures_events() -> None:
    """_attach_event_collector registers handler that appends to context var."""
    from syrin.enums import Hook
    from syrin.events import EventContext, Events

    def _noop(_h: Hook, _c: EventContext) -> None:
        pass

    class MockAgent:
        events = Events(_noop)

    agent = MockAgent()

    _attach_event_collector(agent)
    with _collect_events() as events:
        # Simulate event trigger
        ctx = EventContext({"task": "test", "cost": 0.001})
        for h in [Hook.AGENT_RUN_START, Hook.AGENT_RUN_END]:
            for handler in agent.events._handlers[h]:
                handler(ctx)

    assert len(events) >= 2
    hook_names = [h for h, _ in events]
    assert "agent.run.start" in hook_names
    assert "agent.run.end" in hook_names
