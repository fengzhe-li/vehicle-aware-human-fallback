"""Phase R1: D003 ingestion validation outputs.

Produces three validation tables (not scientific findings):

1. ``trial_qa.csv``: one strict-ingestion QA row per raw trial (all 513).
2. ``owner_reconciliation.csv``: per-trial accounting of our TOR sets against the
   dataset owners' reported analysis set (466 takeovers; arXiv 2507.22252). The
   owners' per-trial exclusion list is not published, so candidate matches are
   labelled NEWLY_INFERRED and are never forced to add up.
3. ``owner_metric_replication.csv``: the owners' established metrics recomputed
   over their documented window (TOR to lane change), to validate ingestion.
   Their numerical results were not available for comparison; definitions and
   counts are compared in ``summary.md``.

Usage:
    python -m src.experiments.r1_ingestion_validation [archive] [output_dir]
"""

from __future__ import annotations

import os
import sys
import zipfile
from typing import Dict, List

import numpy as np
import pandas as pd

from src.data.d003_ingest import (
    D003Archive,
    TTC_COLUMN,
    audit_trial,
    observation_events,
)

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_OUTPUT = "results/R1_ingestion_validation"

OWNER_REFERENCE = "Liang, Calvert & van Lint, arXiv 2507.22252"
OWNER_N_RAW = 513
OWNER_N_ANALYSED = 466
OWNER_EXCLUSIONS = {
    "control before TOR or forgot mode-switch button": 16,
    "incomplete questionnaires or hardware malfunctions": 31,
}


def _md_table(df: pd.DataFrame, index: bool = False) -> str:
    """Minimal Markdown table (avoids an optional `tabulate` dependency)."""
    if index:
        df = df.reset_index()
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


def gaze_trials(archive_path: str) -> set:
    """Trial ids with an eye-tracking gaze file (used only as candidate evidence)."""
    with zipfile.ZipFile(archive_path) as z:
        return {
            os.path.basename(n).replace("_gaze.csv", "")
            for n in z.namelist()
            if n.endswith("_gaze.csv") and "__MACOSX" not in n
        }


def owner_window_metrics(trial) -> Dict[str, object]:
    """Owner metrics over [TOR, lane change] (their documented window).

    Only computed when the TOR anchor is resolved and the lane change is VALIDATED.
    """
    ev = observation_events(trial)
    out: Dict[str, object] = {
        "trial_id": trial.meta.trial_id,
        "tor_state": ev.tor.state,
        "lane_change_state": ev.lane_change.state,
        "t_button_s": None,
        "window_status": None,
        "min_ttc_s": None,
        "max_abs_steering_angle_rad": None,
        "max_abs_steering_dev_from_baseline_rad": None,
        "max_longitudinal_accel_mps2": None,
        "max_longitudinal_decel_mps2": None,
        "n_ttc_samples_excluded": None,
        "vehicle_stopped_in_window": None,
        "brake_semantics": "UNRESOLVED",
    }
    if ev.t_tor is not None and ev.t_manual_start is not None:
        out["t_button_s"] = ev.t_manual_start - ev.t_tor
    if ev.t_tor is None:
        out["window_status"] = f"NO_TOR_ANCHOR ({ev.tor.state})"
        return out
    if ev.lane_change.state != "VALIDATED":
        out["window_status"] = f"NO_VALIDATED_LANE_CHANGE ({ev.lane_change.state})"
        return out
    t = trial.telemetry["t_rel"].to_numpy()
    win = (t >= ev.t_tor) & (t <= ev.lane_change.value)
    base = (t >= ev.t_tor - 4.0) & (t <= ev.t_tor - 0.2)
    ttc = trial.column(TTC_COLUMN)[win]
    speed = trial.column("[00].VehicleUpdate-speed.001")[win]
    steer = trial.column("[00].VehicleUpdate-steeringWheelAngle")
    ax = trial.column("[00].VehicleUpdate-accel.001")[win]
    dist = trial.column("[85 (Distance/Distance_to_Construction)].ExportChannel-val")[win]
    # Dictionary: TTC = distance_to_collision / car_speed_x. It is defined only while
    # approaching (distance > 0, speed > 0), where it must be positive. Samples outside
    # that domain (e.g., a stopped vehicle, or TTC <= 0 from the export channel being
    # sampled out of step with speed) are excluded and counted, not interpreted.
    closing = (speed > 0) & (dist > 0)
    valid = closing & np.isfinite(ttc) & (ttc > 0)
    ttc_valid = ttc[valid]
    out.update(
        window_status="OK",
        min_ttc_s=float(np.min(ttc_valid)) if len(ttc_valid) else None,
        n_ttc_samples_excluded=int((np.isfinite(ttc) & ~valid).sum()),
        vehicle_stopped_in_window=bool((speed <= 0).any()),
        max_abs_steering_angle_rad=float(np.nanmax(np.abs(steer[win]))),
        max_abs_steering_dev_from_baseline_rad=(
            float(np.nanmax(np.abs(steer[win] - np.nanmean(steer[base])))) if base.any() else None),
        max_longitudinal_accel_mps2=float(np.nanmax(ax)),
        max_longitudinal_decel_mps2=float(-np.nanmin(ax)),
    )
    return out


