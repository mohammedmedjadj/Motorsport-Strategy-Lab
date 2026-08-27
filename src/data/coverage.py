"""Which modelling layers actually cover which races — measured, not assumed.

This module exists because "the work is uneven" was a true statement nobody
could check. Every layer of this project writes its own artifact with its own
key columns, so asking "does the multi-stop planner cover every race the
degradation model fits?" meant loading two CSVs by hand and hoping you got the
join right. Nobody did that routinely, and the answer turned out to be **no**:

- The **multi-stop plan** — the layer that produces this project's headline
  strategy conclusion — covered **65 of 209** modelled race-seasons. One
  arbitrary season per circuit-class, justified in a comment on the grounds
  that "fuel range and stop structure are circuit properties". Fuel range is;
  the degradation slope is not, and the plan trades tyre loss against pit loss.
  This project's own most-cited result is that slopes fail to transfer between
  seasons, so a plan fitted on one season is not a property of the circuit.
- **Traffic cost** and **pit-loss transfer** carry no ``car_class`` at all, so
  they describe the prime class and are silently read as describing the field.

None of that was hidden. It was written down in comments, in three separate
files, and no single place put the numbers side by side.

The rule this encodes: **a layer either covers the whole scope, or it declares
the granularity at which it does not.** A layer that quietly covers a third of
the scope while its output is quoted as a fact about the project is the failure
mode here, and it is now a test rather than a reading exercise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.ingestion.config import ENDURANCE_DERIVED_DIR

#: What a layer is expected to cover.
#:
#: ``race-season`` — one row per race that was actually run. The default, and
#:   what any layer whose output depends on a *fitted* quantity must be.
#: ``circuit-class`` — one row per (series, class, circuit). Legitimate only
#:   for quantities that are genuinely properties of the track, measured across
#:   its seasons rather than within one of them.
#: ``class`` — one row per (series, class). For procedural constants like the
#:   tyre-change premium, which is a property of how a team services a car.
Granularity = Literal["race-season", "circuit-class", "class"]


@dataclass(frozen=True)
class Layer:
    """One modelling layer and the artifact it writes."""

    name: str
    artifact: str
    granularity: Granularity
    #: Why this granularity is the right one. Recorded because the multi-stop
    #: layer had a plausible-sounding justification for the wrong one, and the
    #: only way to catch that is to make the reasoning visible next to the fact.
    rationale: str
    #: Column carrying the class, if any. ``None`` means the layer does not
    #: distinguish classes — which is itself a coverage statement.
    class_column: str | None = "car_class"
    circuit_column: str = "circuit_canonical"
    year_column: str | None = "year"


#: Every endurance layer, in pipeline order.
ENDURANCE_LAYERS: tuple[Layer, ...] = (
    Layer(
        "data quality", "endurance_data_quality.csv", "race-season",
        "Lap accounting is per race by construction.",
        year_column="season",
    ),
    Layer(
        "degradation", "endurance_degradation_fits.csv", "race-season",
        "A slope is fitted from one race's laps and does not transfer between "
        "seasons — that is this project's central measured result.",
        year_column="season",
    ),
    Layer(
        "multi-stop plan", "multistop_plans.csv", "race-season",
        "The plan trades this race's fitted degradation slope against pit "
        "loss, so it inherits the slope's per-race variability.",
    ),
    Layer(
        "fuel-limited audit", "fuel_limited_audit.csv", "race-season",
        "Reconstructed from one race's real winning stints.",
        circuit_column="circuit",
    ),
    Layer(
        "traffic cost", "endurance_traffic_cost.csv", "race-season",
        "Measured from one race's multi-class field crossings.",
        class_column=None, circuit_column="circuit",
    ),
    Layer(
        "overtaking difficulty", "endurance_overtaking_difficulty.csv",
        "circuit-class",
        "Position stickiness is a property of track geometry, pooled across "
        "a circuit's seasons on purpose and reported with its spread.",
        circuit_column="circuit", year_column=None,
    ),
    Layer(
        "traffic stability", "endurance_traffic_stability.csv", "circuit-class",
        "The point of this artifact is the season-to-season spread, so it "
        "aggregates seasons by design.",
        class_column=None, circuit_column="circuit", year_column=None,
    ),
    Layer(
        "pit procedure", "endurance_pit_procedure.csv", "class",
        "The tyre-change premium is a property of how a class is serviced, "
        "not of a track.",
        circuit_column="", year_column=None,
    ),
)


def scope_frame() -> pd.DataFrame:
    """The modelled scope: one row per race-season that has a fitted model.

    Taken from the degradation fits rather than from ``ENDURANCE_SCOPE``,
    deliberately. The scope says what *should* be modelled; the fits say what
    is. Measuring coverage against the fits answers the question actually
    being asked — is every race this project claims to model carried through
    every layer — without conflating it with ingestion gaps, which are the
    data-quality report's subject.
    """
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    return fits[["series", "car_class", "circuit_canonical", "season"]].rename(
        columns={"season": "year"}
    )


def _keys(frame: pd.DataFrame, layer: Layer) -> set[tuple]:
    """The identities a layer's artifact actually carries."""
    columns = [c for c in (
        "series",
        layer.class_column,
        layer.circuit_column or None,
        layer.year_column,
    ) if c]
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise KeyError(f"{layer.artifact} lacks {missing}; it carries {list(frame.columns)}")
    return set(map(tuple, frame[columns].drop_duplicates().to_numpy()))


