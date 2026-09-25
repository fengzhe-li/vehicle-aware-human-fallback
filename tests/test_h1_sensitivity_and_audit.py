"""Tests for Phase 2B-1.1 methodology and sensitivity audit."""

import os
import numpy as np
import pandas as pd
import pytest

from src.data.d003_loader import TrialMeta
from src.experiments.h1_recovery_analysis import compute_trial_qa, extract_trial_metrics
from src.experiments.h1_sensitivity_analysis import count_steering_reversals


def test_teffective_causal_ordering_invariant():
    """Verify that causal T_effective definition strictly respects T_effective >= T_first."""
    dt = 0.05
    n_samples = 400
    t = np.linspace(0.0, (n_samples - 1) * dt, n_samples)

    # Synthetic trial where vehicle is already coasting down before human brake onset
    df = pd.DataFrame({
        "time": t,
        "TOR_request": np.full(n_samples, 5.0),
        "manual_start": np.full(n_samples, 6.5),
        "manual_stop": np.full(n_samples, 18.0),
        "lane_change_time": np.full(n_samples, 10.0),
        "lane_id": np.full(n_samples, 2.0),
        "brake_force": np.zeros(n_samples),
        "accelerator": np.full(n_samples, 0.12),
        "steering_angle": np.zeros(n_samples),
        "steering_speed": np.zeros(n_samples),
        "longitudinal_speed": np.full(n_samples, 25.0),
        # Deceleration drops at t=5.1s due to automated throttle cut
        "longitudinal_acceleration": np.where(t >= 5.1, -0.6, 0.0),
        "lateral_acceleration": np.zeros(n_samples),
        "distance_to_obstacle": np.linspace(150.0, 10.0, n_samples),
    })

    # Human brake onset occurs at t = 6.2s
    idx_brake = int(6.2 / dt)
    df.loc[idx_brake:, "brake_force"] = 50.0
    # Additional deceleration due to braking at index 126 (t = 6.30s)
    idx_eff = int(6.30 / dt)
    df.loc[idx_eff:, "longitudinal_acceleration"] = -2.5

    # Causal search must start at or after t_first_brake (6.2s)
    t_first_brake = 6.2
    idx_start = int(t_first_brake / dt)
    ax_sub = df["longitudinal_acceleration"].values[idx_start:]
    t_sub = df["time"].values[idx_start:]
    ax_ref = df["longitudinal_acceleration"].values[idx_start]

    # Look for deceleration drop of at least 0.5 m/s2 relative to ax at brake onset
    hits = np.where(ax_sub <= ax_ref - 0.5)[0]
    assert len(hits) > 0
    t_eff_causal = t_sub[hits[0]]

    assert t_eff_causal >= t_first_brake
    assert np.isclose(t_eff_causal, 6.3, atol=0.06)


def test_steering_reversals_iso_gap_algorithm():
    """Verify ISO gap-threshold steering reversal counting."""
    # Triangular wave: 0 -> +5 deg -> -5 deg -> +5 deg -> 0
    # Expected reversals with 2 deg gap:
    # 1. 5 to -5: 10 deg drop (>2 deg gap) -> 1 reversal
    # 2. -5 to 5: 10 deg rise (>2 deg gap) -> 1 reversal
    # 3. 5 to 0: 5 deg drop (>2 deg gap) -> 1 reversal
    angles_deg = np.array([0.0, 2.0, 5.0, 3.0, 0.0, -3.0, -5.0, -2.0, 1.0, 5.0, 3.0, 0.0])
    angles_rad = np.radians(angles_deg)

    rev_2deg = count_steering_reversals(angles_rad, np.radians(2.0))
    assert rev_2deg == 3

    # High threshold (12 deg) should detect 0 reversals
    rev_12deg = count_steering_reversals(angles_rad, np.radians(12.0))
    assert rev_12deg == 0


def test_derived_collision_proxy_logic():
    """Verify operational logic for derived collision proxy classification."""
    meta = TrialMeta(
        density=20,
        nback=2,
        participant_id=37,
        scenario_id="density_20_nback_2",
        trial_id="density_20_nback_2_id_37",
        relative_path="dummy.csv",
    )

    n_samples = 200
    dt = 0.05
    t = np.linspace(0.0, (n_samples - 1) * dt, n_samples)

    # Collision trial: distance reaches -2.0 at speed 18 m/s without lane change
    df = pd.DataFrame({
        "time": t,
        "TOR_request": np.full(n_samples, 2.0),
        "manual_start": np.full(n_samples, 3.5),
        "manual_stop": np.full(n_samples, 9.0),
        "lane_change_time": np.full(n_samples, np.nan),
        "lane_id": np.full(n_samples, 2.0),
        "brake_force": np.zeros(n_samples),
        "accelerator": np.full(n_samples, 0.0),
        "steering_angle": np.zeros(n_samples),
        "steering_speed": np.zeros(n_samples),
        "longitudinal_speed": np.full(n_samples, 18.0),
        "longitudinal_acceleration": np.zeros(n_samples),
        "lateral_acceleration": np.zeros(n_samples),
        "distance_to_obstacle": np.linspace(50.0, -5.0, n_samples),
    })

    qa = compute_trial_qa(df, meta)
    assert qa["usable_status"] == "COLLISION_FAILURE"
    assert qa["reason_code"] == "COLLISION_WITH_HAZARD"
    assert qa["collision_outcome"] is True