def reconciliation_rows(qa: pd.DataFrame, gaze: set) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for r in qa.itertuples():
        candidates, sources = [], []
        if r.tor_state == "MISSING_TOR_COLUMN":
            candidates.append("owner exclusion: control before TOR / forgot button (16)")
            sources.append("TOR column absent from file (inferred match to owner category)")
        if r.trial_id not in gaze:
            candidates.append("owner exclusion: hardware malfunction (part of 31)")
            sources.append("no eye-tracking gaze file in public archive (inferred)")
        rows.append({
            "trial_id": r.trial_id,
            "header_variant": r.header_variant,
            "tor_state": r.tor_state,
            "in_repo_tor_column_set": r.tor_state != "MISSING_TOR_COLUMN",
            "tor_anchor_resolved": bool(pd.notna(r.tor_selected)),
            "lane_change_state": r.lane_change_state,
            "gaze_file_present": r.trial_id in gaze,
            "owner_per_trial_status": "UNKNOWN (owner per-trial exclusion list not published)",
            "owner_exclusion_candidates": " | ".join(candidates),
            "candidate_evidence": " | ".join(sources),
            "candidate_provenance": "NEWLY_INFERRED" if candidates else "",
            "repo_tor_reason": ("REPO_DEFINED: TOR column absent" if r.tor_state == "MISSING_TOR_COLUMN"
                                else f"REPO_DEFINED: {r.tor_state}"),
        })
    return pd.DataFrame(rows)


