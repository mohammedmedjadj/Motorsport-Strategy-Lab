"""Project data scope and filesystem layout.

Single source of truth for which races the MVP covers (frozen in Phase 0
after verifying real FastF1 availability — see
``reports/data_availability_phase0.md``) and where data lives on disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache"
DERIVED_DIR = REPO_ROOT / "data" / "derived"
#: Derived data is partitioned by series so the three pipelines never collide.
F1_DERIVED_DIR = DERIVED_DIR / "f1"
ENDURANCE_DERIVED_DIR = DERIVED_DIR / "endurance"  # cross-series endurance data
PREDICTION_DERIVED_DIR = DERIVED_DIR / "prediction"  # cross-series calibration backtests
REPORTS_DIR = REPO_ROOT / "reports"
#: Reports are partitioned by series, mirroring the derived-data layout.
F1_REPORTS_DIR = REPORTS_DIR / "f1"
IMSA_REPORTS_DIR = REPORTS_DIR / "imsa"
WEC_REPORTS_DIR = REPORTS_DIR / "wec"
PREDICTION_REPORTS_DIR = REPORTS_DIR / "prediction"  # the cross-series calibration write-up


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


#: Data scope: 4 contrasted circuits (below) x every season from 2023 to the
#: current year. The scope is **rolling**: it automatically extends to the live
#: season so the scheduled refresh (see .github/workflows/post-race-refresh.yml)
#: picks up new rounds as they are run. The current season is usually partial —
#: its later rounds have not happened yet — and ``pipeline.run_all`` skips any
#: round FastF1 cannot yet load rather than failing. 2023-2025 were verified in
#: Phase 0; earlier seasons stay out (2022 = porpoising-era noise; pre-2022 =
#: different regulations).
_FIRST_SEASON = 2023
SEASONS: tuple[int, ...] = tuple(range(_FIRST_SEASON, date.today().year + 1))

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
