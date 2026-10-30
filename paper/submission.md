# Submission packet — Wharton Sports Analytics Journal, Fall 2026

Deadline **16 November 2026**. Publication 7 December 2026. ISSN 3070-4065.
Advanced high school students are listed as eligible.

The form does not take a cover letter. It takes fields, one of which is free
text. Everything below is written to be pasted into the field it names.

Form: <https://wsb.wharton.upenn.edu/wharton-sports-analytics-journal-submission-form/>

---

## Fields

| Field | What to enter |
|---|---|
| Name (Primary Author) | Mohammed Reda Medjadj |
| Email Address (Primary Author) | *your address* |
| University (Primary Author) | *your school's name* — the form says University; for a secondary-school entrant this is the school |
| Graduation Year (Primary Author) | *your year* |
| Secondary Author fields | leave blank, single author |
| Submission Title | Does a tyre-degradation model transfer? Cross-championship evidence and a retrospective audit of 1,280 real pit-stop decisions |
| Sport | Motorsport (Formula 1 and endurance racing) |
| Keywords | race strategy; tyre degradation; out-of-sample validation; motorsport analytics; Formula 1; endurance racing; pit stop optimisation; retrospective audit |
| Abstract | paste the abstract from the compiled PDF |
| Upload | the compiled PDF |
| Formatting guidelines followed? | Yes |

The upload accepts `pdf`, `txt` and `docx`. The guidelines prefer LaTeX and ask
for the raw `.tex` alongside the PDF, but the form takes one file and does not
list `.tex`. Upload the PDF, and offer the source if they ask: `main.tex` is in
the repository and in the Overleaf bundle.

---

## Why are you submitting your research to the Wharton Sports Analytics Journal?

> I built one protocol to ask two questions the motorsport-strategy literature
> mostly does not, and applied it to seven car classes across four
> championships — Formula 1, WEC, IMSA and ELMS — using only public timing
> data. Does a fitted tyre-degradation model predict a season it has never
> seen? And does its recommendation resemble what a professional team actually
> did?
>
> Four findings came back, three of them negative. But the part I would most
> want a reviewer to look at is a result I had to take apart myself. Degradation
> slopes transfer as a property of the circuit-class rather than the
> championship, and transfer is rare: 5 of 51 circuit-classes reach a
> within-stint R² of 0.2 under leave-one-race-out. Two researchers who read a
> draft pointed out that this count cannot mean what I was using it to mean. A
> low out-of-sample score has two explanations that are identical from outside:
> the slope moved between seasons, or it never moved and sits under lap noise
> too large for any protocol to recover.
>
> So I built the null. Lap times are rebuilt from each circuit's own fit with
> one degradation slope shared by every season — stable by construction — plus
> residuals resampled in whole stints to keep their within-stint correlation,
> and the real protocol is run on that. At 18 of 22 Formula 1 circuits a
> perfectly stable slope could not have cleared the threshold I was quoting; the
> achievable ceiling runs from +0.005 at Silverstone to +0.420 at Jeddah.
> Measuring the gap instead of the raw score leaves 8 circuits genuinely
> unstable, 3 stable once noise is priced in, and 7 carrying no recoverable
> signal at all. The finding survives in a narrower and more useful form, and
> the paper now says so where it previously implied that instability was close
> to universal.
>
> Whether an extra pit stop can ever pay is set by the cost of the stop rather
> than by the car: across 205 race-seasons, pit loss alone separates the two
> regimes at an AUC of 0.977 against 0.865 for degradation. That comparison
> drew two objections and both have measurements rather than arguments.
> Standardising pit loss leaves the AUC at 0.977 — a Mann-Whitney statistic is
> computed from ranks, so rescaling cannot reach it. And the separation is not
> class identity in disguise: class means alone score 0.760, 92% of pit-loss
> variance is within class rather than between, and the separation holds inside
> every class where both regimes occur, between 0.963 and 1.000.
>
> Replaying 1,280 real first pit stops, a time-optimal planner stops later than
> teams did on 80% of Formula 1 decisions, by a median of 12 laps, with a
> race-clustered interval of [+8.0, +11.5]. Two of the seven class medians have
> intervals containing zero, so the disagreement is established in Formula 1 and
> all three IMSA classes and not established in WEC Hypercar or ELMS LMP2. Four
> candidate explanations have been tested and none accounts for the magnitude.
> The fourth is the one both readers proposed as the answer — that a linear
> slope misses the immediate gain from a fresh tyre — and it comes back with the
> wrong sign: residuals at the youngest measured tyre age are +0.187s, so new
> tyres are slower than the fit expects for the first two laps. That is warm-up,
> and correcting for it widens the gap rather than closing it.
>
> The fourth is the one I would point a reviewer at. The rival that a
> competition-aware model should respond to turns out to be under-determined:
> four defensible selection rules name the same car on 17 of 271 decisions. Two
> of those rules did not come from me. One is forced by the structure of a
> published model, and one was proposed in correspondence by an author of the
> game-theoretic treatment my own adversarial component reuses. That branch of
> the literature rests on a two-car abstraction, and nobody has measured whether
> those two cars can be identified in a real race. On this evidence they cannot
> be identified uniquely, which constrains a family of models rather than only
> mine.
>
> I am sending it here because this is a sports-analytics result before it is a
> motorsport one, and because the journal publishes work by people at my stage.
>
> Everything is reproducible. The manuscript contains no numbers of its own:
> every quantity is generated from committed artifacts by a script in a public
> repository, and continuous integration fails on any difference between what
> the repository holds and what the code regenerates. Three layers read a
> third-party export I cannot redistribute; the paper names them and says which
> published claim one of them carries.
>
> Repository: https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab
> Archived and citable: https://doi.org/10.5281/zenodo.22726130

---

## Declarations, if a field asks

The work is my own, it is not under review elsewhere, and it has not been
published before. There are no conflicts of interest and no funding to declare.
