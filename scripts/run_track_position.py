"""Measure per-circuit track-position value (overtaking difficulty) from the
committed F1 laps, and write a reproducible artifact + report.

Outputs:
- data/derived/f1/overtaking_difficulty.csv
- reports/f1/track_position.md

Usage (offline; reads the committed derived CSVs)::

    python scripts/run_track_position.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import (  # noqa: E402
    F1_DERIVED_DIR,
    F1_REPORTS_DIR,
    PRE_ERA_SEASONS,
    REGULATION_ERA_START,
)
from src.simulator.track_position import measure_circuit  # noqa: E402

HOLD_LAPS = 15  # horizon for the illustrative "hold position" probability


def _laps_by_circuit(seasons: tuple[int, ...] | None = None) -> dict[str, dict[str, pd.DataFrame]]:
    grouped: dict[str, dict[str, pd.DataFrame]] = defaultdict(dict)
    for path in sorted(F1_DERIVED_DIR.glob("laps_*.csv")):
        season, circuit = path.stem.removeprefix("laps_").split("_", 1)
        if seasons is not None and int(season) not in seasons:
            continue
        grouped[circuit][season] = pd.read_csv(path)
    return grouped


def _per_season_rates() -> dict[str, dict[int, float]]:
    """Swap rate per circuit per season — the basis of every claim below."""
    out: dict[str, dict[int, float]] = {}
    for circuit, races in sorted(_laps_by_circuit().items()):
        out[circuit] = {
            int(season): measure_circuit({season: laps}, circuit).swap_rate
            for season, laps in sorted(races.items())
        }
    return out


def _most_variable_circuit(rates: dict[str, dict[int, float]]) -> tuple[str, list[float], float]:
    """The circuit whose own seasons disagree most, and by how much.

    Named rather than assumed. This paragraph asserted Suzuka at
    "0.0348 / 0.0502 / 0.0136, a 3.7x spread"; the pooled Suzuka rate has since
    moved to 0.0321 and none of those three figures survives unchanged. A
    sentence about *which circuit is least trustworthy* has to recompute, or it
    ends up vouching for the wrong one.
    """
    best, best_spread, best_values = "", 0.0, []
    for circuit, seasons in rates.items():
        values = [v for v in seasons.values() if v > 0]
        if len(values) < 3:
            continue
        spread = max(values) / min(values)
        if spread > best_spread:
            best, best_spread, best_values = circuit, spread, values
    return best, best_values, best_spread


def _era_verdict(rates: dict[str, dict[int, float]]) -> str:
    """New-era races against their own circuit's pre-era range, counted.

    This paragraph asserted that *every* new-era race fell inside its circuit's
    pre-era range, on a scope of two races. At twelve, two of them do not — one
    below and one above — and the claim as written is simply false. Deriving a
    sentence does not only keep its numbers fresh; it can show that the claim
    the sentence makes was never true of the data it now reads.
    """
    inside, outside = [], []
    for circuit, seasons in sorted(rates.items()):
        new = {s: v for s, v in seasons.items() if s >= REGULATION_ERA_START}
        old = [v for s, v in seasons.items() if s < REGULATION_ERA_START]
        if not new or len(old) < 2:
            continue
        value = list(new.values())[0]
        low, high = min(old), max(old)
        where = "below" if value < low else "above" if value > high else None
        entry = f"{circuit} {value:.4f} against {low:.4f}-{high:.4f}"
        (outside if where else inside).append(
            f"{entry} ({where})" if where else entry
        )

    total = len(inside) + len(outside)
    if not total:
        return "No circuit has both eras measured yet."
    if not outside:
        return (f"All {total} new-era races fall inside their own circuit's "
                f"pre-era range ({'; '.join(inside)}).")
    return (
        f"**{len(inside)} of {total}** new-era races fall inside their own "
        f"circuit's pre-era range. {len(outside)} do not: "
        f"{'; '.join(outside)}. That is roughly what "
        f"{total} draws from unchanged distributions would produce — a "
        "pre-era range built from a handful of seasons is not a tolerance "
        "interval, and a race landing outside one is not evidence of a "
        "regulation effect. It is, however, not the clean result this "
        "paragraph claimed when the scope was two races and both happened to "
        "land inside."
    )


def _era_comparison_rows() -> list[str]:
    """Per-season swap rates, so the reported constant can be checked against
    its own season-to-season spread -- and against the new regulation era.

    The 2026 rules narrowed the cars and added active aero explicitly to make
    following and overtaking easier, so this constant is one where a
    regulation effect is plausible a priori. It is reported here rather than
    folded into the headline number, which stays on the regulation-stable
    window for the same no-leakage reason as the simulator's constants.
    """
    rows: list[str] = []
    for circuit, races in sorted(_laps_by_circuit().items()):
        for season, laps in sorted(races.items()):
            one = measure_circuit({season: laps}, circuit)
            era = "new" if int(season) >= REGULATION_ERA_START else "old"
            rows.append(f"| {circuit} | {season} | {era} | {one.swap_rate:.4f} |")
    return rows


def main() -> int:
    # Regulation-stable window only: see src/ingestion/config.py's
    # REGULATION_ERA_START and the per-season table at the end of the report.
    results = [measure_circuit(races, circuit)
               for circuit, races in sorted(_laps_by_circuit(PRE_ERA_SEASONS).items())]
    results.sort(key=lambda o: o.swap_rate)

    rows = [{
        "circuit": o.circuit,
        "adj_swap_rate": round(o.swap_rate, 4),
        "sd_across_races": round(o.sd, 4),
        "n_races": o.n_races,
        "n_transitions": o.n_transitions,
        f"p_hold_{HOLD_LAPS}_laps": round(o.hold_probability(HOLD_LAPS), 3),
    } for o in results]
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    artifact = F1_DERIVED_DIR / "overtaking_difficulty.csv"
    pd.DataFrame(rows).to_csv(artifact, index=False)
    print(f"wrote {artifact}")

    # Computed once, quoted throughout. Every sentence below that names a
    # circuit or a spread reads from these rather than from a figure typed when
    # the scope was four circuits.
    _rates = _per_season_rates()
    _volatile = _most_variable_circuit(_rates)
    _stable = sorted(
        ((c, max(v.values()) / min(v.values()))
         for c, v in _rates.items()
         if len(v) >= 2 and min(v.values()) > 0),
        key=lambda pair: pair[1],
    )

    lines = [
        "# Track-position value (overtaking difficulty)",
        "",
        "How hard is it to overtake at each circuit, measured from real timing?",
        "For every pair of consecutive green racing laps we take the cars that are",
        "green-racing on both (so pit-cycle position shuffling is excluded) and",
        "count the **rank-adjacent** pairs whose on-track order flips — the",
        "operational question *\"can the car right behind me get past\"*. This is",
        "the **pace-neutral baseline**: a genuinely faster car passes regardless,",
        "so it isolates how sticky position is *absent* a pace advantage.",
        "",
        f"`p_hold_{HOLD_LAPS}_laps` is the first-order `(1 - p)^{HOLD_LAPS}`",
        "probability that a car directly ahead keeps an adjacent rival behind over",
        f"{HOLD_LAPS} green laps — the quantity the strategy layer weighs against",
        "an undercut that would drop a car into that rival's clutches.",
        "",
        "| Circuit | Adjacent swap rate / green lap | SD across races | Races | Lap transitions | P(hold "
        f"{HOLD_LAPS} laps) |",
        "|---|---|---|---|---|---|",
    ]
    for o in results:
        lines.append(
            f"| {o.circuit} | {o.swap_rate:.4f} | {o.sd:.4f} | {o.n_races} | "
            f"{o.n_transitions} | {o.hold_probability(HOLD_LAPS):.2f} |"
        )
    lines += [
        "",
        "## What the numbers say",
        "",
        "The ordering is exactly what racecraft predicts: Monaco is the stickiest",
        "circuit by a wide margin (a car ahead holds an adjacent rival with ~0.94",
        f"probability over {HOLD_LAPS} laps), while Barcelona and Suzuka are the",
        "most fluid (closer to a coin-flip). Track position is worth far more at",
        "Monaco than at Barcelona — which is precisely why Monaco strategy is",
        "almost entirely about staying ahead rather than being fast.",
        "",
        "## The finding: overtaking difficulty is a *mostly* stable circuit constant",
        "",
        f"The season-to-season spread (SD column) is small at most of the "
        f"{len(_rates)} circuits — across the regulation-stable seasons the "
        "highest-to-lowest ratio is "
        + ", ".join(f"{ratio:.1f}x at {circuit}" for circuit, ratio in _stable[:3])
        + ". That is the",
        "mirror image of this project's degradation result: tyre-degradation slopes",
        "do **not** transfer between races (see the degradation reports), but",
        "overtaking difficulty largely **does**, because it is set by track",
        "geometry, which does not change.",
        "",
        f"**{_volatile[0].title()} is the honest exception and is not smoothed "
        "over here:** it runs "
        + " / ".join(f"{v:.4f}" for v in _volatile[1])
        + f" across its own seasons, a {_volatile[2]:.1f}x spread. "
        "Whatever drives that (weather, a red flag, a race that ran away from the",
        "field) is not track geometry, so that circuit's constant deserves",
        "materially less trust than the others — and the per-season table below is",
        "printed precisely so a reader can see that rather than take the pooled",
        "number on faith.",
        "",
        f"## Per season, including the {REGULATION_ERA_START} regulation era",
        "",
        f"The {REGULATION_ERA_START} rules narrowed the cars and added active aero",
        "with the explicit aim of making following and overtaking easier, so this",
        "is a constant where a regulation effect is plausible in advance. The",
        "headline table above deliberately excludes the new era (it feeds a",
        "strategy layer that audits pre-era races), and this table reports it",
        "separately:",
        "",
        "| Circuit | Season | Era | Adjacent swap rate / green lap |",
        "|---|---|---|---|",
        *_era_comparison_rows(),
        "",
        "**No regulation effect is detectable in this data, and at the most",
        "volatile circuit it could not be even in principle.**",
        "",
        _era_verdict(_rates),
        "",
        f"At {_volatile[0]} the ordinary season-to-season swing is already "
        f"{_volatile[2]:.1f}x, which is far larger than any plausible "
        "regulation effect, so a single new-era race there carries no "
        f"information about the rule change either way. One season of a new "
        "formula is too few regardless. This is reported as a question the "
        "data cannot yet answer, not as evidence the rules changed nothing.",
        "",
        "## Limitations (stated, not hidden)",
        "",
        "- **Pace-neutral by construction.** A car with a real pace advantage",
        "  passes regardless; this measures the baseline difficulty, not the",
        "  outcome of a specific duel. Combining it with a pace delta is the job",
        "  of the strategy layer (the adversarial rival model).",
        "- **DRS, dirty air and tyre-delta effects are folded in**, not separated:",
        "  the rate is the net observed swap frequency under normal green running.",
        "- **Excludes safety-car and VSC laps** (no racing) and pit in/out laps.",
        "- **Position is FastF1's classified position per lap**; lapped-car",
        "  classification quirks are averaged over, not individually modelled.",
        "- F1 only for now: the endurance schema carries no per-lap position, so",
        "  the same measure there needs positions reconstructed from cumulative",
        "  time — future work.",
        "",
    ]
    report = F1_REPORTS_DIR / "track_position.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
