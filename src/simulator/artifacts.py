"""Assemble the per-circuit model inputs the Monte Carlo engine consumes.

Sources (all produced by earlier phases, all committed):

- ``data/derived/f1/degradation_coefficients.csv`` (Phase 2): per-compound
  polynomial coefficients with CIs, fuel slope, CV RMSE (lap noise).
- ``data/derived/f1/sc_model.csv`` + ``sc_events.csv`` (Phase 3): Gamma
  posterior parameters for per-lap SC/VSC rates and observed duration pools.
- ``data/derived/f1/laps_*.csv`` (Phase 1): green pace, pit loss and
  neutralisation pace ratios, measured on the spot by ``pit_loss.py``.

Coefficient uncertainty convention: the CSVs store 95% CIs; standard
deviations are recovered as ``(ci_high - ci_low) / (2 * 1.96)`` so the
engine can resample coefficients per draw.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd

from src.degradation.robust import t_degrees_of_freedom
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS
from src.simulator.pit_loss import (
    PaceRatios,
    PitLossEstimate,
    estimate_pace_ratios,
    estimate_pit_loss,
    green_median_pace,
)

Z95 = 1.96


@dataclass(frozen=True)
class CoefPosterior:
    """A coefficient the engine resamples per draw.

    ``df`` is the reference distribution's degrees of freedom: ``G - 1`` for a
    cluster-robust estimate on ``G`` driver-races, or ``inf`` when the
    estimate carries no cluster count. It is not decoration — the engine draws
    from ``t(df)``, so an estimate resting on few clusters contributes heavier
    tails to the race-time distribution than one resting on many. With the
    ~55 driver-races per F1 circuit here the t is very close to a normal; the
    machinery matters for the small endurance classes and for any future
    circuit with thin data.
    """

    mean: float
    sd: float
    df: float = float("inf")


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
    fuel_slope: CoefPosterior
    degradation: dict[str, tuple[CoefPosterior, ...]]  # compound -> poly coefs
    sc_hazard: HazardPosterior
    vsc_hazard: HazardPosterior
    sc_durations: tuple[int, ...]
    vsc_durations: tuple[int, ...]
    pit_loss: PitLossEstimate
    pace_ratios: PaceRatios


def _posterior(mean: float, se: float, n_clusters: float) -> CoefPosterior:
    """Build the engine's per-draw coefficient distribution.

    Reads the standard error straight from the artifact rather than
    reconstructing it from the confidence interval. That reconstruction used
    to divide the interval width by ``2 * 1.96``, which silently stopped being
    correct the moment the intervals went cluster-robust and started using a
    ``t(G-1)`` critical value: the recovered "sd" would have been inflated by
    ``t/1.96`` and the degrees of freedom would have been applied twice.
    """
    df = t_degrees_of_freedom(n_clusters if pd.notna(n_clusters) else None)
    return CoefPosterior(mean=float(mean), sd=float(se), df=df)


def _load_all_laps() -> dict[str, pd.DataFrame]:
    """Committed laps per circuit, restricted to the regulation-stable window.

    The simulator's circuit constants (green pace, pit loss, SC/VSC pace
    ratios, lap noise) are consumed by the Phase 5 audit, which replays real
    2023-2024 decisions. Estimating them from ``SEASONS`` -- which rolls into
    the ``REGULATION_ERA_START`` era -- would judge those decisions using data
    from cars that did not exist yet, breaking this project's own no-leakage
    rule, and it visibly moves the numbers (adding 2026 shifted Monaco's
    measured SC pace ratio 1.42 -> 1.17 and its pit loss 19.1s -> 19.7s).
    ``PRE_ERA_SEASONS`` keeps the audit interpretable; new-era races are
    ingested and reported separately (see run_degradation.py's era-transfer
    section) rather than silently folded into constants fit for another era.
    """
    laps_by_circuit: dict[str, pd.DataFrame] = {}
    for path in sorted(F1_DERIVED_DIR.glob("laps_*.csv")):
        season, circuit = path.stem.removeprefix("laps_").split("_", 1)
        if int(season) not in PRE_ERA_SEASONS:
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
    deg = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    sc = pd.read_csv(F1_DERIVED_DIR / "sc_model.csv").set_index("circuit")
    events = pd.read_csv(F1_DERIVED_DIR / "sc_events.csv")
    laps_by_circuit = _load_all_laps()
    ratios = estimate_pace_ratios(laps_by_circuit)

    models: dict[str, CircuitModel] = {}
    unfitted: list[str] = []
    for circuit, laps in laps_by_circuit.items():
        rows = deg[deg["circuit"] == circuit]
        # A circuit whose laps are ingested but whose coefficients have not been
        # refitted yet is a **normal transient state**, not a corrupt artifact:
        # the scope is rolling, so a new round lands on disk before the models
        # are re-run, and widening the scope from four circuits to the whole
        # calendar puts every new circuit in exactly this position for one
        # commit. This used to be an ``IndexError`` from ``rows.iloc[0]`` at
        # import time, which failed test *collection* — the least informative
        # possible symptom for "run scripts/run_degradation.py".
        if rows.empty:
            unfitted.append(circuit)
            continue
        degradation: dict[str, tuple[CoefPosterior, ...]] = {}
        for _, row in rows.iterrows():
            n_clusters = row["n_clusters"]
            coefs = [_posterior(row["deg_p1"], row["deg_p1_se"], n_clusters)]
            if row["degree"] >= 2 and pd.notna(row.get("deg_p2")):
                coefs.append(_posterior(row["deg_p2"], row["deg_p2_se"], n_clusters))
            degradation[str(row["compound"])] = tuple(coefs)

        first = rows.iloc[0]
        sc_row = sc.loc[circuit]
        exposure = float(sc_row["laps_exposure"])
        models[circuit] = CircuitModel(
            circuit=circuit,
            green_pace_s=green_median_pace(laps),
            lap_noise_s=float(first["cv_rmse_s"]),
            fuel_slope=_posterior(
                first["fuel_slope_s_per_lap"],
                first["fuel_slope_se"],
                first["n_clusters"],
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

    if unfitted:
        # Reported, never silent. A caller that gets fewer models than it
        # expected should be told why, and told the one command that fixes it.
        warnings.warn(
            f"{len(unfitted)} circuit(s) have ingested laps but no fitted "
            f"degradation coefficients, so they carry no model: "
            f"{', '.join(sorted(unfitted))}. Run scripts/run_degradation.py.",
            stacklevel=2,
        )
    return models
