"""Score three simple rules against the same 1,280 decisions the audit replayed.

The audit's finding — an exact optimiser stops later than teams do, on 80-86% of
first stops — is only worth reporting if the optimiser is doing something a rule
of thumb could not. That has never been established here, and it is the first
thing a reviewer asks.

So `src/audit/baselines.py`'s three rules are run on exactly the decisions the
audit replayed, from exactly the artifacts it used, and scored on exactly its
metric: absolute lap error against what the team actually did. Nothing is
re-fitted and no decision is re-selected, so any difference is the rule, not the
sample.

Writes ``data/derived/{f1,endurance}/baseline_comparison.csv`` and
``reports/cross_series/baselines.md``.

Usage (offline, from the repo root)::

    python scripts/run_baseline_comparison.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.audit.baselines import fixed_interval, fuel_deadline, threshold  # noqa: E402
from src.audit.state import load_race_laps, state_at  # noqa: E402
from src.data.endurance_loader import slugify  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)

#: The project has no CROSS_SERIES_REPORTS_DIR constant; every cross-series
#: generator builds this path inline, so this one matches rather than inventing
#: a new convention for a single file.
from src.simulator.artifacts import load_circuit_models  # noqa: E402

CROSS_SERIES_REPORTS_DIR = REPORTS_DIR / "cross_series"

#: F1 runs a mandatory two-compound rule, so a dry race needs at least one stop.
#: B1 gets the same stop count the real strategy used, not a guess -- handing a
#: baseline the wrong plan length and then reporting that it lost would be
#: measuring the handicap, not the rule.
F1_MIN_STOPS = 1


def _f1_rows() -> pd.DataFrame:
    """One row per replayed F1 decision, with what each baseline needs."""
    audit = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    models = load_circuit_models()
    rows = []
    for index, decision in enumerate(audit.itertuples(), 1):
        circuit = str(decision.circuit)
        if circuit not in models:
            continue
        model = models[circuit]
        slug = f"{decision.season}_{circuit}"
        try:
            laps = load_race_laps(slug)
            state = state_at(laps, str(decision.driver), int(decision.decision_lap))
        except (LookupError, ValueError, FileNotFoundError):
            continue
        race_laps = int(laps["LapNumber"].max())

        # The compound actually on the car, so B2 uses the tyre being run
        # rather than a circuit average that belongs to no stint.
        compound_coefs = model.degradation.get(state.compound)
        slope = float(compound_coefs[0].mean) if compound_coefs else float("nan")
        pit_loss = float(model.pit_loss.median_s)

        b1 = fixed_interval(race_laps, F1_MIN_STOPS)
        b2 = threshold(
            int(decision.decision_lap), int(state.tyre_age),
            slope, pit_loss, race_laps,
        )
        b3 = fuel_deadline(None, refuelling_allowed=False)

        rows.append({
            "series": "f1", "season": int(decision.season), "circuit": circuit,
            "driver": str(decision.driver),
            "decision_lap": int(decision.decision_lap),
            "real_pit_lap": int(decision.real_pit_lap),
            "model_pit_lap": int(decision.model_pit_lap),
            "race_laps": race_laps, "compound": state.compound,
            "tyre_age": int(state.tyre_age),
            "slope_s_per_lap": round(slope, 5), "pit_loss_s": round(pit_loss, 2),
            "b1_lap": b1.lap, "b2_lap": b2.lap, "b3_lap": b3.lap,
            "b3_undefined": b3.undefined_reason,
        })
        if index % 50 == 0:
            print(f"  f1 {index}/{len(audit)}", flush=True)
    return pd.DataFrame(rows)


def _endurance_rows() -> pd.DataFrame:
    """The endurance counterpart, from the plans table rather than lap files.

    `multistop_plans.csv` already carries every input these rules need — race
    length, net slope, pit loss, fuel range — measured by the same code the
    optimiser consumes, so the baselines see precisely what it saw.
    """
    audit = pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv")
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    # slugify on BOTH sides, not .lower(). The plan table stores slugs
    # ("laguna_seca", "paul_ricard") and the audit table stores display names
    # ("Laguna Seca", "Paul Ricard"), so a casefold join silently drops every
    # multi-word circuit -- 83 race-class keys, a third of the endurance audit.
    # This is the third time a name-as-key join has quietly lost rows in this
    # project; the assertion below is there because being careful evidently is
    # not enough.
    plans["event_key"] = (
        plans["series"].str.lower() + "|" + plans["year"].astype(str) + "|"
        + plans["circuit_canonical"].map(slugify) + "|" + plans["car_class"]
    )
    by_key = plans.set_index("event_key")

    rows: list[dict] = []
    unmatched: list[str] = []
    for decision in audit.itertuples():
        key = (f"{str(decision.series).lower()}|{int(decision.year)}|"
               f"{slugify(str(decision.event))}|{decision.car_class}")
        if key not in by_key.index:
            unmatched.append(key)
            continue
        plan = by_key.loc[key]
        if isinstance(plan, pd.DataFrame):
            plan = plan.iloc[0]

        race_laps = int(plan["race_laps"])
        slope = float(plan["net_slope_s"])
        pit_loss = float(plan["pit_loss_s"])
        # The stops the real plan needed. Using the fuel minimum rather than the
        # tyre optimum keeps B1 a *naive* rule: it is told how long the race is
        # and how many stops the tank forces, nothing about tyres.
        n_stops = int(plan["min_stops"])

        deadline = decision.fuel_deadline_lap
        deadline = int(deadline) if pd.notna(deadline) else None

        # These are **first** stops, so the tyre has been on since lap 1 and
        # its age at the decision lap is the decision lap. Passing 0 here --
        # as this script did first -- tells B2 the car has just fitted new
        # rubber, which delays it by a whole stint and scores the rule on a
        # handicap rather than on itself. The endurance source carries no stint
        # column in the audit table, but for a first stop it does not need one.
        tyre_age = int(decision.decision_lap)

        b1 = fixed_interval(race_laps, n_stops)
        b2 = threshold(
            int(decision.decision_lap), tyre_age, slope, pit_loss, race_laps
        )
        b3 = fuel_deadline(deadline)

        rows.append({
            "series": str(decision.series), "season": int(decision.year),
            "circuit": str(decision.event), "car_class": str(decision.car_class),
            "driver": str(decision.car),
            "decision_lap": int(decision.decision_lap),
            "real_pit_lap": int(decision.real_pit_lap),
            "model_pit_lap": int(decision.model_pit_lap),
            "race_laps": race_laps, "compound": "",
            "tyre_age": tyre_age,
            "slope_s_per_lap": round(slope, 5), "pit_loss_s": round(pit_loss, 2),
            "b1_lap": b1.lap, "b2_lap": b2.lap, "b3_lap": b3.lap,
            "b3_undefined": b3.undefined_reason,
        })

    # A join that loses a third of its rows and says nothing is how this went
    # wrong the first three times. Distinct race-classes, not decisions, so one
    # missing plan is reported once rather than five times.
    lost = sorted(set(unmatched))
    if lost:
        share = len(lost) / (len(lost) + len(set(
            f"{r['series']}|{r['season']}|{r['circuit']}|{r['car_class']}"
            for r in rows
        )))
        print(f"  {len(lost)} race-class keys have no multi-stop plan "
              f"({share:.0%} of those requested):")
        for key in lost[:8]:
            print(f"    {key}")
        assert share < 0.25, (
            f"{share:.0%} of endurance race-classes could not be matched to a "
            "multi-stop plan. That is a join failure, not a scope gap -- check "
            "that both sides are slugified. Examples: " + ", ".join(lost[:5])
        )
    return pd.DataFrame(rows)


def _score(frame: pd.DataFrame) -> pd.DataFrame:
    """Absolute lap error against the real stop, per method."""
    scored = frame.copy()
    scored["model_error"] = (scored["model_pit_lap"] - scored["real_pit_lap"]).abs()
    for column, name in (("b1_lap", "b1"), ("b2_lap", "b2"), ("b3_lap", "b3")):
        scored[f"{name}_error"] = (scored[column] - scored["real_pit_lap"]).abs()
    return scored


def _summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Median absolute error and coverage per method, per series.

    Coverage matters as much as the error: a rule that answers 12% of decisions
    and is close on those has not beaten a rule that answers all of them, and a
    table of medians alone would say it had.
    """
    rows = []
    for series, group in scored.groupby("series"):
        for name, label in (("model", "exact optimiser"),
                            ("b1", "B1 fixed interval"),
                            ("b2", "B2 threshold"),
                            ("b3", "B3 fuel deadline")):
            errors = group[f"{name}_error"].dropna()
            rows.append({
                "series": series, "method": label,
                "decisions_answered": len(errors),
                "coverage_pct": round(100 * len(errors) / len(group), 1),
                "median_abs_error": errors.median() if len(errors) else float("nan"),
                "mean_abs_error": errors.mean() if len(errors) else float("nan"),
                "within_2_laps_pct": (
                    round(100 * (errors <= 2).mean(), 1) if len(errors) else float("nan")
                ),
            })
    return pd.DataFrame(rows)


