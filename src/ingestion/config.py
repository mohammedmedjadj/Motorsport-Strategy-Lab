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
_FIRST_SEASON = 2022
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

#: The F1 core scope: **every round of every season from 2022**, each mapped to
#: a stable circuit slug used in derived file names and in model grouping.
#:
#: This replaced a four-circuit scope. That scope was a Phase 0 MVP decision and
#: it had quietly become the project's largest inconsistency: four circuits
#: received the full treatment — per-compound degradation with cluster-robust
#: intervals, a neutralisation posterior, track position, the simulator, the
#: decision audits — while the 35 circuits of the Kaggle breadth layer received
#: two numbers each. Nothing technical justified the gap. A round costs about
#: 40 seconds to fetch once and is cached afterwards.
#:
#: **Frozen in code rather than read from FastF1's schedule at import time.** A
#: scope that changes because an upstream calendar was revised is not a scope,
#: and every derived file name depends on this mapping. ``tests/test_f1_scope.py``
#: compares it against the live schedule and fails when they diverge, so a real
#: calendar change arrives as a failing test and a deliberate edit here.
#:
#: **Keyed per season, not per event name.** The Spanish Grand Prix ran at
#: Barcelona through 2025 and moves to **Madrid** in 2026, while Barcelona keeps
#: a round of its own under a new name. A season-blind event->circuit map would
#: have filed Madrid's race under ``barcelona`` — a different track, same key,
#: no error — and the old four-circuit scope was one round away from doing
#: exactly that.
_SEASON_EVENTS: dict[int, tuple[tuple[str, str], ...]] = {
    2022: (
        ("Bahrain Grand Prix", "bahrain"),
        ("Saudi Arabian Grand Prix", "jeddah"),
        ("Australian Grand Prix", "melbourne"),
        ("Emilia Romagna Grand Prix", "imola"),
        ("Miami Grand Prix", "miami"),
        ("Spanish Grand Prix", "barcelona"),
        ("Monaco Grand Prix", "monaco"),
        ("Azerbaijan Grand Prix", "baku"),
        ("Canadian Grand Prix", "montreal"),
        ("British Grand Prix", "silverstone"),
        ("Austrian Grand Prix", "red_bull_ring"),
        ("French Grand Prix", "ricard"),
        ("Hungarian Grand Prix", "hungaroring"),
        ("Belgian Grand Prix", "spa"),
        ("Dutch Grand Prix", "zandvoort"),
        ("Italian Grand Prix", "monza"),
        ("Singapore Grand Prix", "singapore"),
        ("Japanese Grand Prix", "suzuka"),
        ("United States Grand Prix", "austin"),
        ("Mexico City Grand Prix", "mexico_city"),
        ("São Paulo Grand Prix", "interlagos"),
        ("Abu Dhabi Grand Prix", "yas_marina"),
    ),
    2023: (
        ("Bahrain Grand Prix", "bahrain"),
        ("Saudi Arabian Grand Prix", "jeddah"),
        ("Australian Grand Prix", "melbourne"),
        ("Azerbaijan Grand Prix", "baku"),
        ("Miami Grand Prix", "miami"),
        ("Monaco Grand Prix", "monaco"),
        ("Spanish Grand Prix", "barcelona"),
        ("Canadian Grand Prix", "montreal"),
        ("Austrian Grand Prix", "red_bull_ring"),
        ("British Grand Prix", "silverstone"),
        ("Hungarian Grand Prix", "hungaroring"),
        ("Belgian Grand Prix", "spa"),
        ("Dutch Grand Prix", "zandvoort"),
        ("Italian Grand Prix", "monza"),
        ("Singapore Grand Prix", "singapore"),
        ("Japanese Grand Prix", "suzuka"),
        ("Qatar Grand Prix", "losail"),
        ("United States Grand Prix", "austin"),
        ("Mexico City Grand Prix", "mexico_city"),
        ("São Paulo Grand Prix", "interlagos"),
        ("Las Vegas Grand Prix", "las_vegas"),
        ("Abu Dhabi Grand Prix", "yas_marina"),
    ),
    2024: (
        ("Bahrain Grand Prix", "bahrain"),
        ("Saudi Arabian Grand Prix", "jeddah"),
        ("Australian Grand Prix", "melbourne"),
        ("Japanese Grand Prix", "suzuka"),
        ("Chinese Grand Prix", "shanghai"),
        ("Miami Grand Prix", "miami"),
        ("Emilia Romagna Grand Prix", "imola"),
        ("Monaco Grand Prix", "monaco"),
        ("Canadian Grand Prix", "montreal"),
        ("Spanish Grand Prix", "barcelona"),
        ("Austrian Grand Prix", "red_bull_ring"),
        ("British Grand Prix", "silverstone"),
        ("Hungarian Grand Prix", "hungaroring"),
        ("Belgian Grand Prix", "spa"),
        ("Dutch Grand Prix", "zandvoort"),
        ("Italian Grand Prix", "monza"),
        ("Azerbaijan Grand Prix", "baku"),
        ("Singapore Grand Prix", "singapore"),
        ("United States Grand Prix", "austin"),
        ("Mexico City Grand Prix", "mexico_city"),
        ("São Paulo Grand Prix", "interlagos"),
        ("Las Vegas Grand Prix", "las_vegas"),
        ("Qatar Grand Prix", "losail"),
        ("Abu Dhabi Grand Prix", "yas_marina"),
    ),
    2025: (
        ("Australian Grand Prix", "melbourne"),
        ("Chinese Grand Prix", "shanghai"),
        ("Japanese Grand Prix", "suzuka"),
        ("Bahrain Grand Prix", "bahrain"),
        ("Saudi Arabian Grand Prix", "jeddah"),
        ("Miami Grand Prix", "miami"),
        ("Emilia Romagna Grand Prix", "imola"),
        ("Monaco Grand Prix", "monaco"),
        ("Spanish Grand Prix", "barcelona"),
        ("Canadian Grand Prix", "montreal"),
        ("Austrian Grand Prix", "red_bull_ring"),
        ("British Grand Prix", "silverstone"),
        ("Belgian Grand Prix", "spa"),
        ("Hungarian Grand Prix", "hungaroring"),
        ("Dutch Grand Prix", "zandvoort"),
        ("Italian Grand Prix", "monza"),
        ("Azerbaijan Grand Prix", "baku"),
        ("Singapore Grand Prix", "singapore"),
        ("United States Grand Prix", "austin"),
        ("Mexico City Grand Prix", "mexico_city"),
        ("São Paulo Grand Prix", "interlagos"),
        ("Las Vegas Grand Prix", "las_vegas"),
        ("Qatar Grand Prix", "losail"),
        ("Abu Dhabi Grand Prix", "yas_marina"),
    ),
    2026: (
        ("Australian Grand Prix", "melbourne"),
        ("Chinese Grand Prix", "shanghai"),
        ("Japanese Grand Prix", "suzuka"),
        ("Miami Grand Prix", "miami"),
        ("Canadian Grand Prix", "montreal"),
        ("Monaco Grand Prix", "monaco"),
        ("Barcelona Grand Prix", "barcelona"),
        ("Austrian Grand Prix", "red_bull_ring"),
        ("British Grand Prix", "silverstone"),
        ("Belgian Grand Prix", "spa"),
        ("Hungarian Grand Prix", "hungaroring"),
        ("Dutch Grand Prix", "zandvoort"),
        ("Italian Grand Prix", "monza"),
        ("Spanish Grand Prix", "madrid"),
        ("Azerbaijan Grand Prix", "baku"),
        ("Bahrain Grand Prix", "bahrain"),
        ("Singapore Grand Prix", "singapore"),
        ("United States Grand Prix", "austin"),
        ("Mexico City Grand Prix", "mexico_city"),
        ("São Paulo Grand Prix", "interlagos"),
        ("Las Vegas Grand Prix", "las_vegas"),
        ("Qatar Grand Prix", "losail"),
        ("Abu Dhabi Grand Prix", "yas_marina"),
    ),
}

