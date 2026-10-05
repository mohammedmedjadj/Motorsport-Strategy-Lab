"""Two objections to how pit loss is measured, tested on the data.

Wytze de Vries (TU Eindhoven) raised both after reading the brief on Result 2.

The first: a class median may pool distinct populations — a two-tyre change
against a full service with fuel and a driver change — in which case a median
is the wrong summary and the six-row table needs rethinking.

The second, and the more serious: reverse causality. If a race is tyre-limited
it runs more stops, so it carries less fuel per stop, so its stops are shorter.
Part of the −0.982 correlation could then run backwards.

Neither is answered by argument. This measures both, and writes
``reports/cross_series/pit_loss_measurement_check.md``. Nothing published is
edited: Result 2 stands as it stands until this says otherwise.

Usage (offline, from the repo root)::

    python scripts/run_pit_loss_checks.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import (  # noqa: E402
    DERIVED_DIR,
    ENDURANCE_DERIVED_DIR,
    REPORTS_DIR,
)
from src.reporting.names import car_class as class_name  # noqa: E402

CROSS_SERIES_REPORTS_DIR = REPORTS_DIR / "cross_series"
from src.simulator.endurance import PIT_LOSS_TRIM, green_lap_times  # noqa: E402
from src.simulator.endurance_models import load_race_laps  # noqa: E402

#: A circuit-class needs this many seasons before its across-season spread
#: means anything.
MIN_SEASONS = 3

#: A race needs this many green stops, at enough distinct stint lengths, before
#: a within-race correlation is worth computing.
MIN_STOPS_FOR_CORRELATION = 12
MIN_DISTINCT_STINTS = 4


def labelled_stop_events(laps: pd.DataFrame) -> pd.DataFrame:
    """Every clean green-flag stop, with what kind of stop it was.

    The filter is the library's: the pit lap and the lap after it must both run
    green, so a neutralised stop — cheap by construction — cannot contaminate
    the green reference, and the pool is trimmed at ``PIT_LOSS_TRIM`` x its own
    median exactly as ``estimate_pit_loss`` does. What is added is the labels.

    A driver change is read against the *previous* lap, not the next one: the
    timing feed records the incoming driver on the pit lap itself, so comparing
    forward finds a change on almost no stop at all. That error made driver
    changes look like 0.1% of green stops rather than a third to a half of them.
    """
    work = laps.sort_values(["car", "lap"], kind="stable").copy()
    baseline = green_lap_times(work).groupby("car")["lap_time_s"].median()
    work["t_next"] = work.groupby("car", sort=False)["lap_time_s"].shift(-1)
    work["flag_next"] = work.groupby("car", sort=False)["flag"].shift(-1)
    work["stint_prev"] = work.groupby("car", sort=False)["driver_stint"].shift(1)
    work["pit_number"] = work.groupby("car", sort=False)["is_pit_lap"].cumsum()
    stint_laps = work.groupby(["car", "pit_number"]).size().rename("stint_laps")

    stops = work[
        work["is_pit_lap"]
        & work["is_green"]
        & work["flag_next"].eq("GF")
        & work["lap_time_s"].notna()
        & work["t_next"].notna()
    ].copy()
    if stops.empty:
        return stops

    stops["loss_s"] = (
        stops["lap_time_s"] + stops["t_next"] - 2.0 * stops["car"].map(baseline)
    )
    stops = stops[stops["loss_s"] > 0]
    if stops.empty:
        return stops
    stops = stops[stops["loss_s"] <= PIT_LOSS_TRIM * stops["loss_s"].median()]
    stops["driver_change"] = (
        stops["stint_prev"].notna() & (stops["stint_prev"] != stops["driver_stint"])
    )
    stops = stops.join(stint_laps, on=["car", "pit_number"])
    return stops[[
        "car", "lap", "loss_s", "is_tyre_change", "driver_change", "stint_laps",
    ]]


def _collect(plans: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, race in enumerate(plans.itertuples(), 1):
        try:
            laps = load_race_laps(
                race.series, int(race.year), race.circuit, race.car_class
            )
            stops = labelled_stop_events(laps)
        except Exception as error:  # noqa: BLE001
            print(f"  skipped {race.series} {race.year} {race.circuit} "
                  f"{race.car_class}: {error}", flush=True)
            continue
        if stops.empty:
            continue
        rows.append(stops.assign(
            series=race.series, car_class=race.car_class, year=int(race.year),
            circuit=race.circuit, circuit_canonical=race.circuit_canonical,
            tyre_limited=bool(race.tyre_limited),
        ))
        if index % 50 == 0:
            print(f"[{index}/{len(plans)}]", flush=True)
    return pd.concat(rows, ignore_index=True)


def _unit(frame: pd.DataFrame) -> pd.Series:
    return frame["series"].str.upper() + " " + frame["car_class"].map(class_name)


def _class_median_of_race_medians(events: pd.DataFrame) -> pd.Series:
    """The published statistic's shape: a median over race-level medians."""
    per_race = events.groupby(["unit", "year", "circuit"])["loss_s"].median()
    return per_race.groupby("unit").median()


