# FastF1 issue — `get_session()` silently returns a different race

**Status:** ready to file at <https://github.com/theOehrly/Fast-F1/issues>
**Reproduction:** `outreach/fastf1_repro.py` (self-contained, no project code)

---

## Title

`get_session()` returns an unrelated event when the requested one did not run
that season

## Body

When an event name does not exist in the requested season, `get_session()` does
not fail — it fuzzy-matches to a **different race** and returns it, logging a
warning. Code that loops over seasons then analyses the wrong Grand Prix with no
error to notice.

### Reproduction

```python
import fastf1

session = fastf1.get_session(2018, "Miami Grand Prix", "R")
print(session.event["EventName"], "|", session.event["Location"])
# Italian Grand Prix | Monza
```

The Miami Grand Prix was first run in 2022. The returned session is a different
race, in a different country, on a different continent.

The same happens for a cancelled round:

```python
session = fastf1.get_session(2020, "Monaco Grand Prix", "R")
print(session.event["EventName"], "|", session.event["Location"])
# Italian Grand Prix | Monza
```

Monaco 2020 was cancelled. Asking for it returns Monza.

`outreach/fastf1_repro.py` in this repository runs all of these against a clean
install. Verified output on **fastf1 3.8.3**:

```
requested                              returned                   location
2018 Miami Grand Prix                  Italian Grand Prix         Monza
2020 Monaco Grand Prix                 Italian Grand Prix         Monza
2018 Las Vegas Grand Prix              French Grand Prix          Le Castellet
2024 Monaco Grand Prix                 Monaco Grand Prix          Monaco        <- control, correct
2018 Mexico City Grand Prix            Mexican Grand Prix         Mexico City   <- rename, correct
```

Three requests for events that did not exist in that season returned three
different unrelated races. The last two rows are the cases that must keep
working: an event that exists, and one that was renamed without moving.

### Current behaviour

A warning is logged —

```
events  WARNING  Correcting user input 'Miami Grand Prix' to 'Italian Grand Prix'
```

— and a valid `Session` is returned. Under `logging` defaults in a notebook or a
batch script the warning is easy to miss, and the returned object gives no
indication that it is not what was asked for.

### Why it matters

The failure is silent and it scales. A loop of the shape

```python
for season in range(2018, 2026):
    for event in CALENDAR:
        session = fastf1.get_session(season, event, "R")
        ...
```

produces a dataset where some rows are the wrong circuit entirely, and nothing
downstream can tell.

Our own sweep is 2018–2025 across 26 circuits: **180 requested editions, of
which 26 did not run that season — and all 26 came back as some other race.**
That is 14% of the requests, and the substitutes are not a single fallback but
ten different Grands Prix:

| handed back instead | times |
|---|---|
| Italian | 5 |
| Hungarian | 5 |
| Austrian | 4 |
| Australian, German, Chinese, Russian, Spanish | 2 each |
| Belgian, Turkish | 1 each |

Every one of those would have entered the dataset as the circuit we asked for.
We only know the count because we added a guard; before that, the same sweep
reported a clean run.

### What makes this hard to guard against downstream

Comparing the requested name to the resolved name looks like the obvious check,
and it is wrong in the other direction: a Grand Prix can be **renamed without
moving**. Mexico ran as the "Mexican Grand Prix" through 2020 and the "Mexico
City Grand Prix" from 2021; Brazil as the "Brazilian Grand Prix" then "São
Paulo". A name check rejects those correct matches.

The property that separates the two cases is the **location**: a rename keeps
it, a substitution changes it. That is what we ended up checking, and it works —
but it needs a per-circuit location table that every consumer has to build
independently.

### Suggested fixes, in order of how little they change

1. **A `strict=` parameter on `get_session()`** — default unchanged, opt-in to
   raising instead of substituting. Smallest possible change, and enough for any
   caller doing a systematic sweep.
2. **Refuse cross-country substitutions.** The schedule already carries
   `Country`; a fuzzy match that changes it is a substitution rather than a
   correction, and could raise while same-country renames still resolve.
3. **Expose the match quality.** Return the score alongside the session so a
   caller can set its own threshold, rather than each rebuilding the check.

Happy to open a PR for whichever of these fits the project's direction — (1) is
the smallest and we have the test cases from our own guard.

### Environment

- FastF1 **3.8.3**
- Python 3.13, Windows 11
- Reproduces from a cold cache and a warm one