def _laps(value: float) -> str:
    """Lap counts read as prose here, so "1 laps" is worth avoiding."""
    return f"{value:.0f} lap" + ("" if abs(value - 1) < 1e-9 else "s")


def _verdict(summary: pd.DataFrame) -> list[str]:
    """State what the numbers say, on both statistics, including when they
    disagree with each other.

    An earlier version ranked on the median alone and wrote "no baseline does
    better" for ELMS, where B1 ties the median and **wins the mean**. It also
    missed the optimiser's strongest evidence: in WEC it lands within two laps
    of the real stop 83% of the time against B1's 52%, an advantage the median
    cannot show because both round to 2.

    Two statistics that rank methods differently is information, not a
    nuisance. Picking one and reporting it as the answer would be a choice
    disguised as a measurement.
    """
    lines = []
    for series, group in summary.groupby("series"):
        answered = group[group["decisions_answered"] > 0].copy()
        model = answered[answered["method"] == "exact optimiser"]
        if answered.empty or model.empty:
            continue
        model_median = float(model["median_abs_error"].iloc[0])
        model_hit = float(model["within_2_laps_pct"].iloc[0])
        rules = answered[answered["method"] != "exact optimiser"]

        on_median = rules[rules["median_abs_error"] < model_median]
        on_hit = rules[rules["within_2_laps_pct"] > model_hit]
        ties = rules[
            (rules["median_abs_error"] == model_median)
            & (rules["within_2_laps_pct"] <= model_hit)
        ]

        if not on_median.empty:
            best = on_median.nsmallest(1, "median_abs_error").iloc[0]
            verdict = (
                f"**{best['method']} beats the exact optimiser on median error** "
                f"— {_laps(best['median_abs_error'])} against "
                f"{_laps(model_median)}, on {best['coverage_pct']:.0f}% of "
                "decisions."
            )
            if float(best["within_2_laps_pct"]) > model_hit:
                verdict += (
                    f" It also lands within two laps more often "
                    f"({best['within_2_laps_pct']:.0f}% against "
                    f"{model_hit:.0f}%), so both statistics agree."
                )
            else:
                verdict += (
                    f" The optimiser still lands within two laps more often "
                    f"({model_hit:.0f}% against "
                    f"{best['within_2_laps_pct']:.0f}%) — it is further out on "
                    "average but more often nearly exact."
                )
        elif not on_hit.empty:
            best = on_hit.nlargest(1, "within_2_laps_pct").iloc[0]
            verdict = (
                f"medians tie at {model_median:.0f} laps, but "
                f"**{best['method']} is within two laps more often** "
                f"({best['within_2_laps_pct']:.0f}% against {model_hit:.0f}%)."
            )
        elif not ties.empty:
            tied = ties.nsmallest(1, "mean_abs_error").iloc[0]
            note = (
                f" — and a lower mean ({tied['mean_abs_error']:.1f} against "
                f"{float(model['mean_abs_error'].iloc[0]):.1f})"
                if float(tied["mean_abs_error"]) < float(model["mean_abs_error"].iloc[0])
                else ""
            )
            verdict = (
                f"the optimiser's median error is **{model_median:.0f} laps** "
                f"and {tied['method']} matches it{note}. The optimiser keeps "
                f"the edge on precision: within two laps {model_hit:.0f}% of "
                f"the time against {tied['within_2_laps_pct']:.0f}%."
            )
        else:
            verdict = (
                f"the optimiser leads on both statistics — median "
                f"**{model_median:.0f} laps**, within two laps "
                f"{model_hit:.0f}% of the time. The machinery earns its place "
                "here."
            )
        lines.append(f"- **{series.upper()}**: {verdict}")

    lines += [
        "",
        "**Closer to what teams did is not the same as better.** Every number "
        "here scores agreement with real strategy, which is what the audit "
        "measures and not a claim about which plan was faster. A rule that "
        "matches practice may be matching a shared habit; the optimiser being "
        "further away may mean it is wrong, or may mean teams leave time on "
        "the table. This comparison cannot separate those, and neither can the "
        "audit.",
        "",
        "What it does settle is narrower and still worth having: **in F1 and "
        "IMSA the exact optimiser is not the closest thing here to what teams "
        "actually do.** A threshold rule using two fitted numbers, and in IMSA "
        "a rule using none at all, sit nearer. Whatever the 12-lap gap is, it "
        "is not explained by the baselines lacking information the optimiser "
        "has.",
        "",
        "B2 is far out in all three endurance series, and that is the rule "
        "being wrong rather than broken: it stops when the *tyre* has cost more "
        "than the stop, while an endurance stop is forced by the *tank*. B3, "
        "which runs the tank out, is the one that belongs there — and it is the "
        "optimiser's closest rival in WEC.",
    ]
    return lines


