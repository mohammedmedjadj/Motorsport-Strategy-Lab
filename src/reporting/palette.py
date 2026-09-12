"""One palette, for the figures, the demo and the website.

Before this file the same four hex values were written out in
`make_headline_figures.py`, in `make_supporting_figures.py`, and again as CSS
custom properties in `docs/index.html` -- and the Streamlit demo used a purple
and a lilac that appear nowhere else in the project. Three surfaces, four
palettes, one project.

Python reads the values from here. The website cannot import Python without a
build step nobody wants, so its CSS keeps its own copy and
`tests/test_palette.py` fails if the two ever disagree. Duplication that is
checked is a different thing from duplication that is hoped about.

Nothing here is new. Every value is what the figures already drew, so adopting
this module changes no pixel of any committed figure -- which matters, because
`tests/test_site.py` compares the site's figures to the generated ones byte for
byte.
"""

from __future__ import annotations

#: Body text and secondary text on figures. Not the same as the website's
#: --ink: a figure sits on white paper in a PDF, a page sits on its own
#: background and has a dark mode.
INK = "#222222"
MUTED = "#666666"

#: The four that carry meaning. These are the website's --red, --teal, --navy
#: and --amber, and `tests/test_palette.py` holds them to it.
RED = "#d1495b"
TEAL = "#00798c"
NAVY = "#2b2d42"
AMBER = "#edae49"

#: Supporting tones, used where a mark should recede rather than signify.
SLATE = "#8d99ae"
STEEL = "#7e9aa8"
GREY = "#888888"

#: Series blues, distinct enough to separate four championships on one axis.
WEC_BLUE = "#30638e"
ELMS_BLUE = "#003d5b"

#: Page colours, matching `:root` and the dark override in docs/index.html.
LIGHT = {
    "ink": "#16181d",
    "muted": "#5c6470",
    "line": "#e3e6ea",
    "bg": "#ffffff",
    "panel": "#f7f8fa",
}
DARK = {
    "ink": "#e8eaed",
    "muted": "#9aa3af",
    "line": "#2a2f38",
    "bg": "#14161a",
    "panel": "#1b1e24",
}

#: Car class to colour. One class, one colour, everywhere it appears.
CLASS_COLOURS = {
    "GTD": RED,
    "GTDPRO": AMBER,
    "GTP": TEAL,
    "HYPERCAR": "#30638e",
    "LMP2": "#003d5b",
    "LMP2 Pro/Am": STEEL,
    "F1": NAVY,
}

#: Tyre compound to colour, in the sense the compound names already imply.
COMPOUND_COLOURS = {"SOFT": RED, "MEDIUM": AMBER, "HARD": SLATE}

#: The website's CSS custom properties, so a test can compare like with like.
SITE_VARIABLES = {
    "--red": RED,
    "--teal": TEAL,
    "--navy": NAVY,
    "--amber": AMBER,
    "--ink": LIGHT["ink"],
    "--muted": LIGHT["muted"],
    "--line": LIGHT["line"],
    "--bg": LIGHT["bg"],
    "--panel": LIGHT["panel"],
}


def matplotlib_rc(dark: bool = False) -> dict[str, object]:
    """rcParams that make a chart look like it belongs to this project.

    Returned rather than applied, so a caller decides the scope. The demo
    applies them once at import; the figure scripts do not use this -- they
    have their own per-figure styling that predates it and that regenerating
    must not perturb.
    """
    from cycler import cycler as __cycler

    page = DARK if dark else LIGHT
    return {
        "figure.facecolor": page["bg"],
        "axes.facecolor": page["bg"],
        "savefig.facecolor": page["bg"],
        "text.color": page["ink"],
        "axes.labelcolor": page["ink"],
        "axes.edgecolor": page["line"],
        "xtick.color": page["muted"],
        "ytick.color": page["muted"],
        "grid.color": page["line"],
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.alpha": 0.5,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        # Imported here, not at module scope: the figure scripts need the hex
        # values without pulling matplotlib in as a hard dependency of every
        # consumer of this module.
        "axes.prop_cycle": __cycler(
            "color", [NAVY, TEAL, RED, AMBER, SLATE, ELMS_BLUE]
        ),
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "regular",
        "legend.frameon": False,
    }
