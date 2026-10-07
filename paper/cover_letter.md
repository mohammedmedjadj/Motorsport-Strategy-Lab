# Cover letter — Wharton Sports Analytics Journal, Fall 2026

*Submission deadline 16 November 2026. Publication 7 December 2026.*

---

To the editors,

I am submitting **"Does a tyre-degradation model transfer? Cross-championship
evidence and a retrospective audit of 1,280 real pit-stop decisions"** for the
Fall 2026 issue.

The paper asks two questions that the motorsport-strategy literature mostly
does not. Does a fitted tyre-degradation model predict a season it has never
seen? And does its recommendation resemble what a professional team actually
did? To answer both I built one protocol and applied it identically to seven
car classes across four championships — Formula 1, WEC, IMSA and ELMS — using
only public timing data.

Four findings come out of it, three of them negative:

1. Degradation slopes transfer as a property of the circuit-class rather than
   the championship, and transfer is rare: 5 of 51 circuit-classes reach a
   within-stint R² of 0.2 under leave-one-race-out. A near-specification
   control field, where every car is the same chassis and engine with no
   Balance of Performance, fails exactly as the balanced fields do, which rules
   out heterogeneous machinery as the cause.
2. Whether an extra pit stop can ever pay is set by the cost of the stop rather
   than by the car. Across 205 race-seasons the class-level correlation between
   median pit loss and tyre-limited share is −0.982, and ranking race-seasons
   by pit loss alone separates the two regimes at an AUC of 0.977 against 0.865
   for degradation.
3. Replaying 1,280 real first pit stops, an exact optimiser stops later than
   teams did on 80% of Formula 1 decisions, by a median of 12 laps. Three
   candidate explanations were tested and all three failed, including one taken
   from a published game-theoretic model.
4. The rival that a competition-aware model should respond to is
   under-determined. Four defensible selection rules — two of them taken from
   published work — name the same car on 17 of 271 decisions.

The fourth result is the one I would point an editor at. The game-theoretic
branch of this literature rests on a two-car abstraction, and nobody has
measured whether those two cars can be identified in a real race. On this
evidence they cannot be identified uniquely, which constrains a family of
models rather than only mine.

Everything is reproducible. The manuscript contains no numbers of its own:
every quantity is a macro generated from committed artifacts by a script in the
public repository, and continuous integration fails on any difference between
what the repository holds and what the code regenerates. Three layers read a
third-party export I cannot redistribute, and the paper names them and says
which published claim one of them carries.

## Eligibility and declarations

I am a high school student, which the call for submissions lists as eligible.
The work is my own, it is not under review elsewhere, and it has not been
published before. There are no conflicts of interest and no funding to
declare.

Thank you for considering it.

Mohammed Reda Medjadj
Independent

Repository: <https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab>
Archived and citable: <https://doi.org/10.5281/zenodo.22726130>