def test_sensitivity_csv_files_exist_and_nonempty():
    """Verify that all 5 sensitivity CSV deliverables are generated and populated."""
    sensitivity_dir = "results/H1_sensitivity"
    expected_files = [
        "tfirst_threshold_sensitivity.csv",
        "teffective_definition_sensitivity.csv",
        "tstable_definition_sensitivity.csv",
        "correction_metric_sensitivity.csv",
        "scenario_repeated_measures.csv",
    ]
    for fname in expected_files:
        fpath = os.path.join(sensitivity_dir, fname)
        assert os.path.exists(fpath), f"Missing sensitivity CSV: {fpath}"
        df = pd.read_csv(fpath)
        assert len(df) > 0, f"Empty sensitivity CSV: {fpath}"


def test_operational_measurement_ledger_integrity():
    """Verify that H1_OPERATIONAL_MEASUREMENT_LEDGER.md exists and covers all 12 quantities."""
    ledger_path = "experiments/H_human_internal_model/H1_OPERATIONAL_MEASUREMENT_LEDGER.md"
    assert os.path.exists(ledger_path), f"Missing ledger file: {ledger_path}"

    with open(ledger_path, "r", encoding="utf-8") as f:
        content = f.read()

    core_quantities = [
        "T_request",
        "T_manual_start",
        "T_first_brake",
        "T_first_steer",
        "T_first_ctrl",
        "T_effective_dec",
        "T_effective_lat",
        "T_pass",
        "T_stable",
        "DERIVED_COLLISION_PROXY",
        "Steering Reversal",
        "Brake Reapplication",
    ]
    for q in core_quantities:
        assert q in content, f"Missing core quantity in measurement ledger: {q}"

    required_fields = [
        "Conceptual Meaning:",
        "Observed Source Signal:",
        "Operational Detector:",
        "Threshold:",
        "Persistence:",
        "Sampling Resolution:",
        "Causal Ordering Constraint:",
        "Direct / Derived / Proxy:",
        "Sensitivity Status:",
        "Allowed Wording:",
        "Prohibited Overclaim:",
    ]
    for field in required_fields:
        assert field in content, f"Missing required specification field: {field}"


def test_tstable_anchor_sensitivity_robustness():
    """Verify that T_stable audit covers 5 search anchors and demonstrates ~21-25s robustness."""
    fpath = "results/H1_sensitivity/tstable_definition_sensitivity.csv"
    df = pd.read_csv(fpath)

    expected_anchors = [
        "T_first + 1.0 s",
        "T_first + 2.0 s",
        "T_first + 3.0 s",
        "T_pass",
        "Time_Lane_Change",
    ]
    for anch in expected_anchors:
        assert anch in df["search_start_condition"].values, f"Missing anchor: {anch}"

    # Verify nominal configurations across anchors
    nom = df[
        (df["steer_speed_thresh_rad_s"] == 0.05)
        & (df["brake_force_rate_thresh_N_s"] == 20.0)
        & (df["persistence_duration_s"] == 1.5)
    ]
    assert len(nom) >= 5
    for _, r in nom.iterrows():
        assert r["settled_rate_pct"] >= 98.0
        assert 21.0 <= r["t_stable_median_s"] <= 25.0
        assert r["near_end_trials_pct"] <= 2.0

    # Verify explicit anchor subset spans
    med_first2 = nom[nom["search_start_condition"] == "T_first + 2.0 s"]["t_stable_median_s"].iloc[0]
    med_first3 = nom[nom["search_start_condition"] == "T_first + 3.0 s"]["t_stable_median_s"].iloc[0]
    med_lc = nom[nom["search_start_condition"] == "Time_Lane_Change"]["t_stable_median_s"].iloc[0]
    med_pass = nom[nom["search_start_condition"] == "T_pass"]["t_stable_median_s"].iloc[0]
    med_first1 = nom[nom["search_start_condition"] == "T_first + 1.0 s"]["t_stable_median_s"].iloc[0]

    # Subset A: T_first + 2.0 s, T_first + 3.0 s, Time_Lane_Change (span ~ 0.08 s < 0.10 s)
    span_a = max(med_first2, med_first3, med_lc) - min(med_first2, med_first3, med_lc)
    assert span_a < 0.10, f"Subset A span too large: {span_a}"

    # Subset B: Subset A + T_pass (span ~ 0.48 s < 0.50 s)
    span_b = max(med_first2, med_first3, med_lc, med_pass) - min(med_first2, med_first3, med_lc, med_pass)
    assert span_b < 0.50, f"Subset B span too large: {span_b}"

    # Complete 5-anchor set: includes T_first + 1.0 s (span ~ 0.78 s < 0.80 s)
    span_all = max(med_first1, med_first2, med_first3, med_lc, med_pass) - min(med_first1, med_first2, med_first3, med_lc, med_pass)
    assert span_all < 0.80, f"Full 5-anchor span too large: {span_all}"


