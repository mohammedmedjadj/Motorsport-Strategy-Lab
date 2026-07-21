"""Leave-one-race-out backtest of neutralisation-occurrence predictions.

The predictor is deliberately the simplest defensible one: **the base rate at
this circuit**. To score its prediction for a given race edition, that edition
is held out and the probability is formed from the *other* editions of the same
circuit only, with a Jeffreys Beta-Binomial smoother::

    p = (k_others + 0.5) / (n_others + 1)

so a circuit seen once falls back to an uninformative 0.5 rather than a
falsely-certain 0 or 1. Because the held-out edition never touches its own
prediction, the resulting Brier / skill numbers are genuinely out-of-sample —
the difference between *fitting* a base rate and *forecasting* with it.

The harness is series-agnostic: it consumes a mapping ``{circuit: outcomes}``
of binary 0/1 arrays and knows nothing about F1 vs endurance. Two adapters
build that mapping — :func:`endurance_outcomes` from the per-lap flag table,
and :func:`f1_outcomes` from the committed safety-car occurrence counts — so
all three series are scored by identical code.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .scoring import (
    ReliabilityBin,
    brier_score,
    brier_skill_score,
    log_loss,
    reliability_curve,
)

# Endurance per-lap flag → which neutralisation kind it signals.
FCY_FLAG = "FCY"   # full course yellow
SC_FLAG = "SF"     # safety car


def leave_one_race_out(outcomes_by_circuit: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """For every race, predict its neutralisation probability from the *other*
    editions of the same circuit (Jeffreys ``(k+0.5)/(n+1)``), and return the
    aligned ``(predictions, outcomes)`` arrays over all races."""
    preds: list[float] = []
    obs: list[float] = []
    for outcomes in outcomes_by_circuit.values():
        y = np.asarray(outcomes, dtype=float)
        total, n = y.sum(), y.size
        for yi in y:
            k_others, n_others = total - yi, n - 1
            preds.append((k_others + 0.5) / (n_others + 1))
            obs.append(yi)
    return np.asarray(preds), np.asarray(obs)


@dataclass(frozen=True)
class BacktestResult:
    """Out-of-sample calibration of a neutralisation predictor for one kind."""

    kind: str
    n_races: int
    base_rate: float
    brier: float
    brier_climatology: float
    skill: float
    log_loss: float
    reliability: list[ReliabilityBin]

    @property
    def beats_climatology(self) -> bool:
        return self.skill > 0

    def summary_row(self) -> dict:
        return {
            "kind": self.kind,
            "n_races": self.n_races,
            "base_rate": round(self.base_rate, 4),
            "brier": round(self.brier, 4),
            "brier_climatology": round(self.brier_climatology, 4),
            "skill": round(self.skill, 4),
            "log_loss": round(self.log_loss, 4),
        }


def score_backtest(kind: str, outcomes_by_circuit: dict[str, np.ndarray],
                   n_bins: int = 5) -> BacktestResult:
    """Run the leave-one-race-out backtest and grade it with proper scoring
    rules plus a reliability curve."""
    preds, y = leave_one_race_out(outcomes_by_circuit)
    base = np.full_like(y, y.mean())
    return BacktestResult(
        kind=kind,
        n_races=int(y.size),
        base_rate=float(y.mean()),
        brier=brier_score(preds, y),
        brier_climatology=brier_score(base, y),
        skill=brier_skill_score(preds, y),
        log_loss=log_loss(preds, y),
        reliability=reliability_curve(preds, y, n_bins=n_bins),
    )


# --- adapters: one tidy row per race, then group by whatever level ----------

def outcomes_by(table: pd.DataFrame, outcome_col: str, group_col: str) -> dict[str, np.ndarray]:
    """Slice a per-race table into ``{group: 0/1 array}`` for the backtest."""
    return {str(g): grp[outcome_col].to_numpy(dtype=float)
            for g, grp in table.groupby(group_col)}


def endurance_race_table(flags: pd.DataFrame) -> pd.DataFrame:
    """Collapse the per-lap flag table to one row per race with binary FCY / SC
    columns (did that neutralisation ever fly?), keyed by series and circuit."""
    hit = flags.assign(fcy=flags["flags"].eq(FCY_FLAG), sc=flags["flags"].eq(SC_FLAG))
    per_race = (
        hit.groupby(["series_code", "event", "year", "session_id"])[["fcy", "sc"]]
        .any()
        .astype(float)
        .reset_index()
        .rename(columns={"series_code": "series", "event": "circuit"})
    )
    return per_race


def f1_race_table(sc_model: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct one row per F1 race edition from the committed occurrence
    counts. A circuit with ``n`` editions and ``k`` races-with-event expands to
    ``k`` ones and ``n-k`` zeros — all the leave-one-out predictor needs, since
    its prediction depends only on ``k`` and ``n``, never on which season."""
    rows = []
    for _, r in sc_model.iterrows():
        n = int(r["n_editions"])
        sc_k, vsc_k = int(r["sc_races_with_event"]), int(r["vsc_races_with_event"])
        for i in range(n):
            rows.append({"series": "f1", "circuit": str(r["circuit"]),
                         "sc": float(i < sc_k), "vsc": float(i < vsc_k)})
    return pd.DataFrame(rows)
