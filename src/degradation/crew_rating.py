"""Does an amateur-rated driver wear tyres faster? Measured, per championship.

Both IMSA and ELMS run **the same car in two classes that differ only in
whether an amateur-rated driver is mandatory** — IMSA's GTD (Pro/Am) against
GTD PRO (all-professional) under one Balance of Performance, ELMS's LMP2
Pro/Am against LMP2 on a near-spec Oreca 07. The class boundary *is* the crew
rating, so the effect is measurable without any external driver-rating data.
That is the whole reason both classes were scoped separately rather than
pooled into "GT3" and "LMP2".

This module exists because the result did not have any. The comparison was
first run by hand, written into two reports and quoted in the README as a
headline finding — and then the slopes underneath it changed, twice, when the
traffic trim and the field-wide hysteresis filter were fixed. Nothing
recomputed it and no test could, so the published numbers drifted away from
the artifacts in silence and the *significance* of the ELMS result did not
survive the correction. A finding with no code behind it cannot go stale; it
can only become quietly wrong.

Method, and why each choice:

- **Paired**, one pair per race where both classes ran. The two classes share
  the track, the weather, the tyre allocation and the race distance, so
  pairing removes every confounder that varies between races — which is most
  of them, and is exactly what the leave-one-race-out result says fails to
  transfer between seasons.
- Pairs are keyed on ``(event, season)``, the race identity, **never on the
  circuit**. IMSA ran two distinct races at Watkins Glen in 2021, and keying
  on the circuit silently averages them into one.
- **Wilcoxon signed-rank**, not a paired t-test. The slope distribution has
  heavy negative outliers from the unmodelled track-evolution term (ELMS
  Portimao 2023 fits −0.298 s/lap), and a mean-based test would let those
  outliers drive the answer.
- ELMS is restricted from ``first_season`` on: before 2023 the ``LMP2`` label
  covers every entry rather than the professional subset, so an unrestricted
  pairing would compare a mixed field against a Pro/Am one and call the
  difference a crew effect.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy.stats import binomtest, wilcoxon


@dataclass(frozen=True)
class CrewPair:
    """One championship's professional class and its Pro/Am counterpart."""

    series: str
    pro_class: str
    proam_class: str
    first_season: int
    #: Why the season floor is where it is — carried into the report, so the
    #: restriction is never silently dropped when the scope widens.
    restriction: str


#: The two natural experiments this project has. Not a list to grow casually:
#: a pair only belongs here if the classes race the same car under the same
#: technical rules and differ *only* in mandated crew rating.
CREW_PAIRS: tuple[CrewPair, ...] = (
    CrewPair(
        "imsa", pro_class="GTDPRO", proam_class="GTD", first_season=2022,
        restriction="GTD PRO was created in 2022; GTD's 2021 races have no counterpart.",
    ),
    CrewPair(
        "elms", pro_class="LMP2", proam_class="LMP2 Pro/Am", first_season=2023,
        restriction="Before 2023 the LMP2 label covers every entry, not the professional subset.",
    ),
)


@dataclass(frozen=True)
class CrewComparison:
    """The paired test for one championship."""

    series: str
    pro_class: str
    proam_class: str
    n_pairs: int
    #: Pro/Am minus professional, so a **positive** value means the amateur
    #: crews degrade faster — the hypothesis under test.
    median_difference_s: float
    proam_steeper: int
    p_value: float
    pro_median_slope: float
    proam_median_slope: float
    first_season: int
    last_season: int

    @property
    def significant(self) -> bool:
        """At the conventional 5%. Reported, never used to decide what to say."""
        return self.p_value < 0.05

    @property
    def direction(self) -> str:
        return "Pro/Am steeper" if self.median_difference_s > 0 else "professional steeper"


