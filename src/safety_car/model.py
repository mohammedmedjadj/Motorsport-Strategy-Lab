"""Bayesian occurrence and rate models for SC/VSC deployments.

With at most 8 editions per circuit, frequentist point estimates would be
noise dressed up as precision. Everything here returns a posterior mean
plus a 95% equal-tailed credible interval under a Jeffreys prior:

- **Occurrence** (did the race contain at least one SC?): Binomial with a
  Beta(1/2, 1/2) prior -> Beta posterior.
- **Per-lap deployment rate** (deployments per green race lap, feeding the
  Phase 4 per-lap hazard): Poisson counts over lap exposure with a
  Gamma(1/2, ~0) prior -> Gamma posterior.

The Jeffreys prior is the standard objective choice for small samples; it
is proper here and adds the equivalent of half an observation, keeping
zero-event circuits away from the dishonest estimate "probability = 0".
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy import stats


@dataclass(frozen=True)
class PosteriorEstimate:
    """Posterior mean with a 95% equal-tailed credible interval."""

    mean: float
    ci_low: float
    ci_high: float
    n_observations: int

    def fmt(self, digits: int = 3) -> str:
        return (
            f"{self.mean:.{digits}f} "
            f"[{self.ci_low:.{digits}f}, {self.ci_high:.{digits}f}]"
        )


def occurrence_probability(k_races_with_event: int, n_races: int) -> PosteriorEstimate:
    """P(a race at this circuit contains >= 1 event), Beta-Binomial."""
    if n_races <= 0:
        raise ValueError("n_races must be positive")
    if not 0 <= k_races_with_event <= n_races:
        raise ValueError("k must be between 0 and n_races")
    alpha = k_races_with_event + 0.5
    beta = n_races - k_races_with_event + 0.5
    dist = stats.beta(alpha, beta)
    return PosteriorEstimate(
        mean=float(alpha / (alpha + beta)),
        ci_low=float(dist.ppf(0.025)),
        ci_high=float(dist.ppf(0.975)),
        n_observations=n_races,
    )


def per_lap_rate(k_deployments: int, n_laps_exposure: int) -> PosteriorEstimate:
    """Deployments per race lap, Gamma-Poisson (Jeffreys prior)."""
    if n_laps_exposure <= 0:
        raise ValueError("exposure must be positive")
    if k_deployments < 0:
        raise ValueError("deployments cannot be negative")
    alpha = k_deployments + 0.5
    dist = stats.gamma(a=alpha, scale=1.0 / n_laps_exposure)
    return PosteriorEstimate(
        mean=float(alpha / n_laps_exposure),
        ci_low=float(dist.ppf(0.025)),
        ci_high=float(dist.ppf(0.975)),
        n_observations=n_laps_exposure,
    )


def duration_summary(durations_laps: list[int]) -> dict[str, float]:
    """Descriptive summary of event durations (laps). Small n — no model."""
    if not durations_laps:
        return {"n": 0, "mean": float("nan"), "min": float("nan"), "max": float("nan")}
    return {
        "n": len(durations_laps),
        "mean": sum(durations_laps) / len(durations_laps),
        "min": min(durations_laps),
        "max": max(durations_laps),
    }
