"""Tests for PromptClassifier and EmbeddingClassifier — embedding-based task classification."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from syrin.router import ComplexityTier, TaskType
from syrin.router.classifier import EmbeddingClassifier, PromptClassifier


class TestEmbeddingClassifierImportError:
    """When sentence-transformers is not installed, classify raises ImportError with install hint."""

    def test_missing_sentence_transformers_raises_import_error(self) -> None:
        from syrin.router.classifier import _CLASSIFIER_IMPORT_ERROR

        with patch(
            "syrin.router.classifier._load_sentence_transformers",
            side_effect=ImportError(_CLASSIFIER_IMPORT_ERROR),
        ):
            classifier = EmbeddingClassifier()
            with pytest.raises(ImportError) as exc_info:
                classifier.classify("write a function")
            assert "classifier-embeddings" in str(exc_info.value)
            assert "sentence-transformers" in str(exc_info.value)


class TestEmbeddingClassifierWithMock:
    """EmbeddingClassifier with mocked sentence-transformers for fast unit tests."""

    @pytest.fixture
    def mock_encode(self) -> object:
        """Fake encode that returns fixed embeddings per prompt prefix."""

        def _encode(
            self_or_texts: object, texts: object | None = None, **kwargs: object
        ) -> list[list[float]]:
            t_list = texts if texts is not None else self_or_texts
            if not isinstance(t_list, list):
                t_list = [t_list]
            dim = 384
            result = []
            for t in t_list:
                s = str(t) if t else " "
                vals = [0.1 * (ord(c) % 10) for c in (s[:20] + "x" * 20)[:dim]]
                while len(vals) < dim:
                    vals.append(0.0)
                result.append(vals[:dim])
            return result

        return _encode

    @pytest.fixture
    def mock_model(self, mock_encode: object) -> object:
        return type("MockModel", (), {"encode": mock_encode})()

    def test_classify_returns_tuple_task_confidence(
        self, mock_model: object, mock_encode: object
    ) -> None:
        with patch("syrin.router.classifier._load_sentence_transformers", return_value=mock_model):
            classifier = EmbeddingClassifier(
                model="sentence-transformers/all-MiniLM-L6-v2",
                examples={
                    TaskType.CODE: ["write a function", "debug code"],
                    TaskType.GENERAL: ["hello", "what is the weather"],
                },
            )
            task, confidence = classifier.classify("write a function to sort")
            assert isinstance(task, TaskType)
            assert task in (TaskType.CODE, TaskType.GENERAL)  # One of our examples
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_classify_with_custom_examples(self, mock_model: object, mock_encode: object) -> None:
        with patch("syrin.router.classifier._load_sentence_transformers", return_value=mock_model):
            classifier = EmbeddingClassifier(
                examples={
                    TaskType.CODE: ["implement binary search"],
                    TaskType.REASONING: ["solve this math problem"],
                },
            )
            task, confidence = classifier.classify("solve this math problem")
            assert task in (TaskType.CODE, TaskType.REASONING)
            assert 0.0 <= confidence <= 1.0

    def test_empty_prompt_returns_valid_result(
        self, mock_model: object, mock_encode: object
    ) -> None:
        with patch("syrin.router.classifier._load_sentence_transformers", return_value=mock_model):
            classifier = EmbeddingClassifier(
                examples={TaskType.GENERAL: ["hi"], TaskType.CODE: ["code"]},
            )
            task, confidence = classifier.classify("")
            assert isinstance(task, TaskType)
            assert 0.0 <= confidence <= 1.0

    def test_classify_is_lazy_model_load(self) -> None:
        load_called = []

        def track_load(*args: object, **kwargs: object) -> object:
            load_called.append(1)
            return type(
                "Mock", (), {"encode": lambda _s, texts, **_k: [[0.0] * 384 for _ in texts]}
            )()

        with patch("syrin.router.classifier._load_sentence_transformers", side_effect=track_load):
            classifier = EmbeddingClassifier(examples={TaskType.GENERAL: ["hi"]})
            assert len(load_called) == 0
            classifier.classify("hello")
            assert len(load_called) == 1
            classifier.classify("hi again")
            assert len(load_called) == 1  # Still 1, model cached


class TestPromptClassifierValidation:
    """PromptClassifier construction validations."""

    def test_min_confidence_in_range(self) -> None:
        with pytest.raises(ValueError, match="min_confidence"):
            PromptClassifier(min_confidence=1.5)
        with pytest.raises(ValueError, match="min_confidence"):
            PromptClassifier(min_confidence=-0.1)
        # Valid
        c = PromptClassifier(min_confidence=0.0)
        assert c.min_confidence == 0.0
        c = PromptClassifier(min_confidence=1.0)
        assert c.min_confidence == 1.0
        c = PromptClassifier(min_confidence=0.6)
        assert c.min_confidence == 0.6

    def test_defaults(self) -> None:
        c = PromptClassifier()
        assert c.min_confidence == 0.6
        assert c.low_confidence_fallback == TaskType.GENERAL
        assert c.model == "sentence-transformers/all-MiniLM-L6-v2"
        assert c.cache_dir is None

    def test_custom_low_confidence_fallback(self) -> None:
        c = PromptClassifier(low_confidence_fallback=TaskType.CODE)
        assert c.low_confidence_fallback == TaskType.CODE

    def test_cache_dir_file_raises(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            with pytest.raises(ValueError, match="cache_dir must be a directory"):
                PromptClassifier(cache_dir=path)
        finally:
            import os

            os.unlink(path)

    def test_cache_dir_nonexistent_parent_raises(self) -> None:
        with pytest.raises(ValueError, match="parent does not exist"):
            PromptClassifier(cache_dir="/nonexistent/parent/cache")


class TestPromptClassifierClassify:
    """PromptClassifier.classify behavior."""

    @pytest.fixture
    def mock_embedding_result(self) -> tuple[TaskType, float]:
        return (TaskType.CODE, 0.85)

    def test_classify_delegates_to_embedding_and_returns_high_confidence(
        self, mock_embedding_result: tuple[TaskType, float]
    ) -> None:
        with patch.object(
            EmbeddingClassifier,
            "classify",
            return_value=mock_embedding_result,
        ):
            c = PromptClassifier(min_confidence=0.5)
            task, confidence = c.classify("write a function")
            assert task == TaskType.CODE
            assert confidence == 0.85

    def test_classify_below_min_confidence_returns_fallback(
        self, mock_embedding_result: tuple[TaskType, float]
    ) -> None:
        # Embedding returns CODE with 0.3 (below min)
        with patch.object(
            EmbeddingClassifier,
            "classify",
            return_value=(TaskType.CODE, 0.3),
        ):
            c = PromptClassifier(min_confidence=0.6, low_confidence_fallback=TaskType.GENERAL)
            task, confidence = c.classify("ambiguous prompt")
            assert task == TaskType.GENERAL
            assert confidence == 0.3  # Pass through original confidence

    def test_classify_exactly_at_min_confidence_uses_detected(
        self, mock_embedding_result: tuple[TaskType, float]
    ) -> None:
        with patch.object(
            EmbeddingClassifier,
            "classify",
            return_value=(TaskType.REASONING, 0.6),
        ):
            c = PromptClassifier(min_confidence=0.6)
            task, confidence = c.classify("solve this")
            assert task == TaskType.REASONING
            assert confidence == 0.6

    def test_classify_on_failure_returns_fallback_and_logs(self) -> None:
        with patch.object(
            EmbeddingClassifier,
            "classify",
            side_effect=RuntimeError("model OOM"),
        ):
            c = PromptClassifier(low_confidence_fallback=TaskType.GENERAL)
            task, confidence = c.classify("anything")
            assert task == TaskType.GENERAL
            assert confidence == 0.0

    def test_classify_preserves_import_error(self) -> None:
        from syrin.router.classifier import _CLASSIFIER_IMPORT_ERROR

        with patch(
            "syrin.router.classifier._load_sentence_transformers",
            side_effect=ImportError(_CLASSIFIER_IMPORT_ERROR),
        ):
            c = PromptClassifier()
            with pytest.raises(ImportError) as exc_info:
                c.classify("test")
            assert "classifier-embeddings" in str(exc_info.value)

    def test_warmup_loads_model(self) -> None:
        load_called = []

        def fake_encode(
            self_or_texts: object, texts: object | None = None, **k: object
        ) -> list[list[float]]:
            t_list = texts if texts is not None else self_or_texts
            n = len(t_list) if isinstance(t_list, list) else 1
            return [[0.0] * 384 for _ in range(n)]

        def track_load(*args: object, **kwargs: object) -> object:
            load_called.append(1)
            return type("Mock", (), {"encode": fake_encode})()

        with patch("syrin.router.classifier._load_sentence_transformers", side_effect=track_load):
            c = PromptClassifier()
            c.warmup()
            assert len(load_called) == 1


class TestClassificationResult:
    """ClassificationResult dataclass."""

    def test_create_with_all_fields(self) -> None:
        from syrin.router import ComplexityTier
        from syrin.router.classifier import ClassificationResult as CR

        r = CR(
            task_type=TaskType.CODE,
            confidence=0.85,
            complexity_score=0.6,
            complexity_tier=ComplexityTier.MEDIUM,
            system_alignment_score=0.72,
            used_fallback=False,
            latency_ms=12.5,
        )
        assert r.task_type == TaskType.CODE
        assert r.confidence == 0.85
        assert r.complexity_score == 0.6
        assert r.complexity_tier == ComplexityTier.MEDIUM
        assert r.system_alignment_score == 0.72
        assert r.used_fallback is False
        assert r.latency_ms == 12.5

    def test_create_with_none_system_alignment(self) -> None:
        from syrin.router.classifier import ClassificationResult

        r = ClassificationResult(
            task_type=TaskType.GENERAL,
            confidence=0.5,
            complexity_score=0.1,
            complexity_tier=ComplexityTier.LOW,
            system_alignment_score=None,
            used_fallback=True,
            latency_ms=5.0,
        )
        assert r.system_alignment_score is None


class TestClassifyExtended:
    """PromptClassifier.classify_extended with mocked embedding."""

    def _make_mock_embedding_classifier(
        self,
        task: TaskType = TaskType.CODE,
        confidence: float = 0.8,
        complexity_score: float = 0.5,
        system_alignment: float = 0.7,
    ) -> object:
        dim = 384

        class MockEmb:
            def _ensure_loaded(self) -> None:
                pass

            def classify(self, prompt: str) -> tuple[TaskType, float]:
                return (task, confidence)

            def complexity_score(self, prompt_emb: list[float]) -> float:
                return complexity_score

            def system_alignment_score(
                self, prompt_emb: list[float], system_emb: list[float]
            ) -> float:
                return system_alignment

            _model = type(
                "MockModel",
                (),
                {
                    "encode": lambda _self, texts: [
                        [0.1] * dim for _ in (texts if isinstance(texts, list) else [texts])
                    ]
                },
            )()

        return MockEmb()

    def test_classify_extended_returns_classification_result(self) -> None:
        from syrin.router.classifier import ClassificationResult

        mock_emb = self._make_mock_embedding_classifier(
            task=TaskType.REASONING, confidence=0.9, complexity_score=0.3
        )
        with patch.object(
            PromptClassifier,
            "_get_embedding_classifier",
            return_value=mock_emb,
        ):
            c = PromptClassifier(complexity_use_embedding=True)
            result = c.classify_extended(
                "solve this math problem", system_prompt="You are a math tutor."
            )
            assert isinstance(result, ClassificationResult)
            assert result.task_type == TaskType.REASONING
            assert result.confidence == 0.9
            assert 0.0 <= result.complexity_score <= 1.0
            assert result.complexity_tier in (
                ComplexityTier.LOW,
                ComplexityTier.MEDIUM,
                ComplexityTier.HIGH,
            )
            assert result.system_alignment_score == 0.7
            assert result.used_fallback is False
            assert result.latency_ms >= 0

    def test_classify_extended_without_system_prompt(self) -> None:
        mock_emb = self._make_mock_embedding_classifier()
        with patch.object(
            PromptClassifier,
            "_get_embedding_classifier",
            return_value=mock_emb,
        ):
            c = PromptClassifier(complexity_use_embedding=True)
            result = c.classify_extended("write code")
            assert result.system_alignment_score is None

    def test_classify_extended_low_confidence_uses_fallback(self) -> None:
        mock_emb = self._make_mock_embedding_classifier(
            task=TaskType.CODE, confidence=0.3, complexity_score=0.2
        )
        with patch.object(
            PromptClassifier,
            "_get_embedding_classifier",
            return_value=mock_emb,
        ):
            c = PromptClassifier(
                min_confidence=0.6,
                low_confidence_fallback=TaskType.GENERAL,
                complexity_use_embedding=True,
            )
            result = c.classify_extended("xyz ambiguous")
            assert result.task_type == TaskType.GENERAL
            assert result.used_fallback is True

    def test_classify_extended_complexity_tier_high(self) -> None:
        mock_emb = self._make_mock_embedding_classifier(complexity_score=0.9)
        with patch.object(
            PromptClassifier,
            "_get_embedding_classifier",
            return_value=mock_emb,
        ):
            c = PromptClassifier(complexity_use_embedding=True)
            # Long prompt (>200 chars) + tech words gives heuristic ~0.5; with e=0.9 -> tier HIGH
            long_prompt = (
                "Implement a distributed system with consensus and fault tolerance. "
                "Design the architecture for high availability and scalability. "
                "Prove the following theorem about the protocol correctness. "
                "Refactor the existing codebase to support horizontal scaling."
            )
            result = c.classify_extended(long_prompt)
            assert result.complexity_tier == ComplexityTier.HIGH

    def test_classify_extended_complexity_heuristic_only(self) -> None:
        mock_emb = self._make_mock_embedding_classifier()
        with patch.object(
            PromptClassifier,
            "_get_embedding_classifier",
            return_value=mock_emb,
        ):
            c = PromptClassifier(complexity_use_embedding=False)
            result = c.classify_extended("hi")
            assert result.complexity_tier in (ComplexityTier.LOW, ComplexityTier.MEDIUM)


class TestClassifyExtendedEdgeCases:
    """Edge cases for classify_extended."""

    def _mock_emb(self, task: TaskType = TaskType.GENERAL, confidence: float = 0.8) -> object:
        dim = 384
        mock = type("Mock", (), {})()
        mock._ensure_loaded = lambda: None
        mock.classify = lambda _: (task, confidence)
        mock.complexity_score = lambda _: 0.2
        mock.system_alignment_score = lambda _a, _b: 0.5
        mock._model = type(
            "M",
            (),
            {
                "encode": lambda _s, texts: [
                    [0.0] * dim for _ in (texts if isinstance(texts, list) else [texts])
                ]
            },
        )()
        return mock

    def test_empty_prompt(self) -> None:
        with patch.object(
            PromptClassifier, "_get_embedding_classifier", return_value=self._mock_emb()
        ):
            c = PromptClassifier()
            result = c.classify_extended("")
            assert result.task_type is not None
            assert 0.0 <= result.complexity_score <= 1.0

    def test_whitespace_only_prompt(self) -> None:
        with patch.object(
            PromptClassifier, "_get_embedding_classifier", return_value=self._mock_emb()
        ):
            c = PromptClassifier()
            result = c.classify_extended("   \n\t  ")
            assert result.task_type is not None

    def test_empty_system_prompt_ignored(self) -> None:
        with patch.object(
            PromptClassifier, "_get_embedding_classifier", return_value=self._mock_emb()
        ):
            c = PromptClassifier()
            result = c.classify_extended("hello", system_prompt="")
            assert result.system_alignment_score is None
            result2 = c.classify_extended("hello", system_prompt="   ")
            assert result2.system_alignment_score is None

    def test_very_long_prompt(self) -> None:
        with patch.object(
            PromptClassifier, "_get_embedding_classifier", return_value=self._mock_emb()
        ):
            c = PromptClassifier()
            long_prompt = "x" * 2000
            result = c.classify_extended(long_prompt)
            assert result.complexity_score >= 0.0

    def test_complexity_tier_boundary_low_medium(self) -> None:
        """Score just below 0.33 -> LOW; at 0.33 -> MEDIUM."""
        mock = self._mock_emb()
        mock.complexity_score = lambda _: 0.1
        with patch.object(PromptClassifier, "_get_embedding_classifier", return_value=mock):
            c = PromptClassifier(complexity_use_embedding=True)
            result = c.classify_extended("hi")
            assert result.complexity_tier == ComplexityTier.LOW

    def test_complexity_tier_boundary_medium_high(self) -> None:
        """Score >= 0.66 -> HIGH."""
        mock = self._mock_emb()
        mock.complexity_score = lambda _: 0.95
        with patch.object(PromptClassifier, "_get_embedding_classifier", return_value=mock):
            c = PromptClassifier(complexity_use_embedding=True)
            long_tech = (
                "Implement a distributed system. Design the architecture. "
                "Prove the theorem. " + "x" * 150
            )
            result = c.classify_extended(long_tech)
            assert result.complexity_tier == ComplexityTier.HIGH

    def test_complexity_tier_exactly_at_medium(self) -> None:
        """Score in [0.33, 0.66) -> MEDIUM. Heuristic + embedding -> ~0.4."""
        mock = self._mock_emb()
        mock.complexity_score = lambda _: 0.5
        with patch.object(PromptClassifier, "_get_embedding_classifier", return_value=mock):
            c = PromptClassifier(complexity_use_embedding=True)
            # >200 chars adds 0.2; 0.5*0.2+0.5*0.5=0.35 -> MEDIUM
            med_prompt = "Write a function to process the data. " + "x" * 180
            result = c.classify_extended(med_prompt)
            assert result.complexity_tier == ComplexityTier.MEDIUM


class TestCache:
    """LRU cache for classify."""

    def test_cache_enabled_returns_same_result(self) -> None:
        with patch.object(
            EmbeddingClassifier,
            "classify",
            return_value=(TaskType.CODE, 0.9),
        ):
            c = PromptClassifier(enable_cache=True, max_cache_size=100)
            t1, c1 = c.classify("write a function")
            t2, c2 = c.classify("write a function")
            assert t1 == t2 and c1 == c2

    def test_cache_disabled_calls_classifier_each_time(self) -> None:
        call_count = [0]

        def counting_classify(prompt: str) -> tuple[TaskType, float]:
            call_count[0] += 1
            return (TaskType.GENERAL, 0.8)

        with patch.object(EmbeddingClassifier, "classify", side_effect=counting_classify):
            c = PromptClassifier(enable_cache=False)
            c.classify("hi")
            c.classify("hi")
            assert call_count[0] == 2

    def test_clear_cache_resets(self) -> None:
        with patch.object(
            EmbeddingClassifier,
            "classify",
            return_value=(TaskType.GENERAL, 0.7),
        ):
            c = PromptClassifier(enable_cache=True, max_cache_size=10)
            c.classify("hello")
            c.clear_cache()
            assert len(c._cache) == 0

    def test_max_cache_size_zero_disables_cache(self) -> None:
        with patch.object(EmbeddingClassifier, "classify", return_value=(TaskType.CODE, 0.8)):
            c = PromptClassifier(enable_cache=True, max_cache_size=0)
            c.classify("a")
            c.classify("a")
            assert len(c._cache) == 0


class TestComplexityHeuristic:
    """_complexity_heuristic edge cases."""

    def test_simple_short_prompt(self) -> None:
        from syrin.router.classifier import _complexity_heuristic

        s = _complexity_heuristic("hi")
        assert s < 0.5

    def test_long_technical_prompt(self) -> None:
        from syrin.router.classifier import _complexity_heuristic

        s = _complexity_heuristic(
            "Implement a distributed consensus protocol. Refactor for scalability. "
            "Design the architecture. Prove the theorem." + " x" * 200
        )
        assert s > 0.5

    def test_question_simple(self) -> None:
        from syrin.router.classifier import _complexity_heuristic

        s = _complexity_heuristic("What is the capital of France?")
        assert s < 0.4
