# Third-party notices

This repository redistributes data derived from sources that are not its own.
`LICENSE` covers this project's code, models and derived output; it cannot and
does not relicense anything below.

MIT grants redistribution freely and asks one thing in return: *"The above
copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software."* Naming the licence is attribution;
reproducing the notice is the condition.

The largest source here is MIT and ships no notice to reproduce — checked, and
recorded below rather than assumed. So what this file actually carries is the
attribution that remains: who made what, where it came from before that, and
which link in each chain the licence covers. This repository, the Zenodo
deposit and the Kaggle dataset all redistribute the same derived files, so all
three point at it.

---

## Endurance timing — `tobil/imsa` on Hugging Face

**Licence: MIT.** Confirmed against the Hugging Face API: `cardData.license` is
`mit` and the repository carries the `license:mit` tag. MIT permits
redistribution, including of modified versions.

- Source: `hf://datasets/tobil/imsa/imsa.duckdb`, published on Hugging Face by
  `tobil` and curated by the IMSA Data Scraper Project
- Read by: [`src/data/endurance_loader.py`](src/data/endurance_loader.py)
- What this repository redistributes from it: the per-lap and per-race tables
  under `data/derived/imsa/`, `data/derived/wec/` and `data/derived/elms/` —
  reshaped, joined to weather, and annotated with stint and tyre-age columns
  this project computes, but carrying the upstream lap and sector times
  throughout. That is about 97 MB, roughly four fifths of `data/derived/` by
  volume, which is why the attribution below is load-bearing rather than a
  courtesy.

### There is no notice to reproduce, and that was checked

Verified on 13 September 2026. The dataset holds five files —
`.gitattributes`, `README.md`, `drivers.csv`, `imsa.duckdb` and `laps.csv` —
and **no `LICENSE`**. Its README carries no copyright line, no named holder and
no year.

So MIT's reproduction condition has nothing to attach to here. A dataset tagged
MIT that ships no notice leaves attribution by name and link as what there is,
and that is what this file gives. This paragraph is the record that the check
happened, so the next person does not have to repeat it or guess.

### Who to attribute, and to what

The dataset's own README is more specific than "a community-maintained
dataset", which is how this project described it for months:

| | |
|---|---|
| Curated by | IMSA Data Scraper Project |
| Source code | <https://github.com/tobi/imsa_data> |
| Upstream data | IMSA WeatherTech official results, <https://imsa.results.alkamelcloud.com/Results/> |

The chain is therefore **IMSA / Alkamel → the scraper → Hugging Face → here**,
and it matters that MIT sits at only one link of it. The MIT tag covers the
scraper project's own work. Whether it reaches the underlying timing data,
which originates with IMSA's results service and not with the scraper, is a
question this file does not answer and should not pretend to. Recorded as the
chain, not as a conclusion.

Note also the handles. The Hugging Face account is **`tobil`** and the GitHub
one is **`tobi`**, without the `l`. `hf://datasets/tobil/imsa/imsa.duckdb` in
`src/data/endurance_loader.py` is correct as written, and "correcting" it to
`tobi` breaks every endurance load.

### What the upstream asks that this file should carry

The dataset's README lists, under *Out-of-Scope Use*, commercial use without
proper attribution to IMSA and to the data sources. This project is
non-commercial and attributes both, so nothing here conflicts with it. It is
recorded because a reader taking this project's derived output onward inherits
that expectation, and they will not find it by reading `LICENSE`.

### This project's own licence does not reach it

`LICENSE` applies CC BY-NC-SA 4.0 to this project's contribution. It does not
apply to the upstream material, and the non-commercial restriction in
particular cannot be imposed on it: anyone is free to take the upstream dataset
from upstream under MIT and use it commercially. What CC BY-NC-SA covers is the
modelling, the code, the reports and this project's derived output as a
collection.

---

## Formula 1 timing — FastF1

**Licence: MIT**, for the library.

- Source: <https://github.com/theOehrly/Fast-F1>
- Used as a client at ingestion time. The library's own code is not
  redistributed here, so its MIT notice condition is not triggered by this
  repository.
- The F1 timing data FastF1 retrieves is a separate question from FastF1's own
  licence. This project is unaffiliated with Formula 1, the FIA or any team,
  uses no proprietary or non-public information, and redistributes derived
  measurements for independent research.

---

## Weather — Open-Meteo

Retrieved from the Open-Meteo archive API. Non-commercial use is free under
their terms; the derived per-race weather columns are what is committed here,
not a copy of their archive.

---

## The two exports under `data/external/` — still unresolved

**These are a different question from the endurance dataset above, and the MIT
finding does not settle them.** They are a relational Formula 1 history in the
Ergast schema and a results-level WEC history, both obtained from Kaggle, both
gitignored and not redistributed by this repository.

Their licences have not been recorded. See
[`data/external/README.md`](data/external/README.md), which describes what they
feed and what is blocked without them. Four committed files are derived from
them — `data/derived/f1/history_degradation.csv`,
`data/derived/f1/history_pit_loss.csv`, `data/derived/f1/reliability.csv` and
`data/derived/wec/reliability.csv` — and all four are aggregate statistics
rather than reshaped source rows, which is a materially weaker exposure than
the endurance case. Smaller, and still worth closing.
