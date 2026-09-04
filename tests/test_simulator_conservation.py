"""Does the Monte Carlo add up? Conservation invariants for race time.

`test_simulator_properties.py` checks that outputs are *well formed* — `p_best`
is a distribution, times are finite, candidates sit inside the race. None of
that would notice the engine dropping a lap, charging a pit loss twice, or
letting a slower tyre produce a faster race. Those are accounting errors, they
shift every recommendation the audit reports, and they are invisible in a
smoke test because the output still looks like a plausible race time.

`SimulationResult` exposes only `our_time`, so the components cannot be
inspected directly. They can still be pinned, by perturbing one input and
requiring the output to move by exactly the amount arithmetic demands:

- add `c` seconds to every lap  ->  every draw must gain exactly `c * laps`
- add `d` seconds to the pit loss  ->  a one-stop plan gains exactly `d`,
  and a no-stop plan gains nothing
- make the tyre wear faster  ->  no draw may get quicker

Each runs under common random numbers, so the two simulations differ only in
the perturbed quantity and the comparison is exact rather than statistical.

Neutralisations are neutralised on purpose: with both pace ratios set to 1.0 a
Safety Car lap costs what a green lap costs, so these equalities hold whatever
the sampled timeline does. That isolates the accounting from the neutralisation
model, which has its own tests.
"""

from __future__ import annotations

import numpy as np

from src.simulator.artifacts import CircuitModel, CoefPosterior, HazardPosterior
from src.simulator.engine import Scenario, simulate
from src.simulator.pit_loss import PaceRatios, PitLossEstimate

SEED = 20260904
DRAWS = 400

#: Laps under caution cost the same as green laps, so a lap is a lap no matter
#: what the status timeline draws. Without this, adding `c` to the base pace
#: adds `c * sum(pace_ratios)` and the equality below is no longer exact.
FLAT_RATIOS = PaceRatios("hyp", 1.0, 1.0, 10, 5, False, False)


def _model(
    green_pace_s: float = 90.0,
    pit_loss_s: float = 22.0,
    soft_slope: float = 0.05,
    hard_slope: float = 0.03,
) -> CircuitModel:
    """A deterministic circuit: no lap noise, no coefficient spread.

    Randomness is not what these test. Removing it makes every difference below
    an exact arithmetic identity instead of something that holds to a
    tolerance, and a tolerance is where an accounting bug hides.
    """
    return CircuitModel(
        circuit="hyp",
        green_pace_s=green_pace_s,
        lap_noise_s=0.0,
        fuel_slope=CoefPosterior(mean=-0.05, sd=0.0),
        degradation={
            "SOFT": (CoefPosterior(mean=soft_slope, sd=0.0),),
            "HARD": (CoefPosterior(mean=hard_slope, sd=0.0),),
        },
        sc_hazard=HazardPosterior(alpha=2.0, beta=200.0),
        vsc_hazard=HazardPosterior(alpha=2.0, beta=200.0),
        sc_durations=(3, 4, 5),
        vsc_durations=(2, 3),
        pit_loss=PitLossEstimate("hyp", median_s=pit_loss_s, iqr_s=0.0, n_events=10),
        pace_ratios=FLAT_RATIOS,
    )


def _scenario(include_no_stop: bool = False) -> Scenario:
    return Scenario(
        circuit="hyp",
        current_lap=10,
        total_laps=50,
        compound="SOFT",
        tyre_age=5,
        target_compound="HARD",
        include_no_stop=include_no_stop,
    )


def _run(model: CircuitModel, scenario: Scenario):
    return simulate(scenario, model, n_draws=DRAWS, seed=SEED)


