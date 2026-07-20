"""Endurance (IMSA / WEC) tyre-degradation model.

Headline specification, fitted per race on green non-pit laps::

    lap_time = a_{car,driver} + n * tyre_age + eps

where ``n`` is the **net within-stint pace slope**: the combined effect of the
car getting lighter (faster) and the tyres going off (slower).

Why only the net slope? A fuel/degradation decomposition was attempted and
**rejected on the evidence**. The plan was that endurance's fuel-only stops
would reset a ``laps_since_refuel`` regressor while leaving ``tyre_age``
untouched, decoupling the two. Measured on the real races, that is not what
teams do: **88% of pit visits at Watkins Glen 2023 and 93% at Spa 2024 include a
tyre change**, so the two regressors move together with a post-fixed-effects
correlation of **+0.99 and +0.95**. Fitting both yields a collinear ridge, not a
measurement — at Watkins Glen it produced a fuel slope of -0.11 s/lap and a
degradation slope of +0.11 s/lap with wide, near-mirror-image intervals that
sum to roughly the observed net of ~0.

The decomposition is therefore reported only as a *diagnostic*
(``fuel_deg_correlation``, ``separable``), never as a headline coefficient. This
is the same discipline the F1 model applies to its own identification, and it is
why the raw slope against tyre age looks near-zero at Watkins Glen: the fuel gain
cancels the tyre loss, and nothing in this data can honestly split them.

Two other departures from the F1 model (``src/degradation/model.py``):

- **Fuel resets.** Endurance cars refuel, so fuel load is not monotone in lap
  number as it is in F1 — hence ``laps_since_refuel`` rather than lap number.
- **Fixed effects are per car *and* driver.** Endurance rotates drivers within a
  car and driver pace differences are large; a car-only intercept would push them
  into the residual.

Traffic is the dominant noise source in multi-class racing (a GTP car stuck
behind GT traffic loses seconds through no fault of its tyres), so slow laps are
trimmed per car before fitting — the endurance analogue of the F1 pace-lap
filter. Estimation is plain OLS via least squares with classical standard
errors, matching the F1 model's conventions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data.endurance_loader import green_lap_times

Z95 = 1.96

#: Laps slower than this quantile of a car's own green laps are treated as
#: traffic-compromised and dropped before fitting.
TRAFFIC_QUANTILE = 0.90

#: A car needs at least this many usable green laps to carry a fixed effect.
MIN_LAPS_PER_CAR = 20

#: A lap NUMBER is excluded field-wide if the median lap time across all cars
#: on that lap exceeds this multiple of the race's overall green median. Found
#: necessary by inspection of IMSA Road America 2024 (a 62-lap sprint): laps 2
#: and 3 are flagged "GF" in the source but are field-wide standing-start/
#: early-caution laps at ~2x green pace (median 246.6s and 197.8s vs a ~113s
#: green median) — a per-car quantile trim cannot catch this because it
#: compromises most of each car's own laps in a short race, pushing each car's
#: own 90th-percentile cutoff up to swallow the anomaly.
FIELD_WIDE_TRIM_RATIO = 1.3


@dataclass(frozen=True)
class Coefficient:
    """One estimated coefficient with its 95% confidence interval."""

    value: float
    se: float

    @property
    def ci_low(self) -> float:
        return self.value - Z95 * self.se

    @property
    def ci_high(self) -> float:
        return self.value + Z95 * self.se


#: Above this post-fixed-effects correlation, fuel and tyre age are treated as
#: not separately identified and only the net slope is reported.
SEPARABILITY_LIMIT = 0.90


@dataclass(frozen=True)
class EnduranceFit:
    """Fitted degradation model for one endurance race.

    ``net_slope`` is the identified quantity. ``fuel_slope``/``deg_slope`` are
    the attempted decomposition and are meaningless unless ``separable`` is
    True — check it before quoting them.
    """

    series: str
    event: str
    car_class: str
    #: Net within-stint pace slope (s per lap of tyre age): fuel gain + tyre loss.
    net_slope: Coefficient
    n_laps: int
    n_cars: int
    n_units: int              # car-driver intercepts
    rmse_s: float
    #: Correlation between the fuel and tyre-age regressors after absorbing the
    #: fixed effects. Near 0 would mean they are separable; in practice ~0.95+.
    fuel_deg_correlation: float
    #: Diagnostic-only decomposition; trustworthy only when ``separable``.
    fuel_slope: Coefficient
    deg_slope: Coefficient

    @property
    def separable(self) -> bool:
        """Whether fuel and tyre wear can be split in this race at all."""
        r = self.fuel_deg_correlation
        return bool(np.isfinite(r) and abs(r) < SEPARABILITY_LIMIT)


def build_endurance_frame(laps: pd.DataFrame) -> pd.DataFrame:
    """Green, non-pit, traffic-trimmed laps with the fuel and tyre regressors.

    Adds ``laps_since_refuel`` (resets at every pit visit) and ``unit`` (the
    car-driver fixed-effect key). Rows missing any modelling input are dropped,
    never imputed.
    """
    work = laps.sort_values(["car", "lap"], kind="stable").copy()
    # A pit visit opens a new fuel stint; the count is the stint index.
    work["fuel_stint"] = work.groupby("car", sort=False)["is_pit_lap"].cumsum()
    work["laps_since_refuel"] = work.groupby(["car", "fuel_stint"], sort=False).cumcount()
    work["unit"] = work["car"].astype(str) + "::" + work["driver"].astype(str)

    green = green_lap_times(work)
    green = green[green["tyre_age"].notna()]
    if green.empty:
        raise ValueError("no usable green laps with tyre age in this race")

    # Field-wide filter FIRST: drop lap numbers where the whole field was slow
    # at once (standing start / an early caution mislabelled green) — this
    # must run before the per-car quantile, because such laps inflate a car's
    # own cutoff and become invisible to it.
    overall_median = float(green["lap_time_s"].median())
    lap_median = green.groupby("lap")["lap_time_s"].transform("median")
    green = green[lap_median <= FIELD_WIDE_TRIM_RATIO * overall_median]

    # Trim remaining traffic-compromised laps per car.
    cutoff = green.groupby("car")["lap_time_s"].transform(
        lambda s: s.quantile(TRAFFIC_QUANTILE)
    )
    green = green[green["lap_time_s"] <= cutoff]

    # Drop cars with too little running to support an intercept.
    counts = green.groupby("car")["lap_time_s"].transform("size")
    green = green[counts >= MIN_LAPS_PER_CAR]
    if green.empty:
        raise ValueError("no car has enough green laps to fit")
    return green


def fit_endurance_degradation(frame: pd.DataFrame) -> EnduranceFit:
    """Fit the car-driver fixed-effects degradation model for one race."""
    if frame.empty:
        raise ValueError("cannot fit an empty frame")

    fe_mat = pd.get_dummies(frame["unit"]).to_numpy(dtype=float)
    fuel = frame["laps_since_refuel"].to_numpy(dtype=float)
    age = frame["tyre_age"].to_numpy(dtype=float)
    y = frame["lap_time_s"].to_numpy(dtype=float)

    def ols(design: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
        resid = y - design @ beta
        dof = max(len(y) - rank, 1)
        s2 = float(resid @ resid) / dof
        se = np.sqrt(np.clip(np.diag(np.linalg.pinv(design.T @ design)) * s2, 0.0, None))
        return beta, se, s2

    # Headline: the identified net within-stint slope.
    beta_net, se_net, sigma2 = ols(np.hstack([fe_mat, age[:, None]]))
    # Diagnostic only: the fuel/degradation split (see module docstring).
    beta_dec, se_dec, _ = ols(np.hstack([fe_mat, fuel[:, None], age[:, None]]))

    # How separable are the two effects here? Correlate them after removing the
    # fixed effects, which is the variation the slopes are actually fitted on.
    resid = {}
    for name, col in (("fuel", fuel), ("age", age)):
        b, *_ = np.linalg.lstsq(fe_mat, col, rcond=None)
        resid[name] = col - fe_mat @ b
    if resid["fuel"].std() > 0 and resid["age"].std() > 0:
        corr = float(np.corrcoef(resid["fuel"], resid["age"])[0, 1])
    else:
        corr = float("nan")

    return EnduranceFit(
        series=str(frame["series"].iloc[0]),
        event=str(frame["event"].iloc[0]),
        car_class=str(frame["car_class"].iloc[0]),
        net_slope=Coefficient(float(beta_net[-1]), float(se_net[-1])),
        n_laps=len(frame),
        n_cars=int(frame["car"].nunique()),
        n_units=int(fe_mat.shape[1]),
        rmse_s=float(np.sqrt(sigma2)),
        fuel_deg_correlation=corr,
        fuel_slope=Coefficient(float(beta_dec[-2]), float(se_dec[-2])),
        deg_slope=Coefficient(float(beta_dec[-1]), float(se_dec[-1])),
    )
