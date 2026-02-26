# Test layout

Tests are grouped by kind:

- **unit/** — Single-component tests (mocked or no real I/O). One directory per domain (agent, budget, memory, tool, etc.).
- **integration/** — Multi-component or real I/O tests (e.g. agent with budget/model/memory, core_stability).
- **e2e/** — Full-system / end-to-end tests (reserved for future use).

Run all tests:

```bash
uv run pytest tests/
```

Run only unit or integration:

```bash
uv run pytest tests/unit/
uv run pytest tests/integration/
```
