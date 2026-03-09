# Model Routing

Intelligent model routing selects the best model based on task type, modality, cost, and developer preferences — **before** any LLM call.

Key components: ModelProfile, ModalityDetector, RouterConfig, ModelRouter, RoutingReason, DEFAULT_PROFILES, Agent integration, OpenRouter, response metadata, ROUTING_DECISION hook.

## What Developers Can Build

With the routing system, you can:

| Capability | How |
|------------|-----|
| **Task-based routing** | Route code → Claude, general → GPT-4o-mini, vision → Gemini, etc. |
| **Cost optimization** | COST_FIRST mode; budget thresholds; `max_cost_per_1k_tokens` cap |
| **Quality-first** | QUALITY_FIRST mode; HIGH complexity → highest-priority model |
| **Single API key** | OpenRouterBuilder — one key for Anthropic, OpenAI, Google, etc. |
| **Custom routing logic** | `routing_rule_callback` — VIP prompts, A/B tests, manual overrides |
| **Force specific model** | `force_model` — bypass routing for debugging or pinned model |
| **Tools-aware** | Exclude text-only models when Agent has tools (`supports_tools`) |
| **Vision/Video routing** | `modality_input` — route to vision models when messages have images |
| **Budget-aware** | `economy_at`, `cheapest_at`, `budget_optimisation` — prefer cheap when low |
| **Custom classifier** | Pass `classifier` to RouterConfig for custom task detection |
| **Production classification** | `classify_extended` — complexity, system alignment, LRU cache |
| **Observability** | `Hook.ROUTING_DECISION`; `r.routing_reason`, `r.model_used`, `r.actual_cost` |

Use Agent with `model=[...]` + `router_config=RouterConfig(...)` for automatic per-request routing. Or use `ModelRouter` standalone with custom profiles.

## Enums

### TaskType

Detected task type for routing:

| Value | Use |
|-------|-----|
| `CODE` | Code generation, debugging, review |
| `GENERAL` | General conversation, Q&A |
| `VISION` | Image understanding, OCR |
| `VIDEO` | Video analysis |
| `PLANNING` | Task decomposition, strategy |
| `REASONING` | Math, logic, analysis |
| `CREATIVE` | Writing, brainstorming |
| `TRANSLATION` | Language translation |

### Modality

Generic enum for content and model capabilities (TEXT, IMAGE, VIDEO, AUDIO, FILE). Use for message content detection and model input/output capabilities.

### RoutingMode

| Value | Behavior |
|-------|----------|
| `AUTO` | Balance cost and capability (default) |
| `COST_FIRST` | Cheapest capable model |
| `QUALITY_FIRST` | Highest-priority capable model |
| `MANUAL` | Developer provides task type |

## PromptClassifier

Embedding-based task classification — no LLM needed. Uses sentence-transformers for cosine similarity between prompt and task examples.

**Install optional dependency:**

```bash
uv pip install syrin[classifier-embeddings]
```

**Usage:**

```python
from syrin.router import PromptClassifier, TaskType

classifier = PromptClassifier(
    model="sentence-transformers/all-MiniLM-L6-v2",
    min_confidence=0.6,
    low_confidence_fallback=TaskType.GENERAL,
)

task_type, confidence = classifier.classify("write a function to sort a list")
# → (TaskType.CODE, 0.92)

# Low-confidence prompts use fallback
task_type, confidence = classifier.classify("hi")
# → (TaskType.GENERAL, 0.35)  # Below min, returns fallback
```

**Custom examples:**

```python
classifier = PromptClassifier(
    examples={
        TaskType.CODE: ["implement binary search", "fix the bug"],
        TaskType.REASONING: ["solve this math problem", "prove the following"],
    },
)
task_type, confidence = classifier.classify("solve this math problem")
```

**Warmup (optional):** Load the model before first use to avoid latency on first classify:

```python
classifier.warmup()
```

### Production: Extended Classification

For higher vs lower model selection and system-prompt alignment:

```python
from syrin.router import PromptClassifier, ClassificationResult, ComplexityTier

classifier = PromptClassifier(enable_cache=True, max_cache_size=1000)

# Returns task_type, confidence, complexity_score, system_alignment_score
result = classifier.classify_extended(
    "Implement a distributed consensus algorithm",
    system_prompt="You are a coding assistant.",
)
# result.task_type, result.confidence
# result.complexity_score  # 0=cheap model, 1=premium
# result.complexity_tier   # LOW, MEDIUM, HIGH
# result.system_alignment_score  # High = prompt in scope
```

When `complexity_tier == HIGH`, the router prefers highest-priority capable models.

### ComplexityTier

| Value | Use |
|-------|-----|
| `LOW` | Simple prompts — use cheaper models |
| `MEDIUM` | Moderate — balance cost/capability |
| `HIGH` | Complex — prefer premium models |

### Production Settings

