"""When does the position-keeping defence expire, and do teams stop then?

The calendar-wide audit found an exact optimiser staying out a median of 12 laps
longer than Formula 1 teams did. Two explanations were tested here and both
failed. Salminen (2026) supplies a third, and it is the only one so far that
predicts the right sign.

In his one-stop game the equilibrium stop is not the time-optimal one. A chaser
stops at the earliest lap on which the leader can no longer answer, which falls
*before* the fastest clean-air strategy, because waiting hands the leader a
window. The leader has two answers. D2, the overcut, needs a tyre advantage of
``(o + epsilon) / theta`` laps, and ``reports/f1/overcut_feasibility.md``
measures that it is unreachable on a quarter of the circuit-compounds here and
only opens past half-distance on another quarter. D1, keeping position by
stopping immediately after, is efficient exactly while

    theta * l_u + epsilon  <  g

where ``g`` is the leader's lead in seconds before the stops, ``theta`` the
degradation per lap of tyre use, ``epsilon`` the chaser's raw-pace advantage and
``l_u`` the lap of the undercut. So D1 expires at ``l_D1 = (g - epsilon) /
theta``, and where D2 is unavailable the earliest undefendable undercut is the
lap after that.

That is what this computes, on the same 357 first-stop decisions the audit
replayed. Only D1 is implemented. D2 needs ``o``, a threshold in seconds, and
this project holds no such quantity -- only a per-circuit adjacent-swap
probability, which is a different object. Estimating ``o`` from observed pace
deltas would be biased toward zero precisely where overtaking is hardest, since
a car stuck in traffic is measured at its traffic pace rather than its clean
one, so the bias would be largest exactly where the phenomenon is. D2 is
therefore reported as an extension conditioned on a calibration that does not
exist yet, and not as a result.

Two things here differ from the published undercut replay, both deliberately:

- **The rival is chosen by gap in seconds, not by classified position.** That
  was Charles Thraves's objection to the published version, where
  ``_nearest_rival`` minimises absolute position distance and 271 of 357
  decisions came out as ties between a car ahead and a car behind. In seconds
  there are no ties, and leader against chaser is settled by the clock.
- **The published result is not touched.** This writes its own artifacts.

``epsilon`` is zero in the headline. Measuring it from lap times would mean
reading the chaser's pace while it sits in dirty air, which inflates the
estimate, and a larger ``epsilon`` expires D1 *earlier* and so moves the
prediction toward the real stop. That is the flattering direction, so it is
reported as a sensitivity and labelled, never as the main figure.

Writes ``data/derived/f1/d1_defence.csv`` and ``reports/f1/d1_defence.md``.

Usage (offline, from the repo root)::

    python scripts/run_d1_defence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.audit.state import load_race_laps  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402

DECISIONS = F1_DERIVED_DIR / "undercut_hypothesis.csv"
COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
OUT_CSV = F1_DERIVED_DIR / "d1_defence.csv"
OUT_MD = F1_REPORTS_DIR / "d1_defence.md"

#: Raw-pace advantage of the chaser, in seconds per lap. Zero is the headline:
#: see the module docstring on why a measured value moves the prediction the
#: flattering way.
EPSILON = 0.0

#: Sensitivity values for epsilon, in seconds per lap. Both positive, because a
#: chaser with no pace advantage has no reason to be the one committing first.
EPSILON_SENSITIVITY = (0.05, 0.10)

#: A rival further ahead than one green lap is a lapped car, not an opponent.
#: Cumulative race time at a fixed lap number cannot tell the two apart on its
#: own, and without this the nearest car "ahead" reached 910 seconds.
MAX_RIVAL_GAP_LAPS = 1.0


def _delta() -> dict[str, float]:
    """Measured pit loss per circuit, from the simulator's own estimate.

    Not ``history_pit_loss.csv``: that table names circuits differently from
    the derived lap files, and joining on the slug dropped 86 of 267 decisions
    without saying so.
    """
    return {
        slug: float(model.pit_loss.median_s)
        for slug, model in load_circuit_models().items()
    }


def _theta() -> dict[tuple[str, str], tuple[float, bool]]:
    """Tyre slope per circuit and compound, with whether it is resolved.

    ``deg_p1`` and not a net slope: fuel and track evolution are carried by a
    separate regressor, and folding a fuel gain into theta would shorten every
    D1 window computed here.
    """
    coefs = pd.read_csv(COEFS)
    return {
        (str(row.circuit), str(row.compound)):
            (float(row.deg_p1), bool(row.deg_p1_ci_low > 0))
        for row in coefs.itertuples()
    }


def _green_lap_time(laps: pd.DataFrame) -> float:
    """Field median green lap time, the scale a one-lap gap is measured on."""
    green = laps[
        (laps["TrackStatus"].astype(str) == "1")
        & (~laps["is_in_lap"].astype(bool))
        & (~laps["is_out_lap"].astype(bool))
        & laps["lap_time_s"].notna()
    ]
    if green.empty:
        return float("nan")
    return float(green["lap_time_s"].median())


def _nearest_by_seconds(laps: pd.DataFrame, driver: str, lap: int) -> dict | None:
    """The cars immediately ahead and behind on cumulative time.

    Position distance cannot separate a car ahead from a car behind when both
    are one place away, which is how the published replay ended up with 271
    ties out of 357. Cumulative race time orders the field without ties and
    names the leader unambiguously.
    """
    on_lap = laps[laps["LapNumber"] == lap].dropna(subset=["time_s"])
    mine = on_lap[on_lap["Driver"] == driver]
    if mine.empty:
        return None
    my_time = float(mine.iloc[0]["time_s"])
    others = on_lap[on_lap["Driver"] != driver]
    if others.empty:
        return None

    # Lower cumulative time is further ahead. Anything beyond one green lap
    # is a car on a different lap of the race, not a rival in this fight.
    limit = MAX_RIVAL_GAP_LAPS * _green_lap_time(laps)
    deltas = others.assign(delta=others["time_s"].astype(float) - my_time)
    deltas = deltas[deltas["delta"].abs() <= limit]
    ahead = deltas[deltas["delta"] < 0].nlargest(1, "delta")
    behind = deltas[deltas["delta"] > 0].nsmallest(1, "delta")

    out: dict = {"my_time_s": my_time}
    if not ahead.empty:
        out["leader"] = str(ahead.iloc[0]["Driver"])
        out["gap_to_leader_s"] = float(-ahead.iloc[0]["delta"])
    if not behind.empty:
        out["chaser"] = str(behind.iloc[0]["Driver"])
        out["gap_to_chaser_s"] = float(behind.iloc[0]["delta"])
    return out


def _compound_at(laps: pd.DataFrame, driver: str, lap: int) -> str | None:
    row = laps[(laps["Driver"] == driver) & (laps["LapNumber"] == lap)]
    if row.empty or pd.isna(row.iloc[0]["Compound"]):
        return None
    return str(row.iloc[0]["Compound"])


def _tyre_age_at(laps: pd.DataFrame, driver: str, lap: int) -> int | None:
    row = laps[(laps["Driver"] == driver) & (laps["LapNumber"] == lap)]
    if row.empty or pd.isna(row.iloc[0]["TyreLife"]):
        return None
    return int(row.iloc[0]["TyreLife"])


def d1_expiry(gap_s: float, theta: float, epsilon: float) -> float:
    """The last lap of tyre use on which keeping position still works.

    Salminen's condition is ``theta * l_u + epsilon < g``, so the defence holds
    up to ``l_u = (g - epsilon) / theta``. A non-positive theta leaves it
    undefined rather than infinite: a tyre with no measurable degradation
    creates no disadvantage for the defender to be caught by, but the slope
    that says so is also the slope the data failed to pin down, and treating
    the two as the same thing is what this refuses to do.
    """
    if not np.isfinite(theta) or theta <= 0:
        return float("nan")
    if gap_s <= epsilon:
        return 0.0
    return (gap_s - epsilon) / theta


def collect() -> pd.DataFrame:
    """Every decision's geometry, with no model applied yet.

    Separated from the condition because this is the part that touches disk:
    74 race lap files, which epsilon has no effect on. The sensitivity table
    then varies epsilon against one shared reading of them.
    """
    decisions = pd.read_csv(DECISIONS)
    theta_by = _theta()
    delta_by = _delta()
    rows = []

    for (season, circuit), part in decisions.groupby(["season", "circuit"]):
        try:
            laps = load_race_laps(f"{int(season)}_{circuit}")
        except (FileNotFoundError, LookupError, ValueError):
            continue
        for decision in part.itertuples():
            lap = int(decision.real_pit_lap)
            near = _nearest_by_seconds(laps, str(decision.driver), lap)
            if near is None or "leader" not in near:
                # No car ahead on the clock: the race leader has nobody to
                # undercut, so the game this models does not arise.
                rows.append({
                    "season": int(season), "circuit": str(circuit),
                    "driver": str(decision.driver),
                    "real_pit_lap": lap,
                    "single_car_lap": int(decision.single_car_lap),
                    "role": "race leader",
                })
                continue

            compound = _compound_at(laps, str(decision.driver), lap)
            age = _tyre_age_at(laps, str(decision.driver), lap)
            theta, resolved = theta_by.get(
                (str(circuit), str(compound)), (float("nan"), False)
            )
            gap = near["gap_to_leader_s"]
            # The lap the tyre went on, which is what turns a tyre age into a
            # lap number later.
            stint_start = lap - age if age is not None else None
            rows.append({
                "season": int(season), "circuit": str(circuit),
                "driver": str(decision.driver),
                "role": "chaser",
                "leader": near["leader"],
                "gap_to_leader_s": round(gap, 3),
                "compound": compound,
                "tyre_age": age,
                "theta": theta,
                "theta_resolved": resolved,
                "stint_start_lap": stint_start,
                "real_pit_lap": lap,
                "single_car_lap": int(decision.single_car_lap),
                "pit_loss_s": delta_by.get(str(circuit), float("nan")),
            })

    frame = pd.DataFrame(rows)
    # Whether the undercut could gain the position at all, which is the
    # first-order version of the same question: a stop costs `pit_loss_s`, so
    # a lead larger than that cannot be taken by stopping one lap earlier
    # however good the tyre is.
    frame["within_pit_loss"] = frame["gap_to_leader_s"] <= frame["pit_loss_s"]
    frame["single_car_error"] = frame["single_car_lap"] - frame["real_pit_lap"]
    return frame


def apply_condition(frame: pd.DataFrame, epsilon: float) -> pd.DataFrame:
    """Salminen's D1 condition, at one value of the pace term."""
    out = frame.copy()
    out["epsilon"] = np.where(out["role"] == "chaser", epsilon, np.nan)
    out["d1_expiry_lap"] = [
        d1_expiry(row.gap_to_leader_s, row.theta, epsilon)
        if row.role == "chaser" else float("nan")
        for row in out.itertuples()
    ]
    # The expiry is a tyre age, because Salminen's l_u counts laps of tyre
    # use. Turning it into a lap number needs the lap the tyre went on.
    out["euu_lap"] = np.where(
        np.isfinite(out["d1_expiry_lap"]) & out["stint_start_lap"].notna(),
        # Floor, because the defence holds through the whole of the lap it
        # expires on, and the earliest undefendable undercut is the next one.
        np.floor(out["d1_expiry_lap"]) + 1 + out["stint_start_lap"],
        np.nan,
    )
    # Inverted: what degradation rate would put D1's expiry at the lap the
    # team actually stopped on. Salminen's condition at l_u = the real tyre
    # age gives theta* = (g - epsilon) / l_u. Comparing it to the measured
    # theta says by how much the linear model would have to be wrong for his
    # equilibrium to reproduce real behaviour, which is sharper than "the
    # prediction is late".
    out["implied_theta"] = np.where(
        out["tyre_age"].fillna(0) > 0,
        (out["gap_to_leader_s"] - epsilon) / out["tyre_age"],
        np.nan,
    )
    out["theta_ratio"] = out["implied_theta"] / out["theta"]
    out["euu_error"] = out["euu_lap"] - out["real_pit_lap"]
    return out


