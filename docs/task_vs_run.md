# Task vs Run: When to Use `agent.run()` vs `@syrin.task` Methods

## Overview

Syrin offers two ways to invoke agent behavior:

1. **`agent.run()` / `agent.response()`** — Direct LLM calls with user input
2. **`@syrin.task` methods** — Named entry points that wrap `run()` or `response()`

This guide helps you choose the right pattern.

---

## When to Use `agent.run()` / `agent.response()` Directly

**Use direct run/response when:**

- You want a simple, one-off LLM call
- You're prototyping or building minimal flows
- The user input is the primary driver (chat, Q&A, general prompts)
- You don't need a structured API surface for the agent

**Example:**

```python
agent = Agent(model=almock, system_prompt="You are helpful.")
result = agent.response("What is 2 + 2?")
print(result.content)
```

---

## When to Use `@syrin.task` Methods

**Use `@syrin.task` when:**

- You want **named, typed entry points** (e.g. `research`, `write`, `triage`)
- You're building a library or API where callers invoke specific capabilities
- You need **multiple distinct operations** on the same agent (e.g. Researcher with `research` and `summarize`)
- You want clearer semantics and better discoverability than raw prompts

**Example:**

```python
from syrin import Agent, task

class Researcher(Agent):
    model = almock
    system_prompt = "You are a research assistant."

    @task
    def research(self, topic: str) -> str:
        return self.response(f"Research: {topic}").content or ""

researcher = Researcher()
result = researcher.research.func(researcher, "AI in healthcare")
```

**Invocation:** Because `@task` returns a `TaskSpec`, call via `.func(agent, args)`:

```python
result = researcher.research.func(researcher, "AI trends")
```

---

## Comparison

| Aspect                | `agent.response("...")`        | `@syrin.task` methods               |
|-----------------------|--------------------------------|-------------------------------------|
| **Input**             | Free-form string               | Typed parameters (e.g. `topic: str`)|
| **Semantics**         | General chat/completion        | Named operation (research, write)   |
| **API surface**       | Single entry point             | Multiple named entry points         |
| **Typing**            | String in, string out          | Parameter/return types from hints   |
| **Discoverability**   | Via docstring or convention    | Via method names and TaskSpec       |
| **Use case**          | Chatbots, Q&A, general use     | Libraries, agents with roles        |

---

## Hybrid: Both Together

You can use both in the same agent:

```python
class Writer(Agent):
    model = almock
    system_prompt = "You are a writer."

    @task
    def research(self, topic: str) -> str:
        return self.response(f"Research: {topic}").content or ""

    @task
    def write(self, topic: str, style: str = "professional") -> str:
        return self.response(f"Write about {topic} in {style} style.").content or ""

writer = Writer()

# Named task
summary = writer.research.func(writer, "renewable energy")

# Or direct run for ad-hoc prompts
ad_hoc = writer.response("Rewrite that in haiku form")
```

---

## Summary

- **Direct `run`/`response`** — Best for chat-style, ad-hoc, or simple flows.
- **`@syrin.task`** — Best when you want named, typed capabilities and a clearer API.
