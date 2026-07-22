"""Historical race-day weather from the Open-Meteo archive — the honest fix for
the missing-weather gap (documented for two IMSA circuits, but really a gap
anywhere the timing source ships no weather).

Open-Meteo's archive API is public and needs no key. Given a circuit's
latitude/longitude and the race date, it returns hourly reanalysis weather, from
which we derive a race-day summary and, above all, a **wet flag**: the single
most strategically important weather fact, because wet laps must not pollute a
dry-tyre degradation fit. Nothing is invented — a circuit with no measured
weather gets *real* reanalysis data, not an imputed constant.

The HTTP call is isolated from the parsing so the logic is tested offline.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Real coordinates of the scoped endurance circuits (decimal degrees), so the
#: same fetcher fills the IMSA/WEC weather gap the timing source leaves. F1
#: coordinates come from the Kaggle circuits table directly, so are not repeated
#: here. Verified against public circuit locations.
ENDURANCE_CIRCUIT_COORDS: dict[tuple[str, str], tuple[float, float]] = {
    ("imsa", "watkins_glen"): (42.3369, -76.9272),
    ("imsa", "sebring"): (27.4547, -81.3483),
    ("imsa", "mosport"): (44.0530, -78.6753),
    ("imsa", "road_america"): (43.7986, -87.9897),
    ("wec", "spa"): (50.4372, 5.9714),
    ("wec", "fuji"): (35.3717, 138.9269),
    ("wec", "bahrain"): (26.0325, 50.5106),
    ("wec", "imola"): (44.3439, 11.7167),
}

#: A race day with more than this total precipitation (mm) is treated as wet —
#: enough real rain that tyre-degradation laps from it should not feed a dry fit.
#: Set at 3 mm, not a trace: 1 mm over a whole day is a brief sprinkle (it flags
#: ~35% of races, over-excluding genuinely dry ones), while >3 mm (~19% of races)
#: indicates rain that plausibly affected running — it still catches Monaco 2022
#: (3.5 mm, wet-to-dry) and Monaco 2016 (11 mm), the cases this must exclude.
WET_PRECIP_MM = 3.0

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass(frozen=True)
class WeatherSummary:
    """Race-day weather derived from hourly reanalysis."""

    date: str
    temp_mean_c: float
    temp_max_c: float
    humidity_mean_pct: float
    precip_mm: float
    wet: bool

    def row(self) -> dict:
        return {
            "date": self.date, "temp_mean_c": round(self.temp_mean_c, 1),
            "temp_max_c": round(self.temp_max_c, 1),
            "humidity_mean_pct": round(self.humidity_mean_pct, 1),
            "precip_mm": round(self.precip_mm, 2), "wet": self.wet,
        }


def summarise_hourly(date: str, hourly: dict) -> WeatherSummary:
    """Reduce an Open-Meteo ``hourly`` block to a race-day summary. Pure — takes
    the parsed JSON dict, so it is unit-tested without any network."""
    temps = [t for t in hourly.get("temperature_2m", []) if t is not None]
    hums = [h for h in hourly.get("relative_humidity_2m", []) if h is not None]
    precip = [p for p in hourly.get("precipitation", []) if p is not None]
    total_precip = float(sum(precip))
    if not temps:
        raise ValueError(f"no temperature data for {date}")
    return WeatherSummary(
        date=date,
        temp_mean_c=float(sum(temps) / len(temps)),
        temp_max_c=float(max(temps)),
        humidity_mean_pct=float(sum(hums) / len(hums)) if hums else float("nan"),
        precip_mm=total_precip,
        wet=total_precip > WET_PRECIP_MM,
    )


def fetch_open_meteo(lat: float, lng: float, date: str,
                     timeout: float = 30.0) -> dict:  # pragma: no cover - network
    """Fetch one day's hourly reanalysis for a location. Returns the ``hourly``
    block of the Open-Meteo archive response."""
    import json
    import urllib.parse
    import urllib.request

    params = urllib.parse.urlencode({
        "latitude": lat, "longitude": lng, "start_date": date, "end_date": date,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
    })
    with urllib.request.urlopen(f"{_ARCHIVE_URL}?{params}", timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("hourly", {})


def race_weather(lat: float, lng: float, date: str) -> WeatherSummary:  # pragma: no cover - network
    """Fetch and summarise one race day's weather for a location."""
    return summarise_hourly(date, fetch_open_meteo(lat, lng, date))
