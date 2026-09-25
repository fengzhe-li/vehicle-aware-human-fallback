"""Phase R2A: observation-safe D003 descriptives (event timing and vehicle state).

Built only on the canonical strict ingestion (`src/data/d003_ingest.py`) and the
populations/windows in `src/data/d003_populations.py`.

Interpretation rule (blocker B17): the accelerator, brake and steering channels
are NOT driver-only channels. They may carry automation actuation,
simulator/controller activity, driver activity, or a mixture. Nothing in this
module infers human input, driver action or driver command from them. Such
channels appear only as neutral "channel activity" observations.

No model is fitted, no causal claim is made, no stabilisation metric is defined,
and no data at or after handback enters a manual-interval window.

Outputs (``results/R2A_event_vehicle_descriptives/``):

- ``populations.csv``: per-trial membership, exclusion reasons, events.
- ``event_and_vehicle_state_metrics.csv``: event timing (t_button, TOR to lane
  change) and vehicle-state quantities (minimum TTC in the approach domain,
  vehicle longitudinal acceleration/deceleration, hazard-station crossing), each
  under the owners' published window and, separately, the manual-interval window.
- ``control_channel_observations.csv``: neutral channel observations around TOR.
- ``channel_transition_pattern_by_cell.csv``: per-cell counts of the TOR-adjacent
  channel changes documented in blocker B17.
- ``channel_activity_diagnostics.csv``: window-restricted channel-activity counts
  (the withdrawn correction counts, re-examined as channel activity only).
- ``summary.md`` and ``provenance.json``.

Usage:
    python -m src.experiments.r2a_event_vehicle_descriptives [archive] [output_dir]
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

from src.data.d003_ingest import TTC_COLUMN, D003Archive
from src.data.d003_populations import (
    POPULATION_RULES,
    WINDOW_DEFINITIONS,
    TrialPopulation,
    classify_trial,
    window_bounds,
    window_mask,
)
from src.metrics.control_activity import count_hysteresis_reversals, count_signal_peaks, lowpass

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_OUTPUT = "results/R2A_event_vehicle_descriptives"

BRAKE = "[00].VehicleUpdate-brake"
STEER = "[00].VehicleUpdate-steeringWheelAngle"
ACCEL_PEDAL = "[00].VehicleUpdate-accelerator"
AX = "[00].VehicleUpdate-accel.001"
SPEED = "[00].VehicleUpdate-speed.001"
DIST = "[85 (Distance/Distance_to_Construction)].ExportChannel-val"

TRANSITION_WINDOW_S = 0.3        # "immediately after TOR", before plausible human reaction
PRE_TOR_WINDOW_S = (4.0, 0.2)    # [TOR - 4.0, TOR - 0.2]
ACCEL_CHANNEL_ACTIVE = 0.02
ACCEL_CHANNEL_NEAR_ZERO = 0.005
BRAKE_CHANNEL_ACTIVE = 5.0
STEER_CHANNEL_MOVING_RAD = 0.02
BRAKE_CHANNEL_ONSET = 15.0       # channel units (dictionary: "brake force, N")
STEER_CHANNEL_ONSET_RAD = 0.05
REVERSAL_GAPS_DEG = (1.0, 2.0, 3.0, 5.0)
PEAK_PROMINENCES = (5.0, 15.0, 30.0)
HISTORICAL_ACUTE_S = 8.0

UNRESOLVED_DEPENDENCIES = [
    "B17: accelerator, brake and steering channel authorship (automation / simulator / driver / mixed) UNRESOLVED",
    "B6: brake channel physical meaning and unit UNRESOLVED",
    "B7: Manual_Start as authority transfer UNRESOLVED (used only as a button/event marker)",
    "B14: meaning of additional Manual_Stop values UNRESOLVED",
    "B12: owners' 466-trial analysis set NOT RECONSTRUCTED",
]

STATUS_TABLE = [
    ("t_button = Manual_Start − TOR", "VALIDATED MEASUREMENT", "event timing of the mode-switch press; not authority transfer"),
    ("TOR → validated lane change duration", "VALIDATED MEASUREMENT", "both events validated per trial"),
    ("minimum TTC in the approach domain", "PROVISIONAL MEASUREMENT", "domain rule (distance > 0, speed > 0, TTC > 0) is ours; owners' handling not stated"),
    ("vehicle maximum longitudinal acceleration / deceleration", "VEHICLE-STATE DESCRIPTIVE", "kinematics only; not attributed to the driver"),
    ("longitudinal hazard-station crossing (T_pass)", "VEHICLE-STATE DESCRIPTIVE", "geometric crossing only; not clearance, not collision"),
    ("steering-wheel-angle channel maxima (owners' 'maximum steering angle')", "UNRESOLVED CHANNEL AUTHORSHIP", "channel observation; not attributed to the driver"),
    ("earliest brake/steering channel activity after TOR", "UNRESOLVED CHANNEL AUTHORSHIP", "not a human first input"),
    ("window-restricted channel reversal / peak counts", "UNRESOLVED CHANNEL AUTHORSHIP", "diagnostic of channel activity only"),
    ("T_first / first brake / first steering input as human response", "WITHDRAWN", "INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS"),
    ("brake-first vs steer-first; negative handover lag; brake-rise latency", "WITHDRAWN", "INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS"),
    ("maximum braking / steering attributed to the driver", "WITHDRAWN", "INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS"),
    ("correction counts as human corrections", "WITHDRAWN", "full-record windows and channel authorship"),
    ("T_stable", "WITHDRAWN", "window extends past handback"),
    ("collision proxy", "WITHDRAWN", "disagrees with lane evidence; hazard geometry unidentified"),
]


def _baseline(t: np.ndarray, x: np.ndarray, t_tor: float) -> float:
    m = (t >= t_tor - PRE_TOR_WINDOW_S[0]) & (t <= t_tor - PRE_TOR_WINDOW_S[1])
    return float(np.nanmean(x[m])) if m.any() else float("nan")


def _vehicle_state_in_window(trial, pop: TrialPopulation, window: str, prefix: str) -> Dict[str, object]:
    t = trial.telemetry["t_rel"].to_numpy()
    start, end = window_bounds(pop, window)
    m = window_mask(t, pop, window)
    ttc, v, d, ax = (trial.column(c)[m] for c in (TTC_COLUMN, SPEED, DIST, AX))
    valid = (v > 0) & (d > 0) & np.isfinite(ttc) & (ttc > 0)
    return {
        f"{prefix}window_start": start,
        f"{prefix}window_end": end,
        f"{prefix}tor_to_lane_change_s": end - start,
        f"{prefix}min_ttc_approach_domain_s": float(ttc[valid].min()) if valid.any() else None,
        f"{prefix}n_ttc_samples_outside_domain": int((np.isfinite(ttc) & ~valid).sum()),
        f"{prefix}vehicle_stopped_in_window": bool((v <= 0).any()),
        f"{prefix}vehicle_max_longitudinal_accel_mps2": float(np.nanmax(ax)),
        f"{prefix}vehicle_max_longitudinal_decel_mps2": float(-np.nanmin(ax)),
    }


def event_vehicle_row(trial, pop: TrialPopulation) -> Dict[str, object]:
    ev = pop.events
    t = trial.telemetry["t_rel"].to_numpy()
    row: Dict[str, object] = {
        "trial_id": trial.meta.trial_id, "density": trial.meta.density, "nback": trial.meta.nback,
        "OWNER_WINDOW_ELIGIBLE": pop.owner_window_eligible,
        "LANE_CHANGE_ANCHORED": pop.lane_change_anchored,
        "t_button_s": (ev.t_manual_start - ev.t_tor) if pop.tor_anchored and ev.t_manual_start is not None else None,
        "t_handback": pop.handback,
        "vehicle_speed_at_tor_mps": None,
        "hazard_station_crossing_after_tor_s": None,
        "hazard_station_crossing_after_handback": None,
        "owner_window_excluded_reason": pop.reasons.get("OWNER_WINDOW_ELIGIBLE", ""),
        "manual_window_excluded_reason": pop.reasons.get("LANE_CHANGE_ANCHORED", ""),
    }
    if pop.tor_anchored:
        i = int(np.searchsorted(t, ev.t_tor))
        row["vehicle_speed_at_tor_mps"] = float(trial.column(SPEED)[min(i, len(t) - 1)])
        d = trial.column(DIST)
        k = np.where((t >= ev.t_tor) & (d <= 0))[0]
        if len(k):
            row["hazard_station_crossing_after_tor_s"] = float(t[k[0]] - ev.t_tor)
            row["hazard_station_crossing_after_handback"] = (
                None if pop.handback is None else bool(t[k[0]] >= pop.handback))
    if pop.owner_window_eligible:
        row.update(_vehicle_state_in_window(trial, pop, "OWNER_TOR_TO_LANE_CHANGE", "owner_"))
    if pop.lane_change_anchored:
        row.update(_vehicle_state_in_window(trial, pop, "MANUAL_TOR_TO_LANE_CHANGE", "manual_"))
    return row


def channel_observation_row(trial, pop: TrialPopulation) -> Dict[str, object]:
    """Neutral channel observations around TOR (B17 evidence). No authorship is assigned."""
    ev = pop.events
    t = trial.telemetry["t_rel"].to_numpy()
    t0 = ev.t_tor
    pre = (t >= t0 - PRE_TOR_WINDOW_S[0]) & (t <= t0 - PRE_TOR_WINDOW_S[1])
    post = (t >= t0) & (t < t0 + TRANSITION_WINDOW_S)
    acc, brake, steer = trial.column(ACCEL_PEDAL), trial.column(BRAKE), trial.column(STEER)
    manual = window_mask(t, pop, "POST_TOR_MANUAL")
    b_on = np.where(manual & (brake > BRAKE_CHANNEL_ONSET))[0]
    s_on = np.where(manual & (np.abs(steer - _baseline(t, steer, t0)) > STEER_CHANNEL_ONSET_RAD))[0]
    b_s = float(t[b_on[0]] - t0) if len(b_on) else None
    s_s = float(t[s_on[0]] - t0) if len(s_on) else None
    earliest = min([x for x in (b_s, s_s) if x is not None], default=None)
    row = {
        "trial_id": trial.meta.trial_id, "density": trial.meta.density, "nback": trial.meta.nback,
        "accelerator_channel_pre_tor_mean": float(np.nanmean(acc[pre])),
        "accelerator_channel_min_0_to_0p3s": float(np.nanmin(acc[post])),
        "accelerator_channel_drops_to_zero_within_0p3s": bool(
            np.nanmean(acc[pre]) > ACCEL_CHANNEL_ACTIVE and np.nanmin(acc[post]) < ACCEL_CHANNEL_NEAR_ZERO),
        "brake_channel_max_0_to_0p3s": float(np.nanmax(brake[post])),
        "brake_channel_active_within_0p3s": bool(np.nanmax(brake[post]) > BRAKE_CHANNEL_ACTIVE),
        "steering_channel_pre_tor_range_rad": float(np.ptp(steer[pre])),
        "steering_channel_moving_before_tor": bool(np.ptp(steer[pre]) > STEER_CHANNEL_MOVING_RAD),
        "brake_channel_onset_after_tor_s": b_s,
        "steering_channel_onset_after_tor_s": s_s,
        "earliest_channel_activity_after_tor_s": earliest,
        "earliest_channel_activity_within_0p3s": None if earliest is None else earliest < TRANSITION_WINDOW_S,
        "earliest_channel_activity_minus_manual_start_s": None if earliest is None else earliest + t0 - ev.t_manual_start,
        "authorship": "UNRESOLVED (B17)",
    }
    if pop.owner_window_eligible:
        m = window_mask(t, pop, "OWNER_TOR_TO_LANE_CHANGE")
        row["steering_channel_max_abs_in_owner_window_rad"] = float(np.nanmax(np.abs(steer[m])))
        row["steering_channel_max_abs_dev_in_owner_window_rad"] = float(np.nanmax(np.abs(steer[m] - _baseline(t, steer, t0))))
    return row


def channel_activity_rows(trial, pop: TrialPopulation) -> List[Dict[str, object]]:
    """Window-restricted channel-activity counts plus the invalid full-record comparators."""
    t = trial.telemetry["t_rel"].to_numpy()
    steer, brake = trial.column(STEER), trial.column(BRAKE)
    t0 = pop.events.t_tor
    windows = {
        "POST_TOR_MANUAL": window_mask(t, pop, "POST_TOR_MANUAL"),
        "POST_BUTTON_MANUAL": window_mask(t, pop, "POST_BUTTON_MANUAL"),
        "HISTORICAL_ACUTE_8S_POST_TOR": (t >= t0) & (t <= t0 + HISTORICAL_ACUTE_S),
        "HISTORICAL_FULL_RECORD_POST_TOR_INVALID": t >= t0,
    }
    rows = []
    for name, m in windows.items():
        base = {"trial_id": trial.meta.trial_id, "density": trial.meta.density, "nback": trial.meta.nback,
                "window": name,
                "window_duration_s": float(t[m][-1] - t[m][0]) if m.sum() > 1 else 0.0,
                "window_reaches_handback": bool(m.any() and t[m][-1] >= pop.handback),
                "authorship": "UNRESOLVED (B17)"}
        for gap in REVERSAL_GAPS_DEG:
            for filt, sig in (("raw", steer[m]), ("lowpass2Hz", lowpass(steer[m]))):
                rows.append({**base, "observation": "steering_channel_hysteresis_reversals",
                             "detector": f"gap{gap:g}deg_{filt}", "value": count_hysteresis_reversals(sig, np.radians(gap))})
        for prom in PEAK_PROMINENCES:
            rows.append({**base, "observation": "brake_channel_peaks", "detector": f"prominence{prom:g}",
                         "value": count_signal_peaks(brake[m], prom)})
    return rows


def archive_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> Dict[str, object]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"],
                               capture_output=True, text=True, check=True).stdout.strip() != ""
        return {"code_commit": commit, "src_tree_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"code_commit": "UNKNOWN", "src_tree_dirty": None}


def _q(s: pd.Series) -> str:
    s = pd.to_numeric(s, errors="coerce").dropna()
    return "n=0" if not len(s) else f"n={len(s)}; median {s.median():.3g} (IQR {s.quantile(.25):.3g}–{s.quantile(.75):.3g})"


def _md(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(out)


def pattern_by_cell(obs: pd.DataFrame) -> pd.DataFrame:
    return obs.groupby(["density", "nback"]).agg(
        n_trials=("trial_id", "size"),
        accelerator_channel_drops_to_zero_within_0p3s=("accelerator_channel_drops_to_zero_within_0p3s", "sum"),
        brake_channel_active_within_0p3s=("brake_channel_active_within_0p3s", "sum"),
        steering_channel_moving_before_tor=("steering_channel_moving_before_tor", "sum"),
        earliest_channel_activity_within_0p3s=("earliest_channel_activity_within_0p3s", lambda s: int(s.fillna(False).astype(bool).sum())),
    ).reset_index()


def summarise(pops, ev, obs, pattern, act, prov) -> str:
    counts = {k: int(pops[k].sum()) for k in POPULATION_RULES if k != "OWNER_ANALYSIS_SET"}
    ow, mw = ev[ev.OWNER_WINDOW_ELIGIBLE], ev[ev.LANE_CHANGE_ANCHORED]
    L = ["# R2A: observation-safe D003 descriptives (event timing and vehicle state)", "",
         "**Interpretation rule (B17):** accelerator, brake and steering channels are not driver-only channels. "
         "Nothing here is a driver action, driver command or human input. No model fitted; no causal claim; no "
         "stabilisation metric. Scenario cells are descriptive only: they are aliased with road, speed, hazard state, "
         "lane configuration, run timing and automation-transition behaviour (B11).", "",
         f"Source archive sha256 `{prov['archive_sha256']}`; code commit `{prov['code_commit']}` "
         f"(src/ dirty at generation: {prov['src_tree_dirty']}).", "",
         "## Populations", "",
         _md(pd.DataFrame([{"population": k, "n": counts.get(k, "UNKNOWN / NOT RECONSTRUCTED"), "rule": v}
                           for k, v in POPULATION_RULES.items()])), "",
         "There is no universal clean denominator. A trial can be eligible for one metric and not another: e.g. "
         "the 6 multi-TOR-unresolved trials have valid Manual_Start/Manual_Stop events but no TOR anchor, so they "
         "enter no TOR-anchored metric; the 13 trials without a lane-change channel (plus 1 lane-change clock "
         "exception) have TOR-anchored manual windows but no lane-change window; one trial "
         "(lane change after handback) is in the owners' window but not in the manual-interval lane-change window.", "",
         "## Windows", "", _md(pd.DataFrame([{"window": k, "definition": v} for k, v in WINDOW_DEFINITIONS.items()])), "",
         "Handback (first Manual_Stop after Manual_Start) is a protocol-driven competing event, not independent censoring. "
         "The owners' published window and the handback-bounded window are stored separately (`owner_*` and `manual_*` columns).", "",
         "## Event timing and vehicle-state quantities", "",
         "| Quantity | Window | Denominator | Result |", "|---|---|---|---|",
         f"| t_button (Manual_Start − TOR) | event difference | TOR_ANCHORED with Manual_Start | {_q(ev.t_button_s)} s |",
         f"| TOR → lane change | owners' published | OWNER_WINDOW_ELIGIBLE | {_q(ow.owner_tor_to_lane_change_s)} s |",
         f"| TOR → lane change | manual-interval | LANE_CHANGE_ANCHORED | {_q(mw.manual_tor_to_lane_change_s)} s |",
         f"| minimum TTC, approach domain | owners' published | OWNER_WINDOW_ELIGIBLE | {_q(ow.owner_min_ttc_approach_domain_s)} s |",
         f"| minimum TTC, approach domain | manual-interval | LANE_CHANGE_ANCHORED | {_q(mw.manual_min_ttc_approach_domain_s)} s |",
         f"| vehicle max longitudinal acceleration | owners' published | OWNER_WINDOW_ELIGIBLE | {_q(ow.owner_vehicle_max_longitudinal_accel_mps2)} m/s² |",
         f"| vehicle max longitudinal deceleration | owners' published | OWNER_WINDOW_ELIGIBLE | {_q(ow.owner_vehicle_max_longitudinal_decel_mps2)} m/s² |",
         f"| vehicle max longitudinal deceleration | manual-interval | LANE_CHANGE_ANCHORED | {_q(mw.manual_vehicle_max_longitudinal_decel_mps2)} m/s² |",
         f"| vehicle speed at TOR | TOR sample | TOR_ANCHORED | {_q(ev.vehicle_speed_at_tor_mps)} m/s |",
         f"| hazard-station crossing after TOR | first distance ≤ 0 | TOR_ANCHORED with a crossing | {_q(ev.hazard_station_crossing_after_tor_s)} s |",
         "",
         "The owners (arXiv 2507.22252) report 'maximum deceleration' and 'maximum acceleration' as takeover-quality "
         "indicators. Here they are **vehicle kinematics** only: under B17, automation or simulator activity may "
         "contribute, so they are not evidence of driver braking. The sources read gave no owner numerical values, "
         "so these are definition-compatible measurements, not numerical replications.", "",
         "## Control-channel observations around TOR (B17 evidence; authorship UNRESOLVED)", "",
         f"Denominator: MANUAL_WINDOW_ELIGIBLE (n={len(obs)}). Within 0.3 s of TOR (before plausible human reaction):", "",
         _md(pattern), "",
         "The pattern is scenario-cell-specific. It is **consistent with** different automation-transition behaviours "
         "across cells (for example, accelerator actuation released at TOR in some cells and held in others), but the "
         "controller semantics are undocumented and no transition policy is inferred.", "",
         f"- Earliest brake/steering channel activity after TOR: {_q(obs.earliest_channel_activity_after_tor_s)} s; "
         f"relative to Manual_Start: {_q(obs.earliest_channel_activity_minus_manual_start_s)} s. These are channel "
         "observations, not human first inputs.",
         f"- Steering-wheel-angle channel maximum in the owners' window (owners' 'maximum steering angle'): "
         f"{_q(obs.steering_channel_max_abs_in_owner_window_rad)} rad (authorship UNRESOLVED).", ""]
    g = act.groupby(["observation", "detector", "window"]).value.median().unstack("window")
    order = ["POST_TOR_MANUAL", "POST_BUTTON_MANUAL", "HISTORICAL_ACUTE_8S_POST_TOR", "HISTORICAL_FULL_RECORD_POST_TOR_INVALID"]
    g = g[[o for o in order if o in g.columns]].reset_index().round(2)
    L += ["## Channel-activity diagnostics (withdrawn correction counts, re-examined as channel activity)", "",
          f"Denominator: MANUAL_WINDOW_ELIGIBLE (n={act.trial_id.nunique()}). Medians per trial:", "", _md(g), "",
          "Counts depend strongly on the detector (hysteresis gap, prominence) and scale with window length, which "
          "ends at a protocol-driven handback. They are not promoted to any human-correction metric. Historical "
          "pre-audit values (INVALID): median 3 brake extrema, 2 brake reapplications and 13 steering reversals over "
          "the full post-TOR record; 2 reversals in the 8 s acute window.", "",
          "## Status of candidate quantities", "",
          _md(pd.DataFrame(STATUS_TABLE, columns=["quantity", "status", "note"])), ""]
    return "\n".join(L).rstrip("\n") + "\n"


def run(archive_path: str = DEFAULT_ARCHIVE, output_dir: str = DEFAULT_OUTPUT) -> Dict[str, object]:
    archive = D003Archive(archive_path)
    pop_rows, ev_rows, obs_rows, act_rows = [], [], [], []
    for name in archive.trial_names():
        trial = archive.load(name)
        pop = classify_trial(trial)
        e = pop.events
        pop_rows.append({
            "trial_id": pop.trial_id, "participant_id": trial.meta.participant_id,
            "density": trial.meta.density, "nback": trial.meta.nback,
            "RAW": True, "TOR_PRESENT": pop.tor_present, "TOR_ANCHORED": pop.tor_anchored,
            "OWNER_WINDOW_ELIGIBLE": pop.owner_window_eligible,
            "LANE_CHANGE_ANCHORED": pop.lane_change_anchored,
            "MANUAL_WINDOW_ELIGIBLE": pop.manual_window_eligible,
            "OWNER_ANALYSIS_SET": "UNKNOWN",
            "tor_state": e.tor.state, "lane_change_state": e.lane_change.state, "handback_state": e.handback.state,
            "t_tor": e.t_tor, "t_manual_start": e.t_manual_start, "t_lane_change": e.lane_change.value,
            "t_handback": pop.handback,
            **{f"excluded_from_{k}": v for k, v in pop.reasons.items()},
        })
        ev_rows.append(event_vehicle_row(trial, pop))
        if pop.manual_window_eligible:
            obs_rows.append(channel_observation_row(trial, pop))
            act_rows.extend(channel_activity_rows(trial, pop))
    archive.close()
    pops, ev, obs, act = (pd.DataFrame(x) for x in (pop_rows, ev_rows, obs_rows, act_rows))
    pattern = pattern_by_cell(obs)
    prov = {
        "archive_path": archive_path,
        "archive_sha256": archive_sha256(archive_path),
        "archive_source": "TU Delft / 4TU.ResearchData, DOI 10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB",
        **git_state(),
        "ingestion": "src/data/d003_ingest.py (canonical)",
        "interpretation_rule": "B17: accelerator/brake/steering channels are not driver-only; no human-input inference",
        "populations": POPULATION_RULES,
        "windows": WINDOW_DEFINITIONS,
        "unresolved_semantic_dependencies": UNRESOLVED_DEPENDENCIES,
        "outputs": {
            "populations.csv": "RAW (all trials)",
            "event_and_vehicle_state_metrics.csv": "RAW rows; t_button for TOR_ANCHORED; owner_* for OWNER_WINDOW_ELIGIBLE; manual_* for LANE_CHANGE_ANCHORED",
            "control_channel_observations.csv": "MANUAL_WINDOW_ELIGIBLE; windows: pre-TOR [TOR-4, TOR-0.2], post-TOR [TOR, TOR+0.3), POST_TOR_MANUAL, OWNER_TOR_TO_LANE_CHANGE",
            "channel_transition_pattern_by_cell.csv": "MANUAL_WINDOW_ELIGIBLE, grouped by scenario cell (descriptive)",
            "channel_activity_diagnostics.csv": "MANUAL_WINDOW_ELIGIBLE; one row per trial x window (POST_TOR_MANUAL, POST_BUTTON_MANUAL and two historical comparators); authorship UNRESOLVED (B17)",
        },
    }
    os.makedirs(output_dir, exist_ok=True)
    pops.to_csv(os.path.join(output_dir, "populations.csv"), index=False)
    ev.to_csv(os.path.join(output_dir, "event_and_vehicle_state_metrics.csv"), index=False)
    obs.to_csv(os.path.join(output_dir, "control_channel_observations.csv"), index=False)
    pattern.to_csv(os.path.join(output_dir, "channel_transition_pattern_by_cell.csv"), index=False)
    wide = act.pivot_table(
        index=["trial_id", "density", "nback", "window", "window_duration_s", "window_reaches_handback"],
        columns=["observation", "detector"], values="value", aggfunc="first")
    wide.columns = [f"{o}__{d}" for o, d in wide.columns]
    wide.reset_index().to_csv(os.path.join(output_dir, "channel_activity_diagnostics.csv"), index=False)
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(summarise(pops, ev, obs, pattern, act, prov))
    return {"populations": pops, "events": ev, "observations": obs, "pattern": pattern, "activity": act,
            "provenance": prov}


if __name__ == "__main__":
    run(*sys.argv[1:3])