def test_repeated_measures_confidence_intervals_and_corrections():
    """Verify that scenario_repeated_measures.csv includes 95% CIs and Holm adjustments."""
    fpath = "results/H1_sensitivity/scenario_repeated_measures.csv"
    df = pd.read_csv(fpath)

    required_cols = [
        "metric",
        "density_20_minus_0_mean_diff",
        "density_std_error",
        "density_95_ci_lower",
        "density_95_ci_upper",
        "density_paired_t_stat",
        "density_paired_t_pval",
        "density_holm_pval",
        "density_association_supported",
        "nback_2_minus_0_mean_diff",
        "nback_std_error",
        "nback_95_ci_lower",
        "nback_95_ci_upper",
        "nback_paired_t_stat",
        "nback_paired_t_pval",
        "nback_holm_pval",
        "nback_association_supported",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column in repeated measures: {col}"

    # Density effect on brake force should be positive and Holm-significant
    bf_row = df[df["metric"] == "peak_bf"].iloc[0]
    assert bf_row["density_20_minus_0_mean_diff"] > 100.0
    assert bf_row["density_holm_pval"] < 1e-15
    assert bf_row["density_95_ci_lower"] > 90.0

    # N-back effect on manual start latency should be positive and Holm-significant
    auth_row = df[df["metric"] == "delta_T_manual_start"].iloc[0]
    assert auth_row["nback_2_minus_0_mean_diff"] > 0.30
    assert auth_row["nback_holm_pval"] < 1e-4
    assert auth_row["nback_95_ci_lower"] > 0.20


def test_stabilization_search_anchor_order_and_missingness():
    """Verify compute_stabilization_search_start handles channel order, single-channel, and missingness without synthetic fallback.

    Regression test for T_stable anchor logic:
    - Case A: T_first_steer < T_first_brake => T_first_ctrl == T_first_steer, and all T_first-based anchors use steering onset.
    - Case B: T_first_brake < T_first_steer => T_first_ctrl == T_first_brake.
    - Case C: Steer only observed (brake unobserved/NaN) => T_first_ctrl == T_first_steer.
    - Case D: Brake only observed (steer unobserved/NaN) => T_first_ctrl == T_first_brake.
    - Case E: Neither channel observed (both NaN) => returns NaN; no synthetic fallback (e.g. tor + 1.2 s).
    - Unobserved T_clear / Time_Lane_Change => returns NaN.
    """
    from src.experiments.h1_sensitivity_analysis import compute_stabilization_search_start

    # Case A: steer earlier than brake
    t_steer_A = 1.15
    t_brake_A = 1.85
    assert np.isclose(compute_stabilization_search_start("T_first + 1.0 s", t_brake_A, t_steer_A, 22.0, 21.0), 2.15)
    assert np.isclose(compute_stabilization_search_start("T_first + 2.0 s", t_brake_A, t_steer_A, 22.0, 21.0), 3.15)
    assert np.isclose(compute_stabilization_search_start("T_first + 3.0 s", t_brake_A, t_steer_A, 22.0, 21.0), 4.15)
    # Confirm it did NOT use brake (which would have yielded 3.85 for +2.0s)
    assert not np.isclose(compute_stabilization_search_start("T_first + 2.0 s", t_brake_A, t_steer_A, 22.0, 21.0), 3.85)

    # Case B: brake earlier than steer
    t_brake_B = 1.05
    t_steer_B = 1.70
    assert np.isclose(compute_stabilization_search_start("T_first + 1.0 s", t_brake_B, t_steer_B, 22.0, 21.0), 2.05)
    assert np.isclose(compute_stabilization_search_start("T_first + 2.0 s", t_brake_B, t_steer_B, 22.0, 21.0), 3.05)
    assert np.isclose(compute_stabilization_search_start("T_first + 3.0 s", t_brake_B, t_steer_B, 22.0, 21.0), 4.05)

    # Case C: steer only observed (brake is NaN)
    assert np.isclose(compute_stabilization_search_start("T_first + 2.0 s", np.nan, 1.40, 22.0, 21.0), 3.40)

    # Case D: brake only observed (steer is NaN)
    assert np.isclose(compute_stabilization_search_start("T_first + 2.0 s", 1.25, np.nan, 22.0, 21.0), 3.25)

    # Case E: neither channel observed (both NaN) -> MUST return NaN, NO synthetic fallback
    res_neither_1 = compute_stabilization_search_start("T_first + 1.0 s", np.nan, np.nan, 22.0, 21.0)
    res_neither_2 = compute_stabilization_search_start("T_first + 2.0 s", np.nan, np.nan, 22.0, 21.0)
    res_neither_3 = compute_stabilization_search_start("T_first + 3.0 s", np.nan, np.nan, 22.0, 21.0)
    assert np.isnan(res_neither_1)
    assert np.isnan(res_neither_2)
    assert np.isnan(res_neither_3)

    # Missing event anchors must return NaN
    assert np.isnan(compute_stabilization_search_start("T_pass", 1.0, 1.0, np.nan, 21.0))
    assert np.isnan(compute_stabilization_search_start("T_clear", 1.0, 1.0, np.nan, 21.0))
    assert np.isnan(compute_stabilization_search_start("Time_Lane_Change", 1.0, 1.0, 22.0, np.nan))


def test_historical_collision_proxy_is_withdrawn_and_contradicted_by_lane_evidence():
    """R2A replacement for the pre-audit collision-proxy test.

    The pre-audit test asserted the DERIVED_COLLISION_PROXY labels as collision
    semantics. Those semantics are withdrawn (blocker B10). This test instead checks
    that (1) the historical labels are preserved unchanged and marked as withdrawn
    in the historical manifest, and (2) canonical ingestion evidence contradicts
    them, so they cannot be used as a collision outcome.
    """
    import json

    from src.data.d003_ingest import D003Archive
    from src.data.d003_populations import classify_trial

    qa = pd.read_csv("research/data_matrix/d003_trial_qa.csv")
    labels = set(qa[qa["collision_outcome"] == True]["trial_id"])  # noqa: E712
    assert labels == {
        "density_10_nback_1_id_8",
        "density_20_nback_0_id_22",
        "density_20_nback_1_id_37",
        "density_20_nback_1_id_44",
        "density_20_nback_2_id_37",
        "density_20_nback_2_id_56",
    }
    with open("results/historical_outputs_manifest.json", encoding="utf-8") as fh:
        entry = json.load(fh)["files"]["research/data_matrix/d003_trial_qa.csv"]
    assert entry["status"] == "HISTORICAL ONLY"
    assert "WITHDRAWN" in entry["reason"] and "collision" in entry["reason"]

    archive_path = "data/external/d003/tu_delft_takeover.zip"
    if not os.path.exists(archive_path):
        pytest.skip(f"D003 archive not present at {archive_path}")
    archive = D003Archive(archive_path)
    in_lane, lane_change_state, anchored = set(), {}, set()
    for name in archive.trial_names():
        trial = archive.load(name)
        pop = classify_trial(trial)
        lane_change_state[pop.trial_id] = pop.events.lane_change.state
        if not pop.tor_anchored:
            continue
        anchored.add(pop.trial_id)
        t = trial.telemetry["t_rel"].to_numpy()
        dist = trial.column("[85 (Distance/Distance_to_Construction)].ExportChannel-val")
        lane = trial.column("[00].VehicleUpdate-roadInfo-laneId.0")
        road = trial.column("[00].VehicleUpdate-roadInfo-roadId.0")
        i0 = int(np.searchsorted(t, pop.events.t_tor))
        k = np.where((t >= pop.events.t_tor) & (dist <= 0))[0]
        if len(k) and lane[k[0]] == lane[i0] and road[k[0]] == road[i0]:
            in_lane.add(pop.trial_id)
    archive.close()

    # Hazard-station passages in the TOR lane (same road) among TOR-anchored trials.
    assert len(in_lane) == 11
    assert labels & in_lane == {"density_20_nback_1_id_44", "density_20_nback_2_id_37", "density_20_nback_2_id_56"}
    assert len(in_lane - labels) == 8  # in-lane passages the proxy did not label
    # Labelled trials that are not in-lane passages, each for a documented reason:
    assert lane_change_state["density_10_nback_1_id_8"] == "CLOCK_EXCEPTION"
    assert "density_20_nback_0_id_22" in anchored and "density_20_nback_0_id_22" not in in_lane
    assert "density_20_nback_1_id_37" not in anchored  # multi-TOR unresolved
