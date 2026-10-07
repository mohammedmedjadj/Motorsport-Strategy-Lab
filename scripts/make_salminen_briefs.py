"""Two one-page briefs for Tomi Salminen, on his own model's assumptions.

He sent a preprint deriving the earliest undefendable undercut from a two-car
one-stop game. Two things here bear on it, and neither is a review of the
proofs, which concern a model and hold inside it. Both measure how much of that
model real parameter values leave switched on.

**Brief 1, the overcut.** His D2 defence needs a tyre advantage of
``(o + epsilon) / theta`` laps. His worked example takes ``theta = 0.1``, which
sits near the top of the degradation rates fitted here. The brief gives the
distribution of what his own inequality asks for across the Formula 1
circuit-compounds measured in this project, and where it asks for more laps
than the race has.

**Brief 2, the position-keeping defence.** His D1 is efficient while
``theta * l_u + epsilon < g``. Tested on 357 real first-stop decisions it
predicts a stop far later than teams made, and the brief says by how much and
why, including the three defects found while building it -- all of which
inflated the window and so made the negative result look stronger than it is.

Every number is read from the committed artifacts
``data/derived/f1/overcut_feasibility.csv`` and
``data/derived/f1/d1_defence.csv``. Nothing here is typed.

Writes ``outreach/overcut_feasibility_brief.pdf`` and
``outreach/d1_defence_brief.pdf``.

Usage (offline, from the repo root)::

    python scripts/run_overcut_feasibility.py
    python scripts/run_d1_defence.py
    python scripts/make_salminen_briefs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import F1_DERIVED_DIR, REPO_ROOT  # noqa: E402
from src.reporting import palette  # noqa: E402
from src.reporting.names import circuit as circuit_name  # noqa: E402
from src.reporting.brief import Brief  # noqa: E402

OVERCUT = F1_DERIVED_DIR / "overcut_feasibility.csv"
D1 = F1_DERIVED_DIR / "d1_defence.csv"
OUT_DIR = REPO_ROOT / "outreach"

REPO_URL = "github.com/mohammedmedjadj/Motorsport-Strategy-Lab"
CONCEPT_DOI = "10.5281/zenodo.22726130"
BYLINE = f"Mohammed Reda Medjadj  ·  {REPO_URL}  ·  doi.org/{CONCEPT_DOI}"

#: His own overtaking threshold, from section 2.6 of the preprint.
SALMINEN_O = 0.55

#: The pace term this analysis fixes. Stated in the brief from here, so
#: the prose cannot disagree with what was computed.
EPSILON = 0.0


def overcut_facts() -> dict:
    table = pd.read_csv(OVERCUT)
    main = table[table["o_s"] == SALMINEN_O]
    resolved = main[main["resolved"]]
    return {
        "n_fits": len(main),
        "n_resolved": len(resolved),
        "n_unresolved": int((~main["resolved"]).sum()),
        "pct_below": 100 * float((resolved["deg_p1"] < 0.10).mean()),
        "q25": float(resolved["a_laps"].quantile(0.25)),
        "median": float(resolved["a_laps"].median()),
        "q75": float(resolved["a_laps"].quantile(0.75)),
        "n_unreachable": int(main["d2_unreachable"].sum()),
        "n_past_half": int(main["d2_past_half_distance"].sum()),
        "by_threshold": table.groupby("o_s").agg(
            median=("a_laps", "median"),
            unreachable=("d2_unreachable", "sum"),
            past_half=("d2_past_half_distance", "sum"),
        ),
        "hardest": resolved.nlargest(3, "a_laps"),
        # The worst of the unresolved fits, to show what dividing by an
        # unidentified slope produces. Derived rather than quoted: it is the
        # number that made the exclusion obviously right, so it should move
        # with the data if the data moves.
        "worst_unresolved": main[~main["resolved"]].nlargest(1, "a_laps").iloc[0],
    }


def _percentile_of(rate: float) -> float:
    """Share of every fitted Formula 1 tyre slope below a given rate."""
    slopes = pd.read_csv(
        F1_DERIVED_DIR / "degradation_coefficients.csv"
    )["deg_p1"].dropna()
    return 100 * float((slopes < rate).mean())


def d1_facts() -> dict:
    table = pd.read_csv(D1)
    chasers = table[table["role"] == "chaser"]
    leaders = table[table["role"] == "race leader"]
    usable = chasers[chasers["euu_lap"].notna()]
    reachable = chasers[chasers["pit_loss_s"].notna()]
    implied = chasers[
        chasers["theta_resolved"].astype(bool) & chasers["theta_ratio"].notna()
    ]
    return {
        "n_total": len(table),
        "n_leaders": len(leaders),
        "n_chasers": len(chasers),
        "n_usable": len(usable),
        "median_gap": float(chasers["gap_to_leader_s"].median()),
        "n_within": int(reachable["within_pit_loss"].sum()),
        "n_reachable": len(reachable),
        "median_real": float(chasers["real_pit_lap"].median()),
        "median_error": float(usable["euu_error"].median()),
        "median_baseline": float(usable["single_car_error"].median()),
        "closer": int(
            (usable["euu_error"].abs() < usable["single_car_error"].abs()).sum()
        ),
        "further": int(
            (usable["euu_error"].abs() > usable["single_car_error"].abs()).sum()
        ),
        "past_race_end": 100 * float(
            (usable["euu_lap"] > usable["real_pit_lap"] + 40).mean()
        ),
        "implied_theta": float(implied["implied_theta"].median()),
        "measured_theta": float(implied["theta"].median()),
        "ratio": float(implied["theta_ratio"].median()),
        "ratio_q25": float(implied["theta_ratio"].quantile(0.25)),
        "ratio_q75": float(implied["theta_ratio"].quantile(0.75)),
        "pct_above": 100 * float((implied["theta_ratio"] > 1).mean()),
        "n_implied": len(implied),
        # Where the rate his condition would need sits among every slope
        # this project fits. It is what makes "the data almost never shows
        # this" a measurement rather than a flourish, so it is derived.
        "theta_percentile": _percentile_of(
            float(implied["implied_theta"].median())
        ),
        "max_gap": float(chasers["gap_to_leader_s"].max()),
        # Share of decisions whose tyre age equals the lap number, which is the
        # only case where an expiry in tyre ages can be compared against a lap
        # number without converting. It was 100% in my head and is not.
        "pct_age_equals_lap": 100 * float(
            (chasers["tyre_age"] == chasers["real_pit_lap"]).mean()
        ),
        **_stale_join_cost(chasers),
        **_audit_headline(),
    }


def _stale_join_cost(chasers: pd.DataFrame) -> dict:
    """What the circuit-slug mismatch would still cost, recomputed.

    The brief says a join dropped values silently. Quoting the figure I
    remembered would have said 86 of 267; on the current table it is 85 of 266,
    because the lapped-car bound added since then removes one decision. A
    number describing a defect drifts like any other number.
    """
    history = pd.read_csv(F1_DERIVED_DIR / "history_pit_loss.csv")
    delta = history.groupby("circuit")["pit_loss_median_s"].median()
    matched = int(chasers["circuit"].map(delta).notna().sum())
    return {
        "stale_matched": matched,
        "stale_dropped": len(chasers) - matched,
        "stale_total": len(chasers),
    }


def _audit_headline() -> dict:
    """The optimiser's own bias, from the macros the manuscript quotes."""
    import re

    text = (REPO_ROOT / "paper" / "numbers.tex").read_text(encoding="utf-8")
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))
    return {
        "late_share": macros["FoneLateShare"],
        "late_median": macros["FoneLateMedian"],
    }


