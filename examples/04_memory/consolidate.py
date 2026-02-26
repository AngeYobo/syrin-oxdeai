"""Consolidate Example — Memory consolidation concepts.

Demonstrates:
- Memory consolidation: deduplicate by content
- Memory.consolidate(deduplicate=True)
- Keeps highest-importance entry when duplicates found

Run: python -m examples.04_memory.consolidate
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from syrin import Memory, MemoryType

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


mem = Memory()
mem.remember("User asked about ML at 2pm", memory_type=MemoryType.EPISODIC, importance=0.5)
mem.remember("User asked about ML at 2pm", memory_type=MemoryType.EPISODIC, importance=0.9)
mem.remember("User asked about ML at 2pm", memory_type=MemoryType.EPISODIC, importance=0.3)
removed = mem.consolidate(deduplicate=True)
print(f"Consolidated: removed {removed} duplicate(s).")
