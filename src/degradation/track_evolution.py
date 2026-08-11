"""Race-time (track-evolution) basis for the endurance degradation fit.

Why this exists
---------------
The endurance model absorbs each car-driver's *level* with a fixed effect and
carries no term for race time. Track evolution — a circuit drying, rubbering
in, or cooling over a race — therefore lands on the tyre-age coefficient, and
lands there with its sign inverted: inside any stint, later laps are on older
tyres *and* on a changed track. At ELMS Portimao 2023 the track improves by
17.8 s a lap and the model returns -0.213 s/lap for a tyre that is wearing.
Diagnosis and evidence: ``reports/track_evolution_omitted_variable.md``.

Why it is conditional
---------------------
A piecewise-linear basis in lap number recovers a known +0.080 s/lap slope as
+0.081 on synthetic races with an 18 s non-linear drying curve, where the
uncorrected model returns **-0.075** — the wrong sign. But on a race with too
few stints it returns **-3.88**, catastrophically worse than the bug it fixes.

The cause is identifiability, not sample size. When a car-driver unit covers
essentially one stint, tyre age *is* race time after the fixed effects are
absorbed, and the basis simply eats the degradation. :func:`identifiability`
measures that directly — the multiple correlation of tyre age on the time
basis, both residualised on the fixed effects. It reads 1.000 in the
degenerate case and 0.18-0.66 where the correction works.

So the term is applied where it is identified and refused where it is not,
and which of the two happened is recorded per race rather than inferred.

**This module is not wired into the model, and the reason is a measurement.**
Wiring it and refitting all 210 scoped race-seasons made the results *worse*:
negative slopes went 41 -> 64, physically impossible ones 3 -> 5, and the ELMS
median crossed from +0.019 to -0.007. The synthetic validation above had said
the opposite.

The gap between the two is the useful part. Median identifiability on real
races is **0.585**, against 0.18-0.39 in the synthetic races that validated
the approach — real fields sit far closer to the degenerate boundary than the
generator implied, so a 0.95 limit passes races the basis cannot actually
support. The synthetic test was too idealised and produced false confidence:
it modelled track evolution as the only confounder, on stint structures
cleaner than any real race has.

Kept rather than deleted because the diagnosis it rests on is solid and
independently evidenced (``reports/track_evolution_omitted_variable.md``): a
lap-number term moves exactly the races that drift and leaves the others
untouched to four decimals. What is missing is a basis that separates track
evolution from tyre age on *real* stint structures, and a validation harness
built from real races rather than an idealised generator. Anyone resuming this
should start by lowering IDENTIFIABILITY_LIMIT until the real-data refit stops
degrading, and treat that threshold as the finding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Number of piecewise-linear segments in the race-time basis. Six is enough
#: to follow a drying curve that is steep early and flat late; more segments
#: buy nothing measurable and cost identifiability.
N_SEGMENTS = 6

#: Refuse the track term at or above this correlation. At 1.0 tyre age and
#: race time are the same variable after fixed effects; 0.95 leaves a margin
#: without excluding the 0.66 cases where the correction demonstrably works.
IDENTIFIABILITY_LIMIT = 0.95


def basis(lap: np.ndarray, n_segments: int = N_SEGMENTS) -> np.ndarray:
    """Piecewise-linear basis in lap number, knots at equally-spaced quantiles.

    Linear rather than cubic on purpose: a spline that can curve sharply can
    also curve to fit a stint, and this basis has to describe the track, not
    the tyre.
    """
    lap = np.asarray(lap, dtype=float)
    knots = np.quantile(lap, np.linspace(0.0, 1.0, n_segments + 1)[1:-1])
    return np.column_stack([lap] + [np.clip(lap - k, 0.0, None) for k in knots])


def _residualise(fe: np.ndarray, v: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(fe, v, rcond=None)
    return v - fe @ beta


def identifiability(fe: np.ndarray, tyre_age: np.ndarray, lap: np.ndarray) -> float:
    """Multiple correlation of tyre age on the race-time basis, after the
    fixed effects are absorbed from both.

    1.0 means the two carry the same information and the degradation slope
    cannot be separated from track evolution at all. Returns 1.0 defensively
    if the residualised tyre age is degenerate, so a caller that trusts the
    limit never proceeds on a fit it cannot support.
    """
    age_r = _residualise(fe, np.asarray(tyre_age, dtype=float))
    denom = float(age_r @ age_r)
    if denom <= 1e-12:
        return 1.0
    b = basis(lap)
    b_r = np.column_stack([_residualise(fe, b[:, j]) for j in range(b.shape[1])])
    proj = b_r @ np.linalg.pinv(b_r.T @ b_r) @ b_r.T @ age_r
    return float(np.sqrt(max(float(proj @ proj), 0.0) / denom))


def design(
    fe: np.ndarray, tyre_age: np.ndarray, lap: np.ndarray
) -> tuple[np.ndarray, bool, float]:
    """``(design_matrix, applied, identifiability)`` for one race.

    The tyre-age column is always at index ``fe.shape[1]`` so callers read the
    slope from the same place whether or not the track term was added.
    """
    r = identifiability(fe, tyre_age, lap)
    age = np.asarray(tyre_age, dtype=float)[:, None]
    if r >= IDENTIFIABILITY_LIMIT:
        return np.hstack([fe, age]), False, r
    return np.hstack([fe, age, basis(lap)]), True, r
