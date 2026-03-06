# Handoff & Spawn

Transfer control to another agent or create sub-agents for subtasks. Handoff is ideal for routing to specialists (e.g. triage → billing agent); spawn is for sub-tasks with isolated or shared budget.

---

## handoff()

Transfer control to another agent. Optional context (memories) and budget transfer.

### How handoff works

1. **HANDOFF_START** is emitted — before-handlers can validate or block.
2. Target agent is instantiated.
3. If `transfer_budget=True`, target shares source’s budget.
4. If `transfer_context=True`, persistent memories are copied to target.
5. Target runs `target.response(task)`.
6. **HANDOFF_END** is emitted with cost, duration, and `response_preview`.
7. Target’s `Response` is returned.

### Basic usage

```python
from syrin import Agent

class Researcher(Agent):
    model = model
    system_prompt = "You research topics."

class Writer(Agent):
    model = model
    system_prompt = "You write articles."

researcher = Researcher()
response = researcher.handoff(
    Writer,
    "Write an article based on your research",
    transfer_context=True,
    transfer_budget=False,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_agent` | `type[Agent]` | — | Target agent class (not an instance) |
| `task` | `str` | — | Task/query for the target |
| `transfer_context` | `bool` | `True` | Copy persistent memories to target |
| `transfer_budget` | `bool` | `False` | Share remaining budget with target |

**Returns:** `Response[str]`

### Validation

- `target_agent` must be an `Agent` class (not `None` or an instance). Raises `ValidationError` otherwise.
- `task` must be a non-empty string. `None`, `""`, or whitespace-only raise `ValidationError`.

### Handoff hooks

| Hook | When | Context fields |
|------|------|----------------|
| **HANDOFF_START** | Before transfer | `source_agent`, `target_agent`, `task`, `mem_count`, `transfer_context`, `transfer_budget`, `handoff_context` |
| **HANDOFF_END** | After target completes | `source_agent`, `target_agent`, `task`, `cost`, `duration`, `response_preview` |
| **HANDOFF_BLOCKED** | When blocked by before-handler | `source_agent`, `target_agent`, `task`, `reason`, `handoff_context` |

- **handoff_context:** A `ContextSnapshot` of the source agent's context at handoff time. Use it to see token counts, breakdown, `context_rot_risk`, and provenance. If the source never ran `response()` yet, the snapshot has `total_tokens=0`. For JSON export use `ctx["handoff_context"].to_dict()`.
- **response_preview:** First ~200 chars of target's response; use to debug handoff output without inspecting the full response.

### Context visibility at handoff

Handlers for **HANDOFF_START** and **HANDOFF_BLOCKED** receive `handoff_context`, a point-in-time view of the source agent's context (messages, tokens, rot risk). Use it for logging, audit, or to decide whether to block handoff when context is too large or in a rot-risk state.

**When is handoff_context populated?**

- **Empty snapshot:** If the source agent has never run `response()` before the handoff, no context has been prepared for it. In that case `handoff_context` is still a `ContextSnapshot`, but with `total_tokens=0`, `utilization_pct=0`, and breakdown (system, tools, memory, messages) all zero. This is expected when the first thing the source does is hand off.
- **Populated snapshot:** After the source has run `response()` at least once, the context manager has a last-prepared state. At the next handoff, `handoff_context` reflects that state: non-zero `total_tokens`, breakdown (e.g. `system_tokens`, `messages_tokens`), and `context_rot_risk` from utilization. Use this to see exactly what was in the source's context window when it handed off.

**transfer_context and memory:** `transfer_context=True` (default) copies the source's **persistent memories** (from `Memory`) to the target. If the source has no memory backend (`memory=None`), nothing is transferred and a warning is logged. To avoid the warning when you are not using memory, pass `transfer_context=False` (e.g. when the demo only needs context visibility in the snapshot, not memory transfer).

### Blocking handoff

Register a before-handler and raise `HandoffBlockedError` to abort:

```python
from syrin import Agent, HandoffBlockedError, Hook

def block_invalid(ctx):
    if "forbidden" in (ctx.task or "").lower():
        raise HandoffBlockedError(
            "Task contains forbidden keyword",
            ctx.source_agent,
            ctx.target_agent,
            ctx.task,
        )

agent.events.before(Hook.HANDOFF_START, block_invalid)
```

On block, **HANDOFF_BLOCKED** is emitted and the exception propagates.

### Retry on invalid data

If the target detects bad or incompatible input, it can raise `HandoffRetryRequested`. The caller catches it and retries with corrected data:

```python
from syrin import HandoffRetryRequested

try:
    result = source.handoff(TargetAgent, task)
except HandoffRetryRequested as e:
    # Reformat task using e.format_hint and retry
    task = reformat(task, e.format_hint)
    result = source.handoff(TargetAgent, task)
```

### Exceptions

