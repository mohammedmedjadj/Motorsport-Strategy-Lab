"""Identification checks a reviewer asks for before trusting Result 1 or Result 3.

Five questions, each answered on the committed data and the same seasons as the
paper (Formula 1 before the 2026 rules):

1. **How much does the slope really move between seasons?** The within-stint
   R² threshold answers that only indirectly. Here each circuit-compound gets one
   slope per season, with its driver-race-clustered standard error, and the
   between-season variance is estimated directly (DerSimonian--Laird tau², with
   a Q-profile interval, Cochran's Q and I²). Each season is one race, so tau²
   is the variance of the slope between races -- track temperature, weather,
   track evolution and everything else a race shares. The same is done for the
   endurance circuit-classes, whose model has one net slope.

2. **Does track temperature explain that movement?** A meta-regression of the
   season slopes on the race's median track temperature, with one intercept per
   circuit-compound, reports the slope change per degree and the share of tau²
   it removes. A leave-one-season-out repair that adds tyre age x track
   temperature to the model, with the held-out race's own temperature, is scored
   on the same within-stint R² as Result 1.

3. **Do first stints wear faster?** A heavy car may use its tyres harder. The
   circuit model is refitted with a separate slope for the first stint and for
   later stints of each compound, and the closed-form stop lap is recomputed with
   the first-stint slope for the tyre the car is on and the later-stint slope for
   the one it fits.

4. **How far does the planner extrapolate?** Long stints are observed only on
   cars whose tyres held. If the planner recommends stopping at a tyre age no
   car reached on that compound at that circuit, its recommendation rests on the
   linear extrapolation, not on data.

5. **How wide should the slope uncertainty be?** The random-effects standard
   error of each circuit-compound mean (sampling plus between-race variance) is
   compared with the driver-race-clustered one the engine draws from.

Writes ``data/derived/f1/identification_checks_summary.json``,
``data/derived/f1/variance_components.csv`` and
``reports/f1/identification_checks.md``.

    python scripts/run_identification_checks.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from src.degradation.dataset import build_modelling_frame, circuits_with_laps, load_circuit_laps  # noqa: E402
from src.degradation.model import _design_matrix, fit_circuit  # noqa: E402
from src.degradation.robust import cluster_robust_se  # noqa: E402
from src.ingestion.config import DERIVED_DIR, F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
CEILING = F1_DERIVED_DIR / "transfer_ceiling.csv"
DECISIONS = F1_DERIVED_DIR / "audit_design_checks.csv"
COMMITTED = F1_DERIVED_DIR / "committed_strategy.csv"
END_CEILING = DERIVED_DIR / "endurance" / "endurance_ceiling.csv"
OUT_JSON = F1_DERIVED_DIR / "identification_checks_summary.json"
OUT_CSV = F1_DERIVED_DIR / "variance_components.csv"
OUT_END_CSV = DERIVED_DIR / "endurance" / "variance_components.csv"
OUT_MD = REPORTS_DIR / "f1" / "identification_checks.md"

#: A season slope enters only if it rests on this many driver-races.
MIN_CLUSTERS = 4
#: A circuit-compound enters the between-season analysis with this many seasons.
MIN_SEASONS = 3
#: A circuit-class needs at least two seasons for Q to have a degree of freedom.
MIN_SEASONS_ENDURANCE = 2
BOOT_SEED = 20261110
BOOT_DRAWS = 10_000

warnings.filterwarnings("ignore", message=".*not ingested yet.*")


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


# --------------------------------------------------------------------------
# Random-effects machinery
# --------------------------------------------------------------------------
def random_effects(y: np.ndarray, v: np.ndarray) -> dict:
    """DerSimonian--Laird tau², Cochran's Q, I² and a Q-profile 95% interval."""
    y, v = np.asarray(y, float), np.asarray(v, float)
    k = len(y)
    w = 1.0 / v
    mu_fe = float(np.sum(w * y) / np.sum(w))
    q = float(np.sum(w * (y - mu_fe) ** 2))
    c = float(np.sum(w) - np.sum(w**2) / np.sum(w))
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    i2 = max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0

    def q_gen(t2: float) -> float:
        ww = 1.0 / (v + t2)
        m = np.sum(ww * y) / np.sum(ww)
        return float(np.sum(ww * (y - m) ** 2))

    hi_crit, lo_crit = stats.chi2.ppf(0.975, k - 1), stats.chi2.ppf(0.025, k - 1)
    big = 1e4 * (np.var(y) + np.max(v))

    def solve(target: float) -> float:
        if q_gen(0.0) <= target:
            return 0.0
        return float(optimize.brentq(lambda t: q_gen(t) - target, 0.0, big))

    tau2_lo, tau2_hi = solve(hi_crit), solve(lo_crit)
    ws = 1.0 / (v + tau2)
    mu = float(np.sum(ws * y) / np.sum(ws))
    return {
        "k": k, "q": q, "q_p": float(stats.chi2.sf(q, k - 1)), "i2": i2,
        "tau2": tau2, "tau2_lo": tau2_lo, "tau2_hi": tau2_hi,
        "mu": mu, "mu_se_re": float(np.sqrt(1.0 / np.sum(ws))),
        "mu_se_fe": float(np.sqrt(1.0 / np.sum(w))),
    }


