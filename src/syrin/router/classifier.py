"""Embedding-based prompt classification for model routing.

Production features: LRU cache, batch classify, complexity score, system alignment.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from syrin.router.enums import ComplexityTier, TaskType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_CLASSIFIER_IMPORT_ERROR = (
    "Routing with embedding-based classification requires sentence-transformers. "
    "Install with: uv pip install syrin[classifier-embeddings]"
)

# Improved default examples — more diverse, disambiguate VIDEO vs GENERAL/PLANNING
_DEFAULT_EXAMPLES: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "write a Python function",
        "debug this code",
        "implement binary search",
        "create a REST API",
        "fix the bug in this function",
        "refactor this into a class",
        "write unit tests",
        "what's wrong with my async await",
        "create a FastAPI endpoint",
        "review this pull request",
    ],
    TaskType.GENERAL: [
        "hello how are you",
        "what is the weather",
        "tell me about yourself",
        "thanks for your help",
        "what is the capital of France",
        "can you explain how this works",
        "summarize the meeting notes",
        "what time is it",
        "what is 2 plus 2",
    ],
    TaskType.VISION: [
        "describe this image",
        "what is in the picture",
        "extract text from this image",
        "what objects are in the photo",
        "OCR this screenshot",
    ],
    TaskType.VIDEO: [
        "summarize this video",
        "what happens in the clip",
        "transcribe this video",
        "analyze the footage",
    ],
    TaskType.PLANNING: [
        "plan a project",
        "break down the task",
        "create a strategy",
        "plan a 3-day trip",
        "create a migration strategy",
    ],
    TaskType.REASONING: [
        "solve this math problem",
        "prove the following",
        "analyze the logic",
        "what's the probability",
        "compare pros and cons",
    ],
    TaskType.CREATIVE: [
        "write a short story",
        "brainstorm ideas",
        "compose a poem",
        "write a haiku",
    ],
    TaskType.TRANSLATION: [
        "translate to French",
        "convert to Spanish",
        "translate hello world to Japanese",
    ],
}

# For complexity: simple = low model need, complex = high model need
_COMPLEXITY_SIMPLE: list[str] = [
    "hi",
    "hello",
    "thanks",
    "ok",
    "bye",
    "what time",
    "weather",
]
_COMPLEXITY_COMPLEX: list[str] = [
    "implement a distributed system with consensus",
    "prove the following theorem",
    "refactor this codebase for scalability",
    "design an architecture for high availability",
]


@dataclass
class ClassificationResult:
    """Extended classification result for production routing.

    Attributes:
        task_type: Detected task type.
        confidence: Classification confidence [0, 1].
        complexity_score: 0 = use cheap model, 1 = prefer premium. Based on prompt heuristics + embedding.
        complexity_tier: LOW, MEDIUM, or HIGH.
        system_alignment_score: When system_prompt provided, similarity [0, 1]. High = prompt in scope.
        used_fallback: True if confidence < min_confidence.
        latency_ms: Classification latency in milliseconds.
    """

    task_type: TaskType
    confidence: float
    complexity_score: float
    complexity_tier: ComplexityTier
    system_alignment_score: float | None
    used_fallback: bool
    latency_ms: float


def _load_sentence_transformers(
    model_name: str,
    cache_dir: str | None,
) -> Any:
    """Lazy load SentenceTransformer. Raises ImportError with install hint if missing."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name, cache_folder=cache_dir)
    except ImportError as e:
        raise ImportError(_CLASSIFIER_IMPORT_ERROR) from e


def _cosine_sim(a: list[float], b: list[float]) -> float:
    import numpy as np

    na, nb = np.array(a), np.array(b)
    dot = float(np.dot(na, nb))
    norm = np.linalg.norm(na) * np.linalg.norm(nb) + 1e-9
    raw = dot / norm
    return float((raw + 1) / 2)  # map [-1,1] to [0,1]


def _complexity_heuristic(prompt: str) -> float:
    """Heuristic complexity score [0, 1]. Fast, no embedding."""
    score = 0.0
    text = prompt.strip().lower()
    # Length (rough: >500 chars = complex)
    if len(text) > 500:
        score += 0.4
    elif len(text) > 200:
        score += 0.2
    elif len(text) < 20:
        score -= 0.2
    # Multiple sentences
    sents = re.split(r"[.!?]+", text)
    if len([s for s in sents if s.strip()]) > 3:
        score += 0.2
    # Technical indicators
    tech = [
        "implement",
        "design",
        "architecture",
        "refactor",
        "debug",
        "prove",
        "algorithm",
        "distributed",
        "scalable",
        "consensus",
        "theorem",
    ]
    if any(t in text for t in tech):
        score += 0.3
    # Question words often simpler
    if text.startswith(("what is", "who is", "when", "where", "how many")) and len(text) < 80:
        score -= 0.1
    return min(1.0, max(0.0, score))


