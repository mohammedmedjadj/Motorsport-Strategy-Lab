"""Proper scoring rules and calibration for probabilistic predictions.

A model that outputs probabilities must be graded on two things a point
prediction cannot express:

- **Sharpness / accuracy** — a *proper* scoring rule (Brier, log-loss) that is
  optimised only by reporting your true belief, so it cannot be gamed by
  hedging.
- **Calibration** — of the events you called 70% likely, did ~70% happen? A
  reliability curve bins predictions and compares predicted to observed
  frequency.

The headline is the **Brier skill score**: how much the model beats simply
predicting the base rate every time (climatology). Positive means genuine
skill; zero means the model adds nothing over the long-run average; negative
means it is worse than knowing nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-12  # keeps log-loss finite at p = 0 or 1


def _validate(p: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    if p.shape != y.shape:
        raise ValueError("predictions and outcomes must have the same shape")
    if p.size == 0:
        raise ValueError("no predictions to score")
    if ((p < 0) | (p > 1)).any():
        raise ValueError("predictions must be probabilities in [0, 1]")
    if not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("outcomes must be binary (0/1)")
    return p, y


def brier_score(p: np.ndarray, y: np.ndarray) -> float:
    """Mean squared error of the probabilities — lower is better, 0 is perfect."""
    p, y = _validate(p, y)
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    """Mean negative log-likelihood — lower is better; punishes confident misses."""
    p, y = _validate(p, y)
    p = np.clip(p, _EPS, 1 - _EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier_skill_score(p: np.ndarray, y: np.ndarray) -> float:
    """Brier score improvement over predicting the base rate (climatology) every
    time. > 0 = genuine skill; 0 = no better than the long-run average; < 0 =
    worse than knowing nothing."""
    p, y = _validate(p, y)
    base = brier_score(np.full_like(y, y.mean()), y)
    return float("nan") if base == 0 else 1.0 - brier_score(p, y) / base


@dataclass(frozen=True)
class ReliabilityBin:
    """One bin of a reliability curve."""

    predicted: float   # mean predicted probability in the bin
    observed: float    # observed event frequency in the bin
    count: int


def reliability_curve(p: np.ndarray, y: np.ndarray, n_bins: int = 5) -> list[ReliabilityBin]:
    """Bin predictions into ``n_bins`` equal-width probability buckets and, for
    each non-empty bin, return the mean predicted probability against the
    observed frequency. A well-calibrated model sits on the diagonal."""
    p, y = _validate(p, y)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    out: list[ReliabilityBin] = []
    for b in range(n_bins):
        mask = idx == b
        if mask.any():
            out.append(ReliabilityBin(float(p[mask].mean()),
                                      float(y[mask].mean()), int(mask.sum())))
    return out