def summary_markdown(qa: pd.DataFrame, rec: pd.DataFrame, met: pd.DataFrame) -> str:
    n_missing = int((qa.tor_state == "MISSING_TOR_COLUMN").sum())
    n_tor = int((qa.tor_state != "MISSING_TOR_COLUMN").sum())
    no_gaze = ~rec.gaze_file_present
    miss = rec.tor_state == "MISSING_TOR_COLUMN"
    lines = [
        "# R1 ingestion validation summary",
        "",
        "Generated by `src/experiments/r1_ingestion_validation.py`. Validation output, not a scientific finding.",
        "",
        "## TOR states",
        "",
        _md_table(qa.tor_state.value_counts().rename_axis("tor_state").reset_index(name="n")),
        "",
        f"- Raw trials: {len(qa)}; with TOR column: {n_tor}; without TOR column: {n_missing}.",
        f"- TOR anchor resolved (single or protocol-resolved): {int(qa.tor_selected.notna().sum())}.",
        "",
        "## Owner exclusion reconciliation (NOT reconciled)",
        "",
        f"- Owner report ({OWNER_REFERENCE}): {OWNER_N_RAW} raw → {OWNER_N_ANALYSED} analysed; exclusions "
        + "; ".join(f"{k}: {v}" for k, v in OWNER_EXCLUSIONS.items()) + ".",
        f"- Candidate for the owners' 16: {int(miss.sum())} trials without a TOR column (inferred).",
        f"- Trials without an eye-tracking gaze file: {int(no_gaze.sum())} "
        f"(overlap with no-TOR: {int((no_gaze & miss).sum())}); a possible, inferred match to part of the owners' 31.",
        "- Questionnaire completeness cannot be assessed: the public scenario-experience file has no missing values.",
        "- The owners' per-trial list is not published, so the 466-trial set cannot be reconstructed without "
        "undocumented assumptions. Status: **UNRECONCILED**.",
        "",
        "## Owner metric replication (definitions and counts)",
        "",
        "| Owner metric | Owner window | Our definition | Status |",
        "|---|---|---|---|",
        "| t_button | TOR → mode-switch press | `Manual_Start − TOR` (resolved TOR only) | computed |",
        "| minimum TTC | TOR → lane change | min of `Time_TTC` over [TOR, validated lane change], only samples with distance > 0, speed > 0 and TTC > 0 (the documented formula's domain); excluded samples counted | computed; owners' handling of stopped vehicles not stated |",
        "| maximum steering wheel angle | TOR → lane change | max abs(angle) and max abs(angle − pre-TOR baseline) (owners' variant not stated) | computed, definition ambiguous |",
        "| maximum acceleration | TOR → lane change | max `accel.001` | computed; axis/sign convention not stated by owners |",
        "| maximum deceleration | TOR → lane change | −min `accel.001` | computed; axis/sign convention not stated by owners |",
        "",
        f"- Trials with metrics over the owner window: {int((met.window_status == 'OK').sum())}; "
        f"without: {int((met.window_status != 'OK').sum())} "
        f"({met.window_status[met.window_status != 'OK'].str.split(' ').str[0].value_counts().to_dict()}).",
        f"- Trials where the vehicle stopped (speed ≤ 0) inside the owner window: "
        f"{int(met.vehicle_stopped_in_window.fillna(False).astype(bool).sum())}. Trials with TTC samples excluded "
        f"from minimum TTC: {int((met.n_ttc_samples_excluded.fillna(0) > 0).sum())}.",
        "- Owners' numerical results (means, distributions) were not available in the sources read, so no numerical "
        "comparison was made. This table validates that the ingestion supports their definitions; it is not a "
        "replication of their findings.",
        "",
        "## Descriptive distribution of replicated metrics (validation only)",
        "",
        _md_table(met[met.window_status == "OK"][["t_button_s", "min_ttc_s", "max_abs_steering_angle_rad",
                                                  "max_longitudinal_accel_mps2", "max_longitudinal_decel_mps2"]]
                  .astype(float).describe().round(3), index=True),
        "",
    ]
    return "\n".join(lines)


def run(archive_path: str = DEFAULT_ARCHIVE, output_dir: str = DEFAULT_OUTPUT) -> Dict[str, pd.DataFrame]:
    archive = D003Archive(archive_path)
    qa_rows, met_rows = [], []
    for name in archive.trial_names():
        trial = archive.load(name)
        qa_rows.append(audit_trial(trial))
        met_rows.append(owner_window_metrics(trial))
    qa = pd.DataFrame(qa_rows)
    met = pd.DataFrame(met_rows)
    rec = reconciliation_rows(qa, gaze_trials(archive_path))
    os.makedirs(output_dir, exist_ok=True)
    qa.to_csv(os.path.join(output_dir, "trial_qa.csv"), index=False)
    rec.to_csv(os.path.join(output_dir, "owner_reconciliation.csv"), index=False)
    met.to_csv(os.path.join(output_dir, "owner_metric_replication.csv"), index=False)
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(summary_markdown(qa, rec, met))
    return {"qa": qa, "reconciliation": rec, "metrics": met}


if __name__ == "__main__":
    run(*sys.argv[1:3])
