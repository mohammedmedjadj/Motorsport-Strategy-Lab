# Third-party notices

This repository redistributes data derived from sources that are not its own.
`LICENSE` covers this project's code, models and derived output; it cannot and
does not relicense anything below.

The point of this file is the MIT permission notice. MIT grants redistribution
freely and asks one thing in return: *"The above copyright notice and this
permission notice shall be included in all copies or substantial portions of
the Software."* Naming the licence is attribution; reproducing the notice is the
condition. This repository, the Zenodo deposit and the Kaggle dataset all carry
substantial derived portions of an MIT-licensed source, so all three need it.

---

## Endurance timing — `tobil/imsa` on Hugging Face

**Licence: MIT.** Confirmed against the Hugging Face API: `cardData.license` is
`mit` and the repository carries the `license:mit` tag. MIT permits
redistribution, including of modified versions, provided the notice below
travels with it.

- Source: `hf://datasets/tobil/imsa/imsa.duckdb`, maintained by "tobil"
- Read by: [`src/data/endurance_loader.py`](src/data/endurance_loader.py)
- What this repository redistributes from it: the per-lap and per-race tables
  under `data/derived/imsa/`, `data/derived/wec/` and `data/derived/elms/` —
  reshaped, joined to weather, and annotated with stint and tyre-age columns
  this project computes, but carrying the upstream lap and sector times
  throughout. That is about 97 MB, roughly four fifths of `data/derived/` by
  volume, which is why the notice matters rather than being a formality.

### The notice itself is not yet reproduced here

> **Paste the upstream `LICENSE` verbatim in this block.** It is deliberately
> empty. MIT's copyright line names a holder and a year, and neither the
> `license: mit` tag nor the API field carries that text — they record which
> licence applies, not the notice it obliges you to reproduce. A copyright line
> written from memory attributes someone's work to the wrong name or year,
> which is worse than the gap it fills.
>
> Open the dataset's file listing on Hugging Face and look for `LICENSE`:
>
> - **If it is there**, copy it in full into this block. That discharges the
>   condition for the repository. Then add the same text to the Kaggle
>   dataset's description and to the Zenodo deposit, which carry the same data.
> - **If there is no `LICENSE` file**, say so here instead. A dataset tagged
>   MIT with no notice shipped has no notice to reproduce, and recording that
>   you checked is the honest end state. Attribution by name and link, which
>   this file already gives, is then what there is.

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
