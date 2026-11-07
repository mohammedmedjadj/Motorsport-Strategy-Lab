"""Is Result 2's AUC gap a gap in measurement precision?

Pit loss separates the tyre-limited race-seasons from the fuel-limited ones at
a higher AUC than the net degradation slope does. Pit loss is measured from
stop durations; the slope is estimated, and a fifth of the endurance slopes
have an interval containing zero. A noisily measured predictor loses AUC even
when the underlying quantity matters as much, so the gap could be precision
rather than importance.

The check: recompute both AUCs on the race-seasons whose slope is most
precisely estimated (narrowest interval). If imprecision were what held the
slope back, its AUC would rise toward pit loss's as the noisy slopes are
dropped.

Writes ``data/derived/cross_series/regime_precision.csv``.

    python scripts/run_regime_precision.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.ingestion.config import ENDURANCE_DERIVED_DIR, DERIVED_DIR  # noqa: E402

OUT = DERIVED_DIR / "cross_series" / "regime_precision.csv"
#: Share of race-seasons kept, from all of them down to the most precise third.
KEEP = (1.0, 0.5, 1 / 3)


def _auc(score: np.ndarray, positive: np.ndarray) -> float:
    """Mann-Whitney AUC: chance a positive outranks a negative, ties half."""
    pos, neg = score[positive], score[~positive]
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))


def build() -> pd.DataFrame:
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    # The plans carry the slope they were solved with, to four decimals; the
    # fit table carries its interval. Matching on series, class, season and
    # that slope pairs each race-season with the interval of its own fit.
    key = lambda d, season, slope: (d["series"] + "|" + d["car_class"] + "|"
                                    + d[season].astype(str) + "|"
                                    + d[slope].round(4).astype(str))
    plans["key"] = key(plans, "year", "net_slope_s")
    fits["key"] = key(fits, "season", "net_slope")
    merged = plans.merge(fits[["key", "ci_low", "ci_high"]].drop_duplicates("key"),
                         on="key", how="left")
    if merged["ci_low"].isna().any():
        raise RuntimeError("race-seasons without a matching slope interval")
    merged["ci_width"] = merged["ci_high"] - merged["ci_low"]
    tyre_limited = ~merged["fuel_limited"].astype(bool)

    rows = []
    for keep in KEEP:
        mask = (merged["ci_width"] <= merged["ci_width"].quantile(keep)).to_numpy()
        tl = tyre_limited.to_numpy()[mask]
        rows.append({
            "kept_share": round(keep, 3),
            "n_race_seasons": int(mask.sum()),
            "n_tyre_limited": int(tl.sum()),
            "auc_slope": round(_auc(merged["net_slope_s"].to_numpy()[mask], tl), 4),
            # Pit loss separates the other way round: a cheap stop goes with
            # the tyre-limited regime.
            "auc_pit_loss": round(_auc(-merged["pit_loss_s"].to_numpy()[mask], tl), 4),
            "max_ci_width_s": round(float(merged["ci_width"][mask].max()), 4),
        })
    return pd.DataFrame(rows)


def main() -> int:
    table = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
