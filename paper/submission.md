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
> mostly does not, and applied it identically to seven car classes across four
> championships — Formula 1, WEC, IMSA and ELMS — using only public timing
> data. Does a fitted tyre-degradation model predict a season it has never
> seen? And does its recommendation resemble what a professional team actually
> did?
>
> Four findings came back, three of them negative. Degradation slopes transfer
> as a property of the circuit-class rather than the championship, and transfer
> is rare: 5 of 51 circuit-classes reach a within-stint R² of 0.2 under
> leave-one-race-out. A near-specification control field, where every car is
> the same chassis and engine with no Balance of Performance, fails exactly as
> the balanced fields do, which rules out heterogeneous machinery as the cause.
> Whether an extra pit stop can ever pay is set by the cost of the stop rather
> than by the car: across 205 race-seasons the class-level correlation between
> median pit loss and tyre-limited share is −0.982, and ranking race-seasons by
> pit loss alone separates the two regimes at an AUC of 0.977 against 0.865 for
> degradation. Replaying 1,280 real first pit stops, an exact optimiser stops
> later than teams did on 80% of Formula 1 decisions, by a median of 12 laps;
> three candidate explanations were tested and all three failed.
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
