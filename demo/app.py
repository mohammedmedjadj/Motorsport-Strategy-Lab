"""Interactive demo: circuit + lap + compound -> live Monte Carlo pit-lap
distribution, using the exact same measured models and simulator engine as
the rest of this project (no separate/simplified model for the demo).

Run locally:

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
import streamlit as st

from src.simulator.artifacts import CircuitModel, load_circuit_models
from src.simulator.engine import RivalSpec, Scenario, simulate

st.set_page_config(page_title="Motorsport Strategy Lab", page_icon="\U0001F3C1", layout="wide")


@st.cache_resource
def _models() -> dict[str, CircuitModel]:
    return load_circuit_models()


def main() -> None:
    st.title("Motorsport Strategy Lab — live pit-window simulator")
    st.caption(
        "F1 · same measured degradation, safety-car and pit-loss models as the "
        "committed reports — not a simplified demo model. Source: "
        "[github.com/mohammedmedjadj/Motorsport-Strategy-Lab]"
        "(https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab)."
    )

    models = _models()

    with st.sidebar:
        st.header("Race state")
        circuit = st.selectbox("Circuit", sorted(models), format_func=str.title)
        model = models[circuit]
        compounds = sorted(model.degradation)

        total_laps = st.slider("Race distance (laps)", 40, 80, 66)
        current_lap = st.slider("Current lap (decision point)", 1, total_laps - 5, 20)
        compound = st.selectbox("Current compound", compounds)
        tyre_age = st.slider("Tyre age (laps)", 0, 40, 12)
        target_compound = st.selectbox(
            "Compound if we stop", compounds, index=compounds.index(compound)
        )

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
        run = st.button("Simulate", type="primary", use_container_width=True)

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
        include_no_stop=True,
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

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Total race time by candidate pit lap")
        fig, ax = plt.subplots(figsize=(8, 4.2))
        order = np.argsort([c if c else total_laps + 1 for c in candidates])
        x = np.arange(len(candidates))
        ax.errorbar(
            x, median[order], yerr=[median[order] - p10[order], p90[order] - median[order]],
            fmt="o", color="#7C3AED", ecolor="#B8A6E8", capsize=3,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(np.array(labels)[order], rotation=60, ha="right", fontsize=8)
        ax.set_ylabel("Total race time (s)")
        ax.set_title(f"{circuit.title()} — median ± [P10, P90], {n_draws} draws")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        st.pyplot(fig)

    with col2:
        st.subheader("Recommendation")
        st.metric("P(best) pit lap", labels[best_idx], f"{p_best[best_idx]:.0%} P(best)")
        st.metric("Median time", f"{median[best_idx]:.1f}s")
        st.metric("P10–P90 range", f"{p10[best_idx]:.0f}–{p90[best_idx]:.0f}s")
        if rival:
            ahead = result.ahead_of_rival["Rival"][best_idx].mean()
            st.metric("P(ahead of rival)", f"{ahead:.0%}")

    st.subheader("Every candidate")
    import pandas as pd

    table = pd.DataFrame({
        "Candidate": labels,
        "Median (s)": median.round(1),
        "P10 (s)": p10.round(1),
        "P90 (s)": p90.round(1),
        "P(best)": (p_best * 100).round(1),
    }).sort_values("P(best)", ascending=False)
    if rival:
        table["P(ahead of rival) %"] = (
            np.array([result.ahead_of_rival["Rival"][i].mean() for i in range(len(candidates))]) * 100
        ).round(1)
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.caption(
        "P(best) is a clean per-draw argmin across candidates sharing the same "
        "random realisations (common random numbers) — not an independent "
        "comparison of separately-simulated candidates. Coefficients are "
        "resampled per draw from their measured confidence intervals; nothing "
        "here is a fixed point estimate."
    )


if __name__ == "__main__":
    main()