class EmbeddingClassifier:
    """Embedding-based task classifier. Uses sentence-transformers for cosine similarity."""

    def __init__(
        self,
        *,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir: str | None = None,
        examples: dict[TaskType, list[str]] | None = None,
    ) -> None:
        self._model_name = model
        self._cache_dir = cache_dir
        self._examples = examples or _DEFAULT_EXAMPLES
        self._model: Any = None
        self._task_embeddings: dict[TaskType, list[list[float]]] | None = None
        self._simple_emb: list[list[float]] | None = None
        self._complex_emb: list[list[float]] | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        self._model = _load_sentence_transformers(self._model_name, self._cache_dir)
        self._compute_task_embeddings()
        self._simple_emb = [list(e) for e in self._model.encode(_COMPLEXITY_SIMPLE)]
        self._complex_emb = [list(e) for e in self._model.encode(_COMPLEXITY_COMPLEX)]

    def _compute_task_embeddings(self) -> None:
        texts: list[str] = []
        task_indices: list[TaskType] = []
        for task, prompts in self._examples.items():
            for p in prompts:
                texts.append(p)
                task_indices.append(task)
        embeddings = self._model.encode(texts)
        self._task_embeddings = {}
        for i, task in enumerate(task_indices):
            if task not in self._task_embeddings:
                self._task_embeddings[task] = []
            emb = embeddings[i]
            self._task_embeddings[task].append(
                emb.tolist() if hasattr(emb, "tolist") else list(emb)
            )

    def classify(self, prompt: str) -> tuple[TaskType, float]:
        """Classify prompt into TaskType and return confidence in [0, 1]."""
        self._ensure_loaded()
        prompt_emb = self._model.encode([prompt.strip() or " "])[0]
        prompt_list = prompt_emb.tolist() if hasattr(prompt_emb, "tolist") else list(prompt_emb)
        best_task = TaskType.GENERAL
        best_score = -1.0
        for task, task_embs in (self._task_embeddings or {}).items():
            for te in task_embs:
                score = _cosine_sim(prompt_list, te)
                if score > best_score:
                    best_score = score
                    best_task = task
        return (best_task, min(1.0, max(0.0, best_score)))

    def complexity_score(self, prompt_emb: list[float]) -> float:
        """Embedding-based complexity [0,1]. Higher = needs premium model."""
        self._ensure_loaded()
        sim_simple = (
            max(_cosine_sim(prompt_emb, se) for se in (self._simple_emb or []))
            if self._simple_emb
            else 0.0
        )
        sim_complex = (
            max(_cosine_sim(prompt_emb, ce) for ce in (self._complex_emb or []))
            if self._complex_emb
            else 0.0
        )
        # More similar to complex examples = higher score
        return min(1.0, max(0.0, (sim_complex - sim_simple + 1) / 2))

    def system_alignment_score(self, prompt_emb: list[float], system_emb: list[float]) -> float:
        """Similarity between prompt and system prompt. High = prompt in scope."""
        return _cosine_sim(prompt_emb, system_emb)


