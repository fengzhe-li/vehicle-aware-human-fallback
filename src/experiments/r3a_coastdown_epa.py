"""Phase R3A: drag-only (coast-down) deceleration bounds from US EPA road-load data.

The EPA Test Car List reports, for each certification test vehicle, the target
road-load coefficients A (lbf), B (lbf/mph), C (lbf/mph^2) and the equivalent
test weight (lb). The road-load force F(v) = A + B v + C v^2 is determined from
coast-down testing, so F(v) / m is the deceleration from tyre rolling resistance,
driveline losses in neutral and aerodynamic drag, with no propulsion, engine
braking, regeneration or friction braking.

This is a deterministic unit conversion of a public dataset. It bounds the
"coast / drag" component of a_pre only; it says nothing about engine braking,
regenerative or one-pedal deceleration, or automation braking.

Assumptions (stated in the output):
- mass = equivalent test weight (an inertia class, not measured kerb mass);
  rotational inertia is not added, so values are slightly high;
- level road, still air;
- rows are deduplicated to unique (make, model, test weight, A, B, C).

Usage:
    python -m src.experiments.r3a_coastdown_epa [xlsx] [output_csv]
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Dict

import numpy as np
import pandas as pd

LBF_TO_N = 4.4482216152605
LB_TO_KG = 0.45359237
MPH_TO_MPS = 0.44704

DEFAULT_XLSX = "data/external/epa/24-testcar-2025-05.xlsx"
SOURCE_URL = "https://www.epa.gov/system/files/documents/2025-05/24-testcar-2025-05.xlsx"
DEFAULT_OUTPUT = "research/data_matrix/r3a_epa_coastdown_deceleration.csv"
SPEEDS_KMH = (60, 80, 100, 130)
COLS = {"A": "Target Coef A (lbf)", "B": "Target Coef B (lbf/mph)", "C": "Target Coef C (lbf/mph**2)",
        "W": "Equivalent Test Weight (lbs.)"}
KEY = ["Represented Test Veh Make", "Represented Test Veh Model", COLS["W"], COLS["A"], COLS["B"], COLS["C"]]


def road_load_decel_mps2(a_lbf, b_lbf_mph, c_lbf_mph2, etw_lb, speed_kmh):
    """Deceleration (m/s^2, positive) from EPA road-load coefficients at a given speed."""
    v_mph = speed_kmh / 3.6 / MPH_TO_MPS
    force_n = (np.asarray(a_lbf) + np.asarray(b_lbf_mph) * v_mph + np.asarray(c_lbf_mph2) * v_mph ** 2) * LBF_TO_N
    return force_n / (np.asarray(etw_lb) * LB_TO_KG)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=list(COLS.values())).drop_duplicates(KEY).copy()
    d["group"] = np.where(d["Test Fuel Type Description"].str.contains("Electric", case=False, na=False),
                          "battery electric (road load only; regen NOT included)", "non-electric")
    rows = []
    for kmh in SPEEDS_KMH:
        d["_a"] = road_load_decel_mps2(d[COLS["A"]], d[COLS["B"]], d[COLS["C"]], d[COLS["W"]], kmh)
        for grp, g in [("all", d), *d.groupby("group")]:
            q = g["_a"].quantile([0.05, 0.25, 0.5, 0.75, 0.95])
            rows.append({"speed_kmh": kmh, "group": grp, "n_configurations": int(len(g)),
                         "p05_mps2": round(float(q[0.05]), 4), "p25_mps2": round(float(q[0.25]), 4),
                         "median_mps2": round(float(q[0.5]), 4), "p75_mps2": round(float(q[0.75]), 4),
                         "p95_mps2": round(float(q[0.95]), 4)})
    return pd.DataFrame(rows)


def run(xlsx: str = DEFAULT_XLSX, output_csv: str = DEFAULT_OUTPUT) -> Dict[str, object]:
    with open(xlsx, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    out = summarise(pd.read_excel(xlsx))
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    out.to_csv(output_csv, index=False)
    prov = {
        "source": "US EPA Test Car List, model year 2024 (file dated 2025-05)",
        "source_url": SOURCE_URL,
        "source_sha256": sha,
        "definition": "deceleration = (A + B v + C v^2) / equivalent test weight; coast-down road load only",
        "unit_conversions": {"lbf_to_N": LBF_TO_N, "lb_to_kg": LB_TO_KG, "mph_to_mps": MPH_TO_MPS},
        "assumptions": ["mass = equivalent test weight; rotational inertia not added (values slightly high)",
                        "level road, still air",
                        "deduplicated to unique make, model, test weight and coefficients"],
        "scope_limitation": "bounds the drag / coast component of a_pre only; excludes engine braking, "
                            "regenerative and one-pedal deceleration, and automation braking",
        "code": "src/experiments/r3a_coastdown_epa.py",
    }
    with open(os.path.splitext(output_csv)[0] + "_provenance.json", "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2)
        fh.write("\n")
    return {"summary": out, "provenance": prov}


if __name__ == "__main__":
    run(*sys.argv[1:3])
