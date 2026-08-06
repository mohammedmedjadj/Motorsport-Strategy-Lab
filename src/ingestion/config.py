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

#: First season of the new F1 regulation era (power unit, active aero + Manual
#: Override Mode, lighter/narrower cars, less fuel, narrower tyres). Ingestion
#: is deliberately era-blind -- a 2026 race is data like any other and is
#: collected the same way -- but any model whose *coefficients* describe car or
#: tyre behaviour must not pool across this boundary without saying so, since a
#: single fitted slope spanning it describes neither era. Measured, not
#: assumed: pooling 2026 into Suzuka's fit halves its tyre-age slope (HARD
#: +0.131 -> +0.066 s/lap) and flips the cross-validated degree selection, which
#: is what prompted this split. Circuit *geometry* is unaffected by a
#: regulation change, so the safety-car layer deliberately does not use this
#: boundary (see scripts/run_safety_car.py's own window). This constant is
#: **F1-only** on purpose: WEC's HYPERCAR and IMSA's GTP rulesets run
#: continuously through this window with no comparable reset, so the endurance
#: scope (src/data/endurance_scope.py) pools its own 2026 races normally. The
#: boundary marks a real discontinuity in one series, not a project-wide
#: policy of distrusting recent data.
REGULATION_ERA_START = 2026
#: The regulation-stable window the reported degradation coefficients are fit on.
PRE_ERA_SEASONS: tuple[int, ...] = tuple(s for s in SEASONS if s < REGULATION_ERA_START)
#: Seasons in the new era, kept separate and used as a held-out transfer test.
ERA_SEASONS: tuple[int, ...] = tuple(s for s in SEASONS if s >= REGULATION_ERA_START)

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
