"""BroadcastBus — topic-based publish-subscribe bus for in-swarm communication."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch

from syrin.enums import Hook
from syrin.swarm._agent_ref import AgentRef, _aid

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class BroadcastEvent:
    """A delivered broadcast message.

    Attributes:
        sender_id: Agent ID that sent the broadcast.
        topic: Topic string the message was published on.
        payload: Arbitrary payload dict attached to the broadcast.
    """

    sender_id: str
    topic: str
    payload: dict[str, object]


@dataclass
class BroadcastConfig:
    """Configuration for the broadcast pub-sub system.

    Attributes:
        max_payload_bytes: Maximum serialised payload size in bytes.
            ``0`` means unlimited.
        max_pending_per_agent: Maximum number of pending messages queued per
            subscriber agent.  When the queue is full the oldest message is
            dropped (FIFO eviction).  ``0`` means unlimited.
    """

    max_payload_bytes: int = 0
    max_pending_per_agent: int = 0


class BroadcastPayloadTooLarge(Exception):
    """Raised when a broadcast payload exceeds the configured size limit.

    Attributes:
        size_bytes: Actual serialised size.
        max_bytes: Configured limit.
    """

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        """Initialise BroadcastPayloadTooLarge.

        Args:
            size_bytes: Actual payload size in bytes.
            max_bytes: Configured maximum.
        """
        super().__init__(
            f"Broadcast payload is {size_bytes} bytes, exceeds limit of {max_bytes} bytes"
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


# ---------------------------------------------------------------------------
# Internal subscription record
# ---------------------------------------------------------------------------


@dataclass
class _Subscription:
    """Internal record of a single pub-sub subscription.

    Attributes:
        agent_id: Subscriber agent ID.
        pattern: Topic pattern (may include glob wildcards).
        handler: Callable invoked when a matching message arrives.
    """

    agent_id: str
    pattern: str
    handler: Callable[[BroadcastEvent], None]


# ---------------------------------------------------------------------------
# BroadcastBus
# ---------------------------------------------------------------------------


class BroadcastBus:
    """Topic-based publish-subscribe bus for in-swarm agent communication.

    Distinct from A2A direct messaging: broadcast is topic-based pub-sub
    (one sender, many receivers); A2A is point-to-point.

    Wildcard patterns use :func:`fnmatch.fnmatch` semantics:

    - ``"research.*"`` matches ``"research.done"`` and ``"research.error"``.
    - ``"*"`` matches every topic.

    Example::

        bus = BroadcastBus(config=BroadcastConfig(max_payload_bytes=1024))

        bus.subscribe("agent_b", "research.*", on_research_event)
        await bus.broadcast("agent_a", "research.done", {"summary": "..."})
    """

    def __init__(
        self,
        config: BroadcastConfig | None = None,
        fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> None:
        """Initialise BroadcastBus.

        Args:
            config: Optional :class:`BroadcastConfig`; defaults to unlimited.
            fire_event_fn: Optional hook emitter for lifecycle events.
        """
        self._config: BroadcastConfig = config or BroadcastConfig()
        self._fire: Callable[[Hook, dict[str, object]], None] = fire_event_fn or (
            lambda _h, _d: None
        )
        self._subscriptions: list[_Subscription] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(
        self,
        agent_id: AgentRef | str,
        topic: str,
        handler: Callable[[BroadcastEvent], None],
    ) -> None:
        """Register *handler* to receive messages matching *topic*.

        Args:
            agent_id: Subscribing agent instance or agent ID string.
            topic: Exact topic or glob pattern (e.g. ``"research.*"``).
            handler: Callable invoked with a :class:`BroadcastEvent` on match.

        Example:
            bus = BroadcastBus()

            def on_done(event: BroadcastEvent) -> None:
                print(f"Got {event.topic}: {event.payload}")

            bus.subscribe("writer", "research.*", on_done)
        """
        self._subscriptions.append(
            _Subscription(agent_id=_aid(agent_id), pattern=topic, handler=handler)
        )

    async def broadcast(
        self,
        sender: AgentRef | str,
        topic: str,
        payload: dict[str, object],
    ) -> int:
        """Broadcast *payload* to all subscribers matching *topic*.

        Args:
            sender: Sending agent instance or agent ID string.
            topic: Topic string to publish on.
            payload: Arbitrary dict payload.

        Returns:
            Number of matching subscribers that received the message.

        Raises:
            BroadcastPayloadTooLarge: If the serialised payload exceeds
                :attr:`BroadcastConfig.max_payload_bytes`.
        """
        # Payload size check
        if self._config.max_payload_bytes > 0:
            payload_bytes = len(json.dumps(payload).encode("utf-8"))
            if payload_bytes > self._config.max_payload_bytes:
                raise BroadcastPayloadTooLarge(payload_bytes, self._config.max_payload_bytes)

        # Find matching subscriptions
        matching = [sub for sub in self._subscriptions if fnmatch(topic, sub.pattern)]

        subscriber_count = len(matching)

        # Compute payload size for hook (even if no limit check was needed)
        payload_size = len(json.dumps(payload).encode("utf-8"))

        # Deliver to all matching handlers
        sender_id = _aid(sender)
        event = BroadcastEvent(sender_id=sender_id, topic=topic, payload=payload)
        for sub in matching:
            sub.handler(event)

        # Fire lifecycle hook
        self._fire(
            Hook.AGENT_BROADCAST,
            {
                "sender_id": sender_id,
                "topic": topic,
                "payload_size": payload_size,
                "subscriber_count": subscriber_count,
            },
        )

        return subscriber_count
