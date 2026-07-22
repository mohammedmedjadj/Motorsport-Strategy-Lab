"""F1 net degradation across the whole calendar, from the Kaggle per-lap history.

The breadth complement to the FastF1 degradation model (which is deep but only
four circuits). Reads ``data/external/f1/`` and writes
``data/derived/f1/history_degradation.csv`` + ``reports/f1/degradation_history.md``.

Usage::

    python scripts/run_f1_history_degradation.py            # 2011+ (default)
    python scripts/run_f1_history_degradation.py --from 2022
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.f1_history_loader import (  # noqa: E402
    DEFAULT_ERA_START,
    load_f1_lap_history,
    regulation_era,
)
from src.degradation.f1_history import fit_history_degradation  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402

OUT_CSV = F1_DERIVED_DIR / "history_degradation.csv"
OUT_REPORT = F1_REPORTS_DIR / "degradation_history.md"
_CURRENT_ERA = regulation_era(__import__("datetime").date.today().year)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=DEFAULT_ERA_START)
    args = ap.parse_args()

    df = load_f1_lap_history(era_start=args.start)

    # Exclude wet races so a wet-to-dry track is not read as tyre wear — the
    # weather layer's purpose. Uses the committed weather.csv if it exists.
    wet: set[tuple[str, int]] = set()
    weather_csv = F1_DERIVED_DIR / "weather.csv"
    if weather_csv.exists():
        wx = pd.read_csv(weather_csv)
        wet = {(r["circuitRef"], int(r["year"]))
               for _, r in wx[wx["wet"]].iterrows()}

    table = fit_history_degradation(df, exclude=wet)
    n_wet_excluded = len(wet & {(c, y) for c, y in
                               zip(df["circuitRef"], df["year"])})
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)

    n_circuits = table["circuit"].nunique()
    n_races = len(table)
    per_era = (table.groupby("era")
               .agg(circuits=("circuit", "nunique"), races=("circuit", "size"),
                    median_net=("net_slope_s", "median"),
                    median_tyre=("tyre_slope_s", "median"),
                    median_fuel=("fuel_evo_slope_s", "median"))
               .reset_index())
    tyre_positive = (table["tyre_slope_s"] > 0).mean()

    lines = [
        "# F1 degradation — full-calendar breadth (Kaggle per-lap history)",
        "",
        "The FastF1 model in [degradation_phase2.md](degradation_phase2.md) is "
        "**deep** (tyre compound, per-lap Safety-Car/VSC flags) but covers only "
        "the four scoped circuits. This layer is the **breadth** complement: the "
        "same net-slope definition fitted per race across the *whole calendar* "
        "from Kaggle per-lap times, trading compound/flag fidelity for coverage.",
        "",
        f"Coverage: **{n_circuits} circuits, {n_races} race-seasons** fitted "
        f"(was 4 via FastF1), after excluding **{n_wet_excluded} wet races** "
        "(via the weather layer) so a wet-to-dry track is not mistaken for tyre "
        "wear. Slopes are fitted with driver-and-stint fixed effects removed, on "
        "green laps only (field-wide slow laps inferred as neutralisations and "
        "dropped, since Kaggle carries no SC flag).",
        "",
        "## Solving the fuel/tyre confound (not just documenting it)",
        "",
        "A single 'net slope' in F1 is dominated by **fuel burn**: the car sheds "
        "~1.5 kg/lap and speeds up, which can swamp or invert tyre wear — the "
        "median net slope is near zero or negative for that reason, not because "
        "tyres improve. But **F1 has had no refuelling since 2010**, so fuel mass "
        "is a whole-race function of the *absolute* lap while tyre age *resets "
        "each stint*. The two stop being collinear, so a two-regressor fit "
        "`lap_time ~ driver + tyre*tyre_age + fuel_evo*lap` **separates them** — "
        "something the endurance data fundamentally cannot do, because every "
        "endurance stop refuels and re-aligns fuel with tyre age.",
        "",
        f"The isolated tyre slope is **positive in {tyre_positive:.0%} of "
        "races** (physically correct — tyres wear), while the fuel/evolution "
        "term carries the negative whole-race trend. This is the direct answer "
        "to the 'fuel and tyre age are confounded' limitation.",
        "",
        "## Regulation eras — and why 2026 is walled off",
        "",
        "Degradation is comparable only **within** a regulation era. The artifact "
        "carries an `era` column so no fit is ever pooled across a rules boundary:",
        "",
        "| Era | Circuits | Race-seasons | Median net | Median tyre-only | Median fuel/evo |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in per_era.iterrows():
        lines.append(f"| {r['era']} | {int(r['circuits'])} | {int(r['races'])} "
                     f"| {r['median_net']:+.4f} | {r['median_tyre']:+.4f} "
                     f"| {r['median_fuel']:+.4f} |")
    lines += [
        "",
        f"**2026 is its own era (`2026-nextgen`), the deepest break in a "
        "generation** — MGU-H removed and ~50% electric power, ~30% less race "
        "fuel, active aero with a Manual Override Mode replacing DRS, narrower "
        "lighter cars and narrower tyres. Less fuel and narrower tyres move both "
        "the tyre and fuel terms this report separates, so no pre-2026 slope "
        "transfers. This source stops at 2024; a 2026 race (current era: "
        f"`{_CURRENT_ERA}`) is modelled from 2026 data via the live FastF1 "
        "pipeline, never from here.",
        "",
        "## Highest and lowest tyre wear, current era (`ground-effect`)",
        "",
        "Ranked by the **isolated tyre slope**, not the fuel-confounded net:",
        "",
        "| Circuit | Year | Tyre-only (s/lap) | Fuel/evo | Net | Green laps |",
        "|---|---|---|---|---|---|",
    ]
    ge = (table[table["era"] == "ground-effect"]
          .dropna(subset=["tyre_slope_s"])
          .sort_values("tyre_slope_s", ascending=False))
    for _, r in pd.concat([ge.head(6), ge.tail(4)]).iterrows():
        lines.append(f"| {r['circuit']} | {int(r['year'])} | "
                     f"{r['tyre_slope_s']:+.4f} | {r['fuel_evo_slope_s']:+.4f} "
                     f"| {r['net_slope_s']:+.4f} | {int(r['n_laps'])} |")
    lines += [
        "",
        "## Honest limits of this source",
        "",
        "- No tyre compound: a slope is the net across whatever compounds ran in "
        "the race, not split by tyre.",
        "- No SC/VSC flag: neutralised laps are *inferred* from field-wide slow "
        "laps, a heuristic, not the ground truth FastF1 provides.",
        "- Cross-season stability within an era is not asserted here; each row is "
        "a self-contained per-race fit (the same discipline as the endurance "
        "reports).",
        "- **Scrubbed (lightly-used) tyres do not bias the slope.** Kaggle has no "
        "tyre-life column, so a stint's tyre age is counted from 0, whereas a "
        "scrubbed set really starts a few laps old. But a per-stint age offset "
        "shifts only the *intercept*: `lap = a + b*(age + scrub)` = "
        "`(a + b*scrub) + b*age`, and the per-(driver, stint) fixed effect "
        "absorbs the `b*scrub` term, leaving the slope `b` unchanged — so the "
        "net and tyre-only wear rates are robust to scrubbing. Only an absolute "
        "tyre-age readout would be affected, which this layer never uses. (The "
        "high-fidelity FastF1 model sidesteps it entirely via the real `TyreLife`"
        " / `FreshTyre` columns.)",
    ]
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(per_era.to_string(index=False))
    print(f"\n{n_circuits} circuits, {n_races} race-seasons fitted "
          f"({n_wet_excluded} wet races excluded).")
    print(f"wrote {OUT_CSV}\nwrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
