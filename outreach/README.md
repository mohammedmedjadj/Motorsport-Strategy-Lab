# Outreach pack

Everything needed to contact a researcher, an academic or a race engineer about
this project — written before the first contact rather than after, so that no
message goes out improvised.

| file | what it is |
|---|---|
| [`one_pager.md`](one_pager.md) | The project in one page: three results, one figure each, and what underwrites them. Export to PDF and attach. |
| [`questions.md`](questions.md) | Three methodological questions with a stated position and what would change it. This is the substance. |
| [`emails.md`](emails.md) | Three short contact variants — researcher, race engineer, academic — with a pre-send checklist. |
| [`targets.md`](targets.md) | Categories, how to identify the right person, and the tracking table. **Contains the literature-review step, which blocks everything else.** |
| [`fastf1_issue.md`](fastf1_issue.md) | A ready-to-file bug report against FastF1, with a fix proposal. |
| [`fastf1_repro.py`](fastf1_repro.py) | Self-contained reproduction for it — no project code, runs on a clean `pip install fastf1`. |

## Order of work

1. **File the FastF1 issue.** It is the only item here that depends on nobody
   else. A maintainer's response on a public tracker is third-party validation
   that no amount of internal testing substitutes for, and the reproduction is
   already written.
2. **Do the literature review** (`targets.md`). It gates the Variant A emails
   and section 1 of the paper.
3. **Contact categories 1 and 2** while the paper is still being written — a
   methods opinion is only useful before the methods are fixed.
4. **Contact category 3 after the DOI exists.**

## The two things not to get wrong

**Do not send a message containing a placeholder.** Every `[…]` in `emails.md`
is a detail that must be verified first, and the ones referring to someone's own
work are the whole reason the message gets a reply.

**Do not cite a paper you have not opened.** There is a list of five candidate
references in my planning notes and **not one of them has been verified against
a real publication record.** A citation to a paper that does not exist would do
more damage than the missing literature review it was meant to fix.

## What a reply is worth

The plan behind this pack treats a mentor as unlocking arXiv endorsement, and
that is true. It is not the main thing. The main thing is that two of this
project's three results are negative and one is measured-but-unexplained, and
**there is currently nobody outside this repository who has checked whether that
is honest work or a mistake.** A single serious reply changes that.
