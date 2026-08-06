"""Interactive demo: a live pit-window simulator for all three series, using
the exact same measured models and simulator engines as the rest of this
project (no separate or simplified model built for the demo).

The three series are kept **strictly separate**, one panel each, because they
are not variants of one another:

- F1 has a tyre-compound choice and a sporting rule forcing two dry compounds;
  it has no fuel constraint (refuelling is banned).
- WEC has a fuel constraint and no compound choice, and its neutralisations are
  Safety-Car-dominated (44 SC vs 18 FCY events across its 33 committed races).
- IMSA has the same fuel constraint but a completely different neutralisation
  regime: 293 full-course yellows and *zero* Safety Cars across its 63
  committed races.

Merging them into one "endurance" panel would hide exactly the differences a
strategy engineer cares about, so nothing here pools them.

Run locally:

    pip install -r demo/requirements.txt
    streamlit run demo/app.py

Deploy: push this repo to a Hugging Face Space (Streamlit SDK) or Streamlit
Community Cloud, entry point ``demo/app.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.simulator.artifacts import CircuitModel, load_circuit_models
from src.simulator.endurance import EnduranceRaceModel, EnduranceScenario
from src.simulator.endurance import simulate as simulate_endurance
from src.simulator.endurance_models import (
    available_races,
    load_race_model,
    race_distance,
)
from src.simulator.engine import RivalSpec, Scenario, simulate
from src.simulator.multistop import (
    deterministic_time,
    evaluate_plan,
    min_stops_plan,
    optimal_stop_plan,
)

st.set_page_config(page_title="Motorsport Strategy Lab", page_icon="\U0001F3C1", layout="wide")

PURPLE, LILAC = "#7C3AED", "#B8A6E8"


@st.cache_resource
def _f1_models() -> dict[str, CircuitModel]:
    return load_circuit_models()


@st.cache_resource
def _endurance_model(series: str, year: int, event: str, car_class: str) -> EnduranceRaceModel:
    return load_race_model(series, year, event, car_class)


@st.cache_resource
def _endurance_distance(series: str, year: int, event: str, car_class: str) -> int:
    return race_distance(series, year, event, car_class)


@st.cache_data
def _races(series: str) -> pd.DataFrame:
    return available_races(series)


def _candidate_chart(
    labels: list[str], median: np.ndarray, p10: np.ndarray, p90: np.ndarray, title: str
) -> None:
    """Median with a [P10, P90] whisker per candidate — never a bare point
    estimate, since the whole argument of this project is that the spread is
    the decision-relevant part."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(labels))
    ax.errorbar(
        x, median, yerr=[median - p10, p90 - median],
        fmt="o", color=PURPLE, ecolor=LILAC, capsize=3,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("Total race time (s)")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)


# --------------------------------------------------------------------------
# Formula 1
# --------------------------------------------------------------------------