def meta_regression(frame: pd.DataFrame, moderator: str | None) -> dict:
    """Method-of-moments residual tau² with one intercept per group.

    ``frame`` has columns group, y, v and, optionally, the moderator. The
    residual heterogeneity Q_E is computed under fixed-effect weights and
    converted to tau² with the general DerSimonian--Laird constant, which is
    what metafor's ``method="DL"`` does for a meta-regression.
    """
    groups = pd.get_dummies(frame["group"]).to_numpy(dtype=float)
    parts = [groups]
    if moderator is not None:
        x = frame[moderator] - frame.groupby("group")[moderator].transform("mean")
        parts.append(x.to_numpy(dtype=float)[:, None])
    X = np.hstack(parts)
    y = frame["y"].to_numpy(dtype=float)
    v = frame["v"].to_numpy(dtype=float)
    W = np.diag(1.0 / v)
    xtwx_inv = np.linalg.pinv(X.T @ W @ X)
    b = xtwx_inv @ X.T @ W @ y
    resid = y - X @ b
    q_e = float(resid @ W @ resid)
    df = len(y) - np.linalg.matrix_rank(X)
    p = W - W @ X @ xtwx_inv @ X.T @ W
    tau2 = max(0.0, (q_e - df) / float(np.trace(p)))
    out = {"tau2": tau2, "q_e": q_e, "df": int(df)}
    if moderator is not None:
        Ws = np.diag(1.0 / (v + tau2))
        cov = np.linalg.pinv(X.T @ Ws @ X)
        bs = cov @ X.T @ Ws @ y
        out["theta"] = float(bs[-1])
        out["theta_se"] = float(np.sqrt(cov[-1, -1]))
    return out


# --------------------------------------------------------------------------
# 1, 2 and 5 -- Formula 1 season slopes
# --------------------------------------------------------------------------
def season_slopes() -> pd.DataFrame:
    """One linear slope per circuit, compound and season, with its race's temperature."""
    rows = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
        frame, _ = build_modelling_frame(laps, circuit)
        for season, part in frame.groupby("season"):
            if part["driver_race"].nunique() < MIN_CLUSTERS:
                continue
            fit = fit_circuit(part, circuit, degree=1)
            temp = float(part["track_temp_c"].median())
            for compound, coefs in fit.deg_coefs.items():
                c = coefs[0]
                n_dr = part.loc[part["Compound"] == compound, "driver_race"].nunique()
                if n_dr < MIN_CLUSTERS or not np.isfinite(c.se) or c.se <= 0:
                    continue
                rows.append({
                    "circuit": circuit, "compound": compound, "season": int(season),
                    "slope": c.value, "se": c.se, "n_driver_races": int(n_dr),
                    "track_temp_c": temp,
                })
    return pd.DataFrame(rows)


def variance_components(slopes: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    coefs = pd.read_csv(COEFS)
    published = coefs.set_index(["circuit", "compound"])["deg_p1_se"]
    ceiling = pd.read_csv(CEILING)
    ceiling = ceiling[ceiling["verdict"].notna()].set_index("circuit")["verdict"]
    rows = []
    for (circuit, compound), g in slopes.groupby(["circuit", "compound"]):
        if len(g) < MIN_SEASONS:
            continue
        re = random_effects(g["slope"].to_numpy(), g["se"].to_numpy() ** 2)
        rows.append({
            "circuit": circuit, "compound": compound, **re,
            "tau": float(np.sqrt(re["tau2"])),
            "tau_lo": float(np.sqrt(re["tau2_lo"])), "tau_hi": float(np.sqrt(re["tau2_hi"])),
            "tau_over_mu": float(np.sqrt(re["tau2"]) / abs(re["mu"])) if re["mu"] != 0 else np.nan,
            "published_se": float(published.get((circuit, compound), np.nan)),
            "verdict": ceiling.get(circuit, np.nan),
        })
    vc = pd.DataFrame(rows)
    vc["se_inflation"] = vc["mu_se_re"] / vc["published_se"]
    het = vc["q_p"] < 0.05
    by_verdict = (
        vc.groupby("verdict")["i2"].median().round(3).to_dict() if vc["verdict"].notna().any() else {}
    )
    rng = np.random.default_rng(BOOT_SEED)
    circuits = vc["circuit"].unique()

    def med(frame: pd.DataFrame, col: str) -> float:
        return float(frame[col].median())

    def boot(col: str) -> list[float]:
        draws = []
        for _ in range(BOOT_DRAWS):
            pick = rng.choice(circuits, len(circuits))
            draws.append(med(pd.concat([vc[vc["circuit"] == c] for c in pick]), col))
        return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]

    summary = {
        "n": int(len(vc)), "n_circuits": int(vc["circuit"].nunique()),
        "n_heterogeneous": int(het.sum()),
        "i2_median": med(vc, "i2"), "i2_median_ci": boot("i2"),
        "n_i2_above_half": int((vc["i2"] > 0.5).sum()),
        "tau_over_mu_median": med(vc, "tau_over_mu"), "tau_over_mu_ci": boot("tau_over_mu"),
        "n_tau_ci_excludes_zero": int((vc["tau2_lo"] > 0).sum()),
        "n_tau_ci_upper_above_half_mu": int((np.sqrt(vc["tau2_hi"]) > 0.5 * vc["mu"].abs()).sum()),
        "se_inflation_median": med(vc, "se_inflation"),
        "se_inflation_max": float(vc["se_inflation"].max()),
        "i2_by_verdict": by_verdict,
    }
    return vc, summary


