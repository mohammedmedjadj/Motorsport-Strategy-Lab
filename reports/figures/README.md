# The figures, and the rule they are held to

Nine figures, all generated from committed artifacts by
[`make_headline_figures.py`](../../scripts/make_headline_figures.py) and
[`make_supporting_figures.py`](../../scripts/make_supporting_figures.py). Never
edited by hand — a figure that disagrees with its own data is the same defect as
a sentence that does, and it is harder to notice.

## The comparison rule

Set by the project owner, and it is methodological rather than cosmetic:

> Do not compare series or classes against each other on **performance**.
> Compare like with like — GTP against GTP, GTD against GTD — and within that,
> compare drivers, circuits and teams. For each class or series, compare only
> across the same modern seasons.
>
> The only figures showing all four series together should be about the
> accuracy of the audit or something of that order — **not about comparing
> performance**. And even there, the classes within a series must be
> distinguished.

Applying it properly found two figures that broke it, and fixing one of those
turned up something the old version had been hiding.

## The audit

| figure | verdict | why |
|---|---|---|
| `r1_transfer` | **complies** | Transfer is a property of the *model*, not the car. A GT3 car is not better than a prototype because its fitted slope predicts a held-out season; it means the slope is stable. Classes are distinguished by colour, which is what the rule asks. |
| `r2_pit_loss_rule` | **complies, and this is worth arguing** | See below. |
| `r3_audit_bias` | **broke the rule; fixed** | Four series on one axis is the allowed category — this is audit accuracy. But it pooled IMSA's three classes into one row, and the rule says the classes must be distinguished even there. Now split into seven class rows. |
| `s1_neutralisation_regimes` | **complies** | Share of races seeing a Safety Car is a property of a championship's race control, not of any car. Nothing about performance. |
| `s2_pit_loss_spectrum` | **complies, same argument as r2** | See below. |
| `s3_f1_degradation` | **complies** | Formula 1 only, per circuit and compound. Like with like throughout. |
| `s4_track_position` | **complies** | Formula 1 only, per circuit. Same. |
| `s5_baselines` | **broke the rule; fixed** | Same defect as r3, same fix. Now seven class rows. |
| `s6_intervals` | **complies** | GT3 against prototype is a group comparison, but on *transfer* — the stability of a fitted parameter — not on lap time or race result. The difference between the two groups is the published finding. |

## Why the pit-loss figures stand

The owner flagged `s2_pit_loss_spectrum` as the case to argue rather than
obey, since it puts seven classes from four championships on one axis. The
distinction holds, and here is the reasoning.

Pit loss is **procedural**, not competitive. It measures how long a car is
stationary and travelling at pit-lane speed — a function of the pit lane's
length, the speed limit, and what the rules require the crew to do while the car
is there. A GT3 stop is a tyre change. A prototype stop is a tank, a driver and
four tyres. Neither number says a car is quicker; they say the two
championships have written different rules about what happens in a pit box.

That distinction is exactly why the figure earns its place. The finding is that
this procedural quantity, which has nothing to do with how fast anything goes,
is what decides whether an extra stop can ever pay. Showing it *requires* the
classes on one axis, because the relationship between them is the result.
Splitting the figure into seven separate panels would destroy the thing it
exists to show.

The same reasoning covers `r2_pit_loss_rule`. Its left panel is six class
points; the correlation between them is result 2, and there is no way to draw a
correlation with each point on its own chart.

Two things keep this from being a loophole. Every point stays labelled with its
class, so nobody reads an unlabelled cloud. And no figure anywhere in this
repository puts lap times, race results, degradation slopes or driver
performance from different classes on one axis — those comparisons genuinely do
not mean anything, and none is drawn.

## What the fix to r3 uncovered

Splitting IMSA into its three classes changed what the figure says.

| | pooled | split |
|---|---|---|
| IMSA | +12 laps | GTP +9, GTD +12, GTD PRO +13 |

GTP has the dearest stops of the three and the *smallest* disagreement with real
practice. The pooled row averaged that away and reported a single IMSA number
describing none of the three. The same split applied to the baseline comparison
moved its headline from "a rule of thumb wins in three championships out of
four" to **"in five of the seven classes"** — more precise, and stronger.

Both figures had been generated, published and read for weeks with the pooling
in place. The rule caught it; nothing else did.

## Legibility

Fixed while auditing:

- Circuit names come through [`src/reporting/names.py`](../../src/reporting/names.py)
  rather than from slugs. `red_bull_ring` was reading as script output;
  `Red Bull Ring` reads as a figure. The same map handles COTA, VIR, Mid-Ohio
  and Gilles Villeneuve, where title-casing alone gets it wrong.
- `s3_f1_degradation` had two extremes stretching the axis until every other
  circuit sat in an unreadable band. The axis is clipped to where the mass is,
  points outside it are marked with an arrow at the edge, and their values are
  printed under the plot. Clipped, never silently dropped.
- `s2_pit_loss_spectrum` had a four-line callout sitting on top of the data it
  pointed at. The point now carries a mark and the explanation went below the
  axis.
- Titles and subtitles no longer collide anywhere.

## Adding a figure

Run it past the rule first. If it puts more than one class on an axis, it needs
to be measuring either the accuracy of a model or a procedural quantity, and it
needs to say which class every point belongs to.