def f1_panel() -> None:
    st.subheader("Formula 1 — pit-window simulator")
    st.caption(
        "Same measured degradation, safety-car and pit-loss models as the "
        "committed F1 reports. Coefficients are fit on the regulation-stable "
        "seasons only; 2026 is held out as a transfer test, so nothing here "
        "pools across the rule change."
    )

    models = _f1_models()
    with st.sidebar:
        st.header("Race state")
        circuit = st.selectbox("Circuit", sorted(models), format_func=str.title)
        model = models[circuit]
        compounds = sorted(model.degradation)

        total_laps = st.slider("Race distance (laps)", 40, 80, 66)
        current_lap = st.slider("Current lap (decision point)", 1, total_laps - 5, 20)
        compound = st.selectbox("Current compound", compounds)
        tyre_age = st.slider("Tyre age (laps)", 0, 40, 12)

        # The engine optimises time and knows nothing about the sporting
        # regulations. In a dry race each car must use at least two different
        # dry-weather specifications, so until that is satisfied, "stay out to
        # the flag" and "stop for the same compound" are both disqualifications
        # rather than strategies -- and this demo used to recommend the first
        # of them by default.
        two_compounds_used = st.checkbox(
            "Two dry compounds already used", value=False,
            help=(
                "F1's sporting regulations require at least two different "
                "dry-weather compounds per car in a dry race. Until that is "
                "met, running to the flag is not a legal option and the new "
                "set must be a different compound."
            ),
        )
        legal_targets = compounds if two_compounds_used else [
            c for c in compounds if c != compound
        ]
        if not legal_targets:  # single-compound model: nothing to enforce
            legal_targets = compounds
        target_compound = st.selectbox("Compound if we stop", legal_targets)

        st.header("Rival (optional)")
        add_rival = st.checkbox("Add a rival to compare against", value=False)
        rival = None
        if add_rival:
            rival_gap = st.slider("Rival gap now (s, + = ahead of us)", -20.0, 20.0, 3.0)
            rival_compound = st.selectbox("Rival compound", compounds, key="rival_compound")
            rival_pits = st.checkbox("Rival stops at some point", value=False)
            rival_pit_lap = None
            if rival_pits:
                rival_pit_lap = st.slider(
                    "Rival's pit lap", current_lap + 1, total_laps - 3, current_lap + 5
                )
            rival = RivalSpec(
                name="Rival", gap_s=rival_gap, compound=rival_compound,
                tyre_age=tyre_age, pit_lap=rival_pit_lap,
            )

        n_draws = st.select_slider("Monte Carlo draws", [1000, 2000, 5000, 10000], value=5000)
        run = st.button("Simulate", type="primary", width="stretch")

    if not two_compounds_used:
        st.info(
            "**No-stop is excluded**: this car has not yet used two dry "
            "compounds, so running to the flag would be a disqualification, "
            "not a strategy. Tick the box in the sidebar for a car that has "
            "already met the requirement."
        )

    if not run:
        st.info(
            "Set the race state on the left and press **Simulate**. Every "
            "number below is a live re-run of the same Monte Carlo engine "
            "(`src/simulator/engine.py::simulate`) used to produce this "
            "project's committed reports — same measured coefficients, "
            "same common-random-numbers guarantee across candidates."
        )
        return

    scenario = Scenario(
        circuit=circuit,
        current_lap=current_lap,
        total_laps=total_laps,
        compound=compound,
        tyre_age=tyre_age,
        target_compound=target_compound,
        rivals=(rival,) if rival else (),
        include_no_stop=two_compounds_used,
    )

    with st.spinner("Running the Monte Carlo simulation..."):
        result = simulate(scenario, model, n_draws=n_draws)

    candidates = result.candidates
    median = np.median(result.our_time, axis=1)
    p10 = np.percentile(result.our_time, 10, axis=1)
    p90 = np.percentile(result.our_time, 90, axis=1)
    p_best = result.p_best

    labels = ["No stop" if c == 0 else f"Lap {c}" for c in candidates]
    best_idx = int(np.argmax(p_best))
    order = np.argsort([c if c else total_laps + 1 for c in candidates])

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**Total race time by candidate pit lap**")
        _candidate_chart(
            list(np.array(labels)[order]), median[order], p10[order], p90[order],
            f"{circuit.title()} — median ± [P10, P90], {n_draws} draws",
        )
    with col2:
        st.markdown("**Recommendation**")
        st.metric("P(best) pit lap", labels[best_idx], f"{p_best[best_idx]:.0%} P(best)")
        st.metric("Median time", f"{median[best_idx]:.1f}s")
        st.metric("P10-P90 range", f"{p10[best_idx]:.0f}-{p90[best_idx]:.0f}s")
        if rival:
            ahead = result.ahead_of_rival["Rival"][best_idx].mean()
            st.metric("P(ahead of rival)", f"{ahead:.0%}")

    st.markdown("**Every candidate**")
    table = pd.DataFrame({
        "Candidate": labels,
        "Median (s)": median.round(1),
        "P10 (s)": p10.round(1),
        "P90 (s)": p90.round(1),
        "P(best)": (p_best * 100).round(1),
    }).sort_values("P(best)", ascending=False)
    if rival:
        table["P(ahead of rival) %"] = (
            np.array([result.ahead_of_rival["Rival"][i].mean() for i in range(len(candidates))])
            * 100
        ).round(1)
    st.dataframe(table, width="stretch", hide_index=True)

    st.caption(
        "P(best) is a clean per-draw argmin across candidates sharing the same "
        "random realisations (common random numbers) — not an independent "
        "comparison of separately-simulated candidates. Coefficients are "
        "resampled per draw from their measured confidence intervals; nothing "
        "here is a fixed point estimate."
    )


