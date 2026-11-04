"""Evaluation variants for ablation studies."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.kb.store import KnowledgeBase, load_kb
from app.kg.enrich import enrich
from app.postprocess import postprocess

VariantFn = Callable[[Any, str], Any]

_KB_CACHE: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase | None:
    """Return the cached KnowledgeBase loaded lazily from CSV seed files."""
    global _KB_CACHE
    if _KB_CACHE is None:
        seed_dir = Path(__file__).resolve().parent.parent / "kb" / "seed"
        _KB_CACHE = load_kb(None, seed_dir)
    return _KB_CACHE


def _variant_c(data: Any, cv: str) -> Any:
    if not isinstance(data, dict):
        return data
    b, stats = postprocess(data, cv)
    kb = get_kb()
    return enrich(b, kb, stats)


VARIANT_ORDER: tuple[str, ...] = ("A", "B", "C")

VARIANTS: dict[str, VariantFn] = {
    "A": lambda data, cv: data,
    "B": lambda data, cv: postprocess(data, cv)[0] if isinstance(data, dict) else data,
    "C": _variant_c,
}

