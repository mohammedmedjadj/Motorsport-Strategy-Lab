# The negative slopes are track evolution, not tyres

A diagnosis, not a fix. It explains a defect this project has carried in every
endurance series since the first fit, and it names what the model is missing
rather than patching the symptom.

## The symptom

41 of 210 scoped race-seasons fit a **negative** net degradation slope, and
three of them are physically impossible: tyres apparently gaining more than
0.1 s/lap as they age. ELMS Portimao 2023 fits −0.213 s/lap.

Chasing that number produced three real filtering fixes (see the field-wide
hysteresis in `src/degradation/endurance.py`), which took the impossible cases
from 7 to 3. Portimao survived all of them, so the cause is not filtering.

## The paradox that identified it

At Portimao 2023, fitting each **car** separately gives a positive slope for
six of seven cars (+0.10 to +0.26). The pooled car-driver fixed-effects fit
gives **−0.21**. A within-group sign that flips when groups are pooled is
Simpson's paradox, and it means a variable correlated with both the regressor
and the outcome has been left out.

Fitting each **car-driver unit** separately settles which: 18 of 21 units are
negative. So the negative slope is genuinely inside the stints, not an
artefact of averaging across them.

## The variable

The race gets **17.8 seconds a lap faster** from start to finish:

| race phase | median lap |
|---|---|
| laps 11–25 | 116.0 s |
| laps 25–39 | 114.1 s |
| laps 39–52 | 110.5 s |
| laps 52–66 | 103.0 s |
| laps 66–80 | 98.6 s |
| laps 80–94 | 98.2 s |

A drying or rapidly rubbering-in track. Within any stint, `tyre_age` rises
lap by lap — the correlation between lap number and tyre age *inside a unit*
is **1.000** — so later-in-stint laps are simultaneously on older tyres and on
a much better track. The fixed effects absorb each unit's pace **level**; they
absorb nothing of a trend that runs through the whole race. Track evolution is
therefore attributed to tyre age, with its sign inverted.

The F1 model has a lap-number regressor as a fuel proxy, which incidentally
absorbs some of this. The endurance model deliberately replaced it with
`laps_since_refuel`, because endurance cars refuel and fuel load is not
monotone in lap number. That substitution was correct for fuel and left
nothing carrying race time.

## Measured, not argued

Adding a plain lap-number term to the design moves the slope exactly where the
drift is, and leaves races without drift alone:

| race | start-to-finish drift | slope | with a lap-number term |
|---|---|---|---|
| ELMS Portimao 2023 | **−17.6 s** | −0.2134 | **−0.1311** |
| WEC COTA 2025 | −5.3 s | −0.1645 | −0.1116 |
| WEC Bahrain 2024 | −0.8 s | +0.0576 | +0.0577 |
| IMSA Sebring 2024 | +0.2 s | +0.0139 | +0.0137 |

The two races with no drift are untouched to four decimal places. The two with
drift move substantially toward zero. That is the signature of a real omitted
variable rather than a coincidence.

## An attempted fix, and why it was withdrawn

A linear term recovers only ~40% of the gap because the drying is non-linear
(116 → 114 → 110 → 103 → 98.6 → 98.2, steep early and flat late). So a
piecewise-linear race-time basis was built and validated on synthetic races
with a known +0.080 s/lap slope and an 18 s drying curve
(`src/degradation/track_evolution.py`). It looked convincing:

| model | recovered slope (truth +0.0800) |
|---|---|
| current (fixed effects + tyre age) | **−0.0750** — wrong sign |
| + linear lap term | +0.0555 |
| + piecewise-linear basis | **+0.0810** |

It also failed catastrophically on races with too few stints (−3.88), so an
identifiability test was added — the multiple correlation of tyre age on the
time basis after fixed effects, which reads 1.000 in the degenerate case — and
the term applied only below a 0.95 limit. On synthetic data that guard worked
exactly as designed.

**Refitting all 210 real race-seasons then made everything worse**: negative
slopes 41 → 64, physically impossible ones 3 → 5, the ELMS median crossing
from +0.019 to −0.007. The wiring was reverted; the module and this evidence
are kept.

The explanation is in the diagnostic itself. Median identifiability on real
races is **0.585**, against 0.18–0.39 in the synthetic races used to validate
it. Real fields sit far closer to the degenerate boundary than the generator
implied, so a 0.95 limit admits races the basis cannot support. The synthetic
test modelled track evolution as the only confounder on cleaner stint
structures than any real race has, and produced false confidence.

That is the whole reason to measure a fix on real data before keeping it, and
the reason this section reports a withdrawal rather than a success.

## What this does and does not invalidate

- **Slope magnitudes are affected** in races with strong track evolution, most
  of all where the fit is negative. Those numbers should be read as a lower
  bound on degradation, not a measurement.
- **The cross-series tyre-vs-fuel rule is not affected in kind.** Its
  tyre-limited group carries clearly *positive* slopes (+0.024 to +0.066); the
  bias here pushes slopes down, so correcting it can only strengthen that
  finding, never create it.
- **The near-spec control result is not affected.** ELMS slopes failing to
  transfer between seasons is a statement about *variance* between fits, and
  an omitted trend that differs by race is one more reason they do not
  transfer — it supports that conclusion rather than undermining it.
- **The crew comparison is affected symmetrically.** Both classes race the
  same weekend on the same track, so a shared trend cancels in the paired
  differences that test uses.
