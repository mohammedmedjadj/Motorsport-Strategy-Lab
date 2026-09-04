"""Three simple pit-stop rules, to answer the first question a reviewer asks.

The decision audit replays 1,280 real first stops through an exact dynamic
program and a Monte Carlo engine, and reports that the model stops later than
the team did on 80-83% of them. The obvious response is: *does your optimiser
beat a rule of thumb?* Without an answer, the audit measures a sophisticated
model against reality and never establishes that the sophistication earns its
place.

So three baselines, scored on the **same decisions and the same metric** as the
audit itself — absolute lap error against what the team actually did:

- **B1, fixed interval.** Divide the race into equal stints. Uses no
  measurement at all beyond the race length and how many stops are needed.
- **B2, threshold.** Stop when the time lost to tyre wear since the stint began
  has grown past the cost of the stop. Uses the fitted slope and the measured
  pit loss, and nothing else — no fuel model, no neutralisations, no Monte
  Carlo.
- **B3, fuel deadline.** Run until the tank is empty. Undefined for F1, which
  has not refuelled since 2010, and reported as undefined rather than faked.

**These are written to win if they can.** A baseline built as a straw man
proves nothing, and the interesting outcome is the one where a naive rule sits
closer to practice than the exact optimum — that would not weaken the audit's
finding, it would sharpen it into a claim about what optimisers are for.

Every function here is pure: it takes numbers and returns a lap. The messy part
— finding each decision's inputs in the committed artifacts — lives in
`scripts/run_baseline_comparison.py`, so these can be tested against worked
examples with no data pipeline attached.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """A baseline's answer, and whether it had enough to answer at all."""

    lap: int | None
    #: Why the rule could not be applied, when `lap` is None. Populated rather
    #: than silently returning a default, because a baseline that quietly
    #: guesses when it lacks inputs is not a baseline, it is noise that looks
    #: like a comparison.
    undefined_reason: str | None = None

    @property
    def is_defined(self) -> bool:
        return self.lap is not None


def fixed_interval(race_laps: int, n_stops: int, which: int = 1) -> Recommendation:
    """B1: split the race into ``n_stops + 1`` equal stints.

    The crudest defensible rule, and a real one — it is what a team does before
    it knows anything about the tyre. Uses no fitted quantity whatsoever, which
    is exactly what makes it a floor: anything the model does that this rule
    does not do has to justify itself against this.

    ``which`` selects the stop, so the first of a two-stop plan is
    ``which=1, n_stops=2``. The audit compares first stops, so ``which`` is 1
    throughout, but the parameter exists because a rule that can only produce
    the first stop is not the rule teams use.
    """
    if race_laps <= 0:
        return Recommendation(None, "race length unknown")
    if n_stops < 1:
        return Recommendation(None, "a plan with no stops has no stop lap")
    if not 1 <= which <= n_stops:
        return Recommendation(None, f"stop {which} does not exist in a {n_stops}-stop plan")
    return Recommendation(int(round(which * race_laps / (n_stops + 1))))


def cumulative_degradation_s(slope_s_per_lap: float, tyre_age: int) -> float:
    """Time lost to tyre wear over a stint, against running on fresh rubber.

    A tyre `a` laps old is ``slope * a`` seconds slower than a new one, so the
    whole stint has cost ``slope * (1 + 2 + ... + a)``. The exact triangular sum
    is used rather than the ``slope * a^2 / 2`` integral: they differ by
    ``slope * a / 2``, which is about a second over a 40-lap stint at a typical
    F1 slope — small, but this is the quantity the whole rule turns on and
    there is no reason to approximate it.
    """
    if tyre_age <= 0:
        return 0.0
    return float(slope_s_per_lap) * tyre_age * (tyre_age + 1) / 2.0


def threshold(
    decision_lap: int,
    tyre_age_at_decision: int,
    slope_s_per_lap: float,
    pit_loss_s: float,
    race_laps: int,
    min_final_stint: int = 3,
) -> Recommendation:
    """B2: stop once the stint's accumulated tyre loss exceeds the pit loss.

    The rule an engineer states out loud: *the tyre has now cost you more than
    the stop would*. It consumes the same fitted slope and the same measured pit
    loss the simulator does, and none of the rest — no fuel term, no
    neutralisation hazard, no distribution over outcomes. The gap between this
    and the full engine is precisely what the Monte Carlo buys.

    The comparison is strictly *greater than*, so a stint whose accumulated
    loss exactly equals the pit loss does not yet fire. At that point the rule
    is genuinely indifferent — stopping and staying out cost the same — and
    floating point decides it either way (0.20 s/lap against a 60 s pit loss
    computes 60.000000000000014 at age 24 and fires, where exact arithmetic
    would not). A tolerance would relocate the arbitrariness rather than remove
    it, and real fitted slopes never land on the boundary, so it is left
    stated rather than papered over.

    Returns the first lap at or after ``decision_lap`` where the condition
    holds. If it never holds before the flag, the rule says *do not stop*, and
    that is reported as undefined rather than coerced to the last lap — a rule
    forced to produce an answer it does not have is being scored on the
    coercion, not the rule.
    """
    if slope_s_per_lap <= 0:
        return Recommendation(
            None, "slope is not positive: this tyre never repays a stop"
        )
    if pit_loss_s <= 0:
        return Recommendation(None, "pit loss unknown or not positive")

    latest = race_laps - min_final_stint
    lap, age = decision_lap, tyre_age_at_decision
    while lap <= latest:
        if cumulative_degradation_s(slope_s_per_lap, age) > pit_loss_s:
            return Recommendation(int(lap))
        lap += 1
        age += 1
    return Recommendation(
        None,
        f"tyre loss never exceeds the {pit_loss_s:.1f}s pit loss before the flag",
    )


def threshold_age(slope_s_per_lap: float, pit_loss_s: float) -> float:
    """The tyre age at which B2 fires, ignoring where the stint started.

    Closed form for the same condition, useful for reasoning about the rule
    rather than running it: solving ``slope * a(a+1)/2 = pit_loss`` gives
    ``a = (-1 + sqrt(1 + 8*pit_loss/slope)) / 2``. Reported in laps, unrounded.
    """
    if slope_s_per_lap <= 0 or pit_loss_s <= 0:
        return float("inf")
    return (-1.0 + math.sqrt(1.0 + 8.0 * pit_loss_s / slope_s_per_lap)) / 2.0


def fuel_deadline(deadline_lap: int | None, refuelling_allowed: bool = True) -> Recommendation:
    """B3: run to the last lap the fuel load reaches, then stop.

    In endurance racing this is not naive at all — it is close to what teams
    actually do, because the stop is expensive and the tank is the binding
    constraint in all but a handful of races. It is the baseline most likely to
    beat the optimiser, which is the point of including it.

    **Undefined for Formula 1.** Refuelling has been banned since 2010, so
    there is no fuel deadline to run to and no honest way to invent one. It
    returns undefined rather than substituting the race end, because scoring a
    rule that does not exist against real stops would put a number in a table
    that means nothing.
    """
    if not refuelling_allowed:
        return Recommendation(
            None, "no refuelling in this series: the rule does not apply"
        )
    if deadline_lap is None or deadline_lap <= 0:
        return Recommendation(None, "no measured fuel range for this race")
    return Recommendation(int(deadline_lap))


#: The baselines, in the order they should be reported: cheapest information
#: first, so a reader can see what each additional input buys.
NAMES = ("B1 fixed interval", "B2 threshold", "B3 fuel deadline")