def temperature_meta(slopes: pd.DataFrame) -> dict:
    """How much of the between-race variance does track temperature remove?"""
    keep = slopes.groupby(["circuit", "compound"])["season"].transform("size") >= MIN_SEASONS
    f = slopes[keep].copy()
    f["group"] = f["circuit"] + "|" + f["compound"]
    f["y"], f["v"] = f["slope"], f["se"] ** 2
    base = meta_regression(f, None)
    with_t = meta_regression(f, "track_temp_c")
    spread = f.groupby("group")["track_temp_c"].agg(lambda s: s.max() - s.min())
    return {
        "n_slopes": int(len(f)), "n_groups": int(f["group"].nunique()),
        "tau2_base": base["tau2"], "tau2_temp": with_t["tau2"],
        "share_removed": 1.0 - with_t["tau2"] / base["tau2"] if base["tau2"] > 0 else 0.0,
        "theta_per_10c": 10 * with_t["theta"], "theta_per_10c_se": 10 * with_t["theta_se"],
        "temp_range_median_c": float(spread.median()),
    }


# --------------------------------------------------------------------------
# 2b -- the temperature repair, scored like Result 1
# --------------------------------------------------------------------------
def _temp_design(df: pd.DataFrame, compounds: tuple[str, ...], t_ref: float) -> np.ndarray:
    X, _ = _design_matrix(df, compounds, 1)
    t = (df["track_temp_c"].to_numpy(dtype=float) - t_ref)
    age = df["TyreLife"].to_numpy(dtype=float)
    extra = [t[:, None]]
    for c in compounds:
        mask = (df["Compound"] == c).to_numpy(dtype=float)
        extra.append((mask * age * t)[:, None])
    return np.hstack([X] + extra)


def _within_r2(test: pd.DataFrame, shape: np.ndarray) -> float:
    s = pd.Series(shape, index=test.index)
    actual = test["lap_time_s"] - test.groupby("stint_id")["lap_time_s"].transform("mean")
    pred = s - s.groupby(test["stint_id"]).transform("mean")
    ss_tot = float((actual**2).sum())
    return 1.0 - float(((actual - pred) ** 2).sum()) / ss_tot if ss_tot > 0 else np.nan


def _pooled_theta(slopes: pd.DataFrame, exclude_circuit: str) -> float:
    """Temperature sensitivity of the slope, estimated without one circuit."""
    keep = slopes.groupby(["circuit", "compound"])["season"].transform("size") >= MIN_SEASONS
    f = slopes[keep & (slopes["circuit"] != exclude_circuit)].copy()
    f["group"] = f["circuit"] + "|" + f["compound"]
    f["y"], f["v"] = f["slope"], f["se"] ** 2
    return meta_regression(f, "track_temp_c")["theta"]