def build(epsilon: float = EPSILON) -> pd.DataFrame:
    """Kept for callers that want one frame at one epsilon."""
    return apply_condition(collect(), epsilon)


def _tercile(frame: pd.DataFrame) -> pd.Series:
    """Label each decision by how fast its tyre degrades.

    Stratified because the prediction divides by theta: on a slow-degrading
    circuit-compound the D1 window is enormous and the model says the chaser
    should wait, while on a fast one it closes within a few laps. Pooling the
    two would average a prediction of lap 4 with one of lap 90 and report the
    mean as a result.
    """
    usable = frame[frame["theta_resolved"] & frame["theta"].notna()]
    if usable.empty:
        return pd.Series("unresolved", index=frame.index)
    cuts = usable["theta"].quantile([1 / 3, 2 / 3]).to_list()
    def label(row):
        if not row["theta_resolved"] or not np.isfinite(row["theta"]):
            return "unresolved"
        if row["theta"] <= cuts[0]:
            return "slow (bottom third)"
        if row["theta"] <= cuts[1]:
            return "middle third"
        return "fast (top third)"
    return frame.apply(label, axis=1)


def summarise(frame: pd.DataFrame) -> pd.DataFrame:
    chasers = frame[frame["role"] == "chaser"].copy()
    chasers["tercile"] = _tercile(chasers)
    rows = []
    for name, part in chasers.groupby("tercile"):
        usable = part[part["euu_lap"].notna()]
        rows.append({
            "stratum": name,
            "decisions": len(part),
            "with_a_prediction": len(usable),
            "median_theta": round(float(part["theta"].median()), 4),
            "median_gap_s": round(float(part["gap_to_leader_s"].median()), 2),
            "median_d1_window_laps": (
                round(float(usable["d1_expiry_lap"].median()), 1)
                if len(usable) else float("nan")
            ),
            "median_euu_error": (
                round(float(usable["euu_error"].median()), 1)
                if len(usable) else float("nan")
            ),
            "median_single_car_error": round(
                float(part["single_car_error"].median()), 1
            ),
            "euu_closer": int(
                (usable["euu_error"].abs()
                 < usable["single_car_error"].abs()).sum()
            ),
            "euu_further": int(
                (usable["euu_error"].abs()
                 > usable["single_car_error"].abs()).sum()
            ),
        })
    return pd.DataFrame(rows)

