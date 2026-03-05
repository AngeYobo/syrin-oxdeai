"""Config registry: track live agents and their schemas. Singleton, thread-safe."""

from __future__ import annotations

import threading
import uuid
from weakref import WeakKeyDictionary, WeakValueDictionary

from syrin.agent import Agent
from syrin.remote._schema import extract_agent_schema
from syrin.remote._types import AgentSchema

_REGISTRY: ConfigRegistry | None = None


def get_registry() -> ConfigRegistry:
    """Return the global ConfigRegistry singleton. Thread-safe."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ConfigRegistry()
    return _REGISTRY


class ConfigRegistry:
    """Tracks live agents and their config schemas. Singleton via get_registry().

    Agents are stored by weak reference so they can be garbage-collected. Schema
    entries remain until unregister(agent_id) is called. Agent IDs are
    deterministic: named agents use 'name:ClassName', unnamed use 'ClassName:uuid8'.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._agents: WeakValueDictionary[str, Agent] = WeakValueDictionary()
        self._schemas: dict[str, AgentSchema] = {}
        # Unnamed agents get a stable id per instance; cache by agent identity.
        self._unnamed_ids: WeakKeyDictionary[Agent, str] = WeakKeyDictionary()

    def make_agent_id(self, agent: Agent) -> str:
        """Return deterministic agent ID: 'name:ClassName' when named, 'ClassName:uuid8' when unnamed.

        Unnamed means no explicit name or name equals class name (e.g. Agent default 'agent').
        """
        name = getattr(agent, "_agent_name", None) or getattr(agent, "name", None)
        class_name = type(agent).__name__
        name_str = str(name).strip() if name is not None else ""
        # Treat default name (class name lowercased) as unnamed so multiple agents get unique ids.
        if name_str and name_str.lower() != class_name.lower():
            return f"{name_str}:{class_name}"
        with self._lock:
            if agent in self._unnamed_ids:
                return self._unnamed_ids[agent]
            new_id = f"{class_name}:{uuid.uuid4().hex[:8]}"
            self._unnamed_ids[agent] = new_id
            return new_id

    def register(self, agent: Agent) -> AgentSchema:
        """Extract schema from agent, store agent (weak) and schema; return schema with canonical agent_id."""
        with self._lock:
            agent_id = self.make_agent_id(agent)
            schema = extract_agent_schema(agent)
            schema = schema.model_copy(update={"agent_id": agent_id})
            self._agents[agent_id] = agent
            self._schemas[agent_id] = schema
            return schema

    def unregister(self, agent_id: str) -> None:
        """Remove agent and schema for the given id. Idempotent if id unknown."""
        with self._lock:
            self._agents.pop(agent_id, None)
            self._schemas.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> Agent | None:
        """Return the live agent for the id, or None if unknown or GC'd."""
        with self._lock:
            return self._agents.get(agent_id)

    def get_schema(self, agent_id: str) -> AgentSchema | None:
        """Return the stored schema for the id, or None if unknown."""
        with self._lock:
            return self._schemas.get(agent_id)

    def all_schemas(self) -> dict[str, AgentSchema]:
        """Return a copy of all stored schemas (agent_id -> AgentSchema)."""
        with self._lock:
            return dict(self._schemas)
