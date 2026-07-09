"""Project data scope and filesystem layout.

Single source of truth for which races the MVP covers (frozen in Phase 0
after verifying real FastF1 availability — see
``reports/data_availability_phase0.md``) and where data lives on disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache"
DERIVED_DIR = REPO_ROOT / "data" / "derived"
REPORTS_DIR = REPO_ROOT / "reports"


@dataclass(frozen=True)
class RaceId:
    """Identifies one race in the project scope.

    ``gp_name`` is the fuzzy-matchable FastF1 event name; ``circuit`` is the
    short stable key used in derived file names and model grouping.
    """

    season: int
    gp_name: str
    circuit: str

    @property
    def slug(self) -> str:
        """Stable file-name fragment, e.g. ``2024_monaco``."""
        return f"{self.season}_{self.circuit}"


#: MVP scope: 4 contrasted circuits x 3 seasons (2023-2025), all verified
#: to load with laps + TrackStatus + weather in Phase 0.
SEASONS: tuple[int, ...] = (2023, 2024, 2025)

_CIRCUITS: tuple[tuple[str, str], ...] = (
    ("Monaco", "monaco"),
    ("Singapore", "singapore"),
    ("Spanish", "barcelona"),
    ("Japanese", "suzuka"),
)

RACES: tuple[RaceId, ...] = tuple(
    RaceId(season=season, gp_name=gp, circuit=circuit)
    for season in SEASONS
    for gp, circuit in _CIRCUITS
)
