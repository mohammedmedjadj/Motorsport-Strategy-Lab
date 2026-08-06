# Interactive demo

`app.py` is a Streamlit front-end over the exact same measured models and
simulator engines used everywhere else in this project — no separate or
simplified model built for the demo. Pick a series, a race state, and it
re-runs the real simulation live.

## The three series are separate panels, on purpose

They are not variants of one another, and the demo is structured so a visitor
cannot read one as the other:

| | Compound choice | Fuel constraint | Neutralisations in the committed data |
|---|---|---|---|
| **F1** | yes, and two dry compounds are mandatory | none (refuelling banned) | SC + VSC, per circuit |
| **WEC** | not modelled | hard tank limit | **44 Safety Cars, 18 FCY** over 33 races |
| **IMSA** | not modelled | hard tank limit | **293 FCY, zero Safety Cars** over 63 races |

That last row is why WEC and IMSA never share a model here: IMSA's Safety Car
hazard is a Jeffreys-prior floor rather than a measured rate, and its SC pace
ratio falls back to its FCY ratio, because there is no IMSA Safety Car in the
data to measure. Pooling the two series would produce a neutralisation model
that describes neither.

## What each panel does

- **F1** — `src/simulator/engine.py::simulate`: candidate pit laps scored by
  P(best) under common random numbers, optional rival, coefficients resampled
  per draw from their measured CIs. Fit on the regulation-stable seasons; 2026
  is held out.
  The panel enforces the sporting regulations that the engine, which only
  minimises time, does not know about: until the car has used two different dry
  compounds, running to the flag is excluded and the new set must differ from
  the current one.
- **WEC / IMSA** — `src/simulator/endurance.py::simulate` for the *next* stop
  under the fuel clock, plus `src/simulator/multistop.py::optimal_stop_plan`
  for the whole race: an exact dynamic program over every fuel-feasible stint
  partition, compared against the fuel-minimum baseline both at expected pace
  and under stochastic neutralisations.
  When the remaining distance exceeds one tank, the panel says so — the
  single-stop totals rank candidates but are not achievable race times.

## Is it tested?

Yes — [`tests/test_demo_app.py`](../tests/test_demo_app.py) drives this app
headlessly with Streamlit's `AppTest`: it switches series, presses **Simulate**
and asserts on the real output (P(best) sums to 100%, no candidate stop lies
beyond the fuel range, no-stop is absent until the two-compound box is ticked,
and the two endurance panels never show the same model). CI installs
`demo/requirements.txt` so those tests run rather than skip.

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
   (`data/derived/`) is already committed.