| Exception | When |
|-----------|------|
| `ValidationError` | `task` is `None`, empty, or whitespace; or `target_agent` is invalid |
| `HandoffBlockedError` | A before-handler raises it to block handoff |
| `HandoffRetryRequested` | Target signals invalid data; caller should retry with `format_hint` |

**HandoffBlockedError** attributes: `message`, `source_agent`, `target_agent`, `task`.

**HandoffRetryRequested** attributes: `message`, `format_hint` (instructions for correct format).

### See also

- [Events & Hooks](events-hooks.md) — Hook registration and context
- [Agent API Reference](api-reference.md) — Method signatures and exceptions
- [Context](../context.md) — Snapshot, breakdown, and handoff/spawn context visibility
- `examples/07_multi_agent/handoff_intercept.py` — Observability, blocking, retry
- `examples/07_multi_agent/handoff_spawn_context_visibility.py` — handoff_context and spawn metadata in hooks

---

## spawn()

Create a sub-agent to run a task or return an agent for manual use. Budget can be inherited (shared) or pocket money.

### How spawn works

1. **SPAWN_START** is emitted before child creation.
2. Child is instantiated with optional budget (pocket money or shared).
3. If `task` is given: child runs `child.response(task)`, **SPAWN_END** is emitted, and the response is returned.
4. If `task` is `None`: child agent is returned; **SPAWN_END** is not emitted.

### Basic usage

```python
from syrin import Agent, Budget

child_response = parent.spawn(
    ChildAgent,
    task="Research topic X",
    budget=Budget(run=0.10),
    max_children=5,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_class` | `type[Agent]` | — | Sub-agent class |
| `task` | `str \| None` | `None` | Task to run immediately |
| `budget` | `Budget \| None` | `None` | Pocket money or shared |
| `max_children` | `int \| None` | `None` | Max concurrent children for this call; overrides instance default |

**Returns:** `Agent` if `task` is `None`, else `Response[str]`

You can set the default cap at construction: `Agent(..., max_children=5)`. The spawn limit is then 5 unless you pass `max_children=N` to `spawn()` for that call.

### Budget inheritance

- **Shared budget** (`budget.shared=True`): Child uses parent budget; spend is deducted from parent.
- **Pocket money**: Child gets own budget; must be ≤ parent’s remaining.
- **No budget**: Child runs without budget (parent may still have budget).

### Validation

- Child budget cannot exceed parent’s remaining when parent has budget.
- **max_children** limit is enforced: if you spawn more than the cap (without completing tasks that decrement the count), the next spawn raises `RuntimeError`. Set the cap via `Agent(..., max_children=N)` or per call with `spawn(..., max_children=N)`. Default cap is 10.

```python
parent = ParentAgent(budget=Budget(run=1.0, shared=True))
response = parent.spawn(ChildAgent, task="...")  # Child uses parent budget
```

### Spawn hooks

| Hook | When | Context fields |
|------|------|----------------|
| **SPAWN_START** | Before child creation | `source_agent`, `child_agent`, `child_task`, `child_budget`, `context_inherited`, `initial_context_tokens`, `parent_context_tokens` |
| **SPAWN_END** | After child completes (only when `task` given) | `source_agent`, `child_agent`, `child_task`, `cost`, `duration` |

- **context_inherited:** Whether the child received parent context (currently always `False`; reserved for future context-inheritance features).
- **initial_context_tokens:** Child's context token count at spawn time; `0` because the child has not run `response()` yet.
- **parent_context_tokens:** Parent's context token count at spawn time (from the parent's last context snapshot). Use for visibility into how large the parent's context was when it spawned.

**When is spawn context metadata populated?**

- **parent_context_tokens = 0:** If the parent has never run `response()` before the spawn, it has no last-prepared context, so `parent_context_tokens` is 0. After the parent has run `response()` at least once, the next spawn reports the parent's last snapshot size (e.g. 28 or 29 tokens from that prepare).
- **Child does not receive parent conversation:** With `context_inherited=False` (current behaviour), the child only receives the **task string** you pass to `spawn(..., task="...")`. The child does not see the parent's message history or prior turns. So if the parent asked "What is 2+2?" and then spawns with `task="Repeat that number"`, the child has no access to "4" — it only sees the literal task. Give the child a self-contained task (e.g. "Reply with the number 4") when the child must produce an answer without parent context.

---

## spawn_parallel()

Run multiple sub-agents via `spawn()`, one per task. Runs sequentially to respect parent budget and `max_children`. Emits **SPAWN_START** and **SPAWN_END** per child.

```python
results = parent.spawn_parallel([
    (Researcher, "Research A"),
    (Analyst, "Analyze B"),
    (Writer, "Write C"),
])
# results: list[Response[str]]
```

**Note:** Uses sequential execution (not parallel) to avoid event-loop conflicts with sync `response()` in threaded/async environments. For true parallelism, use `asyncio` with `agent.arun()` directly.
