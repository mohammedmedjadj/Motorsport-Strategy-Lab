# CSAS 2027 talk abstract

Connecticut Sports Analytics Symposium 2027, UConn. Talk abstracts close
**1 December 2026** through the Google Form on
<https://statds.org/events/csas2027/>; the page states no word limit. Written
from the paper of 11 November 2026; every figure below is in `paper/numbers.tex`.

**Title**

What public timing cannot identify about tyre wear, and what 1,280 real pit
stops reveal

**Abstract**

Race-strategy models are fitted and validated inside one championship. I apply
one protocol to seven car classes in Formula 1, WEC, IMSA and ELMS and ask two
validation questions: does a fitted tyre-degradation slope predict a season it
never saw, and does a time-optimal planner stop where teams stopped?

Transfer is mostly not measurable from public timing. Inside a stint the fuel
burned nearly cancels the tyre's wear, so even a slope stable by construction
could not reach a within-stint R² of 0.2 at 16 of 22 Formula 1 circuits; measured
directly as a variance component, the slope moves between races by about a third
of its mean.

Replaying 1,136 real first stops with each team's next stop held fixed, the
planner lands a median of +3 laps [+2, +4] from the Formula 1 team out of sample,
but a rule with no fitted quantity, balancing tyre age before that stop, does as
well: the agreement comes from the horizon.

What the stops do reveal is the compound difference the fit misses. Read as an
implied wear ratio, the ratio of a team's first stint to the next is 0.73
[0.68, 0.77] when it moves to a harder compound and 1.74 [1.43, 2.53] when it moves
to a softer one, on the side hardness predicts for 79% of decisions, against 48%
for the fitted slopes and 64% once each compound has its own baseline pace.

Code, data and a pre-registered prospective test:
<https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab>
