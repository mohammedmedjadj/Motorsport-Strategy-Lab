"""Online degradation Kalman filter: converges to a known constant slope,
tightens its uncertainty as laps arrive, and — unlike a static fit — tracks a
mid-stint change in the degradation rate."""

from __future__ import annotations

import numpy as np
import pytest

from src.degradation.kalman import DegradationKalman, filter_stint


def _linear_stint(slope: float, n: int, noise_s: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ages = np.arange(1, n + 1)
    return slope * ages + rng.normal(0.0, noise_s, n)


def test_converges_to_known_constant_slope() -> None:
    true_slope = 0.08
    offsets = _linear_stint(true_slope, n=25, noise_s=0.15, seed=1)
    states = filter_stint(offsets, meas_var=0.15**2, slope_process_var=1e-6)
    assert states[-1].slope == pytest.approx(true_slope, abs=0.02)


def test_uncertainty_shrinks_as_laps_arrive() -> None:
    offsets = _linear_stint(0.08, n=25, noise_s=0.15, seed=2)
    states = filter_stint(offsets, meas_var=0.15**2, slope_process_var=1e-6)
    early = states[4].slope_sd   # after 5 laps
    late = states[-1].slope_sd   # after 25 laps
    assert late < early
    assert all(np.all(np.linalg.eigvalsh(s.cov) >= -1e-9) for s in states)  # PSD


def test_tracks_a_degradation_cliff() -> None:
    """Gentle deg for 15 laps, then a steep cliff. A single static slope cannot
    represent both; the filter's slope estimate must climb after the cliff."""
    rng = np.random.default_rng(3)
    gentle = 0.03 * np.arange(1, 16)
    cliff_start = gentle[-1]
    steep = cliff_start + 0.30 * np.arange(1, 16)
    offsets = np.concatenate([gentle, steep]) + rng.normal(0.0, 0.10, 30)
    # A looser slope process variance lets the filter adapt to the regime change.
    states = filter_stint(offsets, meas_var=0.10**2, slope_process_var=1e-3)
    slope_before = states[13].slope   # end of the gentle phase
    slope_after = states[-1].slope    # deep into the cliff
    assert slope_after > slope_before + 0.10
    assert slope_after == pytest.approx(0.30, abs=0.08)


def test_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="meas_var"):
        DegradationKalman(meas_var=0.0)
    with pytest.raises(ValueError, match="process variance"):
        DegradationKalman(meas_var=0.1, slope_process_var=-1.0)


def test_state_accessors_and_dims() -> None:
    kf = DegradationKalman(meas_var=0.02, init_slope=0.05)
    st = kf.step(0.05)
    assert st.mean.shape == (2,) and st.cov.shape == (2, 2)
    assert isinstance(st.slope, float) and isinstance(st.slope_sd, float)
