"""Interactive demo: a live pit-window simulator for every class this project
models, using the exact same measured models and simulator engines as the rest
of the repository — no separate or simplified model built for the demo.

**Seven panels, one per class**, because the class is the unit this project
models and never pools:

- **F1** — compound choice, a mandatory two-dry-compound rule, no fuel
  constraint (refuelling is banned).
- **WEC Hypercar** — 44 Safety Cars against 18 FCY over 33 races; a 76 s pit
  loss makes every circuit fuel-limited.
- **IMSA GTP** — 293 FCY and *zero* Safety Cars over 63 races.
- **IMSA GTD / GTD PRO** — the same GT3 cars under the same Balance of
  Performance, separated only by whether an amateur-rated driver is
  mandatory. GTD is tyre-limited at five circuits where the prototypes are at
  one and none.
- **ELMS LMP2 / LMP2 Pro/Am** — a near-spec Oreca 07 field, and the second
  crew-rating experiment, which disagrees with IMSA's.

Keying a panel on series alone would have been a real defect rather than a
tidiness one: IMSA's three classes race the same rounds and their measured
tyre-change premiums are 8.7 s, 17.6 s and 16.9 s, so one race's model would
have appeared under another class's name.

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
def _races(series: str, car_class: str) -> pd.DataFrame:
    """One class's committed races. Filtered by class, not just series: IMSA
    fields three and ELMS two, and a panel that mixed them would be the very
    pooling this project refuses everywhere else."""
    races = available_races(series)
    return races[races["car_class"] == car_class].reset_index(drop=True)


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

def endurance_panel(series: str, car_class: str, heading: str, intro: str,
                    caveat: str) -> None:
    """One endurance **class's** panel — the unit this project models.

    ``series`` selects the neutralisation posterior, so a WEC race is never
    simulated with IMSA's hazards; ``car_class`` selects the degradation fit,
    pit loss and fuel range, so GT3 is never simulated with a prototype's.
    Six panels share this rendering code and share no fitted number.

    The class argument is not cosmetic. IMSA runs GTP, GTD and GTD PRO at the
    same rounds and their measured pit-stop premiums are 8.7 s, 17.6 s and
    16.9 s; a panel keyed on series alone would have shown one race's model
    under another class's name.
    """
    key = f"{series}_{car_class}".replace(" ", "_").replace("/", "_")
    st.subheader(heading)
    st.caption(intro)

    races = _races(series, car_class)
    if races.empty:
        st.warning(
            f"No {car_class} race for {series.upper()} is committed in this "
            "checkout. Run scripts/materialise_endurance.py to fetch them."
        )
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
            key=f"{key}_event",
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
            distance, key=f"{key}_total",
        )
        current_lap = st.slider(
            "Current lap (decision point)", 1, max(2, total_laps - 2),
            min(total_laps // 3, max(2, total_laps - 2)), key=f"{key}_lap",
        )
        tyre_age = st.slider("Tyre age (laps)", 0, 60, 10, key=f"{key}_age")
        laps_since_refuel = st.slider(
            "Laps since refuelling", 0, max(1, model.fuel_range_laps - 1),
            min(10, max(1, model.fuel_range_laps - 1)), key=f"{key}_fuel",
            help=(
                f"The measured fuel range for this race is "
                f"{model.fuel_range_laps} laps. The car must visit the pits "
                "before it runs out — that is a constraint, not a preference."
            ),
        )
        n_draws = st.select_slider(
            "Monte Carlo draws", [500, 1000, 2000, 5000], value=2000, key=f"{key}_draws",
        )
        run = st.button("Simulate", type="primary", width="stretch", key=f"{key}_run")

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


# Each panel states what its own class measured. Nothing here is shared
# between classes except the rendering code — the numbers quoted are each
# class's own, and where two classes disagree the panels say so.

WEC_INTRO = (
    "Hypercar. Degradation fit on this race; FCY and Safety Car hazards from "
    "WEC's own series-wide posterior over its 33 committed races."
)
WEC_CAVEAT = (
    "WEC's neutralisations are Safety-Car-dominated: 44 SC deployments against "
    "18 FCY periods, with SC durations running as long as 18 laps. A 76 s "
    "median pit loss makes every WEC circuit in scope fuel-limited on stop "
    "count — no extra stop ever pays for itself here."
)

GTP_INTRO = (
    "IMSA's manufacturer prototype class. Degradation fit on this race; "
    "neutralisation hazards from IMSA's own posterior over 63 committed races."
)
GTP_CAVEAT = (
    "IMSA has **293 full-course yellows and zero Safety Cars** in the "
    "committed data, so its SC hazard is a Jeffreys-prior floor rather than a "
    "measured rate — the model refuses to encode 'can never happen' from an "
    "absence of evidence. GTP services tyres in parallel with the fuel fill: "
    "a 8.7 s tyre-change premium against WEC's 21.6 s."
)

GTD_INTRO = (
    "GT3, **Pro/Am**: every entry must field a bronze- or silver-rated driver. "
    "Same cars and Balance of Performance as GTD PRO, different crews."
)
GTD_CAVEAT = (
    "The class that overturned this project's headline endurance finding. "
    "GTD's 19.7 s median pit loss is cheap enough that an extra stop can pay "
    "for itself, and it is **tyre-limited at five circuits** where the "
    "prototypes are at one and none. 'Every measured race is fuel-limited' was "
    "a fact about expensive stops, not about endurance racing."
)

GTDPRO_INTRO = (
    "GT3, **all-professional** line-ups. The same cars under the same Balance "
    "of Performance as GTD — the class boundary is the crew rating."
)
GTDPRO_CAVEAT = (
    "The controlled comparison: holding the car fixed and changing only the "
    "crew moves the tyre-change premium 17.6 s → 16.9 s, while changing the "
    "car moves it 8.7 s → 17.6 s. The pit-stop difference is the **car, not "
    "the crew**. On tyre wear the crew comparison is inconclusive here and "
    "contradicted in ELMS."
)

LMP2_INTRO = (
    "ELMS LMP2 — close to a one-make formula (Oreca 07 chassis, Gibson "
    "engine), which is why this class is the project's near-spec control."
)
LMP2_CAVEAT = (
    "ELMS is the most Safety-Car-dominated series in scope: **23 of 29 races** "
    "see one, against WEC's 19 of 33 and IMSA's none. A neutralised stop is "
    "worth more here than anywhere else this project models. Note that before "
    "2023 this label covered every LMP2 entry; from 2023 it means the "
    "professional subset only."
)

LMP2_PROAM_INTRO = (
    "ELMS LMP2 Pro/Am — the same Oreca 07 with a mandatory amateur-rated "
    "driver. A second natural experiment on crew rating, independent of IMSA's."
)
LMP2_PROAM_CAVEAT = (
    "And it **disagrees with IMSA's**. Paired on circuit and season, the "
    "Pro/Am slope is *shallower* by 0.0143 s/lap (p = 0.0093) where IMSA's "
    "was steeper by 0.0040 (p = 0.085). Two independent tests pointing "
    "opposite ways: no consistent crew effect on tyre wear survives across "
    "championships."
)

PANELS = {
    "Formula 1": f1_panel,
    "WEC — Hypercar": lambda: endurance_panel(
        "wec", "HYPERCAR", "WEC Hypercar — pit-window simulator",
        WEC_INTRO, WEC_CAVEAT),
    "IMSA — GTP": lambda: endurance_panel(
        "imsa", "GTP", "IMSA GTP — pit-window simulator", GTP_INTRO, GTP_CAVEAT),
    "IMSA — GTD (GT3 Pro/Am)": lambda: endurance_panel(
        "imsa", "GTD", "IMSA GTD — pit-window simulator", GTD_INTRO, GTD_CAVEAT),
    "IMSA — GTD PRO (GT3 all-pro)": lambda: endurance_panel(
        "imsa", "GTDPRO", "IMSA GTD PRO — pit-window simulator",
        GTDPRO_INTRO, GTDPRO_CAVEAT),
    "ELMS — LMP2": lambda: endurance_panel(
        "elms", "LMP2", "ELMS LMP2 — pit-window simulator",
        LMP2_INTRO, LMP2_CAVEAT),
    "ELMS — LMP2 Pro/Am": lambda: endurance_panel(
        "elms", "LMP2 Pro/Am", "ELMS LMP2 Pro/Am — pit-window simulator",
        LMP2_PROAM_INTRO, LMP2_PROAM_CAVEAT),
}


def main() -> None:
    st.title("Motorsport Strategy Lab — live pit-window simulator")
    st.caption(
        "Four series, six classes, six separate models, one engine. Source: "
        "[github.com/mohammedmedjadj/Motorsport-Strategy-Lab]"
        "(https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab)."
    )
    with st.sidebar:
        series = st.radio("Series / class", list(PANELS), index=0)
        st.divider()
    PANELS[series]()


if __name__ == "__main__":
    main()
