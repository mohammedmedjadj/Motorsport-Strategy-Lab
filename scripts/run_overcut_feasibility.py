"""How much tyre advantage does overtaking need, on real degradation slopes?

Salminen (2026) solves the two-car one-stop pit-stop game analytically and finds
two defences against an undercut. D1 keeps position by stopping immediately
after. D2 is the overcut: stay out, build a tyre advantage, catch the opponent
and pass on track. D2 is efficient only if a stop lap exists that gives enough
advantage to pass and still leaves time to close the gap, and the advantage
needed in laps follows from his own inequality

    theta * a  >=  o + epsilon

where theta is the degradation in seconds per lap of tyre use, o the overtaking
threshold in seconds, and epsilon the raw-pace deficit. So

    a = (o + epsilon) / theta.

His worked example uses theta = 0.1 s/lap, which gives a = 6.5 laps and a
comfortable D2. That value sits near the top of the distribution this project
measures. On a median circuit-compound the same inequality asks for roughly
twice as many laps.

This measures that. It is a sensitivity analysis on his parameter rather than
a calibration of it: o is taken from his example and varied around it, because
this project holds no overtaking threshold in seconds at all. What it holds is
a per-circuit adjacent-swap probability, which is a different quantity and does
not convert into one.

Three denominators, kept apart on purpose, because mixing them is how this
report first contradicted itself:

- **73** fitted circuit-compound slopes in total;
- **57** whose cluster-robust interval excludes zero, the only ones where `a`
  is a measurement rather than a division by noise. Every average over `a` is
  taken on these;
- **16** whose interval contains zero, where `a` is not identified. Dividing
  anyway gave Singapore's soft tyre a requirement of some four thousand laps,
  out of a slope of 0.0001 s/lap -- the noise, not the tyre. They count as
  circuit-compounds where D2 is unreachable, are named, and are excluded from
  every average.

theta comes from ``deg_p1``, the tyre term, with fuel and track evolution
carried by a separate regressor. A net slope would fold a fuel gain into theta
and shrink every `a` reported here.

Writes ``data/derived/f1/overcut_feasibility.csv`` and
``reports/f1/overcut_feasibility.md``.

Usage (offline, from the repo root)::

    python scripts/run_overcut_feasibility.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402

OUT_CSV = F1_DERIVED_DIR / "overcut_feasibility.csv"
OUT_MD = F1_REPORTS_DIR / "overcut_feasibility.md"

#: Overtaking thresholds in seconds. The middle value is Salminen's own, from
#: his section 2.6; the others bracket it, because the parameter is free in his
#: model and nothing here measures it.
THRESHOLDS = (0.30, 0.55, 0.80)
SALMINEN_O = 0.55
SALMINEN_THETA = 0.10
SALMINEN_EPSILON = 0.10
SALMINEN_A = 6.5
SALMINEN_RACE_LAPS = 40

#: Raw-pace deficit. Zero is the equal-pace case, which his three-car model
#: assumes and which is the most favourable to D2 -- any real deficit makes the
#: required advantage larger, never smaller, so every figure here understates
#: the difficulty.
EPSILON = 0.0


def load() -> pd.DataFrame:
    coefs = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    sessions = pd.read_csv(F1_DERIVED_DIR / "sessions.csv")
    laps = (
        sessions.groupby("circuit")["scheduled_laps"].median().round().astype(int)
    )
    frame = coefs[[
        "circuit", "compound", "deg_p1", "deg_p1_ci_low", "deg_p1_ci_high",
        "n_stints", "n_clusters",
    ]].copy()
    frame["race_laps"] = frame["circuit"].map(laps)
    missing = sorted(frame[frame["race_laps"].isna()]["circuit"].unique())
    if missing:
        raise KeyError(
            f"no scheduled lap count for {missing}; sessions.csv and the "
            "degradation fit disagree about which circuits exist"
        )
    frame["race_laps"] = frame["race_laps"].astype(int)
    # An interval excluding zero is what makes theta a rate rather than a
    # number near noise. The partition is checked rather than assumed: if a
    # slope were significantly negative it would belong in neither group, and
    # the report's framing would be wrong rather than merely incomplete.
    if (frame["deg_p1_ci_high"] < 0).any():
        raise ValueError(
            "a slope is now significantly negative, which this report assumes "
            "away when it treats every unresolved fit as a near-zero"
        )
    frame["resolved"] = frame["deg_p1_ci_low"] > 0
    return frame


def required_advantage(frame: pd.DataFrame, o: float) -> pd.DataFrame:
    """Laps of tyre advantage needed to pass, with theta's interval inverted.

    `a` falls as theta rises, so theta's upper bound gives `a`'s lower one. An
    interval on theta that reaches zero leaves `a` unbounded above, which is
    reported as such rather than clipped to a large number.
    """
    out = frame.copy()
    out["o_s"] = o
    need = o + EPSILON
    with np.errstate(divide="ignore", invalid="ignore"):
        out["a_laps"] = np.where(out["deg_p1"] > 0, need / out["deg_p1"], np.nan)
        out["a_low"] = np.where(
            out["deg_p1_ci_high"] > 0, need / out["deg_p1_ci_high"], np.nan
        )
        out["a_high"] = np.where(
            out["deg_p1_ci_low"] > 0, need / out["deg_p1_ci_low"], np.inf
        )
    # Unreachable covers both ways D2 fails: the advantage needed exceeds the
    # race, or theta is unresolved so no advantage is identified at all.
    out["d2_unreachable"] = ~(out["resolved"] & (out["a_laps"] < out["race_laps"]))
    out["d2_past_half_distance"] = ~(
        out["resolved"] & (out["a_laps"] < out["race_laps"] / 2.0)
    )
    return out


def summary(table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for o, part in table.groupby("o_s"):
        resolved = part[part["resolved"]]
        rows.append({
            "o_s": o,
            "n_fits": len(part),
            "n_resolved": len(resolved),
            "n_unresolved": int((~part["resolved"]).sum()),
            # Quartiles of `a`, which runs opposite to theta: the 25th
            # percentile of the requirement comes from the 75th of the slope.
            "a_p25": round(float(resolved["a_laps"].quantile(0.25)), 1),
            "a_median": round(float(resolved["a_laps"].median()), 1),
            "a_p75": round(float(resolved["a_laps"].quantile(0.75)), 1),
            "n_d2_unreachable": int(part["d2_unreachable"].sum()),
            "pct_d2_unreachable": round(100 * part["d2_unreachable"].mean()),
            "n_past_half": int(part["d2_past_half_distance"].sum()),
            "pct_past_half": round(100 * part["d2_past_half_distance"].mean()),
        })
    return pd.DataFrame(rows)


def _interval(row: pd.Series) -> str:
    if not np.isfinite(row["a_low"]):
        return "not identified"
    high = "unbounded" if not np.isfinite(row["a_high"]) else f"{row['a_high']:.0f}"
    return f"{row['a_low']:.0f}–{high}"


def _verdict(row: pd.Series) -> str:
    if not row["resolved"]:
        return "not identified"
    if row["a_laps"] >= row["race_laps"]:
        return "**longer than the race**"
    if row["a_laps"] >= row["race_laps"] / 2.0:
        return "past half-distance"
    return "available"


def write_report(table: pd.DataFrame, totals: pd.DataFrame) -> Path:
    main = table[table["o_s"] == SALMINEN_O].copy()
    resolved = main[main["resolved"]]
    unresolved = main[~main["resolved"]]
    pct_below = 100 * (resolved["deg_p1"] < SALMINEN_THETA).mean()
    n_negative = int((main["deg_p1"] <= 0).sum())

    lines = [
        "<!-- generated by scripts/run_overcut_feasibility.py -->",
        "",
        "# How much tyre advantage does an overcut need?",
        "",
        "Generated. Do not edit by hand.",
        "",
        "Salminen (2026) proves that the overcut defence against an undercut "
        "— his D2 — is efficient only when a driver can build enough tyre "
        "advantage to pass on track. His own inequality fixes how much: with "
        "a linear degradation of `theta` seconds per lap of tyre use, an "
        "overtaking threshold of `o` seconds and a raw-pace deficit "
        "`epsilon`, the advantage needed is",
        "",
        "```",
        "a = (o + epsilon) / theta",
        "```",
        "",
        f"His worked example takes `theta = {SALMINEN_THETA}`, "
        f"`o = {SALMINEN_O}` and `epsilon = {SALMINEN_EPSILON}`, giving "
        f"`a = {SALMINEN_A}` laps on a {SALMINEN_RACE_LAPS}-lap race. D2 is "
        "available to the defender for most of it.",
        "",
        f"Of the {len(resolved)} Formula 1 circuit-compound slopes measured "
        f"here with a resolved rate, **{pct_below:.0f}%** degrade more slowly "
        f"than `theta = {SALMINEN_THETA}`. His example is therefore not a "
        "typical circuit; it sits close to the most degrading one in five "
        "seasons. This is what the same inequality asks for elsewhere.",
        "",
        "## Three denominators, kept apart",
        "",
        f"- **{len(main)}** fitted circuit-compound slopes in total.",
        f"- **{len(resolved)}** whose cluster-robust interval excludes zero. "
        "Every average over `a` is taken on these, because `a` is only a "
        "measurement where `theta` is one.",
        f"- **{len(unresolved)}** whose interval contains zero, where `a` is "
        "not identified. Dividing anyway gives Singapore's soft tyre a "
        "requirement of some four thousand laps out of a slope of 0.0001 "
        "s/lap, which measures the noise and not the tyre. These count as "
        "circuit-compounds where D2 is unreachable, are named below, and are "
        "excluded from every average.",
        "",
        "No slope in the table is significantly negative, so those groups "
        f"account for all {len(main)} with nothing left over. "
        f"{n_negative} have a point estimate at or below zero, all of them "
        "inside the unresolved group.",
        "",
        "## What this is and is not",
        "",
        "A sensitivity analysis on his parameter rather than a calibration "
        "of it. "
        "`o` is a threshold in seconds and this project holds no such "
        "quantity. What it measures per circuit is an adjacent-pair swap "
        "probability per lap, a different object that does not convert into "
        "one. So `o` is taken from his example and varied around it.",
        "",
        f"`epsilon` is set to zero rather than to his {SALMINEN_EPSILON}. "
        "That is the equal-pace case his three-car model assumes, and the "
        "one most favourable to D2: any real pace deficit makes the required "
        "advantage larger, never smaller, so every figure below understates "
        "the difficulty.",
        "",
        "`theta` is the tyre term from the Formula 1 degradation fit "
        "(`deg_p1`), with fuel and track evolution carried by a separate "
        "regressor. A net slope would fold a fuel gain into `theta` and "
        "shrink every `a` here.",
        "",
        "## The required advantage",
        "",
        "| `o` (s) | `a` at the quartiles (laps) | D2 unreachable | D2 only past half-distance |",
        "| ---: | :---: | ---: | ---: |",
    ]
    for _, row in totals.iterrows():
        lines.append(
            f"| {row['o_s']:.2f} | {row['a_p25']:.0f} – "
            f"**{row['a_median']:.0f}** – {row['a_p75']:.0f} | "
            f"{int(row['n_d2_unreachable'])} of {int(row['n_fits'])} "
            f"({int(row['pct_d2_unreachable'])}%) | "
            f"{int(row['n_past_half'])} of {int(row['n_fits'])} "
            f"({int(row['pct_past_half'])}%) |"
        )
    lines += [
        "",
        f"Quartiles over the {len(resolved)} resolved fits, median in bold. "
        f"The two right-hand columns are over all {len(main)}, because a "
        "slope that is not resolved is one where no tyre advantage is "
        "identified and D2 has nothing to build from. *Unreachable* means "
        "the required advantage is at least the full race distance.",
        "",
        "### Where it is hardest",
        "",
        "The ten resolved circuit-compounds asking for the most tyre "
        f"advantage at `o = {SALMINEN_O}`. The interval on `a` is the "
        "interval on `theta`, inverted.",
        "",
        "| circuit | compound | `theta` (s/lap) | `a` (laps) | 95% interval | race laps | D2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in resolved.nlargest(10, "a_laps").iterrows():
        lines.append(
            f"| {row['circuit']} | {row['compound'].lower()} | "
            f"{row['deg_p1']:.4f} | {row['a_laps']:.0f} | "
            f"{_interval(row)} | {int(row['race_laps'])} | {_verdict(row)} |"
        )
    lines += [
        "",
        "### Where it is easiest",
        "",
        "The six where his model behaves as his example does.",
        "",
        "| circuit | compound | `theta` (s/lap) | `a` (laps) | 95% interval | race laps |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in resolved.nsmallest(6, "a_laps").iterrows():
        lines.append(
            f"| {row['circuit']} | {row['compound'].lower()} | "
            f"{row['deg_p1']:.4f} | {row['a_laps']:.0f} | "
            f"{_interval(row)} | {int(row['race_laps'])} |"
        )
    lines += [
        "",
        "### Where the rate is not identified",
        "",
        f"The {len(unresolved)} circuit-compounds whose interval contains "
        "zero. A tyre with no measurable degradation cannot generate a tyre "
        "advantage, so D2 does not exist there under any `o`.",
        "",
        "| circuit | compound | `theta` (s/lap) | 95% interval on `theta` |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in unresolved.sort_values("deg_p1").iterrows():
        lines.append(
            f"| {row['circuit']} | {row['compound'].lower()} | "
            f"{row['deg_p1']:+.4f} | "
            f"[{row['deg_p1_ci_low']:+.4f}, {row['deg_p1_ci_high']:+.4f}] |"
        )
    lines += [
        "",
        "This is a statement about the measurement as much as about the "
        "model. An unresolved slope may be a real near-zero or a slope the "
        "data never pinned down, and these fits do not separate the two. The "
        "negative point estimates are a known defect rather than a tyre that "
        "improves with age: nothing in the Formula 1 specification carries "
        "track evolution separately from tyre age at the compound level.",
        "",
        "## What it implies for his model",
        "",
        "His two defences are not equally robust to measured parameters. D1 "
        "turns on `theta * l_u + epsilon < g`, which stays well defined as "
        "`theta` falls and simply means the defence survives longer. D2 "
        "turns on dividing by `theta`, and at the rates measured here it is "
        "unreachable on a large share of circuit-compounds.",
        "",
        "The consequence is structural rather than a matter of degree. Where "
        "D2 is unavailable the defender holds only D1, so the earliest "
        "undefendable undercut collapses onto the lap D1 expires — the "
        "point where a lead in seconds stops covering the accumulated tyre "
        "and pace loss. Most of the one-stop model is inactive there, and "
        "the equilibrium reduces to a single inequality.",
        "",
        "That is why the implementation here takes the D1 condition and "
        "treats D2 as an extension conditioned on a new calibration. It is "
        "not a judgement on the proofs, which concern a model and hold "
        "inside it. It measures how much of that model real parameter values "
        "leave switched on.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return OUT_MD


def main() -> None:
    frame = load()
    table = pd.concat(
        [required_advantage(frame, o) for o in THRESHOLDS], ignore_index=True
    )
    totals = summary(table)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(Path.cwd())}")
    out = write_report(table, totals)
    print(f"wrote {out.relative_to(Path.cwd())}")
    print()
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()
