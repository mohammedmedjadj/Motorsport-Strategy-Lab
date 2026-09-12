"""One palette, three surfaces, and only one of them can import Python.

`src/reporting/palette.py` is the definition. The figure scripts and the
Streamlit demo import it. The website cannot without a build step, and neither
can `.streamlit/config.toml`, so both keep their own copy of the values — and
these tests fail when a copy drifts.

That is the whole point. Before this, the same four hex values were written out
by hand in two figure scripts, each carrying a comment asserting it matched the
other, again as CSS custom properties in the site, and the demo used a purple
and a lilac belonging to nothing. Checked duplication is a different thing from
duplication that is hoped about.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from src.reporting import palette

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "docs" / "index.html"
CONFIG = REPO / ".streamlit" / "config.toml"


def _css_variables() -> dict[str, str]:
    """The `:root` block's custom properties, light theme."""
    if not SITE.exists():
        pytest.skip("docs/index.html not present")
    text = SITE.read_text(encoding="utf-8")
    start = text.index(":root {")
    block = text[start:text.index("}", start)]
    return {
        name: value.strip().lower()
        for name, value in re.findall(r"(--[\w-]+):\s*([^;]+);", block)
    }


def test_the_site_declares_every_colour_the_palette_names() -> None:
    declared = _css_variables()
    missing = [
        name for name in palette.SITE_VARIABLES if name not in declared
    ]
    assert not missing, (
        "src/reporting/palette.py names CSS variables the site does not "
        f"declare: {missing}. One of the two was renamed."
    )


@pytest.mark.parametrize(
    ("name", "expected"), sorted(palette.SITE_VARIABLES.items())
)
def test_each_site_colour_matches_the_palette(name: str, expected: str) -> None:
    declared = _css_variables()
    if name not in declared:
        pytest.skip(f"{name} not declared; covered by the test above")
    assert declared[name] == expected.lower(), (
        f"the site declares {name}: {declared[name]}, the palette says "
        f"{expected}. The figures and the demo follow the palette, so the "
        "site is now a different colour from everything it illustrates."
    )


def test_the_site_dark_theme_matches_the_palette() -> None:
    """The dark block redefines five surface roles and nothing else."""
    text = SITE.read_text(encoding="utf-8")
    start = text.index('prefers-color-scheme: dark')
    block = text[start:text.index("}", text.index(":root", start))]
    declared = {
        name: value.strip().lower()
        for name, value in re.findall(r"(--[\w-]+):\s*([^;]+);", block)
    }
    for role, expected in palette.DARK.items():
        variable = f"--{role}"
        if variable not in declared:
            continue
        assert declared[variable] == expected.lower(), (
            f"the site's dark theme sets {variable}: {declared[variable]}, "
            f"the palette says {expected}"
        )


def _streamlit_theme() -> dict:
    if not CONFIG.exists():
        pytest.skip(".streamlit/config.toml not present")
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))["theme"]


def test_the_demo_light_theme_is_the_site_light_theme() -> None:
    theme = _streamlit_theme()
    expected = {
        "backgroundColor": palette.LIGHT["bg"],
        "secondaryBackgroundColor": palette.LIGHT["panel"],
        "textColor": palette.LIGHT["ink"],
        "borderColor": palette.LIGHT["line"],
        "linkColor": palette.TEAL,
        "primaryColor": palette.NAVY,
    }
    wrong = {
        key: (theme.get(key), value)
        for key, value in expected.items()
        if str(theme.get(key, "")).lower() != value.lower()
    }
    assert not wrong, (
        "the demo's theme has drifted from the site's (key: got, expected): "
        f"{wrong}"
    )


def test_the_demo_dark_theme_uses_the_sites_dark_surfaces() -> None:
    theme = _streamlit_theme().get("dark", {})
    expected = {
        "backgroundColor": palette.DARK["bg"],
        "secondaryBackgroundColor": palette.DARK["panel"],
        "textColor": palette.DARK["ink"],
        "borderColor": palette.DARK["line"],
    }
    wrong = {
        key: (theme.get(key), value)
        for key, value in expected.items()
        if str(theme.get(key, "")).lower() != value.lower()
    }
    assert not wrong, (
        f"the demo's dark theme has drifted from the site's: {wrong}"
    )


def test_the_demo_charts_use_the_palette_cycle() -> None:
    """Streamlit's own charts and a matplotlib figure must not disagree."""
    declared = [c.lower() for c in _streamlit_theme()["chartCategoricalColors"]]
    cycle = [
        c.lower()
        for c in palette.matplotlib_rc()["axes.prop_cycle"].by_key()["color"]
    ]
    assert declared == cycle, (
        "a built-in Streamlit chart and a matplotlib figure on the same page "
        f"would use different colours: config has {declared}, the palette "
        f"cycles {cycle}"
    )


def test_the_figure_scripts_take_their_colours_from_the_palette() -> None:
    """The two dicts this module replaced must not grow back."""
    for name in ("make_headline_figures.py", "make_supporting_figures.py"):
        source = (REPO / "scripts" / name).read_text(encoding="utf-8")
        assert "from src.reporting.palette import" in source, (
            f"scripts/{name} no longer imports the shared palette"
        )
        redefined = re.findall(r"(?m)^(CLASS_COLOURS|COMPOUND_COLOURS)\s*=", source)
        assert not redefined, (
            f"scripts/{name} redefines {redefined} locally, which is the "
            "hand-copied duplication src/reporting/palette.py exists to end"
        )
