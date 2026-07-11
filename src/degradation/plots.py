"""Degradation visualisations for the Phase 2 report.

One figure per circuit: degradation-attributable lap-time delta vs tyre age,
scatter per compound with the fitted polynomial overlaid. The plotted y is
``lap_time - driver_race_intercept - fuel_term`` from the full fit, i.e. the
component of pace the model attributes to the tyre plus residual noise.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: never require a display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.degradation.model import FitResult

COMPOUND_COLORS = {"SOFT": "#DA291C", "MEDIUM": "#FFD100", "HARD": "#4B4B4B"}


def degradation_figure(df: pd.DataFrame, fit: FitResult, path: Path) -> None:
    """Save the per-compound degradation plot for one circuit."""
    fe = df["driver_race"].map(fit.fixed_effects)
    fuel = fit.fuel_slope.value * df["LapNumber"]
    tyre_delta = df["lap_time_s"] - fe - fuel

    fig, ax = plt.subplots(figsize=(8, 5))
    for compound, coefs in fit.deg_coefs.items():
        mask = df["Compound"] == compound
        if not mask.any():
            continue
        color = COMPOUND_COLORS.get(compound, "#1F77B4")
        ax.scatter(
            df.loc[mask, "TyreLife"], tyre_delta[mask],
            s=8, alpha=0.25, color=color, edgecolors="none",
        )
        ages = np.linspace(1, float(df.loc[mask, "TyreLife"].max()), 100)
        label = f"{compound} ({' '.join(f'{c.value:+.3f}t^{p}' for p, c in enumerate(coefs, 1))} s)"
        ax.plot(ages, fit.degradation_delta(compound, ages), color=color, lw=2, label=label)

    ax.set_xlabel("Tyre age (laps)")
    ax.set_ylabel("Degradation-attributable delta (s/lap)")
    ax.set_title(
        f"{fit.circuit} — tyre degradation (degree {fit.degree}, "
        f"{fit.n_laps} laps, {fit.n_stints} stints, seasons pooled)"
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
