"""The two briefs sent to Salminen, and what must stay true of them.

These are documents sent to a named researcher about his own model, so the
failure modes that matter are the ones that make them look careless. Three are
guarded here.

Every digit has to come from an artifact. The first draft typed four: the
audit's headline share and median, the measured slope, and the count of values a
stale circuit-slug join drops. That last one was already wrong -- it said 86 of
267 and recomputing gave 85 of 266, because the lapped-car bound added since
then removes one decision. A number describing a defect drifts like any other.

They have to fit one page and stay inside the right margin. The vertical check
existed; nothing checked the width, and the first build came back with its title
silently clipped at the page edge.

And they have to be byte-reproducible, so that regenerating an unchanged brief
produces an unchanged file and a diff means a real change.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "make_salminen_briefs.py"
BRIEFS = (
    REPO / "outreach" / "overcut_feasibility_brief.pdf",
    REPO / "outreach" / "d1_defence_brief.pdf",
)


def test_both_briefs_are_committed() -> None:
    missing = [p.name for p in BRIEFS if not p.exists()]
    assert not missing, f"run scripts/make_salminen_briefs.py: {missing}"


def test_regenerating_them_changes_nothing() -> None:
    """A brief that is not reproducible cannot be diffed, so it cannot be reviewed."""
    if not SCRIPT.exists():
        pytest.skip("scripts/make_salminen_briefs.py not present")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in BRIEFS}
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout + done.stderr
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            f"{path.name} differs after regeneration from unchanged inputs. "
            "Either an input moved, or something non-deterministic (a "
            "timestamp) is being written into it."
        )


def _prose_literals(source: str) -> list[str]:
    """Every string literal that reaches the page, and nothing else.

    Line matching cannot tell a sentence from a code path: it read
    `quantile(0.25)` as a typed number. The AST can, because the prose is
    exactly the literal arguments of page.block(), page.heading() and the
    Brief() constructor, including the literal parts of f-strings.
    """
    import ast

    out: list[str] = []

    def literal_parts(node) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.JoinedStr):
            return [v.value for v in node.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        if isinstance(node, ast.BinOp):  # implicit concatenation is a BinOp? no
            return literal_parts(node.left) + literal_parts(node.right)
        return []

    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        if name not in {"block", "heading", "Brief"}:
            continue
        for argument in node.args:
            out.extend(literal_parts(argument))
    return out


def test_the_briefs_type_no_numbers_of_their_own() -> None:
    """The project's oldest defect is a number typed instead of derived.

    Narrow on purpose. Salminen's own constants are quoted from his paper and
    belong in the prose; season years are not claims. What this catches is a
    multi-digit quantity sitting in a sentence, which is where every drift in
    this project has lived.
    """
    import re as _re

    if not SCRIPT.exists():
        pytest.skip("scripts/make_salminen_briefs.py not present")

    #: His worked example, cited from the preprint rather than measured here.
    HIS = {"0.1", "0.55", "6.5", "2.6", "40", "1", "2"}
    #: Seasons.
    CONTEXT = {"2022", "2026"}

    offenders: list[str] = []
    for text in _prose_literals(SCRIPT.read_text(encoding="utf-8")):
        for number in _re.findall(r"\d[\d,.]*", text):
            cleaned = number.rstrip(".,")
            if cleaned in HIS or cleaned in CONTEXT:
                continue
            offenders.append(f"{cleaned!r} in {text.strip()[:70]!r}")
    assert not offenders, (
        "these briefs contain typed numbers:\n  " + "\n  ".join(offenders) +
        "\nDerive them from the committed artifacts. A figure quoted from "
        "memory is unsourced even when it happens to be right."
    )


def test_the_width_guard_refuses_an_overrunning_line() -> None:
    """The guard that caught the clipped title, checked rather than trusted."""
    sys.path.insert(0, str(REPO))
    from src.reporting.brief import Brief

    page = Brief("Title", "Subtitle", "Byline")
    page.block("x" * 400)
    with pytest.raises(SystemExit) as raised:
        page.finish(REPO / "outreach" / "_probe.pdf", {"Title": "probe"})
    assert "right margin" in str(raised.value)
    assert not (REPO / "outreach" / "_probe.pdf").exists(), (
        "the page was written despite overrunning"
    )


def test_the_height_guard_refuses_an_overflowing_page() -> None:
    sys.path.insert(0, str(REPO))
    from src.reporting.brief import Brief

    page = Brief("Title", "Subtitle", "Byline")
    for _ in range(80):
        page.block("a line of body text")
    with pytest.raises(SystemExit) as raised:
        page.finish(REPO / "outreach" / "_probe.pdf", {"Title": "probe"})
    assert "overflows one page" in str(raised.value)
    assert not (REPO / "outreach" / "_probe.pdf").exists()


def test_the_layout_constants_have_not_drifted_apart() -> None:
    """scripts/make_outreach_brief.py keeps its own copy of these.

    Deliberately: its output is compared byte for byte by
    tests/test_outreach_brief.py, and refactoring a file under that kind of
    test risks a committed artifact for no reader's benefit. The cost is two
    copies of the layout, so they are checked against each other here.
    """
    import ast

    sys.path.insert(0, str(REPO))
    from src.reporting import brief as module

    source = (REPO / "scripts" / "make_outreach_brief.py").read_text(
        encoding="utf-8"
    )
    # Tuple assignment is how half of these are written
    # (`PAGE_W, PAGE_H = 8.27, 11.69`), which a line-matching version could not
    # read.
    found: dict[str, float] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        targets, values = node.targets[0], node.value
        pairs = (
            zip(targets.elts, values.elts)
            if isinstance(targets, ast.Tuple) and isinstance(values, ast.Tuple)
            else [(targets, values)]
        )
        for target, value in pairs:
            if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                if isinstance(value.value, (int, float)):
                    found[target.id] = float(value.value)

    shared = ("PAGE_W", "PAGE_H", "LEFT", "RIGHT", "BODY", "SMALL", "HEAD",
              "LINESPACING", "MARGIN")
    missing = [name for name in shared if name not in found]
    assert not missing, (
        f"{missing} no longer defined in make_outreach_brief.py, so the two "
        "layouts can no longer be compared"
    )
    for name in shared:
        assert getattr(module, name) == found[name], (
            f"{name} is {getattr(module, name)} in src/reporting/brief.py and "
            f"{found[name]} in scripts/make_outreach_brief.py. The two "
            "layouts have drifted apart."
        )
