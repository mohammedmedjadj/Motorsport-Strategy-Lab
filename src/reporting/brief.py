"""One-page A4 briefs, laid out with a measured cursor.

A brief is a document sent to a named person, so it has two properties an
ordinary report does not need. It has to fit on one page, and it has to be the
same file every time it is built, so that a real diff means a real change
rather than a new timestamp.

Both are enforced rather than hoped for. The cursor tracks its own position
down the page and :meth:`Brief.finish` refuses to emit a page that ran past the
bottom margin, which is a loud failure instead of text silently printed off the
sheet. And the PDF is written with no CreationDate, which is the only byte that
would otherwise differ between two builds of identical content.

``scripts/make_outreach_brief.py`` predates this module and keeps its own copy
of the layout. That is deliberate: its output is compared byte for byte by
``tests/test_outreach_brief.py``, and refactoring a file under that kind of test
risks a committed artifact for no gain to the reader. ``tests/test_brief.py``
checks the two sets of constants still agree, so they cannot drift apart
quietly.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from src.reporting import palette

matplotlib.use("Agg")

#: A4 in inches.
PAGE_W, PAGE_H = 8.27, 11.69

#: Left and right text edges, in figure fractions.
LEFT, RIGHT = 0.072, 0.928

#: Point sizes. Small enough to fit a dense page, large enough to read on
#: paper rather than only on a screen.
BODY, SMALL, HEAD = 7.85, 7.35, 9.9
TITLE, SUBTITLE, BYLINE = 15.0, 10.2, 8.0

LINESPACING = 1.20

#: Top and bottom margins, in figure fractions. The overflow check uses the
#: same constant, so a page cannot acquire a thinner footer than header by
#: drifting.
MARGIN = 0.028


def height(size: float, lines: int) -> float:
    """Figure-fraction height of a block of text, in the units the cursor moves in."""
    return lines * size * LINESPACING / 72.0 / PAGE_H


class Brief:
    """A page that knows how far down it has written."""

    def __init__(self, title: str, subtitle: str, byline: str) -> None:
        self.fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        self.fig.patch.set_facecolor("white")
        self.y = 1.0 - MARGIN
        self.ink = palette.LIGHT["ink"]
        self.muted = palette.LIGHT["muted"]

        self.block(title, size=TITLE, weight="bold", gap=0.004)
        self.block(subtitle, size=SUBTITLE, colour=self.muted, gap=0.003)
        self.block(byline, size=BYLINE, colour=self.muted, gap=0.012)
        self.rule()

    def block(self, body: str, size: float = BODY, colour: str | None = None,
              weight: str = "normal", gap: float = 0.0075) -> None:
        self.fig.text(
            LEFT, self.y, body, size=size, color=colour or self.ink,
            weight=weight, va="top", ha="left", linespacing=LINESPACING,
        )
        self.y -= height(size, body.count("\n") + 1) + gap

    def heading(self, body: str, colour: str = palette.NAVY) -> None:
        self.block(body, size=HEAD, colour=colour, weight="bold", gap=0.004)

    def rule(self, gap: float = 0.014) -> None:
        self.fig.add_artist(plt.Line2D(
            [LEFT, RIGHT], [self.y] * 2, color=palette.LIGHT["line"],
            linewidth=0.9, transform=self.fig.transFigure,
        ))
        self.y -= gap

    def _overrunning_lines(self) -> list[tuple[str, float]]:
        """Lines whose rendered width passes the right margin.

        The vertical overflow check catches text printed off the bottom of the
        sheet. Nothing caught text printed off the side, and a title set two
        characters too long came back from the first build silently truncated
        at the page edge. Measuring is the only way to know: the width depends
        on the glyphs, not on the character count, so no column limit applied
        to the source would be reliable.
        """
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        width = self.fig.get_figwidth() * self.fig.dpi
        over = []
        for artist in self.fig.texts:
            box = artist.get_window_extent(renderer=renderer)
            right = box.x1 / width
            if right > RIGHT + 1e-6:
                longest = max(artist.get_text().split("\n"), key=len)
                over.append((longest, right))
        return over

    def finish(self, path: Path, metadata: dict[str, str]) -> Path:
        """Write the page, refusing one that ran off the bottom or the side."""
        if self.y < MARGIN:
            plt.close(self.fig)
            raise SystemExit(
                f"{path.name} overflows one page (ended at {self.y:.3f}, "
                f"margin {MARGIN}). Cut text rather than shrinking the type: a "
                "brief that needs a second page is a brief that needs editing."
            )
        over = self._overrunning_lines()
        if over:
            plt.close(self.fig)
            detail = "\n".join(
                f"  reaches {right:.3f} (margin {RIGHT}): {line.strip()[:78]}"
                for line, right in over
            )
            raise SystemExit(
                f"{path.name} has {len(over)} block(s) running past the right "
                f"margin:\n{detail}\n"
                "Rewrap the source lines. A line that overruns is clipped at "
                "the page edge without any error, which is how a truncated "
                "title reached a first build."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        # No CreationDate. It is the only byte that changes between runs, and a
        # timestamp says nothing about the brief. Rebuilding unchanged content
        # should produce an unchanged file, so a diff means a real change.
        self.fig.savefig(
            path, format="pdf",
            metadata={**metadata, "Creator": metadata.get("Creator", ""),
                      "CreationDate": None},
        )
        plt.close(self.fig)
        return path
