# Working rules for this repository

Three rules, set by the project owner on 5 September 2026. They apply to every
session, not just the one that established them.

## 1. Write the handover before compacting

Before any context compaction, write a full summary of the session: files
touched, decisions taken, numbers that moved, what is still open. Important work
has already been lost to a compaction once. Do not let it happen again.

## 2. Stop and report at the end of every block

At the end of each block of work, stop. Write down what changed, why, what it
breaks or might break, and what the owner needs to verify themselves. Then wait
for approval before starting the next block. These are stop-gates, the same way
phases 0–7 were.

## 3. Write like a person

This matters for every piece of text produced here — README, reports, the site,
emails, commit messages.

What gives generated prose away, and what to stop doing:

- an em-dash aside in every paragraph
- the "not X, but Y" construction
- the two-beat sentence with a colon announcing a revelation
- section headings built to one mould ("X, and what it caught", "Y, and both
  failed") — it becomes a tic and it shows across a whole page
- bold placed mid-sentence to make a phrase land
- paragraphs of even length, ticking like a metronome

Write instead the way someone explains their own work: uneven sentence lengths,
some short, ordinary transitions, less staging. "This is the strongest result"
reads fine without the bold.

**Never soften a caveat while rewriting.** Numbers, intervals, reservations and
limitations stay exactly as strong as they were. If a passage said a result was
uncertain, it says so just as plainly afterwards.

## A standing constraint that predates these

No fabricated data, ever. A number enters a report, the paper, the site or an
email only if it comes from a committed artifact or a verified source. This is
the rule the project has broken most often, always by typing a number instead of
deriving one, and every guard in `tests/test_paper_claims.py`,
`tests/test_paper_numbers.py` and `tests/test_site.py` exists because of it.
