# F1 degradation — full-calendar breadth (Kaggle per-lap history)

The FastF1 model in [degradation_phase2.md](degradation_phase2.md) is **deep** (tyre compound, per-lap Safety-Car/VSC flags) but covers only the four scoped circuits. This layer is the **breadth** complement: the same net-slope definition fitted per race across the *whole calendar* from Kaggle per-lap times, trading compound/flag fidelity for coverage.

Coverage: **35 circuits, 229 race-seasons** fitted (was 4 via FastF1), after excluding **53 wet races** (via the weather layer) so a wet-to-dry track is not mistaken for tyre wear. Slopes are fitted with driver-and-stint fixed effects removed, on green laps only (field-wide slow laps inferred as neutralisations and dropped, since Kaggle carries no SC flag).

## Solving the fuel/tyre confound (not just documenting it)

A single 'net slope' in F1 is dominated by **fuel burn**: the car sheds ~1.5 kg/lap and speeds up, which can swamp or invert tyre wear — the median net slope is near zero or negative for that reason, not because tyres improve. But **F1 has had no refuelling since 2010**, so fuel mass is a whole-race function of the *absolute* lap while tyre age *resets each stint*. The two stop being collinear, so a two-regressor fit `lap_time ~ driver + tyre*tyre_age + fuel_evo*lap` **separates them** — something the endurance data fundamentally cannot do, because every endurance stop refuels and re-aligns fuel with tyre age.

The isolated tyre slope is **positive in 88% of races** (physically correct — tyres wear), while the fuel/evolution term carries the negative whole-race trend. This is the direct answer to the 'fuel and tyre age are confounded' limitation.

## Regulation eras — and why 2026 is walled off

Degradation is comparable only **within** a regulation era. The artifact carries an `era` column so no fit is ever pooled across a rules boundary:

| Era | Circuits | Race-seasons | Median net | Median tyre-only | Median fuel/evo |
|---|---|---|---|---|---|
| ground-effect | 24 | 54 | -0.0046 | +0.0453 | -0.0537 |
| hybrid-v6 | 21 | 48 | +0.0071 | +0.0564 | -0.0511 |
| v8-blown | 20 | 45 | -0.0241 | +0.0626 | -0.0835 |
| wide-aero | 29 | 82 | -0.0218 | +0.0222 | -0.0577 |

**2026 is its own era (`2026-nextgen`), the deepest break in a generation** — MGU-H removed and ~50% electric power, ~30% less race fuel, active aero with a Manual Override Mode replacing DRS, narrower lighter cars and narrower tyres. Less fuel and narrower tyres move both the tyre and fuel terms this report separates, so no pre-2026 slope transfers. This source stops at 2024; a 2026 race (current era: `2026-nextgen`) is modelled from 2026 data via the live FastF1 pipeline, never from here.

## Highest and lowest tyre wear, current era (`ground-effect`)

Ranked by the **isolated tyre slope**, not the fuel-confounded net:

| Circuit | Year | Tyre-only (s/lap) | Fuel/evo | Net | Green laps |
|---|---|---|---|---|---|
| spa | 2022 | +0.1873 | -0.0909 | +0.1035 | 614 |
| spa | 2023 | +0.1777 | -0.1142 | +0.0846 | 673 |
| bahrain | 2023 | +0.1256 | -0.0811 | +0.0460 | 872 |
| catalunya | 2022 | +0.1176 | -0.0537 | +0.0694 | 1022 |
| suzuka | 2023 | +0.1176 | -0.0761 | +0.0477 | 660 |
| suzuka | 2024 | +0.1153 | -0.0955 | +0.0169 | 705 |
| miami | 2022 | -0.0038 | -0.0500 | -0.0486 | 807 |
| losail | 2024 | -0.0465 | -0.0513 | -0.0671 | 621 |
| monza | 2022 | -0.0854 | +0.0531 | +0.0061 | 765 |
| silverstone | 2024 | -0.1338 | +0.0039 | +0.0469 | 800 |

## Honest limits of this source

- No tyre compound: a slope is the net across whatever compounds ran in the race, not split by tyre.
- No SC/VSC flag: neutralised laps are *inferred* from field-wide slow laps, a heuristic, not the ground truth FastF1 provides.
- Cross-season stability within an era is not asserted here; each row is a self-contained per-race fit (the same discipline as the endurance reports).
- **Scrubbed (lightly-used) tyres do not bias the slope.** Kaggle has no tyre-life column, so a stint's tyre age is counted from 0, whereas a scrubbed set really starts a few laps old. But a per-stint age offset shifts only the *intercept*: `lap = a + b*(age + scrub)` = `(a + b*scrub) + b*age`, and the per-(driver, stint) fixed effect absorbs the `b*scrub` term, leaving the slope `b` unchanged — so the net and tyre-only wear rates are robust to scrubbing. Only an absolute tyre-age readout would be affected, which this layer never uses. (The high-fidelity FastF1 model sidesteps it entirely via the real `TyreLife` / `FreshTyre` columns.)
