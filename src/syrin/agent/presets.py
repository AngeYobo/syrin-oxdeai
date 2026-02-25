"""Agent presets — preconfigured agents for common use cases.

Usage:
    >>> from syrin import Agent
    >>> agent = Agent.presets.research()
    >>> agent = Agent.presets.assistant()
    >>> agent = Agent.presets.code_helper()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.model import Model


def research() -> Agent:
    """Create an agent preset for research-style workflows.

    - REACT loop (tool use)
    - Run budget: $0.50
    - Memory: core + episodic
    - Higher tool iterations (15) for multi-step reasoning

    Example:
        >>> agent = Agent.presets.research()
        >>> agent.response("Summarize the latest papers on RAG")
    """
    from syrin import Agent, Budget
    from syrin.enums import LoopStrategy, MemoryType
    from syrin.memory import Memory

    return Agent(
        model=_default_model(),
        system_prompt="You are a research assistant. Use tools to search and cite sources. Be thorough and accurate.",
        budget=Budget(run=0.50),
        memory=Memory(types=[MemoryType.CORE, MemoryType.EPISODIC], top_k=15),
        loop_strategy=LoopStrategy.REACT,
        max_tool_iterations=15,
    )


def assistant() -> Agent:
    """Create an agent preset for conversational assistants.

    - REACT loop
    - Run budget: $0.25
    - Memory: core + episodic
    - Conversational system prompt

    Example:
        >>> agent = Agent.presets.assistant()
        >>> agent.response("What can you help me with?")
    """
    from syrin import Agent, Budget
    from syrin.enums import LoopStrategy, MemoryType
    from syrin.memory import Memory

    return Agent(
        model=_default_model(),
        system_prompt="You are a helpful assistant. Be concise and friendly.",
        budget=Budget(run=0.25),
        memory=Memory(types=[MemoryType.CORE, MemoryType.EPISODIC], top_k=10),
        loop_strategy=LoopStrategy.REACT,
    )


def code_helper() -> Agent:
    """Create an agent preset for code-related tasks.

    - REACT loop (for running tools, executing code)
    - Run budget: $0.50
    - Memory: core + episodic
    - System prompt oriented toward code clarity

    Example:
        >>> agent = Agent.presets.code_helper()
        >>> agent.response("Refactor this function to use async")
    """
    from syrin import Agent, Budget
    from syrin.enums import LoopStrategy, MemoryType
    from syrin.memory import Memory

    return Agent(
        model=_default_model(),
        system_prompt="You are a code assistant. Provide clear, idiomatic code. Prefer standard library and minimal dependencies.",
        budget=Budget(run=0.50),
        memory=Memory(types=[MemoryType.CORE, MemoryType.EPISODIC], top_k=10),
        loop_strategy=LoopStrategy.REACT,
    )


def _default_model() -> Model:
    """Default model for presets when none is configured."""
    from syrin.model import Model

    try:
        return Model.OpenAI("gpt-4o-mini")
    except Exception:
        try:
            return Model.Anthropic("claude-3-haiku-20240307")
        except Exception:
            return Model.Ollama("llama3.2")
