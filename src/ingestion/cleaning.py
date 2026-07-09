"""Lap-data cleaning: exclusion flags and pace-lap selection.

Design principle: **never silently drop rows**. Every lap keeps a set of
boolean exclusion flags and a single derived ``is_pace_lap`` flag;
downstream models filter on it, and the data quality report accounts for
every excluded lap by reason. All functions are pure
DataFrame -> DataFrame transformations with no network access.

Flag semantics (a lap is a *pace lap* iff none of these is True):

- ``is_in_lap`` / ``is_out_lap``: pit entry/exit laps — distorted by the
  pit-lane delta, never representative of clean pace.
- ``is_missing_laptime``: no timing available for the lap.
- ``is_inaccurate``: FastF1's ``IsAccurate`` is False (known timing issues).
- ``is_wet_compound``: INTERMEDIATE/WET tyre — the MVP degradation model
  targets dry running (scope decision from Phase 0).
- ``is_non_green``: any track status other than all-clear during the lap
  (yellow, SC, VSC, red) — pace is not representative.
- ``is_unknown_status``: track status missing — conservatively excluded
  because green running cannot be confirmed.
- ``is_deleted``: lap time deleted by race control.

``stint_crosses_red_flag`` is informational, NOT a pace exclusion: it marks
every lap of any stint that contains a red flag, because tyres may be
changed for free during red flags, which weakens stint-level tyre-age
arithmetic (Phase 2 decides how to use it).
"""

from __future__ import annotations

import pandas as pd

WET_COMPOUNDS: tuple[str, ...] = ("INTERMEDIATE", "WET")
GREEN_STATUS = "1"
RED_FLAG_CODE = "5"

#: Flags whose True value removes a lap from pace analysis, in report order.
EXCLUSION_FLAGS: tuple[str, ...] = (
    "is_in_lap",
    "is_out_lap",
    "is_missing_laptime",
    "is_inaccurate",
    "is_wet_compound",
    "is_non_green",
    "is_unknown_status",
    "is_deleted",
)


def convert_lap_times(laps: pd.DataFrame) -> pd.DataFrame:
    """Add float-second columns for the timedelta timing fields.

    Derived data is stored as CSV, where timedeltas do not round-trip;
    plain float seconds are explicit and portable.
    """
    out = laps.copy()
    out["lap_time_s"] = out["LapTime"].dt.total_seconds()
    for source, target in (("Time", "time_s"), ("LapStartTime", "lap_start_time_s")):
        if source in out.columns:
            out[target] = out[source].dt.total_seconds()
    return out


def _status_str(track_status: pd.Series) -> pd.Series:
    """Track status as trimmed strings, with missing values as ''."""
    return track_status.fillna("").astype(str).str.strip().replace("nan", "")


def add_exclusion_flags(laps: pd.DataFrame) -> pd.DataFrame:
    """Compute all boolean exclusion flags (requires ``convert_lap_times``)."""
    out = laps.copy()
    out["is_in_lap"] = out["PitInTime"].notna()
    out["is_out_lap"] = out["PitOutTime"].notna()
    out["is_missing_laptime"] = out["lap_time_s"].isna()
    # astype("boolean") first: plain fillna on object dtype triggers pandas'
    # silent-downcasting FutureWarning.
    out["is_inaccurate"] = ~out["IsAccurate"].astype("boolean").fillna(False).astype(bool)
    out["is_wet_compound"] = out["Compound"].isin(WET_COMPOUNDS)

    status = _status_str(out["TrackStatus"])
    out["is_unknown_status"] = status == ""
    out["is_non_green"] = (status != "") & (status != GREEN_STATUS)

    if "Deleted" in out.columns:
        out["is_deleted"] = out["Deleted"].astype("boolean").fillna(False).astype(bool)
    else:
        out["is_deleted"] = False
    return out


def mark_red_flag_stints(laps: pd.DataFrame) -> pd.DataFrame:
    """Flag every lap of any (driver, stint) that contains a red flag."""
    out = laps.copy()
    red = _status_str(out["TrackStatus"]).str.contains(RED_FLAG_CODE, regex=False)
    out["stint_crosses_red_flag"] = red.groupby(
        [out["Driver"], out["Stint"]]
    ).transform("any")
    return out


def add_pace_lap_flag(laps: pd.DataFrame) -> pd.DataFrame:
    """Derive ``is_pace_lap``: True iff no exclusion flag is set."""
    out = laps.copy()
    out["is_pace_lap"] = ~out[list(EXCLUSION_FLAGS)].any(axis=1)
    return out


def attach_weather(laps: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Join the latest weather reading at or before each lap's end time.

    Weather is a ~1-minute-resolution session time series; ``merge_asof``
    (backward) gives each lap the most recent reading, which is the best
    available proxy without interpolation. Laps with no usable time key
    keep NaN weather.
    """
    out = laps.copy()
    weather_cols = {"AirTemp": "air_temp_c", "TrackTemp": "track_temp_c",
                    "Humidity": "humidity_pct", "Rainfall": "rainfall"}
    for target in weather_cols.values():
        out[target] = pd.NA

    if weather.empty or "Time" not in weather.columns or "Time" not in out.columns:
        return out

    wx = weather[["Time", *weather_cols]].dropna(subset=["Time"]).sort_values("Time")
    wx = wx.rename(columns=weather_cols)
    valid = out["Time"].notna()
    if not valid.any():
        return out

    merged = pd.merge_asof(
        out.loc[valid, ["Time"]].reset_index().sort_values("Time"),
        wx,
        on="Time",
        direction="backward",
    ).set_index("index")
    for target in weather_cols.values():
        out.loc[merged.index, target] = merged[target]
    return out


def clean_laps(laps: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning pipeline for one race's laps.

    Order matters: times first (flags depend on ``lap_time_s``), then flags,
    then the derived pace flag, then weather.
    """
    out = convert_lap_times(laps)
    out = add_exclusion_flags(out)
    out = mark_red_flag_stints(out)
    out = add_pace_lap_flag(out)
    out = attach_weather(out, weather)
    return out
