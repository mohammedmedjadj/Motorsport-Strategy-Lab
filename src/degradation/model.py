"""Fixed-effects OLS degradation model.

Specification, fitted per circuit on the pooled seasons::

    lap_time = a_{driver,race} + f * lap_number + sum_c d_c(tyre_life) + eps

- ``a_{driver,race}``: one intercept per driver per race, absorbing car pace,
  driver pace and race-day conditions.
- ``f * lap_number``: fuel-burn proxy (cars get lighter as the race runs).
- ``d_c``: per-compound degradation polynomial in tyre age (degree 1 or 2).

Identification note: within a single stint, tyre age and lap number advance
together (collinear). Fuel and degradation are separable only because
different stints start at different lap numbers with fresh tyres. This is
also why the fixed effect is per driver-race, NOT per stint — stint-level
intercepts would destroy that identification.

Estimation is plain OLS via least squares; standard errors use the classical
homoscedastic formula (limitation documented in the Phase 2 report).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

Z95 = 1.96  # normal approximation, n is in the thousands


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


@dataclass(frozen=True)
class FitResult:
    """Fitted degradation model for one circuit."""

    circuit: str
    degree: int
    fuel_slope: Coefficient  # seconds per race lap (fuel-burn proxy)
    deg_coefs: dict[str, tuple[Coefficient, ...]]  # compound -> poly coefs
    fixed_effects: dict[str, float]  # driver_race -> intercept
    n_laps: int
    n_stints: int
    r2_overall: float  # inflated by fixed effects; CV within-stint R2 is the honest metric

    def degradation_delta(self, compound: str, tyre_life: np.ndarray) -> np.ndarray:
        """Degradation-attributable lap-time delta (s) at given tyre ages."""
        coefs = self.deg_coefs[compound]
        out = np.zeros_like(np.asarray(tyre_life, dtype=float))
        for power, coef in enumerate(coefs, start=1):
            out += coef.value * np.asarray(tyre_life, dtype=float) ** power
        return out


def _design_matrix(
    df: pd.DataFrame, compounds: tuple[str, ...], degree: int
) -> tuple[np.ndarray, list[str]]:
    """Build [driver-race dummies | lap_number | per-compound tyre-age powers]."""
    fe = pd.get_dummies(df["driver_race"])
    parts = [fe.to_numpy(dtype=float)]
    names = [f"fe::{c}" for c in fe.columns]

    parts.append(df["LapNumber"].to_numpy(dtype=float)[:, None])
    names.append("fuel::lap_number")

    tyre_life = df["TyreLife"].to_numpy(dtype=float)
    for compound in compounds:
        mask = (df["Compound"] == compound).to_numpy(dtype=float)
        for power in range(1, degree + 1):
            parts.append((mask * tyre_life**power)[:, None])
            names.append(f"deg::{compound}::p{power}")
    return np.hstack(parts), names


def fit_circuit(df: pd.DataFrame, circuit: str, degree: int = 1) -> FitResult:
    """Fit the fixed-effects degradation model for one circuit."""
    compounds = tuple(sorted(df["Compound"].unique()))
    X, names = _design_matrix(df, compounds, degree)
    y = df["lap_time_s"].to_numpy(dtype=float)

    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ beta
    dof = max(len(y) - rank, 1)
    sigma2 = float(residuals @ residuals) / dof
    # pinv tolerates rank deficiency (e.g. a driver-race seen on one compound only)
    se = np.sqrt(np.clip(np.diag(np.linalg.pinv(X.T @ X)) * sigma2, 0.0, None))

    by_name = {n: Coefficient(float(b), float(s)) for n, b, s in zip(names, beta, se)}
    deg_coefs = {
        c: tuple(by_name[f"deg::{c}::p{p}"] for p in range(1, degree + 1))
        for c in compounds
    }
    fixed_effects = {
        n.removeprefix("fe::"): float(by_name[n].value) for n in names if n.startswith("fe::")
    }
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(residuals @ residuals) / ss_tot if ss_tot > 0 else 0.0

    return FitResult(
        circuit=circuit,
        degree=degree,
        fuel_slope=by_name["fuel::lap_number"],
        deg_coefs=deg_coefs,
        fixed_effects=fixed_effects,
        n_laps=len(df),
        n_stints=df["stint_id"].nunique(),
        r2_overall=r2,
    )


def predict_shape(fit: FitResult, df: pd.DataFrame) -> pd.Series:
    """Predict the intercept-free lap-time shape: fuel + degradation terms.

    Used for cross-validation on unseen races, where driver-race intercepts
    are unknown by construction. Laps on compounds absent from the fit get
    NaN (counted and reported by the caller, never silently filled).
    """
    tyre_life = df["TyreLife"].to_numpy(dtype=float)
    out = fit.fuel_slope.value * df["LapNumber"].to_numpy(dtype=float)
    result = pd.Series(out, index=df.index, dtype=float)
    known = df["Compound"].isin(fit.deg_coefs.keys())
    for compound in fit.deg_coefs:
        mask = (df["Compound"] == compound).to_numpy()
        if mask.any():
            result[mask] += fit.degradation_delta(compound, tyre_life[mask])
    result[~known.to_numpy()] = np.nan
    return result
