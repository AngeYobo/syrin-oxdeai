# Postman flow: Remote config (and serve) APIs

Use this with the agent served from `init_and_serve.py` (budget + agent section) or **`serve_full_features.py`** (guardrails, prompt_vars, tools, budget) for testing all override types. Base URL with default config: **`http://localhost:8000`**. If you use `ServeConfig(route_prefix="/api/v1")`, prepend that (e.g. `http://localhost:8000/api/v1`).

For a full test flow (run server → override → verify), see **`TESTING_REMOTE_CONFIG.md`**.

---

## 1. Start the server

**Minimal (budget + agent):**
```bash
PYTHONPATH=. python examples/12_remote_config/init_and_serve.py
```

**Full-featured (guardrails, prompt_vars, tools, budget) — for testing all sections:**
```bash
PYTHONPATH=. python examples/12_remote_config/serve_full_features.py
```

Server runs at `http://localhost:8000` (no route prefix by default).

---

## 2. API calls in order (Postman flow)

### Call 1: Health check (optional)

| Field | Value |
|-------|--------|
| **Method** | `GET` |
| **URL** | `{{baseUrl}}/health` |
| **When** | First, to confirm server is up. |
| **Body** | None |
| **Response** | `200` — `{"status": "ok"}` |

---

### Call 2: Get config (schema + current values) — **required before PATCH**

| Field | Value |
|-------|--------|
| **Method** | `GET` |
| **URL** | `{{baseUrl}}/config` |
| **When** | Before any PATCH; use response to get `agent_id` and see editable paths. |
| **Body** | None |
| **Response** | `200` — JSON with: |

**Response shape (GET /config):**

```json
{
  "agent_id": "my_agent:Agent",
  "agent_name": "my_agent",
  "class_name": "Agent",
  "sections": {
    "agent": {
      "section": "agent",
      "class_name": "Agent",
      "fields": [
        { "name": "max_tool_iterations", "path": "agent.max_tool_iterations", "type": "int", "default": 10, "description": null, "constraints": {}, "enum_values": null, "children": null, "remote_excluded": false },
        { "name": "debug", "path": "agent.debug", "type": "bool", "default": false, "description": null, "constraints": {}, "enum_values": null, "children": null, "remote_excluded": false },
        { "name": "loop_strategy", "path": "agent.loop_strategy", "type": "str", "default": null, "description": null, "constraints": {}, "enum_values": ["react", "plan_execute", "code_action", "single_shot"], "children": null, "remote_excluded": false },
        { "name": "system_prompt", "path": "agent.system_prompt", "type": "str", "default": "", "description": null, "constraints": {}, "enum_values": null, "children": null, "remote_excluded": false },
        { "name": "hitl_timeout", "path": "agent.hitl_timeout", "type": "int", "default": 300, "description": null, "constraints": {}, "enum_values": null, "children": null, "remote_excluded": false }
      ]
    },
    "budget": {
      "section": "budget",
      "class_name": "Budget",
      "fields": [
        { "name": "run", "path": "budget.run", "type": "float", "default": null, "description": "...", "constraints": { "ge": 0 }, "enum_values": null, "children": null, "remote_excluded": false },
        { "name": "reserve", "path": "budget.reserve", "type": "float", "default": 0, "description": null, "constraints": { "ge": 0 }, "enum_values": null, "children": null, "remote_excluded": false }
      ]
    }
  },
  "current_values": {
    "budget.run": 1.0,
    "budget.reserve": 0,
    "agent.max_tool_iterations": 10,
    "agent.debug": false,
    "agent.system_prompt": "You are a helpful assistant."
  }
}
```

**Save for next step:** Copy `agent_id` (e.g. `my_agent:Agent`) into your PATCH request.

---

### Call 3: Apply overrides (PATCH config)

| Field | Value |
|-------|--------|
| **Method** | `PATCH` |
| **URL** | `{{baseUrl}}/config` |
| **Headers** | `Content-Type: application/json` |
| **When** | After GET /config; use the same `agent_id` from the GET response. |
| **Body (raw JSON)** | See below |
| **Response** | `200` — `{ "accepted": [...], "rejected": [...], "pending_restart": [] }` |

**Body shape (PATCH /config):**

```json
{
  "agent_id": "my_agent:Agent",
  "version": 1,
  "overrides": [
    { "path": "budget.run", "value": 2.0 }
  ]
}
```

- **`agent_id`** — Must match the agent you’re serving (from GET /config). Wrong id → `400` with `agent_id mismatch`.
- **`version`** — Integer ≥ 0; use for ordering (e.g. increment after each PATCH).
- **`overrides`** — Array of `{ "path": "section.field", "value": <any JSON> }`. Paths must exist in GET /config `sections` and not be `remote_excluded`. Values are validated (e.g. `budget.run` has `ge: 0`).

**Example response (success):**

