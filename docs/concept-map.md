# Concept Map — Budget, Context, Memory

Quick reference to avoid confusion between similar names.

## Budget vs Token Limits

| Concept | Type | Where | Meaning |
|---------|------|-------|---------|
| **Budget** | `Budget` | `Agent.budget` | Cost limits in **USD** (run, per hour/day/month). Prevents overspend. |
| **TokenLimits** | `TokenLimits` | `Context.budget` | Token caps (run, per hour/day/month). Caps token usage. |

Both use the same field names (`run`, `per`, `on_exceeded`) for consistency, but they track different units: **Budget** = dollars, **TokenLimits** = tokens.

```python
from syrin import Agent, Budget, Context, TokenLimits, TokenRateLimit

agent = Agent(
    model=...,
    budget=Budget(run=0.50),  # USD: max $0.50 per run
    context=Context(budget=TokenLimits(run=50_000, per=TokenRateLimit(hour=100_000))),  # tokens
)
```

## Memory Types

| Concept | Type | Where | Meaning |
|---------|------|-------|---------|
| **Memory** | `Memory` | `Agent.memory` | Persistent memory config (top_k, backend, types). Enables remember/recall/forget. |
| **ConversationMemory** | `BufferMemory`, `WindowMemory` | `Agent.memory` | Session history (last N messages). Use when you only need turn-by-turn context. |

Use **Memory** for persistent recall (remember/recall/forget). Use **BufferMemory** or **WindowMemory** for simple session history.

```python
from syrin import Agent
from syrin.memory import Memory, BufferMemory

# Persistent memory (remember/recall/forget)
agent = Agent(model=..., memory=Memory(top_k=10, types=[MemoryType.CORE, MemoryType.EPISODIC]))

# Session history only (last N messages)
agent = Agent(model=..., memory=BufferMemory())
```

## Context Budget Types (Internal)

| Concept | Type | Use | Meaning |
|---------|------|-----|---------|
| **ContextWindowBudget** | Internal | During `prepare()` | max_tokens, reserve, utilization. Internal window capacity. |
| **TokenLimits** | User-facing | `Context.budget` | User-configured token caps. Same shape as Budget. |

You configure **TokenLimits** on `Context.budget`. The context manager uses it to enforce caps and builds an internal **ContextWindowBudget** for each prepare call.

## Summary

- **Budget** = USD limits on Agent
- **TokenLimits** = token caps on Context.budget
- **Memory** = persistent recall (Memory) or session history (BufferMemory/WindowMemory)
- **ContextWindowBudget** = internal; you don't construct it