def temperature_repair(slopes: pd.DataFrame) -> pd.DataFrame:
    """Two repairs scored like Result 1, on the circuits with a ceiling verdict.

    *Own*: the circuit model plus temperature and tyre age x temperature per
    compound, fitted on the training races. *Category*: the published linear
    model, with every compound slope shifted by a temperature sensitivity
    estimated on the other circuits' season slopes, at the held-out race's own
    temperature. The first is what a team would fit; the second borrows the
    sensitivity from the whole calendar, which three training races cannot pin
    down on their own.
    """
    ceiling = pd.read_csv(CEILING)
    sane = set(ceiling.loc[ceiling["sane"].fillna(False).astype(bool), "circuit"])
    rows = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in sane:
            continue
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        if frame["race"].nunique() < 3:
            continue
        theta = _pooled_theta(slopes, circuit)
        base_scores, temp_scores, cat_scores = [], [], []
        for race in sorted(frame["race"].unique()):
            train, test = frame[frame["race"] != race], frame[frame["race"] == race]
            compounds = tuple(sorted(train["Compound"].unique()))
            test = test[test["Compound"].isin(compounds)]
            if test.empty:
                continue
            n_fe = train["driver_race"].nunique()
            y = train["lap_time_s"].to_numpy(dtype=float)
            t_ref = float(train["track_temp_c"].mean())
            # Baseline: the published linear model.
            Xb, _ = _design_matrix(train, compounds, 1)
            bb = _ols(Xb, y)[n_fe:]
            # Repair: plus temperature and tyre age x temperature per compound.
            Xt = _temp_design(train, compounds, t_ref)
            bt = _ols(Xt, y)[n_fe:]
            Xtest_b, _ = _design_matrix(test.assign(driver_race="x"), compounds, 1)
            Xtest_t = _temp_design(test.assign(driver_race="x"), compounds, t_ref)
            base_scores.append(_within_r2(test, Xtest_b[:, 1:] @ bb))
            temp_scores.append(_within_r2(test, Xtest_t[:, 1:] @ bt))
            # Category sensitivity: shift every compound slope by theta x dT.
            dt = float(test["track_temp_c"].median()) - t_ref
            shift = theta * dt * test["TyreLife"].to_numpy(dtype=float)
            cat_scores.append(_within_r2(test, Xtest_b[:, 1:] @ bb + shift))
        rows.append({"circuit": circuit, "r2_base": float(np.nanmean(base_scores)),
                     "r2_temp": float(np.nanmean(temp_scores)),
                     "r2_category_temp": float(np.nanmean(cat_scores))})
    out = pd.DataFrame(rows)
    out["difference"] = out["r2_temp"] - out["r2_base"]
    out["difference_category"] = out["r2_category_temp"] - out["r2_base"]
    return out


# --------------------------------------------------------------------------
# 3 -- first stint against later stints
# --------------------------------------------------------------------------
def first_stint() -> dict:
    degrees = pd.read_csv(COEFS).groupby("circuit")["degree"].first()
    fits, diffs = {}, []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in degrees.index or int(degrees[circuit]) != 1:
            continue
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        compounds = tuple(sorted(frame["Compound"].unique()))
        fe = pd.get_dummies(frame["driver_race"]).to_numpy(dtype=float)
        n_fe = fe.shape[1]
        age = frame["TyreLife"].to_numpy(dtype=float)
        first = (frame["Stint"] == 1).to_numpy(dtype=float)
        cols, names = [fe, frame["LapNumber"].to_numpy(dtype=float)[:, None]], []
        for c in compounds:
            m = (frame["Compound"] == c).to_numpy(dtype=float)
            for tag, sel in (("first", first), ("later", 1 - first)):
                col = m * sel * age
                if col.any():
                    cols.append(col[:, None])
                    names.append((c, tag))
        X = np.hstack(cols)
        y = frame["lap_time_s"].to_numpy(dtype=float)
        b = _ols(X, y)
        se, g = cluster_robust_se(X, y, b, frame["driver_race"].to_numpy())
        coef = {n: (b[n_fe + 1 + j], se[n_fe + 1 + j]) for j, n in enumerate(names)}
        pooled = _ols(_design_matrix(frame, compounds, 1)[0], y)[n_fe + 1:]
        fits[circuit] = {"split": coef, "pooled": dict(zip(compounds, pooled))}
        crit = stats.t.ppf(0.975, g - 1)
        for c in compounds:
            if (c, "first") in coef and (c, "later") in coef:
                d = coef[(c, "first")][0] - coef[(c, "later")][0]
                # Conservative: the two slopes treated as independent.
                s = np.hypot(coef[(c, "first")][1], coef[(c, "later")][1])
                diffs.append({"circuit": circuit, "compound": c, "difference": d,
                              "significant": abs(d) > crit * s})
    d = pd.DataFrame(diffs)

    dec = pd.read_csv(DECISIONS)
    dec = dec[(dec["lookback"] == 5) & dec["top"] & (dec["compound"] != dec["target"])]
    rows = []
    for r in dec.itertuples():
        f = fits.get(r.circuit)
        if f is None:
            continue
        split, pooled = f["split"], f["pooled"]
        if (r.compound, "first") not in split or (r.target, "later") not in split:
            continue
        if r.compound not in pooled or r.target not in pooled:
            continue
        w = r.horizon - r.decision_lap
        if w < 4:
            continue

        def best(old: float, new: float) -> int:
            k = np.arange(1, w)
            cost = old * np.array([np.sum(r.tyre_age + np.arange(1, j + 1)) for j in k]) + \
                new * np.array([np.sum(np.arange(1, w - j + 1)) for j in k])
            return int(k[np.argmin(cost)])

        real_k = r.real_pit_lap - r.decision_lap
        old_s, new_s = split[(r.compound, "first")][0], split[(r.target, "later")][0]
        rows.append({
            "one_stop": r.n_stops == 1,
            "pooled": best(pooled[r.compound], pooled[r.target]) - real_k,
            "split": best(old_s, new_s) - real_k,
            "ratio_pooled": pooled[r.compound] / pooled[r.target] if pooled[r.target] else np.nan,
            "ratio_split": old_s / new_s if new_s else np.nan,
        })
    g = pd.DataFrame(rows)
    one = g[g["one_stop"]]
    return {
        "n_pairs": int(len(d)), "n_first_steeper": int((d["difference"] > 0).sum()),
        "n_significant": int(d["significant"].sum()),
        "n_significant_steeper": int((d["significant"] & (d["difference"] > 0)).sum()),
        "median_difference": float(d["difference"].median()),
        "n_decisions": int(len(g)),
        "gap_pooled": float(g["pooled"].median()), "gap_split": float(g["split"].median()),
        "ratio_pooled_median": float(g["ratio_pooled"].median()),
        "ratio_split_median": float(g["ratio_split"].median()),
        "one_n": int(len(one)),
        "one_gap_pooled": float(one["pooled"].median()), "one_gap_split": float(one["split"].median()),
    }


