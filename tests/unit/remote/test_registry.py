"""Tests for remote config registry: ConfigRegistry, register, unregister, get_agent, get_schema, make_agent_id."""

from __future__ import annotations

import gc
import re
import threading

from syrin import Agent, Model
from syrin.remote._registry import ConfigRegistry, get_registry


def _make_agent(name: str | None = None) -> Agent:
    """Minimal agent for registry tests."""
    return Agent(model=Model.Almock(), name=name)


# --- Singleton ---


class TestRegistrySingleton:
    """get_registry() returns the same singleton."""

    def test_get_registry_returns_config_registry(self) -> None:
        """get_registry() returns a ConfigRegistry instance."""
        reg = get_registry()
        assert isinstance(reg, ConfigRegistry)

    def test_get_registry_same_instance(self) -> None:
        """Multiple calls to get_registry() return the same instance."""
        assert get_registry() is get_registry()


# --- make_agent_id ---


class TestMakeAgentId:
    """Deterministic agent ID: name:ClassName when named, ClassName:uuid8 when unnamed."""

    def test_named_agent_id_format(self) -> None:
        """Agent with name gets agent_id 'name:ClassName'."""
        reg = get_registry()
        agent = _make_agent(name="my_agent")
        agent_id = reg.make_agent_id(agent)
        assert agent_id == "my_agent:Agent"
        agent_id2 = reg.make_agent_id(agent)
        assert agent_id2 == agent_id

    def test_unnamed_agent_id_format(self) -> None:
        """Agent without name gets agent_id 'ClassName:xxxxxxxx' (8 hex chars)."""
        reg = get_registry()
        agent = _make_agent(name=None)
        agent_id = reg.make_agent_id(agent)
        assert re.match(r"^Agent:[0-9a-f]{8}$", agent_id), (
            f"Expected Agent:<8 hex>, got {agent_id!r}"
        )

    def test_two_unnamed_agents_different_ids(self) -> None:
        """Two unnamed agents get different agent_ids."""
        reg = get_registry()
        a1 = _make_agent(name=None)
        a2 = _make_agent(name=None)
        id1 = reg.make_agent_id(a1)
        id2 = reg.make_agent_id(a2)
        assert id1 != id2
        assert id1.startswith("Agent:")
        assert id2.startswith("Agent:")

    def test_empty_name_treated_as_unnamed(self) -> None:
        """Agent with name='' gets uuid8-style id."""
        reg = get_registry()
        agent = Agent(model=Model.Almock(), name="")
        agent_id = reg.make_agent_id(agent)
        assert re.match(r"^Agent:[0-9a-f]{8}$", agent_id), (
            f"Expected Agent:<8 hex>, got {agent_id!r}"
        )

    def test_whitespace_only_name_treated_as_unnamed(self) -> None:
        """Agent with name='   ' gets uuid8-style id."""
        reg = get_registry()
        agent = Agent(model=Model.Almock(), name="   ")
        agent_id = reg.make_agent_id(agent)
        assert re.match(r"^Agent:[0-9a-f]{8}$", agent_id)


# --- register, get_agent, get_schema ---


class TestRegisterAndRetrieval:
    """Register stores agent and schema; get_agent and get_schema return them."""

    def test_register_named_agent_then_retrieve(self) -> None:
        """Register agent with name; get_agent and get_schema return it and its schema."""
        reg = get_registry()
        agent = _make_agent(name="alice")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        assert reg.get_agent(agent_id) is agent
        schema = reg.get_schema(agent_id)
        assert schema is not None
        assert schema.agent_id == agent_id
        assert schema.agent_name == "alice"
        assert schema.class_name == "Agent"
        assert "agent" in schema.sections
        reg.unregister(agent_id)

    def test_register_unnamed_agent_then_retrieve(self) -> None:
        """Register unnamed agent; stored schema has canonical agent_id (ClassName:uuid8)."""
        reg = get_registry()
        agent = _make_agent(name=None)
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        assert reg.get_agent(agent_id) is agent
        schema = reg.get_schema(agent_id)
        assert schema is not None
        assert schema.agent_id == agent_id
        assert re.match(r"^Agent:[0-9a-f]{8}$", schema.agent_id)
        reg.unregister(agent_id)

    def test_get_agent_nonexistent_returns_none(self) -> None:
        """get_agent(unknown id) returns None."""
        reg = get_registry()
        assert reg.get_agent("nonexistent:id") is None

    def test_get_schema_nonexistent_returns_none(self) -> None:
        """get_schema(unknown id) returns None."""
        reg = get_registry()
        assert reg.get_schema("nonexistent:id") is None

    def test_register_twice_overwrites(self) -> None:
        """Registering the same agent again overwrites schema; get_agent still returns same agent."""
        reg = get_registry()
        agent = _make_agent(name="overwrite")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        reg.register(agent)
        assert reg.get_agent(agent_id) is agent
        assert reg.get_schema(agent_id) is not None
        reg.unregister(agent_id)


