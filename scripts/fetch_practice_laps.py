"""Download the Friday long-run laps that ``run_practice_long_runs.py`` reads.

FastF1's timing source now needs an account, so the practice laps come from
the OpenF1 API (https://openf1.org), which serves the same timing feed from 2023
on. For every race weekend in the Formula 1 scope from 2023 to 2025 this takes
the second practice session, which is the one teams use for race-fuel long
runs; on a sprint weekend there is only one practice session and that one is
taken instead, and the session is recorded so the two kinds can be separated.

Writes ``data/derived/f1/practice_laps.csv``, which is committed so that the
analysis runs offline like every other layer.

    python scripts/fetch_practice_laps.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.ingestion.config import F1_DERIVED_DIR  # noqa: E402

API = "https://api.openf1.org/v1/"
SEASONS = (2023, 2024, 2025)
OUT = F1_DERIVED_DIR / "practice_laps.csv"

#: OpenF1 circuit names to this project's circuit keys.
CIRCUITS = {
    "Austin": "austin", "Baku": "baku", "Catalunya": "barcelona",
    "Hungaroring": "hungaroring", "Imola": "imola", "Interlagos": "interlagos",
    "Jeddah": "jeddah", "Las Vegas": "las_vegas", "Lusail": "losail",
    "Melbourne": "melbourne", "Mexico City": "mexico_city", "Miami": "miami",
    "Monte Carlo": "monaco", "Montreal": "montreal", "Monza": "monza",
    "Sakhir": "bahrain", "Shanghai": "shanghai", "Silverstone": "silverstone",
    "Singapore": "singapore", "Spa-Francorchamps": "spa", "Spielberg": "red_bull_ring",
    "Suzuka": "suzuka", "Yas Marina Circuit": "yas_marina", "Zandvoort": "zandvoort",
}


def get(endpoint: str, **params) -> list[dict]:
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 404:  # OpenF1's answer when a session has no rows
                return []
            time.sleep(3 * (attempt + 1))  # rate limit or transient failure
        except OSError:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"OpenF1 unreachable: {url}")


def practice_session(sessions: list[dict]) -> dict | None:
    named = {s["session_name"]: s for s in sessions if not s.get("is_cancelled")}
    if "Practice 2" in named and "Sprint" not in {s["session_name"] for s in sessions}:
        return named["Practice 2"]
    return named.get("Practice 1")


def session_laps(session: dict, circuit: str) -> pd.DataFrame:
    key = session["session_key"]
    laps = pd.DataFrame(get("laps", session_key=key))
    stints = pd.DataFrame(get("stints", session_key=key))
    time.sleep(0.5)
    if laps.empty or stints.empty:
        return pd.DataFrame()
    rows = []
    for lap in laps.itertuples():
        match = stints[
            (stints["driver_number"] == lap.driver_number)
            & (stints["lap_start"] <= lap.lap_number)
            & (stints["lap_end"] >= lap.lap_number)
        ]
        if match.empty:
            continue
        stint = match.iloc[0]
        rows.append({
            "season": session["year"],
            "circuit": circuit,
            "session": session["session_name"],
            "driver_number": int(lap.driver_number),
            "lap_number": int(lap.lap_number),
            "lap_time_s": lap.lap_duration,
            "is_pit_out_lap": bool(lap.is_pit_out_lap),
            "stint": int(stint["stint_number"]),
            "compound": stint["compound"],
            "tyre_age": int(stint["tyre_age_at_start"]) + int(lap.lap_number) - int(stint["lap_start"]),
        })
    return pd.DataFrame(rows)


def main() -> int:
    frames = []
    for season in SEASONS:
        sessions = get("sessions", year=season)
        by_meeting: dict[int, list[dict]] = {}
        for s in sessions:
            by_meeting.setdefault(s["meeting_key"], []).append(s)
        for meeting in by_meeting.values():
            circuit = CIRCUITS.get(meeting[0]["circuit_short_name"])
            names = {s["session_name"] for s in meeting}
            if circuit is None or "Race" not in names:
                continue
            session = practice_session(meeting)
            if session is None:
                continue
            laps = session_laps(session, circuit)
            print(season, circuit, session["session_name"], len(laps), flush=True)
            frames.append(laps)
    out = pd.concat(frames, ignore_index=True).sort_values(
        ["season", "circuit", "driver_number", "lap_number"]
    )
    out.to_csv(OUT, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
