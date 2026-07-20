"""Series -> loader factory.

Scope note (honest): F1 is *not* routed through ``BaseLoader`` yet. Its
ingestion (``src/ingestion/``) predates this abstraction, is driven by FastF1's
own session objects, and is already covered by the Phase 1 pipeline and its
tests. Wrapping it in an adapter is a follow-up; forcing it now would mean
rewriting working, tested code for symmetry alone. Asking for ``"f1"`` therefore
raises with a pointer rather than silently returning a half-adapter.
"""

from __future__ import annotations

from src.data.base_loader import BaseLoader
from src.data.endurance_loader import SUPPORTED_SERIES, EnduranceLoader


def get_loader(series: str) -> BaseLoader:
    """Return the loader for ``series`` ("imsa", "wec", "elms", "alms")."""
    key = series.lower()
    if key in SUPPORTED_SERIES:
        return EnduranceLoader(key)
    if key == "f1":
        raise NotImplementedError(
            "F1 is loaded by src.ingestion (FastF1), not through BaseLoader; "
            "see src/ingestion/loader.py"
        )
    raise ValueError(f"unknown series {series!r}")
