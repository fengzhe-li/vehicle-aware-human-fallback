"""Adapter connecting compatible VLA trajectory observations to the existing R3B braking-only recoverability framework (Phase D).

Reuses the frozen R3B functions in `src.experiments.r3b_braking_bounds` (`bound`,
`classify`, `boundary_flag`, `intervals_for`, `BRANCHES`, `PARAMETERS`) without
modifying any original repository code.

SCIENTIFIC & EVIDENCE BOUNDARIES:
1. A VLA-predicted future state at `tau_req > 0` is a hypothetical planning state,
   NOT observed vehicle motion or empirical human response.
2. Obstacle distance is never inferred from camera images alone. If a scene lacks
   an observed 3D in-lane obstacle annotation and no explicit counterfactual
   obstacle assumption is specified, the adapter returns
   `INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE`.
3. R3B establishes 1D longitudinal braking-only necessary conditions against a
   stationary obstacle. When a VLA trajectory departs the straight-line lane
   corridor (`|y| > 1.75 m` or `|heading| > 0.35 rad`), the adapter flags or
   withholds 1D longitudinal R3B application.
"""

from __future__ import annotations

import csv
import itertools
import math
from typing import Sequence

from src.experiments.r3b_braking_bounds import (
    BRANCHES,
    EPA_TABLE,
    FRICTION,
    PARAMETERS,
    SUCCESS,
    boundary_flag,
    classify,
    t_required,
)

from extensions.vla_handover_feasibility.schemas import (
    ObstacleSourceType,
    R3BBranchPointResult,
    TakeoverR3BStatus,
    TakeoverRequestEvaluation,
    TrajectoryWaypoint,
    WaypointKinematics,
)


DEFAULT_TAKEOVER_REQUEST_TIMES_S: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
LATERAL_CORRIDOR_HALF_WIDTH_M: float = 1.75
MAX_LONGITUDINAL_HEADING_RAD: float = 0.35  # ~20 deg
MIN_APPLICABLE_SPEED_MPS: float = 0.05

POLICY_BRANCH_MAP: dict[str, str] = {
    "P0": "P0|AUTH_AT_EFFECTIVE",
    "P1": "P1",
    "P2": "P2|AUTH_AT_EFFECTIVE",
}
DEFAULT_POLICY_BRANCHES: tuple[str, ...] = ("P0", "P1", "P2")
DEFAULT_MU_VALUES: tuple[float, ...] = tuple(float(k) for k in FRICTION.keys())


