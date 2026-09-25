"""R4V: D003 control-channel authorship validation.

Tests whether D003 signal behaviour is consistent with the archive-documented design
intent that Manual_Start (button, "switched to manual mode"; owners: pressed "to enable
manual inputs") enables manual control. Correlation is never treated as authorship; the
classification uses pre-stated criteria (AUTHORSHIP_CRITERIA) combining documented
channel semantics with signal behaviour.

Windows per trial (seconds, t_rel clock): pre-TOR [TOR-4, TOR-0.2]; TOR->MS [TOR, MS);
post-MS [MS, MS+2); manual [MS+2, handback); after handback [handback+1, handback+4).

Usage: python -m src.experiments.r4v_channel_authorship [archive] [output_dir]
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.data.d003_ingest import (BRAKE_CANDIDATE_THRESHOLD, STEER_CANDIDATE_THRESHOLD_RAD, D003Archive,
                                  classify_adjacent_lane_values, observation_events)
from src.experiments.r2a_event_vehicle_descriptives import archive_sha256, git_state

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_OUTPUT = "results/R4V_channel_authorship"

COL = {
    "brake": "[00].VehicleUpdate-brake",
    "accel_pedal": "[00].VehicleUpdate-accelerator",
    "steer_angle": "[00].VehicleUpdate-steeringWheelAngle",
    "steer_speed": "[00].VehicleUpdate-steeringWheelSpeed",
    "steer_torque": "[00].VehicleUpdate-steeringTorq",
    "state": "[00].VehicleUpdate-state",
    "lights": "[00].VehicleUpdate-lights",
    "indicators": "[00].VehicleUpdate-indicators",
    "ax": "[00].VehicleUpdate-accel.001",
    "abscissa": "[00].VehicleUpdate-roadInfo-roadAbscissa.0",
    "road_id": "[00].VehicleUpdate-roadInfo-roadId.0",
    "d_construction": "[85 (Distance/Distance_to_Construction)].ExportChannel-val",
    "d_follow": "[82 (Distance/Distance_to_Following_Vehicle)].ExportChannel-val",
    "d_lead_next": "[83 (Distance/Distance_to_Leading_Vehicle_Next_Lane)].ExportChannel-val",
    "d_follow_next": "[84 (Distance/Distance_to_Following_Vehicle_Next_Lane)].ExportChannel-val",
}

# Thresholds (stated before computing results)
BRAKE_T = BRAKE_CANDIDATE_THRESHOLD           # 15 channel units (reused from ingestion)
STEER_T = STEER_CANDIDATE_THRESHOLD_RAD       # 0.05 rad deviation (reused from ingestion)
ACCEL_T = 0.02                                # accelerator activity, fraction of full travel (new)
STEREO_FRACTION, STEREO_IQR_S = 0.9, 0.10     # cell-locked stereotypy: >=90% of trials, onset IQR <= 0.1 s
MAX_LAG_S = 0.5                               # brake -> deceleration coupling lag search

AUTHORSHIP_CRITERIA = {
    "a1_documented_as_control_input": "data dictionary documents the channel as a control-input quantity",
    "a2_no_automation_signature_after_MS": "no scenario cell shows cell-locked stereotyped post-MS activity "
                                           f"(>= {STEREO_FRACTION:.0%} of trials with onset IQR <= {STEREO_IQR_S} s)",
    "a3_participant_structure": "post-MS onset latency: participant ICC(1) > 0.1 and cell eta^2 < 0.5",
    "a4_mode_locked_automation_content": "automation-like content present while automation drives is absent "
                                         "between MS and handback",
    "a5_vehicle_response_consistency": "post-MS channel activity is followed by the expected vehicle response "
                                       "(consistency only, not authorship)",
    "classes": {
        "DRIVER_AUTHORSHIP_SUPPORTED": "a1-a5 all hold",
        "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED": "a1 and a2 hold, but a3 or a4 is not established",
        "MIXED_OR_AMBIGUOUS": "a2 fails, or evidence conflicts",
        "NOT_IDENTIFIABLE": "a1 fails (semantics undocumented) and behaviour cannot discriminate",
    },
}


# Post-rule scientific review (stated after inspecting the rule output; disclosed as such).
# A review may only DOWNGRADE a rule verdict, never upgrade it.
REVIEW_OVERRIDES = {
    "steering_wheel_angle": (
        "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED",
        "rule verdict SUPPORTED not accepted: while automation drives, the angle is cell-locked (pre-TOR mean "
        "angle near-identical within a scenario cell, eta^2 ~1) and changes at TOR in whole cells only, so the same "
        "channel carries scenario/automation-driven content under undocumented logic; post-MS onset ICC(1) (~0.16) "
        "is only marginally above the 0.1 criterion"),
    "left_indicator": (
        "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED",
        "channel is not in the data dictionary (a1 fails); the 1 = left mapping is inferred; behaviour "
        "(never before MS, not stereotyped, precedes lane crossing) is corroborative only"),
}
ORDER = ["NOT_IDENTIFIABLE", "MIXED_OR_AMBIGUOUS", "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED",
         "DRIVER_AUTHORSHIP_SUPPORTED"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def first_crossing(t: np.ndarray, x: np.ndarray, t0: float, t1: float, pred) -> Optional[float]:
    m = (t >= t0) & (t < t1)
    idx = np.where(m & pred(x))[0]
    return float(t[idx[0]]) if len(idx) else None


def lagged_coupling(t, u, y, t0, t1, max_lag=MAX_LAG_S) -> Optional[float]:
    """Max correlation of u(t) with y(t + lag), lag in [0, max_lag]; None if u does not vary."""
    m = (t >= t0) & (t < t1)
    if m.sum() < 10 or np.nanstd(u[m]) < 1e-6:
        return None
    dt = float(np.nanmedian(np.diff(t)))
    best = None
    for k in range(0, int(round(max_lag / dt)) + 1):
        idx = np.where(m)[0]
        idx = idx[idx + k < len(y)]
        a, b = u[idx], y[idx + k]
        ok = ~(np.isnan(a) | np.isnan(b))
        if ok.sum() < 10 or np.std(a[ok]) < 1e-9 or np.std(b[ok]) < 1e-9:
            continue
        c = float(np.corrcoef(a[ok], b[ok])[0, 1])
        best = c if best is None or c > best else best
    return best


def icc1(values: pd.Series, groups: pd.Series) -> Optional[float]:
    """One-way random-effects ICC(1) with unequal group sizes."""
    d = pd.DataFrame({"y": values, "g": groups}).dropna()
    counts = d.groupby("g").size()
    d = d[d.g.isin(counts[counts >= 2].index)]
    if d.g.nunique() < 3:
        return None
    grand = d.y.mean()
    gm = d.groupby("g").y.agg(["mean", "size"])
    k = len(gm); n = len(d)
    msb = (gm["size"] * (gm["mean"] - grand) ** 2).sum() / (k - 1)
    msw = ((d.y - d.g.map(gm["mean"])) ** 2).sum() / (n - k)
    k0 = (n - (gm["size"] ** 2).sum() / n) / (k - 1)
    return float((msb - msw) / (msb + (k0 - 1) * msw))


def eta2(values: pd.Series, groups: pd.Series) -> Optional[float]:
    d = pd.DataFrame({"y": values, "g": groups}).dropna()
    if len(d) < 3 or d.y.var() == 0:
        return None
    ss_b = (d.groupby("g").y.transform("mean") - d.y.mean()).pow(2).sum()
    return float(ss_b / ((d.y - d.y.mean()) ** 2).sum())


# ---------------------------------------------------------------------------
# per-trial features
# ---------------------------------------------------------------------------


def trial_features(tr) -> Optional[Dict[str, object]]:
    ev = observation_events(tr)
    if ev.t_tor is None or ev.t_manual_start is None:
        return None
    t = tr.telemetry["t_rel"].to_numpy()
    x = {k: tr.column(c) for k, c in COL.items() if tr.has(c)}
    tor, ms = ev.t_tor, ev.t_manual_start
    hb = ev.handback.first_manual_episode_end
    lc = ev.lane_change.value if ev.lane_change.state == "VALIDATED" else None
    end = hb if hb is not None else ms + 10.0
    pre = (t >= tor - 4.0) & (t <= tor - 0.2)
    torms = (t >= tor) & (t < ms)
    post2 = (t >= ms) & (t < ms + 2.0)
    manual = (t >= ms + 2.0) & (t < end)
    after = (t >= end + 1.0) & (t < end + 4.0) if hb is not None else np.zeros_like(t, dtype=bool)
    br, ap, sa, sq, ax = x["brake"], x["accel_pedal"], x["steer_angle"], x["steer_torque"], x["ax"]

    def mean(v, m):
        return float(np.nanmean(v[m])) if m.any() else None

    def std(v, m):
        return float(np.nanstd(v[m])) if m.any() else None

    f = {"trial_id": tr.meta.trial_id, "participant_id": tr.meta.participant_id,
         "cell": f"d{tr.meta.density}_n{tr.meta.nback}", "t_tor": tor, "t_ms": ms, "t_handback": hb, "t_lane_change": lc,
         "t_button_s": ms - tor}
    # state flag
    f["state_values"] = ";".join(str(v) for v in sorted(set(np.unique(x["state"][~np.isnan(x["state"])]).tolist())))
    # brake
    f["brake_active_pre_tor"] = bool((br[pre] > BRAKE_T).any())
    b_torms = first_crossing(t, br, tor, ms, lambda v: v > BRAKE_T)
    f["brake_onset_tor_ms_rel_tor_s"] = (b_torms - tor) if b_torms is not None else None
    b_post = first_crossing(t, br, ms, end, lambda v: v > BRAKE_T)
    f["brake_onset_after_ms_rel_ms_s"] = (b_post - ms) if b_post is not None else None
    f["brake_active_at_ms"] = bool(np.nanmax(br[(t >= ms - 0.1) & (t <= ms + 0.05)], initial=0) > BRAKE_T)
    f["brake_peak_tor_ms"] = float(np.nanmax(br[torms], initial=0.0))
    f["brake_peak_post_ms"] = float(np.nanmax(br[(t >= ms) & (t < end)], initial=0.0))
    f["brake_max_value_trial"] = float(np.nanmax(br))
    # automation transient straddling MS: brake already active at MS, and when it first releases
    if f["brake_active_at_ms"]:
        rel_b = first_crossing(t, br, ms, end, lambda v: v < BRAKE_T)
        f["brake_straddle_release_rel_ms_s"] = (rel_b - ms) if rel_b is not None else None
        f["brake_straddle_release_rel_tor_s"] = (rel_b - tor) if rel_b is not None else None
        clean_from = rel_b
    else:
        f["brake_straddle_release_rel_ms_s"] = f["brake_straddle_release_rel_tor_s"] = None
        clean_from = ms
    i_ms_ = int(np.argmin(np.abs(t - ms)))
    w_step = (t >= ms - 0.2) & (t <= ms + 0.2)
    f["brake_max_step_near_ms"] = float(np.nanmax(np.abs(np.diff(br[w_step])))) if w_step.sum() > 2 else None
    clean = first_crossing(t, br, clean_from + 1e-9, end, lambda v: v > BRAKE_T) if clean_from is not None else None
    f["brake_clean_onset_rel_ms_s"] = (clean - ms) if clean is not None else None
    f["brake_decel_coupling_tor_ms"] = lagged_coupling(t, br, -ax, tor, ms)
    f["brake_decel_coupling_post_ms"] = lagged_coupling(t, br, -ax, ms, end)
    f["ax_mean_tor_ms"] = mean(ax, torms)
    # accelerator
    f["accel_mean_pre_tor"] = mean(ap, pre)
    f["accel_active_at_ms"] = bool(ap[int(np.argmin(np.abs(t - ms)))] > ACCEL_T)
    drop = first_crossing(t, ap, ms, end, lambda v: v < ACCEL_T) if f["accel_active_at_ms"] else None
    f["accel_straddle_drop_rel_ms_s"] = (drop - ms) if drop is not None else None
    rel = first_crossing(t, ap, tor, end, lambda v: v < ACCEL_T)
    f["accel_release_rel_tor_s"] = (rel - tor) if rel is not None else None
    f["accel_mean_tor_ms"] = mean(ap, torms)
    a_post = first_crossing(t, ap, ms, end, lambda v: v > ACCEL_T)
    f["accel_onset_after_ms_rel_ms_s"] = (a_post - ms) if a_post is not None else None
    f["accel_mean_manual"] = mean(ap, manual)
    f["accel_mean_after_handback"] = mean(ap, after)
    # steering angle / torque
    f["steer_mean_pre_tor"], f["steer_std_pre_tor"] = mean(sa, pre), std(sa, pre)
    f["steer_mean_tor_ms"], f["steer_std_tor_ms"] = mean(sa, torms), std(sa, torms)
    i_ms = int(np.argmin(np.abs(t - ms)))
    s_on = first_crossing(t, np.abs(sa - sa[i_ms]), ms, end, lambda v: v > STEER_T)
    f["steer_onset_after_ms_rel_ms_s"] = (s_on - ms) if s_on is not None else None
    f["steer_onset_to_lane_crossing_s"] = (lc - s_on) if (lc is not None and s_on is not None) else None
    i_tor = int(np.argmin(np.abs(t - tor)))
    f["steer_moved_tor_ms"] = bool((np.abs(sa[torms] - sa[i_tor]) > STEER_T).any()) if torms.any() else False
    f["torque_mean_pre_tor"], f["torque_std_pre_tor"] = mean(sq, pre), std(sq, pre)
    f["torque_mean_tor_ms"], f["torque_std_tor_ms"] = mean(sq, torms), std(sq, torms)
    f["torque_std_manual"] = std(sq, manual)
    f["torque_mean_after_handback"] = mean(sq, after)
    f["steer_mean_after_handback"] = mean(sa, after)
    # indicator: NOT in the data dictionary; 1 = left is inferred from the documented left lane change
    ind_on = first_crossing(t, x["indicators"], ms, end, lambda v: v == 1)
    f["indicator_left_onset_rel_ms_s"] = (ind_on - ms) if ind_on is not None else None
    f["indicator_left_before_ms"] = bool((x["indicators"][(t >= tor) & (t < ms)] == 1).any())
    f["indicator_before_lane_crossing"] = (bool(ind_on < lc) if (ind_on is not None and lc is not None) else None)
    # hazard station: roadAbscissa + Distance_to_Construction on the TOR road
    rid = x["road_id"][i_tor]
    same = (x["road_id"] == rid) & (t >= tor - 4.0) & (t < ms) & ~np.isnan(x["d_construction"])
    h = x["abscissa"][same] + x["d_construction"][same]
    f["hazard_station_sd_m"] = float(np.nanstd(h)) if same.sum() > 5 else None
    h2 = x["abscissa"][same] - x["d_construction"][same]
    f["hazard_station_sd_minus_m"] = float(np.nanstd(h2)) if same.sum() > 5 else None
    ds, dd = np.diff(x["abscissa"][same]), np.diff(x["d_construction"][same])
    ok = np.abs(ds) > 1e-6
    f["d_construction_rate_per_abscissa"] = float(np.median(dd[ok] / ds[ok])) if ok.sum() > 5 else None
    f["d_construction_at_tor_m"] = float(x["d_construction"][i_tor])
    for k in ("d_follow", "d_lead_next", "d_follow_next"):
        v = x[k]
        cls = classify_adjacent_lane_values(v)
        f[f"{k}_zero_fraction"] = float((cls == "zero_semantics_unresolved").mean())
        f[f"{k}_missing_fraction"] = float((cls == "missing").mean())
        nz = v[(v != 0) & ~np.isnan(v)]
        f[f"{k}_min_nonzero"] = float(np.min(np.abs(nz))) if len(nz) else None
        # magnitude just before a value -> zero transition (sentinel vs physical closeness)
        idx = np.where((v[:-1] != 0) & ~np.isnan(v[:-1]) & (v[1:] == 0))[0]
        f[f"{k}_value_before_zero_median"] = float(np.median(np.abs(v[idx]))) if len(idx) else None
        f[f"{k}_n_negative"] = int((v < 0).sum())
    return f


# ---------------------------------------------------------------------------
# aggregate tests
# ---------------------------------------------------------------------------


def cell_stereotypy(df: pd.DataFrame, col: str) -> pd.DataFrame:
    rows = []
    for cell, g in df.groupby("cell"):
        v = g[col].dropna()
        frac = len(v) / len(g)
        iqr = float(v.quantile(0.75) - v.quantile(0.25)) if len(v) >= 4 else None
        rows.append({"event": col, "cell": cell, "n_trials": len(g), "fraction_with_event": round(frac, 3),
                     "median_latency_s": round(float(v.median()), 3) if len(v) else None,
                     "iqr_latency_s": round(iqr, 3) if iqr is not None else None,
                     "stereotyped": bool(frac >= STEREO_FRACTION and iqr is not None and iqr <= STEREO_IQR_S)})
    return pd.DataFrame(rows)


def structure(df: pd.DataFrame, col: str) -> Dict[str, object]:
    v = df[col]
    return {"event": col, "n": int(v.notna().sum()), "median_s": float(v.median()) if v.notna().any() else None,
            "iqr_s": [float(v.quantile(.25)), float(v.quantile(.75))] if v.notna().any() else None,
            "participant_icc1": icc1(v, df.participant_id), "cell_eta2": eta2(v, df.cell)}


def classify_channel(documented: bool, stereo_post: bool, icc: Optional[float], eta: Optional[float],
                     mode_locked: Optional[bool], consistent: Optional[bool]) -> str:
    if not documented:
        return "NOT_IDENTIFIABLE"
    if stereo_post:
        return "MIXED_OR_AMBIGUOUS"
    a3 = icc is not None and eta is not None and icc > 0.1 and eta < 0.5
    if a3 and mode_locked and consistent:
        return "DRIVER_AUTHORSHIP_SUPPORTED"
    return "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED"


def run(archive_path: str = DEFAULT_ARCHIVE, output_dir: str = DEFAULT_OUTPUT) -> Dict[str, object]:
    arc = D003Archive(archive_path)
    feats = [f for f in (trial_features(arc.load(n)) for n in arc.trial_names()) if f is not None]
    arc.close()
    df = pd.DataFrame(feats)
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "trial_features.csv"), index=False)

    events = ["brake_onset_tor_ms_rel_tor_s", "accel_release_rel_tor_s", "brake_onset_after_ms_rel_ms_s",
              "brake_straddle_release_rel_ms_s", "brake_clean_onset_rel_ms_s", "accel_straddle_drop_rel_ms_s",
              "accel_onset_after_ms_rel_ms_s", "steer_onset_after_ms_rel_ms_s", "indicator_left_onset_rel_ms_s"]
    stereo = pd.concat([cell_stereotypy(df, e) for e in events], ignore_index=True)
    stereo.to_csv(os.path.join(output_dir, "cell_stereotypy.csv"), index=False)
    struct = [structure(df, e) for e in events + ["steer_onset_to_lane_crossing_s", "t_button_s", "brake_straddle_release_rel_tor_s"]]
    pd.DataFrame(struct).to_csv(os.path.join(output_dir, "event_structure.csv"), index=False)

    def stereo_any(ev):
        return bool(stereo[(stereo.event == ev)].stereotyped.any())

    S = {s["event"]: s for s in struct}
    q = lambda c: df[c].dropna()
    # mode locking of automation content
    accel_locked = bool((q("accel_mean_pre_tor") > ACCEL_T).mean() > 0.9 and
                        (q("accel_mean_after_handback") > ACCEL_T).mean() > 0.9)
    torque_locked = bool((q("torque_mean_pre_tor").abs() > 0.1).mean() > 0.9 and
                         (q("torque_mean_tor_ms").abs() < 0.1).mean() > 0.9)
    brake_consistent = bool(q("brake_decel_coupling_post_ms").median() > 0.5)
    steer_consistent = bool(q("steer_onset_to_lane_crossing_s").gt(0).mean() > 0.9)
    verdict = {
        "brake": classify_channel(True, stereo_any("brake_onset_after_ms_rel_ms_s"),
                                  S["brake_onset_after_ms_rel_ms_s"]["participant_icc1"],
                                  S["brake_onset_after_ms_rel_ms_s"]["cell_eta2"], None, brake_consistent),
        "accelerator": classify_channel(True, stereo_any("accel_onset_after_ms_rel_ms_s"),
                                        S["accel_onset_after_ms_rel_ms_s"]["participant_icc1"],
                                        S["accel_onset_after_ms_rel_ms_s"]["cell_eta2"], accel_locked, True),
        "steering_wheel_angle": classify_channel(True, stereo_any("steer_onset_after_ms_rel_ms_s"),
                                                 S["steer_onset_after_ms_rel_ms_s"]["participant_icc1"],
                                                 S["steer_onset_after_ms_rel_ms_s"]["cell_eta2"],
                                                 bool((q("steer_std_tor_ms") < 0.01).mean() > 0.9), steer_consistent),
        "steering_torque": classify_channel(False, False, None, None, torque_locked, None),
        "left_indicator": classify_channel(True, stereo_any("indicator_left_onset_rel_ms_s"),
                                           S["indicator_left_onset_rel_ms_s"]["participant_icc1"],
                                           S["indicator_left_onset_rel_ms_s"]["cell_eta2"],
                                           bool(not df.indicator_left_before_ms.any()),
                                           bool(q("indicator_before_lane_crossing").astype(bool).mean() > 0.9)),
        "state_flag": "NOT_IDENTIFIABLE",
    }
    final = dict(verdict)
    for ch, (cls, _) in REVIEW_OVERRIDES.items():
        if ORDER.index(cls) > ORDER.index(verdict[ch]):
            raise ValueError(f"review may only downgrade: {ch} {verdict[ch]} -> {cls}")
        final[ch] = cls
    summary = {
        "n_trials": int(len(df)), "n_participants": int(df.participant_id.nunique()),
        "thresholds": {"brake": BRAKE_T, "steer_rad": STEER_T, "accelerator": ACCEL_T,
                       "stereotypy_fraction": STEREO_FRACTION, "stereotypy_iqr_s": STEREO_IQR_S},
        "criteria": AUTHORSHIP_CRITERIA,
        "state_flag_values": sorted(set(";".join(df.state_values).split(";"))),
        "mode_locking": {"accelerator_automation_content_before_TOR_and_after_handback": accel_locked,
                         "torque_offset_present_pre_TOR_and_absent_TOR_to_MS": torque_locked},
        "event_structure": S,
        "fractions": {
            "brake_active_pre_tor": float(df.brake_active_pre_tor.mean()),
            "brake_onset_in_tor_ms": float(df.brake_onset_tor_ms_rel_tor_s.notna().mean()),
            "brake_active_at_ms": float(df.brake_active_at_ms.mean()),
            "brake_onset_after_ms": float(df.brake_onset_after_ms_rel_ms_s.notna().mean()),
            "brake_saturated_400": float((df.brake_max_value_trial >= 400).mean()),
            "steer_moved_tor_ms": float(df.steer_moved_tor_ms.mean()),
            "indicator_left_before_ms": float(df.indicator_left_before_ms.mean()),
        },
        "straddle": {
            "brake_active_at_ms_fraction": float(df.brake_active_at_ms.mean()),
            "brake_straddle_release_rel_ms": S["brake_straddle_release_rel_ms_s"],
            "brake_straddle_release_sd_rel_ms_vs_rel_tor": [float(q("brake_straddle_release_rel_ms_s").std()),
                                                            float(q("brake_straddle_release_rel_tor_s").std())],
            "brake_max_step_near_ms_median": float(q("brake_max_step_near_ms").median()),
            "accel_active_at_ms_fraction": float(df.accel_active_at_ms.mean()),
            "accel_active_at_ms_by_cell": {c: float(v) for c, v in df.groupby("cell").accel_active_at_ms.mean().items()},
            "interpretation": "brake/accelerator content present at MS continues smoothly across the switch and "
                              "releases later: the channels are not driver-only at MS",
        },
        "geometry": {
            "hazard_station_sd_plus_m_median": float(q("hazard_station_sd_m").median()),
            "hazard_station_sd_minus_m_median": float(q("hazard_station_sd_minus_m").median()),
            "d_construction_rate_per_abscissa_median": float(q("d_construction_rate_per_abscissa").median()),
            "d_construction_at_tor_m_median": float(q("d_construction_at_tor_m").median()),
            "gap_zero_fraction_by_cell": {k: {c: float(v) for c, v in df.groupby("cell")[f"{k}_zero_fraction"].median().items()}
                                          for k in ("d_follow", "d_lead_next", "d_follow_next")},
            "gap_value_before_zero_median_m": {k: float(q(f"{k}_value_before_zero_median").median())
                                               for k in ("d_follow", "d_lead_next", "d_follow_next")},
            "gap_min_nonzero_m": {k: float(q(f"{k}_min_nonzero").min()) for k in ("d_follow", "d_lead_next", "d_follow_next")},
        },
        "steering_mode_content": {
            "pre_tor_mean_angle_cell_eta2": eta2(df.steer_mean_pre_tor, df.cell),
            "pre_tor_mean_angle_by_cell": {c: [float(v.median()), float(v.quantile(.75) - v.quantile(.25))]
                                           for c, v in df.groupby("cell").steer_mean_pre_tor},
            "step_at_tor_gt_0p03_rad_by_cell": {c: float(v) for c, v in
                                                df.assign(_s=(df.steer_mean_tor_ms - df.steer_mean_pre_tor).abs() > 0.03)
                                                .groupby("cell")._s.mean().items()},
            "steer_std_tor_ms_median": float(q("steer_std_tor_ms").median()),
        },
        "handback_window": {
            "accel_gt_threshold_after_handback_fraction": float((q("accel_mean_after_handback") > ACCEL_T).mean()),
            "accel_gt_threshold_pre_tor_fraction": float((q("accel_mean_pre_tor") > ACCEL_T).mean()),
        },
        "coupling_median": {"brake_decel_tor_ms": float(q("brake_decel_coupling_tor_ms").median()),
                            "brake_decel_post_ms": float(q("brake_decel_coupling_post_ms").median())},
        "authorship_classification_rule": verdict,
        "review_overrides": {k: {"class": c, "reason": r} for k, (c, r) in REVIEW_OVERRIDES.items()},
        "authorship_classification": final,
        "brake_magnitude": {"class": "NOT_IDENTIFIABLE",
                            "reason": "unit conflict (dictionary: force N; owners' paper: pedal position), automation "
                                      "brake content straddles MS, max value 400 reached in "
                                      f"{float((df.brake_max_value_trial >= 400).mean()):.1%} of trials (possible cap)"},
        "not_authorship_evidence": "correlations and vehicle-response coupling are consistency checks only",
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
        fh.write("\n")
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump({"archive_sha256": archive_sha256(archive_path), **git_state(),
                   "code": "src/experiments/r4v_channel_authorship.py"}, fh, indent=2)
        fh.write("\n")
    return {"features": df, "stereotypy": stereo, "structure": S, "summary": summary}


if __name__ == "__main__":
    run(*sys.argv[1:3])
