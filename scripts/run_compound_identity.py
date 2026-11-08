"""Does coding the tyre by its real Pirelli compound make the slope transfer?

The Formula 1 degradation model carries one slope per compound *label*: Soft,
Medium, Hard. Those labels are relative. Pirelli nominates three of its range
for each race, and the same circuit can get a different three from one season
to the next: Interlagos had the C2-C4 in 2023, the C3-C5 in 2024 and the C2-C4
again in 2025, so "Medium" there was the C3, then the C4, then the C3. A model
that asks last season's Medium slope to predict this season's Medium is, at
those circuits, asking one rubber to predict another.

That is an alternative explanation for Result 1's low transfer, and it can be
tested directly: recode every lap to the compound Pirelli actually supplied and
rerun the same leave-one-race-out protocol.

- **The allocation.** ``data/reference/pirelli_compounds.csv`` gives the three
  compounds nominated for every race from 2022 to 2025, taken from the race
  articles on Wikipedia, which cite Pirelli. Pirelli's own press releases state
  the allocation in text for some races; where they do, the URL is recorded and
  the two agree in every case.
- **The 2023 rename.** Pirelli added a compound in 2023 and renamed the 2022 C1
  the C0, with a new C1 between it and the C2. A 2022 C1 lap is therefore coded
  C0 so that it is matched with the rubber it physically was, not with its
  name. Pirelli also revises formulations between seasons (a new C4 and C5 and
  the C6 in 2025); those changes are inside the label in both codings.
- **The same laps for both codings.** A held-out season can use a compound no
  training season used (the C6 at Monaco in 2025, for instance). The relative
  coding always has a training slope; the real one does not. Both codings are
  scored on the laps both can predict, and the share of laps the real coding
  cannot predict is reported in its own right: it is a cost of the recoding,
  not a detail.

Writes ``data/derived/f1/compound_identity.csv``, ``compound_identity_summary.json`` and
``reports/f1/compound_identity.md``.

    python scripts/run_compound_identity.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.degradation.dataset import (  # noqa: E402
    build_modelling_frame,
    circuits_with_laps,
    load_circuit_laps,
)
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

ALLOCATION = REPO / "data" / "reference" / "pirelli_compounds.csv"
CEILING = F1_DERIVED_DIR / "transfer_ceiling.csv"
OUT_CSV = F1_DERIVED_DIR / "compound_identity.csv"
OUT_SUMMARY = F1_DERIVED_DIR / "compound_identity_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "compound_identity.md"

BOOT_SEED = 20261107
BOOT_DRAWS = 10_000
ROLE = {"HARD": "hard", "MEDIUM": "medium", "SOFT": "soft"}


def load_allocation() -> pd.DataFrame:
    table = pd.read_csv(ALLOCATION)
    long = table.melt(
        id_vars=["season", "circuit"], value_vars=["hard", "medium", "soft"],
        var_name="role", value_name="compound",
    )
    # The 2022 C1 is the compound Pirelli renamed C0 for 2023.
    renamed = (long["season"] == 2022) & (long["compound"] == "C1")
    long.loc[renamed, "compound"] = "C0"
    return long


def recode(frame: pd.DataFrame, allocation: pd.DataFrame, circuit: str) -> pd.DataFrame:
    """The same frame with ``Compound`` replaced by the real compound."""
    alloc = allocation[allocation["circuit"] == circuit]
    lookup = {(int(r.season), r.role): r.compound for r in alloc.itertuples()}
    out = frame.copy()
    out["Compound"] = [
        lookup[(int(s), ROLE[c])] for s, c in zip(out["season"], out["Compound"])
    ]
    return out


def _demean(values: pd.Series, stints: pd.Series) -> pd.Series:
    return values - values.groupby(stints).transform("mean")


def _r2(actual: pd.Series, shape: pd.Series, stints: pd.Series) -> float:
    a = _demean(actual, stints)
    p = _demean(shape, stints)
    ss_tot = float((a**2).sum())
    return 1.0 - float(((a - p) ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")


def score_circuit(circuit: str, degree: int, allocation: pd.DataFrame) -> dict:
    laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
    relative, _ = build_modelling_frame(laps, circuit)
    real = recode(relative, allocation, circuit)
    rel_scores, real_scores, unseen = [], [], []
    for race in sorted(relative["race"].unique()):
        train_rel = relative[relative["race"] != race]
        train_real = real[real["race"] != race]
        test_rel = relative[relative["race"] == race]
        test_real = real[real["race"] == race]
        shape_rel = predict_shape(fit_circuit(train_rel, circuit, degree), test_rel)
        shape_real = predict_shape(fit_circuit(train_real, circuit, degree), test_real)
        both = shape_rel.notna() & shape_real.notna()
        unseen.append(float((shape_real.isna() & shape_rel.notna()).mean()))
        if both.sum() == 0:
            continue
        stints = test_rel.loc[both, "stint_id"]
        actual = test_rel.loc[both, "lap_time_s"]
        rel_scores.append(_r2(actual, shape_rel[both], stints))
        real_scores.append(_r2(actual, shape_real[both], stints))
    # Only seasons that reach the frame count: a wet race leaves no dry laps.
    raced = set(relative["season"].unique())
    seasons = allocation[(allocation["circuit"] == circuit) & allocation["season"].isin(raced)]
    trios = seasons.groupby("season")["compound"].apply(lambda s: "/".join(sorted(s)))
    return {
        "circuit": circuit,
        "seasons": int(relative["season"].nunique()),
        "degree": degree,
        "allocations": int(trios.nunique()),
        "allocation_changed": bool(trios.nunique() > 1),
        "r2_relative": float(np.nanmean(rel_scores)) if rel_scores else float("nan"),
        "r2_real": float(np.nanmean(real_scores)) if real_scores else float("nan"),
        "unseen_share": float(np.mean(unseen)),
    }


def bootstrap_median(values: np.ndarray, rng) -> tuple[float, float]:
    draws = np.median(rng.choice(values, size=(BOOT_DRAWS, len(values)), replace=True), axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def build() -> pd.DataFrame:
    allocation = load_allocation()
    degrees = pd.read_csv(CEILING).set_index("circuit")["degree"]
    rows = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in degrees.index:
            continue
        published = score_circuit(circuit, int(degrees[circuit]), allocation)
        linear = score_circuit(circuit, 1, allocation)
        published["r2_relative_linear"] = linear["r2_relative"]
        published["r2_real_linear"] = linear["r2_real"]
        rows.append(published)
    frame = pd.DataFrame(rows)
    # Result 1's own verdict per circuit: degenerate fits are excluded here
    # for the same reason they are excluded there.
    ceiling = pd.read_csv(CEILING)[["circuit", "sane", "verdict"]]
    frame = frame.merge(ceiling, on="circuit", how="left")
    frame["difference"] = frame["r2_real"] - frame["r2_relative"]
    frame["difference_linear"] = frame["r2_real_linear"] - frame["r2_relative_linear"]
    return frame


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    out = {}
    frame = frame[frame["verdict"].notna()]
    # Circuits with too few seasons for Result 1's ceiling carry no verdict and
    # are left out, as they are there.
    moved = frame[frame["allocation_changed"] & frame["verdict"].notna()]
    changed = moved[moved["sane"].fillna(False).astype(bool)]
    unstable = changed[changed["verdict"] == "slope unstable"]
    for name, part, suffix in (
        ("changed", changed, ""),
        ("changed_linear", changed, "_linear"),
        ("unstable", unstable, ""),
    ):
        diff = part["difference" + suffix].dropna().to_numpy()
        lo, hi = bootstrap_median(diff, rng)
        better, worse = int((diff > 0).sum()), int((diff < 0).sum())
        out[name] = {
            "n": int(len(diff)),
            "median_relative": float(part["r2_relative" + suffix].median()),
            "median_real": float(part["r2_real" + suffix].median()),
            "median_difference": float(np.median(diff)),
            "ci_low": lo,
            "ci_high": hi,
            "n_better": better,
            "n_worse": worse,
            "sign_p": float(binomtest(better, better + worse).pvalue) if better + worse else float("nan"),
            "max_difference": float(diff.max()),
            "min_difference": float(diff.min()),
        }
    out["n_circuits"] = int(len(frame))
    out["n_moved"] = int(len(moved))
    out["n_degenerate"] = int(len(moved) - len(changed))
    out["n_changed"] = int(len(changed))
    out["unseen_share"] = float(changed["unseen_share"].mean())
    out["unseen_max"] = float(frame["unseen_share"].max())
    return out


def report(frame: pd.DataFrame, stats: dict) -> str:
    c, l = stats["changed"], stats["changed_linear"]
    lines = [
        "<!-- GENERATED by scripts/run_compound_identity.py — do not edit by hand. -->",
        "",
        "# Relative compound labels against the real Pirelli compound",
        "",
        "Leave-one-race-out within-stint R², the Result 1 protocol at each",
        "circuit's published degree, with the tyre coded two ways: the relative",
        "label (Soft/Medium/Hard) and the compound Pirelli nominated (C0-C6, the",
        "2022 C1 coded C0). Both are scored on the same laps.",
        "",
        f"The allocation changed between seasons at {stats['n_moved']} of "
        f"{stats['n_circuits']} circuits; elsewhere the two codings are the same "
        f"model. {stats['n_degenerate']} of those are fits Result 1 excludes as "
        f"degenerate and are excluded here too. At the other {stats['n_changed']} "
        "the median score moves from "
        f"{c['median_relative']:.3f} to {c['median_real']:.3f}, a median difference of "
        f"{c['median_difference']:+.3f} (95% interval over circuits "
        f"[{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]). The real compound scores better "
        f"at {c['n_better']}, worse at {c['n_worse']} (sign test p = {c['sign_p']:.2f}), "
        f"and its largest gain anywhere is {c['max_difference']:+.3f}.",
        "",
        f"At the {stats['unstable']['n']} of them Result 1 calls unstable, the ones "
        "where a better coding had something to repair, the difference runs from "
        f"{stats['unstable']['min_difference']:+.3f} to "
        f"{stats['unstable']['max_difference']:+.3f} (median "
        f"{stats['unstable']['median_difference']:+.3f}).",
        "",
        "With every circuit forced to the linear model, so that no quadratic can",
        f"extrapolate on a compound seen in one season only: median difference "
        f"{l['median_difference']:+.3f} ([{l['ci_low']:+.3f}, {l['ci_high']:+.3f}]), "
        f"better at {l['n_better']}, worse at {l['n_worse']} (p = {l['sign_p']:.2f}).",
        "",
        f"On average {100 * stats['unseen_share']:.1f}% of a held-out season's laps at "
        "those circuits are on a compound no other season used (at most "
        f"{100 * stats['unseen_max']:.1f}% at one circuit), and the real coding cannot "
        "predict them at all.",
        "",
        "| circuit | Result 1 verdict | seasons | allocations | R², relative | R², real compound | difference | difference, linear | laps on an unseen compound |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in frame.sort_values("difference", ascending=False).itertuples():
        lines.append(
            f"| {r.circuit} | {r.verdict} | {r.seasons} | {r.allocations} | {r.r2_relative:.3f} | "
            f"{r.r2_real:.3f} | {r.difference:+.3f} | {r.difference_linear:+.3f} | "
            f"{100 * r.unseen_share:.1f}% |"
        )
    lines.append("")
    return "\n".join(lines)


def _json(stats: dict) -> str:
    """Rounded so the committed file does not churn on the last float digit."""
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        return round(v, 6) if isinstance(v, float) else v
    return json.dumps(clean(stats), indent=1, sort_keys=True) + "\n"


def main() -> int:
    warnings.filterwarnings("ignore")
    frame = build()
    stats = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    OUT_SUMMARY.write_text(_json(stats), encoding="utf-8")
    OUT_MD.write_text(report(frame, stats), encoding="utf-8")
    print(frame.to_string())
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