def overcut_brief(facts: dict) -> Path:
    page = Brief(
        "What your overcut defence asks for",
        f"Measured degradation rates across {facts['n_fits']} Formula 1 "
        "circuit-compound slopes, 2022–2026",
        BYLINE,
    )

    page.heading("The quantity")
    page.block(
        "Your D2 is efficient only where a driver can build enough tyre advantage to pass, and your\n"
        "inequality fixes how much: a = (o + ε) / θ. Section 2.6 takes θ = 0.1 s/lap, o = 0.55, ε = 0.1,\n"
        "giving a = 6.5 laps on a 40-lap race, so D2 is open to the defender for most of it.\n"
        "\n"
        f"I fit θ per circuit and compound on five seasons of public timing. Of the {facts['n_resolved']} slopes whose\n"
        f"cluster-robust interval excludes zero, {facts['pct_below']:.0f}% degrade more slowly than your 0.1. Your example\n"
        "is close to the most degrading circuit I measure, not a typical one."
    )

    page.heading("What a = (o + ε) / θ asks for elsewhere")
    lines = [
        "   o (s)      a: lower quartile – median – upper      a > race distance      a > half-distance",
    ]
    for threshold, row in facts["by_threshold"].iterrows():
        part = pd.read_csv(OVERCUT)
        part = part[(part["o_s"] == threshold) & part["resolved"]]
        lines.append(
            f"   {threshold:.2f}       "
            f"{part['a_laps'].quantile(0.25):>5.0f}  –  {part['a_laps'].median():>3.0f}  –  "
            f"{part['a_laps'].quantile(0.75):>5.0f}            "
            f"{int(row['unreachable']):>3} of {facts['n_fits']}            "
            f"{int(row['past_half']):>3} of {facts['n_fits']}"
        )
    page.block("\n".join(lines), size=7.35)

    page.block(
        f"At your own o = {SALMINEN_O}: a median of {facts['median']:.0f} laps against your 6.5, quartiles "
        f"{facts['q25']:.0f} to {facts['q75']:.0f}. D2 is\n"
        f"unreachable on {facts['n_unreachable']} of {facts['n_fits']} circuit-compounds and opens only past "
        f"half-distance on {facts['n_past_half']}.\n"
        "\n"
        f"I set ε = {EPSILON:.0f} throughout rather than your 0.1. That is the equal-pace case and the one\n"
        "most favourable to the defence, so every figure above understates the difficulty."
    )

    hardest = ", ".join(
        f"{circuit_name(row.circuit)} {row.compound.lower()} "
        f"({row.a_laps:.0f} laps of {int(row.race_laps)})"
        for row in facts["hardest"].itertuples()
    )
    page.heading("Where it is hardest")
    page.block(hardest, size=7.35)

    page.heading("Three things this is not", colour=palette.RED)
    page.block(
        "It is not a calibration of o. I hold no overtaking threshold in seconds — what I measure per\n"
        "circuit is an adjacent-pair swap probability per lap, a different object that does not convert\n"
        "into one. So o is yours throughout, varied around your value.\n"
        "\n"
        f"It is not a complete picture. On {facts['n_unresolved']} of the {facts['n_fits']} slopes the interval contains zero, so θ is\n"
        "not identified and a is undefined rather than large. I count those as unreachable and exclude\n"
        f"them from every average; dividing by them gives "
        f"{circuit_name(facts['worst_unresolved']['circuit'])}'s "
        f"{facts['worst_unresolved']['compound'].lower()} tyre {facts['worst_unresolved']['a_laps']:,.0f} laps, out\n"
        f"of a slope of {facts['worst_unresolved']['deg_p1']:.4f} s/lap, which measures my noise and not your model.\n"
        "\n"
        "It is not a judgement on your proofs. They concern a model and hold inside it. What this\n"
        "measures is how much of that model real parameter values leave switched on — and my reading\n"
        "is that D1 and D2 are not equally robust to small θ, since D1 stays well defined as θ falls\n"
        "while D2 divides by it."
    )

    page.heading("What I would value your view on")
    page.block(
        "Whether a linear θ is the right object for D2 at all. If the advantage that lets a car pass is\n"
        "concentrated in a fresh tyre's first laps rather than accumulated linearly, then a = (o + ε) / θ\n"
        "understates D2's availability on exactly the low-θ circuits where I report it as unreachable."
    )

    return page.finish(
        OUT_DIR / "overcut_feasibility_brief.pdf",
        {
            "Title": "What your overcut defence asks for",
            "Author": "Mohammed Reda Medjadj",
            "Subject": "D2 feasibility across Formula 1 degradation slopes",
            "Creator": "scripts/make_salminen_briefs.py",
        },
    )


