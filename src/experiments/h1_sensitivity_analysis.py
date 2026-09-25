"""Phase 2B-1.1: Empirical Recovery Methodology and Sensitivity Audit.

PRE-AUDIT CODE (Phase R1 notice, 2026-09-22): uses the legacy loader, silently
takes the first TOR value (26 trials have several), searches windows past
Time_Manual_Stop, and does not validate lane-change timing. Its outputs are
retained as pre-audit artifacts (see docs/RESEARCH_STATUS_BASELINE_2026-09-22.md).
Do not rerun it for new results; new work must use src/data/d003_ingest.py.

Generates:
- results/H1_sensitivity/tfirst_threshold_sensitivity.csv
- results/H1_sensitivity/teffective_definition_sensitivity.csv
- results/H1_sensitivity/tstable_definition_sensitivity.csv
- results/H1_sensitivity/correction_metric_sensitivity.csv
- results/H1_sensitivity/scenario_repeated_measures.csv
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import butter, filtfilt, find_peaks

from src.data.d003_loader import D003Dataset


def count_steering_reversals(angle_rad: np.ndarray, gap_rad: float) -> int:
    """Count steering reversals using project operational amplitude-hysteresis detector (precedent: McLean & Hoffmann 1975)."""
    if len(angle_rad) < 2:
        return 0
    reversals = 0
    state = 0  # 0: uncommitted, 1: looking for peak, -1: looking for valley
    extreme_val = angle_rad[0]

    for val in angle_rad[1:]:
        if state == 0:
            if val - extreme_val >= gap_rad:
                state = 1
                extreme_val = val
            elif extreme_val - val >= gap_rad:
                state = -1
                extreme_val = val
        elif state == 1:
            if val > extreme_val:
                extreme_val = val
            elif extreme_val - val >= gap_rad:
                reversals += 1
                state = -1
                extreme_val = val
        elif state == -1:
            if val < extreme_val:
                extreme_val = val
            elif val - extreme_val >= gap_rad:
                reversals += 1
                state = 1
                extreme_val = val
    return reversals


def compute_stabilization_search_start(
    anchor: str,
    t_first_brake: float,
    t_first_steer: float,
    t_pass: float = np.nan,
    t_lc: float = np.nan,
    *,
    t_clear: Optional[float] = None,
) -> float:
    """Compute stabilization search start time according to operational event semantics.

    T_first_ctrl is strictly defined as min(T_first_brake, T_first_steer) when both exist,
    or the single observed channel if only one is available. Never uses synthetic fallbacks.

    Parameters
    ----------
    anchor : str
        Search anchor definition ("T_first + 1.0 s", "T_first + 2.0 s",
        "T_first + 3.0 s", "T_pass", "Time_Lane_Change").
    t_first_brake : float
        Nominal brake onset timestamp (or np.nan if unobserved).
    t_first_steer : float
        Nominal steer onset timestamp (or np.nan if unobserved).
    t_pass : float
        Obstacle longitudinal station passage timestamp (or np.nan if unobserved).
    t_lc : float
        Lane change transition timestamp (or np.nan if unobserved).
    t_clear : Optional[float], keyword-only
        Legacy alias for t_pass.

    Returns
    -------
    float
        Search start timestamp in absolute time, or np.nan if required anchor event is unobserved.
    """
    if t_clear is not None and np.isnan(t_pass):
        t_pass = t_clear

    cands = [x for x in [t_first_brake, t_first_steer] if not np.isnan(x)]
    t_first_ctrl = min(cands) if cands else np.nan

    if anchor == "T_first + 1.0 s":
        return t_first_ctrl + 1.0 if not np.isnan(t_first_ctrl) else np.nan
    elif anchor == "T_first + 2.0 s":
        return t_first_ctrl + 2.0 if not np.isnan(t_first_ctrl) else np.nan
    elif anchor == "T_first + 3.0 s":
        return t_first_ctrl + 3.0 if not np.isnan(t_first_ctrl) else np.nan
    elif anchor in ("T_pass", "T_clear"):
        return t_pass if not np.isnan(t_pass) else np.nan
    elif anchor == "Time_Lane_Change":
        return t_lc if not np.isnan(t_lc) else np.nan
    else:
        return t_first_ctrl + 2.0 if not np.isnan(t_first_ctrl) else np.nan


def run_sensitivity_audit(
    archive_path: str = "data/external/d003/tu_delft_takeover.zip",
    output_dir: str = "results/H1_sensitivity",
) -> Dict[str, pd.DataFrame]:
    """Execute all sensitivity analyses and save audit tables."""
    warnings.warn(
        "run_sensitivity_audit is HISTORICAL ONLY: it reproduces pre-audit outputs whose human-response, "
        "T_stable, correction-count and collision claims are withdrawn (see "
        "results/HISTORICAL_OUTPUTS_MANIFEST.md). It is not an active scientific path.",
        DeprecationWarning,
        stacklevel=2,
    )
    os.makedirs(output_dir, exist_ok=True)
    ds = D003Dataset(archive_path)
    trials = ds.list_trials()
    print(f"Loaded dataset with {len(trials)} trials for methodology audit.")

    # 1. Cache trial data
    data_cache = []
    b_filt, a_filt = butter(2, 2.0 / (20.0 / 2), btype="low")

    for t in trials:
        df, meta = ds.load_trial(t)
        t0 = df["time"].iloc[0]
        t_rel = df["time"].values - t0
        tors = df["TOR_request"].dropna()
        has_tor = len(tors) > 0 and not np.isnan(tors.iloc[0])
        tor = float(tors.iloc[0]) if has_tor else np.nan

        man_start_vals = df["manual_start"].dropna()
        has_man_start = len(man_start_vals) > 0 and not np.isnan(man_start_vals.iloc[0])
        man_start = float(man_start_vals.iloc[0]) if has_man_start else np.nan

        pre = df[(t_rel >= tor - 4.0) & (t_rel <= tor - 0.2)] if has_tor else df[t_rel <= man_start]
        if len(pre) < 10:
            pre = df[t_rel <= (tor if has_tor else man_start)]

        st_base = float(pre["steering_angle"].mean())
        ax_base = float(pre["longitudinal_acceleration"].mean())
        ay_base = float(pre["lateral_acceleration"].mean())

        post = df[t_rel >= (tor if has_tor else man_start)].copy()
        t_post = post["time"].values - t0
        bf_post = post["brake_force"].values
        acc_post = post["accelerator"].values
        st_raw = post["steering_angle"].values
        st_dev = np.abs(st_raw - st_base)
        st_spd = np.abs(post["steering_speed"].values)
        ax_post = post["longitudinal_acceleration"].values
        ay_post = post["lateral_acceleration"].values
        dist_obs = post["distance_to_obstacle"].values
        spd_post = post["longitudinal_speed"].values

        # Lane change time and obstacle longitudinal station passage time (T_pass)
        lcs = df["lane_change_time"].dropna()
        has_lc = len(lcs) > 0 and not np.isnan(lcs.iloc[0])
        t_lc = float(lcs.iloc[0]) if has_lc else np.nan

        pass_idx = np.where(dist_obs <= 0.0)[0]
        t_pass = t_post[pass_idx[0]] if len(pass_idx) > 0 else np.nan

        # Filtered steering
        if len(st_raw) > 15:
            st_filt = filtfilt(b_filt, a_filt, st_raw)
        else:
            st_filt = st_raw

        data_cache.append({
            "trial_id": meta.trial_id,
            "participant_id": meta.participant_id,
            "scenario_id": meta.scenario_id,
            "density": meta.density,
            "nback": meta.nback,
            "has_tor": has_tor,
            "tor": tor,
            "has_man_start": has_man_start,
            "man_start": man_start,
            "t0": t0,
            "total_dur": t_rel[-1] - t_rel[0],
            "t_post": t_post,
            "bf_post": bf_post,
            "st_dev": st_dev,
            "st_raw": st_raw,
            "st_filt": st_filt,
            "st_spd": st_spd,
            "ax_post": ax_post,
            "ay_post": ay_post,
            "ax_base": ax_base,
            "ay_base": ay_base,
            "st_base": st_base,
            "dist_obs": dist_obs,
            "spd_post": spd_post,
            "t_lc": t_lc,
            "t_pass": t_pass,
            "t_clear": t_pass,  # alias for backwards compatibility
        })

    tor_trials = [d for d in data_cache if d["has_tor"]]
    n_tor = len(tor_trials)
    print(f"Extracted {n_tor} trials with valid TOR.")

    # =========================================================================
    # AUDIT 1: T_first Threshold Sensitivity
    # =========================================================================
    brake_threshs = [5.0, 10.0, 15.0, 20.0, 30.0]
    steer_threshs = [0.02, 0.03, 0.05, 0.07]
    tfirst_records = []

    for bf_th in brake_threshs:
        for st_th in steer_threshs:
            t_first_list = []
            bf_first_cnt = 0
            st_first_cnt = 0
            simul_cnt = 0
            pre_man_cnt = 0

            for tr in tor_trials:
                tor = tr["tor"]
                man_start = tr["man_start"]
                t_post = tr["t_post"]

                bf_idx = np.where(tr["bf_post"] > bf_th)[0]
                t_bf = t_post[bf_idx[0]] if len(bf_idx) > 0 else np.nan

                st_idx = np.where(tr["st_dev"] > st_th)[0]
                t_st = t_post[st_idx[0]] if len(st_idx) > 0 else np.nan

                cands = [x for x in [t_bf, t_st] if not np.isnan(x)]
                t_first = min(cands) if cands else np.nan

                if not np.isnan(t_first):
                    t_first_list.append(t_first - tor)
                    if t_first < man_start:
                        pre_man_cnt += 1

                if not np.isnan(t_bf) and not np.isnan(t_st):
                    dt_sb = t_st - t_bf
                    if abs(dt_sb) <= 0.10:
                        simul_cnt += 1
                    elif dt_sb < -0.10:
                        st_first_cnt += 1
                    else:
                        bf_first_cnt += 1
                elif not np.isnan(t_st):
                    st_first_cnt += 1
                elif not np.isnan(t_bf):
                    bf_first_cnt += 1

            s_tf = pd.Series(t_first_list)
            tfirst_records.append({
                "brake_thresh_N": bf_th,
                "steer_thresh_rad": st_th,
                "steer_thresh_deg": float(np.degrees(st_th)),
                "t_first_median_s": float(s_tf.median()),
                "t_first_iqr_s": float(s_tf.quantile(0.75) - s_tf.quantile(0.25)),
                "pct_brake_first": float((bf_first_cnt / n_tor) * 100),
                "pct_steer_first": float((st_first_cnt / n_tor) * 100),
                "pct_simultaneous": float((simul_cnt / n_tor) * 100),
                "pct_input_before_manual_start": float((pre_man_cnt / n_tor) * 100),
            })

    df_tfirst = pd.DataFrame(tfirst_records)
    p_tfirst = os.path.join(output_dir, "tfirst_threshold_sensitivity.csv")
    df_tfirst.to_csv(p_tfirst, index=False)
    print(f"Saved: {p_tfirst}")

    # =========================================================================
    # AUDIT 2: Causal T_effective Definition Sensitivity
    # =========================================================================
    ax_thresholds = [0.3, 0.5, 0.8, 1.0]
    ay_thresholds = [0.2, 0.4, 0.6]
    persist_samples = [1, 2, 3]  # 50ms, 100ms, 150ms
    teff_records = []

    # Nominal baseline onset reference: 15N brake, 0.05 rad steer
    for tr in tor_trials:
        bf_idx = np.where(tr["bf_post"] > 15.0)[0]
        tr["t_first_brake_nom"] = tr["t_post"][bf_idx[0]] if len(bf_idx) > 0 else np.nan
        tr["idx_first_brake_nom"] = bf_idx[0] if len(bf_idx) > 0 else None

        st_idx = np.where(tr["st_dev"] > 0.05)[0]
        tr["t_first_steer_nom"] = tr["t_post"][st_idx[0]] if len(st_idx) > 0 else np.nan
        tr["idx_first_steer_nom"] = st_idx[0] if len(st_idx) > 0 else None

    # Audit Longitudinal Causal Response
    for d_th in ax_thresholds:
        for k in persist_samples:
            latencies = []
            det_cnt = 0
            causal_viols = 0
            for tr in tor_trials:
                if tr["idx_first_brake_nom"] is None:
                    continue
                i0 = tr["idx_first_brake_nom"]
                ax_sub = tr["ax_post"][i0:]
                t_sub = tr["t_post"][i0:]
                ax_ref = tr["ax_post"][i0]

                cond = (ax_sub <= ax_ref - d_th)
                for j in range(len(cond) - k + 1):
                    if np.all(cond[j : j + k]):
                        lat = t_sub[j] - tr["t_first_brake_nom"]
                        latencies.append(lat)
                        det_cnt += 1
                        if lat < 0:
                            causal_viols += 1
                        break
            s_lat = pd.Series(latencies)
            teff_records.append({
                "channel": "longitudinal_deceleration",
                "onset_trigger": "T_first_brake (15 N)",
                "delta_accel_thresh_m_s2": d_th,
                "persistence_samples": k,
                "persistence_duration_ms": k * 50,
                "detection_rate_pct": float(det_cnt / n_tor * 100),
                "latency_median_s": float(s_lat.median()),
                "latency_iqr_s": float(s_lat.quantile(0.75) - s_lat.quantile(0.25)),
                "latency_mean_s": float(s_lat.mean()),
                "latency_std_s": float(s_lat.std()),
                "causal_violations_count": causal_viols,
            })

    # Audit Lateral Causal Response
    for d_th in ay_thresholds:
        for k in persist_samples:
            latencies = []
            det_cnt = 0
            causal_viols = 0
            for tr in tor_trials:
                if tr["idx_first_steer_nom"] is None:
                    continue
                i0 = tr["idx_first_steer_nom"]
                ay_sub = tr["ay_post"][i0:]
                t_sub = tr["t_post"][i0:]
                ay_ref = tr["ay_post"][i0]

                cond = (np.abs(ay_sub - ay_ref) >= d_th)
                for j in range(len(cond) - k + 1):
                    if np.all(cond[j : j + k]):
                        lat = t_sub[j] - tr["t_first_steer_nom"]
                        latencies.append(lat)
                        det_cnt += 1
                        if lat < 0:
                            causal_viols += 1
                        break
            s_lat = pd.Series(latencies)
            teff_records.append({
                "channel": "lateral_acceleration",
                "onset_trigger": "T_first_steer (0.05 rad)",
                "delta_accel_thresh_m_s2": d_th,
                "persistence_samples": k,
                "persistence_duration_ms": k * 50,
                "detection_rate_pct": float(det_cnt / n_tor * 100),
                "latency_median_s": float(s_lat.median()),
                "latency_iqr_s": float(s_lat.quantile(0.75) - s_lat.quantile(0.25)),
                "latency_mean_s": float(s_lat.mean()),
                "latency_std_s": float(s_lat.std()),
                "causal_violations_count": causal_viols,
            })

    df_teff = pd.DataFrame(teff_records)
    p_teff = os.path.join(output_dir, "teffective_definition_sensitivity.csv")
    df_teff.to_csv(p_teff, index=False)
    print(f"Saved: {p_teff}")

    # =========================================================================
    # AUDIT 3: T_stable Definition Sensitivity & Right-Censoring
    # =========================================================================
    st_rate_threshs = [0.03, 0.05, 0.08]
    bf_rate_threshs = [10.0, 20.0, 30.0]
    persist_durations = [1.0, 1.5, 2.0]
    dt_sample = 0.05
    search_anchors = [
        "T_first + 2.0 s",
        "T_first + 1.0 s",
        "T_first + 3.0 s",
        "T_pass",
        "Time_Lane_Change",
    ]

    tstable_records = []
    for tr in tor_trials:
        # Precompute derivatives
        tr["d_bf"] = np.abs(np.diff(tr["bf_post"], prepend=tr["bf_post"][0])) / dt_sample

    for anch in search_anchors:
        for st_th in st_rate_threshs:
            for bf_th in bf_rate_threshs:
                for dur in persist_durations:
                    n_win = int(dur / dt_sample)
                    settled_cnt = 0
                    near_end_cnt = 0
                    eligible_cnt = 0
                    t_stab_list = []

                    for tr in tor_trials:
                        tor = tr["tor"]
                        t_post = tr["t_post"]
                        t_s_start = compute_stabilization_search_start(
                            anch,
                            tr["t_first_brake_nom"],
                            tr["t_first_steer_nom"],
                            tr["t_pass"],
                            tr["t_lc"],
                        )
                        if np.isnan(t_s_start):
                            continue

                        eligible_cnt += 1
                        idx_start = np.where(t_post >= t_s_start)[0]
                        if len(idx_start) < n_win:
                            continue
                        i0 = idx_start[0]

                        cond = (tr["st_spd"][i0:] <= st_th) & (tr["d_bf"][i0:] <= bf_th)
                        for k in range(len(cond) - n_win + 1):
                            if np.all(cond[k : k + n_win]):
                                t_s = float(t_post[i0 + k] - tor)
                                t_stab_list.append(t_s)
                                settled_cnt += 1
                                if (tr["total_dur"] - t_post[i0 + k]) <= 3.0:
                                    near_end_cnt += 1
                                break

                    s_ts = pd.Series(t_stab_list)
                    tstable_records.append({
                        "steer_speed_thresh_rad_s": st_th,
                        "brake_force_rate_thresh_N_s": bf_th,
                        "persistence_duration_s": dur,
                        "search_start_condition": anch,
                        "eligible_trials": eligible_cnt,
                        "settled_rate_pct": float(settled_cnt / eligible_cnt * 100) if eligible_cnt > 0 else 0.0,
                        "t_stable_median_s": float(s_ts.median()),
                        "t_stable_iqr_s": float(s_ts.quantile(0.75) - s_ts.quantile(0.25)),
                        "t_stable_mean_s": float(s_ts.mean()),
                        "t_stable_std_s": float(s_ts.std()),
                        "near_end_trials_pct": float(near_end_cnt / eligible_cnt * 100) if eligible_cnt > 0 else 0.0,
                    })

    df_tstable = pd.DataFrame(tstable_records)
    p_tstable = os.path.join(output_dir, "tstable_definition_sensitivity.csv")
    df_tstable.to_csv(p_tstable, index=False)
    print(f"Saved: {p_tstable}")

    # =========================================================================
    # AUDIT 4: Correction Metric Sensitivity (Filtering & Prominence)
    # =========================================================================
    corr_records = []
    gap_deg_list = [1.0, 2.0, 3.0, 5.0]

    for gap_deg in gap_deg_list:
        gap_rad = np.radians(gap_deg)
        acute_raw = []
        acute_filt = []
        full_raw = []
        full_filt = []

        for tr in tor_trials:
            tor = tr["tor"]
            t_post = tr["t_post"]
            st_raw = tr["st_raw"]
            st_filt = tr["st_filt"]

            full_raw.append(count_steering_reversals(st_raw, gap_rad))
            full_filt.append(count_steering_reversals(st_filt, gap_rad))

            # Acute window: first 8s post-TOR
            idx_acute = np.where((t_post >= tor) & (t_post <= tor + 8.0))[0]
            if len(idx_acute) > 10:
                acute_raw.append(count_steering_reversals(st_raw[idx_acute], gap_rad))
                acute_filt.append(count_steering_reversals(st_filt[idx_acute], gap_rad))

        s_ar = pd.Series(acute_raw)
        s_af = pd.Series(acute_filt)
        s_fr = pd.Series(full_raw)
        s_ff = pd.Series(full_filt)

        corr_records.append({
            "metric_type": "steering_wheel_reversals",
            "gap_threshold_deg": gap_deg,
            "gap_threshold_rad": gap_rad,
            "acute_window_s": 8.0,
            "acute_raw_median": float(s_ar.median()),
            "acute_raw_iqr": float(s_ar.quantile(0.75) - s_ar.quantile(0.25)),
            "acute_filt_median": float(s_af.median()),
            "acute_filt_iqr": float(s_af.quantile(0.75) - s_af.quantile(0.25)),
            "full_raw_median": float(s_fr.median()),
            "full_raw_iqr": float(s_fr.quantile(0.75) - s_fr.quantile(0.25)),
            "full_filt_median": float(s_ff.median()),
            "full_filt_iqr": float(s_ff.quantile(0.75) - s_ff.quantile(0.25)),
        })

    # Brake reapplication sensitivity across prominence thresholds
    prominences = [5.0, 10.0, 15.0, 20.0]
    for prom in prominences:
        reapp_cnts = []
        extrema_cnts = []
        for tr in tor_trials:
            bf = tr["bf_post"]
            peaks, _ = find_peaks(bf, prominence=prom, distance=10)
            valleys, _ = find_peaks(-bf, prominence=prom, distance=10)
            extrema_cnts.append(len(peaks))

            reapp = 0
            for v_idx in valleys:
                if bf[v_idx] < 20.0 and np.any(bf[v_idx:] > 30.0):
                    reapp += 1
            reapp_cnts.append(reapp)

        s_ex = pd.Series(extrema_cnts)
        s_re = pd.Series(reapp_cnts)
        corr_records.append({
            "metric_type": "brake_reapplications_and_peaks",
            "gap_threshold_deg": np.nan,
            "gap_threshold_rad": np.nan,
            "acute_window_s": np.nan,
            "acute_raw_median": np.nan,
            "acute_raw_iqr": np.nan,
            "acute_filt_median": np.nan,
            "acute_filt_iqr": np.nan,
            "full_raw_median": float(s_re.median()),
            "full_raw_iqr": float(s_re.quantile(0.75) - s_re.quantile(0.25)),
            "full_filt_median": float(s_ex.median()),
            "full_filt_iqr": float(s_ex.quantile(0.75) - s_ex.quantile(0.25)),
        })

    df_corr = pd.DataFrame(corr_records)
    p_corr = os.path.join(output_dir, "correction_metric_sensitivity.csv")
    df_corr.to_csv(p_corr, index=False)
    print(f"Saved: {p_corr}")

    # =========================================================================
    # AUDIT 5: Repeated-Measures Scenario Effects
    # =========================================================================
    # Build trial-level DataFrame
    trial_records = []
    for tr in tor_trials:
        # Determine first action with nominal thresholds (15N, 0.05 rad)
        t_bf = tr["t_first_brake_nom"]
        t_st = tr["t_first_steer_nom"]
        if not np.isnan(t_bf) and not np.isnan(t_st):
            if abs(t_st - t_bf) <= 0.10:
                act = "SIMULTANEOUS"
            elif t_st < t_bf:
                act = "STEER_FIRST"
            else:
                act = "BRAKE_FIRST"
        elif not np.isnan(t_st):
            act = "STEER_FIRST"
        elif not np.isnan(t_bf):
            act = "BRAKE_FIRST"
        else:
            act = "NONE"

        t_first = min([x for x in [t_bf, t_st] if not np.isnan(x)]) if (not np.isnan(t_bf) or not np.isnan(t_st)) else np.nan

        trial_records.append({
            "trial_id": tr["trial_id"],
            "participant_id": tr["participant_id"],
            "scenario_id": tr["scenario_id"],
            "density": tr["density"],
            "nback": tr["nback"],
            "delta_T_manual_start": tr["man_start"] - tr["tor"],
            "dt_req_to_first": t_first - tr["tor"] if not np.isnan(t_first) else np.nan,
            "peak_bf": float(np.max(tr["bf_post"][: int(2.0 / dt_sample)])) if len(tr["bf_post"]) > 0 else np.nan,
            "peak_st_deg": float(np.degrees(np.max(tr["st_dev"][: int(2.0 / dt_sample)]))) if len(tr["st_dev"]) > 0 else np.nan,
            "is_brake_first": 1 if act == "BRAKE_FIRST" else 0,
            "is_steer_first": 1 if act == "STEER_FIRST" else 0,
        })

    df_trials = pd.DataFrame(trial_records)
    metrics_rm = ["delta_T_manual_start", "dt_req_to_first", "peak_bf", "peak_st_deg", "is_brake_first"]
    pvals_d = []
    pvals_nb = []
    temp_records = []

    for m in metrics_rm:
        p_dens = df_trials.groupby(["participant_id", "density"])[m].mean().unstack()
        p_nb = df_trials.groupby(["participant_id", "nback"])[m].mean().unstack()

        # Density contrast 20 vs 0 (within-participant)
        diff_d = (p_dens[20] - p_dens[0]).dropna()
        n_d = len(diff_d)
        mean_d = float(diff_d.mean())
        se_d = float(diff_d.std(ddof=1) / np.sqrt(n_d))
        t_crit_d = float(stats.t.ppf(0.975, df=n_d - 1))
        ci_d_low = mean_d - t_crit_d * se_d
        ci_d_high = mean_d + t_crit_d * se_d
        t_d, p_d = stats.ttest_1samp(diff_d, 0.0)
        w_d, pw_d = stats.wilcoxon(diff_d) if not np.all(diff_d == 0) else (np.nan, np.nan)
        common_d = p_dens[[0, 10, 20]].dropna()
        fr_d_stat, fr_d_p = stats.friedmanchisquare(common_d[0], common_d[10], common_d[20])

        # N-back contrast 2 vs 0 (within-participant)
        diff_nb = (p_nb[2] - p_nb[0]).dropna()
        n_nb = len(diff_nb)
        mean_nb = float(diff_nb.mean())
        se_nb = float(diff_nb.std(ddof=1) / np.sqrt(n_nb))
        t_crit_nb = float(stats.t.ppf(0.975, df=n_nb - 1))
        ci_nb_low = mean_nb - t_crit_nb * se_nb
        ci_nb_high = mean_nb + t_crit_nb * se_nb
        t_nb, p_nb_val = stats.ttest_1samp(diff_nb, 0.0)
        w_nb, pw_nb = stats.wilcoxon(diff_nb) if not np.all(diff_nb == 0) else (np.nan, np.nan)
        common_nb = p_nb[[0, 1, 2]].dropna()
        fr_nb_stat, fr_nb_p = stats.friedmanchisquare(common_nb[0], common_nb[1], common_nb[2])

        pvals_d.append(float(p_d))
        pvals_nb.append(float(p_nb_val))

        temp_records.append({
            "metric": m,
            "n_participants": n_d,
            "density_20_minus_0_mean_diff": mean_d,
            "density_std_error": se_d,
            "density_95_ci_lower": ci_d_low,
            "density_95_ci_upper": ci_d_high,
            "density_paired_t_stat": float(t_d),
            "density_paired_t_pval": float(p_d),
            "density_wilcoxon_pval": float(pw_d),
            "density_friedman_pval": float(fr_d_p),
            "density_effect_supported": bool(p_d < 0.05),
            "density_association_supported": bool(p_d < 0.05),
            "nback_2_minus_0_mean_diff": mean_nb,
            "nback_std_error": se_nb,
            "nback_95_ci_lower": ci_nb_low,
            "nback_95_ci_upper": ci_nb_high,
            "nback_paired_t_stat": float(t_nb),
            "nback_paired_t_pval": float(p_nb_val),
            "nback_wilcoxon_pval": float(pw_nb),
            "nback_friedman_pval": float(fr_nb_p),
            "nback_effect_supported": bool(p_nb_val < 0.05),
            "nback_association_supported": bool(p_nb_val < 0.05),
        })

    # Holm-Bonferroni step-down correction across contrasts
    def holm_bonferroni(pvals: List[float]) -> List[float]:
        n = len(pvals)
        idx_sorted = np.argsort(pvals)
        adj_p = np.zeros(n)
        for rank, idx in enumerate(idx_sorted):
            multiplier = n - rank
            adj_p[idx] = min(1.0, pvals[idx] * multiplier)
        for k in range(1, n):
            idx_curr = idx_sorted[k]
            idx_prev = idx_sorted[k - 1]
            if adj_p[idx_curr] < adj_p[idx_prev]:
                adj_p[idx_curr] = adj_p[idx_prev]
        return [float(x) for x in adj_p]

    holm_d = holm_bonferroni(pvals_d)
    holm_nb = holm_bonferroni(pvals_nb)

    rm_records = []
    for i, rec in enumerate(temp_records):
        rec["density_holm_pval"] = holm_d[i]
        rec["nback_holm_pval"] = holm_nb[i]
        rm_records.append(rec)

    df_rm = pd.DataFrame(rm_records)
    p_rm = os.path.join(output_dir, "scenario_repeated_measures.csv")
    df_rm.to_csv(p_rm, index=False)
    print(f"Saved: {p_rm}")

    return {
        "tfirst": df_tfirst,
        "teffective": df_teff,
        "tstable": df_tstable,
        "correction": df_corr,
        "repeated_measures": df_rm,
    }


if __name__ == "__main__":
    run_sensitivity_audit()
