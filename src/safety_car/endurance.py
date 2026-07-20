"""Endurance neutralisation model (IMSA / WEC).

The endurance analogue of the F1 safety-car layer, and it reuses that layer's
estimators unchanged (``occurrence_probability``, ``per_lap_rate``,
``duration_summary`` — Beta-Binomial and Gamma-Poisson with Jeffreys priors).
Only the *event extraction* is new, because the source encodes race control as a
per-lap flag rather than F1's ``TrackStatus`` intervals.

Flag semantics, established empirically over all 96 available races rather than
assumed (see ``reports/endurance_safety_car_phase2.md``):

===== ============================================================
Flag   Meaning
===== ============================================================
GF     Green flag — racing.
FCY    Full Course Yellow. The dominant neutralisation, in both
       series, present in 70 of 96 races.
SF     Safety Car. Appears **only in WEC** (2022-2026), in
       contiguous runs, essentially never adjacent to FCY — WEC
       runs a full Safety Car procedure distinct from FCY.
FF     Finish flag (chequered): median position 1.00 through the
       race. **Not** a neutralisation; excluded.
RF     Red flag. 4 race-laps across 2 races — too rare to model,
       excluded, exactly as the F1 phase excludes red flags.
===== ============================================================

So two neutralisation kinds are modelled, mirroring F1's SC/VSC split:
``FCY`` (both series) and ``SC`` (WEC only).

**Lap indexing caveat.** Cars are spread around the circuit, so "lap N" is not a
single instant. The race-level timeline takes the *modal* flag across all cars
reporting lap N — a race-progress proxy, not a wall-clock reconstruction. Short
neutralisations that never become the modal state on any lap are therefore
invisible to this method; durations are lower bounds in laps, not minutes.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.ingestion.config import DERIVED_DIR
from src.safety_car.model import (
    PosteriorEstimate,
    duration_summary,
    occurrence_probability,
    per_lap_rate,
)

RACE_FLAGS_CSV = DERIVED_DIR / "endurance" / "race_flags.csv"

#: Raw flag token -> modelled neutralisation kind. Anything absent is not a
#: neutralisation (GF = racing, FF = chequered, RF = red flag, too rare).
NEUTRALISATION_FLAGS: dict[str, str] = {"FCY": "FCY", "SF": "SC"}

RACE_KEY = ["series_code", "year", "event", "session_id"]


@dataclass(frozen=True)
class NeutralisationEvent:
    """One contiguous neutralisation period in one race."""

    series: str
    year: int
    event: str
    session_id: int
    kind: str          # "FCY" | "SC"
    start_lap: int
    duration_laps: int


@dataclass(frozen=True)
class NeutralisationModel:
    """Posterior summary for one series and one neutralisation kind."""

    series: str
    kind: str
    n_races: int
    n_races_with_event: int
    n_events: int
    laps_exposure: int
    occurrence: PosteriorEstimate   # P(race has >= 1 event)
    rate_per_lap: PosteriorEstimate  # deployments per race lap
    durations: dict[str, float]


def load_race_flags(path=RACE_FLAGS_CSV) -> pd.DataFrame:
    """Per (race, lap, flag) car-lap counts, as pulled from the source."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not materialised; run scripts/run_endurance_flags.py with network access"
        )
    return pd.read_csv(path)


def race_timeline(flags: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-car flags into one race-level flag per lap (modal flag)."""
    if flags.empty:
        raise ValueError("no flag rows to build a timeline from")
    idx = flags.groupby(RACE_KEY + ["lap"])["car_laps"].idxmax()
    return (
        flags.loc[idx]
        .sort_values(RACE_KEY + ["lap"])
        .reset_index(drop=True)
    )


def extract_events(timeline: pd.DataFrame) -> list[NeutralisationEvent]:
    """Contiguous runs of each neutralisation flag, per race."""
    events: list[NeutralisationEvent] = []
    for (series, year, event, session_id), race in timeline.groupby(RACE_KEY, sort=True):
        race = race.sort_values("lap")
        kinds = race["flags"].map(NEUTRALISATION_FLAGS)
        # A new run starts when the kind changes or laps are not consecutive.
        broke = kinds.ne(kinds.shift(1)) | race["lap"].diff().ne(1)
        run_id = broke.cumsum()
        for _, run in race.groupby(run_id):
            kind = NEUTRALISATION_FLAGS.get(str(run["flags"].iloc[0]))
            if kind is None:
                continue
            events.append(
                NeutralisationEvent(
                    series=str(series), year=int(year), event=str(event),
                    session_id=int(session_id), kind=kind,
                    start_lap=int(run["lap"].iloc[0]),
                    duration_laps=int(len(run)),
                )
            )
    return events


def race_exposure(timeline: pd.DataFrame) -> pd.DataFrame:
    """Laps run per race — the exposure denominator for the rate posterior."""
    return (
        timeline.groupby(RACE_KEY)["lap"]
        .max()
        .reset_index(name="laps")
    )


def fit_neutralisation_models(
    timeline: pd.DataFrame, events: list[NeutralisationEvent]
) -> list[NeutralisationModel]:
    """Posteriors per (series, kind), over every race of that series.

    Races without the event still count in the denominator — that is the whole
    point of the Beta-Binomial: a series where SC never appears must get a low
    probability with an honest interval, not a missing row.
    """
    exposure = race_exposure(timeline)
    models: list[NeutralisationModel] = []
    for series in sorted(timeline["series_code"].unique()):
        series_races = exposure[exposure["series_code"] == series]
        n_races = len(series_races)
        laps = int(series_races["laps"].sum())
        for kind in sorted(set(NEUTRALISATION_FLAGS.values())):
            hits = [e for e in events if e.series == series and e.kind == kind]
            races_with = {(e.event, e.session_id) for e in hits}
            models.append(
                NeutralisationModel(
                    series=series,
                    kind=kind,
                    n_races=n_races,
                    n_races_with_event=len(races_with),
                    n_events=len(hits),
                    laps_exposure=laps,
                    occurrence=occurrence_probability(len(races_with), n_races),
                    rate_per_lap=per_lap_rate(len(hits), laps),
                    durations=duration_summary([e.duration_laps for e in hits]),
                )
            )
    return models
