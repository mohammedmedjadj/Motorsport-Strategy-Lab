"""Gaussian-process degradation curve — a nonparametric alternative to the
fixed-effects OLS model, benchmarked honestly on the *same* leave-one-race-out
within-stint metric.

Motivation (from the improvement plan): OLS assumes the degradation shape is a
low-degree polynomial. A GP relaxes that — it learns the tyre-age curve without
committing to a functional form, and reports uncertainty on the *function*.

Why this reduces to a clean 1-D problem. The cross-validation scores the
*within-stint shape*: both actual and predicted lap times are demeaned per
stint before scoring (see ``validation.py``). Within one stint tyre age and lap
number advance together, so the demeaned OLS prediction collapses to a single
slope in tyre age (fuel + degradation combined). We therefore fit the GP to the
same demeaned quantity — lap-time deviation from the stint mean as a function of
tyre age, per compound — and score it identically. Demeaning per stint in
training also strips the per-stint fuel level, so what remains is the shared
within-stint shape the simulator actually consumes.

Aggregating the deviations by integer tyre age gives ~30-40 points per compound,
so the GP is an exact (not sparse) fit: no O(n^3) blow-up over thousands of laps.

Kernel: RBF + heteroscedastic observation noise (each aggregated point is a mean
of ``count`` laps, so its variance is the pooled residual variance / count).
Hyperparameters (length scale, signal variance) are fitted by maximising the log
marginal likelihood. Everything uses scipy/numpy — no new dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

_JITTER = 1e-8


def _rbf(xa: np.ndarray, xb: np.ndarray, ell: float, sig: float) -> np.ndarray:
    d2 = (xa[:, None] - xb[None, :]) ** 2
    return sig * np.exp(-0.5 * d2 / (ell * ell))


@dataclass(frozen=True)
class _CompoundGP:
    """Posterior of one compound's degradation curve, ready to predict."""

    x_train: np.ndarray       # aggregated tyre ages
    alpha: np.ndarray         # (K + noise)^-1 y
    ell: float
    sig: float

    def predict(self, ages: np.ndarray) -> np.ndarray:
        k = _rbf(np.asarray(ages, dtype=float), self.x_train, self.ell, self.sig)
        return k @ self.alpha


@dataclass(frozen=True)
class GPFit:
    """Fitted GP degradation model for one circuit (per-compound curves)."""

    circuit: str
    curves: dict[str, _CompoundGP]


def _fit_one(x: np.ndarray, y: np.ndarray, noise: np.ndarray) -> _CompoundGP:
    """Fit RBF hyperparameters by max log marginal likelihood, return posterior."""
    y = y - y.mean()  # curve is only identified up to a constant (eval demeans)
    span = float(x.max() - x.min()) or 1.0
    y_var = float(np.var(y)) or 1.0

    def neg_lml(theta: np.ndarray) -> float:
        ell, sig = np.exp(theta)
        K = _rbf(x, x, ell, sig) + np.diag(noise) + _JITTER * np.eye(len(x))
        try:
            c, low = cho_factor(K)
        except np.linalg.LinAlgError:
            return 1e12
        a = cho_solve((c, low), y)
        logdet = 2.0 * np.sum(np.log(np.diag(c)))
        return float(0.5 * (y @ a) + 0.5 * logdet)

    theta0 = np.log([span / 3.0, y_var])
    bounds = [(np.log(span / 50.0), np.log(span * 2.0)), (np.log(y_var / 100.0), np.log(y_var * 100.0))]
    res = minimize(neg_lml, theta0, method="L-BFGS-B", bounds=bounds)
    ell, sig = np.exp(res.x)

    K = _rbf(x, x, ell, sig) + np.diag(noise) + _JITTER * np.eye(len(x))
    c, low = cho_factor(K)
    alpha = cho_solve((c, low), y)
    return _CompoundGP(x_train=x, alpha=alpha, ell=float(ell), sig=float(sig))


def fit_circuit_gp(df: pd.DataFrame, circuit: str) -> GPFit:
    """Fit a per-compound GP degradation curve on the within-stint deviations."""
    dev = df["lap_time_s"] - df.groupby("stint_id")["lap_time_s"].transform("mean")
    work = pd.DataFrame({
        "Compound": df["Compound"].to_numpy(),
        "TyreLife": df["TyreLife"].to_numpy(dtype=float),
        "dev": dev.to_numpy(dtype=float),
    })
    curves: dict[str, _CompoundGP] = {}
    for compound, sub in work.groupby("Compound"):
        agg = sub.groupby("TyreLife")["dev"].agg(["mean", "count", "var"])
        if len(agg) < 3:
            continue  # too few distinct ages to fit a curve
        x = agg.index.to_numpy(dtype=float)
        y = agg["mean"].to_numpy(dtype=float)
        resid_var = float(np.nanmean(agg["var"].to_numpy())) or 1e-4
        noise = resid_var / np.clip(agg["count"].to_numpy(dtype=float), 1.0, None)
        noise = np.clip(noise, 1e-6, None)
        curves[str(compound)] = _fit_one(x, y, noise)
    return GPFit(circuit=circuit, curves=curves)


def predict_shape_gp(fit: GPFit, df: pd.DataFrame) -> pd.Series:
    """Predict the within-stint lap-time shape; NaN for compounds absent from
    the fit (counted by the caller, never silently filled) — same contract as
    the OLS ``predict_shape``."""
    ages = df["TyreLife"].to_numpy(dtype=float)
    result = pd.Series(np.nan, index=df.index, dtype=float)
    for compound, curve in fit.curves.items():
        mask = (df["Compound"] == compound).to_numpy()
        if mask.any():
            result.iloc[np.where(mask)[0]] = curve.predict(ages[mask])
    return result
