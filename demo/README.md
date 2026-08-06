# Interactive demo

`app.py` is a small Streamlit front-end over the exact same measured models
and Monte Carlo engine used everywhere else in this project
(`src/simulator/artifacts.py::load_circuit_models` +
`src/simulator/engine.py::simulate`) — no separate or simplified model built
for the demo. Pick a circuit, a lap, a tyre compound, optionally a rival, and
it re-runs the real simulation live.

Currently F1 only (the four FastF1-scoped circuits: Monaco, Singapore,
Barcelona, Suzuka); WEC/IMSA support is a natural extension using
`src/simulator/endurance.py`'s equivalent API, not yet wired into this app.

## Run locally

```bash
pip install -r demo/requirements.txt
streamlit run demo/app.py
```

## Deploy (Hugging Face Spaces, Streamlit SDK)

1. Create a Space, SDK = Streamlit.
2. Point it at this repo (or push a copy), with `demo/app.py` as the app
   file and `demo/requirements.txt` as the requirements file — both
   Space settings, configured from the Hugging Face UI, not from this repo.
3. No secrets or network access needed: everything the app reads
   (`data/derived/f1/*.csv`) is already committed.