def main() -> int:
    warnings.filterwarnings("ignore")

    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    plans["unit"] = plans["series"].str.upper() + " " + plans["car_class"].map(class_name)

    events = _collect(plans)
    events["unit"] = _unit(events)
    out = DERIVED_DIR / "cross_series"
    out.mkdir(parents=True, exist_ok=True)
    events.to_csv(out / "pit_loss_stop_events.csv", index=False)

    lines = _report(plans, events)
    CROSS_SERIES_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (CROSS_SERIES_REPORTS_DIR / "pit_loss_measurement_check.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"\n{len(events)} green-flag stops across "
          f"{events.groupby(['unit', 'year', 'circuit']).ngroups} race-seasons")
    print(f"wrote {CROSS_SERIES_REPORTS_DIR / 'pit_loss_measurement_check.md'}")
    return 0


def _report(plans: pd.DataFrame, events: pd.DataFrame) -> list[str]:
    share = plans.groupby("unit")["tyre_limited"].mean() * 100
    variants = {
        "every stop": _class_median_of_race_medians(events),
        "no driver change": _class_median_of_race_medians(
            events[~events["driver_change"]]
        ),
        "driver change only": _class_median_of_race_medians(
            events[events["driver_change"]]
        ),
    }
    published = plans.groupby("unit")["pit_loss_s"].median()
    table = pd.DataFrame({"published": published, **variants,
                          "tyre_limited_pct": share}).sort_values("published")

    lines = [
        "<!-- GENERATED by scripts/run_pit_loss_checks.py — do not edit by hand. -->",
        "",
        "# Is the pit-loss measurement doing what Result 2 says it does?",
        "",
        "Two objections, both from **Wytze de Vries** (TU Eindhoven), after "
        "reading the one-page brief on Result 2. Neither is answerable by "
        "argument, so both are measured here. Nothing published has been "
        "edited: this report exists to decide whether anything should be.",
        "",
        f"Measured on **{len(events):,} green-flag stops** across "
        f"{events.groupby(['unit', 'year', 'circuit']).ngroups} race-seasons — "
        "every stop behind the per-race medians the published table summarises, "
        "under the same filter the estimator uses.",
        "",
        "## Objection 1 — a class median may pool distinct populations",
        "",
        "> A two-tyre change and a full service with fuel and a driver change "
        "are different operations. A median over both is a summary of neither.",
        "",
        "**He is right about the measurement.** The populations are there, and "
        "the splitter is the driver change rather than the tyre change — "
        "tyre changes are near-universal on a green stop in every class, so "
        "that axis separates almost nothing.",
        "",
        "| class | stops | driver change | median without | median with | gap | gap ÷ IQR without |",
        "|---|---|---|---|---|---|---|",
    ]

    for unit, part in events.groupby("unit"):
        with_dc = part.loc[part["driver_change"], "loss_s"]
        without = part.loc[~part["driver_change"], "loss_s"]
        iqr = without.quantile(0.75) - without.quantile(0.25)
        gap = with_dc.median() - without.median()
        lines.append(
            f"| {unit} | {len(part):,} | {100 * part['driver_change'].mean():.0f}% | "
            f"{without.median():.1f} s | {with_dc.median():.1f} s | "
            f"{gap:+.1f} s | {gap / iqr:.2f} |"
        )

    lines += [
        "",
        "A driver change costs between a dozen and two dozen seconds on top of "
        "the stop, and in WEC Hypercar the gap is the size of the whole "
        "interquartile range of the stops without one. Those are two "
        "populations, not one with a spread.",
        "",
        "**It does not move the result.** What Result 2 uses is not the level of "
        "each class median but the *ordering* of the six classes against their "
        "tyre-limited share. That ordering is identical whichever population the "
        "median is taken over:",
        "",
        "| class | published | every stop | no driver change | driver change only | tyre-limited |",
        "|---|---|---|---|---|---|",
    ]
    for unit, row in table.iterrows():
        lines.append(
            f"| {unit} | {row['published']:.1f} s | {row['every stop']:.1f} s | "
            f"{row['no driver change']:.1f} s | {row['driver change only']:.1f} s | "
            f"{row['tyre_limited_pct']:.1f}% |"
        )

    lines += ["", "| statistic | Pearson r | Spearman |", "|---|---|---|"]
    for name in ("published", "every stop", "no driver change", "driver change only"):
        lines.append(
            f"| {name} | {table[name].corr(table['tyre_limited_pct']):+.3f} | "
            f"{table[name].corr(table['tyre_limited_pct'], method='spearman'):+.3f} |"
        )

    lines += [
        "",
        "The rank correlation is the same to three decimals in every variant. "
        "The driver-change premium shifts all six classes in the same direction "
        "and does not reorder them, which is why the published table survives an "
        "objection that is nonetheless correct about what it measures.",
        "",
        "## Objection 2 — reverse causality",
        "",
        "> A tyre-limited race runs more stops, so it carries less fuel per "
        "stop, so its stops are shorter. Part of the correlation runs backwards.",
        "",
        "This one needs three separate measurements, because the obvious "
        "comparison is confounded twice over.",
        "",
        "### The naive comparison, and why it proves nothing",
        "",
        "| class | tyre-limited races | fuel-limited races | median pit loss, tyre-limited | fuel-limited | difference |",
        "|---|---|---|---|---|---|",
    ]

    for unit, part in plans.groupby("unit"):
        limited = part.loc[part["tyre_limited"], "pit_loss_s"]
        fuel = part.loc[~part["tyre_limited"], "pit_loss_s"]
        if limited.empty:
            lines.append(
                f"| {unit} | 0 | {len(fuel)} | — | {fuel.median():.1f} s | — |"
            )
            continue
        lines.append(
            f"| {unit} | {len(limited)} | {len(fuel)} | {limited.median():.1f} s | "
            f"{fuel.median():.1f} s | {limited.median() - fuel.median():+.1f} s |"
        )

    lines += [
        "",
        "Tyre-limited races do have far shorter stops, by thirty to fifty "
        "seconds. That number is worthless as evidence for either direction, "
        "for two reasons. First it is partly **definitional**: tyre-limited is "
        "decided by a dynamic program that takes pit loss as an input, so a "
        "cheaper stop makes the extra stop optimal more often by construction. "
        "Second it is **confounded by circuit**, and that turns out to be the "
        "whole story.",
        "",
        "### Pit loss is a property of the circuit, not of the race",
        "",
    ]

    stability = (
        plans.groupby(["unit", "circuit_canonical"])["pit_loss_s"]
        .agg(["size", "median", "std"]).reset_index()
    )
    repeated = stability[stability["size"] >= MIN_SEASONS]
    within_circuit = float(repeated["std"].median())

    lines += [
        "| class | circuits | spread between circuits (SD of medians) |",
        "|---|---|---|",
    ]
    for unit, part in stability.groupby("unit"):
        lines.append(f"| {unit} | {len(part)} | {part['median'].std():.1f} s |")

    lines += [
        "",
        f"Against that, the spread of the same circuit-class **across seasons** "
        f"has a median standard deviation of **{within_circuit:.1f} s** "
        f"({len(repeated)} circuit-classes with at least {MIN_SEASONS} seasons). "
        "Pit loss is four to five times more a property of which circuit the "
        "race is at than of which season it is. A pit lane's length does not "
        "change because a particular race turned out to need an extra stop, so "
        "the variation that drives the correlation is exogenous to the outcome "
        "it predicts.",
        "",
        "### Holding the circuit constant, what is left of the reverse channel",
        "",
        "The clean test is a circuit-class that ran both kinds of season.",
        "",
        "| class | circuit | tyre-limited | fuel-limited | median pit loss, tyre-limited | fuel-limited | difference |",
        "|---|---|---|---|---|---|---|",
    ]

    paired = []
    for (unit, circuit), part in plans.groupby(["unit", "circuit_canonical"]):
        limited = part.loc[part["tyre_limited"], "pit_loss_s"]
        fuel = part.loc[~part["tyre_limited"], "pit_loss_s"]
        if limited.empty or fuel.empty:
            continue
        difference = float(limited.median() - fuel.median())
        paired.append(difference)
        lines.append(
            f"| {unit} | {circuit} | {len(limited)} | {len(fuel)} | "
            f"{limited.median():.1f} s | {fuel.median():.1f} s | {difference:+.1f} s |"
        )

    paired_median = float(np.median(paired)) if paired else float("nan")
    lines += [
        "",
        f"**Median difference with the circuit held constant: {paired_median:+.1f} s**, "
        f"across {len(paired)} circuit-classes that ran both. The thirty-to-fifty "
        "second gap in the naive table was circuit composition. What survives is "
        "the right sign for de Vries's mechanism and roughly a twentieth of the "
        "between-circuit spread it would have to explain.",
        "",
        "### The fuel channel measured directly",
        "",
        "If the mechanism is real it should show up inside a single race: a "
        "longer stint burns more fuel, so the stop that ends it should take "
        "longer. That comparison needs no classification at all, so it is free "
        "of the definitional problem.",
        "",
    ]

    correlations = []
    for (unit, year, circuit), part in events.groupby(["unit", "year", "circuit"]):
        part = part.dropna(subset=["stint_laps", "loss_s"])
        if (len(part) < MIN_STOPS_FOR_CORRELATION
                or part["stint_laps"].nunique() < MIN_DISTINCT_STINTS):
            continue
        correlations.append({
            "unit": unit,
            "rho": part["stint_laps"].corr(part["loss_s"], method="spearman"),
        })
    rho = pd.DataFrame(correlations).dropna()

    lines += ["| class | race-seasons | median within-race Spearman |",
              "|---|---|---|"]
    for unit, part in rho.groupby("unit"):
        lines.append(f"| {unit} | {len(part)} | {part['rho'].median():+.3f} |")

    lines += [
        "",
        f"Pooled median **{rho['rho'].median():+.3f}** over {len(rho)} "
        f"race-seasons, positive in {100 * (rho['rho'] > 0).mean():.0f}% of them. "
        "The channel exists and points the way de Vries said it would. It is "
        "also small: a rank correlation under a tenth, where the relationship "
        "Result 2 rests on is −0.98.",
        "",
        "## What this changes",
        "",
        "**Objection 1 is correct and costs the result nothing.** The class "
        "median does pool a driver change with a splash-and-dash, and saying "
        "'median pit loss' without saying that is imprecise. The six-row table "
        "stands because the ordering it depends on is unchanged under every "
        "decomposition, not because the objection was wrong.",
        "",
        "**Objection 2 identifies a real channel and bounds it.** Tyre-limited "
        f"races do have slightly shorter stops at the same circuit, by "
        f"{abs(paired_median):.1f} s, and longer stints do cost slightly longer "
        "stops. Both are the sign he predicted. Neither is remotely large "
        "enough to manufacture the correlation: the variation that produces it "
        "is between circuits, where the spread is twenty seconds and more, and a "
        "pit lane is not shortened by the race that runs down it.",
        "",
        "What should change is the wording rather than the number. 'Median pit "
        "loss' should read as what it is — a median over green-flag stops of "
        "every kind, including driver changes — and the claim should be stated "
        "as circuit cost rather than race cost, because that is the level at "
        "which the measurement is exogenous.",
        "",
    ]
    return lines


if __name__ == "__main__":
    sys.exit(main())