class PromptClassifier(BaseModel):
    """Embedding-based prompt classifier for model routing. Production-ready.

    Features: task detection, complexity score, system alignment, LRU cache, batch.
    """

    model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers model name.",
    )
    cache_dir: str | None = Field(
        default=None,
        description="Cache directory for model. None = HF default.",
    )
    min_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Below this confidence, use low_confidence_fallback.",
    )
    low_confidence_fallback: TaskType = Field(
        default=TaskType.GENERAL,
        description="Task type when confidence < min_confidence.",
    )
    examples: dict[TaskType, list[str]] | None = Field(
        default=None,
        description="Custom task examples. None = use defaults.",
    )
    enable_cache: bool = Field(
        default=True,
        description="Enable LRU cache for classify results. Recommended for production.",
    )
    max_cache_size: int = Field(
        default=1000,
        ge=0,
        description="Max cached prompt hashes. 0 = disable cache.",
    )
    complexity_use_embedding: bool = Field(
        default=True,
        description="Use embedding for complexity; else heuristic only.",
    )

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _validate_cache_dir(self) -> PromptClassifier:
        if self.cache_dir is None:
            return self
        path = os.path.abspath(self.cache_dir)
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise ValueError(f"cache_dir must be a directory, got file: {self.cache_dir!r}")
            if not os.access(path, os.W_OK):
                raise ValueError(f"cache_dir must be writable: {self.cache_dir!r}")
        else:
            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                raise ValueError(f"cache_dir parent does not exist: {parent!r}")
            if not os.access(parent, os.W_OK):
                raise ValueError(f"cache_dir parent must be writable to create: {parent!r}")
        return self

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._embedding_classifier: EmbeddingClassifier | None = None
        self._cache: OrderedDict[str, tuple[TaskType, float]] = OrderedDict()
        self._cache_lock = Lock()

    def _get_embedding_classifier(self) -> EmbeddingClassifier:
        if self._embedding_classifier is None:
            self._embedding_classifier = EmbeddingClassifier(
                model=self.model,
                cache_dir=self.cache_dir,
                examples=self.examples or _DEFAULT_EXAMPLES,
            )
        return self._embedding_classifier

    def _cache_key(self, prompt: str, system_prompt: str | None) -> str:
        h = hashlib.sha256((prompt + (system_prompt or "")).encode()).hexdigest()
        return h[:32]

    def _get_cached(self, key: str) -> tuple[TaskType, float] | None:
        if not self.enable_cache or self.max_cache_size <= 0:
            return None
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def _set_cached(self, key: str, value: tuple[TaskType, float]) -> None:
        if not self.enable_cache or self.max_cache_size <= 0:
            return
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_cache_size:
                    self._cache.popitem(last=False)
                self._cache[key] = value

    def classify(self, prompt: str) -> tuple[TaskType, float]:
        """Classify prompt into TaskType and confidence. Uses fallback when confidence < min."""
        key = self._cache_key(prompt, None)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        try:
            emb = self._get_embedding_classifier()
            task, confidence = emb.classify(prompt)
            if confidence < self.min_confidence:
                result = (self.low_confidence_fallback, confidence)
            else:
                result = (task, confidence)
            self._set_cached(key, result)
            return result
        except ImportError:
            raise
        except Exception as e:
            logger.warning("Classification failed, using fallback: %s", e)
            result = (self.low_confidence_fallback, 0.0)
            self._set_cached(key, result)
            return result

    def classify_extended(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ClassificationResult:
        """Extended classification: task_type, confidence, complexity_score, system_alignment_score.

        Use for production routing when you need higher vs lower model selection
        and/or alignment with system prompt scope.
        """
        t0 = time.perf_counter()
        used_fallback = False
        emb_cls = self._get_embedding_classifier()
        emb_cls._ensure_loaded()

        prompt_clean = prompt.strip() or " "
        prompt_emb_raw = emb_cls._model.encode([prompt_clean])[0]
        prompt_emb = (
            prompt_emb_raw.tolist() if hasattr(prompt_emb_raw, "tolist") else list(prompt_emb_raw)
        )

        # Task + confidence
        task, confidence = emb_cls.classify(prompt)
        if confidence < self.min_confidence:
            task = self.low_confidence_fallback
            used_fallback = True

        # Complexity
        h_score = _complexity_heuristic(prompt)
        if self.complexity_use_embedding:
            e_score = emb_cls.complexity_score(prompt_emb)
            complexity = 0.5 * h_score + 0.5 * e_score
        else:
            complexity = h_score
        if complexity < 0.33:
            tier = ComplexityTier.LOW
        elif complexity < 0.66:
            tier = ComplexityTier.MEDIUM
        else:
            tier = ComplexityTier.HIGH

        # System alignment
        alignment: float | None = None
        if system_prompt and system_prompt.strip():
            sys_emb = emb_cls._model.encode([system_prompt.strip()])[0]
            sys_list = sys_emb.tolist() if hasattr(sys_emb, "tolist") else list(sys_emb)
            alignment = emb_cls.system_alignment_score(prompt_emb, sys_list)

        latency_ms = (time.perf_counter() - t0) * 1000
        return ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=round(complexity, 4),
            complexity_tier=tier,
            system_alignment_score=alignment,
            used_fallback=used_fallback,
            latency_ms=round(latency_ms, 2),
        )

    def classify_batch(
        self,
        prompts: list[str],
    ) -> list[tuple[TaskType, float]]:
        """Batch classify. More efficient than repeated classify() for many prompts."""
        results: list[tuple[TaskType, float]] = []
        for p in prompts:
            results.append(self.classify(p))
        return results

    def warmup(self) -> None:
        """Load the model explicitly. Call before first classify to avoid latency spike."""
        self._get_embedding_classifier()._ensure_loaded()

    def clear_cache(self) -> None:
        """Clear classification cache. Use when examples or config change."""
        with self._cache_lock:
            self._cache.clear()
