"""Online (lap-by-lap) degradation estimation with a Kalman filter.

The Phase 2 OLS model is *retrospective*: it needs a whole stint (indeed a whole
season) before it can state a degradation slope. A race strategist needs the
opposite — an estimate of how fast the current tyres are going off **right now**,
updated every lap, with honest uncertainty, and able to react when degradation
accelerates (the "cliff") rather than assuming one constant slope.

This is a textbook local-linear-trend state-space model:

    state  x_t = [level_t, slope_t]         level = pace offset vs fresh (s)
                                             slope = per-lap degradation (s/lap)
    x_{t+1} = F x_t + w,   F = [[1, 1],      (level advances by the slope each lap)
                                [0, 1]]
    z_t     = H x_t + v,   H = [1, 0]        (we observe the pace offset, noisily)

with process noise ``Q`` (mostly on the slope, letting it drift so the filter can
track a changing degradation rate) and measurement noise ``R`` (the Phase 2
lap-time noise variance). The Kalman recursion returns, after each lap, the
posterior mean and covariance of (level, slope) — so ``slope`` and its standard
deviation are available mid-stint and tighten as laps accumulate.

Pure numpy; no new dependency. Nothing here replaces the batch model — it is the
online counterpart the retrospective pipeline cannot provide.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_F = np.array([[1.0, 1.0], [0.0, 1.0]])
_H = np.array([[1.0, 0.0]])


@dataclass(frozen=True)
class KalmanState:
    """Posterior over [level, slope] after one lap."""

    mean: np.ndarray  # shape (2,)
    cov: np.ndarray   # shape (2, 2)

    @property
    def level(self) -> float:
        return float(self.mean[0])

    @property
    def slope(self) -> float:
        return float(self.mean[1])

    @property
    def slope_sd(self) -> float:
        return float(np.sqrt(self.cov[1, 1]))

    @property
    def level_sd(self) -> float:
        return float(np.sqrt(self.cov[0, 0]))


class DegradationKalman:
    """Local-linear-trend Kalman filter for online degradation tracking."""

    def __init__(
        self,
        meas_var: float,
        slope_process_var: float = 1e-4,
        level_process_var: float = 0.0,
        init_level: float = 0.0,
        init_slope: float = 0.0,
        init_var: float = 100.0,
    ) -> None:
        if meas_var <= 0:
            raise ValueError("meas_var must be positive")
        if slope_process_var < 0 or level_process_var < 0:
            raise ValueError("process variances must be non-negative")
        self._R = float(meas_var)
        self._Q = np.array([[level_process_var, 0.0], [0.0, slope_process_var]])
        self.mean = np.array([init_level, init_slope], dtype=float)
        # Diffuse prior: large initial covariance so early laps dominate.
        self.cov = np.diag([init_var, init_var]).astype(float)

    def state(self) -> KalmanState:
        return KalmanState(mean=self.mean.copy(), cov=self.cov.copy())

    def step(self, z: float) -> KalmanState:
        """Advance one lap: predict, then correct with observation ``z``."""
        # Predict
        mean = _F @ self.mean
        cov = _F @ self.cov @ _F.T + self._Q
        # Update (scalar observation, so the "S inverse" is a plain divide).
        # H = [1, 0], so H @ mean is just the level component.
        y = float(z) - float(mean[0])
        s = float(cov[0, 0]) + self._R
        k = cov[:, 0] / s  # Kalman gain = P H^T / S, shape (2,)
        self.mean = mean + k * y
        self.cov = (np.eye(2) - np.outer(k, _H.ravel())) @ cov
        return self.state()


def filter_stint(
    pace_offsets: np.ndarray,
    meas_var: float,
    slope_process_var: float = 1e-4,
    **kwargs: float,
) -> list[KalmanState]:
    """Run the filter over one stint's per-lap pace offsets (s vs fresh tyre),
    returning the posterior state after each lap. The slope estimate at the
    final lap is the online analogue of the OLS within-stint degradation slope,
    but it is available — with its uncertainty — from the very first laps."""
    kf = DegradationKalman(meas_var, slope_process_var=slope_process_var, **kwargs)
    return [kf.step(float(z)) for z in np.asarray(pace_offsets, dtype=float)]