def main() -> int:
    warnings.filterwarnings("ignore")
    print("scoring F1 decisions ...", flush=True)
    f1 = _f1_rows()
    print(f"  {len(f1)} F1 decisions")
    print("scoring endurance decisions ...", flush=True)
    endurance = _endurance_rows()
    print(f"  {len(endurance)} endurance decisions")

    scored = _score(pd.concat([f1, endurance], ignore_index=True))
    f1_scored = scored[scored["series"] == "f1"]
    end_scored = scored[scored["series"] != "f1"]
    f1_scored.to_csv(F1_DERIVED_DIR / "baseline_comparison.csv", index=False)
    end_scored.to_csv(
        ENDURANCE_DERIVED_DIR / "baseline_comparison.csv", index=False
    )

    summary = _summary(scored)
    audit_total = (
        len(pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv"))
        + len(pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv"))
    )

    lines = [
        "<!-- GENERATED by scripts/run_baseline_comparison.py — do not edit by "
        "hand. -->",
        "",
        "# Does the optimiser beat a rule of thumb?",
        "",
        "The [decision audit](../f1/systematic_audit.md) replays every real "
        "first stop through an exact dynamic program and a Monte Carlo engine, "
        "and finds it stops later than teams do on 80–86% of them. That is "
        "only worth reporting if the machinery is doing something a simple rule "
        "could not, and until now nothing here established that.",
        "",
        "Three rules, scored on **the same decisions, from the same artifacts, "
        "on the same metric** — absolute lap error against what the team "
        "actually did. Nothing is re-fitted and no decision is re-selected, so "
        "any difference is the rule and not the sample.",
        "",
        "| rule | what it uses |",
        "|---|---|",
        "| **B1 fixed interval** | race length and stop count. No fitted "
        "quantity at all. |",
        "| **B2 threshold** | the fitted tyre slope and the measured pit loss. "
        "Stop once the tyre has cost more than the stop would. |",
        "| **B3 fuel deadline** | the measured fuel range. Run the tank out. "
        "*Undefined in F1 — no refuelling since 2010.* |",
        "",
        f"**{len(scored)} of the audit's {audit_total} decisions scored** "
        f"({100 * len(scored) / audit_total:.0f}%). The shortfall is decisions "
        "whose inputs could not be recovered: an F1 circuit with no fitted "
        "model or a driver whose state at the decision lap is missing from the "
        "committed laps, and endurance decisions whose race-season has no row "
        "in the multi-stop plan table. Nothing is dropped for being awkward — "
        "the filter is whether the same inputs the optimiser saw are still "
        "available, and where they are not, no method is scored rather than "
        "one being scored on a guess.",
        "",
        "| series | method | answered | coverage | median \\|Δ\\| laps | mean | "
        "within 2 laps |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in summary.itertuples():
        median = ("—" if pd.isna(row.median_abs_error)
                  else f"{row.median_abs_error:.0f}")
        mean = "—" if pd.isna(row.mean_abs_error) else f"{row.mean_abs_error:.1f}"
        within = ("—" if pd.isna(row.within_2_laps_pct)
                  else f"{row.within_2_laps_pct:.0f}%")
        lines.append(
            f"| {row.series} | {row.method} | {row.decisions_answered} | "
            f"{row.coverage_pct:.0f}% | {median} | {mean} | {within} |"
        )

    lines += [
        "",
        "**Coverage is part of the result, not a footnote.** A rule that "
        "answers a fifth of the decisions and is close on those has not beaten "
        "one that answers all of them, and a table of medians alone would say "
        "it had. B2 declines whenever the fitted tyre never accumulates enough "
        "loss to repay the stop before the flag; B3 declines wherever there is "
        "no measured fuel range, and everywhere in F1.",
        "",
        "## What this says",
        "",
        *_verdict(summary),
        "",
        "The baselines were written to win if they could. A straw man would "
        "prove nothing, and the outcome where a naive rule sits closer to "
        "practice than the exact optimum is the more interesting one — it would "
        "not weaken the audit's finding but sharpen it, into a claim about what "
        "an optimiser is for rather than about how good this one is.",
        "",
    ]

    CROSS_SERIES_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (CROSS_SERIES_REPORTS_DIR / "baselines.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\n" + summary.to_string(index=False))
    print(f"\nwrote {CROSS_SERIES_REPORTS_DIR / 'baselines.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
