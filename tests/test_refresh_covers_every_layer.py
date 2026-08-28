"""Every artifact-producing script is refreshed automatically, or says why not.

The failure this exists to stop is the one that keeps happening: a change lands,
some artifact it feeds silently stops matching the code that produces it, and
nobody finds out until a human reads a number and doubts it.

The weekly refresh ran **5 of the 22 scripts that write artifacts**, all of them
F1. Its header documented the choice — endurance reports and tests are pinned to
exact race counts, so an automatic data pull would fail the gate by design. That
reasoning is sound and it conflates two very different operations:

- **Ingestion** reaches the network and can change what races exist. Re-running
  it *is* a scope change, and a scope change should be a reviewed commit.
- **Regeneration** reads already-committed laps and recomputes fits, plans,
  reports and audits. It is deterministic: run it twice on the same data and the
  bytes are identical.

Only the first needs a human. The second is exactly the check that would have
caught every staleness this project has had to fix by hand — the multi-stop
layer covering 31% of its scope, per-class reports quoting a superseded refit,
the crew-rating p-values drifting after the slopes beneath them moved twice.

So the rule this encodes: **every script that regenerates an artifact from
committed data runs in CI, and any script left out names its reason.** The
reason belongs in ``EXCLUDED`` where a reader can weigh it, not in a workflow
comment nobody re-reads.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"

#: Scripts deliberately outside CI, each with the reason it cannot run there.
#: An entry is a claim a reviewer can disagree with; an omission is an accident.
EXCLUDED: dict[str, str] = {
    "check_data_availability.py":
        "A Phase 0 scoping check that queries the source directly. It informs a "
        "human decision about what to scope; no model reads its output.",
    "discover_endurance_events.py":
        "Scans the upstream source for races that exist and clear the "
        "eligibility floor. Widening the scope is a reviewed decision, not "
        "something a schedule should do.",
    "run_ingestion.py":
        "Network ingestion. Adding a race changes the scope, and the scope is "
        "what every pinned count in this repository is pinned to.",
    "run_ingestion_waves.py":
        "The same ingestion, spread across FastF1's hourly rate limit.",
    "run_endurance_flags.py":
        "Pulls race-control flags from the network; same reasoning as ingestion.",
    "run_safety_car.py":
        "Loads 180 race editions through FastF1. Rate-limited and network-bound, "
        "so it belongs with ingestion rather than with regeneration.",
    "generate_banner.py":
        "Writes an image, not an artifact any model reads. It counts its own "
        "figures from the repository, so regenerating it is a one-line step "
        "whenever the headline numbers move.",
    "demo_extensions.py":
        "A worked demonstration for the reports, not a pipeline stage.",
    "inspect_external.py":
        "An interactive helper for looking at a raw source file.",
    "materialise_endurance.py":
        "Writes derived laps from the raw source; part of ingestion, not of "
        "regeneration.",
    "materialise_endurance_fields.py":
        "Same: materialises multi-class field data from the raw source.",
    # --- the external-source layer ------------------------------------------
    # data/external/ is gitignored: the Kaggle exports behind the breadth layer
    # are large and licensed separately, so a CI runner has nothing to read.
    # Their source is also static — a historical export, not a live feed — so
    # re-running them on a schedule would recompute identical bytes.
    "run_f1_history_degradation.py":
        "Reads the Kaggle per-lap export from data/external/, which is "
        "gitignored, and whose source is a static historical dump.",
    "run_f1_history_pit_loss.py":
        "Same source, same reason.",
    "run_f1_reliability.py":
        "Same: the retirement history comes from the gitignored Kaggle export.",
    "run_wec_reliability.py":
        "Same, for the WEC entry list.",
    "run_f1_weather.py":
        "Joins the gitignored external weather export onto the derived laps.",
}


def _artifact_scripts() -> set[str]:
    """Scripts that write into data/derived or reports/."""
    writes = re.compile(r"to_csv\(|write_text\(|write_all\(|savefig\(")
    return {
        path.name
        for path in sorted((REPO / "scripts").glob("*.py"))
        if writes.search(path.read_text(encoding="utf-8"))
    }


def _scripts_in_ci() -> set[str]:
    """Every scripts/*.py invoked by any workflow."""
    invoked: set[str] = set()
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        invoked |= set(re.findall(r"scripts/([a-z_0-9]+\.py)", text))
    return invoked


def test_every_artifact_script_is_scheduled_or_excused() -> None:
    """No artifact regenerates only when someone remembers to run it."""
    produced = _artifact_scripts()
    scheduled = _scripts_in_ci()
    unaccounted = sorted(produced - scheduled - set(EXCLUDED))

    assert not unaccounted, (
        f"{len(unaccounted)} script(s) write artifacts but never run in CI and "
        f"give no reason: {unaccounted}.\n"
        "Add them to a workflow, or add an entry to EXCLUDED saying why a "
        "schedule cannot run them. An artifact that only refreshes when someone "
        "remembers is an artifact that goes stale without anyone noticing."
    )


def test_exclusions_are_real_scripts() -> None:
    """An excuse for a script that no longer exists is a stale excuse."""
    existing = {path.name for path in (REPO / "scripts").glob("*.py")}
    ghosts = sorted(set(EXCLUDED) - existing)
    assert not ghosts, f"EXCLUDED names scripts that do not exist: {ghosts}"


def test_every_series_is_regenerated_not_just_f1() -> None:
    """The refresh covered F1 only, and that is how the rest drifted.

    Named explicitly rather than left to the general check, because the general
    check passes the moment *someone* adds an excuse — and "endurance is pinned
    to exact counts" was exactly such an excuse. It is true of ingestion and
    false of regeneration, and the distinction is the whole point.
    """
    scheduled = _scripts_in_ci()
    required = {
        "run_endurance_models.py": "endurance fits, quality, transfer, traffic",
        "run_multistop.py": "full-race plans — the strategy layer",
        "run_class_reports.py": "the per-class tables for all six classes",
        "run_systematic_audit.py": "the calendar-wide F1 decision audit",
        "run_systematic_endurance_audit.py": "its endurance counterpart, all six classes",
        "run_track_position.py": "overtaking difficulty per circuit",
    }
    missing = {name: why for name, why in required.items() if name not in scheduled}
    assert not missing, (
        "these regenerate deterministically from committed data and are not in "
        f"any workflow: {missing}. Each one has already gone stale once."
    )