def d1_brief(facts: dict) -> Path:
    page = Brief(
        f"Your position-keeping defence, tested on {facts['n_total']} decisions",
        "D1 against the first pit stop of every audited Formula 1 car, "
        "2022–2026",
        BYLINE,
    )

    page.heading("Why I tested it")
    page.block(
        f"An exact optimiser I built stops later than Formula 1 teams do on {facts['late_share']}% of decisions, by a\n"
        f"median of {facts['late_median']} laps. I proposed two explanations, tested both, and lost both. Yours is the\n"
        "third, and the only mechanism I have found that predicts stopping before the time optimum —\n"
        "the right direction. So I implemented D1: efficient while θ·l_u + ε < g, expiring at a tyre age\n"
        "of (g − ε)/θ, with the earliest undefendable undercut the lap after."
    )

    page.heading("The result is negative", colour=palette.RED)
    page.block(
        f"Across {facts['n_usable']} decisions carrying a prediction, D1's earliest undefendable undercut lands a\n"
        f"median of {facts['median_error']:+.0f} laps from the real stop, against {facts['median_baseline']:+.0f} for my single-car optimiser. It is\n"
        f"closer on {facts['closer']} and further on {facts['further']}. On {facts['past_race_end']:.0f}% the predicted lap is past the end of the race.\n"
        "\n"
        "Fed with the gaps and slopes I measure, the condition says a leader can defend an undercut for\n"
        f"longer than the race lasts, so a chaser should never undercut. Teams undercut at a median lap\n"
        f"{facts['median_real']:.0f}."
    )

    page.heading("Why, as a number rather than a story")
    page.block(
        "Inverting the condition at the tyre age of the stop teams actually made gives the degradation\n"
        "rate at which D1 would have expired exactly then: θ* = (g − ε) / l_u(real).\n"
        "\n"
        f"Over {facts['n_implied']} decisions with a resolved slope the median θ* is {facts['implied_theta']:.3f} s/lap against a measured\n"
        f"{facts['measured_theta']:.3f} — a ratio of {facts['ratio']:.1f}×, quartiles {facts['ratio_q25']:.1f} to {facts['ratio_q75']:.1f}, larger on {facts['pct_above']:.0f}% of them. A rate of\n"
        f"{facts['implied_theta']:.3f} s/lap sits at the {facts['theta_percentile']:.0f}th percentile of every slope I fit in five seasons.\n"
        "\n"
        "So this is not a calibration gap. For your equilibrium to reproduce what teams do, tyres would\n"
        "have to degrade at a rate the data almost never shows."
    )

    page.heading("My reading, which I have not established")
    page.block(
        "θ·l_u prices the defender's loss over a single lap on a tyre l_u laps old. At my measured\n"
        f"median of {facts['measured_theta']:.3f} s/lap and a tyre the age teams actually stop at, that is under a\n"
        f"second, which the median {facts['median_gap']:.1f} s lead covers easily. What wins a real undercut is the\n"
        "advantage of a tyre on its first flying lap over one at the end of its life, and a linear\n"
        "slope has no term for that. Measuring it directly is a different estimator and I have not\n"
        "attempted it."
    )

    page.heading("Two measurements that hold regardless")
    page.block(
        f"{facts['n_leaders']} of the {facts['n_total']} decisions belong to a car with nobody ahead within one lap. The race leader\n"
        "has no undercut to perform, so a quarter of the set carries no prediction under any two-car\n"
        "model. For the other "
        f"{facts['n_chasers']}, the median gap to the leader is {facts['median_gap']:.1f} s, and on {facts['n_within']} of {facts['n_reachable']} it is\n"
        "smaller than the circuit's measured pit loss. Reachability is not the binding constraint —\n"
        "the opposite of what I expected to find."
    )

    page.heading("Three defects I found while building this", colour=palette.RED)
    page.block(
        "All three inflated the D1 window, so all three made this negative result look stronger than it\n"
        "is. Comparing cumulative race time with no bound found rivals a full lap away; the nearest car\n"
        f"ahead is now capped at one green lap and the widest retained gap is {facts['max_gap']:.0f} s. The expiry is a\n"
        "tyre age and I was comparing it against a lap number, which agree on only\n"
        f"{facts['pct_age_equals_lap']:.0f}% of these decisions. And my pit-loss table names circuits differently from my lap\n"
        f"files, which still drops {facts['stale_dropped']} of {facts['stale_total']} values if joined on the slug. Each now has a test, as\n"
        "does the conclusion itself."
    )

    return page.finish(
        OUT_DIR / "d1_defence_brief.pdf",
        {
            "Title": "Your position-keeping defence, tested on real decisions",
            "Author": "Mohammed Reda Medjadj",
            "Subject": "D1 against 357 real Formula 1 first-stop decisions",
            "Creator": "scripts/make_salminen_briefs.py",
        },
    )


def main() -> int:
    for path in (OVERCUT, D1):
        if not path.exists():
            raise SystemExit(
                f"{path} is missing; run the script that writes it first"
            )
    first = overcut_brief(overcut_facts())
    print(f"wrote {first.relative_to(REPO_ROOT)}")
    second = d1_brief(d1_facts())
    print(f"wrote {second.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
