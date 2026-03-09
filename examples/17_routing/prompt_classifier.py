"""PromptClassifier — embedding-based task type detection.

Requires: uv pip install syrin[classifier-embeddings]
"""

from syrin.router import PromptClassifier, TaskType


def main() -> None:
    classifier = PromptClassifier(
        min_confidence=0.6,
        low_confidence_fallback=TaskType.GENERAL,
    )

    prompts = [
        "write a Python function to sort a list",
        "what is the weather today?",
        "describe this image",
        "solve this math problem: 2+2",
        "hello",
    ]

    for p in prompts:
        task, conf = classifier.classify(p)
        print(f"  {p!r}")
        print(f"    -> {task.value} (confidence={conf:.2f})")


if __name__ == "__main__":
    main()