RACES: tuple[RaceId, ...] = tuple(
    RaceId(season=season, gp_name=gp, circuit=circuit)
    for season in SEASONS
    for gp, circuit in _SEASON_EVENTS.get(season, ())
)

#: Every circuit slug in the core scope, sorted. The unit models group on.
CIRCUITS: tuple[str, ...] = tuple(
    sorted({circuit for events in _SEASON_EVENTS.values() for _, circuit in events})
)

#: Core slug -> the Kaggle breadth layer's circuit reference, where they differ.
#: The two layers measure the same net slope from independent sources, so
#: joining them is a genuine cross-check rather than bookkeeping — but only if
#: the keys line up, and they were chosen years apart. Absent here means the two
#: layers already agree on the slug (``monaco``, ``monza``, ``spa``, ...).
BREADTH_CIRCUIT_ALIASES: dict[str, str] = {
    "barcelona": "catalunya",
    "singapore": "marina_bay",
    "melbourne": "albert_park",
    "austin": "americas",
    "montreal": "villeneuve",
    "mexico_city": "rodriguez",
    "las_vegas": "vegas",
}


def breadth_key(circuit: str) -> str:
    """The Kaggle breadth layer's name for a core circuit slug."""
    return BREADTH_CIRCUIT_ALIASES.get(circuit, circuit)
