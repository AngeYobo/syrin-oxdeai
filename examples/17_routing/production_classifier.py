"""Production PromptClassifier — extended classification, complexity, system alignment.

Requires: uv sync --extra classifier-embeddings
Run: uv run python -m examples.17_routing.production_classifier
"""

from __future__ import annotations

from syrin.router import (
    ClassificationResult,
    PromptClassifier,
)


def main() -> None:
    classifier = PromptClassifier(
        min_confidence=0.6,
        enable_cache=True,
        max_cache_size=500,
    )
    classifier.warmup()

    system = "You are a helpful coding assistant. Answer concisely."

    prompts = [
        "Hello",
        "Implement quicksort in Python",
        "Design a distributed consensus protocol for a fault-tolerant key-value store",
    ]

    print("Extended classification (complexity + system alignment)\n")
    for p in prompts:
        r: ClassificationResult = classifier.classify_extended(p, system)
        print(f"  {p[:60]!r}")
        print(f"    task={r.task_type.value} conf={r.confidence:.2f}")
        print(f"    complexity={r.complexity_tier.value} ({r.complexity_score:.2f})")
        print(
            f"    system_alignment={r.system_alignment_score:.2f}"
            if r.system_alignment_score is not None
            else "    system_alignment=N/A"
        )
        print(f"    latency={r.latency_ms:.0f}ms")
        print()


if __name__ == "__main__":
    main()
