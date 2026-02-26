# Breaking Changes (v0.3.0 Chaos Stress Test Fixes)

> **Status:** Development. No backward compatibility guarantees in dev stage.
>
> These changes fix chaos stress test bugs documented in `plan/v0.3.0.md`.

## Summary

- **Agent validation** — Wrong types now raise clear `TypeError` / `ValueError` at construction or entry instead of late `AttributeError` / `ValidationError`.
- **Loop validation** — `ReactLoop(max_iterations < 1)` now raises at construction instead of `UnboundLocalError` at run.
- **Provider kwargs** — Agent now passes `Model._provider_kwargs` to `provider.complete()`, so provider-specific options (e.g. `latency_seconds`) are applied.

## Breaking Changes

### Agent construction

| Before | After |
|--------|-------|
| `Agent(model="gpt-4")` → `AttributeError` deep in provider | `TypeError: model must be Model or ModelConfig, got str` |
| `Agent(memory=Budget())` → `AttributeError` in memory call | `TypeError: memory must be Memory, ConversationMemory, False, or None, got Budget` |
| `Agent(max_tool_iterations=-1)` → `UnboundLocalError` in loop | `ValueError: max_tool_iterations must be >= 1` |
| `Agent(max_tool_iterations="10")` → `TypeError` in loop | `TypeError: max_tool_iterations must be int` |
| `Agent(system_prompt=123)` → `ValidationError` in Message | `TypeError: system_prompt must be str, got int` |
| `Agent(tools="search")` → Accepted (iterates chars) | `TypeError: tools must be list of ToolSpec or None` |
| `Agent(tools=["search"])` → Accepted | `TypeError: tools[0] must be ToolSpec, got str` |
| `Agent(tools=[None, tool])` → Accepted | `TypeError: tools must not contain None` |
| `Agent(budget=5)` → May accept | `TypeError: budget must be Budget, got int` |
| `Agent(budget="0.50")` → May accept | `TypeError: budget must be Budget, got str` |

### Agent.response() / run() / arun() / stream() / astream()

| Before | After |
|--------|-------|
| `agent.response(None)` → `ValidationError` in Message | `TypeError: user_input must be str, got NoneType` |
| `agent.response(42)` → `ValidationError` in Message | `TypeError: user_input must be str, got int` |
| `agent.response({"key": "val"})` → `ValidationError` | `TypeError: user_input must be str, got dict` |

### Loop

| Before | After |
|--------|-------|
| `ReactLoop(max_iterations=0)` → Accepted, `UnboundLocalError` at run | `ValueError: max_iterations must be int >= 1` |
| `ReactLoop(max_iterations=-1)` → Accepted, `UnboundLocalError` at run | `ValueError: max_iterations must be int >= 1` |

### Provider kwargs (Bug fix, may change behavior)

- **Before:** Agent called `provider.complete(model=_model_config)` without `_provider_kwargs`. E.g. `Model.Almock(latency_seconds=0)` was ignored when using `agent.response()`; provider used defaults.
- **After:** Agent passes `Model._provider_kwargs` to `provider.complete()`. Invalid options (e.g. `latency_seconds=0`) now raise `ValueError` at response time as intended.

## Migration

- Use `Model` or `ModelConfig` for `model`; `Memory` or `ConversationMemory` for `memory`; `Budget` for `budget`.
- Use `@syrin.tool` / `syrin.tool()` for tools; pass a list of `ToolSpec` or `None`. Import `ToolSpec` from `syrin.tool` (or `syrin`), not from `syrin.types`.
- Ensure `max_tool_iterations` is an `int` >= 1.
- Ensure `user_input` to `response()`, `arun()`, etc. is a `str`.
- Use `max_iterations >= 1` for `ReactLoop` (and equivalent for other loops).
