"""Adversarial pass #2: does a safety car contaminate the *green* laps of a
stint that experienced one, the same way rain contaminated Monaco?

The degradation frame already drops the neutralised laps themselves
(`is_pace_lap` / `is_non_green` filtering, `src/degradation/dataset.py`).
What it does not check is a second-order effect: a stint that experienced a
safety car earlier still fits on that stint's *own remaining green laps* --
but a safety car changes tyre temperature (a genuine physical effect, the
same category of contamination the Monaco wet-race bug turned out to be),
so those green laps could plausibly show a different pace evolution than a
stint that never saw one, even with the neutralised laps themselves excluded.

This script splits each circuit's stints into "clean" (no non-green lap
anywhere in the stint) and "SC-touched" (>=1 non-green lap somewhere in the
stint, but only its own green laps enter the fit either way), fits the
existing degree-1 model on the *clean* stints only, and compares its
within-stint residual pattern against the SC-touched stints held out --
if SC-touched stints predict systematically worse (or with a different-
signed residual trend) than an ordinary LORO fold would, that is evidence
of contamination this project has not yet caught.

Writes ``reports/cross_series/sc_contamination_check.md``.

Usage (from the repo root; offline)::

    python scripts/run_sc_contamination_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from src.ingestion.config import REPORTS_DIR  # noqa: E402

from src.ingestion.config import CIRCUITS  # noqa: E402
#: The regulation-stable fitting window, from the config rather than repeated
#: here. This was ``(2023, 2024, 2025)`` — a third copy of a season list that
#: had already moved to 2022-2025, so this check silently ran on a narrower
#: window than the model it is checking.
from src.ingestion.config import PRE_ERA_SEASONS as SEASONS  # noqa: E402


def _stint_touched_by_neutralisation(raw_laps: pd.DataFrame) -> set[str]:
    """Every ``{race}_{Driver}_S{Stint}`` stint id with >= 1 non-green lap
    anywhere in it (red flag, SC, VSC), from the *raw* (unfiltered) laps --
    the modelling frame itself only ever contains the green laps, so this
    has to be reconstructed from before that filter runs."""
    non_green = raw_laps[raw_laps["is_non_green"].fillna(False)]
    # A lap can be non-green *and* carry no stint number — a car that never
    # takes the restart, or a red-flagged lap the source leaves unattributed.
    # It belongs to no stint, so it cannot mark one as touched, and casting it
    # to int raises. None of the four originally scoped circuits had such a
    # lap, which is why this only surfaced when the scope reached 26.
    non_green = non_green[non_green["Stint"].notna()]
    ids = (
        non_green["race"] + "_" + non_green["Driver"] + "_S"
        + non_green["Stint"].astype(int).astype(str)
    )
    return set(ids)


def _residuals(fit, frame: pd.DataFrame) -> pd.Series:
    shape = predict_shape(fit, frame)
    valid = shape.notna()
    actual = frame.loc[valid, "lap_time_s"] - frame.loc[valid].groupby("stint_id")["lap_time_s"].transform("mean")
    predicted = shape[valid] - shape[valid].groupby(frame.loc[valid, "stint_id"]).transform("mean")
    return actual - predicted


def main() -> int:
    lines = [
        "# Adversarial check: does a safety car contaminate a stint's own green laps?",
        "",
        "The degradation frame already excludes neutralised laps themselves. "
        "This checks a second-order effect a safety car could plausibly cause "
        "even so -- tyre-temperature disruption showing up in the green laps "
        "*around* a neutralisation, the same category of contamination the "
        "Monaco wet-race bug turned out to be, just for a different cause.",
        "",
        "| Circuit | Clean stints | SC-touched stints | Clean RMSE (s) | "
        "SC-touched RMSE (s) | Ratio |",
        "|---|---|---|---|---|---|",
    ]

    ratios = []
    for circuit in CIRCUITS:
        # A circuit can be in scope before its first race — Madrid joins with
        # the 2026 calendar and runs in September 2026. Recorded and skipped,
        # never fatal: a rolling scope guarantees this state exists.
        try:
            raw = load_circuit_laps(circuit, seasons=SEASONS)
        except ValueError:
            lines.append(f"| {circuit} | -- | -- | -- | -- | no laps in {SEASONS} |")
            continue
        touched_ids = _stint_touched_by_neutralisation(raw)

        frame, _ = build_modelling_frame(raw, circuit)
        is_touched = frame["stint_id"].isin(touched_ids)
        clean, touched = frame[~is_touched], frame[is_touched]

        n_clean_stints = clean["stint_id"].nunique()
        n_touched_stints = touched["stint_id"].nunique()
        if n_clean_stints < 5 or n_touched_stints < 3:
            lines.append(f"| {circuit} | {n_clean_stints} | {n_touched_stints} | -- | -- | too few to compare |")
            continue

        fit = fit_circuit(clean, circuit, degree=1)
        clean_resid = _residuals(fit, clean)
        touched_resid = _residuals(fit, touched)
        clean_rmse = float(np.sqrt((clean_resid**2).mean()))
        touched_rmse = float(np.sqrt((touched_resid**2).mean()))
        ratio = touched_rmse / clean_rmse if clean_rmse > 0 else float("nan")
        ratios.append((circuit, ratio))

        lines.append(
            f"| {circuit} | {n_clean_stints} | {n_touched_stints} | "
            f"{clean_rmse:.3f} | {touched_rmse:.3f} | {ratio:.2f}x |"
        )

    lines += [
        "",
        "**Reading `Ratio`**: fit the model on clean stints only, then score "
        "its within-stint residual on both clean stints (in-sample, the "
        "floor) and SC-touched stints it never saw (out-of-sample). A ratio "
        "near 1x means SC-touched green laps behave like any other held-out "
        "stint -- no detectable contamination beyond ordinary season-to-season "
        "noise. A ratio well above 1x would mean SC-touched stints are "
        "harder to predict specifically *because* they were touched, which "
        "would be a real, previously uncaught bias.",
        "",
    ]

    if ratios:
        max_circuit, max_ratio = max(ratios, key=lambda r: r[1])
        if max_ratio < 1.5:
            lines.append(
                f"**No contamination detected.** Every circuit's ratio stays "
                f"under 1.5x (worst: {max_circuit} at {max_ratio:.2f}x) -- well "
                "within the range ordinary out-of-sample noise already produces "
                "elsewhere in this project's LORO folds. The existing "
                "neutralised-lap exclusion appears sufficient; a safety car's "
                "effect on tyre temperature, if real, is not large enough to "
                "show up above the season-to-season noise this project already "
                "treats as expected."
            )
        else:
            lines.append(
                f"**Possible contamination at {max_circuit}** ({max_ratio:.2f}x) "
                "-- worth a closer look before this is treated as settled; "
                "SC-touched stints there predict meaningfully worse than clean "
                "stints do, which is at least consistent with a real effect."
            )
    lines.append("")

    out = REPORTS_DIR / "cross_series" / "sc_contamination_check.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