def expected_keys(scope: pd.DataFrame, layer: Layer) -> set[tuple]:
    """What the layer's granularity says it should carry."""
    columns = ["series"]
    if layer.class_column:
        columns.append("car_class")
    if layer.circuit_column:
        columns.append("circuit_canonical")
    if layer.year_column:
        columns.append("year")
    return set(map(tuple, scope[columns].drop_duplicates().to_numpy()))


@dataclass(frozen=True)
class Coverage:
    layer: Layer
    covered: int
    expected: int
    missing: tuple[tuple, ...]

    @property
    def share(self) -> float:
        return self.covered / self.expected if self.expected else 1.0

    @property
    def complete(self) -> bool:
        return not self.missing


def measure(layers: tuple[Layer, ...] = ENDURANCE_LAYERS) -> list[Coverage]:
    """Coverage of every layer against the modelled scope.

    Circuit keys are slugified on **both** sides before comparison, because the
    artifacts do not agree on a convention: ``circuit_canonical`` holds
    ``"Barcelona"`` in ``endurance_degradation_fits.csv`` and ``"barcelona"`` in
    ``multistop_plans.csv``. Same column name, two formats, and a consumer
    joining on it gets an empty frame rather than an error. Normalising here
    means this module measures coverage rather than measuring that bug —
    ``tests/test_artifact_keys.py`` is what measures the bug.
    """
    from src.data.endurance_loader import slugify

    scope = scope_frame()
    scope["circuit_canonical"] = scope["circuit_canonical"].map(slugify)

    out: list[Coverage] = []
    for layer in layers:
        frame = pd.read_csv(ENDURANCE_DERIVED_DIR / layer.artifact)
        probe = layer
        if layer.circuit_column == "circuit":
            # Drop any existing canonical column first: several artifacts carry
            # both, and renaming onto an occupied name yields two columns with
            # the same label, after which `frame[name]` is a DataFrame and every
            # downstream operation silently does the wrong thing.
            frame = frame.drop(columns=["circuit_canonical"], errors="ignore").rename(
                columns={"circuit": "circuit_canonical"}
            )
            probe = Layer(**{**probe.__dict__, "circuit_column": "circuit_canonical"})
        if layer.circuit_column:
            frame["circuit_canonical"] = frame["circuit_canonical"].map(slugify)
        if layer.year_column == "season":
            frame = frame.rename(columns={"season": "year"})
            probe = Layer(**{**probe.__dict__, "year_column": "year"})

        have = _keys(frame, probe)
        want = expected_keys(scope, probe)
        out.append(
            Coverage(
                layer=layer,
                covered=len(want & have),
                expected=len(want),
                missing=tuple(sorted(want - have)),
            )
        )
    return out


def report(coverages: list[Coverage]) -> str:
    """A table a human can read, and a report can quote."""
    width = max(len(c.layer.name) for c in coverages)
    lines = [f"{'layer':<{width}}  {'granularity':<14}  covered  expected  share",
             "-" * (width + 45)]
    for c in coverages:
        lines.append(
            f"{c.layer.name:<{width}}  {c.layer.granularity:<14}  "
            f"{c.covered:7d}  {c.expected:8d}  {c.share:5.0%}"
            + ("" if c.complete else "  <-- INCOMPLETE")
        )
    return "\n".join(lines)