def epa_drag_interval_for_speed_mps(v_mps: float, path: str = EPA_TABLE) -> tuple[float, float]:
    """Interpolate (or clamp to table range [60, 130] km/h) the EPA 5th-95th percentile coastdown drag interval."""
    v_kmh = float(v_mps) * 3.6
    rows: list[tuple[float, float, float]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["group"] == "all":
                rows.append((float(r["speed_kmh"]), float(r["p05_mps2"]), float(r["p95_mps2"])))
    rows.sort(key=lambda x: x[0])
    if v_kmh <= rows[0][0]:
        return rows[0][1], rows[0][2]
    if v_kmh >= rows[-1][0]:
        return rows[-1][1], rows[-1][2]
    for i in range(len(rows) - 1):
        s0, lo0, hi0 = rows[i]
        s1, lo1, hi1 = rows[i + 1]
        if s0 <= v_kmh <= s1:
            alpha = (v_kmh - s0) / (s1 - s0)
            return lo0 + alpha * (lo1 - lo0), hi0 + alpha * (hi1 - hi0)
    return rows[0][1], rows[0][2]


def parameter_intervals_for_speed_mps(v_mps: float) -> dict[str, tuple[float, float]]:
    """Build the R3B parameter interval box at speed `v_mps` using frozen `PARAMETERS` and `EPA_TABLE`."""
    out = {k: (float(p["low"]), float(p["high"])) for k, p in PARAMETERS.items() if k != "a_drag"}
    out["a_drag"] = epa_drag_interval_for_speed_mps(v_mps)
    return out


def interpolate_hypothetical_state_at_tau(
    tau_req_s: float,
    initial_speed_mps: float,
    waypoints: Sequence[TrajectoryWaypoint],
    kinematics: Sequence[WaypointKinematics],
) -> tuple[float, float, float, float] | None:
    """Return `(x_m, y_m, heading_rad, implied_speed_mps)` at `tau_req_s`, or None if out of horizon."""
    if tau_req_s < -1e-6:
        return None
    if abs(tau_req_s) <= 1e-6:
        return (0.0, 0.0, 0.0, float(initial_speed_mps))
    if not waypoints or not kinematics or len(waypoints) != len(kinematics):
        return None
    if tau_req_s > waypoints[-1].t_s + 1e-6:
        return None

    prev_t = 0.0
    prev_x = 0.0
    prev_y = 0.0
    prev_h = 0.0
    prev_v = float(initial_speed_mps)

    for wp, kin in zip(waypoints, kinematics):
        if abs(wp.t_s - tau_req_s) <= 1e-4:
            return (float(wp.x_m), float(wp.y_m), float(wp.heading_rad), float(kin.implied_speed_mps))
        if prev_t < tau_req_s < wp.t_s:
            alpha = (tau_req_s - prev_t) / (wp.t_s - prev_t)
            x_i = prev_x + alpha * (wp.x_m - prev_x)
            y_i = prev_y + alpha * (wp.y_m - prev_y)
            h_i = prev_h + alpha * (wp.heading_rad - prev_h)
            v_i = prev_v + alpha * (kin.implied_speed_mps - prev_v)
            return (float(x_i), float(y_i), float(h_i), float(v_i))
        prev_t = float(wp.t_s)
        prev_x = float(wp.x_m)
        prev_y = float(wp.y_m)
        prev_h = float(wp.heading_rad)
        prev_v = float(kin.implied_speed_mps)

    return None


def evaluate_r3b_branches_at_state(
    v_req_mps: float,
    d_rem_m: float,
    branches: Sequence[str] = DEFAULT_POLICY_BRANCHES,
    mu_values: Sequence[float] | None = None,
) -> list[R3BBranchPointResult]:
    """Evaluate R3B interval bounds across policy branches (`P0`, `P1`, `P2`) and friction levels."""
    mus = tuple(float(m) for m in mu_values) if mu_values is not None else DEFAULT_MU_VALUES
    iv = parameter_intervals_for_speed_mps(v_req_mps)
    t_avail_s = float(d_rem_m) / float(v_req_mps)
    results: list[R3BBranchPointResult] = []

    for branch_label in branches:
        r3b_branch_key = POLICY_BRANCH_MAP.get(branch_label, branch_label)
        param_names = BRANCHES[r3b_branch_key]["params"]

        for mu in mus:
            t_reqs: list[float] = []
            for combo in itertools.product(*[iv[name] for name in param_names]):
                p_point = dict(zip(param_names, combo))
                t_reqs.append(float(t_required(v_req_mps, float(mu), r3b_branch_key, p_point)))

            t_req_min = min(t_reqs)
            t_req_max = max(t_reqs)

            # Required distance including standstill margin is v0 * T_required
            d_req_min = t_req_min * v_req_mps
            d_req_max = t_req_max * v_req_mps

            margin_best_s = t_avail_s - t_req_min
            margin_worst_s = t_avail_s - t_req_max
            margin_max_m = margin_best_s * v_req_mps
            margin_min_m = margin_worst_s * v_req_mps

            raw_r3b_cls = classify(margin_worst_s, margin_best_s)
            if raw_r3b_cls == "ROBUSTLY SATISFIED":
                interval_cls = "UNIFORMLY_POSITIVE"
            elif raw_r3b_cls == "ROBUSTLY UNSATISFIED":
                interval_cls = "UNIFORMLY_VIOLATED"
            else:
                interval_cls = "PARAMETER_SENSITIVE"

            opt_cls = (
                "RECOVERABILITY_MARGIN_POSITIVE"
                if margin_best_s >= 0.0
                else "NECESSARY_CONDITION_VIOLATED"
            )
            cons_cls = (
                "RECOVERABILITY_MARGIN_POSITIVE"
                if margin_worst_s >= 0.0
                else "NECESSARY_CONDITION_VIOLATED"
            )

            b_flag = bool(
                boundary_flag(margin_worst_s, margin_best_s)
                or (interval_cls == "PARAMETER_SENSITIVE")
            )

            eff_a_lo = min(iv["a_max"][0], float(mu) * 9.81)
            eff_a_hi = min(iv["a_max"][1], float(mu) * 9.81)

            results.append(
                R3BBranchPointResult(
                    branch_id=branch_label,
                    mu=round(float(mu), 3),
                    tau_r_lo_s=round(float(iv["t1"][0]), 4),
                    tau_r_hi_s=round(float(iv["t1"][1]), 4),
                    a_max_lo_mps2=round(eff_a_lo, 4),
                    a_max_hi_mps2=round(eff_a_hi, 4),
                    t_b_lo_s=round(float(iv["t2"][0] + iv["t3"][0]), 4),
                    t_b_hi_s=round(float(iv["t2"][1] + iv["t3"][1]), 4),
                    d_stop_min_m=round(d_req_min, 4),
                    t_req_min_s=round(t_req_min, 4),
                    margin_max_m=round(margin_max_m, 4),
                    d_stop_max_m=round(d_req_max, 4),
                    t_req_max_s=round(t_req_max, 4),
                    margin_min_m=round(margin_min_m, 4),
                    optimistic_classification=opt_cls,
                    conservative_classification=cons_cls,
                    interval_classification=interval_cls,
                    boundary_proximity_flag=b_flag,
                    t_avail_s=round(t_avail_s, 4),
                    margin_max_s=round(margin_best_s, 4),
                    margin_min_s=round(margin_worst_s, 4),
                )
            )

    return results


def resolve_scenario_state_source(
    tau_req_s: float,
    obstacle_source: ObstacleSourceType,
    observed_lead_speed_mps: float | None = None,
    initial_obstacle_distance_d0_m: float | None = None,
) -> tuple[str, str]:
    """Return `(state_source, state_disclaimer)` without ever labelling a state with counterfactual obstacle input as purely observed."""
    is_t0 = abs(tau_req_s) <= 1e-6
    d0_txt = f"d0 = {initial_obstacle_distance_d0_m:.2f} m" if initial_obstacle_distance_d0_m is not None else "d0 = N/A"

    if obstacle_source == ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION:
        if is_t0:
            return (
                "OBSERVED_EGO_T0_PLUS_ASSUMED_OBSTACLE_D0",
                f"At tau_req = 0.0 s, initial ego kinematics are observed at t0, but the stationary obstacle distance ({d0_txt}) is a COUNTERFACTUAL ASSUMPTION. The complete scenario state is therefore counterfactual, not purely observed.",
            )
        return (
            "HYPOTHETICAL_VLA_STATE_PLUS_ASSUMED_OBSTACLE_D0",
            f"At tau_req = {tau_req_s:.1f} s, ego position and speed are derived from the hypothetical VLA-predicted trajectory AND the stationary obstacle distance ({d0_txt}) is a COUNTERFACTUAL ASSUMPTION.",
        )

    if obstacle_source == ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION:
        is_moving_lead = observed_lead_speed_mps is not None and abs(observed_lead_speed_mps) > 0.1
        if is_moving_lead:
            if is_t0:
                return (
                    "OBSERVED_EGO_T0_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD",
                    f"At tau_req = 0.0 s, ego kinematics and lead vehicle position ({d0_txt}, v_lead = {observed_lead_speed_mps:.2f} m/s) are observed in 3D annotations, but applying R3B treats {d0_txt} as a counterfactual stationary target.",
                )
            return (
                "HYPOTHETICAL_VLA_STATE_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD",
                f"At tau_req = {tau_req_s:.1f} s, ego state is a hypothetical VLA planning state evaluated against the static t0 projection ({d0_txt}) of an observed moving lead vehicle (v_lead = {observed_lead_speed_mps:.2f} m/s).",
            )
        if is_t0:
            return (
                "OBSERVED_EGO_T0_AND_OBSERVED_STATIONARY_OBSTACLE",
                f"At tau_req = 0.0 s, both initial ego kinematics and the stationary in-lane obstacle ({d0_txt}, v_lead = 0.00 m/s) are observed in the dataset at t0.",
            )
        return (
            "HYPOTHETICAL_VLA_STATE_WITH_OBSERVED_STATIONARY_OBSTACLE",
            f"At tau_req = {tau_req_s:.1f} s, the obstacle ({d0_txt}) is observed as stationary at t0, while ego position and speed are hypothetical VLA planning states under open-loop trajectory following until tau_req.",
        )

    if is_t0:
        return (
            "OBSERVED_EGO_T0_NO_CREDIBLE_OBSTACLE",
            "At tau_req = 0.0 s, ego kinematics are observed at t0, but no credible in-lane obstacle exists in the dataset 3D annotations and no counterfactual obstacle was assumed.",
        )
    return (
        "HYPOTHETICAL_VLA_STATE_NO_CREDIBLE_OBSTACLE",
        f"At tau_req = {tau_req_s:.1f} s, ego state is a hypothetical VLA planning state, and no credible in-lane obstacle exists in the dataset 3D annotations.",
    )


def evaluate_takeover_at_request_time(
    scene_id: str,
    inference_mode: str,
    tau_req_s: float,
    initial_speed_mps: float,
    waypoints: Sequence[TrajectoryWaypoint],
    kinematics: Sequence[WaypointKinematics],
    obstacle_source: ObstacleSourceType,
    initial_obstacle_distance_d0_m: float | None,
    observed_lead_speed_mps: float | None = None,
    strict_longitudinal_corridor: bool = True,
) -> TakeoverRequestEvaluation:
    """Evaluate braking-only human fallback margin at a specific takeover request time `tau_req_s`."""
    state_source, state_disclaimer = resolve_scenario_state_source(
        tau_req_s=tau_req_s,
        obstacle_source=obstacle_source,
        observed_lead_speed_mps=observed_lead_speed_mps,
        initial_obstacle_distance_d0_m=initial_obstacle_distance_d0_m,
    )
    insufficient_reasons: list[str] = []

    interp = interpolate_hypothetical_state_at_tau(
        tau_req_s=tau_req_s,
        initial_speed_mps=initial_speed_mps,
        waypoints=waypoints,
        kinematics=kinematics,
    )
    if interp is None:
        insufficient_reasons.append(
            f"Requested takeover time tau_req={tau_req_s:.2f}s lies outside available valid VLA trajectory horizon."
        )
        return TakeoverRequestEvaluation(
            scene_id=scene_id,
            inference_mode=inference_mode,
            tau_req_s=round(float(tau_req_s), 3),
            state_source=state_source,
            status=TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE,
            obstacle_source=obstacle_source,
            initial_obstacle_distance_d0_m=initial_obstacle_distance_d0_m,
            ego_lon_displacement_at_req_m=0.0,
            ego_lat_displacement_at_req_m=0.0,
            ego_heading_at_req_rad=0.0,
            hypothetical_speed_at_req_mps=0.0,
            remaining_obstacle_distance_m=None,
            available_ttc_stationary_s=None,
            available_ttc_closing_s=None,
            observed_lead_speed_mps=observed_lead_speed_mps,
            lateral_corridor_warning=False,
            insufficient_evidence_reasons=insufficient_reasons,
            branch_results=[],
            state_disclaimer=state_disclaimer,
        )

    x_req, y_req, heading_req, v_req = interp
    lat_warning = (abs(y_req) > LATERAL_CORRIDOR_HALF_WIDTH_M) or (abs(heading_req) > MAX_LONGITUDINAL_HEADING_RAD)

    if obstacle_source == ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE or initial_obstacle_distance_d0_m is None:
        insufficient_reasons.append(
            "No observed in-lane lead obstacle in dataset 3D annotations within +-1.75 m corridor, "
            "and no counterfactual obstacle distance was assumed; TTC cannot be inferred from camera images alone."
        )

    if v_req <= MIN_APPLICABLE_SPEED_MPS:
        insufficient_reasons.append(
            f"Hypothetical ego speed at tau_req={tau_req_s:.2f}s is {v_req:.3f} m/s (<= {MIN_APPLICABLE_SPEED_MPS} m/s); "
            "R3B braking-only stopping model requires strictly positive initial speed (v0 > 0)."
        )

    if strict_longitudinal_corridor and lat_warning:
        insufficient_reasons.append(
            f"Hypothetical VLA state at tau_req={tau_req_s:.2f}s departs straight-line longitudinal corridor "
            f"(|y|={abs(y_req):.2f} m > {LATERAL_CORRIDOR_HALF_WIDTH_M} m or |heading|={abs(heading_req):.2f} rad > {MAX_LONGITUDINAL_HEADING_RAD} rad); "
            "1D longitudinal R3B braking-only model is not applicable without combined lateral-longitudinal assumptions."
        )

    d_rem: float | None = None
    ttc_stat: float | None = None
    ttc_closing: float | None = None

    if initial_obstacle_distance_d0_m is not None:
        d_rem = float(initial_obstacle_distance_d0_m - x_req)
        if d_rem <= 0.0:
            insufficient_reasons.append(
                f"Remaining obstacle distance d(tau_req) = {d_rem:.2f} m <= 0 m at tau_req={tau_req_s:.2f}s "
                f"(ego advanced x={x_req:.2f} m past initial obstacle coordinate d0={initial_obstacle_distance_d0_m:.2f} m prior to takeover request)."
            )
        elif v_req > MIN_APPLICABLE_SPEED_MPS:
            ttc_stat = round(d_rem / v_req, 4)
            if observed_lead_speed_mps is not None and v_req > observed_lead_speed_mps + 1e-3:
                dynamic_gap = float(initial_obstacle_distance_d0_m + observed_lead_speed_mps * tau_req_s - x_req)
                if dynamic_gap > 0.0:
                    ttc_closing = round(dynamic_gap / (v_req - observed_lead_speed_mps), 4)

    if insufficient_reasons or d_rem is None or d_rem <= 0.0 or v_req <= MIN_APPLICABLE_SPEED_MPS:
        return TakeoverRequestEvaluation(
            scene_id=scene_id,
            inference_mode=inference_mode,
            tau_req_s=round(float(tau_req_s), 3),
            state_source=state_source,
            status=TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE,
            obstacle_source=obstacle_source,
            initial_obstacle_distance_d0_m=(
                round(float(initial_obstacle_distance_d0_m), 3) if initial_obstacle_distance_d0_m is not None else None
            ),
            ego_lon_displacement_at_req_m=round(x_req, 4),
            ego_lat_displacement_at_req_m=round(y_req, 4),
            ego_heading_at_req_rad=round(heading_req, 4),
            hypothetical_speed_at_req_mps=round(v_req, 4),
            remaining_obstacle_distance_m=round(d_rem, 4) if d_rem is not None else None,
            available_ttc_stationary_s=ttc_stat,
            available_ttc_closing_s=ttc_closing,
            observed_lead_speed_mps=observed_lead_speed_mps,
            lateral_corridor_warning=lat_warning,
            insufficient_evidence_reasons=insufficient_reasons,
            branch_results=[],
            state_disclaimer=state_disclaimer,
        )

    branch_results = evaluate_r3b_branches_at_state(v_req_mps=v_req, d_rem_m=d_rem)
    return TakeoverRequestEvaluation(
        scene_id=scene_id,
        inference_mode=inference_mode,
        tau_req_s=round(float(tau_req_s), 3),
        state_source=state_source,
        status=TakeoverR3BStatus.EVALUATED,
        obstacle_source=obstacle_source,
        initial_obstacle_distance_d0_m=round(float(initial_obstacle_distance_d0_m), 3),
        ego_lon_displacement_at_req_m=round(x_req, 4),
        ego_lat_displacement_at_req_m=round(y_req, 4),
        ego_heading_at_req_rad=round(heading_req, 4),
        hypothetical_speed_at_req_mps=round(v_req, 4),
        remaining_obstacle_distance_m=round(d_rem, 4),
        available_ttc_stationary_s=ttc_stat,
        available_ttc_closing_s=ttc_closing,
        observed_lead_speed_mps=observed_lead_speed_mps,
        lateral_corridor_warning=lat_warning,
        insufficient_evidence_reasons=[],
        branch_results=branch_results,
        state_disclaimer=state_disclaimer,
    )



def evaluate_takeover_timing_schedule(
    scene_id: str,
    inference_mode: str,
    initial_speed_mps: float,
    waypoints: Sequence[TrajectoryWaypoint],
    kinematics: Sequence[WaypointKinematics],
    obstacle_source: ObstacleSourceType,
    initial_obstacle_distance_d0_m: float | None,
    observed_lead_speed_mps: float | None = None,
    request_times_s: Sequence[float] = DEFAULT_TAKEOVER_REQUEST_TIMES_S,
    strict_longitudinal_corridor: bool = True,
) -> list[TakeoverRequestEvaluation]:
    """Evaluate R3B recoverability across a schedule of takeover request times `tau_req_s`."""
    return [
        evaluate_takeover_at_request_time(
            scene_id=scene_id,
            inference_mode=inference_mode,
            tau_req_s=float(tau),
            initial_speed_mps=initial_speed_mps,
            waypoints=waypoints,
            kinematics=kinematics,
            obstacle_source=obstacle_source,
            initial_obstacle_distance_d0_m=initial_obstacle_distance_d0_m,
            observed_lead_speed_mps=observed_lead_speed_mps,
            strict_longitudinal_corridor=strict_longitudinal_corridor,
        )
        for tau in request_times_s
    ]