def test_race_time_is_exactly_linear_in_lap_pace() -> None:
    """Adding c to every lap must add exactly c x laps. No lap lost or doubled.

    This is the strongest statement available without decomposing the result:
    the coefficient on the pace shift *is* the number of laps the engine
    charged for. If it drops the in-lap, double-counts the lap of the stop, or
    runs one lap past the flag, this equality breaks by exactly that lap.
    """
    scenario = _scenario()
    shift = 1.5
    base = _run(_model(), scenario)
    bumped = _run(_model(green_pace_s=90.0 + shift), scenario)

    laps = scenario.total_laps - scenario.current_lap
    difference = bumped.our_time - base.our_time

    assert base.candidates == bumped.candidates
    charged = difference / shift
    assert np.allclose(charged, laps, atol=1e-6), (
        f"the engine charged for {np.unique(np.round(charged, 6))} laps where "
        f"the race has {laps} remaining. A pace shift must scale with the lap "
        "count exactly; anything else means a lap is being dropped, "
        "double-counted, or simulated past the flag."
    )


def test_a_pit_stop_is_charged_exactly_once() -> None:
    """Every one-stop candidate absorbs the pit-loss change once, no more."""
    scenario = _scenario()
    extra = 4.0
    base = _run(_model(), scenario)
    dearer = _run(_model(pit_loss_s=22.0 + extra), scenario)

    difference = dearer.our_time - base.our_time
    stops = difference / extra
    assert np.allclose(stops, 1.0, atol=1e-6), (
        f"candidates absorbed {np.unique(np.round(stops, 6))} pit losses, not "
        "one. Every candidate here stops exactly once, so a value of 2 means "
        "the loss is applied on both the in- and out-lap, and 0 means the "
        "plan is not paying for its own stop."
    )


def test_a_plan_that_never_stops_pays_no_pit_loss() -> None:
    """The control for the test above: no stop, no charge.

    Without it, an engine that added the pit loss to *every* candidate
    regardless of its plan would pass the one-stop check unnoticed.
    """
    scenario = _scenario(include_no_stop=True)
    base = _run(_model(), scenario)
    dearer = _run(_model(pit_loss_s=99.0), scenario)

    # `simulate` appends the stay-out plan as candidate lap **0**, not as a lap
    # at or past the flag. Written against the guessed encoding first, this
    # test skipped silently and protected nothing — which is its own lesson
    # about controls that are allowed to opt out.
    no_stop = [i for i, lap in enumerate(base.candidates) if lap == 0]
    assert no_stop, (
        "include_no_stop=True produced no stay-out candidate. Either the "
        "encoding changed or the option stopped working, and either way the "
        "control below is not running."
    )

    for index in no_stop:
        assert np.allclose(base.our_time[index], dearer.our_time[index], atol=1e-6), (
            f"candidate {base.candidates[index]} never pits, yet quadrupling "
            "the pit loss changed its race time. The loss is being applied to "
            "plans that do not use it."
        )


def test_a_faster_wearing_tyre_never_produces_a_faster_race() -> None:
    """Monotone in degradation, per draw, for every candidate.

    A sign error in the tyre-age term is the kind of defect that leaves every
    number plausible and every recommendation wrong, and no well-formedness
    check can see it.
    """
    scenario = _scenario()
    gentle = _run(_model(soft_slope=0.02, hard_slope=0.01), scenario)
    harsh = _run(_model(soft_slope=0.20, hard_slope=0.10), scenario)

    assert np.all(harsh.our_time >= gentle.our_time - 1e-9), (
        "a tyre that wears ten times faster produced a quicker race in "
        f"{int(np.sum(harsh.our_time < gentle.our_time - 1e-9))} of "
        f"{harsh.our_time.size} draws. The tyre-age term is not adding time."
    )


def test_common_random_numbers_really_are_common() -> None:
    """The three tests above are only exact if the two runs share their draws.

    If the seed did not fully determine the status timeline and the per-lap
    noise, each comparison would be measuring sampling noise as well as the
    perturbation, and the tight tolerances above would be meaningless — or
    worse, would pass by luck at this draw count.
    """
    scenario = _scenario()
    first = _run(_model(), scenario)
    second = _run(_model(), scenario)
    assert np.array_equal(first.our_time, second.our_time), (
        "two identical simulations with the same seed disagree, so the "
        "comparisons in this file are not controlled and their tolerances "
        "mean nothing."
    )
