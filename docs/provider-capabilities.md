# Provider Capabilities & Capability-Aware Routing

This document describes the architecture for provider capability mapping, capability-aware routing, and extensibility for custom providers (e.g., Sarvam AI).

## Current Issues

### 1. Why classification fails

Classification falls back to `GENERAL` because:

- **sentence-transformers not installed**: Embedding-based classification requires `uv pip install 'syrin[classifier-embeddings]'`. Without it, the router catches `ImportError` and uses `low_confidence_fallback` (GENERAL).
- **Fix**: Install the classifier extra, or pass a custom classifier that doesn't need sentence-transformers.

### 2. Why OpenAI/general is selected for "Generate an image of rat"

1. Classification fails → task = `GENERAL`
2. Router filters profiles by task; `general` profile has `strengths=[GENERAL, CREATIVE, TRANSLATION]`
3. Router selects `general` (gpt-4o-mini) because it matches GENERAL
4. `vision` profile has `strengths=[VISION, VIDEO]` — not GENERAL, so it's not considered
5. **Gap**: There is no `IMAGE_GENERATION` task type; "generate image" is semantically different from "understand image" (VISION)

### 3. Generation is hardcoded to Gemini

The Agent's `generate_image` / `generate_video` tools use `get_default_image_generator()` → Gemini Imagen/Veo. When the router selects OpenAI, generation still tries Gemini and fails if `GEMINI_API_KEY` is missing.

---

## Provider Capabilities Matrix (Research)

| Provider | Text | Image Understanding | Image Generation | Video Generation | Voice/Audio |
|----------|------|---------------------|------------------|------------------|-------------|
| **OpenAI** | GPT-4o, GPT-4o-mini, etc. | GPT-4o vision | DALL-E 3, GPT Image (gpt-image-1.5, etc.) | — | Whisper (STT), TTS |
| **Google/Gemini** | Gemini Pro, Flash | Gemini vision | Imagen 3 (Imagen) | Veo 2/3 | — |
| **Anthropic** | Claude 3/4 | Claude vision (analysis) | — | — | — |
| **Sarvam AI** | Sarvam-30B, 105B | Sarvam Vision | — | — | Saaras (STT), Bulbul (TTS), Translation |

### Notes

- **OpenAI**: DALL-E 3 deprecated in favor of GPT Image models (May 2026). Use `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`.
- **Anthropic**: Vision = input analysis only; no image/video generation.
- **Sarvam**: Indian languages; STT (23 langs), TTS (11 langs), Translation, Chat, Document intelligence.

---

## Proposed Architecture

### 1. TaskType: Add IMAGE_GENERATION and VIDEO_GENERATION

```python
class TaskType(StrEnum):
    # existing
    CODE = "code"
    GENERAL = "general"
    VISION = "vision"
    VIDEO = "video"
    # ...
    # new
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
```

Classify "create/draw/generate an image" as `IMAGE_GENERATION`, not `GENERAL` or `VISION`.

### 2. Model: Add generation_backend

Model routing fields (strengths, input_media, output_media, etc.) would gain optional generation backends:

```python
# Proposed: Add to Model constructor / with_routing
image_generation_backend: str | None = None   # "dalle" | "imagen" | None
video_generation_backend: str | None = None   # "veo" | None
```

### 3. Provider Capability Registry (Extensible)

```python
# syrin/router/capabilities.py

@dataclass
class ProviderCapability:
    """Describes what a provider/model can do."""
    provider: str
    text_models: list[str]
    vision_models: list[str]
    image_gen_models: list[str]
    video_gen_models: list[str]
    stt_models: list[str]
    tts_models: list[str]
    # Extensible: custom capabilities
    custom: dict[str, Any] | None = None

# Built-in registry
BUILTIN_CAPABILITIES: dict[str, ProviderCapability] = {
    "openai": ProviderCapability(
        provider="openai",
        text_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", ...],
        vision_models=["gpt-4o", "gpt-4o-mini", ...],
        image_gen_models=["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "dall-e-3", "dall-e-2"],
        video_gen_models=[],
        stt_models=["whisper-1"],
        tts_models=["tts-1", "tts-1-hd"],
    ),
    "gemini": ProviderCapability(
        provider="gemini",
        text_models=["gemini-2.0-flash", "gemini-1.5-pro", ...],
        vision_models=["gemini-2.0-flash", "gemini-1.5-pro", ...],
        image_gen_models=["imagen-3.0-generate-002"],
        video_gen_models=["veo-2.0-generate-001", "veo-3.1"],
        stt_models=[],
        tts_models=[],
    ),
    "anthropic": ProviderCapability(
        provider="anthropic",
        text_models=["claude-sonnet-4-5", "claude-opus-4", ...],
        vision_models=["claude-sonnet-4-5", "claude-opus-4", ...],
        image_gen_models=[],
        video_gen_models=[],
        stt_models=[],
        tts_models=[],
    ),
}

def register_provider_capability(name: str, capability: ProviderCapability) -> None:
    """Allow users to register custom providers (e.g., Sarvam AI)."""
    BUILTIN_CAPABILITIES[name] = capability
```

