# Testing remote config (manual and automated)

This document describes how to verify that remote config overrides (guardrails, prompt_vars, tools, budget, etc.) work end-to-end: run a server, apply overrides via the config API, then confirm the agent state and behavior change.

## Automated test

The project includes an E2E test that runs a full-featured agent behind the config routes and asserts overrides are applied correctly:

```bash
uv run pytest tests/unit/serve/test_http_config_routes.py -v -k "TestRemoteConfigE2EFullFeatures"
```

The test:

1. Builds an agent with guardrails (e.g. `PIIScanner`), `prompt_vars`, and two tools (`alpha`, `beta`).
2. Serves it via FastAPI TestClient (GET/PATCH `/config`).
3. **GET /config** — Asserts `sections` include `guardrails`, `prompt_vars`, `tools`, and `current_values` match (e.g. `prompt_vars.x`, `tools.alpha.enabled`, `guardrails.PIIScanner.enabled`).
4. **PATCH /config** — Sends overrides: disable `PIIScanner`, set `prompt_vars.env` to `prod`, disable tool `alpha`.
5. Asserts agent state: `agent._guardrails_disabled`, `agent._prompt_vars`, `agent._tools_disabled`, and `len(agent.tools) == 1` (only `beta`).
6. **GET /config** again — Asserts `current_values` reflect the overrides (e.g. `guardrails.PIIScanner.enabled: false`, `prompt_vars.env: "prod"`, `tools.alpha.enabled: false`).

So: **we did test it** — the automated test runs a server (in-process), overrides guardrails, prompt_vars, and tools, and verifies the agent state and config response.

## Manual test (run server + curl)

Use the full-featured example server so all relevant sections (guardrails, prompt_vars, tools, budget, agent) are present.

### 1. Start the server

```bash
cd /path/to/syrin-python
PYTHONPATH=. python examples/12_remote_config/serve_full_features.py
```

Server runs at `http://localhost:8000`.

### 2. Get config (schema + current values)

```bash
curl -s http://localhost:8000/config | jq .
```

From the response, note:

- `agent_id` (e.g. `full_features_agent:Agent`) — needed for PATCH.
- `sections` — should include `agent`, `budget`, `guardrails`, `prompt_vars`, `tools`.
- `current_values` — e.g. `guardrails.PIIScanner.enabled: true`, `prompt_vars.env: "staging"`, `tools.get_weather.enabled: true`, `tools.get_time.enabled: true`.

### 3. Apply overrides

Disable the PIIScanner guardrail, change prompt_vars, and disable one tool:

```bash
curl -s -X PATCH http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "full_features_agent:Agent",
    "version": 1,
    "overrides": [
      {"path": "guardrails.PIIScanner.enabled", "value": false},
      {"path": "prompt_vars.env", "value": "prod"},
      {"path": "prompt_vars.limit", "value": "20"},
      {"path": "tools.get_weather.enabled", "value": false}
    ]
  }' | jq .
```

Expected: `200` with body like `{"accepted": ["guardrails.PIIScanner.enabled", "prompt_vars.env", "prompt_vars.limit", "tools.get_weather.enabled"], "rejected": [], "pending_restart": []}`.

(Replace `full_features_agent:Agent` with the `agent_id` from step 2 if different.)

### 4. Verify config after overrides

```bash
curl -s http://localhost:8000/config | jq '.current_values | {guardrails_PIIScanner: .["guardrails.PIIScanner.enabled"], prompt_vars_env: .["prompt_vars.env"], prompt_vars_limit: .["prompt_vars.limit"], tools_get_weather: .["tools.get_weather.enabled"], tools_get_time: .["tools.get_time.enabled"]}'
```

Expected: `guardrails_PIIScanner: false`, `prompt_vars_env: "prod"`, `prompt_vars_limit: "20"`, `tools_get_weather: false`, `tools_get_time: true`.

### 5. Verify behavior (optional)

- **Tools:** After disabling `get_weather`, the agent should not be offered that tool. Send a chat request; the model should only have `get_time` available.
- **Prompt vars:** The system prompt uses `{env}` and `{limit}`; after overrides they should resolve to `prod` and `20` in the actual prompt.
- **Guardrails:** With PIIScanner disabled, that guardrail is not run on input/output.

Example chat request:

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?"}' | jq .
```

The agent will only use the `get_time` tool (get_weather is disabled).

## Summary

| What we test | How |
|--------------|-----|
| Schema and current values | GET /config → sections and current_values for guardrails, prompt_vars, tools, budget, agent |
| Override application | PATCH /config with OverridePayload → accepted paths, no rejected |
| Agent state after PATCH | Assert `_guardrails_disabled`, `_prompt_vars`, `_tools_disabled`, `agent.tools` (automated test) |
| Config reflects overrides | GET /config again → current_values match overrides |
| Behavior | Disabled tool not in `agent.tools`; prompt_vars used in prompt; disabled guardrail not run (manual) |

Automated tests live in `tests/unit/serve/test_http_config_routes.py` (class `TestRemoteConfigE2EFullFeatures`). Manual flow uses `examples/12_remote_config/serve_full_features.py` and the curl steps above.
