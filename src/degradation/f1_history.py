"""Net tyre-degradation slopes across the *whole* F1 calendar, from the Kaggle
per-lap history — the breadth complement to the FastF1 model's four circuits.

Same "net slope" definition as everywhere else in this project
(``lap_time = a_{driver,stint} + n * tyre_age``, fuel-burn and tyre-loss
combined), fitted per race with driver-and-stint fixed effects removed by
demeaning. Two honest filters stand in for the signals Kaggle lacks:

* **No per-lap Safety-Car / VSC flag** → inferred, not ignored: any lap *number*
  whose median across the whole field exceeds ``FIELD_SLOW_FACTOR`` x the race's
  green median is dropped (a field-wide slow lap is a neutralisation, formation
  or red-flag lap). This is the same field-wide filter the endurance model uses
  for standing starts.
* **No tyre compound** → stints are segmented by pit stop only, so a slope is the
  net across whatever compounds ran; reported as such, never split.

Slopes are only ever compared *within* a regulation era (see
``f1_history_loader.regulation_era``); the artifact carries the era so pooling
across a rules boundary — 2026 above all — cannot happen by accident.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: A lap whose field-median time exceeds this multiple of the race green median
#: is treated as neutralised / non-representative and dropped.
FIELD_SLOW_FACTOR = 1.3
#: Per-driver-stint upper trim: drop each stint's slowest laps (traffic, in/out,
#: an SC the field filter missed) before fitting.
STINT_KEEP_QUANTILE = 0.85
#: Minimum green laps left after filtering for a race to yield a slope.
MIN_FIT_LAPS = 50
#: Above this |correlation| between tyre_age and absolute lap, the two-regressor
#: decoupling is variance-inflated to the point of being unreliable (few stints,
#: so age and race lap track each other) — report tyre/fuel NaN rather than an
#: unstable number. 0.90 => variance inflation factor ~5; anything higher (e.g.
#: Monaco 2024 at 1.00) produced physically absurd tyre slopes and is dropped.
SEPARABLE_CORR_MAX = 0.90


@dataclass(frozen=True)
class RaceSlope:
    circuit: str
    year: int
    era: str
    net_slope_s: float        # tyre + fuel + evolution combined (single regressor)
    tyre_slope_s: float       # tyre wear isolated (NaN if the race can't decouple)
    fuel_evo_slope_s: float   # fuel burn + track evolution, the whole-race trend
    n_laps: int
    rmse_s: float


def _green_laps(race: pd.DataFrame) -> pd.DataFrame:
    """Drop field-wide slow laps (neutralisations inferred without a flag) and
    then each driver-stint's slowest tail."""
    green_median = race["lap_time_s"].median()
    field_by_lap = race.groupby("lap")["lap_time_s"].transform("median")
    race = race[field_by_lap <= FIELD_SLOW_FACTOR * green_median]
    keep = race.groupby(["driverId", "stint"])["lap_time_s"].transform(
        lambda s: s <= s.quantile(STINT_KEEP_QUANTILE))
    return race[keep & (race["tyre_age"] > 0)]


def _fit_slope(race: pd.DataFrame) -> tuple[float, float, float, int, float] | None:
    """Fit a race. Returns ``(net, tyre, fuel_evo, n_laps, rmse)`` where:

    * ``net`` is the single-regressor slope (tyre + fuel + evolution combined),
      via within-(driver, stint) demeaning — the value comparable to the
      endurance model's net slope.
    * ``tyre`` / ``fuel_evo`` come from the two-regressor decoupling
      ``lap_time ~ driver_FE + tyre*tyre_age + fuel_evo*lap``. Because F1 has no
      refuelling since 2010, fuel mass is a whole-race function of the absolute
      lap, while tyre_age resets each stint — so the two are separable (they are
      *not* in endurance, where every stop refuels). Both are ``nan`` when a race
      is a single stint / too collinear to identify them.
    """
    g = _green_laps(race)
    if len(g) < MIN_FIT_LAPS:
        return None
    y = g["lap_time_s"] - g.groupby(["driverId", "stint"])["lap_time_s"].transform("mean")
    x = g["tyre_age"] - g.groupby(["driverId", "stint"])["tyre_age"].transform("mean")
    denom = float((x * x).sum())
    if denom <= 0:
        return None
    net = float((x * y).sum() / denom)
    rmse = float(np.sqrt(((y - net * x) ** 2).mean()))

    tyre = fuel_evo = float("nan")
    gd = g.copy()
    for col in ("lap_time_s", "tyre_age", "lap"):
        gd[col + "_d"] = gd[col] - gd.groupby("driverId")[col].transform("mean")
    ta, lp = gd["tyre_age_d"].to_numpy(), gd["lap_d"].to_numpy()
    if ta.std() > 0 and lp.std() > 0 and abs(np.corrcoef(ta, lp)[0, 1]) < SEPARABLE_CORR_MAX:
        beta, *_ = np.linalg.lstsq(np.column_stack([ta, lp]),
                                   gd["lap_time_s_d"].to_numpy(), rcond=None)
        tyre, fuel_evo = float(beta[0]), float(beta[1])
    return net, tyre, fuel_evo, len(g), rmse


def fit_history_degradation(df: pd.DataFrame,
                            exclude: set[tuple[str, int]] | None = None) -> pd.DataFrame:
    """One row per (circuit, season) across the whole calendar, each carrying the
    net slope and its tyre / fuel-evolution decomposition.

    ``df`` is the output of ``load_f1_lap_history``. Races too short or too
    neutralised to fit are skipped, not forced. ``exclude`` is a set of
    ``(circuitRef, year)`` to drop — pass the weather layer's wet races so a
    wet-to-dry track (Monaco 2022) is never read as tyre wear. Sorted
    steepest-tyre-wear first within era (net slope where tyre is undecidable)."""
    exclude = exclude or set()
    rows: list[RaceSlope] = []
    for (circuit, year), race in df.groupby(["circuitRef", "year"]):
        if (circuit, int(year)) in exclude:
            continue
        fit = _fit_slope(race)
        if fit is None:
            continue
        net, tyre, fuel_evo, n, rmse = fit
        rows.append(RaceSlope(
            str(circuit), int(year), race["era"].iloc[0], round(net, 4),
            round(tyre, 4) if tyre == tyre else float("nan"),
            round(fuel_evo, 4) if fuel_evo == fuel_evo else float("nan"),
            n, round(rmse, 3)))
    out = pd.DataFrame(r.__dict__ for r in rows)
    return out.sort_values(["era", "net_slope_s"], ascending=[True, False]).reset_index(drop=True)