# --------------------------------------------------------------------------
# 4 -- extrapolation beyond observed tyre ages
# --------------------------------------------------------------------------
def extrapolation() -> dict:
    observed: dict[tuple[str, str], tuple[float, float]] = {}
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
        laps = laps[laps["Compound"].isin(["SOFT", "MEDIUM", "HARD"])].dropna(subset=["TyreLife"])
        laps = laps.assign(stint_key=laps["race"] + laps["Driver"] + laps["Stint"].astype(str))
        ends = laps.groupby(["Compound", "stint_key"])["TyreLife"].max().reset_index()
        for compound, g in ends.groupby("Compound"):
            observed[(circuit, compound)] = (float(g["TyreLife"].max()),
                                             float(np.percentile(g["TyreLife"], 95)))
    dec = pd.read_csv(DECISIONS)
    dec = dec[(dec["lookback"] == 5) & dec["top"]]
    com = pd.read_csv(COMMITTED).dropna(subset=["committed_pit_lap"])
    m = dec.merge(com[["season", "circuit", "driver", "real_pit_lap", "committed_pit_lap"]],
                  on=["season", "circuit", "driver", "real_pit_lap"])
    rows = []
    for r in m.itertuples():
        key = (r.circuit, r.compound)
        if key not in observed:
            continue
        mx, p95 = observed[key]
        planner_age = r.tyre_age + (r.committed_pit_lap - r.decision_lap)
        real_age = r.tyre_age + (r.real_pit_lap - r.decision_lap)
        rows.append({"beyond_max": planner_age > mx, "beyond_p95": planner_age > p95,
                     "real_beyond_p95": real_age > p95, "n_stops": r.n_stops,
                     "gap": r.committed_pit_lap - r.real_pit_lap})
    e = pd.DataFrame(rows)
    one = e[e["n_stops"] == 1]
    inside = one[~one["beyond_p95"]]
    return {
        "one_gap_inside_p95": float(inside["gap"].median()), "one_n_inside_p95": int(len(inside)),
        "gap_inside_p95": float(e.loc[~e["beyond_p95"], "gap"].median()),
        "n_inside_p95": int((~e["beyond_p95"]).sum()),
        "n": int(len(e)),
        "pct_beyond_max": float(100 * e["beyond_max"].mean()),
        "pct_beyond_p95": float(100 * e["beyond_p95"].mean()),
        "pct_real_beyond_p95": float(100 * e["real_beyond_p95"].mean()),
        "one_n": int(len(one)),
        "one_pct_beyond_max": float(100 * one["beyond_max"].mean()),
        "one_pct_beyond_p95": float(100 * one["beyond_p95"].mean()),
    }


