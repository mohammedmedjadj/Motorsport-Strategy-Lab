"""Circuit and class names as a reader expects to see them.

Internally a circuit is a slug — `red_bull_ring`, `yas_marina`, `cota` — because
a slug is a stable join key and a display name is not. That is the right choice
for the data and the wrong one for a figure axis or a published table, where
`red_bull_ring` reads as script output rather than as a result.

Title-casing is not enough on its own. Half these names are proper nouns with
their own capitalisation (COTA, VIR, Yas Marina), one is a person (Gilles
Villeneuve), and Mosport and Interlagos are the names people actually use for
circuits whose official titles are longer. So the mapping is explicit, and
anything not in it falls back to title-casing the slug, which is right for the
straightforward cases and never worse than the slug itself.
"""

from __future__ import annotations

#: Slug to display name. Only entries where title-casing gets it wrong, plus
#: the ones where the common name differs from the official one.
DISPLAY_NAMES: dict[str, str] = {
    # Formula 1
    "cota": "COTA",
    "red_bull_ring": "Red Bull Ring",
    "yas_marina": "Yas Marina",
    "las_vegas": "Las Vegas",
    "mexico_city": "Mexico City",
    "paul_ricard": "Paul Ricard",
    "ricard": "Paul Ricard",
    "villeneuve": "Gilles Villeneuve",
    "montreal": "Montréal",
    "interlagos": "Interlagos",
    "sao_paulo": "São Paulo",
    "hungaroring": "Hungaroring",
    "zandvoort": "Zandvoort",
    "spa": "Spa-Francorchamps",
    "monza": "Monza",
    "imola": "Imola",
    "jeddah": "Jeddah",
    "losail": "Losail",
    "baku": "Baku",
    "suzuka": "Suzuka",
    "shanghai": "Shanghai",
    "melbourne": "Melbourne",
    "silverstone": "Silverstone",
    "barcelona": "Barcelona",
    "madrid": "Madrid",
    "monaco": "Monaco",
    "bahrain": "Bahrain",
    "miami": "Miami",
    "austin": "Austin",
    "singapore": "Singapore",
    # Endurance
    "vir": "VIR",
    "watkins_glen": "Watkins Glen",
    "watkins_glen_240": "Watkins Glen 240",
    "watkins_glen_6_hours": "Watkins Glen 6 Hours",
    "road_america": "Road America",
    "road_atlanta": "Road Atlanta",
    "laguna_seca": "Laguna Seca",
    "lime_rock": "Lime Rock",
    "long_beach": "Long Beach",
    "mid_ohio": "Mid-Ohio",
    "mid-ohio": "Mid-Ohio",
    "mosport": "Mosport",
    "canadian_tire_motorsport_park": "Mosport",
    "belle_isle": "Belle Isle",
    "indianapolis": "Indianapolis",
    "daytona": "Daytona",
    "sebring": "Sebring",
    "detroit": "Detroit",
    "portimao": "Portimão",
    "aragon": "Aragón",
    "mugello": "Mugello",
    "fuji": "Fuji",
    "le_mans": "Le Mans",
}

#: Class codes as they should read. GTDPRO is the source's spelling; the class
#: is written GTD PRO everywhere a person writes it.
CLASS_NAMES: dict[str, str] = {
    "GTDPRO": "GTD PRO",
    "GTD": "GTD",
    "GTP": "GTP",
    "HYPERCAR": "Hypercar",
    "LMP2": "LMP2",
    "LMP2 Pro/Am": "LMP2 Pro/Am",
    "LMP2 PRO/AM": "LMP2 Pro/Am",
}


def circuit(slug: str) -> str:
    """A circuit slug as it should appear to a reader."""
    key = str(slug).strip().lower().replace(" ", "_").replace("-", "_")
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    # Already a display name (the endurance source stores some that way).
    if str(slug) in DISPLAY_NAMES.values():
        return str(slug)
    return key.replace("_", " ").title()


def car_class(code: str) -> str:
    """A class code as it should appear to a reader."""
    return CLASS_NAMES.get(str(code).strip(), str(code).strip())


def circuit_class(slug: str, code: str) -> str:
    """Circuit and class together, the unit most of this project reports on."""
    return f"{circuit(slug)} {car_class(code)}"
