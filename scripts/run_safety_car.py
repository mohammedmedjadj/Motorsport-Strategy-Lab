"""Run the Phase 3 SC/VSC probability modelling.

Extends the event-history window to 2018-2025 (validated with Mohammed):
SC causes are dominated by circuit geometry, which is far more stable
across seasons than car/tyre behaviour. Editions that were not held
(COVID cancellations) or fail to load are listed explicitly in the report
— never silently skipped.

Outputs: ``data/derived/sc_events.csv``, ``data/derived/sc_model.csv``,
``reports/safety_car_phase3.md``.

Usage (from the repo root)::

    python scripts/run_safety_car.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.ingestion.config import DERIVED_DIR, REPORTS_DIR, RaceId  # noqa: E402
from src.ingestion.loader import load_race  # noqa: E402
from src.safety_car.dataset import RaceEvents, extract_race_events  # noqa: E402
from src.safety_car.model import (  # noqa: E402
    duration_summary,
    occurrence_probability,
    per_lap_rate,
)

#: Extended SC-history window (Phase 3 scoping decision).
SC_SEASONS: tuple[int, ...] = tuple(range(2018, 2026))

CIRCUIT_GPS: tuple[tuple[str, str], ...] = (
    ("Monaco", "monaco"),
    ("Singapore", "singapore"),
    ("Spanish", "barcelona"),
    ("Japanese", "suzuka"),
)


def collect_events() -> tuple[list[RaceEvents], list[str]]:
    """Load every candidate edition; return extracted events + skip notes."""
    collected: list[RaceEvents] = []
    skipped: list[str] = []
    for gp_name, circuit in CIRCUIT_GPS:
        for season in SC_SEASONS:
            race = RaceId(season=season, gp_name=gp_name, circuit=circuit)
            print(f"Loading {race.slug} ...", flush=True)
            try:
                raw = load_race(race)
            except Exception as exc:  # noqa: BLE001 - record and move on
                skipped.append(f"{race.slug}: {type(exc).__name__}: {exc}")
                continue
            collected.append(extract_race_events(raw))
    return collected, skipped


def events_frame(collected: list[RaceEvents]) -> pd.DataFrame:
    rows = [
        {
            "circuit": re.circuit,
            "season": re.season,
            "kind": e.kind,
            "start_lap": e.start_lap,
            "end_lap": e.end_lap,
            "duration_laps": e.duration_laps,
            "start_time_s": round(e.start_time_s, 3),
        }
        for re in collected
        for e in re.events
    ]
    return pd.DataFrame(
        rows, columns=["circuit", "season", "kind", "start_lap", "end_lap",
                       "duration_laps", "start_time_s"]
    )


def build_report(collected: list[RaceEvents], skipped: list[str]) -> tuple[str, pd.DataFrame]:
    lines = [
        "# Phase 3 — Safety Car / VSC probability model",
        "",
        "Event history 2018-2025 extracted from `TrackStatus` (SC=code 4,",
        "VSC=codes 6/7, red flag=code 5). Estimates are posterior means with",
        "95% equal-tailed credible intervals under a Jeffreys prior — with",
        "6-8 editions per circuit, interval width IS the result; point",
        "values alone would be false precision.",
        "",
    ]
    if skipped:
        lines += ["## Editions not included", ""]
        lines += [f"- {s}" for s in skipped]
        lines += ["", "(2020-2021 gaps are COVID cancellations — those races never took place.)", ""]

    model_rows: list[dict[str, object]] = []
    for circuit in sorted({re.circuit for re in collected}):
        races = sorted(
            (re for re in collected if re.circuit == circuit), key=lambda r: r.season
        )
        n = len(races)
        exposure = sum(r.laps_completed for r in races)
        lines += [f"## {circuit} ({n} editions, {exposure} race laps observed)", ""]
        lines += ["| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |",
                  "|---|---|---|---|---|---|---|"]
        for r in races:
            lines.append(
                f"| {r.season} | {r.laps_completed} | {r.count('SC')} | {r.count('VSC')} "
                f"| {r.count('RED')} | {r.deployment_laps('SC') or '-'} "
                f"| {r.deployment_laps('VSC') or '-'} |"
            )
        lines.append("")

        row: dict[str, object] = {"circuit": circuit, "n_editions": n,
                                  "laps_exposure": exposure}
        for kind in ("SC", "VSC"):
            k_races = sum(1 for r in races if r.count(kind) > 0)
            k_events = sum(r.count(kind) for r in races)
            occ = occurrence_probability(k_races, n)
            rate = per_lap_rate(k_events, exposure)
            durations = [e.duration_laps for r in races for e in r.events if e.kind == kind]
            dur = duration_summary(durations)
            lines += [
                f"**{kind}** — races with >= 1: {k_races}/{n}; deployments: {k_events}.",
                f"- P(>= 1 per race) = {occ.fmt()}",
                f"- Per-lap deployment rate = {rate.fmt(5)}",
                f"- Durations (laps): n={dur['n']}, mean={dur['mean']:.1f}, "
                f"min={dur['min']:.0f}, max={dur['max']:.0f}"
                if dur["n"] else "- Durations: no events observed",
                "",
            ]
            row[f"{kind.lower()}_races_with_event"] = k_races
            row[f"{kind.lower()}_deployments"] = k_events
            row[f"{kind.lower()}_p_occurrence"] = occ.mean
            row[f"{kind.lower()}_p_occurrence_ci_low"] = occ.ci_low
            row[f"{kind.lower()}_p_occurrence_ci_high"] = occ.ci_high
            row[f"{kind.lower()}_rate_per_lap"] = rate.mean
            row[f"{kind.lower()}_rate_ci_low"] = rate.ci_low
            row[f"{kind.lower()}_rate_ci_high"] = rate.ci_high
            row[f"{kind.lower()}_mean_duration_laps"] = dur["mean"]
        model_rows.append(row)

    lines += [
        "## Statistical reliability — read this before trusting any number",
        "",
        "- **6-8 races per circuit is a structurally small sample.** The",
        "  credible intervals span factors of 2-4x; any strategy conclusion",
        "  sensitive to the exact SC probability inside those bounds is not",
        "  supported by this data.",
        "- **Deployment laps cluster early** (lap-1 incidents) at some",
        "  circuits; the per-lap rate model assumes a constant hazard and",
        "  therefore understates lap-1 risk and overstates mid-race risk.",
        "  Listed deployment laps above let the reader judge; a two-bin",
        "  hazard is possible future work if Phase 5 shows it matters.",
        "- **Circuit changes are absorbed silently** (e.g. Singapore's 2023",
        "  layout shortening) — the model treats all editions of a circuit",
        "  as exchangeable, which is an approximation.",
        "- **Red flags are counted but not modelled** (too rare: the",
        "  simulator scope excludes them, documented in Phase 4).",
        "- SC and VSC are modelled independently; in reality a VSC sometimes",
        "  escalates into an SC, so the two rates are not fully independent.",
        "",
    ]
    return "\n".join(lines), pd.DataFrame(model_rows)


def main() -> int:
    collected, skipped = collect_events()
    events = events_frame(collected)
    events.to_csv(DERIVED_DIR / "sc_events.csv", index=False)

    report, model = build_report(collected, skipped)
    model.to_csv(DERIVED_DIR / "sc_model.csv", index=False)
    (REPORTS_DIR / "safety_car_phase3.md").write_text(report, encoding="utf-8")
    print(f"\n{len(collected)} editions loaded, {len(skipped)} skipped, "
          f"{len(events)} events extracted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