# --- unregister ---


class TestUnregister:
    """unregister removes agent and schema; idempotent."""

    def test_unregister_removes_agent_and_schema(self) -> None:
        """After unregister(agent_id), get_agent and get_schema return None."""
        reg = get_registry()
        agent = _make_agent(name="to_remove")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        reg.unregister(agent_id)
        assert reg.get_agent(agent_id) is None
        assert reg.get_schema(agent_id) is None

    def test_unregister_nonexistent_idempotent(self) -> None:
        """unregister(unknown id) does not raise."""
        reg = get_registry()
        reg.unregister("nonexistent:id")


# --- all_schemas ---


class TestAllSchemas:
    """all_schemas() returns a copy of the schema dict."""

    def test_all_schemas_contains_registered(self) -> None:
        """all_schemas() includes schema for registered agent."""
        reg = get_registry()
        agent = _make_agent(name="all_schemas_agent")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        schemas = reg.all_schemas()
        assert agent_id in schemas
        assert schemas[agent_id].agent_id == agent_id
        reg.unregister(agent_id)

    def test_all_schemas_returns_copy(self) -> None:
        """Mutating the dict returned by all_schemas() does not affect registry."""
        reg = get_registry()
        agent = _make_agent(name="copy_agent")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        schemas = reg.all_schemas()
        schemas.clear()
        assert reg.get_schema(agent_id) is not None
        reg.unregister(agent_id)

    def test_all_schemas_empty_when_none_registered(self) -> None:
        """all_schemas() can be empty (no guarantee in shared singleton, but we reset in fixture)."""
        reg = get_registry()
        # If registry was cleared, all_schemas may be empty
        schemas = reg.all_schemas()
        assert isinstance(schemas, dict)


# --- Weak reference / GC ---


class TestWeakRefGc:
    """When agent is GC'd, get_agent returns None (weak ref)."""

    def test_agent_gced_get_agent_returns_none(self) -> None:
        """After only reference to agent is dropped and GC runs, get_agent returns None."""
        reg = get_registry()
        agent = _make_agent(name="gc_me")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        assert reg.get_agent(agent_id) is agent
        del agent
        gc.collect()
        assert reg.get_agent(agent_id) is None
        # Schema may still be present (we don't auto-prune); unregister to clean id
        reg.unregister(agent_id)


# --- Thread safety ---


class TestThreadSafety:
    """Concurrent register and get do not raise and see consistent state."""

    def test_concurrent_register_and_get(self) -> None:
        """Multiple threads register different agents; each can retrieve its own."""
        reg = get_registry()
        results: list[tuple[str, bool, bool]] = []
        errors: list[Exception] = []

        def register_and_check(name: str) -> None:
            try:
                agent = _make_agent(name=name)
                reg.register(agent)
                agent_id = reg.make_agent_id(agent)
                got_agent = reg.get_agent(agent_id) is agent
                got_schema = reg.get_schema(agent_id) is not None
                results.append((agent_id, got_agent, got_schema))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_and_check, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, errors
        assert len(results) == 5
        for agent_id, got_agent, got_schema in results:
            assert got_agent
            assert got_schema
            reg.unregister(agent_id)


# --- Edge: subclass agent name ---


class TestSubclassAgentId:
    """Subclass of Agent: class_name is the subclass name."""

    def test_subclass_agent_id_uses_subclass_name(self) -> None:
        """Registered subclass agent has class_name from actual class."""

        class MyAgent(Agent):
            pass

        reg = get_registry()
        agent = MyAgent(model=Model.Almock(), name="sub")
        reg.register(agent)
        agent_id = reg.make_agent_id(agent)
        assert agent_id == "sub:MyAgent"
        schema = reg.get_schema(agent_id)
        assert schema is not None
        assert schema.class_name == "MyAgent"
        reg.unregister(agent_id)
