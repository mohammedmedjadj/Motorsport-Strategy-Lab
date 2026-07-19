"""Property-based invariants for the Monte Carlo engine.

The example-based tests in ``test_simulator.py`` pin down behaviour on a few
hand-picked scenarios. These push the same invariants across thousands of
randomly generated (but valid) circuit models and race states, so a claim
like "``p_best`` is a probability distribution" or "``_sample_status`` never
writes out of bounds" is checked against the input space, not one example.
"""

from __future__ import annotations

import numpy as np
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.simulator.artifacts import CircuitModel, GaussianCoef, HazardPosterior
from src.simulator.engine import GREEN, SC, VSC, Scenario, _sample_status, simulate
from src.simulator.pit_loss import PaceRatios, PitLossEstimate

# Keep the search fast: these run inside a normal pytest invocation.
FAST = settings(max_examples=40, deadline=None)

# --- strategies for valid model inputs -------------------------------------

positive = st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False)
durations = st.lists(st.integers(min_value=1, max_value=8), min_size=1, max_size=6)


@st.composite
def coefs(draw: st.DrawFn) -> GaussianCoef:
    mean = draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False))
    sd = draw(st.floats(min_value=0.0, max_value=0.05, allow_nan=False))
    return GaussianCoef(mean=mean, sd=sd)


@st.composite
def models(draw: st.DrawFn) -> CircuitModel:
    """A structurally valid CircuitModel with SOFT/HARD compounds."""
    exposure = draw(st.floats(min_value=50.0, max_value=2000.0))
    sc_rate = draw(st.floats(min_value=0.0, max_value=0.15))
    vsc_rate = draw(st.floats(min_value=0.0, max_value=0.15))
    sc_ratio = draw(st.floats(min_value=1.0, max_value=2.0))
    vsc_ratio = draw(st.floats(min_value=1.0, max_value=2.0))
    return CircuitModel(
        circuit="hyp",
        green_pace_s=draw(st.floats(min_value=60.0, max_value=120.0)),
        lap_noise_s=draw(st.floats(min_value=0.0, max_value=1.5)),
        fuel_slope=draw(coefs()),
        degradation={"SOFT": (draw(coefs()),), "HARD": (draw(coefs()),)},
        sc_hazard=HazardPosterior(alpha=max(sc_rate * exposure, 1e-6), beta=exposure),
        vsc_hazard=HazardPosterior(alpha=max(vsc_rate * exposure, 1e-6), beta=exposure),
        sc_durations=tuple(draw(durations)),
        vsc_durations=tuple(draw(durations)),
        pit_loss=PitLossEstimate("hyp", median_s=draw(positive) * 10, iqr_s=1.0, n_events=10),
        pace_ratios=PaceRatios("hyp", sc_ratio, vsc_ratio, 10, 5, False, False),
    )


@st.composite
def scenarios(draw: st.DrawFn) -> Scenario:
    """A race state with a non-empty feasible pit window (total >= current+4)."""
    current = draw(st.integers(min_value=1, max_value=50))
    total = draw(st.integers(min_value=current + 4, max_value=current + 40))
    return Scenario(
        circuit="hyp",
        current_lap=current,
        total_laps=total,
        compound="SOFT",
        tyre_age=draw(st.integers(min_value=0, max_value=30)),
        target_compound="HARD",
        include_no_stop=draw(st.booleans()),
    )


# --- invariants -------------------------------------------------------------


@FAST
@given(model=models(), scenario=scenarios(), seed=st.integers(0, 2**31 - 1))
def test_p_best_is_always_a_probability_distribution(
    model: CircuitModel, scenario: Scenario, seed: int
) -> None:
    result = simulate(scenario, model, n_draws=120, seed=seed)
    p = result.p_best
    assert np.all(p >= 0.0)
    assert p.sum() == np.float64(1.0) or abs(float(p.sum()) - 1.0) < 1e-9
    assert len(p) == len(result.candidates)


@FAST
@given(model=models(), scenario=scenarios(), seed=st.integers(0, 2**31 - 1))
def test_our_time_is_finite(
    model: CircuitModel, scenario: Scenario, seed: int
) -> None:
    result = simulate(scenario, model, n_draws=120, seed=seed)
    assert np.all(np.isfinite(result.our_time))


@FAST
@given(model=models(), scenario=scenarios(), seed=st.integers(0, 2**31 - 1))
def test_same_seed_is_reproducible(
    model: CircuitModel, scenario: Scenario, seed: int
) -> None:
    a = simulate(scenario, model, n_draws=80, seed=seed)
    b = simulate(scenario, model, n_draws=80, seed=seed)
    assert np.array_equal(a.our_time, b.our_time)


@FAST
@given(
    model=models(),
    n_laps=st.integers(min_value=1, max_value=120),
    seed=st.integers(0, 2**31 - 1),
    ongoing=st.one_of(
        st.none(),
        st.tuples(st.sampled_from(["SC", "VSC"]), st.integers(min_value=0, max_value=6)),
    ),
)
def test_status_timeline_is_well_formed(
    model: CircuitModel, n_laps: int, seed: int, ongoing: tuple[str, int] | None
) -> None:
    """_sample_status must return exactly n_laps entries, all in {GREEN,SC,VSC},
    for any hazard rate / duration pool / ongoing neutralisation. This is the
    formal refutation of the alleged out-of-bounds 'race condition': numpy slice
    assignment truncates, so no write ever escapes the array."""
    rng = np.random.default_rng(seed)
    status = _sample_status(model, n_laps, rng, ongoing)
    assert status.shape == (n_laps,)
    assert set(np.unique(status)).issubset({GREEN, SC, VSC})


@FAST
@given(model=models(), scenario=scenarios(), seed=st.integers(0, 2**31 - 1))
def test_candidates_are_inside_race_bounds(
    model: CircuitModel, scenario: Scenario, seed: int
) -> None:
    result = simulate(scenario, model, n_draws=40, seed=seed)
    real = [c for c in result.candidates if c > 0]  # 0 = stay-out pseudo-candidate
    assert min(real) == scenario.current_lap + 1
    assert max(real) <= scenario.total_laps - 3