# --------------------------------------------------------------------------
# 1b -- endurance between-season variance
# --------------------------------------------------------------------------
def endurance_components() -> tuple[pd.DataFrame, dict]:
    from run_endurance_models import _frames  # noqa: E402
    from run_formal_tests import GT3_CLASSES  # noqa: E402
    from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402
    from src.degradation.endurance import fit_endurance_degradation  # noqa: E402

    verdicts = pd.read_csv(END_CEILING).set_index(["series", "event", "car_class"])["verdict"]
    rows = []
    for series, circuits in ENDURANCE_SCOPE.items():
        for cs in circuits:
            if len(cs.seasons) < MIN_SEASONS_ENDURANCE:
                continue
            frames = _frames(series, cs.event, cs.car_class, cs.seasons)
            ys, vs = [], []
            for frame in frames.values():
                if frame.empty or frame["car"].nunique() < MIN_CLUSTERS:
                    continue
                fit = fit_endurance_degradation(frame)
                if np.isfinite(fit.net_slope.se) and fit.net_slope.se > 0:
                    ys.append(fit.net_slope.value)
                    vs.append(fit.net_slope.se**2)
            if len(ys) < MIN_SEASONS_ENDURANCE:
                continue
            re = random_effects(np.array(ys), np.array(vs))
            rows.append({"series": series, "event": cs.event, "car_class": cs.car_class,
                         "gt3": cs.car_class in GT3_CLASSES, **re,
                         "tau": float(np.sqrt(re["tau2"])),
                         "verdict": verdicts.get((series, cs.event, cs.car_class), np.nan)})
    vc = pd.DataFrame(rows)
    summary = {
        "n": int(len(vc)), "n_three_plus": int((vc["k"] >= 3).sum()),
        "n_heterogeneous": int((vc["q_p"] < 0.05).sum()),
        "i2_median": float(vc["i2"].median()),
        "n_i2_above_half": int((vc["i2"] > 0.5).sum()),
        "n_tau_ci_excludes_zero": int((vc["tau2_lo"] > 0).sum()),
        "i2_by_verdict": vc.groupby("verdict")["i2"].median().round(3).to_dict(),
    }
    return vc, summary


def cancellation() -> dict:
    """Why the ceiling is low: within a stint, fuel burn and wear nearly cancel.

    The within-stint R² scores the net slope a stint shows -- tyre wear plus the
    fuel gain, which advance together inside a stint. Where they nearly cancel
    there is no within-stint shape to predict, whatever the slope does between
    seasons. This puts that reading to the data: the published fuel slope and
    median wear slope per circuit, their sum, and how closely its size ranks the
    ceiling.
    """
    coefs = pd.read_csv(COEFS)
    ceiling = pd.read_csv(CEILING)
    ceiling = ceiling[ceiling["sane"].fillna(False).astype(bool)].set_index("circuit")
    g = coefs.groupby("circuit").agg(fuel=("fuel_slope_s_per_lap", "first"),
                                     wear=("deg_p1", "median"), noise=("cv_rmse_s", "first"))
    g["net"] = g["fuel"] + g["wear"]
    m = g.join(ceiling[["ceiling_mean"]], how="inner")
    rho = stats.spearmanr(m["net"].abs(), m["ceiling_mean"])
    lowest = m["ceiling_mean"].idxmin()
    return {
        "n": int(len(m)), "fuel_median": float(m["fuel"].median()),
        "wear_median": float(m["wear"].median()), "net_abs_median": float(m["net"].abs().median()),
        "net_abs_over_wear": float((m["net"].abs() / m["wear"].abs()).median()),
        "rho": float(rho.statistic), "rho_p": float(rho.pvalue),
        "lowest": str(lowest), "lowest_net": float(m.loc[lowest, "net"]),
        "lowest_fuel": float(m.loc[lowest, "fuel"]), "lowest_wear": float(m.loc[lowest, "wear"]),
    }


def gt3_paired() -> dict:
    """GT3 against prototypes, paired on the events that run both.

    Classes at one event share its races, weather and track, so they are not
    exchangeable across events. Each event contributes one difference (mean GT3
    score minus mean prototype score), and the null is tested by flipping the
    sign of whole events -- exact, since there are few of them.
    """
    from run_formal_tests import GT3_CLASSES  # noqa: E402

    loro = pd.read_csv(DERIVED_DIR / "endurance" / "endurance_degradation_loro.csv")
    loro = loro[loro["held_out_season"].astype(str) == "MEAN"]
    ceil = pd.read_csv(END_CEILING)
    m = loro.merge(ceil[["series", "event", "car_class", "ceiling_mean", "verdict"]],
                   on=["series", "event", "car_class"], how="left")
    m = m[np.isfinite(m["r2_within"])]
    m["gt3"] = m["car_class"].isin(GT3_CLASSES)
    out = {}
    for name, col, frame in (
        ("measured", "r2_within", m),
        ("ceiling", "ceiling_mean", m[m["verdict"] != "degenerate fit, excluded"]),
    ):
        per = frame.groupby(["series", "event", "gt3"])[col].mean().unstack("gt3").dropna()
        d = (per[True] - per[False]).to_numpy()
        n = len(d)
        signs = np.array(np.meshgrid(*[[-1, 1]] * n)).reshape(n, -1).T if n <= 20 else None
        stat = abs(d.mean())
        null = np.abs((signs * d).mean(axis=1))
        rng = np.random.default_rng(BOOT_SEED)
        boot = [rng.choice(d, n).mean() for _ in range(BOOT_DRAWS)]
        out[name] = {"n_events": int(n), "mean_difference": float(d.mean()),
                     "ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                     "p_sign_flip": float((null >= stat - 1e-12).mean()),
                     "n_gt3_higher": int((d > 0).sum())}
    return out