```json
{
  "accepted": ["budget.run"],
  "rejected": [],
  "pending_restart": []
}
```

**Example response (partial / validation failure):**

```json
{
  "accepted": [],
  "rejected": [["budget.run", "validation error message"]],
  "pending_restart": []
}
```

**Other statuses:**

- `400` — Missing body or `agent_id` mismatch (body: `{"error": "..."}`).
- `422` — Body doesn’t match OverridePayload (body: `{"error": "..."}`).

---

### Call 4: Config stream (SSE) — optional (dashboard / live updates)

| Field | Value |
|-------|--------|
| **Method** | `GET` |
| **URL** | `{{baseUrl}}/config/stream` |
| **When** | Optional; for a UI that wants to react when someone else applies a PATCH. |
| **Body** | None |
| **Response** | `200` — `Content-Type: text/event-stream`; infinite stream. |

**Behavior:**

- First event: `event: heartbeat` with `data: {}`.
- After each PATCH /config, one `event: override` with `data: <JSON>` (same shape as the payload sent to the stream: `agent_id`, `version`, `overrides`).
- Every ~30 s without a PATCH: another `event: heartbeat` with `data: {}`.

**Postman:** Use “Send” and read the stream; or use a separate tool (e.g. `curl`, or a front end) for long-lived SSE. Postman can show the first chunk; it won’t “finish” because the stream never closes.

---

## 3. Other useful endpoints (same server)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness — `{"ready": true}` |
| GET | `/budget` | Current budget state (limit, remaining, spent, percent_used) or 404 if no budget |
| GET | `/describe` | Agent name, description, tools, budget summary |
| POST | `/chat` | Run agent once. Body: `{"message": "Hello"}` or `{"input": "Hello"}`. Response: `{"content": "...", "cost": ..., "tokens": {...}, ...}` |
| POST | `/stream` | Stream agent response as SSE |

**POST /chat body example:**

```json
{
  "message": "Say hi in one word"
}
```

---

## 4. Postman collection variables

Suggested:

| Variable | Value | Usage |
|----------|--------|--------|
| `baseUrl` | `http://localhost:8000` | All requests (or `http://localhost:8000/api/v1` if you use route_prefix) |
| `agent_id` | (set from GET /config response) | PATCH /config body |

**Minimal flow:**

1. GET `{{baseUrl}}/config` → copy `agent_id` into collection variable `agent_id`.
2. PATCH `{{baseUrl}}/config` with body: `{"agent_id": "{{agent_id}}", "version": 1, "overrides": [{"path": "budget.run", "value": 2.0}]}`.

---

## 5. Example paths you can override (this example)

From the example agent (with budget and system_prompt), you’ll typically see:

| Path | Type | Constraint / notes |
|------|------|--------------------|
| `budget.run` | float | `ge: 0` |
| `budget.reserve` | float | `ge: 0` |
| `agent.max_tool_iterations` | int | — |
| `agent.debug` | bool | — |
| `agent.loop_strategy` | str | enum: `react`, `plan_execute`, `code_action`, `single_shot` |
| `agent.system_prompt` | str | — |
| `agent.hitl_timeout` | int | — |

Invalid path (e.g. `budget.foo`) or invalid value (e.g. `budget.run: -1`) → entry in `rejected` and no change.

---

## Maintenance: when you add or remove things

How much you need to change depends on what you change.

| What you change | What to update |
|-----------------|----------------|
| **Add/remove a route** (e.g. new HTTP endpoint) | Add/remove one request in Postman and one row in this doc (e.g. “Other useful endpoints”). |
| **Change a URL path** (e.g. `/config` → `/v1/config`) | Update `baseUrl` or path in every request that uses it; update this doc. |
| **Change request body** (e.g. add a field to OverridePayload) | Update PATCH /config body example and any Postman examples; update “Body shape” in this doc. |
| **Change response shape** (e.g. add a field to GET /config) | Update “Response shape” and any tests/docs that assert on that response. |
| **Add/remove config sections** (e.g. new agent config) | GET /config response changes automatically (schema comes from the agent). Only update “Example paths you can override” if you want to document new paths. |

**Single source of truth:** Request/response contracts are defined in code:

- **GET /config** — `AgentSchema.model_dump(mode="json")` in `src/syrin/serve/http.py` and `syrin.remote._types.AgentSchema`.
- **PATCH /config** — `OverridePayload` in `syrin.remote._types`; response is `ResolveResult` (accepted, rejected, pending_restart).

So:

- **Code change only (no new route):** Update this doc and Postman to match the new contract once; no ongoing “sync” unless you add a new endpoint or change URLs/bodies again.
- **New route:** One new request in Postman + one new section in this doc.
- **Rename/remove route:** Find/replace in Postman and in this doc.

Keeping one Postman collection (and this single doc) next to the example keeps maintenance to a few minutes per API change.
