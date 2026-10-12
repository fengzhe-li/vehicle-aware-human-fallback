"""Automated test suite for VLA-Informed Handover Feasibility Analysis (Phase G).

Covers all 11 required verification categories:
1. Model-output parsing (`parse_cot_and_actions`, codebook extraction, CoT separation)
2. Unit and coordinate conversion (`corners_to_center_and_heading`, `rollout_indices`, angle wrapping)
3. Physical constraint calculations (`compute_waypoint_kinematics`, `verify_trajectory_feasibility`, friction sensitivity)
4. Missing or invalid predictions (empty, incomplete horizon, NaN/Inf, timestamp discontinuity)
5. Takeover-timing assumptions (`OBSERVED_T0` vs `HYPOTHETICAL_VLA_PREDICTED_STATE`, interpolation, remaining distance)
6. R3B adapter compatibility (exact mathematical agreement with `src.experiments.r3b_braking_bounds`)
7. Boundary and interval handling (`UNIFORMLY_POSITIVE`, `PARAMETER_SENSITIVE`, `UNIFORMLY_VIOLATED`, `boundary_proximity_flag`)
8. Insufficient-evidence classifications (missing observed obstacle, stationary ego, lateral corridor departure, d_rem <= 0)
9. Artifact provenance (real saved AutoVLA predictions, `predicts_human_takeover_request == False`, hardware/checkpoint metadata)
10. Deterministic evaluation and report generation (byte-identical JSON and HTML regeneration)
11. Preservation of original research code, 42-claim ledger, and frozen results (`git diff` clean check)
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import pytest

from src.experiments.r3b_braking_bounds import (
    BRANCHES,
    PARAMETERS,
    bound,
    classify,
    intervals_for,
)

from extensions.vla_handover_feasibility.action_tokenizer import (
    ACTION_VOCAB_SIZE,
    BASE_QWEN_VOCAB_SIZE,
    DEFAULT_CODEBOOK_PATH,
    AutoVLAActionTokenizer,
    corners_to_center_and_heading,
    wrap_angle_rad,
)
from extensions.vla_handover_feasibility.experiment_runner import (
    DEFAULT_ARTIFACTS_DIR,
    evaluate_all_predictions_and_counterfactuals,
)
from extensions.vla_handover_feasibility.r3b_adapter import (
    DEFAULT_TAKEOVER_REQUEST_TIMES_S,
    evaluate_r3b_branches_at_state,
    evaluate_takeover_at_request_time,
    evaluate_takeover_timing_schedule,
    interpolate_hypothetical_state_at_tau,
)
from extensions.vla_handover_feasibility.report_generator import (
    generate_interactive_report,
)
from extensions.vla_handover_feasibility.schemas import (
    FeasibilityClassification,
    ObstacleSourceType,
    TakeoverR3BStatus,
    TrajectoryWaypoint,
)
from extensions.vla_handover_feasibility.trajectory_verifier import (
    GRAVITY_MPS2,
    VerifierLimits,
    compute_waypoint_kinematics,
    verify_trajectory_feasibility,
)
from extensions.vla_handover_feasibility.vla_inference import (
    DEFAULT_DATA_DIR,
    DEFAULT_PREDICTIONS_DIR,
    build_autovla_user_message,
    load_prediction_artifact,
    parse_cot_and_actions,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


# =============================================================================
# 1. Model-output parsing tests
# =============================================================================


def test_model_output_parsing_fast_and_cot() -> None:
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    raw_text = (
        "<think>\nThe ego vehicle is travelling at 13.05 m/s behind a lead vehicle.\n</think>\n"
        "<answer>\nThe final output action is: "
        "<action_21><action_127><action_266><action_896><action_1007>"
        "<action_1256><action_1007><action_896><action_11><action_11>\n</answer>"
    )
    expected_indices = [21, 127, 266, 896, 1007, 1256, 1007, 896, 11, 11]
    token_ids = [100, 101] + [BASE_QWEN_VOCAB_SIZE + k for k in expected_indices] + [102]

    cot_text, act_tids, code_idxs, is_valid, notes = parse_cot_and_actions(
        raw_text=raw_text,
        generated_token_ids=token_ids,
        action_tokenizer=tokenizer,
    )
    assert is_valid is True
    assert code_idxs == expected_indices
    assert act_tids == [BASE_QWEN_VOCAB_SIZE + k for k in expected_indices]
    assert cot_text is not None and "travelling at 13.05 m/s" in cot_text
    assert "Decoded 10 action tokens" in notes


def test_model_output_parsing_incomplete_and_out_of_range() -> None:
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    short_text = "<answer><action_5><action_12></answer>"
    _, _, code_idxs, is_valid, notes = parse_cot_and_actions(
        raw_text=short_text,
        generated_token_ids=[BASE_QWEN_VOCAB_SIZE + 5, BASE_QWEN_VOCAB_SIZE + 12],
        action_tokenizer=tokenizer,
    )
    assert is_valid is False
    assert code_idxs == [5, 12]
    assert "Incomplete action token sequence" in notes

    with pytest.raises(ValueError, match="out of valid codebook range"):
        tokenizer.extract_codebook_indices_from_text("<action_2048>")


def test_build_autovla_user_message_structure() -> None:
    dummy_imgs = [DEFAULT_DATA_DIR / "agent_vocab.pkl"] * 4
    msgs, prompt_str = build_autovla_user_message(
        front_images=dummy_imgs,
        front_left_images=dummy_imgs,
        front_right_images=dummy_imgs,
        ego_speed_mps=12.345,
        ego_accel_mps2=0.567,
        driving_command="keep forward",
        use_cot=True,
    )
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    img_items = [c for c in msgs[0]["content"] if c["type"] == "image"]
    assert len(img_items) == 12
    assert "theego velocity is 12.35 m/s" in prompt_str
    assert "Please reason step by step" in prompt_str


# =============================================================================
# 2. Unit and coordinate conversion tests
# =============================================================================


def test_unit_and_coordinate_conversion_and_rollout() -> None:
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    assert tokenizer.n_bins == ACTION_VOCAB_SIZE
    assert tokenizer.raw_corners.shape == (2048, 6, 4, 2)

    # Verify angle wrapping
    assert math.isclose(wrap_angle_rad(math.pi + 0.2), -math.pi + 0.2, abs_tol=1e-9)
    assert math.isclose(wrap_angle_rad(-math.pi - 0.3), math.pi - 0.3, abs_tol=1e-9)

    # Verify synthetic straight-forward bounding box corners
    # 0: front-left (2, 1), 1: front-right (2, -1), 2: rear-right (-2, -1), 3: rear-left (-2, 1)
    box_zero_yaw = np.array([[[2.0, 1.0], [2.0, -1.0], [-2.0, -1.0], [-2.0, 1.0]]])
    pose = corners_to_center_and_heading(box_zero_yaw)
    assert pose.shape == (1, 3)
    assert math.isclose(pose[0, 0], 0.0, abs_tol=1e-9)
    assert math.isclose(pose[0, 1], 0.0, abs_tol=1e-9)
    assert math.isclose(pose[0, 2], 0.0, abs_tol=1e-9)

    # Verify rollout matches 10 waypoints at dt = 0.5 s over 5.0 s horizon
    seq = [21, 127, 266, 896, 1007, 1256, 1007, 896, 11, 11]
    wps = tokenizer.decode_indices_to_waypoints(seq)
    assert len(wps) == 10
    assert math.isclose(wps[0].t_s, 0.5, abs_tol=1e-6)
    assert math.isclose(wps[-1].t_s, 5.0, abs_tol=1e-6)
    # Token 21 is straight forward at ~13.2 m/s (x ~ 6.604 m, |y| < 0.02 m, |heading| < 0.01 rad)
    assert 6.5 < wps[0].x_m < 6.7
    assert abs(wps[0].y_m) < 0.05
    assert abs(wps[0].heading_rad) < 0.02


# =============================================================================
# 3. Physical constraint calculations tests
# =============================================================================


def test_physical_constraint_calculations_satisfied_and_violated() -> None:
    # Construct a smooth constant-speed 10 m/s straight trajectory (dx = 5.0 m per 0.5 s step)
    smooth_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=5.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_ok, kin_ok = verify_trajectory_feasibility(
        scene_id="synthetic_smooth",
        mode="test",
        waypoints=smooth_wps,
        initial_speed_mps=10.0,
        initial_accel_mps2=0.0,
    )
    assert res_ok.classification == FeasibilityClassification.CONSTRAINTS_SATISFIED
    assert len(res_ok.violation_reasons) == 0
    assert math.isclose(res_ok.max_implied_speed_mps, 10.0, abs_tol=1e-5)
    assert math.isclose(res_ok.max_braking_demand_mps2, 0.0, abs_tol=1e-5)
    assert all(c.passed for c in res_ok.checks)
    assert len(kin_ok) == 10

    # Construct a trajectory that slams brakes from v0=20 m/s to v1=2 m/s in 0.5 s -> a_lon = -36 m/s^2
    viol_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=1.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_viol, _ = verify_trajectory_feasibility(
        scene_id="synthetic_violation",
        mode="test",
        waypoints=viol_wps,
        initial_speed_mps=20.0,
        initial_accel_mps2=0.0,
    )
    assert res_viol.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    assert math.isclose(res_viol.max_braking_demand_mps2, 36.0, abs_tol=1e-4)
    assert any("exceeds physical vehicle capability" in r for r in res_viol.violation_reasons)
    # Check friction sensitivity: 36 m/s^2 exceeds mu*g for all mu in {1.0, 0.7, 0.5, 0.35}
    assert all(not fs.braking_within_friction for fs in res_viol.friction_sensitivity)


# =============================================================================
# 4. Missing or invalid predictions tests
# =============================================================================


def test_missing_or_invalid_predictions_handling() -> None:
    # Empty waypoints
    res_empty, _ = verify_trajectory_feasibility(
        scene_id="empty_scene",
        mode="test",
        waypoints=[],
        initial_speed_mps=10.0,
    )
    assert res_empty.classification == FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert any("zero trajectory waypoints" in r for r in res_empty.insufficient_evidence_reasons)

    # Incomplete horizon (only 4 steps instead of 10)
    short_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=4.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 5)
    ]
    res_short, _ = verify_trajectory_feasibility(
        scene_id="short_scene",
        mode="test",
        waypoints=short_wps,
        initial_speed_mps=8.0,
    )
    assert res_short.classification == FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert any("Incomplete trajectory horizon" in r for r in res_short.insufficient_evidence_reasons)

    # Non-finite (NaN) coordinate
    nan_wps = [
        TrajectoryWaypoint(
            step=i,
            t_s=0.5 * i,
            x_m=float("nan") if i == 3 else 4.0 * i,
            y_m=0.0,
            heading_rad=0.0,
        )
        for i in range(1, 11)
    ]
    res_nan, _ = verify_trajectory_feasibility(
        scene_id="nan_scene",
        mode="test",
        waypoints=nan_wps,
        initial_speed_mps=8.0,
    )
    assert res_nan.classification == FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert any("Non-finite" in r for r in res_nan.insufficient_evidence_reasons)


def test_synthetic_verifier_fixtures_c2_through_c10() -> None:
    """Test separate, clearly labelled synthetic fixtures designed to trigger each violation and insufficient-evidence outcome."""
    # Fixture C2: Backward longitudinal jump (dx < -0.05 m)
    c2_wps = [
        TrajectoryWaypoint(
            step=i,
            t_s=0.5 * i,
            x_m=5.0 * i if i < 4 else (15.0 - 0.5 * (i - 3)),
            y_m=0.0,
            heading_rad=0.0,
        )
        for i in range(1, 11)
    ]
    res_c2, _ = verify_trajectory_feasibility("fixture_c2_reverse", "test", c2_wps, initial_speed_mps=10.0)
    assert res_c2.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    assert any("C2" in c.check_id and not c.passed for c in res_c2.checks)

    # Fixture C3: Implied speed exceeding highway ceiling (v > 45.0 m/s)
    c3_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=25.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_c3, _ = verify_trajectory_feasibility("fixture_c3_overspeed", "test", c3_wps, initial_speed_mps=50.0)
    assert res_c3.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    assert any(c.check_id == "C3_IMPLIED_SPEED_LIMIT" and not c.passed for c in res_c3.checks)

    # Fixture C4: Excessive forward longitudinal acceleration (a_lon > 4.5 m/s^2)
    # Step 1: v1 = 10 m/s, Step 2: v2 = 14 m/s (dt=0.5s -> a_lon = +8.0 m/s^2 > 4.5 m/s^2)
    c4_x = [5.0]
    for i in range(2, 11):
        c4_x.append(c4_x[-1] + 7.0)
    c4_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=c4_x[i - 1], y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_c4, _ = verify_trajectory_feasibility("fixture_c4_fwd_accel", "test", c4_wps, initial_speed_mps=10.0, initial_accel_mps2=0.0)
    assert res_c4.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    assert any(c.check_id == "C4_LONGITUDINAL_ACCELERATION_LIMIT" and not c.passed for c in res_c4.checks)

    # Fixture C7 & C8 & C9: Sharp lateral weave triggering lateral accel, yaw rate, and friction circle violations
    c789_wps = [
        TrajectoryWaypoint(
            step=i,
            t_s=0.5 * i,
            x_m=8.0 * i,
            y_m=2.5 * ((-1) ** i),
            heading_rad=0.55 * ((-1) ** i),
        )
        for i in range(1, 11)
    ]
    res_c789, _ = verify_trajectory_feasibility("fixture_c789_lateral_yaw", "test", c789_wps, initial_speed_mps=16.0)
    assert res_c789.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    failed_ids = {c.check_id for c in res_c789.checks if not c.passed}
    assert "C7_LATERAL_ACCELERATION_LIMIT" in failed_ids
    assert "C8_YAW_RATE_LIMIT" in failed_ids
    assert "C9_FRICTION_CIRCLE_LIMIT" in failed_ids

    # Fixture C10: Initial acceleration discontinuity during active motion (|a_lon(1) - ax(0)| > 6.0 m/s^2)
    # Ego is braking at ax(0) = -3.5 m/s^2 at v0 = 10.0 m/s, but Step 1 accelerates at +3.0 m/s^2 (v1 = 11.5 m/s, dx = 5.75 m)
    # Jump is |3.0 - (-3.5)| = 6.5 m/s^2 > 6.0 m/s^2, while |a_lon| <= 4.5 m/s^2 passes C4/C5
    c10_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=5.75 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_c10, _ = verify_trajectory_feasibility(
        "fixture_c10_accel_jump", "test", c10_wps, initial_speed_mps=10.0, initial_accel_mps2=-3.5
    )
    assert res_c10.classification == FeasibilityClassification.CONSTRAINTS_VIOLATED
    assert any(c.check_id == "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY" and not c.passed for c in res_c10.checks)

    # Fixture Stationary Ego: Near-zero path (< 0.25 m) and near-zero speed (< 0.1 m/s) -> INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    stat_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=0.01 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    res_stat, _ = verify_trajectory_feasibility(
        "fixture_stationary_ego",
        "test",
        stat_wps,
        initial_speed_mps=0.002,
        initial_accel_mps2=-0.01,
        treat_stationary_as_not_applicable=True,
    )
    assert res_stat.classification == FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    c10_check = next(c for c in res_stat.checks if c.check_id == "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY")
    assert c10_check.passed is True


# =============================================================================
# 5. Takeover-timing assumptions tests
# =============================================================================


def test_takeover_timing_assumptions_and_state_provenance() -> None:
    wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=5.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    kin = compute_waypoint_kinematics(wps, initial_speed_mps=10.0)

    schedule = evaluate_takeover_timing_schedule(
        scene_id="timing_test",
        inference_mode="fast",
        initial_speed_mps=10.0,
        waypoints=wps,
        kinematics=kin,
        obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
        initial_obstacle_distance_d0_m=30.0,
        request_times_s=(0.0, 0.5, 1.0, 1.5, 2.0),
    )
    assert len(schedule) == 5
    # Crucial Priority 2 requirement: never label a complete scenario state as OBSERVED_T0
    # when it includes a counterfactual obstacle assumption!
    assert schedule[0].state_source == "OBSERVED_EGO_T0_PLUS_ASSUMED_OBSTACLE_D0"
    assert schedule[0].state_source != "OBSERVED_T0"
    assert all(ev.state_source == "HYPOTHETICAL_VLA_STATE_PLUS_ASSUMED_OBSTACLE_D0" for ev in schedule[1:])

    # Verify observed stationary obstacle vs moving lead obstacle state provenance at t=0
    ev_obs_stat = evaluate_takeover_at_request_time(
        scene_id="obs_stationary",
        inference_mode="fast",
        tau_req_s=0.0,
        initial_speed_mps=10.0,
        waypoints=wps,
        kinematics=kin,
        obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
        initial_obstacle_distance_d0_m=55.0,
        observed_lead_speed_mps=0.0,
    )
    assert ev_obs_stat.state_source == "OBSERVED_EGO_T0_AND_OBSERVED_STATIONARY_OBSTACLE"

    ev_obs_moving = evaluate_takeover_at_request_time(
        scene_id="obs_moving",
        inference_mode="fast",
        tau_req_s=0.0,
        initial_speed_mps=10.0,
        waypoints=wps,
        kinematics=kin,
        obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
        initial_obstacle_distance_d0_m=37.3,
        observed_lead_speed_mps=4.62,
    )
    assert ev_obs_moving.state_source == "OBSERVED_EGO_T0_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD"

    # Remaining distance shrinks by 5.0 m per 0.5 s step, so P1 distance & time margins strictly decrease with tau_req
    p1_dry_margins_m = [
        next(b.margin_min_m for b in ev.branch_results if b.branch_id == "P1" and b.mu == 1.0)
        for ev in schedule
    ]
    p1_dry_margins_s = [
        next(b.margin_min_s for b in ev.branch_results if b.branch_id == "P1" and b.mu == 1.0)
        for ev in schedule
    ]
    for i in range(len(p1_dry_margins_m) - 1):
        assert p1_dry_margins_m[i] > p1_dry_margins_m[i + 1]
        assert p1_dry_margins_s[i] > p1_dry_margins_s[i + 1]


# =============================================================================
# 6. R3B adapter compatibility tests
# =============================================================================


def test_r3b_adapter_exact_mathematical_compatibility() -> None:
    from extensions.vla_handover_feasibility.r3b_adapter import (
        DEFAULT_MU_VALUES,
        DEFAULT_POLICY_BRANCHES,
        POLICY_BRANCH_MAP,
    )

    # Test at exact R3B speed grid point v = 60 km/h (16.6667 m/s)
    v_req = 60.0 / 3.6
    d_rem = 45.0
    t_avail = d_rem / v_req
    branch_results = evaluate_r3b_branches_at_state(v_req_mps=v_req, d_rem_m=d_rem)
    assert len(branch_results) == len(DEFAULT_POLICY_BRANCHES) * len(DEFAULT_MU_VALUES)

    iv_60 = intervals_for(60)
    for br in branch_results:
        r3b_key = POLICY_BRANCH_MAP[br.branch_id]
        ref = bound(v_req, br.mu, r3b_key, iv_60)
        assert math.isclose(br.t_req_min_s, float(ref["t_req_min"]), abs_tol=1e-3)
        assert math.isclose(br.t_req_max_s, float(ref["t_req_max"]), abs_tol=1e-3)
        assert math.isclose(br.d_stop_min_m, float(ref["t_req_min"]) * v_req, abs_tol=1e-3)
        assert math.isclose(br.d_stop_max_m, float(ref["t_req_max"]) * v_req, abs_tol=1e-3)
        assert math.isclose(br.t_avail_s, t_avail, abs_tol=1e-3)
        assert math.isclose(br.margin_max_s, t_avail - float(ref["t_req_min"]), abs_tol=1e-3)
        assert math.isclose(br.margin_min_s, t_avail - float(ref["t_req_max"]), abs_tol=1e-3)


# =============================================================================
# 7. Boundary and interval handling tests
# =============================================================================


def test_boundary_and_interval_classifications() -> None:
    # At v=10 m/s, P1 (mu=1.0) has d_stop_min ~ 20.5 m and d_stop_max ~ 43.1 m.
    # Therefore d_rem = 30.0 m lies strictly inside [d_stop_min, d_stop_max] -> PARAMETER_SENSITIVE!
    res_mid = evaluate_r3b_branches_at_state(v_req_mps=10.0, d_rem_m=30.0)
    p1_dry = next(b for b in res_mid if b.branch_id == "P1" and b.mu == 1.0)
    assert p1_dry.interval_classification == "PARAMETER_SENSITIVE"
    assert p1_dry.margin_min_m < 0.0 <= p1_dry.margin_max_m
    assert p1_dry.margin_min_s < 0.0 <= p1_dry.margin_max_s
    assert p1_dry.boundary_proximity_flag is True

    res_far = evaluate_r3b_branches_at_state(v_req_mps=10.0, d_rem_m=60.0)
    p1_far = next(b for b in res_far if b.branch_id == "P1" and b.mu == 1.0)
    assert p1_far.interval_classification == "UNIFORMLY_POSITIVE"

    res_close = evaluate_r3b_branches_at_state(v_req_mps=10.0, d_rem_m=10.0)
    p1_close = next(b for b in res_close if b.branch_id == "P1" and b.mu == 1.0)
    assert p1_close.interval_classification == "UNIFORMLY_VIOLATED"


# =============================================================================
# 8. Insufficient-evidence classifications tests
# =============================================================================


def test_insufficient_evidence_classifications_in_r3b_adapter() -> None:
    wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=5.0 * i, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    kin = compute_waypoint_kinematics(wps, initial_speed_mps=10.0)

    # Case A: Open road without observed obstacle and no counterfactual d0
    ev_no_obs = evaluate_takeover_at_request_time(
        scene_id="open_road",
        inference_mode="fast",
        tau_req_s=0.0,
        initial_speed_mps=10.0,
        waypoints=wps,
        kinematics=kin,
        obstacle_source=ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE,
        initial_obstacle_distance_d0_m=None,
    )
    assert ev_no_obs.status == TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert ev_no_obs.state_source == "OBSERVED_EGO_T0_NO_CREDIBLE_OBSTACLE"
    assert any("No observed in-lane lead obstacle" in r for r in ev_no_obs.insufficient_evidence_reasons)

    # Case B: Stationary ego vehicle (v0 = 0.0 m/s)
    stat_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=0.0, y_m=0.0, heading_rad=0.0)
        for i in range(1, 11)
    ]
    stat_kin = compute_waypoint_kinematics(stat_wps, initial_speed_mps=0.0)
    ev_stat = evaluate_takeover_at_request_time(
        scene_id="stationary_ego",
        inference_mode="fast",
        tau_req_s=0.0,
        initial_speed_mps=0.0,
        waypoints=stat_wps,
        kinematics=stat_kin,
        obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
        initial_obstacle_distance_d0_m=20.0,
    )
    assert ev_stat.status == TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert any("strictly positive initial speed" in r for r in ev_stat.insufficient_evidence_reasons)

    # Case C: Lateral corridor departure (turning trajectory with |y| > 1.75 m)
    turn_wps = [
        TrajectoryWaypoint(step=i, t_s=0.5 * i, x_m=3.0 * i, y_m=0.8 * i, heading_rad=0.12 * i)
        for i in range(1, 11)
    ]
    turn_kin = compute_waypoint_kinematics(turn_wps, initial_speed_mps=6.5)
    ev_turn = evaluate_takeover_at_request_time(
        scene_id="turn_scene",
        inference_mode="fast",
        tau_req_s=2.0,
        initial_speed_mps=6.5,
        waypoints=turn_wps,
        kinematics=turn_kin,
        obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
        initial_obstacle_distance_d0_m=30.0,
        strict_longitudinal_corridor=True,
    )
    assert ev_turn.status == TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    assert ev_turn.lateral_corridor_warning is True
    assert any("departs straight-line longitudinal corridor" in r for r in ev_turn.insufficient_evidence_reasons)


# =============================================================================
# 9. Artifact provenance & strict mismatch detection tests (Priority 1 & 3)
# =============================================================================


def test_saved_vla_prediction_artifacts_provenance() -> None:
    pred_files = sorted(DEFAULT_PREDICTIONS_DIR.glob("*.json"))
    assert len(pred_files) >= 7, "Expected at least 7 genuine AutoVLA prediction artifacts"

    for pf in pred_files:
        art = load_prediction_artifact(pf)
        assert art.checkpoint_repo == "Zewei-Zhou/AutoVLA"
        assert art.checkpoint_file == "AutoVLA_PDMS_89.ckpt"
        assert art.base_vlm_architecture == "Qwen/Qwen2.5-VL-3B-Instruct"
        assert art.predicts_human_takeover_request is False
        assert art.prediction_valid is True
        assert len(art.predicted_waypoints) == 10
        assert len(art.action_codebook_indices) == 10
        assert all(0 <= idx < 2048 for idx in art.action_codebook_indices)
        assert art.inference_latency_ms > 0.0
        assert "torch_version" in art.environment_metadata
        assert "transformers_version" in art.environment_metadata


def test_strict_provenance_audit_and_mismatch_detection() -> None:
    from dataclasses import replace

    from extensions.vla_handover_feasibility.provenance_audit import (
        ProvenanceMismatchError,
        verify_evaluation_and_dashboard_consistency,
        verify_scene_and_prediction_provenance,
    )

    manifest_path = DEFAULT_DATA_DIR / "scenes_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tok = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)

    leakage_flagged = []
    for scene_meta in manifest["scenes"]:
        sid = scene_meta["scene_id"]
        pf = DEFAULT_PREDICTIONS_DIR / f"{sid}_fast.json"
        art = load_prediction_artifact(pf)
        rep = verify_scene_and_prediction_provenance(
            scene_meta=scene_meta,
            artifact=art,
            data_root=DEFAULT_DATA_DIR,
            action_tokenizer=tok,
            artifact_path=pf,
        )
        assert rep["verified"] is True
        if rep["future_displacement_command_leakage_flag"]:
            leakage_flagged.append(sid)

    # Verify that scene_02 and scene_06 are explicitly flagged for future-displacement command conditioning leakage
    assert leakage_flagged == [
        "scene_02_stationary_lead_obstacle",
        "scene_06_intersection_turn_maneuver",
    ]

    # Test 1: Pairing scene_01 manifest with scene_02 prediction must fail immediately
    s1_meta = manifest["scenes"][0]
    s2_art = load_prediction_artifact(DEFAULT_PREDICTIONS_DIR / "scene_02_stationary_lead_obstacle_fast.json")
    with pytest.raises(ProvenanceMismatchError, match="Scene ID mismatch"):
        verify_scene_and_prediction_provenance(s1_meta, s2_art, DEFAULT_DATA_DIR, tok)

    # Test 2: Mismatched frame_token must fail immediately
    s1_art = load_prediction_artifact(DEFAULT_PREDICTIONS_DIR / "scene_01_high_speed_open_road_fast.json")
    bad_token_art = replace(s1_art, frame_token="deadbeef00000000")
    with pytest.raises(ProvenanceMismatchError, match="Sample identifier mismatch on 'frame_token'"):
        verify_scene_and_prediction_provenance(s1_meta, bad_token_art, DEFAULT_DATA_DIR, tok)

    # Test 3: Mismatched initial speed must fail immediately
    bad_speed_art = replace(s1_art, ego_initial_speed_mps=14.3700)
    with pytest.raises(ProvenanceMismatchError, match="Initial speed mismatch"):
        verify_scene_and_prediction_provenance(s1_meta, bad_speed_art, DEFAULT_DATA_DIR, tok)

    # Test 4: Tampered action codebook indices must fail immediately
    bad_codebook_art = replace(s1_art, action_codebook_indices=[0] * 10)
    with pytest.raises(ProvenanceMismatchError, match="Action codebook indices .* do not match raw_generated_text"):
        verify_scene_and_prediction_provenance(s1_meta, bad_codebook_art, DEFAULT_DATA_DIR, tok)

    # Test 5: Evaluation summary and HTML dashboard consistency check
    consistency = verify_evaluation_and_dashboard_consistency(
        manifest_path=manifest_path,
        summary_path=DEFAULT_ARTIFACTS_DIR / "evaluation_summary.json",
        report_html_path=DEFAULT_ARTIFACTS_DIR / "report" / "index.html",
    )
    assert consistency["all_consistent"] is True
    assert consistency["html_records_count"] == 7

    # Test 6: Verify EXT-VLA-C06 command-leakage boundary is present in extension_claim_register.csv
    with open(DEFAULT_ARTIFACTS_DIR / "extension_claim_register.csv", "r", encoding="utf-8") as f:
        claim_ids = [r["extension_claim_id"] for r in csv.DictReader(f)]
    assert "EXT-VLA-C06" in claim_ids


def test_scene_05_active_braking_and_signed_accel_ablation_provenance() -> None:
    s5_art = load_prediction_artifact(DEFAULT_PREDICTIONS_DIR / "scene_05_active_braking_deceleration_fast.json")
    assert math.isclose(s5_art.ego_initial_speed_mps, 4.3103, abs_tol=1e-4)
    assert math.isclose(s5_art.ego_ax_mps2, -1.5525, abs_tol=1e-4)
    assert math.isclose(s5_art.ego_ay_mps2, 0.1831, abs_tol=1e-4)
    assert "the ego acceleration is 1.56 m/s^2" in s5_art.prompt_text

    res_s5, kin_s5 = verify_trajectory_feasibility(
        scene_id=s5_art.scene_id,
        mode=s5_art.inference_mode,
        waypoints=s5_art.predicted_waypoints,
        initial_speed_mps=s5_art.ego_initial_speed_mps,
        initial_accel_mps2=s5_art.ego_initial_accel_mps2,
    )
    assert math.isclose(kin_s5[0].a_lon_mps2, -0.8841, abs_tol=1e-3)
    assert math.isclose(kin_s5[1].a_lon_mps2, 0.7917, abs_tol=1e-3)
    assert math.isclose(kin_s5[2].a_lon_mps2, 1.5442, abs_tol=1e-3)
    assert math.isclose(res_s5.max_lon_accel_mps2, 1.5442, abs_tol=1e-3)

    ablation_path = DEFAULT_ARTIFACTS_DIR / "ablation_scene_05_signed_accel.json"
    assert ablation_path.exists()
    ablation_art = load_prediction_artifact(ablation_path)
    assert "the ego acceleration is -1.55 m/s^2" in ablation_art.prompt_text
    assert ablation_art.action_codebook_indices == [30, 71, 187, 12, 16, 1, 28, 0, 126, 0]

    summary = json.loads((DEFAULT_ARTIFACTS_DIR / "evaluation_summary.json").read_text(encoding="utf-8"))
    ab_sum = summary["scene_05_signed_accel_ablation"]
    assert math.isclose(ab_sum["ablation_ade_5s_m"], 2.4210, abs_tol=1e-3)
    assert math.isclose(ab_sum["ablation_fde_5s_m"], 8.7228, abs_tol=1e-3)
    assert math.isclose(ab_sum["ablation_braking_phase_ade_0_to_2s_m"], 0.1448, abs_tol=1e-3)


# =============================================================================
# 10. Deterministic evaluation and report generation tests
# =============================================================================


def test_deterministic_evaluation_and_report_generation(tmp_path: Path) -> None:
    out_dir_1 = tmp_path / "run1"
    out_dir_2 = tmp_path / "run2"
    sum1 = evaluate_all_predictions_and_counterfactuals(artifacts_dir=out_dir_1)
    sum2 = evaluate_all_predictions_and_counterfactuals(artifacts_dir=out_dir_2)
    assert sum1 == sum2

    html_1 = generate_interactive_report(
        summary_path=out_dir_1 / "evaluation_summary.json",
        claim_register_path=out_dir_1 / "extension_claim_register.csv",
        output_html_path=out_dir_1 / "report.html",
    )
    html_2 = generate_interactive_report(
        summary_path=out_dir_2 / "evaluation_summary.json",
        claim_register_path=out_dir_2 / "extension_claim_register.csv",
        output_html_path=out_dir_2 / "report.html",
    )
    assert html_1.read_text(encoding="utf-8") == html_2.read_text(encoding="utf-8")


# =============================================================================
# 11. Preservation of original research code and 42-claim ledger
# =============================================================================


def test_original_research_code_and_42_claim_ledger_preserved() -> None:
    # Verify git status shows zero modified or deleted tracked files in core research directories
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no", "--", "src", "results", "research", "thesis/figures", "docs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "", f"Core research files were modified: {proc.stdout}"

    # Verify R5A_CLAIM_LEDGER.csv still has exactly 42 frozen claims
    ledger_path = REPO_ROOT / "research" / "R5A_CLAIM_LEDGER.csv"
    assert ledger_path.exists()
    with open(ledger_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 42


def test_one_command_offline_demo_and_readme_assets() -> None:
    import re

    from extensions.vla_handover_feasibility.demo import run_offline_demo

    res = run_offline_demo(open_browser=False, quiet=True)
    assert res["status"] == "PROVENANCE_AND_CONSISTENCY_VERIFIED"
    assert res["verified_scenes_count"] == 7
    assert res["total_csv_evaluation_rows"] == 1011
    assert res["command_sensitivity_verified"] is True
    assert res["c10_robustness_verified"] is True
    assert res["opened_browser"] is False
    assert Path(res["report_html_path"]).exists()
    assert Path(res["report_html_path"]).stat().st_size > 100_000

    # Verify all relative links and embedded screenshots in root README.md and extension README.md exist
    for readme_path in (REPO_ROOT / "README.md", REPO_ROOT / "extensions" / "vla_handover_feasibility" / "README.md"):
        assert readme_path.exists()
        text = readme_path.read_text(encoding="utf-8")
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            target = match.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (readme_path.parent / target).resolve()
            assert resolved.exists(), f"Broken link or image {target!r} in {readme_path} -> {resolved}"


# =============================================================================
# 12. RQ1 Driving-Command Sensitivity & Isolation Tests
# =============================================================================


def test_rq1_command_only_intervention_isolation_and_canonical_immutability(tmp_path: Path) -> None:
    from dataclasses import replace

    from extensions.vla_handover_feasibility.command_sensitivity import (
        CANONICAL_PREDICTION_SHA256,
        DEFAULT_COMMAND_SENSITIVITY_DIR,
        SUPPORTED_AUTOVLA_COMMANDS,
        evaluate_command_sensitivity,
        verify_canonical_predictions_unchanged,
        verify_command_intervention_provenance,
    )
    from extensions.vla_handover_feasibility.provenance_audit import ProvenanceMismatchError

    # 1. Verify all 7 canonical prediction JSON files are byte-for-byte unchanged
    sha_map = verify_canonical_predictions_unchanged(DEFAULT_PREDICTIONS_DIR)
    assert len(sha_map) == 7
    assert sha_map == CANONICAL_PREDICTION_SHA256
    assert SUPPORTED_AUTOVLA_COMMANDS == ("turn left", "keep forward", "turn right")

    manifest = json.loads((DEFAULT_DATA_DIR / "scenes_manifest.json").read_text(encoding="utf-8"))
    scene_by_id = {s["scene_id"]: s for s in manifest["scenes"]}
    tok = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)

    s2_meta = scene_by_id["scene_02_stationary_lead_obstacle"]
    s2_ctrl = load_prediction_artifact(DEFAULT_PREDICTIONS_DIR / "scene_02_stationary_lead_obstacle_fast.json")
    s2_intv = load_prediction_artifact(DEFAULT_COMMAND_SENSITIVITY_DIR / "scene_02_keep_forward.json")

    prov = verify_command_intervention_provenance(
        scene_meta=s2_meta,
        control_artifact=s2_ctrl,
        intervention_artifact=s2_intv,
        expected_intervention_command="keep forward",
        action_tokenizer=tok,
    )
    assert prov["prompt_isolation_verified"] is True
    assert prov["control_command"] == "turn left"
    assert prov["intervention_command"] == "keep forward"

    # Reject unsupported AutoVLA command strings (e.g. "unknown")
    with pytest.raises(ProvenanceMismatchError, match="Unsupported AutoVLA command"):
        verify_command_intervention_provenance(
            scene_meta=s2_meta,
            control_artifact=s2_ctrl,
            intervention_artifact=s2_intv,
            expected_intervention_command="unknown",
            action_tokenizer=tok,
        )

    # Reject any non-command kinematic modification in the intervention artifact
    bad_speed_intv = replace(s2_intv, ego_initial_speed_mps=s2_intv.ego_initial_speed_mps + 0.1)
    with pytest.raises(ProvenanceMismatchError, match="Ego kinematic field ego_initial_speed_mps changed"):
        verify_command_intervention_provenance(
            scene_meta=s2_meta,
            control_artifact=s2_ctrl,
            intervention_artifact=bad_speed_intv,
            expected_intervention_command="keep forward",
            action_tokenizer=tok,
        )

    # Reject prompt text that changes anything other than the driving command substring
    bad_prompt_intv = replace(s2_intv, prompt_text=s2_intv.prompt_text + " extra text")
    with pytest.raises(ProvenanceMismatchError, match="Prompt isolation violated"):
        verify_command_intervention_provenance(
            scene_meta=s2_meta,
            control_artifact=s2_ctrl,
            intervention_artifact=bad_prompt_intv,
            expected_intervention_command="keep forward",
            action_tokenizer=tok,
        )

    # Verify full RQ1 comparative evaluation metrics and R3B corridor non-applicability
    cmd_summary = evaluate_command_sensitivity(
        output_dir=tmp_path / "cmd_sens",
        force_recompute_inference=False,
    )
    assert cmd_summary["canonical_predictions_verified_unchanged"] is True
    assert "not a valid ground-truth target" in cmd_summary["critical_interpretation_rule"]

    s2_res = cmd_summary["scenes"]["scene_02_stationary_lead_obstacle"]
    assert s2_res["control_turn_left"]["action_codebook_indices"] == [418, 728, 418, 728, 1506, 724, 841, 722, 684, 1429]
    assert s2_res["intervention_keep_forward"]["action_codebook_indices"] == [1172, 42, 598, 1506, 1806, 1074, 1257, 522, 1475, 1814]
    assert s2_res["comparative_metrics"]["tokens_changed_count"] == 10
    assert s2_res["comparative_metrics"]["first_divergent_step"] == 1
    assert math.isclose(s2_res["comparative_metrics"]["delta_final_y_m_intv_minus_ctrl"], -6.7527, abs_tol=1e-3)
    assert s2_res["r3b_impact"]["observed_schedule_control_turn_left"]["admissible_count"] == 3
    assert s2_res["r3b_impact"]["observed_schedule_intervention_keep_forward"]["admissible_count"] == 6
    assert (
        s2_res["r3b_impact"]["observed_schedule_intervention_keep_forward"]["p1_dry_mu1.0_by_tau"]["3.0s"]["status"]
        == "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE"
    )

    s6_res = cmd_summary["scenes"]["scene_06_intersection_turn_maneuver"]
    assert s6_res["control_turn_left"]["action_codebook_indices"] == [773, 1466, 1898, 115, 1898, 39, 115, 1108, 672, 646]
    assert s6_res["intervention_keep_forward"]["action_codebook_indices"] == [1205, 1937, 1898, 13, 534, 39, 39, 1188, 120, 5]
    assert s6_res["comparative_metrics"]["tokens_changed_count"] == 8
    assert s6_res["comparative_metrics"]["first_divergent_step"] == 1
    assert math.isclose(s6_res["comparative_metrics"]["delta_final_y_m_intv_minus_ctrl"], -2.5546, abs_tol=1e-3)
    assert s6_res["r3b_impact"]["observed_schedule_control_turn_left"]["admissible_count"] == 0
    assert s6_res["r3b_impact"]["observed_schedule_intervention_keep_forward"]["admissible_count"] == 0
    assert s6_res["r3b_impact"]["counterfactual_schedule_control_turn_left"]["admissible_count"] == 4
    assert s6_res["r3b_impact"]["counterfactual_schedule_intervention_keep_forward"]["admissible_count"] == 5


# =============================================================================
# 13. RQ2 Scene 05 C10 Numerical Robustness Audit Tests
# =============================================================================


def test_rq2_scene_05_c10_numerical_robustness_audit(tmp_path: Path) -> None:
    from extensions.vla_handover_feasibility.c10_robustness import (
        DIAGNOSTIC_THRESHOLDS_MPS2,
        TEMPORAL_WINDOWS,
        compute_all_derivative_estimators,
        run_c10_robustness_audit,
    )

    assert DIAGNOSTIC_THRESHOLDS_MPS2 == (2.0, 2.5, 3.0)
    assert len(TEMPORAL_WINDOWS) == 5

    s5_art = load_prediction_artifact(DEFAULT_PREDICTIONS_DIR / "scene_05_active_braking_deceleration_fast.json")
    series = compute_all_derivative_estimators(
        waypoints=s5_art.predicted_waypoints,
        initial_speed_mps=s5_art.ego_initial_speed_mps,
        initial_vx_mps=s5_art.ego_vx_mps,
    )
    assert set(series.keys()) == {
        "E1_chord_backward_diff",
        "E2_ego_x_taylor_second_diff",
        "E3_body_frame_vx_backward_diff",
        "E4_central_velocity_diff",
        "E5_three_step_moving_average",
    }

    c10_summary = run_c10_robustness_audit(output_dir=tmp_path / "c10_rob")
    assert (
        c10_summary["overall_classification"]
        == "SENSITIVE_TO_TEMPORAL_WINDOW_AND_SMOOTHED_THRESHOLD_ROBUST_FOR_WINDOWS_GE_1P5S_AT_LE_2P5MPS2"
    )
    counts = c10_summary["grid_violation_counts"]
    assert counts["canonical_unsigned_total_cells"] == 75
    assert counts["canonical_unsigned_violated_cells"] == 45
    assert counts["canonical_windows_ge_1.5s_thresholds_le_2.5_cells"] == 30
    assert counts["canonical_windows_ge_1.5s_thresholds_le_2.5_violated"] == 30
    assert counts["signed_ablation_active_motion_total_cells"] == 75
    assert counts["signed_ablation_active_motion_violated_cells"] == 0

    sanity = c10_summary["sanity_checks_d4"]
    assert sanity["heading_distortion_check"]["distorts_longitudinal_accel"] is False
    assert sanity["heading_distortion_check"]["max_diff_e1_chord_vs_e2_pure_x_steps_2_to_10_mps2"] < 0.015
    assert sanity["heading_distortion_check"]["max_diff_e1_chord_vs_e3_body_vx_all_steps_mps2"] < 0.002
    assert sanity["quantization_vs_persistent_reversal_check"]["positive_accel_step_count"] == 9
    assert sanity["quantization_vs_persistent_reversal_check"]["is_single_step_quantization_artifact"] is False


# =============================================================================
# 14. Interactive R3B Simulator, Step Physics Explorer & Coupled Handover Tests
# =============================================================================


def test_interactive_r3b_simulator_analytical_parity_and_monotonic_sensitivity() -> None:
    from extensions.vla_handover_feasibility.interactive_explorer import (
        PRESENTATION_MAPPING_SPEC,
        compute_r3b_point_phase_breakdown,
        evaluate_interactive_r3b,
        kmh_to_mps,
        mps_to_kmh,
    )
    from src.experiments.r3b_braking_bounds import SUCCESS, t_required
    from src.metrics.oracle import stopping_distance_r3b_analytical
    from src.vehicle.models import GRAVITY, effective_braking_deceleration

    # 1. Verify presentation statuses never use "SAFE"
    assert set(PRESENTATION_MAPPING_SPEC.keys()) == {
        "NECESSARY_CONDITION_SATISFIED",
        "NECESSARY_CONDITION_VIOLATED",
        "PARAMETER_SENSITIVE",
        "NOT_APPLICABLE",
        "INSUFFICIENT_EVIDENCE",
    }
    for status_key, status_meta in PRESENTATION_MAPPING_SPEC.items():
        assert status_key != "SAFE"
        assert "underlying_r3b_labels" in status_meta and "meaning" in status_meta

    # 2. Verify exact unit conversion m/s <-> km/h
    for v_mps in (0.0, 6.95, 13.58, 25.0, 35.0):
        v_kmh = mps_to_kmh(v_mps)
        assert math.isclose(v_kmh, v_mps * 3.6, rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(kmh_to_mps(v_kmh), v_mps, rel_tol=1e-12, abs_tol=1e-12)

    # 3. Verify exact analytical parity against src.metrics.oracle & src.experiments.r3b_braking_bounds
    for v0 in (1.5, 5.5, 13.58, 22.0):
        for mu in (1.0, 0.7, 0.5, 0.35):
            for t1 in (1.15, 1.65, 3.0):
                t2, t3, a_max, a_drag, a_sup = 0.10, 0.60, 8.00, 0.25, 2.00
                a_eff = effective_braking_deceleration(a_max, float(SUCCESS["u_brake"]), mu)
                assert math.isclose(a_eff, min(a_max, mu * GRAVITY), rel_tol=1e-12)

                for branch_id, r3b_key, t_auth, a_bef, a_aft in (
                    ("P0", "P0|AUTH_AT_EFFECTIVE", t1, 0.0, a_drag),
                    ("P1", "P1", 0.0, a_drag, a_drag),
                    ("P2", "P2|AUTH_AT_EFFECTIVE", t1, a_sup, a_drag),
                ):
                    bd = compute_r3b_point_phase_breakdown(
                        v0_mps=v0,
                        mu=mu,
                        branch_id=branch_id,
                        t1_s=t1,
                        t2_s=t2,
                        t3_s=t3,
                        a_max_mps2=a_max,
                        a_drag_mps2=a_drag,
                        a_sup_mps2=a_sup,
                    )
                    oracle_d_stop = stopping_distance_r3b_analytical(
                        v0=v0,
                        a_max=a_max,
                        t_effective=t1,
                        t_delay=t2,
                        t_buildup=t3,
                        t_authority=t_auth,
                        a_before_authority=a_bef,
                        a_after_authority=a_aft,
                        u_brake=float(SUCCESS["u_brake"]),
                        road_friction=mu,
                    )
                    oracle_t_req = t_required(
                        v0,
                        mu,
                        r3b_key,
                        {
                            "t1": t1,
                            "t2": t2,
                            "t3": t3,
                            "a_max": a_max,
                            "a_drag": a_drag,
                            "a_sup": a_sup,
                            "f_auth": 1.0,
                        },
                    )
                    assert math.isclose(bd["d_stop_m"], oracle_d_stop, abs_tol=1e-3)
                    assert math.isclose(bd["d_req_m"], oracle_d_stop + 2.0, abs_tol=1e-3)
                    assert math.isclose(bd["t_req_s"], oracle_t_req, abs_tol=1e-3)

    # 4. Monotonic sensitivity checks and P0 >= P1 >= P2 stopping distance ordering
    res_low_v = evaluate_interactive_r3b(v0_mps=10.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=1.5)
    res_high_v = evaluate_interactive_r3b(v0_mps=18.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=1.5)
    assert res_low_v["valid_inputs"] is True and res_high_v["valid_inputs"] is True
    for b in ("P0", "P1", "P2"):
        assert res_high_v["point_results_by_branch"][b]["d_req_m"] > (
            res_low_v["point_results_by_branch"][b]["d_req_m"]
        )
        assert res_high_v["point_results_by_branch"][b]["margin_m"] < (
            res_low_v["point_results_by_branch"][b]["margin_m"]
        )

    # P0 > P1 > P2 required stopping distance
    b_low = res_low_v["point_results_by_branch"]
    assert b_low["P0"]["d_req_m"] > b_low["P1"]["d_req_m"] > b_low["P2"]["d_req_m"]
    assert b_low["P0"]["margin_m"] < b_low["P1"]["margin_m"] < b_low["P2"]["margin_m"]

    # Lower friction (snow mu=0.35 vs dry mu=1.0) increases required stopping distance
    res_snow = evaluate_interactive_r3b(v0_mps=14.0, obstacle_distance_d0_m=45.0, mu=0.35, t1_s=1.5)
    res_dry = evaluate_interactive_r3b(v0_mps=14.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=1.5)
    assert res_snow["point_results_by_branch"]["P1"]["d_req_m"] > (
        res_dry["point_results_by_branch"]["P1"]["d_req_m"]
    )
    assert res_snow["point_results_by_branch"]["P1"]["is_friction_capped"] is True
    assert res_dry["point_results_by_branch"]["P1"]["is_friction_capped"] is False

    # Longer reaction time t1 increases pre-braking distance and total required distance
    res_fast_t1 = evaluate_interactive_r3b(v0_mps=14.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=1.15)
    res_slow_t1 = evaluate_interactive_r3b(v0_mps=14.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=2.80)
    assert res_slow_t1["point_results_by_branch"]["P1"]["d_pre_control_m"] > (
        res_fast_t1["point_results_by_branch"]["P1"]["d_pre_control_m"]
    )
    assert res_slow_t1["point_results_by_branch"]["P1"]["d_req_m"] > (
        res_fast_t1["point_results_by_branch"]["P1"]["d_req_m"]
    )

    # 5. Status transitions across NECESSARY_CONDITION_SATISFIED, PARAMETER_SENSITIVE, NECESSARY_CONDITION_VIOLATED
    sat = evaluate_interactive_r3b(v0_mps=8.0, obstacle_distance_d0_m=60.0, mu=1.0)
    assert sat["presentation_status"] == "NECESSARY_CONDITION_SATISFIED"
    assert sat["interval_presentation_status"] == "NECESSARY_CONDITION_SATISFIED"
    assert sat["interval_results_by_branch"]["P1"]["interval_classification"] == "UNIFORMLY_POSITIVE"

    sens = evaluate_interactive_r3b(v0_mps=13.58, obstacle_distance_d0_m=45.0, mu=1.0)
    assert sens["interval_presentation_status"] == "PARAMETER_SENSITIVE"
    assert sens["interval_results_by_branch"]["P1"]["interval_classification"] == "PARAMETER_SENSITIVE"

    viol = evaluate_interactive_r3b(v0_mps=25.0, obstacle_distance_d0_m=20.0, mu=0.5)
    assert viol["presentation_status"] == "NECESSARY_CONDITION_VIOLATED"
    assert viol["interval_presentation_status"] == "NECESSARY_CONDITION_VIOLATED"
    assert viol["interval_results_by_branch"]["P1"]["interval_classification"] == "UNIFORMLY_VIOLATED"

    # 6. Invalid input guardrails
    bad_neg_v = evaluate_interactive_r3b(v0_mps=-2.0, obstacle_distance_d0_m=45.0, mu=1.0)
    assert bad_neg_v["valid_inputs"] is False
    assert any("Negative vehicle speed" in e for e in bad_neg_v["validation_errors"])

    bad_mu = evaluate_interactive_r3b(v0_mps=10.0, obstacle_distance_d0_m=45.0, mu=0.0)
    assert bad_mu["valid_inputs"] is False
    assert any("friction" in e.lower() for e in bad_mu["validation_errors"])

    bad_unit_sync = evaluate_interactive_r3b(v0_mps=10.0, v0_kmh=50.0, obstacle_distance_d0_m=45.0, mu=1.0)
    assert bad_unit_sync["valid_inputs"] is False
    assert any("Inconsistent speed inputs" in e for e in bad_unit_sync["validation_errors"])


def test_trajectory_explorer_catalog_step_checks_and_coupled_r3b(tmp_path: Path) -> None:
    from extensions.vla_handover_feasibility.interactive_explorer import (
        build_trajectory_explorer_catalog,
        evaluate_interactive_r3b,
    )

    catalog = build_trajectory_explorer_catalog()
    assert catalog["total_scenes"] == 7
    assert catalog["total_conditions"] == 10
    assert len(catalog["scene_condition_map"]) == 7
    assert len(catalog["epa_coastdown_table"]) == 4

    # Verify all 10 conditions exist and have 11 steps (t=0.0s + k=1..10)
    expected_keys = {
        "scene_01_high_speed_open_road__canonical",
        "scene_02_stationary_lead_obstacle__canonical",
        "scene_02_stationary_lead_obstacle__intervention_keep_forward",
        "scene_03_close_urban_lead_following__canonical",
        "scene_04_fast_arterial_lead_vehicle__canonical",
        "scene_05_active_braking_deceleration__canonical",
        "scene_05_active_braking_deceleration__ablation_signed_accel",
        "scene_06_intersection_turn_maneuver__canonical",
        "scene_06_intersection_turn_maneuver__intervention_keep_forward",
        "scene_07_stationary_ego_baseline__canonical",
    }
    assert set(catalog["conditions"].keys()) == expected_keys

    for cond_key, cond in catalog["conditions"].items():
        steps_dry = cond["steps_dry_mu1_0"]
        assert len(steps_dry) == 11, f"{cond_key} expected 11 steps (0..10)"
        t0_step = steps_dry[0]
        assert t0_step["step"] == 0 and math.isclose(t0_step["t_s"], 0.0, abs_tol=1e-9)
        assert t0_step["is_initial_observed_t0"] is True
        assert t0_step["is_recorded_prediction_step"] is False

        # Verify C1 is TRAJECTORY_WIDE at t=0 while C2..C10 are TIME_LOCAL_STEP with NOT_DEFINED_AT_T0
        c1_t0 = next(c for c in t0_step["checks"] if c["check_id"] == "C1_TIMESTAMP_AND_HORIZON_CONTINUITY")
        assert c1_t0["evaluation_scope"] == "TRAJECTORY_WIDE"
        assert c1_t0["step_status"] == "TRAJECTORY_WIDE_PASS"
        for c in t0_step["checks"]:
            if c["check_id"] != "C1_TIMESTAMP_AND_HORIZON_CONTINUITY":
                assert c["evaluation_scope"] == "TIME_LOCAL_STEP"
                assert c["step_status"] == "NOT_DEFINED_AT_T0"

        # Verify steps k=1..10 evaluate TIME_LOCAL_STEP checks explicitly
        for s_idx in range(1, 11):
            st = steps_dry[s_idx]
            assert st["step"] == s_idx
            assert math.isclose(st["t_s"], 0.5 * s_idx, abs_tol=1e-9)
            assert st["is_initial_observed_t0"] is False
            assert st["is_recorded_prediction_step"] is True
            assert len(st["checks"]) == 10

    # Verify Scene 05 canonical C10 step-level diagnostics:
    # Step 1 (t=0.5s) has |0.1811 - (-1.5525)| = 1.7336 <= 3.00 (SATISFIED at step 1),
    # while Steps 3 and 4 (t=1.5s, 2.0s) have |1.6852 - (-1.5525)| = 3.2377 > 3.00 (VIOLATED at steps [3, 4]).
    s05_can_steps = catalog["conditions"]["scene_05_active_braking_deceleration__canonical"]["steps_dry_mu1_0"]
    s05_c10_can_s1 = next(
        c for c in s05_can_steps[1]["checks"] if c["check_id"] == "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY"
    )
    assert s05_c10_can_s1["step_status"] == "SATISFIED"
    assert s05_c10_can_s1["trajectory_wide_passed"] is False
    assert s05_c10_can_s1["trajectory_violation_steps"] == [3, 4]

    s05_c10_can_s3 = next(
        c for c in s05_can_steps[3]["checks"] if c["check_id"] == "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY"
    )
    assert s05_c10_can_s3["step_status"] == "VIOLATED"
    assert s05_c10_can_s3["step_measured_value"] > 3.00

    s05_abl_step3 = catalog["conditions"]["scene_05_active_braking_deceleration__ablation_signed_accel"][
        "steps_dry_mu1_0"
    ][3]
    s05_c10_abl_s3 = next(
        c for c in s05_abl_step3["checks"] if c["check_id"] == "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY"
    )
    assert s05_c10_abl_s3["step_status"] == "SATISFIED"
    assert s05_c10_abl_s3["trajectory_wide_passed"] is True

    # Verify coupled Trajectory-to-R3B transition on Scene 02:
    # Control ('turn left') exits 1D corridor at step 3 (t=1.5s) -> NOT_APPLICABLE
    # Intervention ('keep forward') stays in 1D corridor at step 3 (t=1.5s) -> NECESSARY_CONDITION_SATISFIED
    s02_ctrl_step3 = catalog["conditions"]["scene_02_stationary_lead_obstacle__canonical"]["steps_dry_mu1_0"][3]
    assert s02_ctrl_step3["within_longitudinal_corridor"] is False
    s02_ctrl_r3b = evaluate_interactive_r3b(
        v0_mps=s02_ctrl_step3["implied_speed_mps"],
        obstacle_distance_d0_m=55.49,
        mu=1.0,
        tau_req_s=1.5,
        ego_x_at_req_m=s02_ctrl_step3["x_m"],
        ego_y_at_req_m=s02_ctrl_step3["y_m"],
        ego_heading_at_req_rad=s02_ctrl_step3["heading_rad"],
        obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
    )
    assert s02_ctrl_r3b["presentation_status"] == "NOT_APPLICABLE"

    s02_intv_step3 = catalog["conditions"][
        "scene_02_stationary_lead_obstacle__intervention_keep_forward"
    ]["steps_dry_mu1_0"][3]
    assert s02_intv_step3["within_longitudinal_corridor"] is True
    s02_intv_r3b = evaluate_interactive_r3b(
        v0_mps=s02_intv_step3["implied_speed_mps"],
        obstacle_distance_d0_m=55.49,
        mu=1.0,
        tau_req_s=1.5,
        ego_x_at_req_m=s02_intv_step3["x_m"],
        ego_y_at_req_m=s02_intv_step3["y_m"],
        ego_heading_at_req_rad=s02_intv_step3["heading_rad"],
        obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
    )
    assert s02_intv_r3b["presentation_status"] == "NECESSARY_CONDITION_SATISFIED"
    assert s02_intv_r3b["interval_presentation_status"] == "NECESSARY_CONDITION_SATISFIED"

    # Verify open-road scene without observed in-lane obstacle returns INSUFFICIENT_EVIDENCE in observed mode
    s01_cond = catalog["conditions"]["scene_01_high_speed_open_road__canonical"]
    assert s01_cond["observed_in_lane_lead_obstacle"] is None
    s01_obs_r3b = evaluate_interactive_r3b(
        v0_mps=s01_cond["ego_initial_speed_mps"],
        obstacle_distance_d0_m=None,
        mu=1.0,
        obstacle_source=ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE,
    )
    assert s01_obs_r3b["presentation_status"] == "INSUFFICIENT_EVIDENCE"

    # Verify HTML report embeds VLA_INTERACTIVE_EXPLORER and both interactive demonstrator panels
    html_out = generate_interactive_report(output_html_path=tmp_path / "interactive_report.html")
    html_text = html_out.read_text(encoding="utf-8")
    assert "window.VLA_INTERACTIVE_EXPLORER" in html_text
    assert 'id="interactive-demonstrator-workspace"' in html_text
    assert 'id="interactive-trajectory-explorer"' in html_text
    assert 'id="interactive-r3b-simulator"' in html_text
    assert "NECESSARY_CONDITION_SATISFIED" in html_text
    assert "NOT_DEFINED_AT_T0" in html_text


# =============================================================================
# 14. Public GitHub Pages Demo, 42-Case Browser/Python R3B Parity & Video QA
# =============================================================================


def test_r3b_browser_python_42_reference_cases_and_parity_report() -> None:
    from extensions.vla_handover_feasibility.interactive_explorer import (
        evaluate_interactive_r3b,
        generate_r3b_browser_parity_reference_cases,
    )

    parity_suite = generate_r3b_browser_parity_reference_cases()
    assert parity_suite["total_cases"] == 42
    assert len(parity_suite["cases"]) == 42

    # Verify aerodynamic drag modes and road gradient domain boundaries in Python
    r_mid = evaluate_interactive_r3b(v0_mps=16.67, obstacle_distance_d0_m=45.0, mu=1.0, a_drag_mode="epa_midpoint")
    r_p95 = evaluate_interactive_r3b(v0_mps=16.67, obstacle_distance_d0_m=45.0, mu=1.0, a_drag_mode="epa_p95")
    r_cust = evaluate_interactive_r3b(
        v0_mps=16.67, obstacle_distance_d0_m=45.0, mu=1.0, a_drag_mode="custom", a_drag_custom_mps2=0.42
    )
    assert r_mid["valid_inputs"] is True and r_p95["valid_inputs"] is True and r_cust["valid_inputs"] is True
    assert r_p95["point_results_by_branch"]["P1"]["d_req_m"] < r_mid["point_results_by_branch"]["P1"]["d_req_m"]
    assert r_cust["point_results_by_branch"]["P1"]["d_req_m"] < r_p95["point_results_by_branch"]["P1"]["d_req_m"]

    # Non-zero road grade within [-25%, +25%] -> valid input, R3B NOT_APPLICABLE
    r_grade = evaluate_interactive_r3b(v0_mps=13.58, obstacle_distance_d0_m=45.0, mu=1.0, road_grade_pct=-5.0)
    assert r_grade["valid_inputs"] is True
    assert r_grade["presentation_status"] == "NOT_APPLICABLE"
    assert r_grade["raw_r3b_status"] == "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE"
    assert any("gradient" in r.lower() for r in r_grade["not_applicable_reasons"])

    # Out-of-range road grade (|grade| > 25%) -> rejected as invalid input
    r_bad_grade = evaluate_interactive_r3b(v0_mps=13.58, obstacle_distance_d0_m=45.0, mu=1.0, road_grade_pct=35.0)
    assert r_bad_grade["valid_inputs"] is False
    assert r_bad_grade["presentation_status"] == "NOT_APPLICABLE"

    # Verify headless Chrome parity report artifact
    parity_report_path = DEFAULT_ARTIFACTS_DIR / "r3b_browser_python_parity_report.json"
    assert parity_report_path.exists(), f"Missing browser parity report at {parity_report_path}"
    parity_report = json.loads(parity_report_path.read_text(encoding="utf-8"))
    assert parity_report["total_cases"] == 42
    assert parity_report["passed_count"] == 42
    assert parity_report["failed_count"] == 0
    assert parity_report["all_passed"] is True


def test_animated_trajectory_explorer_controls_video_and_pages_bundle(tmp_path: Path) -> None:
    from extensions.vla_handover_feasibility.demo import build_github_pages_site

    report_dir = DEFAULT_ARTIFACTS_DIR / "report"
    html_text = (report_dir / "index.html").read_text(encoding="utf-8")

    for required_token in (
        'id="btn-explorer-play"',
        'id="btn-explorer-pause"',
        'id="btn-explorer-restart"',
        'id="select-explorer-playback-speed"',
        'data-playback-speed="0.5"',
        'data-playback-speed="1.0"',
        'data-playback-speed="2.0"',
        'id="explorer-interp-badge"',
        'id="bev-ego-vehicle-marker"',
        'id="select-r3b-drag-mode"',
        'id="select-r3b-grade"',
        "verifyAllParityCasesInBrowser",
        "demo_walkthrough.mp4",
    ):
        assert required_token in html_text, f"Missing {required_token} in report index.html"

    # Verify authentic MP4 video and GIF preview exist and meet resolution/duration requirements
    mp4_path = report_dir / "demo_walkthrough.mp4"
    gif_path = report_dir / "demo_preview.gif"
    assert mp4_path.exists() and mp4_path.stat().st_size > 200_000
    assert gif_path.exists() and gif_path.stat().st_size > 100_000

    # Assemble GitHub Pages static bundle in tmp_path and verify contents & security hygiene
    bundle_res = build_github_pages_site(output_dir=tmp_path / "_site")
    site_dir = Path(bundle_res["site_dir"])
    assert (site_dir / ".nojekyll").exists()
    assert (site_dir / "index.html").exists()
    assert (site_dir / "demo_walkthrough.mp4").exists()
    assert (site_dir / "demo_preview.gif").exists()
    assert (site_dir / "vla_handover_feasibility_report.pdf").exists()
    assert (site_dir / "screenshots" / "07_interactive_r3b_and_trajectory_explorer.png").exists()
    assert (site_dir / "artifacts" / "r3b_browser_python_parity_report.json").exists()


def test_frozen_research_files_sha256_invariance() -> None:
    import hashlib

    repo_root = DEFAULT_ARTIFACTS_DIR.parent.parent.parent
    expected_hashes = {
        repo_root / "research" / "R5A_CLAIM_LEDGER.csv": "75e250abc14256fcee1fa1cf2f468baf0850725cce8e389ebc09e1c59c47e6de",
        DEFAULT_PREDICTIONS_DIR / "scene_01_high_speed_open_road_fast.json": "776a1f5121dd21d1cd2949f2e756a3c2efa6b6171bbec561718051bf663423ca",
        DEFAULT_PREDICTIONS_DIR / "scene_02_stationary_lead_obstacle_fast.json": "0d257927c044da1f59149ced11ae9d5fc0cf937af0a89fd99115f84fe7d182d4",
        DEFAULT_PREDICTIONS_DIR / "scene_03_close_urban_lead_following_fast.json": "5a516928de7a3c6c2732c0b4ede31d5e486919315a34fbe22ab2ce291b777aa2",
        DEFAULT_PREDICTIONS_DIR / "scene_04_fast_arterial_lead_vehicle_fast.json": "de61ef1c170292347f054f63af790c2ae2adc78c3c17d9900f7bd1ffed0bd746",
        DEFAULT_PREDICTIONS_DIR / "scene_05_active_braking_deceleration_fast.json": "b54884da70ccccfe516202595a44124c596af016b2d93d480dc81fedd2e81fe3",
        DEFAULT_PREDICTIONS_DIR / "scene_06_intersection_turn_maneuver_fast.json": "a53c5470a8902ecdfda828d65c70ae9a86ceaf620501ad03895302eabc918fd5",
        DEFAULT_PREDICTIONS_DIR / "scene_07_stationary_ego_baseline_fast.json": "88f5f4edd77fc6139d1eed8b0f4a408fca7764b32d45f15d8dc6862ed780e5a8",
        DEFAULT_ARTIFACTS_DIR / "command_sensitivity" / "scene_02_keep_forward.json": "0aa56f4d354737b67f4297f6b0039a44aa42bb2eebbd498fae3908b75da571d1",
        DEFAULT_ARTIFACTS_DIR / "command_sensitivity" / "scene_06_keep_forward.json": "3a3f0f9f80054d5cadc78f65175283b6211ae29c574b56a0936c19c1fed69790",
        DEFAULT_ARTIFACTS_DIR / "ablation_scene_05_signed_accel.json": "837ea08ea77dcd183b129d32c1c6e266f499e40748e91472611f6b119533d595",
    }
    for fpath, expected_sha in expected_hashes.items():
        actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"Frozen research file modified: {fpath} ({actual_sha} != {expected_sha})"





