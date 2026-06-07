"""Format adapters. v0.1 ships auto-memory; mneme follows in W2."""

from .auto_memory import AutoMemoryAdapter

ADAPTERS = {
    "auto-memory": AutoMemoryAdapter,
}


def get_adapter(name: str):
    if name not in ADAPTERS:
        raise ValueError(f"unknown format '{name}'. available: {', '.join(ADAPTERS)}")
    return ADAPTERS[name]()


def detect_format(root: str) -> str:
    """Pick an adapter for a directory. v0.1: only auto-memory, so always that."""
    return "auto-memory"
