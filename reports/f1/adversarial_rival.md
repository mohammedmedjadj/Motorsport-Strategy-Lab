# Adversarial rival — the pit stop as a two-player game

Every other layer of this project treats a rival as a fixed plan. This one does
not: the rival **reacts**. If you pit to undercut, the rival covers; your best
pit lap depends on theirs, and theirs on yours. `src/simulator/adversarial.py`
builds the payoff matrix over both cars' pit-lap choices by Monte Carlo and
solves the game.

## How a pair of choices becomes a probability

For every `(your pit lap, rival pit lap)` the engine runs both cars under the
**same** resampled realisation (degradation and fuel coefficients, the
neutralisation timeline, common random numbers), each with its own lap noise,
and computes each car's time **lap by lap**. Two things then decide who
finishes ahead, and the model needs both:

1. **Who wins the pit exchange** — resolved the lap both cars have finally
   stopped, from the cumulative lap times (your fresh-tyre out-lap against the
   rival's worn in-lap). This is the binary heart of an undercut that a
   final-gap-only model smooths away.
2. **Whether that lead then holds** — governed by the circuit's *measured*
   overtaking difficulty ([track_position.md](track_position.md)): within a
   passing window the leader keeps the place with probability
   `hold_probability(swap_rate, laps)`. Outside the window, pace decides.

The result is `P[i, j] = P(you finish ahead | you pit lap i, rival pits lap j)`.

## Solving the game

- **Rival best response**: for each of your laps, the rival picks the lap that
  *minimises* your win probability — the optimal cover.
- **Naive optimum**: your best lap assuming the rival keeps its announced plan.
- **Stackelberg optimum**: your best lap once the rival is allowed to cover.

## Worked example (reproducible: seed 11, 3000 draws)

You are 1.2 s behind a rival of equal pace, both on 22-lap-old mediums at
lap 38; the rival's announced plan is to stop on lap 48. Your only real route
past is the undercut.

**Monaco** (measured swap rate 0.0038 — very sticky):

| | Your win probability |
|---|---|
| Undercut on lap 39, rival stays on plan (lap 48) | **0.54** — the undercut works and Monaco locks it in |
| Same undercut, but the rival **covers** (also pits lap 39) | **0.46** |
| Naive optimum (lap 39), assuming no reaction | 0.54 |
| ...its real value once the rival covers | 0.46 |
| Cover-aware (Stackelberg) optimum | 0.46 |
| **Win probability given away by ignoring the cover** | **~0.08** |

**Barcelona** (measured swap rate 0.0373 — fluid):

| | Your win probability |
|---|---|
| Undercut on lap 39, rival stays on plan | 0.45 — lower: even a won undercut can be undone on track here |
| Same undercut, rival **covers** (pits lap 41) | 0.35 |
| Cover-aware optimum (shifts to lap 42) | 0.40 |
| **Win probability given away by ignoring the cover** | **~0.09** |

Two things the model gets right, straight from the measured primitives:

- **The cover is worth ~8-9 points of win probability.** A frozen-rival
  simulator that assumes the announced plan overstates the undercut by exactly
  that much — the objection a real strategist raises, now quantified.
- **The same undercut is worth more at Monaco than at Barcelona.** Winning the
  pit exchange is decisive where position is sticky and only provisional where
  it is fluid — the track-position layer feeding straight into the strategy
  call.

## What is and isn't modelled (stated, not hidden)

- **One stop each.** Both cars make a single further stop; multi-stop game trees
  are future work.
- **The passing window (default 1.0 s) is the one racecraft constant not
  measured** from data — it sets the gap within which position is contestable.
  It is a parameter, and the qualitative results hold across a sensible range;
  everything else (pace, degradation, pit loss, hold probability) is measured.
- **Equal-pace battles sit near a coin flip in expectation.** The drama of a
  real undercut is in individual races; averaged over the propagated
  uncertainty, an evenly-matched duel is genuinely close, and the model says so
  rather than manufacturing certainty.
- **Pace, not a separate overtaking-vs-pace model, drives the on-track gap.**
  A genuinely faster car passes because it opens the gap outside the window;
  the measured swap rate governs only the contested near-tie region. A full
  overtaking-probability-vs-pace-delta function would need data (lap-by-lap
  positions in wheel-to-wheel battles) this project does not have.
