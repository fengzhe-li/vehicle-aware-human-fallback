"""Independent Trajectory Physical Feasibility Verifier (Phase C).

Evaluates VLA-generated ego-frame trajectories against explicit kinematic and
vehicle-dynamics limits:
1. Timestamp and position continuity
2. Coordinate and unit consistency
3. Implied speed and non-reverse longitudinal progress
4. Longitudinal acceleration and deceleration bounds
5. Braking demands relative to assumed physical capability limits
6. Lateral acceleration, yaw rate, and Kamm friction-circle limits
7. Road-friction sensitivity across mu in {1.0, 0.7, 0.5, 0.35}

IMPORTANT SCIENTIFIC BOUNDARY:
This verifier is strictly independent of the R3B braking-only human fallback
necessary-condition model. Passing these checks (`CONSTRAINTS_SATISFIED`)
refers only to the explicitly checked trajectory conditions and does NOT
establish collision avoidance, human takeover success, overall driving safety,
or production readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from extensions.vla_handover_feasibility.action_tokenizer import wrap_angle_rad
from extensions.vla_handover_feasibility.schemas import (
    ConstraintCheckDetail,
    FeasibilityClassification,
    FrictionSensitivityCheck,
    TrajectoryFeasibilityResult,
    TrajectoryWaypoint,
    WaypointKinematics,
)


GRAVITY_MPS2: float = 9.81


@dataclass(frozen=True)
class VerifierLimits:
    """Explicitly assumed physical and kinematic limits for trajectory verification."""

    expected_steps: int = 10
    expected_dt_s: float = 0.5
    dt_tolerance_s: float = 2e-3
    max_speed_mps: float = 35.0
    max_reverse_step_m: float = 0.08
    max_lon_accel_mps2: float = 4.5
    max_braking_physical_mps2: float = 8.0
    max_braking_planning_mps2: float = 4.5
    max_abs_lat_accel_mps2: float = 5.0
    max_abs_yaw_rate_radps: float = 0.85
    max_initial_step_accel_jump_mps2: float = 2.5
    reference_mu: float = 1.0
    friction_levels: tuple[float, ...] = (1.0, 0.7, 0.5, 0.35)
    stationary_speed_eps_mps: float = 0.05
    stationary_disp_eps_m: float = 0.15


def compute_waypoint_kinematics(
    waypoints: Sequence[TrajectoryWaypoint],
    initial_speed_mps: float,
) -> list[WaypointKinematics]:
    """Compute step-by-step implied velocities, accelerations, curvature, and braking demands."""
    kinematics: list[WaypointKinematics] = []
    prev_t = 0.0
    prev_x = 0.0
    prev_y = 0.0
    prev_heading = 0.0
    prev_speed = float(initial_speed_mps)

    for wp in waypoints:
        dt = float(wp.t_s - prev_t)
        dx = float(wp.x_m - prev_x)
        dy = float(wp.y_m - prev_y)
        ds = math.hypot(dx, dy)
        dheading = float(wrap_angle_rad(wp.heading_rad - prev_heading))

        # Mean heading across the step for body-frame projection
        mean_heading = math.atan2(
            math.sin(prev_heading) + math.sin(wp.heading_rad),
            math.cos(prev_heading) + math.cos(wp.heading_rad),
        )
        dx_local = dx * math.cos(mean_heading) + dy * math.sin(mean_heading)
        dy_local = -dx * math.sin(mean_heading) + dy * math.cos(mean_heading)

        if dt > 1e-9:
            vx_local = dx_local / dt
            vy_local = dy_local / dt
            # Signed longitudinal speed along body heading (chord speed with sign of dx_local)
            sign_lon = -1.0 if dx_local < -1e-4 else 1.0
            implied_speed = sign_lon * (ds / dt)
            a_lon = (implied_speed - prev_speed) / dt
            yaw_rate = dheading / dt
            a_lat = implied_speed * yaw_rate
            a_total = math.hypot(a_lon, a_lat)
            curvature = yaw_rate / implied_speed if abs(implied_speed) > 0.1 else 0.0
            braking_demand = max(0.0, -a_lon)
        else:
            vx_local = 0.0
            vy_local = 0.0
            implied_speed = 0.0
            a_lon = 0.0
            yaw_rate = 0.0
            a_lat = 0.0
            a_total = 0.0
            curvature = 0.0
            braking_demand = 0.0

        kinematics.append(
            WaypointKinematics(
                step=wp.step,
                t_s=round(float(wp.t_s), 4),
                dt_s=round(dt, 4),
                x_m=round(float(wp.x_m), 5),
                y_m=round(float(wp.y_m), 5),
                heading_rad=round(float(wp.heading_rad), 5),
                ds_m=round(ds, 5),
                dx_m=round(dx_local, 5),
                dy_m=round(dy_local, 5),
                implied_speed_mps=round(implied_speed, 5),
                vx_local_mps=round(vx_local, 5),
                vy_local_mps=round(vy_local, 5),
                a_lon_mps2=round(a_lon, 5),
                a_lat_mps2=round(a_lat, 5),
                a_total_mps2=round(a_total, 5),
                yaw_rate_radps=round(yaw_rate, 5),
                curvature_1pm=round(curvature, 5),
                braking_demand_mps2=round(braking_demand, 5),
            )
        )

        prev_t = float(wp.t_s)
        prev_x = float(wp.x_m)
        prev_y = float(wp.y_m)
        prev_heading = float(wp.heading_rad)
        prev_speed = implied_speed

    return kinematics


def verify_trajectory_feasibility(
    scene_id: str,
    mode: str,
    waypoints: Sequence[TrajectoryWaypoint],
    initial_speed_mps: float,
    initial_accel_mps2: float = 0.0,
    limits: VerifierLimits | None = None,
    treat_stationary_as_not_applicable: bool = False,
) -> tuple[TrajectoryFeasibilityResult, list[WaypointKinematics]]:
    """Run independent physical feasibility verification on a VLA-predicted trajectory.

    Returns `(TrajectoryFeasibilityResult, list[WaypointKinematics])`.
    """
    cfg = limits or VerifierLimits()
    insufficient_reasons: list[str] = []
    violation_reasons: list[str] = []
    checks: list[ConstraintCheckDetail] = []

    # 1. Check for missing, empty, or non-finite waypoints / initial speed
    if not math.isfinite(initial_speed_mps) or initial_speed_mps < -1e-3:
        insufficient_reasons.append(f"Invalid or negative initial ego speed: {initial_speed_mps}")

    if len(waypoints) == 0:
        insufficient_reasons.append("Prediction contains zero trajectory waypoints.")
        empty_res = TrajectoryFeasibilityResult(
            scene_id=scene_id,
            mode=mode,
            classification=FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE,
            initial_speed_mps=float(initial_speed_mps) if math.isfinite(initial_speed_mps) else 0.0,
            initial_accel_mps2=float(initial_accel_mps2) if math.isfinite(initial_accel_mps2) else 0.0,
            dt_s=cfg.expected_dt_s,
            horizon_s=0.0,
            num_waypoints=0,
            max_implied_speed_mps=0.0,
            min_implied_speed_mps=0.0,
            max_lon_accel_mps2=0.0,
            min_lon_accel_mps2=0.0,
            max_braking_demand_mps2=0.0,
            max_abs_lat_accel_mps2=0.0,
            max_total_accel_mps2=0.0,
            max_abs_yaw_rate_radps=0.0,
            total_path_length_m=0.0,
            checks=[],
            friction_sensitivity=[],
            violation_reasons=[],
            insufficient_evidence_reasons=insufficient_reasons,
        )
        return empty_res, []

    non_finite_steps: list[int] = []
    for idx, wp in enumerate(waypoints, 1):
        if not (math.isfinite(wp.t_s) and math.isfinite(wp.x_m) and math.isfinite(wp.y_m) and math.isfinite(wp.heading_rad)):
            non_finite_steps.append(idx)

    if non_finite_steps:
        insufficient_reasons.append(f"Non-finite (NaN/Inf) coordinates at steps {non_finite_steps}.")

    if len(waypoints) != cfg.expected_steps:
        insufficient_reasons.append(
            f"Incomplete trajectory horizon: got {len(waypoints)} waypoints, expected {cfg.expected_steps}."
        )

    # Check timestamp continuity
    dt_violations: list[int] = []
    prev_t = 0.0
    max_dt_err = 0.0
    for idx, wp in enumerate(waypoints, 1):
        dt = float(wp.t_s - prev_t) if math.isfinite(wp.t_s) else -1.0
        err = abs(dt - cfg.expected_dt_s)
        if err > max_dt_err:
            max_dt_err = err
        if dt <= 0.0 or err > cfg.dt_tolerance_s:
            dt_violations.append(idx)
        prev_t = float(wp.t_s) if math.isfinite(wp.t_s) else prev_t

    if dt_violations:
        insufficient_reasons.append(
            f"Timestamp discontinuity or non-uniform step interval at steps {dt_violations} (expected dt={cfg.expected_dt_s}s)."
        )

    checks.append(
        ConstraintCheckDetail(
            check_id="C1_TIMESTAMP_AND_HORIZON_CONTINUITY",
            description=f"Uniform timestamp spacing dt={cfg.expected_dt_s}s across {cfg.expected_steps} steps",
            passed=(len(dt_violations) == 0 and len(waypoints) == cfg.expected_steps and len(non_finite_steps) == 0),
            applicable=True,
            observed_value=round(max_dt_err, 6),
            limit_value=cfg.dt_tolerance_s,
            units="s",
            violation_steps=dt_violations,
            notes=f"num_waypoints={len(waypoints)}",
        )
    )

    if insufficient_reasons:
        return (
            TrajectoryFeasibilityResult(
                scene_id=scene_id,
                mode=mode,
                classification=FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE,
                initial_speed_mps=round(float(initial_speed_mps), 4) if math.isfinite(initial_speed_mps) else 0.0,
                initial_accel_mps2=round(float(initial_accel_mps2), 4) if math.isfinite(initial_accel_mps2) else 0.0,
                dt_s=cfg.expected_dt_s,
                horizon_s=round(float(waypoints[-1].t_s), 4) if math.isfinite(waypoints[-1].t_s) else 0.0,
                num_waypoints=len(waypoints),
                max_implied_speed_mps=0.0,
                min_implied_speed_mps=0.0,
                max_lon_accel_mps2=0.0,
                min_lon_accel_mps2=0.0,
                max_braking_demand_mps2=0.0,
                max_abs_lat_accel_mps2=0.0,
                max_total_accel_mps2=0.0,
                max_abs_yaw_rate_radps=0.0,
                total_path_length_m=0.0,
                checks=checks,
                friction_sensitivity=[],
                violation_reasons=[],
                insufficient_evidence_reasons=insufficient_reasons,
            ),
            [],
        )

    # Compute full kinematics
    kin = compute_waypoint_kinematics(waypoints, initial_speed_mps=initial_speed_mps)
    speeds = [k.implied_speed_mps for k in kin]
    a_lons = [k.a_lon_mps2 for k in kin]
    a_lats = [abs(k.a_lat_mps2) for k in kin]
    a_totals = [k.a_total_mps2 for k in kin]
    brakings = [k.braking_demand_mps2 for k in kin]
    yaw_rates = [abs(k.yaw_rate_radps) for k in kin]
    total_path_m = sum(k.ds_m for k in kin)

    # 2. Coordinate & unit consistency check (heading in [-pi, pi], no reverse jumps)
    heading_viol = [wp.step for wp in waypoints if abs(wp.heading_rad) > math.pi + 1e-4]
    reverse_viol = [k.step for k in kin if k.dx_m < -cfg.max_reverse_step_m]
    coord_passed = (len(heading_viol) == 0) and (len(reverse_viol) == 0)
    min_dx = min(k.dx_m for k in kin)
    checks.append(
        ConstraintCheckDetail(
            check_id="C2_COORDINATE_AND_UNIT_CONSISTENCY",
            description="Ego-local frame consistency (+x forward m, +y left m, heading in [-pi, pi] rad, no reverse jumps)",
            passed=coord_passed,
            applicable=True,
            observed_value=round(min_dx, 4),
            limit_value=-cfg.max_reverse_step_m,
            units="m",
            violation_steps=sorted(set(heading_viol + reverse_viol)),
            notes="Checks min forward body step dx_m and heading bounds.",
        )
    )
    if not coord_passed:
        violation_reasons.append(
            f"Coordinate/reverse-motion violation at steps {sorted(set(heading_viol + reverse_viol))} (min dx={min_dx:.3f} m)."
        )

    # 3. Implied speed bound check
    speed_viol = [k.step for k in kin if k.implied_speed_mps < -0.1 or k.implied_speed_mps > cfg.max_speed_mps]
    max_speed = max(speeds)
    min_speed = min(speeds)
    checks.append(
        ConstraintCheckDetail(
            check_id="C3_IMPLIED_SPEED_LIMIT",
            description=f"Implied longitudinal speed within [0.0, {cfg.max_speed_mps}] m/s",
            passed=(len(speed_viol) == 0),
            applicable=True,
            observed_value=round(max_speed, 4),
            limit_value=cfg.max_speed_mps,
            units="m/s",
            violation_steps=speed_viol,
        )
    )
    if speed_viol:
        violation_reasons.append(
            f"Implied speed violation at steps {speed_viol}: max_speed={max_speed:.2f} m/s (limit {cfg.max_speed_mps:.2f} m/s)."
        )

    # 4. Longitudinal forward acceleration check
    accel_viol = [k.step for k in kin if k.a_lon_mps2 > cfg.max_lon_accel_mps2]
    max_a_lon = max(a_lons)
    min_a_lon = min(a_lons)
    checks.append(
        ConstraintCheckDetail(
            check_id="C4_LONGITUDINAL_ACCELERATION_LIMIT",
            description=f"Longitudinal forward acceleration a_lon <= {cfg.max_lon_accel_mps2} m/s^2",
            passed=(len(accel_viol) == 0),
            applicable=True,
            observed_value=round(max_a_lon, 4),
            limit_value=cfg.max_lon_accel_mps2,
            units="m/s^2",
            violation_steps=accel_viol,
        )
    )
    if accel_viol:
        violation_reasons.append(
            f"Forward acceleration limit exceeded at steps {accel_viol}: max a_lon={max_a_lon:.2f} m/s^2 > {cfg.max_lon_accel_mps2:.2f} m/s^2."
        )

    # 5. Braking demand vs planning comfort/nominal bound and physical tire/brake limit
    max_braking = max(brakings)
    plan_brake_viol = [k.step for k in kin if k.braking_demand_mps2 > cfg.max_braking_planning_mps2]
    phys_brake_viol = [k.step for k in kin if k.braking_demand_mps2 > cfg.max_braking_physical_mps2]
    checks.append(
        ConstraintCheckDetail(
            check_id="C5_BRAKING_DEMAND_PLANNING_LIMIT",
            description=f"Longitudinal braking demand <= nominal planning bound ({cfg.max_braking_planning_mps2} m/s^2)",
            passed=(len(plan_brake_viol) == 0),
            applicable=True,
            observed_value=round(max_braking, 4),
            limit_value=cfg.max_braking_planning_mps2,
            units="m/s^2",
            violation_steps=plan_brake_viol,
        )
    )
    if plan_brake_viol:
        violation_reasons.append(
            f"Longitudinal deceleration exceeds planning bound at steps {plan_brake_viol}: "
            f"max braking={max_braking:.2f} m/s^2 > {cfg.max_braking_planning_mps2:.2f} m/s^2."
        )

    checks.append(
        ConstraintCheckDetail(
            check_id="C6_BRAKING_DEMAND_PHYSICAL_LIMIT",
            description=f"Longitudinal braking demand <= physical vehicle limit ({cfg.max_braking_physical_mps2} m/s^2)",
            passed=(len(phys_brake_viol) == 0),
            applicable=True,
            observed_value=round(max_braking, 4),
            limit_value=cfg.max_braking_physical_mps2,
            units="m/s^2",
            violation_steps=phys_brake_viol,
        )
    )
    if phys_brake_viol:
        violation_reasons.append(
            f"Longitudinal deceleration exceeds physical vehicle capability at steps {phys_brake_viol}: "
            f"max braking={max_braking:.2f} m/s^2 > {cfg.max_braking_physical_mps2:.2f} m/s^2."
        )

    # 6. Lateral acceleration and yaw-rate checks
    max_lat = max(a_lats)
    lat_viol = [k.step for k in kin if abs(k.a_lat_mps2) > cfg.max_abs_lat_accel_mps2]
    checks.append(
        ConstraintCheckDetail(
            check_id="C7_LATERAL_ACCELERATION_LIMIT",
            description=f"Lateral centripetal acceleration |a_lat| <= {cfg.max_abs_lat_accel_mps2} m/s^2",
            passed=(len(lat_viol) == 0),
            applicable=True,
            observed_value=round(max_lat, 4),
            limit_value=cfg.max_abs_lat_accel_mps2,
            units="m/s^2",
            violation_steps=lat_viol,
        )
    )
    if lat_viol:
        violation_reasons.append(
            f"Lateral acceleration limit exceeded at steps {lat_viol}: max |a_lat|={max_lat:.2f} m/s^2 > {cfg.max_abs_lat_accel_mps2:.2f} m/s^2."
        )

    max_yaw_rate = max(yaw_rates)
    yaw_viol = [k.step for k in kin if abs(k.yaw_rate_radps) > cfg.max_abs_yaw_rate_radps]
    checks.append(
        ConstraintCheckDetail(
            check_id="C8_YAW_RATE_LIMIT",
            description=f"Yaw rate |dpsi/dt| <= {cfg.max_abs_yaw_rate_radps} rad/s",
            passed=(len(yaw_viol) == 0),
            applicable=True,
            observed_value=round(max_yaw_rate, 4),
            limit_value=cfg.max_abs_yaw_rate_radps,
            units="rad/s",
            violation_steps=yaw_viol,
        )
    )
    if yaw_viol:
        violation_reasons.append(
            f"Yaw rate limit exceeded at steps {yaw_viol}: max |yaw_rate|={max_yaw_rate:.2f} rad/s > {cfg.max_abs_yaw_rate_radps:.2f} rad/s."
        )

    # 7. Reference road friction circle check at reference_mu
    ref_mu_g = cfg.reference_mu * GRAVITY_MPS2
    max_total_accel = max(a_totals)
    mu_viol = [k.step for k in kin if k.a_total_mps2 > ref_mu_g]
    checks.append(
        ConstraintCheckDetail(
            check_id="C9_FRICTION_CIRCLE_LIMIT",
            description=f"Combined horizontal acceleration sqrt(a_lon^2 + a_lat^2) <= mu*g ({ref_mu_g:.2f} m/s^2 at mu={cfg.reference_mu})",
            passed=(len(mu_viol) == 0),
            applicable=True,
            observed_value=round(max_total_accel, 4),
            limit_value=round(ref_mu_g, 4),
            units="m/s^2",
            violation_steps=mu_viol,
        )
    )
    if mu_viol:
        violation_reasons.append(
            f"Friction-circle limit exceeded at mu={cfg.reference_mu} (limit {ref_mu_g:.2f} m/s^2) at steps {mu_viol}: "
            f"max a_total={max_total_accel:.2f} m/s^2."
        )

    # 8. Longitudinal acceleration consistency with observed initial longitudinal acceleration a_x(0)
    # Evaluates active-motion steps (implied_speed > 0.25 m/s or step == 1) so that a vehicle
    # decelerating to rest (v -> 0, a_lon -> 0) is not penalized once stationary.
    active_motion_kin = [k for k in kin if k.step == 1 or abs(k.implied_speed_mps) > 0.25]
    accel_jump_vals = [abs(k.a_lon_mps2 - float(initial_accel_mps2)) for k in active_motion_kin]
    max_accel_jump = max(accel_jump_vals) if accel_jump_vals else 0.0
    accel_jump_viol = [
        k.step
        for k in active_motion_kin
        if abs(k.a_lon_mps2 - float(initial_accel_mps2)) > cfg.max_initial_step_accel_jump_mps2
    ]
    step1_a_lon = kin[0].a_lon_mps2 if kin else 0.0
    checks.append(
        ConstraintCheckDetail(
            check_id="C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY",
            description=(
                f"Active-motion longitudinal acceleration deviation |a_lon(t) - a_x(0)| "
                f"<= {cfg.max_initial_step_accel_jump_mps2} m/s^2 (observed a_x(0)={initial_accel_mps2:.2f} m/s^2)"
            ),
            passed=(len(accel_jump_viol) == 0),
            applicable=True,
            observed_value=round(max_accel_jump, 4),
            limit_value=cfg.max_initial_step_accel_jump_mps2,
            units="m/s^2",
            violation_steps=accel_jump_viol,
            notes=(
                f"step_1 a_lon={step1_a_lon:+.4f} m/s^2, peak a_lon={max_a_lon:+.4f} m/s^2; "
                "detects active-braking to positive-acceleration reversals."
            ),
        )
    )
    if accel_jump_viol:
        violation_reasons.append(
            f"Longitudinal acceleration state-consistency violation at steps {accel_jump_viol}: "
            f"max |a_lon(t) - a_x(0)|={max_accel_jump:.2f} m/s^2 > {cfg.max_initial_step_accel_jump_mps2:.2f} m/s^2 "
            f"(observed a_x(0)={initial_accel_mps2:.2f} m/s^2, step 1 a_lon={step1_a_lon:+.2f} m/s^2, "
            f"peak a_lon={max_a_lon:+.2f} m/s^2)."
        )


    # Compute road-friction sensitivity across configured friction levels
    friction_sens: list[FrictionSensitivityCheck] = []
    for mu_val in cfg.friction_levels:
        mu_g = float(mu_val * GRAVITY_MPS2)
        brake_ok = max_braking <= mu_g
        circle_ok = max_total_accel <= mu_g
        friction_sens.append(
            FrictionSensitivityCheck(
                mu=round(float(mu_val), 3),
                mu_g_limit_mps2=round(mu_g, 4),
                max_braking_demand_mps2=round(max_braking, 4),
                max_total_accel_mps2=round(max_total_accel, 4),
                braking_within_friction=brake_ok,
                total_accel_within_friction_circle=circle_ok,
                braking_margin_mps2=round(mu_g - max_braking, 4),
                friction_circle_margin_mps2=round(mu_g - max_total_accel, 4),
            )
        )

    if (
        treat_stationary_as_not_applicable
        and initial_speed_mps < cfg.stationary_speed_eps_mps
    ):
        insufficient_reasons.append(
            f"Observed ego vehicle at t0 is stationary (v0={initial_speed_mps:.4f} m/s < {cfg.stationary_speed_eps_mps} m/s, "
            f"predicted creep path={total_path_m:.2f} m); braking-only handover feasibility from initial motion is not applicable."
        )
        classification = FeasibilityClassification.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE
    elif violation_reasons:
        classification = FeasibilityClassification.CONSTRAINTS_VIOLATED
    else:
        classification = FeasibilityClassification.CONSTRAINTS_SATISFIED

    result = TrajectoryFeasibilityResult(
        scene_id=scene_id,
        mode=mode,
        classification=classification,
        initial_speed_mps=round(float(initial_speed_mps), 4),
        initial_accel_mps2=round(float(initial_accel_mps2), 4),
        dt_s=cfg.expected_dt_s,
        horizon_s=round(float(waypoints[-1].t_s), 4),
        num_waypoints=len(waypoints),
        max_implied_speed_mps=round(max_speed, 4),
        min_implied_speed_mps=round(min_speed, 4),
        max_lon_accel_mps2=round(max_a_lon, 4),
        min_lon_accel_mps2=round(min_a_lon, 4),
        max_braking_demand_mps2=round(max_braking, 4),
        max_abs_lat_accel_mps2=round(max_lat, 4),
        max_total_accel_mps2=round(max_total_accel, 4),
        max_abs_yaw_rate_radps=round(max_yaw_rate, 4),
        total_path_length_m=round(total_path_m, 4),
        checks=checks,
        friction_sensitivity=friction_sens,
        violation_reasons=violation_reasons,
        insufficient_evidence_reasons=insufficient_reasons,
    )
    return result, kin
