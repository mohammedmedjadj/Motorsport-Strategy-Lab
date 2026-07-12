"""Assemble the per-circuit model inputs the Monte Carlo engine consumes.

Sources (all produced by earlier phases, all committed):

- ``data/derived/degradation_coefficients.csv`` (Phase 2): per-compound
  polynomial coefficients with CIs, fuel slope, CV RMSE (lap noise).
- ``data/derived/sc_model.csv`` + ``sc_events.csv`` (Phase 3): Gamma
  posterior parameters for per-lap SC/VSC rates and observed duration pools.
- ``data/derived/laps_*.csv`` (Phase 1): green pace, pit loss and
  neutralisation pace ratios, measured on the spot by ``pit_loss.py``.

Coefficient uncertainty convention: the CSVs store 95% CIs; standard
deviations are recovered as ``(ci_high - ci_low) / (2 * 1.96)`` so the
engine can resample coefficients per draw.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.ingestion.config import DERIVED_DIR, SEASONS
from src.simulator.pit_loss import (
    PaceRatios,
    PitLossEstimate,
    estimate_pace_ratios,
    estimate_pit_loss,
    green_median_pace,
)

Z95 = 1.96


@dataclass(frozen=True)
class GaussianCoef:
    """A coefficient the engine resamples as Normal(mean, sd)."""

    mean: float
    sd: float


@dataclass(frozen=True)
class HazardPosterior:
    """Gamma posterior for a per-lap deployment rate: Gamma(alpha, 1/beta)."""

    alpha: float
    beta: float  # exposure in laps

    @property
    def mean(self) -> float:
        return self.alpha / self.beta


@dataclass(frozen=True)
class CircuitModel:
    """Everything the engine needs to simulate one circuit."""

    circuit: str
    green_pace_s: float
    lap_noise_s: float
    fuel_slope: GaussianCoef
    degradation: dict[str, tuple[GaussianCoef, ...]]  # compound -> poly coefs
    sc_hazard: HazardPosterior
    vsc_hazard: HazardPosterior
    sc_durations: tuple[int, ...]
    vsc_durations: tuple[int, ...]
    pit_loss: PitLossEstimate
    pace_ratios: PaceRatios


def _gaussian(mean: float, ci_low: float, ci_high: float) -> GaussianCoef:
    return GaussianCoef(mean=float(mean), sd=float((ci_high - ci_low) / (2 * Z95)))


def _load_all_laps() -> dict[str, pd.DataFrame]:
    laps_by_circuit: dict[str, pd.DataFrame] = {}
    for path in sorted(DERIVED_DIR.glob("laps_*.csv")):
        season, circuit = path.stem.removeprefix("laps_").split("_", 1)
        if int(season) not in SEASONS:
            continue
        df = pd.read_csv(path)
        df["race"] = f"{season}_{circuit}"
        laps_by_circuit.setdefault(circuit, []).append(df)
    return {c: pd.concat(fs, ignore_index=True) for c, fs in laps_by_circuit.items()}


def _duration_pool(events: pd.DataFrame, circuit: str, kind: str) -> tuple[int, ...]:
    """Observed durations for one circuit; pooled fallback if < 2 events."""
    own = events[(events["circuit"] == circuit) & (events["kind"] == kind)]
    pool = own if len(own) >= 2 else events[events["kind"] == kind]
    durations = tuple(int(d) for d in pool["duration_laps"])
    if not durations:
        raise ValueError(f"no observed {kind} durations anywhere")
    return durations


def load_circuit_models() -> dict[str, CircuitModel]:
    """Build the full artifact set for every scoped circuit."""
    deg = pd.read_csv(DERIVED_DIR / "degradation_coefficients.csv")
    sc = pd.read_csv(DERIVED_DIR / "sc_model.csv").set_index("circuit")
    events = pd.read_csv(DERIVED_DIR / "sc_events.csv")
    laps_by_circuit = _load_all_laps()
    ratios = estimate_pace_ratios(laps_by_circuit)

    models: dict[str, CircuitModel] = {}
    for circuit, laps in laps_by_circuit.items():
        rows = deg[deg["circuit"] == circuit]
        degradation: dict[str, tuple[GaussianCoef, ...]] = {}
        for _, row in rows.iterrows():
            coefs = [_gaussian(row["deg_p1"], row["deg_p1_ci_low"], row["deg_p1_ci_high"])]
            if row["degree"] >= 2 and pd.notna(row.get("deg_p2")):
                coefs.append(
                    _gaussian(row["deg_p2"], row["deg_p2_ci_low"], row["deg_p2_ci_high"])
                )
            degradation[str(row["compound"])] = tuple(coefs)

        first = rows.iloc[0]
        sc_row = sc.loc[circuit]
        exposure = float(sc_row["laps_exposure"])
        models[circuit] = CircuitModel(
            circuit=circuit,
            green_pace_s=green_median_pace(laps),
            lap_noise_s=float(first["cv_rmse_s"]),
            fuel_slope=_gaussian(
                first["fuel_slope_s_per_lap"],
                first["fuel_slope_ci_low"],
                first["fuel_slope_ci_high"],
            ),
            degradation=degradation,
            sc_hazard=HazardPosterior(
                alpha=float(sc_row["sc_rate_per_lap"]) * exposure, beta=exposure
            ),
            vsc_hazard=HazardPosterior(
                alpha=float(sc_row["vsc_rate_per_lap"]) * exposure, beta=exposure
            ),
            sc_durations=_duration_pool(events, circuit, "SC"),
            vsc_durations=_duration_pool(events, circuit, "VSC"),
            pit_loss=estimate_pit_loss(laps, circuit),
            pace_ratios=ratios[circuit],
        )
    return models
