# ELMS — Phase 0: data availability

*ELMS only. If this series is ever built out, it gets its own reports at every
phase, as WEC and IMSA do — the three endurance series are never merged into
one write-up.*

Phase 0 answers one question before any modelling: **is the data actually
there, and what is wrong with it?** Everything below comes from direct queries
against the upstream DuckDB (`hf://datasets/tobil/imsa/imsa.duckdb`,
`laps_with_metadata`, `session = 'race'`), not from assumption. Nothing has
been modelled yet and nothing has been materialised.

## 1. Why ELMS, and why now

The endurance loader has listed `elms` and `alms` in `SUPPORTED_SERIES` since
it was written, and nothing has ever used them. With F1, WEC and IMSA closed
out, the next series is the obvious direction, and the upstream source already
carries it — so the cost is a scoping exercise, not a new ingestion path.

There is also a scientific reason to prefer ELMS over simply adding more
Hypercar or GTP data. ELMS's prototype class is **LMP2**, which is close to a
one-make formula (Oreca 07 chassis, Gibson engine) where Hypercar and GTP are
manufacturer prototypes equalised by Balance of Performance. The degradation
instability this project measured in F1 and endurance — slopes that fail to
transfer between seasons — has an obvious candidate explanation in
heterogeneous, BoP-adjusted machinery. A near-spec field is the natural
control: if slopes still fail to transfer in LMP2, the instability is a
property of the data, not of the hardware.

## 2. What is there

| series | race laps | seasons | events |
|---|---|---|---|
| imsa | 564,377 | 2021-2026 | 17 |
| wec | 206,707 | 2021-2026 | 13 |
| **elms** | **111,193** | **2021-2025** | **10** |
| alms | 100,288 | 2022-2026 | **3** |

ELMS is comparable in scale to WEC. Its LMP2 class alone carries 44,280 race
laps across 5 seasons and 33 distinct cars.

Applying the same eligibility floor the existing scan uses (at least 4 cars,
at least 40 laps, and a non-zero green-flag fraction): **25 of 29 LMP2
race-seasons are eligible**, across 9 circuits — Aragon, Barcelona, Imola,
Monza, Mugello, Paul Ricard, Portimao, Silverstone, Spa.

## 3. Two traps, both of which would have silently corrupted a model

**Trap 1 — race-control flags are missing at four 2021 events, not at all of
2021.** Barcelona, Monza, Paul Ricard and Spielberg 2021 return a green-flag
fraction of exactly **0.000**: the `flags` column is empty for those races.
Lap times and tyre ages are complete, so the races look perfectly healthy on
every other measure, and a degradation model would happily fit them — on a
frame that cannot distinguish green running from a caution.

This is the same failure WEC 2021 showed (Monza, Portimao) and it is caught by
the same green-fraction floor. What is worth stating precisely is that it is
an **event-level** problem, not a season-level one: Portimao 2021 (0.946) and
Spa 2021 (0.888) are fine. Dropping the whole of 2021 would discard two usable
races for no reason.

**Trap 2 — the LMP2 class label changes meaning in 2023.** This one has no
precedent in the WEC or IMSA work and is the more dangerous of the two:

| year | `LMP2` cars | `LMP2 Pro/Am` cars |
|---|---|---|
| 2021 | 19 | — |
| 2022 | 17 | — |
| 2023 | 8 | 11 |
| 2024 | 14 | 8 |
| 2025 | 13 | 8 |

Before 2023 the single label `LMP2` covers every LMP2 entry. From 2023 the
field is split, and `LMP2` means *the professional-crew subset only*. The
label is stable; the population behind it is not. A model pooling "LMP2
2022-2025" would be comparing an all-comers field against a pro-only field and
attributing the difference to whatever regressor happened to correlate with
season.

This is structurally identical to the F1 2026 regulation boundary already
handled in `src/ingestion/config.py::REGULATION_ERA_START` — a name whose
meaning changes mid-scope — and it is not cosmetic: a Pro/Am entry must run an
amateur-rated driver, whose stint pace and consistency differ systematically
from a professional's.

Three defensible ways to handle it, none of which should be chosen by default:

1. **Union** `LMP2` and `LMP2 Pro/Am` from 2023 to reconstruct the pre-2023
   all-comers population. Consistent across all 5 seasons; loses the crew
   distinction.
2. **Restrict to 2023-2025** and use `LMP2` (pro-only) consistently. Three
   seasons, cleanest population, smallest sample.
3. **Model the two classes separately.** The most interesting option, because
   it makes the amateur-driver effect *measurable* rather than a nuisance —
   and neither WEC's Hypercar nor IMSA's GTP offers an equivalent split, so it
   is a question this project cannot currently ask anywhere else.

## 4. ALMS is declined, for now

ALMS (the Asian Le Mans Series in this source) carries 100,288 race laps, which
looks ample — but across only **3 distinct events** in 5 seasons. Lap volume is
not the binding constraint for this project's models; circuit diversity is.
Every cross-validation result the endurance work reports is leave-one-circuit-
out or leave-one-season-out, and three circuits cannot support the first. Its
27,697 LMP2 laps would add depth where this project already has depth and
nothing where it is thin.

Stated as a scoping decision with its reason, so it can be revisited if the
source's ALMS coverage widens — not as a claim that the series is unsuitable.

## 5. Definition of Done for this phase, and what is deliberately not done

Done: the source is verified by direct query; the eligible scope is enumerated
from the source's own event strings rather than guessed; both traps are
identified with the numbers that reveal them; the ALMS decision is recorded
with its reason.

**Not done, on purpose:** no ELMS data is materialised, no entry has been added
to `src/data/endurance_scope.py`, and no model has been fitted. Phase 0 is a
gate, and the class-split question in §3 is a scoping decision that changes
what every later phase measures. Making that choice silently, in the same pass
that discovered it, is exactly how a project ends up with a result nobody can
defend.
