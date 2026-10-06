"""How much of the endurance degradation fit is actually resolved?

The Formula 1 side already refuses to show its degradation figure without
saying how much of it is indistinguishable from zero: ``NCoefCrossingZero`` and
``PctCoefCrossingZero`` are generated macros, and the paper quotes them twice.
The endurance side has no such guard, and its figure is shown without one.

This closes that gap, and it does not flatter the answer. Three things are
measured per series, each series on its own because they are different
championships with different calendars and different car classes:

1. **Resolution.** How many fitted net slopes have a cluster-robust interval
   containing zero, and how many are negative outright. A negative slope is not
   a sign error: ``src/degradation/endurance.py`` substitutes
   ``laps_since_refuel`` for lap number, which leaves nothing carrying track
   evolution, so evolution is currently attributed to tyre age with its sign
   inverted. That is diagnosed in ``reports/track_evolution_omitted_variable.md``
   and it is not fixed here.

2. **Separability.** Whether fuel load and tyre age can be told apart at all.
   They cannot, almost everywhere, and the module says so already — this counts
   it per series so the paper can quote a number rather than a claim.

3. **Season completeness.** 2026 is partial and the three series are partial to
   very different degrees. A per-season slope from a third of a calendar is not
   the same measurement as one from a full calendar, and nothing in the fits
   table marks the difference.

Writes one report per series, plus
``data/derived/endurance/endurance_slope_resolution.csv``.

Usage (offline, from the repo root)::

    python scripts/run_endurance_resolution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.degradation.endurance import SEPARABILITY_LIMIT  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    REPORTS_DIR,
)

FITS = ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv"
OUT_CSV = ENDURANCE_DERIVED_DIR / "endurance_slope_resolution.csv"

#: Report directory per series. ELMS has no entry in ingestion.config, so the
#: three are spelled out here rather than half-imported.
REPORT_DIR = {
    "wec": REPORTS_DIR / "wec",
    "imsa": REPORTS_DIR / "imsa",
    "elms": REPORTS_DIR / "elms",
}

#: Printed name. "WEC" and "IMSA" are initialisms, "ELMS" likewise; none of the
#: three is ever folded into the others anywhere in this repository.
LABEL = {"wec": "WEC", "imsa": "IMSA", "elms": "ELMS"}

#: Indefinite article for each label, by how the initialism is said aloud:
#: "weck" takes "a", "IMSA" and "ELMS" open on a vowel and take "an".
ARTICLE = {"wec": "a", "imsa": "an", "elms": "an"}

#: The season whose completeness is in question. It is in progress, so its
#: fits rest on part of a calendar.
PARTIAL_SEASON = 2026


def _join(items: list[str]) -> str:
    """Comma-separated, with "and" before the last — a list a person would say."""
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def load() -> pd.DataFrame:
    fits = pd.read_csv(FITS)
    fits["crosses_zero"] = (fits["ci_low"] <= 0) & (fits["ci_high"] >= 0)
    fits["negative"] = fits["net_slope"] < 0
    fits["ci_width"] = fits["ci_high"] - fits["ci_low"]
    return fits


def resolution_table(fits: pd.DataFrame) -> pd.DataFrame:
    """One row per series and class: the shape of the evidence under each fit."""
    grouped = fits.groupby(["series", "car_class"])
    table = grouped.agg(
        n_fits=("net_slope", "size"),
        n_crossing_zero=("crosses_zero", "sum"),
        n_negative=("negative", "sum"),
        n_separable=("separable", "sum"),
        median_abs_slope=("net_slope", lambda s: s.abs().median()),
        median_ci_width=("ci_width", "median"),
        median_fuel_deg_corr=("fuel_deg_corr", "median"),
        n_laps=("n_laps", "sum"),
    ).reset_index()
    table["pct_crossing_zero"] = (
        100 * table["n_crossing_zero"] / table["n_fits"]
    ).round(0)
    table["pct_negative"] = (100 * table["n_negative"] / table["n_fits"]).round(0)
    for column in ("median_abs_slope", "median_ci_width", "median_fuel_deg_corr"):
        table[column] = table[column].round(4)
    return table.sort_values(["series", "car_class"]).reset_index(drop=True)


def _resolution_section(part: pd.DataFrame, label: str) -> list[str]:
    crossing = int(part["crosses_zero"].sum())
    negative = int(part["negative"].sum())
    total = len(part)
    lines = [
        "## What the fitted slopes resolve",
        "",
        f"{label} contributes **{total}** race-class-season fits across "
        f"{part['circuit_canonical'].nunique()} circuits and "
        f"{part['car_class'].nunique()} "
        f"{'class' if part['car_class'].nunique() == 1 else 'classes'}, on "
        f"{int(part['n_laps'].sum()):,} green laps.",
        "",
        f"**{crossing} of {total}** ({100 * crossing / total:.0f}%) have a "
        "cluster-robust interval containing zero. On those races the data "
        "cannot distinguish tyre degradation from none.",
        "",
        f"**{negative} of {total}** ({100 * negative / total:.0f}%) fit a "
        "negative net slope, meaning lap times that improve with tyre age. "
        "That is a known defect rather than a finding: the endurance model "
        "uses `laps_since_refuel` in place of lap number, which is right for "
        "fuel and leaves nothing carrying track evolution, so evolution is "
        "absorbed into the tyre-age term with its sign inverted. It is "
        "diagnosed in `reports/track_evolution_omitted_variable.md` and it is "
        "not fixed.",
        "",
        "| Class | Fits | Interval contains zero | Negative slope | Median \\|slope\\| (s/lap) | Median interval width (s/lap) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for car_class, rows in part.groupby("car_class"):
        n = len(rows)
        zero = int(rows["crosses_zero"].sum())
        neg = int(rows["negative"].sum())
        lines.append(
            f"| {car_class} | {n} | {zero} ({100 * zero / n:.0f}%) | "
            f"{neg} ({100 * neg / n:.0f}%) | "
            f"{rows['net_slope'].abs().median():.4f} | "
            f"{rows['ci_width'].median():.4f} |"
        )
    lines.append("")
    return lines


def _separability_section(part: pd.DataFrame, label: str) -> list[str]:
    separable = int(part["separable"].sum())
    total = len(part)
    corr = part["fuel_deg_corr"]
    lines = [
        "## Fuel and tyre wear cannot be told apart",
        "",
        f"Fuel and tyre age are separable in **{separable} of {total}** "
        f"{label} fits. The test is the correlation between the two "
        "regressors after absorbing the fixed effects, against a limit of "
        f"{SEPARABILITY_LIMIT:.2f}; here the median correlation is "
        f"**{corr.median():+.3f}** and it ranges from {corr.min():+.3f} to "
        f"{corr.max():+.3f}.",
        "",
        "This is why the reported quantity is a *net* slope and not a "
        "degradation slope. Endurance cars refuel at almost every stop and "
        "change tyres at the same visit, so the two regressors move together "
        "and fitting both produces a collinear ridge rather than a "
        "measurement. The decomposition is carried in the artifact as a "
        "diagnostic and is not quoted anywhere as a coefficient.",
        "",
    ]
    if separable:
        rows = part[part["separable"]]
        where = sorted(rows["circuit_canonical"].unique())
        lines += [
            "The exceptions are worth naming, because they are not spread "
            f"across the calendar: all {separable} sit at "
            f"{_join(where)}, in "
            f"{_join(sorted(str(year) for year in rows['season'].unique()))}.",
            "",
        ]
    else:
        lines += [
            "There are no exceptions in this series. Every fit is above the "
            "limit.",
            "",
        ]
    return lines


def _coverage_section(part: pd.DataFrame, label: str, article: str) -> list[str]:
    by_season = part.groupby("season").agg(
        fits=("net_slope", "size"),
        circuits=("circuit_canonical", "nunique"),
        laps=("n_laps", "sum"),
    )
    heading = (
        f"How complete {PARTIAL_SEASON} is"
        if PARTIAL_SEASON in by_season.index
        else "Which seasons are behind this"
    )
    lines = [
        f"## {heading}",
        "",
        "| Season | Fits | Circuits | Green laps |",
        "| --- | ---: | ---: | ---: |",
    ]
    for season, row in by_season.iterrows():
        lines.append(
            f"| {int(season)} | {int(row['fits'])} | {int(row['circuits'])} | "
            f"{int(row['laps']):,} |"
        )
    lines.append("")

    if PARTIAL_SEASON not in by_season.index:
        lines += [
            f"{label} has no {PARTIAL_SEASON} data at all. Every "
            f"{label} number in this project therefore stops at "
            f"{int(by_season.index.max())}, which is a scope limit rather "
            "than a gap in the fit.",
            "",
        ]
        return lines

    partial = by_season.loc[PARTIAL_SEASON]
    reference = by_season.drop(index=PARTIAL_SEASON)
    full = reference["circuits"].max()
    share = 100 * partial["circuits"] / full
    lines += [
        f"{PARTIAL_SEASON} is in progress: **{int(partial['circuits'])} "
        f"circuits** against a best full season of {int(full)}, so about "
        f"{share:.0f}% of a calendar. Its per-race fits are as valid as any "
        f"other race's. What is not safe is {article} {label}-wide "
        f"{PARTIAL_SEASON} "
        "figure, which is computed on a fraction of the season while nothing "
        "in the artifact marks it as such.",
        "",
    ]
    return lines


def write_series_report(fits: pd.DataFrame, series: str) -> Path:
    part = fits[fits["series"] == series]
    label = LABEL[series]
    out = REPORT_DIR[series] / "slope_resolution.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"<!-- generated by scripts/run_endurance_resolution.py -->",
        "",
        f"# {label}: how much of the degradation fit is resolved",
        "",
        "Generated. Do not edit by hand.",
        "",
        "The Formula 1 degradation figure is never shown without the share of "
        "its slopes that cannot be distinguished from zero. This is the same "
        f"accounting for {label}, kept separate from the other endurance "
        "championships because they run different calendars, different car "
        "classes and different race lengths, and an average over all three "
        "would describe none of them.",
        "",
    ]
    lines += _resolution_section(part, label)
    lines += _separability_section(part, label)
    lines += _coverage_section(part, label, ARTICLE[series])
    lines += [
        "## What this costs",
        "",
        "Nothing here is screened out. Every fit is carried forward into the "
        "transfer and strategy layers exactly as measured, including the ones "
        "whose interval contains zero and the ones that come out negative. "
        "Dropping them would select on the dependent variable, since the "
        "races with tight slopes are also the ones likeliest to transfer, and "
        "the transfer result would then be partly an artefact of the screen.",
        "",
        "The price is that a weak transfer score mixes genuine instability "
        "with parameters the data never pinned down, and this work does not "
        "separate the two.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    fits = load()
    table = resolution_table(fits)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(Path.cwd())}")

    for series in sorted(fits["series"].unique()):
        if series not in REPORT_DIR:
            raise KeyError(
                f"series {series!r} has no report directory; add it to "
                "REPORT_DIR rather than letting it fall out of the report"
            )
        out = write_series_report(fits, series)
        print(f"wrote {out.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
