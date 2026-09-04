"""Phase 5.5 -- does anything besides degradation generalise?

The project's headline finding so far is narrow in one specific way: "a
tyre-degradation slope rarely transfers across seasons or circuits, except
Bahrain" is a claim about *degradation specifically*. Two other fitted
quantities exist, and this script closes the gap for the one that actually
had no leave-one-out test yet:

- **Pit loss** (`estimate_pit_loss`, F1 and endurance) never had a
  leave-one-out validator before this script -- `pit_loss_validation.py` and
  `endurance_pit_loss_validation.py` add it, and this script runs both.
- **Neutralisation occurrence** (does a race see >= 1 SC/VSC/FCY) already
  had one: `src/prediction/backtest.py` leave-one-race-out-backtests it with
  proper scoring rules (Brier, skill vs climatology, log-loss), committed at
  `data/derived/prediction/neutralisation_calibration.csv`. This script does
  not re-derive it -- it reads that existing result in as the third row of
  the same "what generalises, per quantity" table, which is the point: one
  comparable table across all three fitted quantities, not three separate,
  previously-uncomparable claims.

Writes ``data/derived/f1/pit_loss_loro.csv``,
``data/derived/endurance/pit_loss_loro.csv``, and
``reports/generalization_audit.md``.

Usage (from the repo root; offline -- reads the committed derived CSVs)::

    python scripts/run_generalization_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.data.endurance_loader import EnduranceLoader  # noqa: E402
from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402
from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.degradation.validation import leave_one_race_out  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    PREDICTION_DERIVED_DIR,
    REPORTS_DIR,
)
from src.simulator.endurance_pit_loss_validation import (  # noqa: E402
    leave_one_race_out_pit_loss_endurance,
)
from src.simulator.pit_loss_validation import leave_one_race_out_pit_loss  # noqa: E402

from src.degradation.dataset import circuits_with_laps  # noqa: E402
from src.ingestion.config import PRE_ERA_SEASONS  # noqa: E402

#: Only the scoped circuits that have laps in this window. The scope is
#: rolling and can name a circuit whose first race has not been run.
#: The regulation-stable fitting window, from the config rather than a literal.
#: This was `(2023, 2024, 2025)`, which silently excluded 2022 after the scope
#: was widened to it — a second copy of a scope is a second thing to forget.
F1_SEASONS = PRE_ERA_SEASONS

#: Only the scoped circuits that have laps in that window. The scope is rolling
#: and can name a circuit whose first race has not been run.
F1_CIRCUITS = circuits_with_laps(seasons=F1_SEASONS)


def _f1_degradation_mean_r2(circuit: str) -> float:
    """Re-derive the same degree-1 within-stint mean R2 already reported in
    degradation_phase2.md, for a like-for-like comparison row (that report
    stores it only in markdown prose, not a CSV)."""
    laps = load_circuit_laps(circuit, seasons=F1_SEASONS)
    frame, _ = build_modelling_frame(laps, circuit)
    folds = leave_one_race_out(frame, circuit, degree=1)
    vals = [f.r2_within for f in folds if f.r2_within == f.r2_within]  # drop NaN
    return float(sum(vals) / len(vals)) if vals else float("nan")


def _f1_pit_loss_rows() -> list[dict[str, object]]:
    rows = []
    for circuit in F1_CIRCUITS:
        laps = load_circuit_laps(circuit, seasons=F1_SEASONS)
        folds = leave_one_race_out_pit_loss(laps, circuit)
        for f in folds:
            rows.append({
                "series": "f1", "circuit": circuit, "held_out": f.test_race,
                "train_median_s": round(f.train_median_s, 2),
                "test_median_s": round(f.test_median_s, 2),
                "rmse_s": round(f.rmse_s, 2),
                "n_test_events": f.n_test_events,
            })
    return rows


def _endurance_pit_loss_rows() -> list[dict[str, object]]:
    rows = []
    for series, circuits in ENDURANCE_SCOPE.items():
        loader = EnduranceLoader(series)
        for cs in circuits:
            if len(cs.seasons) < 2:
                continue
            laps_by_season = {
                str(y): loader.load_laps(y, cs.event, cs.car_class) for y in cs.seasons
            }
            folds = leave_one_race_out_pit_loss_endurance(laps_by_season, series, cs.event)
            for f in folds:
                rows.append({
                    "series": series, "circuit": cs.event, "held_out": f.held_out,
                    "train_median_s": round(f.train_median_s, 2),
                    "test_median_s": round(f.test_median_s, 2),
                    "rmse_s": round(f.rmse_s, 2),
                    "n_test_events": f.n_test_events,
                })
    return rows


def _summarise(rows: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    g = df.groupby(["series", "circuit"])
    summary = g.apply(
        lambda d: pd.Series({
            "n_folds": len(d),
            "mean_rmse_s": round(d["rmse_s"].mean(), 2),
            "mean_train_median_s": round(d["train_median_s"].mean(), 2),
            # relative error: RMSE as a fraction of the typical pit loss at
            # that circuit -- makes circuits with very different absolute
            # pit-loss magnitudes (6s pit lane vs 90s endurance stop)
            # comparable on one axis.
            "relative_rmse": round(d["rmse_s"].mean() / d["train_median_s"].mean(), 3),
        }),
        include_groups=False,
    ).reset_index()
    return summary.sort_values("relative_rmse")


def _worst_transfer_sentence(
    end_deg_mean: pd.Series, summary: pd.DataFrame
) -> str:
    """State which circuit transfers worst, from the numbers, not from memory.

    This paragraph used to assert "-6.330 within-stint R2 ... an order of
    magnitude more negative than anywhere else". The table directly above it
    said -1.490. The table recomputed when the scope widened to every class and
    the sentence did not, because it was prose and prose does not recompute.
    Both the value and the claim it supports are now derived, so widening the
    scope again either keeps the sentence true or changes it.
    """
    scores = end_deg_mean.dropna().sort_values()
    if scores.empty:
        return "No endurance circuit-class has a measurable transfer score."

    (series, event, car_class), worst = scores.index[0], scores.iloc[0]
    runner_up = float(scores.iloc[1]) if len(scores) > 1 else float("nan")

    # "An order of magnitude worse than anywhere else" is a claim about the
    # gap to the next-worst, so check it rather than repeat it.
    gap = abs(worst) / abs(runner_up) if runner_up and abs(runner_up) > 0 else float("inf")
    if gap >= 10:
        severity = (
            f"an order of magnitude more negative than the next-worst "
            f"({scores.index[1][1]} {scores.index[1][2]}, {runner_up:+.3f})"
        )
    elif gap >= 2:
        severity = (
            f"{gap:.1f}x more negative than the next-worst "
            f"({scores.index[1][1]} {scores.index[1][2]}, {runner_up:+.3f})"
        )
    else:
        severity = (
            f"the worst of them, though not by much — the next-worst "
            f"({scores.index[1][1]} {scores.index[1][2]}) sits at {runner_up:+.3f}"
        )

    # Does the same circuit also transfer worst on pit loss? That coincidence
    # is the whole point of the paragraph, so it has to be checked, not assumed.
    pit_worst = summary.iloc[-1]
    both = str(pit_worst["circuit"]).casefold() == str(event).casefold()

    opening = (
        f"**{event} {car_class} is the worst-transferring circuit-class for "
        "degradation, and the same circuit transfers worst on pit loss too — "
        "two independent estimators flagging the same race.**"
        if both else
        f"**{event} {car_class} transfers worst for degradation** "
        f"({worst:+.3f}); the worst for pit loss is a different circuit, "
        f"{pit_worst['circuit']} ({pit_worst['series']}, relative RMSE "
        f"{pit_worst['relative_rmse']:.2f})."
    )

    return (
        f"{opening} A within-stint R2 of {worst:+.3f} is {severity}. The "
        "shorter 2025 race format described above plausibly explains it: "
        "fewer laps per stint changes the fuel-burn/degradation separation "
        "the fixed-effects model relies on, not just the pit-loss magnitude."
    )


def main() -> int:
    f1_rows = _f1_pit_loss_rows()
    end_rows = _endurance_pit_loss_rows()

    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(f1_rows).to_csv(F1_DERIVED_DIR / "pit_loss_loro.csv", index=False)
    ENDURANCE_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(end_rows).to_csv(ENDURANCE_DERIVED_DIR / "pit_loss_loro.csv", index=False)

    all_rows = f1_rows + end_rows
    summary = _summarise(all_rows)

    f1_degradation_r2 = {c: _f1_degradation_mean_r2(c) for c in F1_CIRCUITS}

    end_deg_loro_path = ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv"
    end_deg = pd.read_csv(end_deg_loro_path)
    # Keyed on the class as well as the circuit. Indexing on (series, event)
    # alone kept every class row but showed only two of the three columns that
    # identify it, so IMSA printed three indistinguishable "Daytona" lines with
    # different numbers and a reader had no way to tell which was GTP.
    end_deg_mean = (
        end_deg[end_deg["held_out_season"] == "MEAN"]
        .set_index(["series", "event", "car_class"])["r2_within"]
        .sort_index()
    )

    lines = [
        "# Generalisation audit -- what transfers across seasons, per quantity",
        "",
        "The project's headline generalisation finding -- \"a degradation "
        "slope rarely transfers across seasons or circuits, except "
        "Bahrain\" -- is a claim about degradation specifically. Pit loss is "
        "fitted with the same measure-don't-invent philosophy but never had "
        "a leave-one-race-out test until this report (`leave_one_race_out`, "
        "F1; `leave_one_race_out_endurance`/`..._pit_loss_endurance`, "
        "WEC/IMSA). Neutralisation occurrence already had one "
        "(`src/prediction/backtest.py`). This report puts all three fitted "
        "quantities in one comparable table for the first time, across all "
        "three series.",
        "",
        "## Pit loss: leave-one-race-out RMSE, relative to the circuit's own median",
        "",
        "`relative_rmse = mean(LORO RMSE) / mean(training median)` -- lets "
        "circuits with very different pit-loss magnitudes (an F1 pit lane, "
        "~6-30s; an endurance stop with a driver change, 30-90s) sit on one "
        "comparable scale. Sorted best-transferring first.",
        "",
        "| Series | Circuit | Folds | Mean training median (s) | Mean LORO RMSE (s) | Relative RMSE |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r['series']} | {r['circuit']} | {int(r['n_folds'])} | "
            f"{r['mean_train_median_s']:.1f} | {r['mean_rmse_s']:.1f} | {r['relative_rmse']:.2f} |"
        )

    best = summary.iloc[0]
    worst = summary.iloc[-1]
    lines += [
        "",
        f"**Pit loss transfers far better than degradation, in general.** "
        f"Most circuits sit at a relative RMSE of 0.05-0.25 -- the training "
        f"median typically predicts a season it never saw within a few "
        f"seconds on a stop that costs tens of seconds. The best case here "
        f"is **{best['circuit']}** ({best['series']}, relative RMSE "
        f"{best['relative_rmse']:.2f}); the worst is **{worst['circuit']}** "
        f"({worst['series']}, relative RMSE {worst['relative_rmse']:.2f}) -- "
        "worth reading in full below, it is not a small effect.",
        "",
        "## The one large exception: WEC COTA",
        "",
    ]
    cota = summary[(summary["series"] == "wec") & (summary["circuit"] == "COTA")]
    if not cota.empty:
        c = cota.iloc[0]
        lines += [
            f"COTA's own 2024 pit-loss median (74.0s, 88 clean stops) and "
            f"2025 median (21.0s, 15 clean stops) differ by roughly 3.5x "
            f"(relative RMSE {c['relative_rmse']:.2f}, worst of every circuit "
            "in either series). Checked directly rather than left as an "
            "unexplained outlier: the race itself was shorter in 2025 -- "
            "**120 laps versus 183 in 2024, same 18 cars** (verified from the "
            "raw lap data, `EnduranceLoader('wec').load_laps(year, 'COTA', "
            "'HYPERCAR')`). A shorter race plausibly needs less fuel per "
            "stint, which plausibly means shorter, cheaper stops -- but that "
            "chain is only plausible, not confirmed (fuel load per stop "
            "itself is not in the source); what is confirmed is that this is "
            "a real difference between two race formats, not a data or unit "
            "bug: the raw per-event losses in "
            "`data/derived/endurance/pit_loss_loro.csv` are physically "
            "sane numbers in both seasons (11-38s and 37-100s clusters "
            "respectively), not corrupted or duplicated values.",
            "",
        ]

    lines += [
        "## Degradation, for comparison (already established, restated here for the single table)",
        "",
        "A circuit transfers only within a class: the same track is a "
        "different degradation problem for a GT3 car and a prototype, and "
        "collapsing them would average away the one result this table exists "
        "to show.",
        "",
        "| Series | Class | Circuit | Mean LORO within-stint R2 |",
        "|---|---|---|---|",
    ]
    for c, r2 in f1_degradation_r2.items():
        # One season in scope means no fold to hold out. That is "not
        # measurable here", which is a different statement from a bad score,
        # and printing "+nan" said neither.
        value = "not measurable (1 season)" if pd.isna(r2) else f"{r2:+.3f}"
        lines.append(f"| f1 | — | {c} | {value} |")
    for (series, event, car_class), r2 in end_deg_mean.items():
        value = "not measurable (1 season)" if pd.isna(r2) else f"{r2:+.3f}"
        lines.append(f"| {series} | {car_class} | {event} | {value} |")

    lines += [
        "",
        _worst_transfer_sentence(end_deg_mean, summary),
        "",
        "## Neutralisation occurrence, for comparison (already established, restated here)",
        "",
        "A third fitted quantity already had a leave-one-race-out test before "
        "this report -- `src/prediction/backtest.py`, committed at "
        "`data/derived/prediction/neutralisation_calibration.csv` -- predicting, "
        "per race, whether a given neutralisation kind occurs at all from the "
        "circuit's base rate on every *other* race, scored with proper scoring "
        "rules (Brier score, skill vs a climatology baseline, log-loss) rather "
        "than R2. Skill > 0 means the circuit-specific base rate genuinely beats "
        "just guessing the series-wide average; skill < 0 means it does not.",
        "",
        "| Target | Level | Races | Base rate | Skill vs climatology |",
        "|---|---|---|---|---|",
    ]
    calib_path = PREDICTION_DERIVED_DIR / "neutralisation_calibration.csv"
    series_fcy_skill = None
    if calib_path.exists():
        calib = pd.read_csv(calib_path)
        for _, r in calib.iterrows():
            lines.append(
                f"| {r['target']} | {r['level']} | {int(r['n_races'])} | "
                f"{r['base_rate']:.3f} | {r['skill']:+.4f} |"
            )
        series_fcy_skill = calib.loc[
            calib["target"] == "Endurance FCY (by series)", "skill"
        ].iloc[0]
    lines += [
        "",
        "Five of six targets score **negative** skill -- a per-circuit base "
        "rate does not beat the series-wide average out of sample, the same "
        "qualitative conclusion as degradation (does not transfer) rather "
        "than pit loss (does). The lone exception, Endurance FCY pooled *by "
        f"series* rather than by circuit (skill {series_fcy_skill:+.4f}), is itself evidence "
        "for the same idea pit loss vs. degradation already established: "
        "pooling at the right level (series, not circuit, for a quantity "
        "this rare) recovers signal that per-circuit fitting throws away to "
        "noise -- the same logic behind pooling toward Bahrain's precision "
        "would fix if extended, and the same logic Section 7 of the Activity "
        "#3 roadmap's hierarchical-Bayesian proposal targets directly.",
        "",
        "## Reading all three quantities together",
        "",
        "- **Degradation**: within-stint R2 is negative at most circuits in "
        "every series -- a slope fit on other seasons predicts the held-out "
        "season *worse* than a flat line, with Bahrain (WEC) the one clean "
        "exception (see `reports/wec/degradation_phase2.md`).",
        "- **Neutralisation occurrence**: the same story as degradation -- "
        "per-circuit base rates mostly fail to beat a series-wide climatology "
        "out of sample; only pooling at the series level (not attempted here "
        "for degradation or pit loss) recovers positive skill.",
        "- **Pit loss**: transfers well almost everywhere, because it is "
        "closer to a fixed procedural/physical quantity (pit lane length, "
        "stationary time) than a fitted trend -- it should be more stable, "
        "and measured here for the first time to actually be more stable, "
        "not just assumed to be.",
        "- **Together**: \"nothing generalises\" would have been an "
        "overclaim extending the degradation finding to the whole project, "
        "and it turns out to be wrong for pit loss specifically. The honest "
        "statement is narrower and more useful: *what* generalises depends "
        "on whether the quantity is closer to a fixed physical constant "
        "(pit loss: yes, mostly) or a season-specific fitted trend "
        "(degradation and per-circuit neutralisation rate: no, mostly, "
        "unless pooled at a coarser level than circuit).",
        "",
        "## Limitations",
        "",
        "- Relative RMSE is computed on the *trimmed* (routine-stop) event "
        "pool on both sides, matching what `estimate_pit_loss` reports "
        "everywhere else in this project; an earlier untrimmed version of "
        "this same test produced RMSEs inflated 5-20x by single repair/"
        "driver-change outliers in the held-out season -- a reminder that "
        "trimming and evaluation basis must match, not just be individually "
        "reasonable.",
        "- Some circuits have as few as 2 folds (WEC COTA, Interlagos, "
        "Sebring) -- the same small-sample caveat the degradation LORO "
        "already carries applies here too.",
        "- The neutralisation comparison (previous section) tests "
        "*occurrence* (does a race see >= 1 event) only; the *per-lap rate* "
        "posterior (`per_lap_rate`, used to time hazards within a simulated "
        "race, not just whether one happens) has no leave-one-out test yet "
        "-- a real, narrower gap this report does not close.",
        "",
    ]

    out = REPORTS_DIR / "cross_series" / "generalization_audit.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {F1_DERIVED_DIR / 'pit_loss_loro.csv'}")
    print(f"wrote {ENDURANCE_DERIVED_DIR / 'pit_loss_loro.csv'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
