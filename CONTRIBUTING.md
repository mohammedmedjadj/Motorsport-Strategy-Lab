# Contributing

This is primarily a solo research project, but issues, questions and pull
requests are welcome — especially from the FastF1 community, since parts of
this repo are meant to be reusable outside it (see `reports/methodology.md`).

## Setup

```bash
git clone https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab.git
cd Motorsport-Strategy-Lab
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on Unix
pip install -r requirements.txt # or requirements.lock for exact pins
python scripts/check_data_availability.py   # populates the FastF1 cache (F1 only)
pytest
```

WEC and IMSA races are already committed as derived CSVs (`data/derived/wec/`,
`data/derived/imsa/`), so their tests run fully offline with no extra setup.

## Project structure

Each series (F1, WEC, IMSA) follows the same phase sequence — data
availability, data quality, degradation model, neutralisation/safety-car
model, simulator, and (F1 only, so far) prediction, racecraft, and a
retrospective audit. See `## How it fits together` and `## Repository map` in
the [README](README.md) for the full breakdown, and each series' own "known
limitations" section before assuming a gap is unintentional.

## Engineering rules

These are non-negotiable for any change, existing or new (full list in the
README's "Engineering rules" section):

- **No fabricated data.** If a source doesn't have something, say so as a
  limitation — never estimate it silently.
- **No data leakage.** Decision models may only use information knowable at
  the simulated moment of the race.
- **Uncertainty is first-class.** Ship an interval or a distribution, not a
  bare point estimate.
- **Nothing is pooled across series.** F1, WEC and IMSA get their own fitted
  coefficients and posteriors; only estimator code (and, for WEC/IMSA, the
  data schema) is shared.

## Before opening a PR

- Run the full suite (`pytest`) and make sure it's green.
- If you touch a fitted artifact (anything under `data/derived/`), regenerate
  it with the matching script under `scripts/` rather than hand-editing the
  CSV, and mention which script in the PR description.
- If a change alters a reported number, update the corresponding report under
  `reports/` in the same PR — a stale report is treated as a bug.
- Keep new tests next to the existing ones in `tests/`, following the
  naming convention already in use (`test_<module>.py`).

## Reporting a bug or proposing a feature

Use the issue templates under `.github/ISSUE_TEMPLATE/` — they ask for
exactly the context needed to reproduce a data or modelling issue (series,
circuit, season) or to scope a feature request.
