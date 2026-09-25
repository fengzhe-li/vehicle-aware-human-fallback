"""Phase 2B-1: Empirical Human Takeover Recovery Characterisation.

PRE-AUDIT CODE (Phase R1 notice, 2026-09-22): uses the legacy loader, silently
takes the first TOR value (26 trials have several), searches windows past
Time_Manual_Stop, and does not validate lane-change timing. Its outputs are
retained as pre-audit artifacts (see docs/RESEARCH_STATUS_BASELINE_2026-09-22.md).
Do not rerun it for new results; new work must use src/data/d003_ingest.py.

Extracts empirical human fallback metrics from the 513 trials of the TU Delft
conditionally automated driving takeover dataset (D003).

Produces:
- research/data_matrix/d003_trial_qa.csv
- results/H1/event_times.csv
- results/H1/action_sequence.csv
- results/H1/initial_control_metrics.csv
- results/H1/correction_metrics.csv
- results/H1/stabilization_candidates.csv
- results/H1/participant_summary.csv
- results/H1/scenario_summary.csv
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import warnings

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from src.data.d003_loader import D003Dataset, TrialMeta


def compute_trial_qa(
    df: pd.DataFrame, meta: TrialMeta
) -> Dict[str, Any]:
    """Audit single-trial data quality and integrity."""
    t0 = df["time"].iloc[0]
    t_rel = df["time"].values - t0
    dts = np.diff(t_rel)

    is_mono = bool(np.all(dts > 0))
    has_dup = bool(np.any(dts == 0))
    dt_mean = float(np.mean(dts)) if len(dts) > 0 else np.nan
    dt_std = float(np.std(dts)) if len(dts) > 0 else np.nan

    tor_vals = df["TOR_request"].dropna().unique()
    man_start_vals = df["manual_start"].dropna().unique()
    man_stop_vals = df["manual_stop"].dropna().unique()
    lc_vals = df["lane_change_time"].dropna().unique()

    has_tor = len(tor_vals) > 0 and not np.isnan(tor_vals[0])
    has_man_start = len(man_start_vals) > 0 and not np.isnan(man_start_vals[0])
    has_man_stop = len(man_stop_vals) > 0 and not np.isnan(man_stop_vals[0])
    has_lc = len(lc_vals) > 0 and not np.isnan(lc_vals[0])

    tor_time = float(tor_vals[0]) if has_tor else np.nan
    man_start_time = float(man_start_vals[0]) if has_man_start else np.nan
    man_stop_time = float(man_stop_vals[0]) if has_man_stop else np.nan
    lc_time = float(lc_vals[0]) if has_lc else np.nan

    delta_t_man_start = man_start_time - tor_time if (has_tor and has_man_start) else np.nan

    bf_min = float(df["brake_force"].min())
    bf_max = float(df["brake_force"].max())
    acc_min = float(df["accelerator"].min())
    acc_max = float(df["accelerator"].max())
    st_min = float(df["steering_angle"].min())
    st_max = float(df["steering_angle"].max())

    dist_obs = df["distance_to_obstacle"].dropna()
    min_dist = float(dist_obs.min()) if len(dist_obs) > 0 else np.nan

    # Collision audit
    # In D003, obstacle is stationary at construction zone.
    # Collision occurs if distance <= 0 at speed > 3 m/s before/without lane change.
    t_ref = tor_time if has_tor else man_start_time
    post = df[t_rel >= t_ref]
    min_speed_post = float(post["longitudinal_speed"].min()) if len(post) > 0 else np.nan

    dist_at_lc = np.nan
    if has_lc:
        lc_rows = post[t_rel[t_rel >= t_ref] >= lc_time]
        if len(lc_rows) > 0:
            dist_at_lc = float(lc_rows["distance_to_obstacle"].iloc[0])

    collision = False
    if not has_lc and min_dist <= 0.0 and min_speed_post > 3.0:
        collision = True
    elif has_lc and dist_at_lc <= 0.0 and min_speed_post > 3.0:
        collision = True

    # Classification & reason code
    if not has_tor and has_man_start:
        usable_status = "USABLE_PREEMPTIVE"
        reason_code = "PREEMPTIVE_TAKEOVER_NO_TOR_ISSUED"
    elif collision:
        usable_status = "COLLISION_FAILURE"
        reason_code = "COLLISION_WITH_HAZARD"
    elif not is_mono:
        usable_status = "FLAGGED_TIMESTAMPS"
        reason_code = "NON_MONOTONIC_TIMESTAMPS"
    else:
        usable_status = "USABLE_FULL"
        reason_code = "NONE"

    return {
        "trial_id": meta.trial_id,
        "participant_id": meta.participant_id,
        "scenario_id": meta.scenario_id,
        "density": meta.density,
        "nback": meta.nback,
        "total_samples": len(df),
        "duration_s": float(t_rel[-1] - t_rel[0]),
        "dt_mean": dt_mean,
        "dt_std": dt_std,
        "is_strictly_monotonic": is_mono,
        "has_duplicate_timestamps": has_dup,
        "has_tor_request": has_tor,
        "tor_request_time": tor_time,
        "has_manual_start": has_man_start,
        "manual_start_time": man_start_time,
        "has_manual_stop": has_man_stop,
        "manual_stop_time": man_stop_time,
        "delta_t_manual_start": delta_t_man_start,
        "bf_min": bf_min,
        "bf_max": bf_max,
        "acc_min": acc_min,
        "acc_max": acc_max,
        "st_min_rad": st_min,
        "st_max_rad": st_max,
        "min_obstacle_distance": min_dist,
        "has_lane_change": has_lc,
        "lane_change_time": lc_time,
        "collision_outcome": collision,
        "usable_status": usable_status,
        "reason_code": reason_code,
    }


def extract_trial_metrics(
    df: pd.DataFrame, meta: TrialMeta
) -> Dict[str, Any]:
    """Compute empirical timeline, action ordering, and control metrics."""
    t0 = df["time"].iloc[0]
    t_rel = df["time"].values - t0
    df = df.copy()
    df["t_rel"] = t_rel

    tor_vals = df["TOR_request"].dropna().unique()
    man_start_vals = df["manual_start"].dropna().unique()
    has_tor = len(tor_vals) > 0 and not np.isnan(tor_vals[0])
    has_man = len(man_start_vals) > 0 and not np.isnan(man_start_vals[0])

    t_req = float(tor_vals[0]) if has_tor else np.nan
    t_man_start = float(man_start_vals[0]) if has_man else np.nan
    t_ref = t_req if has_tor else t_man_start

    # Baseline window immediately preceding reference event: [t_ref - 4.0, t_ref - 0.2]
    pre = df[(t_rel >= t_ref - 4.0) & (t_rel <= t_ref - 0.2)]
    if len(pre) < 10:
        pre = df[t_rel <= t_ref]

    st_base = float(pre["steering_angle"].mean())
    st_std = float(pre["steering_angle"].std())
    ax_base = float(pre["longitudinal_acceleration"].mean())
    ay_base = float(pre["lateral_acceleration"].mean())
    acc_base = float(pre["accelerator"].mean())

    # Post-reference window
    post = df[t_rel >= t_ref].copy()

    # 1. T_first detection
    # Brake onset: threshold 15 N
    bf_hits = post[post["brake_force"] > 15.0]
    t_first_brake = float(bf_hits["t_rel"].iloc[0]) if len(bf_hits) > 0 else np.nan

    # Steer onset: threshold deviation > 0.05 rad (~2.86 deg)
    st_hits = post[(post["steering_angle"] - st_base).abs() > 0.05]
    t_first_steer = float(st_hits["t_rel"].iloc[0]) if len(st_hits) > 0 else np.nan

    # Accel release: only valid if accelerator was actually pressed (> 0.05) pre-event
    t_first_accel = np.nan
    if acc_base > 0.05:
        acc_hits = post[post["accelerator"] <= 0.02]
        if len(acc_hits) > 0:
            t_first_accel = float(acc_hits["t_rel"].iloc[0])

    # T_first_ctrl: earliest active human control input (brake or steer)
    cands_ctrl = [t for t in [t_first_brake, t_first_steer] if not np.isnan(t)]
    t_first_ctrl = min(cands_ctrl) if cands_ctrl else np.nan

    # T_first_any: earliest detectable action (including confirmed throttle release)
    candidates_first = [t for t in [t_first_brake, t_first_steer, t_first_accel] if not np.isnan(t)]
    t_first_any = min(candidates_first) if candidates_first else np.nan

    # Action Sequence Categorisation (following Prompt Section 1):
    # - Steer first: steer precedes brake by > 100 ms
    # - Brake first: brake precedes steer by > 100 ms
    # - Simultaneous: abs(steer - brake) <= 100 ms
    # - Throttle release only: throttle release without steer or brake
    dt_steer_brake = t_first_steer - t_first_brake if (not np.isnan(t_first_steer) and not np.isnan(t_first_brake)) else np.nan
    dt_brake_accel = t_first_brake - t_first_accel if (not np.isnan(t_first_brake) and not np.isnan(t_first_accel)) else np.nan

    is_simul_bs = abs(dt_steer_brake) <= 0.10 if not np.isnan(dt_steer_brake) else False

    if not np.isnan(t_first_steer) and not np.isnan(t_first_brake):
        if is_simul_bs:
            first_action_type = "SIMULTANEOUS_BRAKE_STEER"
        elif dt_steer_brake < -0.10:
            first_action_type = "STEER_FIRST"
        else:
            first_action_type = "BRAKE_FIRST"
    elif not np.isnan(t_first_steer):
        first_action_type = "STEER_FIRST"
    elif not np.isnan(t_first_brake):
        first_action_type = "BRAKE_FIRST"
    elif not np.isnan(t_first_accel):
        first_action_type = "THROTTLE_RELEASE_ONLY"
    else:
        first_action_type = "NO_ACTION"

    # Action chronological order
    actions = []
    if not np.isnan(t_first_accel): actions.append((t_first_accel, "accel_release"))
    if not np.isnan(t_first_steer): actions.append((t_first_steer, "steer"))
    if not np.isnan(t_first_brake): actions.append((t_first_brake, "brake"))
    actions.sort(key=lambda x: x[0])
    action_order_str = " -> ".join([a[1] for a in actions]) if actions else "none"

    # 2. T_effective detection
    # Deceleration onset: ax <= ax_base - 0.5 m/s2
    ax_hits = post[post["longitudinal_acceleration"] <= ax_base - 0.5]
    t_eff_dec = float(ax_hits["t_rel"].iloc[0]) if len(ax_hits) > 0 else np.nan

    # Lateral response onset: abs(ay - ay_base) >= 0.4 m/s2
    ay_hits = post[(post["lateral_acceleration"] - ay_base).abs() >= 0.4]
    t_eff_lat = float(ay_hits["t_rel"].iloc[0]) if len(ay_hits) > 0 else np.nan

    cand_eff = [t for t in [t_eff_dec, t_eff_lat] if not np.isnan(t)]
    t_eff_any = min(cand_eff) if cand_eff else np.nan

    # 3. Initial Control Metrics
    # Initial brake peak within 2.0s of brake onset
    init_peak_bf = np.nan
    bf_rise_rate = np.nan
    time_to_peak_bf = np.nan
    if not np.isnan(t_first_brake):
        window_bf = post[(post["t_rel"] >= t_first_brake) & (post["t_rel"] <= t_first_brake + 2.0)]
        if len(window_bf) > 0:
            init_peak_bf = float(window_bf["brake_force"].max())
            idx_peak = window_bf["brake_force"].idxmax()
            t_peak_bf = float(df.loc[idx_peak, "t_rel"])
            time_to_peak_bf = t_peak_bf - t_first_brake
            if time_to_peak_bf > 0:
                bf_rise_rate = (init_peak_bf - 15.0) / time_to_peak_bf

    # Initial steer peak within 2.0s of steer onset
    init_peak_st = np.nan
    init_peak_st_deg = np.nan
    init_st_rate = np.nan
    if not np.isnan(t_first_steer):
        window_st = post[(post["t_rel"] >= t_first_steer) & (post["t_rel"] <= t_first_steer + 2.0)]
        if len(window_st) > 0:
            init_peak_st = float((window_st["steering_angle"] - st_base).abs().max())
            init_peak_st_deg = float(np.degrees(init_peak_st))
            init_st_rate = float(window_st["steering_speed"].abs().max())

    # Simultaneous brake + steer flag within 0.5s of first action
    simul_bs_05 = False
    if not np.isnan(t_first_brake) and not np.isnan(t_first_steer):
        simul_bs_05 = abs(t_first_brake - t_first_steer) <= 0.50

    # Speeds
    speed_at_first = float(post.loc[post["t_rel"] >= t_first_any, "longitudinal_speed"].iloc[0]) if not np.isnan(t_first_any) and len(post.loc[post["t_rel"] >= t_first_any]) > 0 else np.nan
    speed_at_eff = float(post.loc[post["t_rel"] >= t_eff_any, "longitudinal_speed"].iloc[0]) if not np.isnan(t_eff_any) and len(post.loc[post["t_rel"] >= t_eff_any]) > 0 else np.nan
    min_speed_post = float(post["longitudinal_speed"].min()) if len(post) > 0 else np.nan
    speed_drop = (speed_at_first - min_speed_post) if (not np.isnan(speed_at_first) and not np.isnan(min_speed_post)) else np.nan

    # 4. Closed-Loop Correction Metrics
    # Brake extrema & reapplications during manual phase
    bf_series = post["brake_force"].values
    t_post = post["t_rel"].values
    dt = 0.05

    peaks, _ = find_peaks(bf_series, prominence=15.0, distance=10)
    brake_extrema_count = int(len(peaks))

    # Reapplications: count valleys dropping below 20N then rising above 30N
    valleys, _ = find_peaks(-bf_series, prominence=10.0, distance=10)
    reapp_count = 0
    for v_idx in valleys:
        if bf_series[v_idx] < 20.0:
            # Check if force rises above 30N afterwards
            if np.any(bf_series[v_idx:] > 30.0):
                reapp_count += 1
    brake_reapp_count = reapp_count

    # Brake derivative sign changes
    bf_diff = np.diff(bf_series) / dt
    bf_active_mask = bf_series[:-1] > 10.0
    sign_changes_bf = 0
    if np.sum(bf_active_mask) > 2:
        bf_diff_active = bf_diff[bf_active_mask]
        sign_changes_bf = int(np.sum((bf_diff_active[:-1] * bf_diff_active[1:] < 0) & (np.abs(np.diff(bf_diff_active)) > 5.0)))

    # Steering reversals
    st_series = post["steering_angle"].values - st_base
    st_speed = post["steering_speed"].values
    st_reversals = 0
    # Zero-crossings of steering speed with excursion >= 0.05 rad
    zc_indices = np.where((st_speed[:-1] * st_speed[1:]) < 0)[0]
    for zc in zc_indices:
        if abs(st_series[zc]) >= 0.05:
            st_reversals += 1

    st_rate_sign_changes = int(len(zc_indices))

    # 5. Trajectory Stabilization Candidates (T_stable)
    t_start_stab = t_eff_any if not np.isnan(t_eff_any) else (t_man_start if not np.isnan(t_man_start) else t_req)

    # Candidate A: Control-Input Settling
    # |st_speed| <= 0.05 rad/s and |d_bf| <= 20 N/s for 1.5s (30 consecutive samples)
    candA_time = np.nan
    candA_settled = False
    window_samples_A = 30  # 1.5s at 20Hz
    idx_start_A = np.where(t_post >= t_start_stab)[0]
    if len(idx_start_A) > window_samples_A:
        i0 = idx_start_A[0]
        st_spd_sub = np.abs(st_speed[i0:])
        bf_diff_sub = np.abs(np.diff(bf_series[i0:], prepend=bf_series[i0])) / dt
        cond_A = (st_spd_sub <= 0.05) & (bf_diff_sub <= 20.0)
        # Find first run of 30 True
        for k in range(len(cond_A) - window_samples_A):
            if np.all(cond_A[k : k + window_samples_A]):
                candA_time = float(t_post[i0 + k])
                candA_settled = True
                break

    # Candidate B: Vehicle-State Settling
    # |ax_diff| <= 0.5 m/s3 and |ay| <= 0.3 m/s2 for 1.5s
    candB_time = np.nan
    candB_settled = False
    if len(idx_start_A) > window_samples_A:
        i0 = idx_start_A[0]
        ax_sub = post["longitudinal_acceleration"].values[i0:]
        ay_sub = np.abs(post["lateral_acceleration"].values[i0:] - ay_base)
        ax_diff_sub = np.abs(np.diff(ax_sub, prepend=ax_sub[0])) / dt
        cond_B = (ax_diff_sub <= 0.5) & (ay_sub <= 0.3)
        for k in range(len(cond_B) - window_samples_A):
            if np.all(cond_B[k : k + window_samples_A]):
                candB_time = float(t_post[i0 + k])
                candB_settled = True
                break

    # Candidate C: Lane-Change / Heading Settling
    # Vehicle in new lane (lane_id == 3) and yaw rate settles (|st_speed| <= 0.04) for 2.0s
    candC_time = np.nan
    candC_settled = False
    window_samples_C = 40  # 2.0s at 20Hz
    lane_ids = post["lane_id"].values
    if len(idx_start_A) > window_samples_C:
        i0 = idx_start_A[0]
        lane_sub = lane_ids[i0:]
        st_spd_sub = np.abs(st_speed[i0:])
        cond_C = (lane_sub == 3.0) & (st_spd_sub <= 0.04)
        for k in range(len(cond_C) - window_samples_C):
            if np.all(cond_C[k : k + window_samples_C]):
                candC_time = float(t_post[i0 + k])
                candC_settled = True
                break

    # Candidate D: Obstacle Longitudinal Station Passage (T_pass)
    # distance_to_obstacle <= 0 (reaches obstacle longitudinal station)
    candD_time = np.nan
    candD_settled = False
    dist_sub = post["distance_to_obstacle"].values
    pass_idx = np.where((t_post >= t_start_stab) & (dist_sub <= 0.0))[0]
    if len(pass_idx) > 0:
        candD_time = float(t_post[pass_idx[0]])
        candD_settled = True

    return {
        # Identifiers
        "trial_id": meta.trial_id,
        "participant_id": meta.participant_id,
        "scenario_id": meta.scenario_id,
        "density": meta.density,
        "nback": meta.nback,
        # Event timestamps
        "T_request": t_req,
        "T_manual_start": t_man_start,
        "delta_T_manual_start": t_man_start - t_req if (not np.isnan(t_man_start) and not np.isnan(t_req)) else np.nan,
        "T_first_brake": t_first_brake,
        "T_first_steer": t_first_steer,
        "T_first_accel": t_first_accel,
        "T_first_ctrl": t_first_ctrl,
        "T_first_any": t_first_any,
        "T_effective_dec": t_eff_dec,
        "T_effective_lat": t_eff_lat,
        "T_effective_any": t_eff_any,
        "T_stable_candA": candA_time,
        "T_stable_candB": candB_time,
        "T_stable_candC": candC_time,
        "T_stable_candD": candD_time,
        "candA_settled": candA_settled,
        "candB_settled": candB_settled,
        "candC_settled": candC_settled,
        "candD_settled": candD_settled,
        # Latency intervals
        "dt_req_to_manual_start": t_man_start - t_req if (not np.isnan(t_man_start) and not np.isnan(t_req)) else np.nan,
        "dt_req_to_first": t_first_ctrl - t_req if (not np.isnan(t_first_ctrl) and not np.isnan(t_req)) else np.nan,
        "dt_req_to_first_any": t_first_any - t_req if (not np.isnan(t_first_any) and not np.isnan(t_req)) else np.nan,
        "dt_manual_start_to_first": t_first_ctrl - t_man_start if (not np.isnan(t_first_ctrl) and not np.isnan(t_man_start)) else np.nan,
        "dt_first_to_eff": t_eff_any - t_first_ctrl if (not np.isnan(t_eff_any) and not np.isnan(t_first_ctrl)) else np.nan,
        "dt_eff_to_stable_candA": candA_time - t_eff_any if (candA_settled and not np.isnan(t_eff_any)) else np.nan,
        "dt_eff_to_stable_candB": candB_time - t_eff_any if (candB_settled and not np.isnan(t_eff_any)) else np.nan,
        "dt_req_to_stable_candA": candA_time - t_req if (candA_settled and not np.isnan(t_req)) else np.nan,
        "dt_req_to_stable_candB": candB_time - t_req if (candB_settled and not np.isnan(t_req)) else np.nan,
        # Action sequence
        "first_action_type": first_action_type,
        "action_order_string": action_order_str,
        "dt_steer_minus_brake": dt_steer_brake,
        "dt_brake_minus_accel": dt_brake_accel,
        "is_simultaneous_brake_steer": is_simul_bs,
        "is_simultaneous_accel_steer": False,
        # Initial control metrics
        "initial_peak_brake_force_N": init_peak_bf,
        "brake_rise_rate_N_per_s": bf_rise_rate,
        "time_to_peak_brake_s": time_to_peak_bf,
        "initial_peak_steering_rad": init_peak_st,
        "initial_peak_steering_deg": init_peak_st_deg,
        "initial_steering_rate_rad_per_s": init_st_rate,
        "simultaneous_brake_and_steer_flag": simul_bs_05,
        "speed_at_T_first_m_per_s": speed_at_first,
        "speed_at_T_effective_m_per_s": speed_at_eff,
        "min_speed_post_tor_m_per_s": min_speed_post,
        "speed_drop_m_per_s": speed_drop,
        # Closed-loop corrections
        "brake_extrema_count": brake_extrema_count,
        "brake_reapplication_count": brake_reapp_count,
        "brake_derivative_sign_changes": sign_changes_bf,
        "steering_reversals_count": st_reversals,
        "steering_rate_sign_changes": st_rate_sign_changes,
    }


def run_full_h1_analysis(
    archive_path: str = "data/external/d003/tu_delft_takeover.zip",
    results_dir: str = "results/H1",
    qa_path: str = "research/data_matrix/d003_trial_qa.csv",
) -> Dict[str, pd.DataFrame]:
    """Execute full Phase 2B-1 analysis across all 513 trials and save deliverables."""
    warnings.warn(
        "run_full_h1_analysis is HISTORICAL ONLY: it reproduces pre-audit outputs whose human-response, "
        "T_stable, correction-count and collision claims are withdrawn (see "
        "results/HISTORICAL_OUTPUTS_MANIFEST.md). It is not an active scientific path.",
        DeprecationWarning,
        stacklevel=2,
    )
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(os.path.dirname(qa_path), exist_ok=True)

    ds = D003Dataset(archive_path)
    trials = ds.list_trials()
    print(f"Running Phase 2B-1 empirical characterization on {len(trials)} trials...")

    qa_list = []
    metrics_list = []

    for i, t in enumerate(trials):
        df, meta = ds.load_trial(t)
        qa = compute_trial_qa(df, meta)
        qa_list.append(qa)
        m = extract_trial_metrics(df, meta)
        metrics_list.append(m)

    df_qa = pd.DataFrame(qa_list)
    df_all_metrics = pd.DataFrame(metrics_list)

    # Save QA report
    df_qa.to_csv(qa_path, index=False)
    print(f"Saved: {qa_path} ({len(df_qa)} rows)")

    # 1. results/H1/event_times.csv
    event_cols = [
        "trial_id", "participant_id", "scenario_id", "density", "nback",
        "T_request", "T_manual_start", "delta_T_manual_start",
        "T_first_brake", "T_first_steer", "T_first_accel", "T_first_ctrl", "T_first_any",
        "T_effective_dec", "T_effective_lat", "T_effective_any",
        "T_stable_candA", "T_stable_candB", "T_stable_candC", "T_stable_candD",
        "dt_req_to_manual_start", "dt_req_to_first", "dt_req_to_first_any", "dt_manual_start_to_first", "dt_first_to_eff",
        "dt_eff_to_stable_candA", "dt_eff_to_stable_candB",
        "dt_req_to_stable_candA", "dt_req_to_stable_candB",
    ]
    df_events = df_all_metrics[event_cols].copy()
    events_path = os.path.join(results_dir, "event_times.csv")
    df_events.to_csv(events_path, index=False)
    print(f"Saved: {events_path}")

    # 2. results/H1/action_sequence.csv
    action_cols = [
        "trial_id", "participant_id", "scenario_id", "density", "nback",
        "first_action_type", "action_order_string",
        "dt_steer_minus_brake", "dt_brake_minus_accel",
        "is_simultaneous_brake_steer", "is_simultaneous_accel_steer",
    ]
    df_action = df_all_metrics[action_cols].copy()
    action_path = os.path.join(results_dir, "action_sequence.csv")
    df_action.to_csv(action_path, index=False)
    print(f"Saved: {action_path}")

    # 3. results/H1/initial_control_metrics.csv
    init_cols = [
        "trial_id", "participant_id", "scenario_id", "density", "nback",
        "initial_peak_brake_force_N", "brake_rise_rate_N_per_s", "time_to_peak_brake_s",
        "initial_peak_steering_rad", "initial_peak_steering_deg", "initial_steering_rate_rad_per_s",
        "simultaneous_brake_and_steer_flag",
        "speed_at_T_first_m_per_s", "speed_at_T_effective_m_per_s",
        "min_speed_post_tor_m_per_s", "speed_drop_m_per_s",
    ]
    df_init = df_all_metrics[init_cols].copy()
    init_path = os.path.join(results_dir, "initial_control_metrics.csv")
    df_init.to_csv(init_path, index=False)
    print(f"Saved: {init_path}")

    # 4. results/H1/correction_metrics.csv
    corr_cols = [
        "trial_id", "participant_id", "scenario_id", "density", "nback",
        "brake_extrema_count", "brake_reapplication_count", "brake_derivative_sign_changes",
        "steering_reversals_count", "steering_rate_sign_changes",
    ]
    df_corr = df_all_metrics[corr_cols].copy()
    corr_path = os.path.join(results_dir, "correction_metrics.csv")
    df_corr.to_csv(corr_path, index=False)
    print(f"Saved: {corr_path}")

    # 5. results/H1/stabilization_candidates.csv
    stab_cols = [
        "trial_id", "participant_id", "scenario_id", "density", "nback",
        "T_stable_candA", "candA_settled",
        "T_stable_candB", "candB_settled",
        "T_stable_candC", "candC_settled",
        "T_stable_candD", "candD_settled",
    ]
    df_stab = df_all_metrics[stab_cols].copy()
    df_stab["candB_minus_candA"] = df_stab["T_stable_candB"] - df_stab["T_stable_candA"]
    df_stab["candD_minus_candA"] = df_stab["T_stable_candD"] - df_stab["T_stable_candA"]
    stab_path = os.path.join(results_dir, "stabilization_candidates.csv")
    df_stab.to_csv(stab_path, index=False)
    print(f"Saved: {stab_path}")

    # 6. results/H1/participant_summary.csv
    # Repeated-measures aggregation per participant (57 participants)
    p_records = []
    for pid, grp in df_all_metrics.groupby("participant_id"):
        # Most frequent first action
        mode_action = grp["first_action_type"].mode().iloc[0] if len(grp) > 0 else "UNKNOWN"
        p_records.append({
            "participant_id": pid,
            "n_trials": len(grp),
            "delta_t_man_start_median": grp["delta_T_manual_start"].median(),
            "delta_t_man_start_iqr": grp["delta_T_manual_start"].quantile(0.75) - grp["delta_T_manual_start"].quantile(0.25),
            "dt_req_to_first_median": grp["dt_req_to_first"].median(),
            "dt_req_to_first_iqr": grp["dt_req_to_first"].quantile(0.75) - grp["dt_req_to_first"].quantile(0.25),
            "dt_first_to_eff_median": grp["dt_first_to_eff"].median(),
            "dt_first_to_eff_iqr": grp["dt_first_to_eff"].quantile(0.75) - grp["dt_first_to_eff"].quantile(0.25),
            "dt_eff_to_stableA_median": grp["dt_eff_to_stable_candA"].median(),
            "init_peak_bf_median": grp["initial_peak_brake_force_N"].median(),
            "init_peak_st_deg_median": grp["initial_peak_steering_deg"].median(),
            "st_reversals_median": grp["steering_reversals_count"].median(),
            "brake_reapp_median": grp["brake_reapplication_count"].median(),
            "modal_first_action": mode_action,
        })
    df_part = pd.DataFrame(p_records)
    part_path = os.path.join(results_dir, "participant_summary.csv")
    df_part.to_csv(part_path, index=False)
    print(f"Saved: {part_path} ({len(df_part)} participants)")

    # 7. results/H1/scenario_summary.csv
    # Aggregation per scenario (9 scenarios)
    s_records = []
    for sc, grp in df_all_metrics.groupby("scenario_id"):
        density = grp["density"].iloc[0]
        nback = grp["nback"].iloc[0]
        s_records.append({
            "scenario_id": sc,
            "density": density,
            "nback": nback,
            "n_trials": len(grp),
            "delta_t_man_start_median": grp["delta_T_manual_start"].median(),
            "delta_t_man_start_mean": grp["delta_T_manual_start"].mean(),
            "delta_t_man_start_sd": grp["delta_T_manual_start"].std(),
            "dt_req_to_first_median": grp["dt_req_to_first"].median(),
            "dt_first_to_eff_median": grp["dt_first_to_eff"].median(),
            "dt_eff_to_stableA_median": grp["dt_eff_to_stable_candA"].median(),
            "init_peak_bf_mean": grp["initial_peak_brake_force_N"].mean(),
            "init_peak_st_deg_mean": grp["initial_peak_steering_deg"].mean(),
            "st_reversals_mean": grp["steering_reversals_count"].mean(),
            "pct_brake_first": float(np.mean(grp["first_action_type"] == "BRAKE_FIRST") * 100),
            "pct_steer_first": float(np.mean(grp["first_action_type"] == "STEER_FIRST") * 100),
            "pct_simultaneous": float(np.mean(grp["first_action_type"] == "SIMULTANEOUS_BRAKE_STEER") * 100),
            "pct_throttle_only": float(np.mean(grp["first_action_type"] == "THROTTLE_RELEASE_ONLY") * 100),
        })
    df_scen = pd.DataFrame(s_records)
    scen_path = os.path.join(results_dir, "scenario_summary.csv")
    df_scen.to_csv(scen_path, index=False)
    print(f"Saved: {scen_path} ({len(df_scen)} scenarios)")

    return {
        "qa": df_qa,
        "events": df_events,
        "actions": df_action,
        "initial": df_init,
        "corrections": df_corr,
        "stabilization": df_stab,
        "participants": df_part,
        "scenarios": df_scen,
    }


if __name__ == "__main__":
    run_full_h1_analysis()
