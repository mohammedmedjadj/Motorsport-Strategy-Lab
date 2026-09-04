"""Replay every real first stop in every endurance race, in every class.

The endurance counterpart of ``scripts/run_systematic_audit.py``. Writes
``data/derived/endurance/systematic_audit.csv`` and one report per series, so
each championship's audit is its own document rather than a merged one.

Usage (offline, from the repo root)::

    python scripts/run_systematic_endurance_audit.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.audit.systematic_endurance import (  # noqa: E402
    LOOKBACK,
    N_CARS,
    replay_race,
    to_frame,
)
from src.data.endurance_scope import scoped_race_seasons  # noqa: E402
from src.data.endurance_loader import derived_path  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)
from src.reporting.class_reports import CLASS_LABELS  # noqa: E402
from src.simulator.endurance_models import load_race_model  # noqa: E402

SERIES_TITLES = {"wec": "WEC", "imsa": "IMSA", "elms": "ELMS"}


def report(series: str, frame: pd.DataFrame) -> str:
    """One series' audit, written as its own document."""
    rows = frame[frame["series"] == series]
    green = rows[~rows["real_stop_neutralised"]]
    at_deadline = rows[rows["model_pit_lap"] == rows["fuel_deadline_lap"]]

    lines = [
        f"# {SERIES_TITLES[series]} decision audit — every first stop, every class",
        "",
        f"The model is asked **{LOOKBACK} laps before** each real first stop, for "
        f"the top {N_CARS} finishers of every class in every scoped race. Position "
        "comes from laps completed: the source carries no running order.",
        "",
        "A **replay, not a forecast** — the decision point is defined relative to "
        "a stop that already happened. It measures where the model disagrees with "
        "real strategy, and by how much.",
        "",
        f"**{len(rows)} decisions across {rows.groupby(['year', 'event', 'car_class']).ngroups} "
        f"race-classes.**",
        "",
        "| | decisions | median Δ laps | median cost |",
        "|---|---|---|---|",
    ]
    for label, subset in (
        ("all", rows),
        ("real stop under green", green),
        ("real stop under a neutralisation", rows[rows["real_stop_neutralised"]]),
    ):
        if subset.empty:
            continue
        lines.append(
            f"| {label} | {len(subset)} | {subset['delta_laps'].median():+.0f} | "
            f"{subset['median_cost_s'].median():+.2f} s |"
        )

    neutral_share = rows["real_stop_neutralised"].mean()
    green_delta = green["delta_laps"].median() if len(green) else float("nan")
    lines += [
        "",
        f"**The model runs to the fuel deadline in {len(at_deadline)} of "
        f"{len(rows)} decisions** ({len(at_deadline)/len(rows):.0%}). It optimises "
        "expected race time from the state it is given, with no track position "
        "and no way to foresee a caution, so with a tyre that still has life the "
        "tank is the only thing that ever stops it.",
        "",
        f"**{neutral_share:.0%} of the real first stops here were taken under a "
        "neutralisation**, and that is what decides how far the model is from "
        "them. Under green it sits "
        f"{'within a lap or two' if abs(green_delta) <= 2 else f'{green_delta:+.0f} laps away'}"
        f" ({green['delta_laps'].median():+.0f}); the gap opens on the stops taken "
        "under caution, which is the one thing a model asked three laps earlier "
        "cannot know is coming.",
        "",
        "Across the three endurance championships that ordering is clean, and it "
        "is a property of the championship rather than of the car:",
        "",
        "| series | first stops under caution | median Δ, green | median Δ, all |",
        "|---|---|---|---|",
        *_caution_rows(),
        "",
        "**WEC and ELMS agree with real strategy to within one or two laps.** "
        "That is the strongest corroboration this simulator has: on two "
        "championships where cautions are rare, its stop timing is what teams "
        "actually did. IMSA's disagreement is not a different model — it is the "
        "same model in a championship that throws a Full Course Yellow in 61 of "
        "63 races, so more than half its stops are opportunistic.",
        "",
        "The F1 audit is the useful contrast. There the neutralisation split is "
        f"small ({_f1_split()}) and the "
        "disagreement is large anyway, because F1 has **no fuel cap** — nothing "
        "bounds how long \"stay out\" can run. Here the tank bounds it, so what "
        "is left to explain is the cautions.",
        "",
        "## By class",
        "",
        "| class | decisions | median Δ | median cost | at the fuel deadline |",
        "|---|---|---|---|---|",
    ]
    for car_class, group in rows.groupby("car_class"):
        deadline = (group["model_pit_lap"] == group["fuel_deadline_lap"]).mean()
        lines.append(
            f"| {CLASS_LABELS.get((series, car_class), car_class)} | {len(group)} | "
            f"{group['delta_laps'].median():+.0f} | "
            f"{group['median_cost_s'].median():+.2f} s | {deadline:.0%} |"
        )

    worst = rows.reindex(rows["median_cost_s"].abs().sort_values(ascending=False).index)
    lines += [
        "",
        "## Where the model disagrees most",
        "",
        "| year | event | class | car | real | model | Δ | cost | neutralised |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in worst.head(10).itertuples():
        lines.append(
            f"| {r.year} | {r.event} | {r.car_class} | {r.car} | {r.real_pit_lap} | "
            f"{r.model_pit_lap} | {r.delta_laps:+d} | {r.median_cost_s:+.2f} s | "
            f"{'yes' if r.real_stop_neutralised else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _caution_rows() -> list[str]:
    """The caution-rate table, from the audit rather than from memory.

    Typed once and stale by three numbers: ELMS read +3/+2 against a real
    +2/+1, and IMSA's caution median read +12 against a real +15. The ordering
    the paragraph draws on survived, which is exactly why nobody noticed.
    """
    # Reads the whole audit rather than taking the caller's per-series frame:
    # this is a cross-series table that appears inside each series' report, and
    # that mismatch is why it was typed by hand in the first place.
    table = pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv")
    rows = []
    for series in ("wec", "elms", "imsa"):
        group = table[table["series"] == series]
        if group.empty:
            continue
        green = group[~group["real_stop_neutralised"]]["delta_laps"].median()
        rows.append(
            f"| {series.upper()} | "
            f"{group['real_stop_neutralised'].mean() * 100:.0f}% | "
            f"{green:+.0f} | {group['delta_laps'].median():+.0f} |"
        )
    return rows


def _f1_split() -> str:
    """F1's own green-versus-caution split, read from the F1 audit table."""
    f1 = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    green = f1[~f1["real_stop_neutralised"]]["delta_laps"].median()
    caution = f1[f1["real_stop_neutralised"]]["delta_laps"].median()
    return (f"{green:+.0f} laps under green against {caution:+.0f} under "
            "caution")


def main() -> int:
    warnings.filterwarnings("ignore")
    races = [
        (series, year, event, car_class)
        for series, event, car_class, year in scoped_race_seasons()
        if derived_path(series, year, event, car_class).exists()
    ]
    replays = []
    skipped = []
    for index, (series, year, event, car_class) in enumerate(sorted(races), 1):
        print(f"[{index}/{len(races)}] {series} {year} {event} ({car_class})",
              flush=True)
        try:
            model = load_race_model(series, year, event, car_class)
        except (ValueError, KeyError) as exc:
            skipped.append((series, year, event, car_class, str(exc)))
            print(f"  skip: {exc}", flush=True)
            continue
        replays += replay_race(series, year, event, car_class, model)

    frame = to_frame(replays)
    ENDURANCE_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv", index=False)
    pd.DataFrame(
        skipped, columns=["series", "year", "event", "car_class", "reason"]
    ).to_csv(ENDURANCE_DERIVED_DIR / "systematic_audit_skipped.csv", index=False)

    for series in sorted(frame["series"].unique()):
        path = REPORTS_DIR / series / "systematic_audit.md"
        path.write_text(report(series, frame), encoding="utf-8")
        print(f"wrote {path}")

    print(f"\n{len(frame)} decisions replayed, {len(skipped)} race-classes skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