- **enable_cache** (default True): LRU cache for repeated prompts.
- **max_cache_size** (default 1000): Max cached results. `0` to disable.
- **clear_cache()**: Call when examples or config change.
- **complexity_use_embedding** (default True): Use embedding for complexity; else heuristic only.

## Cache

Models use Hugging Face cache (`~/.cache/huggingface/`). Override with `cache_dir`:

```python
classifier = PromptClassifier(cache_dir="/path/to/cache")
```

If `cache_dir` is provided and does not exist, the parent directory must exist and be writable.

## ModelProfile

Define what each model can do — capabilities, strengths, modality, tool support:

```python
from syrin.model import Model
from syrin.router import Modality, TaskType
from syrin.router import ModelProfile

profile = ModelProfile(
    model=Model.Anthropic("claude-sonnet-4-5", api_key="..."),
    name="claude-code",
    strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
    modality_input={Modality.TEXT},
    modality_output={Modality.TEXT},
    supports_tools=True,
    priority=100,
)
```

Cost is derived from `model.pricing` (or MODEL_PRICING lookup). `supports_tools=False` excludes the profile when tools are present.

## ModalityDetector

Detect required modalities from messages before routing:

```python
from syrin.router import ModalityDetector
from syrin.types import Message

detector = ModalityDetector()
modalities = detector.detect(messages)  # {Modality.TEXT}, or + IMAGE, VIDEO, AUDIO
```

Detects base64 data URLs (`data:image/...;base64,...`) in message content.

## Agent Integration

Pass a list of models and optional `router_config` to enable automatic routing:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import RouterConfig, RoutingMode, TaskType

# Simple: model list + router_config
agent = Agent(
    model=[
        Model.Anthropic("claude-sonnet-4-5", api_key="..."),
        Model.OpenAI("gpt-4o-mini", api_key="..."),
        Model.Google("gemini-2.0-flash", api_key="..."),
    ],
    router_config=RouterConfig(routing_mode=RoutingMode.AUTO),
    system_prompt="You are helpful.",
    budget=Budget(run=10.0),
)

# Agent routes per request
r = agent.response("write a sorting function")
# Uses Claude (CODE task)
print(r.routing_reason.selected_model, r.routing_reason.reason)

r = agent.response("what is the weather?")
# Uses GPT-4o-mini (GENERAL task)

# Task override for ambiguous prompts
r = agent.response("Fix this", task_type=TaskType.CODE)

# Force specific model (bypass routing)
agent = Agent(
    model=[...],
    router_config=RouterConfig(force_model=Model.Anthropic("claude-opus", api_key="...")),
)
```

**Response metadata (when routing):** `r.routing_reason`, `r.model_used`, `r.task_type`, `r.actual_cost`.

**Hook:** Subscribe to `Hook.ROUTING_DECISION` for observability. EventContext includes `routing_reason`, `model`, `task_type`, `prompt`.

## OpenRouter

Single API key for multiple providers. Use `Model.OpenRouter` or `OpenRouterBuilder`:

```python
import os
from syrin.model import Model, OpenRouterBuilder

# Single model
model = Model.OpenRouter(
    "anthropic/claude-sonnet-4-5",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Builder: one key, multiple models (for routing)
builder = OpenRouterBuilder(api_key=os.getenv("OPENROUTER_API_KEY"))
claude = builder.model("anthropic/claude-sonnet-4-5")
gpt = builder.model("openai/gpt-4o-mini")

agent = Agent(
    model=[claude, gpt],
    router_config=RouterConfig(routing_mode=RoutingMode.COST_FIRST),
    system_prompt="You are helpful.",
)
```

OpenRouter response headers (`x-openrouter-total-cost`, `x-openrouter-model-used`) populate `response.actual_cost` and `response.model_used` when available.

## RouterConfig

Configuration for routing — use with Agent or pass to ModelRouter:

```python
from syrin.router import RouterConfig, RoutingMode

config = RouterConfig(
    routing_mode=RoutingMode.AUTO,
    budget_optimisation=True,
    economy_at=0.20,
    cheapest_at=0.10,
)
```

| Field | Default | Description |
|-------|---------|-------------|
| `routing_mode` | AUTO | AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL |
| `force_model` | None | Bypass routing; always use this model |
| `classifier` | None | Custom PromptClassifier; None = default embeddings-based |
| `router` | None | Explicit ModelRouter; overrides auto-created from model list |
| `profiles` | None | Custom profiles; override auto-generated from model list |
| `budget_optimisation` | True | Prefer cheaper models when budget runs low |
| `economy_at` | 0.20 | When remaining/limit < 20%, prefer cheaper capable models |
| `cheapest_at` | 0.10 | When remaining/limit < 10%, force cheapest capable model |
| `max_cost_per_1k_tokens` | None | Cap on cost per 1K tokens when selecting models |
| `routing_rule_callback` | None | `(prompt, task_type, profile_names) -> profile_name | None` |

**Custom routing callback** — VIP prompts, A/B logic, or manual overrides:

```python
def vip_routing(prompt: str, task_type: TaskType, profile_names: list[str]) -> str | None:
    if "VIP" in prompt:
        return "premium"  # Force premium model for VIP
    if task_type == TaskType.CODE and "preview" in profile_names:
        return "preview"  # A/B: use preview model for code
    return None  # Let router decide

agent = Agent(
    model=[claude, gpt],
    router_config=RouterConfig(routing_rule_callback=vip_routing),
)
```

**MANUAL mode** — You provide task type; no classification:

```python
router = ModelRouter(profiles=profiles, routing_mode=RoutingMode.MANUAL)
model, task, reason = router.route("Fix this", task_override=TaskType.CODE)
```

## profiles_from_models

Build profiles from a model list for simple routing (all models get GENERAL strength):

```python
from syrin.model import Model
from syrin.router import profiles_from_models, ModelRouter, TaskType

profiles = profiles_from_models([
    Model.OpenAI("gpt-4o-mini", api_key="..."),
    Model.Anthropic("claude-sonnet", api_key="..."),
], strengths=[TaskType.GENERAL])  # Optional; default GENERAL

router = ModelRouter(profiles=profiles)
```

For specialized routing (code vs vision), define `ModelProfile` directly with per-model strengths.

## ModelRouter

Main routing class. Selects the best model based on task, modality, cost, and budget:

```python
from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RoutingMode,
    TaskType,
)

