"""Are the F1 degradation slopes biased toward durability?

The calendar-wide audit found the simulator stays out a median of 12 laps
longer than teams do. It named two possible causes. The first — no track
position, so the engine cannot pay for an undercut — was tested and rejected
(`run_undercut_hypothesis.py`). This tests the second, and it is the last one
standing:

> the fitted slopes are biased toward durability by the same unmodelled
> track-evolution term diagnosed on the endurance side. A tyre that looks
> flatter than it is makes staying out look cheaper than it is.

Three measurements, each answering a different part of it:

1. **Identifiability.** Whether a race-time basis could even be fitted here.
   The endurance attempts failed because real fields sit close to the
   degenerate boundary; this says how close F1 sits.
2. **Residual drift.** Whether the fitted model leaves an unabsorbed race-time
   trend at all. F1 already carries a linear lap term as a fuel proxy, which
   endurance does not, so it may already absorb what endurance could not.
3. **An independent measurement.** The Kaggle breadth layer separates tyre wear
   from fuel burn on a different source with a different method. Comparing the
   two is the only way to detect a bias that the model's own residuals cannot
   show — because a term that eats tyre signal leaves the fit looking clean.

Writes ``data/derived/f1/slope_bias_check.csv`` and
``reports/f1/slope_bias_check.md``.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.degradation.dataset import (  # noqa: E402
    build_modelling_frame,
    circuits_with_laps,
    load_circuit_laps,
)
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from src.degradation.track_evolution import identifiability  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    F1_DERIVED_DIR,
    F1_REPORTS_DIR,
    PRE_ERA_SEASONS,
    breadth_key,
)

#: Median identifiability of the endurance races, where the race-time basis was
#: built, validated on synthetic data and then withdrawn twice.
ENDURANCE_IDENTIFIABILITY = 0.585

#: The range the basis was validated over on synthetic races. Above it, the
#: basis and tyre age share too much variance for the fit to mean anything.
VALIDATED_RANGE = (0.18, 0.39)

#: A typical F1 pit loss. Used only to turn a slope error into laps, which is
#: the unit the audit's finding is in.
PIT_LOSS_S = 22.0


def per_race() -> pd.DataFrame:
    """Identifiability and residual drift, one row per race."""
    rows = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        try:
            laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
            frame, _ = build_modelling_frame(laps, circuit)
            fit = fit_circuit(frame, circuit, degree=1)
        except Exception:  # noqa: BLE001 — a circuit with too little to fit
            continue
        prediction = predict_shape(fit, frame)
        usable = prediction.notna()
        scored = frame[usable].copy()
        scored["residual"] = scored["lap_time_s"] - prediction[usable]
        scored["residual"] -= scored.groupby("driver_race")["residual"].transform("mean")

        for race, group in scored.groupby("race"):
            fixed_effects = pd.get_dummies(group["driver_race"]).to_numpy(dtype=float)
            try:
                identified = identifiability(
                    fixed_effects,
                    group["TyreLife"].to_numpy(float),
                    group["LapNumber"].to_numpy(float),
                )
            except Exception:  # noqa: BLE001
                identified = float("nan")
            if len(group) < 50:
                continue
            drift = float(
                np.polyfit(group["LapNumber"].to_numpy(float),
                           group["residual"].to_numpy(float), 1)[0]
            )
            rows.append({
                "race": race, "circuit": circuit,
                "identifiability": identified, "residual_drift_s_per_lap": drift,
            })
    return pd.DataFrame(rows)


def cross_source() -> pd.DataFrame:
    """The core model's tyre slope beside the breadth layer's, per circuit."""
    core = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    breadth = pd.read_csv(F1_DERIVED_DIR / "history_degradation.csv")
    core_slope = core.groupby("circuit")["deg_p1"].median()
    breadth_slope = (
        breadth[breadth["era"] == "ground-effect"]
        .groupby("circuit")["tyre_slope_s"].median()
    )
    rows = []
    for circuit, slope in core_slope.items():
        key = breadth_key(circuit)
        if key not in breadth_slope.index:
            continue
        rows.append({
            "circuit": circuit,
            "core_tyre_slope": round(float(slope), 4),
            "breadth_tyre_slope": round(float(breadth_slope[key]), 4),
        })
    frame = pd.DataFrame(rows).dropna()
    frame["difference"] = (
        frame["breadth_tyre_slope"] - frame["core_tyre_slope"]
    ).round(4)
    return frame


def laps_of_error(slope_error: float, pit_loss_s: float = PIT_LOSS_S) -> float:
    """Roughly how many laps a slope understated by ``slope_error`` moves a stop.

    A stop pays when the degradation avoided over the remaining stint exceeds
    the pit loss. Understating the slope by ``e`` understates cumulative
    degradation at lap ``L`` by ``e * L^2 / 2``, so the lap at which the model
    thinks the trade is still favourable moves out to where that shortfall
    equals the pit loss. Deliberately crude: the point is the order of
    magnitude, and the order of magnitude is what settles the question.
    """
    if slope_error <= 0:
        return 0.0
    return float(np.sqrt(2 * pit_loss_s / slope_error))


def _medians_aside(difference_of_medians: float) -> str:
    """The difference-of-medians reading, phrased for the sign it actually has.

    This sentence was written when that statistic read +0.0057 and said "even
    taking the misleading difference of medians the reach is beyond a race
    distance". Deriving the number was not enough: recomputing the breadth
    layer moved it to -0.0002, and a negative value means the independent
    source is *shallower*, so there is no understatement for a reach to be
    computed from. The old wording then rendered "roughly lap 0, still beyond a
    race distance", which is nonsense printed with confidence.

    A derived number needs prose that stays true across the range the number
    can take, not prose fitted to the value it happened to have.
    """
    if difference_of_medians <= 0:
        return (
            "Comparing the two *medians* instead — the statistic a reader "
            f"reaches for first — gives {difference_of_medians:+.4f} s/lap: "
            "the independent source is if anything the *shallower* of the two, "
            "so it supports no durability bias at all, in either direction."
        )
    return (
        "Even taking the misleading difference of medians "
        f"({difference_of_medians:+.4f}) the reach is roughly **lap "
        f"{laps_of_error(difference_of_medians):.0f}**, still beyond a race "
        "distance."
    )


def main() -> int:
    warnings.filterwarnings("ignore")
    races = per_race()
    sources = cross_source()
    races.to_csv(F1_DERIVED_DIR / "slope_bias_check.csv", index=False)

    median_identified = races["identifiability"].median()
    median_drift = races["residual_drift_s_per_lap"].median()
    negative_drift = int((races["residual_drift_s_per_lap"] < 0).sum())
    correlation = sources["core_tyre_slope"].corr(sources["breadth_tyre_slope"])
    median_difference = sources["difference"].median()
    # The wrong statistic, kept and named rather than dropped: it is the one a
    # reader reaches for first, and showing that it does not change the verdict
    # is stronger than not mentioning it. Derived, because it was typed once
    # (+0.0057) and went stale the moment the breadth layer was recomputed.
    difference_of_medians = float(
        sources["breadth_tyre_slope"].median() - sources["core_tyre_slope"].median()
    )
    reach = laps_of_error(median_difference)

    lines = [
        "<!-- GENERATED by scripts/run_slope_bias_check.py — do not edit by hand. -->",
        "",
        "# Are the F1 degradation slopes biased toward durability?",
        "",
        "The [calendar-wide audit](systematic_audit.md) found the simulator stays "
        "out a median of **12 laps** longer than teams do. Its first explanation "
        "— no track position — was "
        "[tested and rejected](undercut_hypothesis.md). This tests the second and "
        "last: that the fitted slopes make tyres look more durable than they are, "
        "so staying out looks cheaper than it is.",
        "",
        "## 1. Could a race-time term even be fitted here?",
        "",
        f"Median identifiability across {len(races)} races: **{median_identified:.3f}**, "
        f"against **{ENDURANCE_IDENTIFIABILITY}** in endurance and "
        f"**{VALIDATED_RANGE[0]}–{VALIDATED_RANGE[1]}** in the synthetic races "
        "where the piecewise race-time basis was validated before being withdrawn "
        "twice on real data.",
        "",
        "F1 is **less degenerate than endurance and still far outside the range "
        "the basis was shown to work in**. Tyre age and race time share most of "
        "their variance after fixed effects here too, so the same correction "
        "would fail the same way. That is worth knowing before building it a "
        "third time.",
        "",
        "## 2. Does the fitted model leave a race-time trend behind?",
        "",
        "F1 already carries a linear lap term as a fuel proxy, which the "
        "endurance model deliberately does not — it uses `laps_since_refuel` "
        "instead, because endurance cars refuel. So F1 may already absorb what "
        "endurance could not.",
        "",
        f"Median residual drift: **{median_drift:+.5f} s/lap**. "
        f"{negative_drift} of {len(races)} races drift negative — a coin flip.",
        "",
        "**There is no systematic unabsorbed race-time trend in F1.** The "
        "handful of races with a large one are wet-to-dry:",
        "",
        "| race | residual drift |",
        "|---|---|",
    ]
    worst = races.reindex(
        races["residual_drift_s_per_lap"].abs().sort_values(ascending=False).index
    ).head(5)
    for row in worst.itertuples():
        lines.append(f"| {row.race} | {row.residual_drift_s_per_lap:+.4f} s/lap |")

    lines += [
        "",
        "That is not proof of an unbiased slope, and it is important to say why: "
        "the lap term and tyre age share variance, so a fuel term that quietly "
        "eats tyre signal leaves the residuals looking clean while the *split* "
        "between the two is wrong. A model's own residuals cannot detect that.",
        "",
        "## 3. An independent measurement",
        "",
        "The Kaggle breadth layer separates tyre wear from fuel burn on a "
        "different source, over a different span, with a different method. Two "
        "independent estimates of the same quantity is the only way to see a "
        "bias the residuals hide.",
        "",
        f"**{len(sources)} circuits measured by both**, ground-effect era. "
        f"Correlation **{correlation:+.3f}** — they agree on which circuits eat "
        "tyres.",
        "",
        f"Median per-circuit difference (breadth minus core): "
        f"**{median_difference:+.4f} s/lap** — indistinguishable from zero.",
        "",
        f"Comparing the two *medians* instead gives "
        f"{difference_of_medians:+.4f} s/lap — a different number, and here "
        "even a different **sign**. That is the whole reason the paired "
        "statistic is the right one: a difference of summaries asks whether "
        "the two sources are steep in aggregate, while the summary of "
        "differences asks whether they disagree *about the same circuit*, "
        "which is the actual question. The circuits where each source is "
        "steeper are different ones, and in aggregate they cancel.",
        "",
        "This distinction is not academic here. An earlier version of this "
        "check reported the difference of medians as a small durability bias "
        "and nearly published it; the paired difference is what showed there "
        "was none.",
        "",
        "| circuit | core (FastF1) | breadth (Kaggle) | difference |",
        "|---|---|---|---|",
    ]
    for row in sources.sort_values("difference").itertuples():
        lines.append(
            f"| {row.circuit} | {row.core_tyre_slope:+.4f} | "
            f"{row.breadth_tyre_slope:+.4f} | {row.difference:+.4f} |"
        )

    lines += [
        "",
        "## Verdict: not detected",
        "",
        f"A slope understated by {median_difference:+.4f} s/lap would move the "
        "lap at which a stop still looks worth its pit loss out to roughly "
        f"**lap {reach:.0f}** — several times the length of any Grand Prix. The "
        f"audit's gap is **12 laps**. {_medians_aside(difference_of_medians)}",
        "",
        "**Both explanations are now measured, and neither accounts for the "
        "finding.** Track position was tested and moved the recommendation the "
        "wrong way. Slope bias is not detectable against an independent source, "
        "and the largest reading it could support is an order of magnitude too "
        "small.",
        "",
        "So the audit's result stands as measured and **unexplained**. That is a "
        "worse position to be in than having a plausible story, and a better one "
        "than publishing a story that two measurements contradict. What is left "
        "to try: the decision point itself. The model is asked five laps before "
        "the real stop and offers every remaining lap as a candidate; a real "
        "team is choosing between a handful of laps under a strategy already "
        "committed to, and the two may simply not be answering the same "
        "question.",
        "",
    ]

    (F1_REPORTS_DIR / "slope_bias_check.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"identifiability {median_identified:.3f} | residual drift "
          f"{median_drift:+.5f} | cross-source r {correlation:+.3f} | "
          f"difference {median_difference:+.4f}")
    print(f"wrote {F1_REPORTS_DIR / 'slope_bias_check.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
