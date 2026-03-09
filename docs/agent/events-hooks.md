# Events & Hooks

The agent emits lifecycle **hooks** during execution. Register handlers with `agent.events` to log, monitor, or modify behavior.

## Registering Handlers

```python
from syrin import Agent, Hook

agent = Agent(model=model)

agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print(f"Input: {ctx.input}"))
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Cost: ${ctx.cost:.4f}"))
```

## Handler Types

### on(hook, handler)

Runs during the event.

```python
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.tokens}"))
```

### before(hook, handler)

Runs before the event. Can modify `EventContext`.

```python
agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({"temperature": 0.5}))
```

### after(hook, handler)

Runs after the event. Good for logging and metrics.

```python
agent.events.after(Hook.TOOL_CALL_END, lambda ctx: log_tool_usage(ctx.name, ctx.output))
```

## EventContext

Handlers receive an `EventContext` (dict-like with dot access):

```python
def on_llm_end(ctx):
    print(ctx.input)     # Dot access
    print(ctx["cost"])   # Dict access
    print(ctx.content)
    print(ctx.tokens)
```

Fields depend on the hook. Common ones: `input`, `content`, `cost`, `tokens`, `model`, `iteration`, `name` (tool), `error`.

## Convenience Methods

| Method | Hook |
|--------|------|
| `on_start(handler)` | `AGENT_RUN_START` |
| `on_complete(handler)` | `AGENT_RUN_END` |
| `on_request(handler)` | `LLM_REQUEST_START` |
| `on_response(handler)` | `LLM_REQUEST_END` |
| `on_tool(handler)` | `TOOL_CALL_END` |
| `on_error(handler)` | `TOOL_ERROR` |
| `on_budget(handler)` | `BUDGET_CHECK` |

```python
agent.events.on_start(lambda ctx: print("Started"))
agent.events.on_complete(lambda ctx: print("Done"))
```

## on_all(handler)

Register a handler for all hooks:

```python
def log_all(hook, ctx):
    print(f"[{hook.value}] {ctx}")

agent.events.on_all(log_all)
```

## All Hooks

### Agent

- `AGENT_INIT` — Agent created
- `AGENT_RUN_START` — `response()` / `arun()` started
- `AGENT_RUN_END` — Run finished
- `AGENT_RESET` — Reset called

### LLM

- `LLM_REQUEST_START` — Before provider call
- `LLM_REQUEST_END` — After provider call
- `LLM_STREAM_CHUNK` — Each streaming chunk
- `LLM_RETRY` — Retrying a failed call
- `LLM_FALLBACK` — Falling back to another model

**LLM_FALLBACK context fields:** `reason` (e.g. `circuit_breaker_open`), `from_model`, `to_model`. Emitted when the Agent uses a fallback model (e.g. circuit breaker open) or when `Model.with_fallback()` is used. Span events `llm.provider_error` and `llm.fallback` are also recorded on the LLM span for full trace visibility.

### Tools

- `TOOL_CALL_START` — Before tool execution
- `TOOL_CALL_END` — After tool execution
- `TOOL_ERROR` — Tool raised an exception

### Budget

- `BUDGET_CHECK` — Budget checked
- `BUDGET_THRESHOLD` — Threshold crossed
- `BUDGET_EXCEEDED` — Limit exceeded

### Routing (Agent with model list)

- `ROUTING_DECISION` — Model selected. Use `debug=True` or `--trace` to see routing in traces.

**Context fields:**

| Field | Description |
|-------|-------------|
| `routing_reason` | `RoutingReason` — `selected_model`, `reason`, `task_type`, `cost_estimate`, `alternatives`, `classification_confidence`, `complexity_tier`, `system_alignment_score` |
| `model` | Model ID chosen (e.g. `anthropic/claude-sonnet-4-5`) |
| `task_type` | Detected or overridden task type |
| `prompt` | User prompt (truncated to 200 chars) |

**Trace span:** When `debug=True`, a `routing.decision` span is emitted with attributes: `routing.model`, `routing.model_id`, `routing.reason`, `routing.task_type`, `routing.cost_estimate`, `routing.confidence`, `routing.alternatives`.

**Example:** Log which model was chosen and why:

```python
agent.events.on(Hook.ROUTING_DECISION, lambda ctx: print(
    f"Chosen: {ctx.routing_reason.selected_model} | {ctx.routing_reason.reason}"
))
```

### Other

- `MODEL_SWITCH` — Model changed
- `HANDOFF_START` / `HANDOFF_END` / `HANDOFF_BLOCKED` — Handoff (see below)
- `SPAWN_START` / `SPAWN_END` — Spawn (see below)

### Pipeline Hooks (static Pipeline)

- `PIPELINE_START` — Pipeline run started
- `PIPELINE_END` — Pipeline run finished
- `PIPELINE_AGENT_START` — Agent about to run
- `PIPELINE_AGENT_COMPLETE` — Agent finished

### Handoff & Spawn Hooks (context fields)

| Hook | Context fields |
|------|----------------|
| `HANDOFF_START` | `source_agent`, `target_agent`, `task`, `mem_count`, `transfer_context`, `transfer_budget` |
| `HANDOFF_END` | `source_agent`, `target_agent`, `task`, `cost`, `duration`, `response_preview` |
| `HANDOFF_BLOCKED` | `source_agent`, `target_agent`, `task`, `reason` |
| `SPAWN_START` | `source_agent`, `child_agent`, `child_task`, `child_budget` |
| `SPAWN_END` | `source_agent`, `child_agent`, `child_task`, `cost`, `duration` |

See [Handoff & Spawn](handoff-spawn.md) for full documentation, blocking (`HandoffBlockedError`), retry (`HandoffRetryRequested`), and examples.
- `GUARDRAIL_INPUT` / `GUARDRAIL_OUTPUT` / `GUARDRAIL_BLOCKED` — Guardrails
- `MEMORY_RECALL` / `MEMORY_STORE` / `MEMORY_FORGET` — Memory
- `CHECKPOINT_SAVE` / `CHECKPOINT_LOAD` — Checkpoints
- `CONTEXT_COMPRESS` / `CONTEXT_OFFLOAD` / `CONTEXT_RESTORE` — Context
- `RATELIMIT_*` — Rate limits
- `OUTPUT_VALIDATION_*` — Output validation

## Debug Mode

With `debug=True`, events are printed to the console:

```python
agent = Agent(model=model, debug=True)
```

## See Also

- [Event Bus](../event-bus.md) — Typed domain events for metrics and observability
- [Audit Logging](../audit.md) — Compliance logging via AuditLog
- [Advanced Topics: Lifecycle Hooks](../advanced-topics.md)
- [Observability](../observability.md)