def _pairs(fits: pd.DataFrame, pair: CrewPair) -> pd.DataFrame:
    """The races where both classes ran, one row per race.

    Returned rather than reduced so callers can inspect which races paired —
    the count alone hides an accidental narrowing of the scope.
    """
    scoped = fits[(fits["series"] == pair.series) & (fits["season"] >= pair.first_season)]
    wide = scoped.pivot_table(
        index=["event", "season"],
        columns="car_class",
        values="net_slope",
        # Refuse to average: two rows for one (event, season, class) would mean
        # the race identity assumption has broken, and a silent mean would hide
        # it. ``pivot_table`` defaults to mean, which is the trap.
        aggfunc="first",
    )
    for car_class in (pair.pro_class, pair.proam_class):
        if car_class not in wide.columns:
            return wide.iloc[:0]
    return wide[[pair.pro_class, pair.proam_class]].dropna()


def compare_crew_ratings(fits: pd.DataFrame) -> list[CrewComparison]:
    """Run the paired test for every championship that has both classes.

    ``fits`` is ``endurance_degradation_fits.csv``: one row per race-season and
    class, carrying ``net_slope``.
    """
    out: list[CrewComparison] = []
    for pair in CREW_PAIRS:
        matched = _pairs(fits, pair)
        if len(matched) < 2:
            continue
        difference = matched[pair.proam_class] - matched[pair.pro_class]
        out.append(
            CrewComparison(
                series=pair.series,
                pro_class=pair.pro_class,
                proam_class=pair.proam_class,
                n_pairs=len(difference),
                median_difference_s=float(difference.median()),
                proam_steeper=int((difference > 0).sum()),
                p_value=float(wilcoxon(difference).pvalue),
                pro_median_slope=float(matched[pair.pro_class].median()),
                proam_median_slope=float(matched[pair.proam_class].median()),
                first_season=int(matched.index.get_level_values("season").min()),
                last_season=int(matched.index.get_level_values("season").max()),
            )
        )
    return out


# --- fragility, as a measured property rather than a caveat ------------------


@dataclass(frozen=True)
class Variant:
    """One defensible analytic choice, and what the test says under it."""

    label: str
    why: str
    n_pairs: int
    median_difference_s: float
    p_value: float


def robustness(fits: pd.DataFrame, pair: CrewPair) -> list[Variant]:
    """Re-run the test under every reasonable perturbation of the choices.

    A borderline p-value is only worth reporting alongside this. IMSA's
    headline test lands at p = 0.032, and each of these variants — none of
    them a strawman, each defensible enough that a careful analyst might have
    picked it first — puts it back above 0.05. That is a statement about
    statistical power, not about an effect, and the reports say so because
    this function makes it checkable.
    """
    matched = _pairs(fits, pair)
    difference = matched[pair.proam_class] - matched[pair.pro_class]
    seasons = matched.index.get_level_values("season")
    both_positive = (matched[pair.pro_class] > 0) & (matched[pair.proam_class] > 0)

    subsets = [
        (
            "sign test",
            "drops the magnitudes and keeps only the direction, so no single "
            "large pair can carry the result",
            difference,
            float(binomtest(int((difference > 0).sum()), len(difference)).pvalue),
        ),
        (
            "latest season dropped",
            "a result that rests on its most recent season is not a result; "
            "for IMSA that season is also still in progress, so its races are "
            "not a random sample of it",
            difference[seasons < seasons.max()],
            None,
        ),
        (
            "both slopes positive",
            "excludes races hit by the unmodelled track-evolution term, whose "
            "negative slopes are a known model defect rather than a measurement",
            difference[both_positive],
            None,
        ),
    ]

    out: list[Variant] = []
    for label, why, subset, p_override in subsets:
        if len(subset) < 2:
            continue
        out.append(
            Variant(
                label=label,
                why=why,
                n_pairs=len(subset),
                median_difference_s=float(subset.median()),
                p_value=p_override if p_override is not None
                else float(wilcoxon(subset).pvalue),
            )
        )
    return out