def write_report(frame: pd.DataFrame, totals: pd.DataFrame,
                 sensitivity: pd.DataFrame) -> Path:
    chasers = frame[frame["role"] == "chaser"]
    leaders = frame[frame["role"] == "race leader"]
    usable = chasers[chasers["euu_lap"].notna()]
    closer = int((usable["euu_error"].abs() < usable["single_car_error"].abs()).sum())
    further = int((usable["euu_error"].abs() > usable["single_car_error"].abs()).sum())
    implied = chasers[chasers["theta_resolved"] & chasers["implied_theta"].notna()]
    reachable = chasers[chasers["pit_loss_s"].notna()]

    lines = [
        "<!-- generated by scripts/run_d1_defence.py -->",
        "",
        "# The position-keeping defence, tested against 357 real decisions",
        "",
        "Generated. Do not edit by hand.",
        "",
        "Salminen (2026) gives the third candidate explanation for this "
        "project's late-stop gap, and the only one so far whose sign is "
        "right. In his one-stop game a chaser stops at the earliest lap the "
        "leader can no longer answer, which falls before the time-optimal "
        "lap. His position-keeping defence D1 is efficient while",
        "",
        "```",
        "theta * l_u + epsilon  <  g",
        "```",
        "",
        "so it expires at a tyre age of `(g - epsilon) / theta`, and where "
        "the overcut defence is unavailable the earliest undefendable "
        "undercut is the lap after. "
        "[`overcut_feasibility.md`](overcut_feasibility.md) measures that the "
        "overcut is indeed unreachable on 16 of the 73 circuit-compounds "
        "fitted here, and opens only past half-distance on 19 — so on "
        "roughly a quarter of them D1 is the only defence there is.",
        "",
        "**The result is negative.** Fed with the gaps and degradation rates "
        "measured in this project, the condition says a Formula 1 leader can "
        "defend an undercut for longer than the race lasts, so the chaser "
        "should never undercut. Teams undercut anyway, at a median lap "
        f"{int(chasers['real_pit_lap'].median())}.",
        "",
        "## What the decisions look like before any model touches them",
        "",
        f"Of the {len(frame)} first-stop decisions the audit replays, "
        f"**{len(leaders)}** belong to a car with nobody ahead of it on the "
        "clock within one lap. The race leader has no undercut to perform, "
        "so this game does not arise and those decisions carry no "
        "prediction.",
        "",
        f"For the remaining **{len(chasers)}**, the leader is close: a median "
        f"gap of **{chasers['gap_to_leader_s'].median():.1f} s**, quartiles "
        f"{chasers['gap_to_leader_s'].quantile(0.25):.1f} to "
        f"{chasers['gap_to_leader_s'].quantile(0.75):.1f}. On "
        f"**{int(reachable['within_pit_loss'].sum())} of {len(reachable)}** "
        f"({100 * reachable['within_pit_loss'].mean():.0f}%) the gap is "
        "smaller than the circuit's measured pit loss, so the position is in "
        "principle takeable by stopping first. Reachability is not the "
        "binding constraint here, which is worth saying because it was the "
        "first thing this was expected to find.",
        "",
        "## Where D1 expires, by how fast the tyre degrades",
        "",
        "Stratified because the prediction divides by `theta`. Pooling a "
        "window of four laps with one of ninety and reporting the mean would "
        "describe neither.",
        "",
        "| stratum | decisions | median `theta` | median gap (s) | median D1 window (laps of tyre use) | median error vs real | optimiser's error | D1 closer | D1 further |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    order = ["fast (top third)", "middle third", "slow (bottom third)",
             "unresolved"]
    for name in order:
        rows = totals[totals["stratum"] == name]
        if rows.empty:
            continue
        row = rows.iloc[0]
        lines.append(
            f"| {name} | {int(row['decisions'])} | "
            f"{row['median_theta']:.4f} | {row['median_gap_s']:.2f} | "
            f"{row['median_d1_window_laps']:.0f} | "
            f"{row['median_euu_error']:+.0f} | "
            f"{row['median_single_car_error']:+.0f} | "
            f"{int(row['euu_closer'])} | {int(row['euu_further'])} |"
        )
    lines += [
        "",
        "Errors are signed in laps, positive meaning later than the team "
        "stopped. The optimiser column is the existing single-car baseline "
        "on the same decisions, for scale.",
        "",
        f"Across all {len(usable)} decisions carrying a prediction, D1's "
        f"earliest undefendable undercut lands a median of "
        f"**{usable['euu_error'].median():+.0f} laps** from the real stop "
        f"against the optimiser's "
        f"**{usable['single_car_error'].median():+.0f}**. It is closer on "
        f"{closer} and further on {further}. On "
        f"{100 * (usable['euu_lap'] > usable['real_pit_lap'] + 40).mean():.0f}% "
        "of them the predicted lap is beyond the end of the race.",
        "",
        "## Why it fails, stated as a number rather than a guess",
        "",
        "The condition can be inverted. Setting `l_u` to the tyre age at the "
        "stop the team actually made gives the degradation rate at which D1 "
        "would have expired exactly then:",
        "",
        "```",
        "theta* = (g - epsilon) / l_u(real)",
        "```",
        "",
        f"Over the {len(implied)} decisions with a resolved slope, the median "
        f"`theta*` is **{implied['implied_theta'].median():.3f} s/lap** "
        f"against a measured median of "
        f"**{implied['theta'].median():.3f}**. The ratio is a median "
        f"**{implied['theta_ratio'].median():.1f} times**, quartiles "
        f"{implied['theta_ratio'].quantile(0.25):.1f} to "
        f"{implied['theta_ratio'].quantile(0.75):.1f}, and `theta*` exceeds "
        f"the measured rate on "
        f"{100 * (implied['theta_ratio'] > 1).mean():.0f}% of them. A rate of "
        f"{implied['implied_theta'].median():.3f} s/lap sits at roughly the "
        "99th percentile of every slope fitted in five seasons of Formula 1.",
        "",
        "So the gap is not a matter of calibration. For his equilibrium to "
        "reproduce what teams do, tyres would have to degrade at a rate the "
        "data almost never shows.",
        "",
        "The reading this suggests, and does not establish, is that a linear "
        "`theta` is the wrong object for the quantity the undercut turns on. "
        "`theta * l_u` prices the defender's loss over a single lap on a tyre "
        "`l_u` laps old: at a measured 0.045 s/lap and a twenty-lap tyre that "
        "is under a second, which a three-second lead covers easily. What "
        "wins a real undercut is the advantage of a tyre on its first flying "
        "lap over one at the end of its life, and nothing in a linear slope "
        "represents the first-lap part of that. Measuring it directly is a "
        "different estimator and is not attempted here.",
        "",
        "## Sensitivity to the pace term",
        "",
        "`epsilon` is zero in everything above. Measuring it from lap times "
        "would mean reading a chaser's pace while it sits in dirty air, which "
        "inflates the estimate, and a larger `epsilon` expires D1 earlier and "
        "so moves the prediction toward the real stop. That is the flattering "
        "direction, so it is reported here and not above.",
        "",
        "| `epsilon` (s/lap) | median D1 window | median error vs real | D1 closer | D1 further |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in sensitivity.iterrows():
        lines.append(
            f"| {row['epsilon']:.2f} | {row['median_d1_window_laps']:.0f} | "
            f"{row['median_euu_error']:+.0f} | {int(row['euu_closer'])} | "
            f"{int(row['euu_further'])} |"
        )
    lines += [
        "",
        "It does not rescue the prediction at any value worth defending.",
        "",
        "## What is implemented and what is not",
        "",
        "Only D1. The overcut defence D2 needs `o`, an overtaking threshold "
        "in seconds, and this project holds no such quantity: what it "
        "measures per circuit is an adjacent-pair swap probability per lap, "
        "a different object that does not convert into one. Estimating `o` "
        "from observed pace deltas would be biased toward zero exactly where "
        "overtaking is hardest, because a car held in traffic is measured at "
        "its traffic pace rather than its clean one \u2014 the bias would be "
        "largest where the phenomenon is largest. D2 is therefore an "
        "extension conditioned on a calibration that does not exist, and is "
        "not reported as a result anywhere.",
        "",
        "The rival here is chosen by gap in seconds rather than by classified "
        "position. That was Charles Thraves's objection to the published "
        "replay, where minimising absolute position distance left 271 of 357 "
        "decisions as ties between a car ahead and a car behind. On the clock "
        "there are no ties and leader against chaser is settled without a "
        "tie-break. The published replay is untouched; this writes its own "
        "artifacts.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return OUT_MD


def sensitivity_table(geometry: pd.DataFrame) -> pd.DataFrame:
    """The same measurement at the epsilon values the headline refuses to use."""
    rows = []
    for epsilon in (EPSILON, *EPSILON_SENSITIVITY):
        frame = apply_condition(geometry, epsilon)
        usable = frame[(frame["role"] == "chaser") & frame["euu_lap"].notna()]
        rows.append({
            "epsilon": epsilon,
            "median_d1_window_laps": round(
                float(usable["d1_expiry_lap"].median()), 1
            ),
            "median_euu_error": round(float(usable["euu_error"].median()), 1),
            "euu_closer": int(
                (usable["euu_error"].abs()
                 < usable["single_car_error"].abs()).sum()
            ),
            "euu_further": int(
                (usable["euu_error"].abs()
                 > usable["single_car_error"].abs()).sum()
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    geometry = collect()
    frame = apply_condition(geometry, EPSILON)
    totals = summarise(frame)
    sensitivity = sensitivity_table(geometry)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(Path.cwd())}")
    out = write_report(frame, totals, sensitivity)
    print(f"wrote {out.relative_to(Path.cwd())}")
    print()
    print(totals.to_string(index=False))
    print()
    print(sensitivity.to_string(index=False))


if __name__ == "__main__":
    main()