### 4. Generation Backend Abstraction

```python
# syrin/generation/registry.py

class GenerationBackend(Protocol):
    def generate_image(self, prompt: str, **kwargs: Any) -> GenerationResult | list[GenerationResult]: ...
    def generate_video(self, prompt: str, **kwargs: Any) -> GenerationResult: ...

# Built-in backends
BACKENDS: dict[str, type] = {
    "imagen": GeminiImageProvider,   # existing
    "dalle": OpenAIDalleProvider,    # new: DALL-E / GPT Image
    "veo": GeminiVideoProvider,      # existing
}

def get_generation_backend(
    backend_name: str,
    api_key: str | None = None,
) -> GenerationBackend | None:
    """Resolve backend by name. Uses provider capabilities + API keys."""
    ...
```

### 5. User Extensibility: Custom Provider (e.g., Sarvam)

```python
from syrin.router.capabilities import ProviderCapability, register_provider_capability

# User registers Sarvam
register_provider_capability("sarvam", ProviderCapability(
    provider="sarvam",
    text_models=["sarvam-30b", "sarvam-105b"],
    vision_models=["sarvam-vision"],
    image_gen_models=[],
    video_gen_models=[],
    stt_models=["saaras-v3"],
    tts_models=["bulbul-v3"],
    custom={"translation": ["mayura", "sarvam-translate"]},
))

# User creates Model with provider="sarvam" and routing fields
model = Model.Custom(
    "sarvam-30b",
    api_base="...",
    provider="sarvam",
    profile_name="sarvam-chat",
    strengths=[TaskType.GENERAL, TaskType.TRANSLATION],
)
```

### 6. Routing Flow (Image Generation)

1. User: "Generate an image of a rat"
2. Classifier (with IMAGE_GENERATION examples): task = `IMAGE_GENERATION`
3. Router filters profiles where `IMAGE_GENERATION in strengths` or `Media.IMAGE in output_media`
4. Prefer profile with `image_generation_backend` matching available API keys:
   - If `OPENAI_API_KEY` → prefer profile with `image_generation_backend="dalle"`
   - If `GEMINI_API_KEY` → prefer profile with `image_generation_backend="imagen"`
5. Agent wires `generate_image` to the selected backend (DALL-E vs Imagen)

### 7. Classifier: Add IMAGE_GENERATION Examples

```python
_DEFAULT_EXAMPLES: dict[TaskType, list[str]] = {
    # ...
    TaskType.IMAGE_GENERATION: [
        "generate an image of a rat",
        "create a picture of a sunset",
        "draw a cat",
        "make an image of a mountain",
        "generate a photo of a dog",
    ],
    TaskType.VIDEO_GENERATION: [
        "create a video of a walking person",
        "generate a short clip of ocean waves",
    ],
}
```

---

## Implementation Status

### Phase 1: Completed

1. **Keyword-based fallback** — "generate an image of X" / "create a video of Y" detected without sentence-transformers. No install needed.
2. **TaskType** — `IMAGE_GENERATION` and `VIDEO_GENERATION` added.
3. **Classifier examples** — Default examples for image/video generation.
4. **Chatbot profiles** — Vision profile includes `IMAGE_GENERATION` and `VIDEO_GENERATION` in strengths.
5. **DX** — Run with `uv run python -m examples.16_serving.chatbot` for full classifier; keyword fallback works without it.

### Phase 2–4: Pending

- `image_generation_backend` on Model.
- DALL-E provider for OpenAI.
- Provider capability registry and `register_provider_capability`.

### Phase 2: Generation Backend Abstraction

1. Implement `OpenAIDalleProvider` (DALL-E / GPT Image) in `syrin/generation`.
2. Refactor Agent to select generation backend from the routed profile.
3. Wire `generate_image` to DALL-E when OpenAI profile selected, Imagen when Gemini.

### Phase 3: Provider Capability Registry

1. Add `syrin/router/capabilities.py` with `ProviderCapability` and `register_provider_capability`.
2. Populate built-in capabilities for OpenAI, Gemini, Anthropic.
3. Document how to add custom providers (Sarvam, etc.).

### Phase 4: Capability-Aware Routing

1. Router considers available API keys when selecting among profiles.
2. Prefer profile whose generation backend has a key.
3. Fallback order: DALL-E if OpenAI key, else Imagen if Gemini key.

---

## References

- [OpenAI Image Generation](https://platform.openai.com/docs/guides/image-generation)
- [Google Gemini Imagen/Veo](https://ai.google.dev/gemini-api/docs/video)
- [Anthropic Vision](https://docs.anthropic.com/claude/docs/vision)
- [Sarvam AI APIs](https://docs.sarvam.ai/)