router = ModelRouter(
    profiles=[
        ModelProfile(
            model=Model.Anthropic("claude-sonnet-4-5", api_key="..."),
            name="code",
            strengths=[TaskType.CODE, TaskType.REASONING],
        ),
        ModelProfile(
            model=Model.OpenAI("gpt-4o-mini", api_key="..."),
            name="general",
            strengths=[TaskType.GENERAL],
        ),
    ],
    routing_mode=RoutingMode.AUTO,
)

model, task_type, reason = router.route("write a sorting function")
print(reason.selected_model, reason.reason, reason.cost_estimate)
```

**Task override:** For ambiguous prompts, pass `task_override`:

```python
model, task, reason = router.route("Fix this", task_override=TaskType.CODE)
```

**Force model:** Bypass routing:

```python
router = ModelRouter(
    profiles=[...],
    force_model=Model.Anthropic("claude-opus", api_key="..."),
)
```

## RoutingReason

Returned by `router.route()`. Explains the selection:

- `selected_model` — Profile name chosen
- `task_type` — Detected or overridden task type
- `reason` — Human-readable explanation
- `cost_estimate` — Estimated cost in USD
- `alternatives` — Other profile names that could have been used
- `classification_confidence` — 0.0–1.0 from PromptClassifier
- `complexity_tier` — LOW/MEDIUM/HIGH when classify_extended used (production)
- `system_alignment_score` — Prompt vs system alignment [0,1] when available

## Default Profiles

Use or override built-in profiles:

```python
from syrin.router import DEFAULT_PROFILES

profiles = list(DEFAULT_PROFILES.values())
router = ModelRouter(profiles=profiles)
```

Default profiles: `claude-code`, `gpt-general`, `gemini-vision`. Pass API keys when using with Agent.

## Budget Thresholds

When `budget_optimisation=True` (default) and Agent has a run budget:

- `economy_at` (default 0.20): When remaining/limit < 20%, router prefers cheaper capable models
- `cheapest_at` (default 0.10): When remaining/limit < 10%, router forces cheapest capable model

Use with `Budget(run=1.0)` for cost-sensitive agents.

## Custom Classifier

Pass a custom `PromptClassifier` to use your own task detection logic:

```python
from syrin.router import PromptClassifier, RouterConfig, TaskType

classifier = PromptClassifier(
    examples={TaskType.CODE: ["write", "debug", "implement"], ...},
    min_confidence=0.7,
)

agent = Agent(
    model=[...],
    router_config=RouterConfig(classifier=classifier),
)
```

Or pass a classifier to `ModelRouter` directly when using standalone routing.

## Response Metadata (when routing)

When using Agent with routing, the response includes:

- `r.routing_reason` — `RoutingReason` (selected_model, task_type, reason, cost_estimate, alternatives, classification_confidence, complexity_tier, system_alignment_score)
- `r.model_used` — Model ID that answered (from provider/OpenRouter headers when available)
- `r.task_type` — Detected or overridden task type
- `r.actual_cost` — Actual cost when provider reports it (e.g. OpenRouter `x-openrouter-total-cost`)

See [Response Object](agent/response.md) for the full response reference.

## See Also

- [Models Guide](models.md) — `Model.OpenRouter`, `OpenRouterBuilder`, built-in providers
- [Agent: Model](agent/model.md) — `model` as list, `router_config` with Agent
- [Response](agent/response.md) — Response fields including routing metadata
- [Events & Hooks](agent/events-hooks.md) — `Hook.ROUTING_DECISION`