# --------------------------------------------------------------------------
# Endurance (WEC and IMSA — same engine, deliberately separate panels)
# --------------------------------------------------------------------------

def endurance_panel(series: str, heading: str, intro: str, caveat: str) -> None:
    """One endurance series' panel.

    ``series`` selects the data *and* the neutralisation posterior, so a WEC
    race is never simulated with IMSA's hazards or vice versa. The two panels
    share this rendering code but never share a model, an event list, or a
    conclusion.
    """
    st.subheader(heading)
    st.caption(intro)

    races = _races(series)
    if races.empty:
        st.warning(f"No eligible {series.upper()} race is committed in this checkout.")
        return

    with st.sidebar:
        st.header("Race")
        options = list(races.index)
        idx = st.selectbox(
            "Event",
            options,
            index=len(options) - 1,
            format_func=lambda i: (
                f"{races.loc[i, 'year']} · {races.loc[i, 'event']} "
                f"({races.loc[i, 'car_class']})"
            ),
            key=f"{series}_event",
        )
        row = races.loc[idx]
        year, event, car_class = int(row["year"]), str(row["event"]), str(row["car_class"])

    with st.spinner(f"Fitting the {event} {year} race model..."):
        model = _endurance_model(series, year, event, car_class)
        distance = _endurance_distance(series, year, event, car_class)

    with st.sidebar:
        st.header("Race state")
        total_laps = st.slider(
            "Race distance (laps)", max(10, distance // 2), max(20, distance * 2),
            distance, key=f"{series}_total",
        )
        current_lap = st.slider(
            "Current lap (decision point)", 1, max(2, total_laps - 2),
            min(total_laps // 3, max(2, total_laps - 2)), key=f"{series}_lap",
        )
        tyre_age = st.slider("Tyre age (laps)", 0, 60, 10, key=f"{series}_age")
        laps_since_refuel = st.slider(
            "Laps since refuelling", 0, max(1, model.fuel_range_laps - 1),
            min(10, max(1, model.fuel_range_laps - 1)), key=f"{series}_fuel",
            help=(
                f"The measured fuel range for this race is "
                f"{model.fuel_range_laps} laps. The car must visit the pits "
                "before it runs out — that is a constraint, not a preference."
            ),
        )
        n_draws = st.select_slider(
            "Monte Carlo draws", [500, 1000, 2000, 5000], value=2000, key=f"{series}_draws",
        )
        run = st.button("Simulate", type="primary", width="stretch", key=f"{series}_run")

    st.markdown("**Measured model for this race** (nothing below is assumed)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Green pace", f"{model.green_pace_s:.1f}s")
    m2.metric(
        "Pit loss", f"{model.pit_loss_s:.1f}s",
        f"IQR {model.pit_loss_iqr_s:.1f}s over {model.n_pit_events} stops",
    )
    m3.metric("Fuel range", f"{model.fuel_range_laps} laps")
    m4.metric("Degradation", f"{model.net_slope_s:+.4f}s/lap", f"± {model.net_slope_se:.4f} SE")

    st.caption(caveat)
    if not model.sc_ratio_measured:
        st.caption(
            "This race saw no Safety Car laps at all, so its SC pace ratio "
            "falls back to the measured FCY ratio rather than being invented."
        )
    if not model.fcy_ratio_measured:
        st.caption(
            "This race saw no full-course-yellow laps, so its FCY pace ratio "
            "falls back to the measured SC ratio."
        )

    fuel_deadline = current_lap + (model.fuel_range_laps - laps_since_refuel)
    if fuel_deadline >= total_laps:
        st.success(
            f"Fuel reaches the flag: {model.fuel_range_laps - laps_since_refuel} "
            f"laps left in the tank with {total_laps - current_lap} to run, so "
            "finishing without stopping is on the table."
        )
    else:
        st.warning(
            f"Fuel forces a stop by lap {fuel_deadline}: "
            f"{model.fuel_range_laps - laps_since_refuel} laps left in the tank. "
            "Candidates beyond that lap are not offered, because running dry is "
            "not a strategy."
        )

    if not run:
        st.info("Set the race state on the left and press **Simulate**.")
        return

    scenario = EnduranceScenario(
        current_lap=current_lap,
        total_laps=total_laps,
        tyre_age=tyre_age,
        laps_since_refuel=laps_since_refuel,
    )
    with st.spinner("Running the Monte Carlo simulation..."):
        table = simulate_endurance(scenario, model, n_draws=n_draws)

    table = table.copy()
    table["Candidate"] = [
        "No stop" if lap == 0 else f"Lap {int(lap)}" for lap in table["pit_lap"]
    ]
    # pit_lap 0 means "run to the flag", so it belongs at the end of the axis.
    ordered = table.assign(
        _sort=table["pit_lap"].replace(0, total_laps + 1)
    ).sort_values("_sort")
    best = table.loc[table["p_best"].idxmax()]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**Remaining race time by candidate next stop**")
        _candidate_chart(
            list(ordered["Candidate"]),
            ordered["median_s"].to_numpy(),
            ordered["p10_s"].to_numpy(),
            ordered["p90_s"].to_numpy(),
            f"{event} {year} ({car_class}) — median ± [P10, P90], {n_draws} draws",
        )
    with col2:
        st.markdown("**Recommendation**")
        st.metric("P(best) next stop", str(best["Candidate"]), f"{best['p_best']:.0%} P(best)")
        st.metric("Median remaining", f"{best['median_s']:.0f}s")
        st.metric("P10-P90 range", f"{best['p10_s']:.0f}-{best['p90_s']:.0f}s")

    st.markdown("**Every candidate**")
    st.dataframe(
        table[["Candidate", "median_s", "p10_s", "p90_s", "p_best"]]
        .rename(columns={
            "median_s": "Median (s)", "p10_s": "P10 (s)",
            "p90_s": "P90 (s)", "p_best": "P(best)",
        })
        .round({"Median (s)": 1, "P10 (s)": 1, "P90 (s)": 1, "P(best)": 3})
        .sort_values("P(best)", ascending=False),
        width="stretch", hide_index=True,
    )

    stints_left = (total_laps - current_lap) / model.fuel_range_laps
    if stints_left > 1.0:
        st.caption(
            f"**Read this as the *next* stop only.** {total_laps - current_lap} "
            f"laps remain on a {model.fuel_range_laps}-lap tank, so roughly "
            f"{stints_left:.1f} more stints are needed; the totals above run to "
            "the flag after a single stop and therefore are not achievable race "
            "times. They rank *when to stop next* on a common set of random "
            "realisations, which is the question this engine answers. The full "
            "plan is below."
        )
    else:
        st.caption(
            "The remaining distance fits inside one tank, so these totals are "
            "achievable race times, not just a ranking."
        )

    _full_race_plan(model, total_laps, event, year, car_class)


def _full_race_plan(
    model: EnduranceRaceModel, total_laps: int, event: str, year: int, car_class: str
) -> None:
    """The whole-race stop sequence, solved exactly rather than searched.

    The Monte Carlo panel above answers "when next?"; this answers "how many
    stops, and where?" — a different question with an exact answer, because
    minimising over partitions of the race into fuel-feasible stints is a
    dynamic program, not a simulation.
    """
    st.markdown("**Full-race plan** — exact dynamic program, not a search")
    optimum = optimal_stop_plan(
        total_laps, model.green_pace_s, model.net_slope_s,
        model.pit_loss_s, model.fuel_range_laps,
    )
    naive = min_stops_plan(total_laps, model.fuel_range_laps)

    score = lambda plan: deterministic_time(  # noqa: E731
        plan, model.green_pace_s, model.net_slope_s, model.pit_loss_s
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Optimal stops", optimum.n_stops, f"stints {list(optimum.stint_lengths)}")
    c2.metric("Fuel-minimum stops", naive.n_stops, f"stints {list(naive.stint_lengths)}")
    c3.metric("Time the optimum saves", f"{score(naive) - score(optimum):.1f}s", "at expected pace")

    if optimum.n_stops == naive.n_stops:
        st.caption(
            f"At {event} {year} ({car_class}) the optimum takes the same number "
            "of stops as simply running the tank dry every time: this race is "
            "fuel-limited, not tyre-limited, and the only thing left to optimise "
            "is where the stints are cut."
        )
    else:
        st.caption(
            f"The optimum takes {optimum.n_stops - naive.n_stops} more stop(s) "
            "than the fuel minimum — degradation here is steep enough to pay for "
            "an extra pit visit."
        )

    stochastic = {
        "Optimal plan": evaluate_plan(optimum, total_laps, model),
        "Fuel-minimum plan": evaluate_plan(naive, total_laps, model),
    }
    st.dataframe(
        pd.DataFrame([
            {
                "Plan": name,
                "Stops": (optimum if name.startswith("Opt") else naive).n_stops,
                "Median (s)": round(res["median_s"], 1),
                "P10 (s)": round(res["p10_s"], 1),
                "P90 (s)": round(res["p90_s"], 1),
            }
            for name, res in stochastic.items()
        ]),
        width="stretch", hide_index=True,
    )
    st.caption(
        "The plan is chosen deterministically, then scored under the same "
        "stochastic neutralisations as everything else — so a deterministic "
        "edge that vanishes inside the P10-P90 spread is visible as such "
        "rather than being reported as a win."
    )


WEC_INTRO = (
    "Hypercar. Degradation fit on this race; FCY and Safety Car hazards from "
    "WEC's own series-wide posterior over its 33 committed races."
)
WEC_CAVEAT = (
    "WEC's neutralisations are Safety-Car-dominated: 44 SC deployments against "
    "18 FCY periods in the committed data, with SC durations running as long "
    "as 18 laps. Both hazards are measured from WEC alone — IMSA data never "
    "enters this model."
)
IMSA_INTRO = (
    "GTP. Degradation fit on this race; neutralisation hazards from IMSA's own "
    "series-wide posterior over its 63 committed races."
)
IMSA_CAVEAT = (
    "IMSA is a different neutralisation regime entirely: 293 full-course "
    "yellows and **zero** Safety Cars in the committed data. The SC hazard is "
    "therefore a Jeffreys-prior floor (half a pseudo-event), not a measured "
    "rate — the model refuses to encode 'can never happen' from an absence of "
    "evidence. WEC data never enters this model."
)

PANELS = {
    "Formula 1": f1_panel,
    "WEC — Hypercar": lambda: endurance_panel("wec", "WEC — pit-window simulator", WEC_INTRO, WEC_CAVEAT),
    "IMSA — GTP": lambda: endurance_panel("imsa", "IMSA — pit-window simulator", IMSA_INTRO, IMSA_CAVEAT),
}


def main() -> None:
    st.title("Motorsport Strategy Lab — live pit-window simulator")
    st.caption(
        "Three series, three separate models, one engine. Source: "
        "[github.com/mohammedmedjadj/Motorsport-Strategy-Lab]"
        "(https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab)."
    )
    with st.sidebar:
        series = st.radio("Series", list(PANELS), index=0)
        st.divider()
    PANELS[series]()


if __name__ == "__main__":
    main()
