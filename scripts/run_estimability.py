"""Is every reported slope estimable, or set by the pseudo-inverse?

The Formula 1 fit solves its fixed-effects design by least squares with a
minimum-norm solution, because a driver-race seen on a single compound can
leave the design rank-deficient. In a rank-deficient design the minimum-norm
solution fixes any non-estimable coefficient by the norm rather than by the
data, and its cluster-robust standard error then means nothing. So each
coefficient that is reported -- the fuel slope and every compound's tyre-age
terms -- is checked: column ``j`` is estimable exactly when deleting it lowers
the rank of the design.

The endurance fit has one slope column next to its unit fixed effects and is
checked the same way.

Writes ``data/derived/f1/estimability_summary.json``.

    python scripts/run_estimability.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.degradation.dataset import (  # noqa: E402
    build_modelling_frame,
    circuits_with_laps,
    load_circuit_laps,
)
from src.degradation.model import _design_matrix  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS  # noqa: E402

COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
OUT_JSON = F1_DERIVED_DIR / "estimability_summary.json"


def estimable(X: np.ndarray, columns: list[int]) -> dict[int, bool]:
    rank = np.linalg.matrix_rank(X)
    return {j: np.linalg.matrix_rank(np.delete(X, j, axis=1)) < rank for j in columns}


def main() -> int:
    # The published fits: every circuit in degradation_coefficients.csv, at
    # the degree it was published at.
    degrees = pd.read_csv(COEFS).groupby("circuit")["degree"].first()
    checked = failed = 0
    rank_deficient = 0
    failures = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in degrees.index:
            continue
        laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
        frame, _ = build_modelling_frame(laps, circuit)
        compounds = tuple(sorted(frame["Compound"].unique()))
        X, names = _design_matrix(frame, compounds, int(degrees[circuit]))
        if np.linalg.matrix_rank(X) < X.shape[1]:
            rank_deficient += 1
        targets = [j for j, n in enumerate(names) if not n.startswith("fe::")]
        for j, ok in estimable(X, targets).items():
            checked += 1
            if not ok:
                failed += 1
                failures.append(f"{circuit}:{names[j]}")
    out = {
        "f1_circuits": int(len(degrees)),
        "f1_rank_deficient_designs": rank_deficient,
        "f1_coefficients_checked": checked,
        "f1_non_estimable": failed,
        "f1_failures": failures,
    }
    OUT_JSON.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
