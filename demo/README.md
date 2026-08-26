# Interactive demo

`app.py` is a Streamlit front-end over the exact same measured models and
simulator engines used everywhere else in this project — no separate or
simplified model built for the demo. Pick a class, set a race state, and it
re-runs the real simulation live.

## Seven panels, one per class

The **class** is the unit this project models, not the series. Keying a panel
on series alone would not be untidy, it would be wrong: IMSA runs three
classes at the same rounds and their measured tyre-change premiums are 8.7 s,
17.6 s and 16.9 s, so one race's model would appear under another's name.

| panel | compound choice | fuel constraint | what makes it different |
|---|---|---|---|
| **F1** | yes, two dry compounds mandatory | none (refuelling banned) | the only panel that enforces a sporting regulation the engine cannot see |
| **WEC Hypercar** | not modelled | 76 s stop, hard tank | 44 Safety Cars vs 18 FCY; fuel-limited at every circuit |
| **IMSA GTP** | not modelled | 48 s stop | **293 FCY and zero Safety Cars** in 63 races |
| **IMSA GTD** | not modelled | 20 s stop | GT3 Pro/Am — **tyre-limited at five circuits** where prototypes are at one |
| **IMSA GTD PRO** | not modelled | 39 s stop | same car and BoP as GTD, all-professional crews |
| **ELMS LMP2** | not modelled | 65 s stop | near-spec Oreca 07; **23 of 29 races see a Safety Car** |
| **ELMS LMP2 Pro/Am** | not modelled | 62 s stop | the second crew experiment, which disagrees with IMSA's |

Every panel states its own class's caveats. Where two classes disagree — and
GTD/GTD PRO and the two ELMS classes do — the panels say so rather than
presenting one number.

## What each panel does

- **F1** — `src/simulator/engine.py::simulate`: candidate pit laps scored by
  P(best) under common random numbers, optional rival, coefficients resampled
  per draw from their measured CIs. Fit on the regulation-stable seasons; 2026
  is held out.
  It enforces what the engine cannot know: until the car has used two
  different dry compounds, running to the flag is excluded and the new set
  must differ from the current one.
- **The six endurance panels** — `src/simulator/endurance.py::simulate` for the
  *next* stop under the fuel clock, plus
  `src/simulator/multistop.py::optimal_stop_plan` for the whole race: an exact
  dynamic program over every fuel-feasible stint partition, compared against
  the fuel-minimum baseline both at expected pace and under stochastic
  neutralisations.
  When the remaining distance exceeds one tank, the panel says so — the
  single-stop totals rank candidates but are not achievable race times.

## Where the race list comes from

`available_races` derives from `ENDURANCE_SCOPE` intersected with what is
committed on disk — **not** from `available_events.csv`, which is a
network-derived scoping aid that enumerates one prototype class per series.
Reading the catalogue is why this demo offered 2 of 6 scoped classes for
weeks, silently. Deriving from the scope cannot drift against it, and two
tests in `tests/test_demo_app.py` assert that every scoped class has a panel
and that the offered race list equals the scope exactly.

## Is it tested?

Yes — [`tests/test_demo_app.py`](../tests/test_demo_app.py) drives this app
headlessly with Streamlit's `AppTest`: it switches class, presses **Simulate**
and asserts on real output (P(best) sums to 100%, no candidate stop lies
beyond the fuel range, no-stop is absent until the two-compound box is ticked,
no two classes show the same model, and every scoped class is reachable). CI
installs `demo/requirements.txt` so those tests run rather than skip.

## Run locally

```bash
pip install -r demo/requirements.txt
streamlit run demo/app.py
```

## Deploy (Hugging Face Spaces, Streamlit SDK)

1. Create a Space, SDK = Streamlit.
2. Point it at this repo (or push a copy), with `demo/app.py` as the app file
   and `demo/requirements.txt` as the requirements file — both Space settings,
   configured from the Hugging Face UI, not from this repo.
3. No secrets or network access needed: everything the app reads
   (`data/derived/`) is already committed.