def _f(x: float, d: int = 3) -> str:
    return f"{x:+.{d}f}"


def report(s: dict, vc: pd.DataFrame, temp_rep: pd.DataFrame) -> str:
    v, t, fs, ex, en = s["variance"], s["temperature"], s["first_stint"], s["extrapolation"], s["endurance"]
    tr = s["temperature_repair"]
    lines = [
        "# Identification checks", "",
        "Generated by `scripts/run_identification_checks.py`. Formula 1 uses the seasons",
        "before the 2026 rules only.", "",
        "## Why the ceiling is low", "",
        f"- Over {s['cancellation']['n']} circuits the median fuel slope is "
        f"{_f(s['cancellation']['fuel_median'], 3)} s/lap and the median wear slope "
        f"{_f(s['cancellation']['wear_median'], 3)}; their sum has a median size of "
        f"{s['cancellation']['net_abs_median']:.3f}. Its size ranks the ceiling with Spearman "
        f"{s['cancellation']['rho']:.2f} (p = {s['cancellation']['rho_p']:.1e}).", "",
        "## Between-season variance of the slope", "",
        f"- Formula 1: {v['n']} circuit-compounds with at least {MIN_SEASONS} season slopes, "
        f"{v['n_circuits']} circuits. Cochran's Q rejects equal slopes at 5% for {v['n_heterogeneous']}; "
        f"median I² {v['i2_median']:.2f} [{v['i2_median_ci'][0]:.2f}, {v['i2_median_ci'][1]:.2f}] "
        f"(circuits resampled); I² above one half for {v['n_i2_above_half']}.",
        f"- Between-race standard deviation tau as a share of the mean slope: median "
        f"{v['tau_over_mu_median']:.2f} [{v['tau_over_mu_ci'][0]:.2f}, {v['tau_over_mu_ci'][1]:.2f}]. "
        f"The Q-profile interval on tau excludes zero for {v['n_tau_ci_excludes_zero']} of {v['n']}.",
        f"- Median I² by ceiling verdict: {v['i2_by_verdict']}.",
        f"- Random-effects standard error of the circuit-compound mean over the published "
        f"driver-race-clustered one: median {v['se_inflation_median']:.2f}x, at most {v['se_inflation_max']:.1f}x.",
        f"- Endurance: {en['n']} circuit-classes with two or more seasons ({en['n_three_plus']} with three); "
        f"Q rejects at 5% for {en['n_heterogeneous']}, median I² {en['i2_median']:.2f}, "
        f"I² above one half for {en['n_i2_above_half']}. By ceiling verdict: {en['i2_by_verdict']}.", "",
        "## Track temperature", "",
        f"- Meta-regression over {t['n_slopes']} season slopes in {t['n_groups']} circuit-compounds: "
        f"{_f(t['theta_per_10c'], 4)} s/lap per 10 °C (SE {t['theta_per_10c_se']:.4f}); "
        f"between-race tau² {t['tau2_base']:.2e} without temperature, {t['tau2_temp']:.2e} with it, "
        f"{100 * t['share_removed']:.0f}% removed. Median within-circuit temperature range {t['temp_range_median_c']:.1f} °C.",
        f"- Leave-one-season-out with tyre age x track temperature, held-out race's own temperature: "
        f"median score {tr['median_temp']:.3f} against {tr['median_base']:.3f} for the linear model on "
        f"{tr['n']} circuits, median paired difference {_f(tr['median_difference'])} "
        f"[{_f(tr['ci'][0])}, {_f(tr['ci'][1])}], better at {tr['n_better']}.",
        f"- Linear model with every slope shifted by the temperature sensitivity estimated on the other "
        f"circuits: median score {tr['median_category']:.3f}, paired difference "
        f"{_f(tr['category']['median_difference'])} [{_f(tr['category']['ci'][0])}, "
        f"{_f(tr['category']['ci'][1])}], better at {tr['category']['n_better']}.", "",
        "## GT3 against prototypes, paired by event", "",
        *[f"- {k}: {g['n_events']} events, mean difference {_f(g['mean_difference'])} "
          f"[{_f(g['ci'][0])}, {_f(g['ci'][1])}], GT3 higher at {g['n_gt3_higher']}, "
          f"exact sign-flip p = {g['p_sign_flip']:.3f}" for k, g in s["gt3_paired"].items()], "",
        "## First stint against later stints", "",
        f"- {fs['n_pairs']} circuit-compounds with both: first stint steeper at {fs['n_first_steeper']}, "
        f"significant at {fs['n_significant']} ({fs['n_significant_steeper']} of them steeper); "
        f"median difference {_f(fs['median_difference'], 4)} s/lap per lap.",
        f"- Closed form on {fs['n_decisions']} decisions: median gap {fs['gap_pooled']:+.0f} laps with pooled slopes, "
        f"{fs['gap_split']:+.0f} with the first-stint slope for the old tyre; one-stop "
        f"({fs['one_n']}) {fs['one_gap_pooled']:+.0f} and {fs['one_gap_split']:+.0f}. Median slope ratio "
        f"{fs['ratio_pooled_median']:.2f} pooled, {fs['ratio_split_median']:.2f} split.", "",
        "## Extrapolation", "",
        f"- Of {ex['n']} committed recommendations, {ex['pct_beyond_max']:.0f}% stop at a tyre age beyond "
        f"the oldest stint observed on that compound at that circuit, {ex['pct_beyond_p95']:.0f}% beyond the "
        f"95th percentile of observed stint lengths (real stops: {ex['pct_real_beyond_p95']:.0f}%). One-stop "
        f"({ex['one_n']}): {ex['one_pct_beyond_max']:.0f}% and {ex['one_pct_beyond_p95']:.0f}%.",
        f"- Median committed gap where the recommendation stays inside the 95th percentile: "
        f"{ex['gap_inside_p95']:+.0f} laps over {ex['n_inside_p95']}; one-stop {ex['one_gap_inside_p95']:+.0f} "
        f"over {ex['one_n_inside_p95']}.", "",
        "## Circuit-compound table", "",
        "| circuit | compound | seasons | mean slope | tau [95%] | I² | Q p | verdict |",
        "|---|---|---:|---:|---|---:|---:|---|",
    ]
    for r in vc.sort_values(["circuit", "compound"]).itertuples():
        lines.append(f"| {r.circuit} | {r.compound} | {r.k} | {r.mu:+.4f} | {r.tau:.4f} "
                     f"[{r.tau_lo:.4f}, {r.tau_hi:.4f}] | {r.i2:.2f} | {r.q_p:.3f} | {r.verdict} |")
    lines += ["", "## Temperature repair by circuit", "",
              "| circuit | linear | own temperature term | category sensitivity |",
              "|---|---:|---:|---:|"]
    for r in temp_rep.itertuples():
        lines.append(f"| {r.circuit} | {r.r2_base:+.3f} | {r.r2_temp:+.3f} | {r.r2_category_temp:+.3f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    slopes = season_slopes()
    vc, var_summary = variance_components(slopes)
    temp = temperature_meta(slopes)
    rep = temperature_repair(slopes)
    rng = np.random.default_rng(BOOT_SEED)

    def paired(col: str) -> dict:
        diffs = rep[col].to_numpy()
        boot = [np.median(rng.choice(diffs, len(diffs))) for _ in range(BOOT_DRAWS)]
        return {"median_difference": float(np.median(diffs)),
                "ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                "n_better": int((diffs > 0).sum()), "n_worse": int((diffs < 0).sum())}

    temp_repair = {
        "n": int(len(rep)), "median_base": float(rep["r2_base"].median()),
        "median_temp": float(rep["r2_temp"].median()),
        "median_category": float(rep["r2_category_temp"].median()),
        **paired("difference"),
        "category": paired("difference_category"),
    }
    fs = first_stint()
    ex = extrapolation()
    end_vc, end_summary = endurance_components()
    summary = {"variance": var_summary, "temperature": temp, "temperature_repair": temp_repair,
               "first_stint": fs, "extrapolation": ex, "endurance": end_summary,
               "gt3_paired": gt3_paired(), "cancellation": cancellation()}

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(x) for k, x in o.items()}
        if isinstance(o, list):
            return [clean(x) for x in o]
        if isinstance(o, float):
            return round(o, 6)
        return o

    OUT_JSON.write_text(json.dumps(clean(summary), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    vc.round(6).to_csv(OUT_CSV, index=False)
    end_vc.round(6).to_csv(OUT_END_CSV, index=False)
    slopes.round(6).to_csv(F1_DERIVED_DIR / "season_slopes.csv", index=False)
    OUT_MD.write_text(report(summary, vc, rep), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8").split("## Circuit-compound")[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
