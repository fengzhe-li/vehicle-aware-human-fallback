"""Interactive R3B Human Fallback Simulator & AutoVLA Trajectory/Physics Explorer Engine.

Provides pure, reusable calculation functions and provenance-checked data bundles
for the two integrated interactive capabilities:
1. Interactive R3B Human Takeover Feasibility Simulator
2. Interactive AutoVLA Trajectory & Step-Aware Physics Explorer (C1-C10 + R3B Bridge)

SCIENTIFIC & ARCHITECTURAL GUARANTEES:
- Reuses the exact validated R3B equations (`stopping_distance_r3b_analytical`,
  `braking_t_required` in `src.metrics.oracle`, `t_required`, `classify`,
  `boundary_flag`, `PARAMETERS`, `BRANCHES`, `SUCCESS` in
  `src.experiments.r3b_braking_bounds`, and `effective_braking_deceleration` in
  `src.vehicle.models`). Never substitutes a textbook approximation.
- Enforces strict physical and methodological guardrails: rejects nonphysical inputs,
  withholds numerical R3B margins outside the 1D longitudinal corridor (`|y| > 1.75 m`
  or `|heading| > 0.35 rad`), at stationary speeds (`v <= 0.05 m/s`), or when no
  obstacle distance is observed/assumed.
- Never labels any necessary-condition result as "SAFE". Maps outputs through an
  explicit, documented Necessary-Condition Presentation Mapping:
    * `NECESSARY_CONDITION_SATISFIED`
    * `NECESSARY_CONDITION_VIOLATED`
    * `PARAMETER_SENSITIVE`
    * `NOT_APPLICABLE`
    * `INSUFFICIENT_EVIDENCE`
- Strictly distinguishes `TIME_LOCAL_STEP` C1-C10 checks (evaluated on discrete step
  intervals k = 1..10, t = 0.5..5.0 s, and undefined at t = 0.0 s) from
  `TRAJECTORY_WIDE` checks (horizon completeness, full-rollout peak bounds, and
  multi-step C10 windows).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Sequence

from src.experiments.r3b_braking_bounds import (
    BRANCHES,
    EPA_TABLE,
    EPSILON_S,
    FRICTION,
    PARAMETERS,
    SUCCESS,
    boundary_flag,
    classify,
    t_required,
)
from src.metrics.oracle import (
    braking_t_required,
    stopping_distance_r3b_analytical,
)
from src.vehicle.models import GRAVITY, effective_braking_deceleration

from extensions.vla_handover_feasibility.action_tokenizer import (
    AutoVLAActionTokenizer,
)
from extensions.vla_handover_feasibility.command_sensitivity import (
    DEFAULT_COMMAND_SENSITIVITY_DIR,
    recompute_ade_fde,
    verify_canonical_predictions_unchanged,
)
from extensions.vla_handover_feasibility.r3b_adapter import (
    DEFAULT_POLICY_BRANCHES,
    DEFAULT_TAKEOVER_REQUEST_TIMES_S,
    LATERAL_CORRIDOR_HALF_WIDTH_M,
    MAX_LONGITUDINAL_HEADING_RAD,
    MIN_APPLICABLE_SPEED_MPS,
    POLICY_BRANCH_MAP,
    epa_drag_interval_for_speed_mps,
    evaluate_r3b_branches_at_state,
    evaluate_takeover_at_request_time,
    interpolate_hypothetical_state_at_tau,
    parameter_intervals_for_speed_mps,
    resolve_scenario_state_source,
)
from extensions.vla_handover_feasibility.schemas import (
    ObstacleSourceType,
    TakeoverR3BStatus,
    TrajectoryWaypoint,
    VLAPredictionArtifact,
    WaypointKinematics,
)
from extensions.vla_handover_feasibility.trajectory_verifier import (
    VerifierLimits,
    compute_waypoint_kinematics,
    verify_trajectory_feasibility,
)
from extensions.vla_handover_feasibility.vla_inference import (
    DEFAULT_CODEBOOK_PATH,
    DEFAULT_DATA_DIR,
    DEFAULT_PREDICTIONS_DIR,
    load_prediction_artifact,
)


EXT_ROOT = Path(__file__).resolve().parent

# Presentation status constants (never "SAFE")
STATUS_NECESSARY_SATISFIED = "NECESSARY_CONDITION_SATISFIED"
STATUS_NECESSARY_VIOLATED = "NECESSARY_CONDITION_VIOLATED"
STATUS_PARAMETER_SENSITIVE = "PARAMETER_SENSITIVE"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

PRESENTATION_MAPPING_SPEC: dict[str, dict[str, str]] = {
    STATUS_NECESSARY_SATISFIED: {
        "underlying_r3b_labels": "ROBUSTLY SATISFIED / RECOVERABILITY_MARGIN_POSITIVE",
        "meaning": (
            "Under the selected 1D braking-only model assumptions, available stopping distance/time "
            "meets or exceeds the required stopping distance/time (including the 2.0 m standstill margin). "
            "This is a necessary condition only and does NOT guarantee real-world collision avoidance or safety."
        ),
    },
    STATUS_NECESSARY_VIOLATED: {
        "underlying_r3b_labels": "ROBUSTLY UNSATISFIED / NECESSARY_CONDITION_VIOLATED",
        "meaning": (
            "Under the selected 1D braking-only model assumptions, required stopping distance/time exceeds "
            "available obstacle distance/time (negative margin). Pure longitudinal braking cannot stop at least "
            "2.0 m before the stationary target under these parameters."
        ),
    },
    STATUS_PARAMETER_SENSITIVE: {
        "underlying_r3b_labels": "PARAMETER-SENSITIVE / PARAMETER_SENSITIVE",
        "meaning": (
            "Across the frozen R3B parameter interval box (t1 in [1.15, 3.00] s, t2 in [0.05, 0.17] s, "
            "t3 in [0.30, 1.20] s, a_max in [6.43, 9.10] m/s^2), the optimistic corner satisfies the braking-only "
            "bound while the conservative corner violates it (or lies within +-0.01 s of zero)."
        ),
    },
    STATUS_NOT_APPLICABLE: {
        "underlying_r3b_labels": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE (Out-of-Domain / Corridor Exit / Stationary)",
        "meaning": (
            "The selected state or parameter combination violates R3B domain assumptions (e.g., ego speed v <= 0.05 m/s, "
            "trajectory lateral offset |y| > 1.75 m or heading |psi| > 0.35 rad outside the 1D corridor, remaining "
            "obstacle distance d_rem <= 0 m, or nonphysical negative/out-of-range inputs). Numerical margins are withheld."
        ),
    },
    STATUS_INSUFFICIENT_EVIDENCE: {
        "underlying_r3b_labels": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE (Missing Obstacle Geometry)",
        "meaning": (
            "No observed 3D in-lane obstacle exists in the dataset annotations for this scene and no explicit "
            "counterfactual obstacle distance d0 was supplied. Obstacle distance is never inferred from camera images alone."
        ),
    },
}

POLICY_METADATA: dict[str, dict[str, Any]] = {
    "P0": {
        "r3b_branch_key": "P0|AUTH_AT_EFFECTIVE",
        "short_label": "P0: Hold Speed in t1",
        "title": "P0 (P0|AUTH_AT_EFFECTIVE) — Constant-Speed Pre-Control",
        "pre_control_formula": "a_before_authority = 0.0 m/s^2 across [0, t1)",
        "assumptions": (
            "Automation maintains constant longitudinal speed v0 (zero net deceleration) from TOR (t=0) "
            "until effective human braking onset at t = t1 (equivalent to legacy W0)."
        ),
    },
    "P1": {
        "r3b_branch_key": "P1",
        "short_label": "P1: Passive EPA Coastdown Drag in t1",
        "title": "P1 — Passive Propulsion Release (EPA Coastdown Road-Load Drag)",
        "pre_control_formula": "a_before_authority = a_after_authority = a_drag(v0) across [0, t1)",
        "assumptions": (
            "Automation ceases propulsion at TOR (t=0); the vehicle decelerates passively under EPA "
            "road-load coastdown drag a_drag(v0) (5th-95th percentile interval from r3a_epa_coastdown_deceleration.csv) "
            "until effective human braking at t = t1."
        ),
    },
    "P2": {
        "r3b_branch_key": "P2|AUTH_AT_EFFECTIVE",
        "short_label": "P2: Supported Pre-Control Decel (a_sup in [1.0, 3.0] m/s^2)",
        "title": "P2 (P2|AUTH_AT_EFFECTIVE) — Automation Supported Pre-Control Deceleration",
        "pre_control_formula": "a_before_authority = a_sup in [1.0, 3.0] m/s^2 across [0, t1)",
        "assumptions": (
            "Automation applies bounded longitudinal deceleration a_sup in [1.0, 3.0] m/s^2 (kept below the "
            "UN R157 5.0 m/s^2 emergency threshold) from TOR until effective human braking at t = t1."
        ),
    },
}

# Nominal (dry mu=1.0) and wet (mu=0.5) verifier limits matching experiment_runner.py
NOMINAL_VERIFIER_LIMITS = VerifierLimits(
    max_lon_accel_mps2=4.0,
    max_braking_planning_mps2=4.0,
    max_braking_physical_mps2=8.0,
    max_abs_lat_accel_mps2=4.5,
    max_abs_yaw_rate_radps=0.75,
    reference_mu=1.0,
)
WET_VERIFIER_LIMITS = VerifierLimits(
    max_lon_accel_mps2=3.5,
    max_braking_planning_mps2=3.5,
    max_braking_physical_mps2=4.905,
    max_abs_lat_accel_mps2=2.0,
    max_abs_yaw_rate_radps=0.65,
    reference_mu=0.5,
)


def mps_to_kmh(speed_mps: float) -> float:
    """Convert speed from m/s to km/h with finite validation."""
    if not isinstance(speed_mps, (int, float)) or isinstance(speed_mps, bool) or not math.isfinite(float(speed_mps)):
        raise ValueError(f"Speed in m/s must be a finite number, got {speed_mps!r}")
    return float(speed_mps) * 3.6


def kmh_to_mps(speed_kmh: float) -> float:
    """Convert speed from km/h to m/s with finite validation."""
    if not isinstance(speed_kmh, (int, float)) or isinstance(speed_kmh, bool) or not math.isfinite(float(speed_kmh)):
        raise ValueError(f"Speed in km/h must be a finite number, got {speed_kmh!r}")
    return float(speed_kmh) / 3.6


SUPPORTED_AERO_DRAG_MODES: dict[str, str] = {
    "epa_midpoint": "EPA 5th-95th Midpoint (Default R3B)",
    "epa_p05": "EPA 5th Percentile (Low Aero/Rolling Drag)",
    "epa_median": "EPA 50th Percentile Median (All Vehicles)",
    "epa_p95": "EPA 95th Percentile (High Aero/Rolling Drag)",
    "epa_bev_median": "EPA Battery Electric Median (Road-Load Only, No Regen)",
    "custom": "Custom Coastdown Drag a_drag [m/s^2]",
}


def load_epa_drag_table_rows(path: str | Path = EPA_TABLE) -> list[dict[str, float]]:
    """Load the frozen EPA coastdown drag table (`group == 'all'` + BEV/ICE medians) for embedding in the interactive bundle."""
    by_speed: dict[float, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            spd = float(r["speed_kmh"])
            entry = by_speed.setdefault(spd, {"speed_kmh": spd})
            grp = r["group"]
            if grp == "all":
                p05 = float(r["p05_mps2"])
                p95 = float(r["p95_mps2"])
                p50 = float(r.get("median_mps2") or r.get("p50_mps2") or 0.5 * (p05 + p95))
                entry["p05_mps2"] = p05
                entry["p25_mps2"] = float(r.get("p25_mps2", p05))
                entry["p50_mps2"] = p50
                entry["median_mps2"] = p50
                entry["p75_mps2"] = float(r.get("p75_mps2", p95))
                entry["p95_mps2"] = p95
            elif "electric" in grp.lower() and "non-electric" not in grp.lower():
                entry["bev_median_mps2"] = float(r.get("median_mps2", 0.0))
            elif grp == "non-electric":
                entry["ice_median_mps2"] = float(r.get("median_mps2", 0.0))
    rows = sorted(by_speed.values(), key=lambda x: x["speed_kmh"])
    return rows


def resolve_epa_drag_for_speed_mps(
    v_mps: float,
    a_drag_mode: str = "epa_midpoint",
    a_drag_custom_mps2: float | None = None,
    path: str | Path = EPA_TABLE,
) -> tuple[float, float, float]:
    """Return `(drag_lo_mps2, drag_hi_mps2, selected_point_drag_mps2)` at speed `v_mps`."""
    rows = load_epa_drag_table_rows(path)
    v_kmh = max(rows[0]["speed_kmh"], min(rows[-1]["speed_kmh"], float(v_mps) * 3.6))

    interp_row = dict(rows[-1])
    for i in range(len(rows) - 1):
        r0, r1 = rows[i], rows[i + 1]
        if r0["speed_kmh"] - 1e-9 <= v_kmh <= r1["speed_kmh"] + 1e-9:
            alpha = (
                (v_kmh - r0["speed_kmh"]) / (r1["speed_kmh"] - r0["speed_kmh"])
                if r1["speed_kmh"] > r0["speed_kmh"]
                else 0.0
            )
            interp_row = {
                k: r0[k] + alpha * (r1[k] - r0[k])
                for k in r0.keys()
                if k in r1
            }
            break

    drag_lo = float(interp_row["p05_mps2"])
    drag_hi = float(interp_row["p95_mps2"])
    drag_mid = 0.5 * (drag_lo + drag_hi)

    if a_drag_mode == "epa_p05":
        sel = drag_lo
    elif a_drag_mode == "epa_median":
        sel = float(interp_row.get("median_mps2", drag_mid))
    elif a_drag_mode == "epa_p95":
        sel = drag_hi
    elif a_drag_mode == "epa_bev_median":
        sel = float(interp_row.get("bev_median_mps2", drag_mid))
    elif a_drag_mode == "custom" and a_drag_custom_mps2 is not None:
        sel = float(a_drag_custom_mps2)
    else:
        sel = drag_mid

    return drag_lo, drag_hi, sel


def map_r3b_interval_to_presentation_status(raw_r3b_classification: str) -> str:
    """Map frozen R3B interval classifications to necessary-condition presentation labels."""
    if raw_r3b_classification in ("ROBUSTLY SATISFIED", "UNIFORMLY_POSITIVE"):
        return STATUS_NECESSARY_SATISFIED
    if raw_r3b_classification in ("ROBUSTLY UNSATISFIED", "UNIFORMLY_VIOLATED"):
        return STATUS_NECESSARY_VIOLATED
    if raw_r3b_classification in ("PARAMETER-SENSITIVE", "PARAMETER_SENSITIVE"):
        return STATUS_PARAMETER_SENSITIVE
    return STATUS_NOT_APPLICABLE


def map_r3b_point_margin_to_presentation_status(margin_s: float) -> str:
    """Map a point R3B time margin (seconds) to a necessary-condition presentation status."""
    if not math.isfinite(margin_s):
        return STATUS_NOT_APPLICABLE
    return STATUS_NECESSARY_SATISFIED if margin_s >= 0.0 else STATUS_NECESSARY_VIOLATED


def compute_r3b_point_phase_breakdown(
    v0_mps: float,
    mu: float,
    branch_id: str,
    t1_s: float,
    t2_s: float,
    t3_s: float,
    a_max_mps2: float,
    a_drag_mps2: float,
    a_sup_mps2: float = 2.0,
) -> dict[str, Any]:
    """Compute exact R3B point stopping distance, required time, and phase-by-phase breakdown.

    Guaranteed to match `src.metrics.oracle.stopping_distance_r3b_analytical` and
    `src.experiments.r3b_braking_bounds.t_required` to within floating-point precision (< 1e-12).
    """
    r3b_branch_key = POLICY_BRANCH_MAP.get(branch_id, branch_id)
    if r3b_branch_key not in BRANCHES:
        raise ValueError(f"Unsupported R3B policy branch: {branch_id!r}")

    p_point = {
        "t1": float(t1_s),
        "t2": float(t2_s),
        "t3": float(t3_s),
        "a_max": float(a_max_mps2),
        "a_drag": float(a_drag_mps2),
        "a_sup": float(a_sup_mps2),
        "f_auth": 1.0,
    }
    if branch_id == "P1" or r3b_branch_key == "P1":
        t_auth = 0.0
        a_before = float(a_drag_mps2)
        a_after = float(a_drag_mps2)
    elif branch_id == "P0" or r3b_branch_key == "P0|AUTH_AT_EFFECTIVE":
        t_auth = float(t1_s)
        a_before = 0.0
        a_after = float(a_drag_mps2)
    else:
        t_auth = float(t1_s)
        a_before = float(a_sup_mps2)
        a_after = float(a_drag_mps2)

    # Exact oracle call
    d_stop_oracle = stopping_distance_r3b_analytical(
        v0=float(v0_mps),
        a_max=float(a_max_mps2),
        t_effective=float(t1_s),
        t_delay=float(t2_s),
        t_buildup=float(t3_s),
        t_authority=t_auth,
        a_before_authority=a_before,
        a_after_authority=a_after,
        u_brake=float(SUCCESS["u_brake"]),
        road_friction=float(mu),
    )
    t_req_oracle = t_required(float(v0_mps), float(mu), r3b_branch_key, p_point)
    d_req_oracle = float(t_req_oracle * float(v0_mps))

    # Phase-by-phase decomposition (mirrors stopping_distance_r3b_analytical exactly)
    v_curr = float(v0_mps)
    d_pre = 0.0
    stopped_in_pre = False
    for dur, dec in ((t_auth, a_before), (float(t1_s) - t_auth, a_after)):
        if dur <= 0.0:
            continue
        if dec > 0.0 and v_curr - dec * dur <= 0.0:
            d_pre += v_curr * v_curr / (2.0 * dec)
            v_curr = 0.0
            stopped_in_pre = True
            break
        d_pre += v_curr * dur - 0.5 * dec * dur * dur
        v_curr -= dec * dur

    v_after_t1 = v_curr
    if stopped_in_pre:
        d_delay = 0.0
        d_brake = 0.0
        a_eff = effective_braking_deceleration(float(a_max_mps2), float(SUCCESS["u_brake"]), float(mu))
    else:
        d_delay = v_curr * float(t2_s)
        a_eff = effective_braking_deceleration(float(a_max_mps2), float(SUCCESS["u_brake"]), float(mu))
        if float(t3_s) > 0.0:
            dv_ramp = 0.5 * a_eff * float(t3_s)
            if v_curr <= dv_ramp:
                tau = math.sqrt(2.0 * v_curr * float(t3_s) / a_eff)
                d_brake = v_curr * tau - a_eff * (tau**3) / (6.0 * float(t3_s))
            else:
                d_brake = (
                    (v_curr * v_curr) / (2.0 * a_eff)
                    + v_curr * float(t3_s) / 2.0
                    - a_eff * (float(t3_s) ** 2) / 24.0
                )
        else:
            d_brake = (v_curr * v_curr) / (2.0 * a_eff)

    friction_cap_mps2 = float(mu) * GRAVITY
    is_friction_capped = float(a_max_mps2) > friction_cap_mps2 + 1e-6

    return {
        "branch_id": branch_id,
        "r3b_branch_key": r3b_branch_key,
        "pre_control_decel_mps2": round(a_before if t_auth > 0 else a_after, 5),
        "v_at_effective_braking_mps": round(v_after_t1, 5),
        "effective_braking_decel_mps2": round(a_eff, 5),
        "friction_cap_mu_g_mps2": round(friction_cap_mps2, 5),
        "is_friction_capped": is_friction_capped,
        "d_pre_control_m": round(d_pre, 4),
        "d_actuation_delay_m": round(d_delay, 4),
        "d_braking_phase_m": round(d_brake, 4),
        "d_stop_m": round(d_stop_oracle, 4),
        "standstill_margin_m": float(SUCCESS["standstill_margin_m"]),
        "d_req_m": round(d_req_oracle, 4),
        "t_req_s": round(t_req_oracle, 4),
    }


def evaluate_interactive_r3b(
    *,
    v0_mps: float | None = None,
    v0_kmh: float | None = None,
    obstacle_distance_d0_m: float | None = None,
    mu: float = 1.0,
    t1_s: float = 1.65,
    t2_s: float = 0.10,
    t3_s: float = 0.60,
    a_max_mps2: float = 8.00,
    a_sup_mps2: float = 2.00,
    a_drag_mode: str = "epa_midpoint",
    a_drag_custom_mps2: float | None = None,
    road_grade_pct: float = 0.0,
    selected_branch: str = "P1",
    tau_req_s: float = 0.0,
    ego_x_at_req_m: float = 0.0,
    ego_y_at_req_m: float = 0.0,
    ego_heading_at_req_rad: float = 0.0,
    obstacle_source: ObstacleSourceType | str = ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
    observed_lead_speed_mps: float | None = None,
    strict_longitudinal_corridor: bool = True,
) -> dict[str, Any]:
    """Evaluate both point-parameter and full R3B interval-box recoverability with strict guardrails.

    Accepts speed in either `v0_mps` or `v0_kmh` (if both are provided, checks consistency).
    Never fabricates a numerical margin when inputs are invalid, out of corridor, stationary,
    outside the validated level-road R3A/R3B domain, or lacking obstacle geometry.
    """
    if isinstance(obstacle_source, str):
        obstacle_source = ObstacleSourceType(obstacle_source)

    validation_errors: list[str] = []
    not_applicable_reasons: list[str] = []
    insufficient_evidence_reasons: list[str] = []

    # 1. Resolve and validate speed
    resolved_v_mps: float | None = None
    if v0_mps is not None:
        try:
            resolved_v_mps = float(v0_mps)
            if not math.isfinite(resolved_v_mps):
                validation_errors.append(f"Initial speed v0_mps must be finite, got {v0_mps!r}.")
        except (TypeError, ValueError):
            validation_errors.append(f"Invalid speed v0_mps: {v0_mps!r}.")
    if v0_kmh is not None:
        try:
            v_from_kmh = kmh_to_mps(float(v0_kmh))
            if resolved_v_mps is not None and abs(resolved_v_mps - v_from_kmh) > 1e-2:
                validation_errors.append(
                    f"Inconsistent speed inputs: v0_mps={resolved_v_mps:.3f} m/s vs v0_kmh={v0_kmh:.3f} km/h."
                )
            resolved_v_mps = v_from_kmh
        except ValueError as exc:
            validation_errors.append(str(exc))

    if resolved_v_mps is None:
        validation_errors.append("Initial speed (v0_mps or v0_kmh) is required.")
        resolved_v_mps = 0.0

    # 2. Check physical bounds on parameters
    for name, val in (
        ("mu", mu),
        ("t1_s", t1_s),
        ("t2_s", t2_s),
        ("t3_s", t3_s),
        ("a_max_mps2", a_max_mps2),
        ("a_sup_mps2", a_sup_mps2),
        ("road_grade_pct", road_grade_pct),
        ("tau_req_s", tau_req_s),
        ("ego_x_at_req_m", ego_x_at_req_m),
        ("ego_y_at_req_m", ego_y_at_req_m),
        ("ego_heading_at_req_rad", ego_heading_at_req_rad),
    ):
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(float(val)):
            validation_errors.append(f"Parameter {name} must be a finite number, got {val!r}.")

    if selected_branch not in POLICY_METADATA:
        validation_errors.append(
            f"Unsupported policy branch {selected_branch!r}; supported branches are {list(POLICY_METADATA.keys())}."
        )
    if a_drag_mode not in SUPPORTED_AERO_DRAG_MODES:
        validation_errors.append(
            f"Unsupported aerodynamic drag mode {a_drag_mode!r}; supported modes are {list(SUPPORTED_AERO_DRAG_MODES.keys())}."
        )

    if not validation_errors:
        if resolved_v_mps < 0.0:
            validation_errors.append(f"Negative vehicle speed v = {resolved_v_mps:.2f} m/s is nonphysical.")
        elif resolved_v_mps > 60.0:
            validation_errors.append(
                f"Vehicle speed v = {resolved_v_mps:.2f} m/s ({resolved_v_mps * 3.6:.1f} km/h) exceeds supported road-vehicle domain (<= 60 m/s)."
            )

        if obstacle_distance_d0_m is not None:
            if (
                not isinstance(obstacle_distance_d0_m, (int, float))
                or isinstance(obstacle_distance_d0_m, bool)
                or not math.isfinite(float(obstacle_distance_d0_m))
            ):
                validation_errors.append(f"Obstacle distance d0 must be finite, got {obstacle_distance_d0_m!r}.")
            elif float(obstacle_distance_d0_m) <= 0.0 or float(obstacle_distance_d0_m) > 500.0:
                validation_errors.append(
                    f"Initial obstacle distance d0 = {float(obstacle_distance_d0_m):.2f} m must be in (0.0, 500.0] m."
                )

        if float(mu) <= 0.0 or float(mu) > 1.2:
            validation_errors.append(
                f"Road friction coefficient mu = {float(mu):.2f} lies outside physical tire-road bounds (0.0 < mu <= 1.2)."
            )
        if float(t1_s) < 0.0 or float(t1_s) > 10.0:
            validation_errors.append(
                f"Takeover reaction delay t1 = {float(t1_s):.2f} s lies outside valid domain [0.0, 10.0] s."
            )
        if float(t2_s) < 0.0 or float(t2_s) > 2.0:
            validation_errors.append(
                f"Hydraulic actuation delay t2 = {float(t2_s):.2f} s lies outside valid domain [0.0, 2.0] s."
            )
        if float(t3_s) < 0.0 or float(t3_s) > 5.0:
            validation_errors.append(
                f"Deceleration ramp build-up t3 = {float(t3_s):.2f} s lies outside valid domain [0.0, 5.0] s."
            )
        if float(a_max_mps2) <= 0.0 or float(a_max_mps2) > 15.0:
            validation_errors.append(
                f"Maximum vehicle braking capability a_max = {float(a_max_mps2):.2f} m/s^2 must be in (0.0, 15.0] m/s^2."
            )
        if float(a_sup_mps2) < 0.0 or float(a_sup_mps2) > 5.0:
            validation_errors.append(
                f"Supported pre-control deceleration a_sup = {float(a_sup_mps2):.2f} m/s^2 must be in [0.0, 5.0] m/s^2 (UN R157 non-emergency bound)."
            )
        if a_drag_mode == "custom":
            if (
                a_drag_custom_mps2 is None
                or not isinstance(a_drag_custom_mps2, (int, float))
                or isinstance(a_drag_custom_mps2, bool)
                or not math.isfinite(float(a_drag_custom_mps2))
                or float(a_drag_custom_mps2) < 0.0
                or float(a_drag_custom_mps2) > 1.5
            ):
                validation_errors.append(
                    f"Custom aerodynamic coastdown drag a_drag_custom_mps2 = {a_drag_custom_mps2!r} must be in [0.0, 1.5] m/s^2."
                )
        if abs(float(road_grade_pct)) > 25.0:
            validation_errors.append(
                f"Road gradient grade = {float(road_grade_pct):+.1f}% exceeds physical highway grade bounds [-25.0%, +25.0%]."
            )
        if float(tau_req_s) < -1e-6 or float(tau_req_s) > 3.0 + 1e-6:
            validation_errors.append(
                f"Takeover request timing tau_req = {float(tau_req_s):.2f} s lies outside the validated R3B schedule horizon [0.0, 3.0] s."
            )

    state_source, state_disclaimer = resolve_scenario_state_source(
        tau_req_s=float(tau_req_s) if math.isfinite(float(tau_req_s)) else 0.0,
        obstacle_source=obstacle_source,
        observed_lead_speed_mps=observed_lead_speed_mps,
        initial_obstacle_distance_d0_m=(
            float(obstacle_distance_d0_m)
            if obstacle_distance_d0_m is not None and isinstance(obstacle_distance_d0_m, (int, float)) and math.isfinite(float(obstacle_distance_d0_m))
            else None
        ),
    )

    if validation_errors:
        return {
            "valid_inputs": False,
            "presentation_status": STATUS_NOT_APPLICABLE,
            "raw_r3b_status": "INVALID_PARAMETERS",
            "state_source": state_source,
            "state_disclaimer": state_disclaimer,
            "validation_errors": validation_errors,
            "not_applicable_reasons": validation_errors,
            "insufficient_evidence_reasons": [],
            "selected_branch": selected_branch,
            "point_results_by_branch": {},
            "interval_results_by_branch": {},
            "causal_explanation": "Input parameters are nonphysical or outside supported model bounds: " + " ".join(validation_errors),
        }

    # 3. Check evidence & applicability boundaries
    if obstacle_source == ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE or obstacle_distance_d0_m is None:
        insufficient_evidence_reasons.append(
            "No observed 3D in-lane obstacle exists in the dataset annotations within the +-1.75 m corridor, "
            "and no counterfactual obstacle distance d0 was assumed. Obstacle distance and TTC are never inferred from camera images alone."
        )

    if resolved_v_mps <= MIN_APPLICABLE_SPEED_MPS:
        not_applicable_reasons.append(
            f"Vehicle speed v = {resolved_v_mps:.3f} m/s ({resolved_v_mps * 3.6:.2f} km/h) is stationary or near-zero "
            f"(<= {MIN_APPLICABLE_SPEED_MPS} m/s); the 1D R3B braking-only stopping model requires v > {MIN_APPLICABLE_SPEED_MPS} m/s."
        )

    if abs(float(road_grade_pct)) > 1e-6:
        not_applicable_reasons.append(
            f"Non-zero road gradient (grade = {float(road_grade_pct):+.1f}%) is outside the validated level-road (0.0% grade) "
            "R3A/R3B analytical slice; numerical R3B margins are withheld rather than approximated."
        )

    corridor_lat_exceeded = abs(float(ego_y_at_req_m)) > LATERAL_CORRIDOR_HALF_WIDTH_M
    corridor_heading_exceeded = abs(float(ego_heading_at_req_rad)) > MAX_LONGITUDINAL_HEADING_RAD
    corridor_exited = corridor_lat_exceeded or corridor_heading_exceeded
    if strict_longitudinal_corridor and corridor_exited:
        not_applicable_reasons.append(
            f"Trajectory state at tau_req = {float(tau_req_s):.1f} s exits the validated 1D longitudinal corridor "
            f"(|y| = {abs(float(ego_y_at_req_m)):.2f} m vs. {LATERAL_CORRIDOR_HALF_WIDTH_M:.2f} m limit; "
            f"|psi| = {abs(float(ego_heading_at_req_rad)):.2f} rad [{abs(math.degrees(float(ego_heading_at_req_rad))):.1f} deg] "
            f"vs. {MAX_LONGITUDINAL_HEADING_RAD:.2f} rad limit). 1D braking-only R3B is not applicable during a lateral turn maneuver."
        )

    d_rem_m: float | None = None
    if obstacle_distance_d0_m is not None:
        d_rem_m = float(obstacle_distance_d0_m) - float(ego_x_at_req_m)
        if d_rem_m <= 0.0:
            not_applicable_reasons.append(
                f"Remaining obstacle distance d_rem(tau_req={float(tau_req_s):.1f}s) = {d_rem_m:.2f} m <= 0.0 m "
                f"(ego longitudinal progress x={float(ego_x_at_req_m):.2f} m has already reached or passed initial obstacle position d0={float(obstacle_distance_d0_m):.2f} m prior to takeover request)."
            )

    if insufficient_evidence_reasons:
        return {
            "valid_inputs": True,
            "presentation_status": STATUS_INSUFFICIENT_EVIDENCE,
            "raw_r3b_status": TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE.value,
            "state_source": state_source,
            "state_disclaimer": state_disclaimer,
            "v_req_mps": round(resolved_v_mps, 4),
            "v_req_kmh": round(mps_to_kmh(resolved_v_mps), 3),
            "d0_m": None,
            "d_rem_m": None,
            "t_avail_s": None,
            "mu": round(float(mu), 3),
            "road_grade_pct": round(float(road_grade_pct), 2),
            "a_drag_mode": a_drag_mode,
            "tau_req_s": round(float(tau_req_s), 3),
            "corridor_valid": not corridor_exited,
            "validation_errors": [],
            "not_applicable_reasons": not_applicable_reasons,
            "insufficient_evidence_reasons": insufficient_evidence_reasons,
            "selected_branch": selected_branch,
            "point_results_by_branch": {},
            "interval_results_by_branch": {},
            "causal_explanation": " ".join(insufficient_evidence_reasons),
        }

    if not_applicable_reasons or d_rem_m is None or d_rem_m <= 0.0:
        return {
            "valid_inputs": True,
            "presentation_status": STATUS_NOT_APPLICABLE,
            "raw_r3b_status": TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE.value,
            "state_source": state_source,
            "state_disclaimer": state_disclaimer,
            "v_req_mps": round(resolved_v_mps, 4),
            "v_req_kmh": round(mps_to_kmh(resolved_v_mps), 3),
            "d0_m": round(float(obstacle_distance_d0_m), 3) if obstacle_distance_d0_m is not None else None,
            "d_rem_m": round(d_rem_m, 4) if d_rem_m is not None else None,
            "t_avail_s": None,
            "mu": round(float(mu), 3),
            "road_grade_pct": round(float(road_grade_pct), 2),
            "a_drag_mode": a_drag_mode,
            "tau_req_s": round(float(tau_req_s), 3),
            "corridor_valid": not corridor_exited,
            "validation_errors": [],
            "not_applicable_reasons": not_applicable_reasons,
            "insufficient_evidence_reasons": [],
            "selected_branch": selected_branch,
            "point_results_by_branch": {},
            "interval_results_by_branch": {},
            "causal_explanation": " ".join(not_applicable_reasons),
        }

    # 4. Valid R3B evaluation: compute both exact point results and frozen interval box results
    t_avail_s = float(d_rem_m) / float(resolved_v_mps)
    drag_lo, drag_hi, selected_a_drag = resolve_epa_drag_for_speed_mps(
        resolved_v_mps,
        a_drag_mode=a_drag_mode,
        a_drag_custom_mps2=a_drag_custom_mps2,
    )
    drag_mid = 0.5 * (drag_lo + drag_hi)

    # Check if selected point parameters lie within frozen R3B sensitivity intervals
    in_r3b_box = (
        PARAMETERS["t1"]["low"] - 1e-6 <= float(t1_s) <= PARAMETERS["t1"]["high"] + 1e-6
        and PARAMETERS["t2"]["low"] - 1e-6 <= float(t2_s) <= PARAMETERS["t2"]["high"] + 1e-6
        and PARAMETERS["t3"]["low"] - 1e-6 <= float(t3_s) <= PARAMETERS["t3"]["high"] + 1e-6
        and PARAMETERS["a_max"]["low"] - 1e-6 <= float(a_max_mps2) <= PARAMETERS["a_max"]["high"] + 1e-6
        and PARAMETERS["a_sup"]["low"] - 1e-6 <= float(a_sup_mps2) <= PARAMETERS["a_sup"]["high"] + 1e-6
        and drag_lo - 1e-6 <= float(selected_a_drag) <= drag_hi + 1e-6
    )

    point_results: dict[str, dict[str, Any]] = {}
    for bid in DEFAULT_POLICY_BRANCHES:
        bd = compute_r3b_point_phase_breakdown(
            v0_mps=resolved_v_mps,
            mu=float(mu),
            branch_id=bid,
            t1_s=float(t1_s),
            t2_s=float(t2_s),
            t3_s=float(t3_s),
            a_max_mps2=float(a_max_mps2),
            a_drag_mps2=selected_a_drag,
            a_sup_mps2=float(a_sup_mps2),
        )
        margin_s = t_avail_s - float(bd["t_req_s"])
        margin_m = float(d_rem_m) - float(bd["d_req_m"])
        pres_status = map_r3b_point_margin_to_presentation_status(margin_s)
        point_results[bid] = {
            **bd,
            "t_avail_s": round(t_avail_s, 4),
            "d_avail_m": round(float(d_rem_m), 4),
            "margin_m": round(margin_m, 4),
            "margin_s": round(margin_s, 4),
            "presentation_status": pres_status,
            "policy_metadata": POLICY_METADATA[bid],
        }

    interval_objs = evaluate_r3b_branches_at_state(
        v_req_mps=resolved_v_mps,
        d_rem_m=float(d_rem_m),
        branches=DEFAULT_POLICY_BRANCHES,
        mu_values=(float(mu),),
    )
    interval_results: dict[str, dict[str, Any]] = {}
    for br_obj in interval_objs:
        d = br_obj.to_dict()
        d["presentation_status"] = map_r3b_interval_to_presentation_status(br_obj.interval_classification)
        d["policy_metadata"] = POLICY_METADATA[br_obj.branch_id]
        interval_results[br_obj.branch_id] = d

    sel_pt = point_results[selected_branch]
    sel_iv = interval_results[selected_branch]
    p0_pt = point_results["P0"]
    p2_pt = point_results["P2"]

    cap_txt = (
        f"road friction mu*g = {sel_pt['friction_cap_mu_g_mps2']:.2f} m/s^2 caps chassis a_max = {float(a_max_mps2):.2f} m/s^2"
        if sel_pt["is_friction_capped"]
        else f"chassis capability a_max = {float(a_max_mps2):.2f} m/s^2 is below the road-friction cap mu*g = {sel_pt['friction_cap_mu_g_mps2']:.2f} m/s^2"
    )
    causal_explanation = (
        f"At v = {resolved_v_mps:.2f} m/s ({mps_to_kmh(resolved_v_mps):.1f} km/h) and remaining distance d_rem = {float(d_rem_m):.2f} m "
        f"(available TTC = {t_avail_s:.2f} s), policy {selected_branch} ({POLICY_METADATA[selected_branch]['short_label']}) covers "
        f"{sel_pt['d_pre_control_m']:.2f} m during pre-control reaction t1 = {float(t1_s):.2f} s (leaving speed v1 = {sel_pt['v_at_effective_braking_mps']:.2f} m/s), "
        f"{sel_pt['d_actuation_delay_m']:.2f} m during hydraulic delay t2 = {float(t2_s):.2f} s, and {sel_pt['d_braking_phase_m']:.2f} m during ramp/steady braking "
        f"(where {cap_txt}, giving a_eff = {sel_pt['effective_braking_decel_mps2']:.2f} m/s^2). "
        f"Adding the {sel_pt['standstill_margin_m']:.1f} m standstill margin requires D_req = {sel_pt['d_req_m']:.2f} m (T_req = {sel_pt['t_req_s']:.2f} s), "
        f"yielding a point distance margin of {sel_pt['margin_m']:+.2f} m ({sel_pt['margin_s']:+.2f} s -> {sel_pt['presentation_status']}). "
        f"Across policies at these parameters, P2 saves {p0_pt['d_req_m'] - p2_pt['d_req_m']:.2f} m of stopping distance relative to P0."
    )

    return {
        "valid_inputs": True,
        "presentation_status": sel_pt["presentation_status"],
        "interval_presentation_status": sel_iv["presentation_status"],
        "raw_r3b_status": TakeoverR3BStatus.EVALUATED.value,
        "state_source": state_source,
        "state_disclaimer": state_disclaimer,
        "v_req_mps": round(resolved_v_mps, 4),
        "v_req_kmh": round(mps_to_kmh(resolved_v_mps), 3),
        "d0_m": round(float(obstacle_distance_d0_m), 3),
        "ego_x_at_req_m": round(float(ego_x_at_req_m), 4),
        "ego_y_at_req_m": round(float(ego_y_at_req_m), 4),
        "ego_heading_at_req_rad": round(float(ego_heading_at_req_rad), 4),
        "d_rem_m": round(float(d_rem_m), 4),
        "t_avail_s": round(t_avail_s, 4),
        "mu": round(float(mu), 3),
        "road_grade_pct": round(float(road_grade_pct), 2),
        "a_drag_mode": a_drag_mode,
        "selected_a_drag_mps2": round(float(selected_a_drag), 5),
        "tau_req_s": round(float(tau_req_s), 3),
        "t1_s": round(float(t1_s), 3),
        "t2_s": round(float(t2_s), 3),
        "t3_s": round(float(t3_s), 3),
        "a_max_mps2": round(float(a_max_mps2), 3),
        "a_sup_mps2": round(float(a_sup_mps2), 3),
        "epa_drag_interval_mps2": [round(drag_lo, 5), round(drag_hi, 5)],
        "epa_drag_midpoint_mps2": round(drag_mid, 5),
        "within_frozen_r3b_parameter_box": in_r3b_box,
        "corridor_valid": True,
        "validation_errors": [],
        "not_applicable_reasons": [],
        "insufficient_evidence_reasons": [],
        "selected_branch": selected_branch,
        "point_results_by_branch": point_results,
        "interval_results_by_branch": interval_results,
        "causal_explanation": causal_explanation,
    }


def compute_step_level_c1_to_c10_diagnostics(
    waypoints: Sequence[TrajectoryWaypoint],
    kinematics: Sequence[WaypointKinematics],
    initial_speed_mps: float,
    initial_accel_mps2: float,
    limits: VerifierLimits,
) -> list[dict[str, Any]]:
    """Compute step-by-step diagnostics for steps k=0..10 (t=0.0..5.0 s), explicitly distinguishing
    `TIME_LOCAL_STEP` checks from `TRAJECTORY_WIDE` checks.

    Never assigns a per-step violation to a trajectory-wide check without a genuine time-local
    measurement at that step. At t = 0.0 s (step 0), discrete interval checks C2-C10 are marked
    `NOT_DEFINED_AT_T0` because finite-difference kinematics are defined on intervals [t_{k-1}, t_k]
    for k = 1..10.
    """
    traj_res, _ = verify_trajectory_feasibility(
        scene_id="step_inspector",
        mode="step_inspector",
        waypoints=waypoints,
        initial_speed_mps=initial_speed_mps,
        initial_accel_mps2=initial_accel_mps2,
        limits=limits,
        treat_stationary_as_not_applicable=True,
    )
    traj_checks_by_id = {c.check_id: c for c in traj_res.checks}
    ref_mu_g = limits.reference_mu * GRAVITY

    steps_out: list[dict[str, Any]] = []

    # Step 0 (t = 0.0 s): Initial observed state at t0
    corridor_ok_t0 = True
    c0_checks: list[dict[str, Any]] = []
    for cid, c_traj in traj_checks_by_id.items():
        c0_checks.append(
            {
                "check_id": cid,
                "description": c_traj.description,
                "evaluation_scope": "TRAJECTORY_WIDE" if cid == "C1_TIMESTAMP_AND_HORIZON_CONTINUITY" else "TIME_LOCAL_STEP",
                "defined_at_current_step": False,
                "step_status": (
                    "TRAJECTORY_WIDE_PASS"
                    if (cid == "C1_TIMESTAMP_AND_HORIZON_CONTINUITY" and c_traj.passed)
                    else ("TRAJECTORY_WIDE_VIOLATED" if cid == "C1_TIMESTAMP_AND_HORIZON_CONTINUITY" else "NOT_DEFINED_AT_T0")
                ),
                "step_measured_value": None,
                "limit_value": c_traj.limit_value,
                "units": c_traj.units,
                "trajectory_wide_passed": c_traj.passed,
                "trajectory_wide_observed_value": c_traj.observed_value,
                "trajectory_violation_steps": list(c_traj.violation_steps),
                "step_note": (
                    "Evaluated across full 10-step horizon (t = 0.5..5.0 s)."
                    if cid == "C1_TIMESTAMP_AND_HORIZON_CONTINUITY"
                    else "Discrete step kinematics (dx, v_k, a_lon, a_lat, yaw_rate) are defined on intervals [t_{k-1}, t_k] for steps k = 1..10 (t = 0.5..5.0 s), not at t0 = 0.0 s."
                ),
            }
        )

    steps_out.append(
        {
            "step": 0,
            "t_s": 0.0,
            "is_recorded_prediction_step": False,
            "is_initial_observed_t0": True,
            "action_codebook_index": None,
            "x_m": 0.0,
            "y_m": 0.0,
            "heading_rad": 0.0,
            "heading_deg": 0.0,
            "implied_speed_mps": round(float(initial_speed_mps), 5),
            "implied_speed_kmh": round(mps_to_kmh(float(initial_speed_mps)), 4),
            "a_lon_mps2": round(float(initial_accel_mps2), 5),
            "a_lat_mps2": 0.0,
            "a_total_mps2": round(abs(float(initial_accel_mps2)), 5),
            "yaw_rate_radps": 0.0,
            "braking_demand_mps2": round(max(0.0, -float(initial_accel_mps2)), 5),
            "within_longitudinal_corridor": corridor_ok_t0,
            "r3b_time_horizon_supported": True,
            "r3b_corridor_applicable": corridor_ok_t0 and float(initial_speed_mps) > MIN_APPLICABLE_SPEED_MPS,
            "checks": c0_checks,
        }
    )

    for wp, kin in zip(waypoints, kinematics):
        k = wp.step
        dt_err = abs(float(kin.dt_s) - limits.expected_dt_s)
        c1_local_ok = kin.dt_s > 0.0 and dt_err <= limits.dt_tolerance_s
        c1_traj_ok = traj_checks_by_id["C1_TIMESTAMP_AND_HORIZON_CONTINUITY"].passed
        c2_ok = abs(wp.heading_rad) <= math.pi + 1e-4 and kin.dx_m >= -limits.max_reverse_step_m
        c3_ok = -0.1 <= kin.implied_speed_mps <= limits.max_speed_mps
        c4_ok = kin.a_lon_mps2 <= limits.max_lon_accel_mps2
        c5_ok = kin.braking_demand_mps2 <= limits.max_braking_planning_mps2
        c6_ok = kin.braking_demand_mps2 <= limits.max_braking_physical_mps2
        c7_ok = abs(kin.a_lat_mps2) <= limits.max_abs_lat_accel_mps2
        c8_ok = abs(kin.yaw_rate_radps) <= limits.max_abs_yaw_rate_radps
        c9_ok = kin.a_total_mps2 <= ref_mu_g

        active_motion = (k == 1) or (abs(kin.implied_speed_mps) > 0.25)
        c10_jump = abs(kin.a_lon_mps2 - float(initial_accel_mps2))
        c10_ok = (not active_motion) or (c10_jump <= limits.max_initial_step_accel_jump_mps2)

        step_specs = [
            (
                "C1_TIMESTAMP_AND_HORIZON_CONTINUITY",
                "TRAJECTORY_WIDE_AND_STEP_DT",
                True,
                "SATISFIED" if (c1_local_ok and c1_traj_ok) else "VIOLATED",
                round(dt_err, 6),
                limits.dt_tolerance_s,
                f"Step dt={kin.dt_s:.3f}s (|dt-0.5|={dt_err:.5f}s); full horizon={len(waypoints)}/10 steps.",
            ),
            (
                "C2_COORDINATE_AND_UNIT_CONSISTENCY",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c2_ok else "VIOLATED",
                round(kin.dx_m, 4),
                -limits.max_reverse_step_m,
                f"Body-frame forward step dx_local={kin.dx_m:+.4f} m, heading={wp.heading_rad:+.4f} rad.",
            ),
            (
                "C3_IMPLIED_SPEED_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c3_ok else "VIOLATED",
                round(kin.implied_speed_mps, 4),
                limits.max_speed_mps,
                f"Implied step speed v_{k}={kin.implied_speed_mps:.3f} m/s ({kin.implied_speed_mps * 3.6:.1f} km/h).",
            ),
            (
                "C4_LONGITUDINAL_ACCELERATION_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c4_ok else "VIOLATED",
                round(kin.a_lon_mps2, 4),
                limits.max_lon_accel_mps2,
                f"Step longitudinal acceleration a_lon,{k}={kin.a_lon_mps2:+.4f} m/s^2.",
            ),
            (
                "C5_BRAKING_DEMAND_PLANNING_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c5_ok else "VIOLATED",
                round(kin.braking_demand_mps2, 4),
                limits.max_braking_planning_mps2,
                f"Step braking demand max(0, -a_lon,{k})={kin.braking_demand_mps2:.4f} m/s^2.",
            ),
            (
                "C6_BRAKING_DEMAND_PHYSICAL_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c6_ok else "VIOLATED",
                round(kin.braking_demand_mps2, 4),
                limits.max_braking_physical_mps2,
                f"Step braking demand vs physical tire/chassis bound ({limits.max_braking_physical_mps2:.3f} m/s^2 at mu={limits.reference_mu}).",
            ),
            (
                "C7_LATERAL_ACCELERATION_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c7_ok else "VIOLATED",
                round(abs(kin.a_lat_mps2), 4),
                limits.max_abs_lat_accel_mps2,
                f"Step lateral acceleration |a_lat,{k}|={abs(kin.a_lat_mps2):.4f} m/s^2 (mu={limits.reference_mu} limit: {limits.max_abs_lat_accel_mps2:.2f} m/s^2).",
            ),
            (
                "C8_YAW_RATE_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c8_ok else "VIOLATED",
                round(abs(kin.yaw_rate_radps), 4),
                limits.max_abs_yaw_rate_radps,
                f"Step yaw rate |dpsi/dt|_{k}={abs(kin.yaw_rate_radps):.4f} rad/s.",
            ),
            (
                "C9_FRICTION_CIRCLE_LIMIT",
                "TIME_LOCAL_STEP",
                True,
                "SATISFIED" if c9_ok else "VIOLATED",
                round(kin.a_total_mps2, 4),
                round(ref_mu_g, 4),
                f"Step combined horizontal acceleration |a_tot,{k}|={kin.a_total_mps2:.4f} m/s^2 vs mu*g={ref_mu_g:.2f} m/s^2.",
            ),
            (
                "C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY",
                "TIME_LOCAL_STEP",
                active_motion,
                ("SATISFIED" if c10_ok else "VIOLATED") if active_motion else "NOT_APPLICABLE_AT_STEP",
                round(c10_jump, 4) if active_motion else None,
                limits.max_initial_step_accel_jump_mps2,
                (
                    f"|a_lon({wp.t_s:.1f}s) - a_x(0)| = |{kin.a_lon_mps2:+.4f} - ({initial_accel_mps2:+.4f})| = {c10_jump:.4f} m/s^2."
                    if active_motion
                    else f"Step {k} implied speed |v_{k}|={abs(kin.implied_speed_mps):.4f} m/s <= 0.25 m/s (vehicle at rest; active-motion C10 check not applicable at stationary tail steps)."
                ),
            ),
        ]

        step_checks: list[dict[str, Any]] = []
        for cid, scope, defined_here, st_status, val_here, lim_val, note in step_specs:
            c_traj = traj_checks_by_id[cid]
            step_checks.append(
                {
                    "check_id": cid,
                    "description": c_traj.description,
                    "evaluation_scope": scope,
                    "defined_at_current_step": defined_here,
                    "step_status": st_status,
                    "step_measured_value": val_here,
                    "limit_value": lim_val,
                    "units": c_traj.units,
                    "trajectory_wide_passed": c_traj.passed,
                    "trajectory_wide_observed_value": c_traj.observed_value,
                    "trajectory_violation_steps": list(c_traj.violation_steps),
                    "step_note": note,
                }
            )

        within_corr = (
            abs(wp.y_m) <= LATERAL_CORRIDOR_HALF_WIDTH_M
            and abs(wp.heading_rad) <= MAX_LONGITUDINAL_HEADING_RAD
        )
        time_in_r3b = wp.t_s <= 3.0 + 1e-6

        steps_out.append(
            {
                "step": k,
                "t_s": round(float(wp.t_s), 3),
                "is_recorded_prediction_step": True,
                "is_initial_observed_t0": False,
                "x_m": round(float(wp.x_m), 4),
                "y_m": round(float(wp.y_m), 4),
                "heading_rad": round(float(wp.heading_rad), 5),
                "heading_deg": round(math.degrees(float(wp.heading_rad)), 2),
                "ds_m": round(float(kin.ds_m), 4),
                "dx_local_m": round(float(kin.dx_m), 4),
                "dy_local_m": round(float(kin.dy_m), 4),
                "implied_speed_mps": round(float(kin.implied_speed_mps), 4),
                "implied_speed_kmh": round(mps_to_kmh(float(kin.implied_speed_mps)), 3),
                "a_lon_mps2": round(float(kin.a_lon_mps2), 4),
                "a_lat_mps2": round(float(kin.a_lat_mps2), 4),
                "a_total_mps2": round(float(kin.a_total_mps2), 4),
                "yaw_rate_radps": round(float(kin.yaw_rate_radps), 4),
                "braking_demand_mps2": round(float(kin.braking_demand_mps2), 4),
                "within_longitudinal_corridor": within_corr,
                "r3b_time_horizon_supported": time_in_r3b,
                "r3b_corridor_applicable": (
                    within_corr
                    and time_in_r3b
                    and float(kin.implied_speed_mps) > MIN_APPLICABLE_SPEED_MPS
                ),
                "checks": step_checks,
            }
        )

    return steps_out


def _build_condition_entry(
    *,
    condition_id: str,
    condition_label: str,
    condition_role: str,
    is_canonical: bool,
    gt_comparison_meaningful: bool,
    gt_comparison_note: str,
    scene_meta: dict[str, Any],
    artifact: VLAPredictionArtifact,
    comparison_counterpart_id: str | None = None,
) -> dict[str, Any]:
    """Build a complete, step-indexed trajectory explorer entry for a saved model rollout."""
    treat_stat = scene_meta["scene_id"] == "scene_07_stationary_ego_baseline"
    feas_dry, kin = verify_trajectory_feasibility(
        scene_id=artifact.scene_id,
        mode=condition_id,
        waypoints=artifact.predicted_waypoints,
        initial_speed_mps=artifact.ego_initial_speed_mps,
        initial_accel_mps2=artifact.ego_initial_accel_mps2,
        limits=NOMINAL_VERIFIER_LIMITS,
        treat_stationary_as_not_applicable=treat_stat,
    )
    feas_wet, _ = verify_trajectory_feasibility(
        scene_id=artifact.scene_id,
        mode=condition_id,
        waypoints=artifact.predicted_waypoints,
        initial_speed_mps=artifact.ego_initial_speed_mps,
        initial_accel_mps2=artifact.ego_initial_accel_mps2,
        limits=WET_VERIFIER_LIMITS,
        treat_stationary_as_not_applicable=treat_stat,
    )
    gt_kin = compute_waypoint_kinematics(
        artifact.ground_truth_waypoints,
        initial_speed_mps=artifact.ego_initial_speed_mps,
    )
    ade_m, fde_m = recompute_ade_fde(artifact.predicted_waypoints, artifact.ground_truth_waypoints)

    steps_dry = compute_step_level_c1_to_c10_diagnostics(
        waypoints=artifact.predicted_waypoints,
        kinematics=kin,
        initial_speed_mps=artifact.ego_initial_speed_mps,
        initial_accel_mps2=artifact.ego_initial_accel_mps2,
        limits=NOMINAL_VERIFIER_LIMITS,
    )
    steps_wet = compute_step_level_c1_to_c10_diagnostics(
        waypoints=artifact.predicted_waypoints,
        kinematics=kin,
        initial_speed_mps=artifact.ego_initial_speed_mps,
        initial_accel_mps2=artifact.ego_initial_accel_mps2,
        limits=WET_VERIFIER_LIMITS,
    )

    # Attach action token and ground-truth pose at each step k=1..10
    for idx in range(1, len(steps_dry)):
        tok_idx = artifact.action_codebook_indices[idx - 1] if idx - 1 < len(artifact.action_codebook_indices) else None
        gt_wp = artifact.ground_truth_waypoints[idx - 1] if idx - 1 < len(artifact.ground_truth_waypoints) else None
        gt_k = gt_kin[idx - 1] if idx - 1 < len(gt_kin) else None
        l2_err = (
            round(math.hypot(steps_dry[idx]["x_m"] - gt_wp.x_m, steps_dry[idx]["y_m"] - gt_wp.y_m), 4)
            if gt_wp is not None
            else None
        )
        for st_list in (steps_dry, steps_wet):
            st_list[idx]["action_codebook_index"] = tok_idx
            st_list[idx]["gt_x_m"] = round(float(gt_wp.x_m), 4) if gt_wp else None
            st_list[idx]["gt_y_m"] = round(float(gt_wp.y_m), 4) if gt_wp else None
            st_list[idx]["gt_heading_rad"] = round(float(gt_wp.heading_rad), 5) if gt_wp else None
            st_list[idx]["gt_heading_deg"] = round(math.degrees(float(gt_wp.heading_rad)), 2) if gt_wp else None
            st_list[idx]["gt_speed_mps"] = round(float(gt_k.implied_speed_mps), 4) if gt_k else None
            st_list[idx]["gt_a_lon_mps2"] = round(float(gt_k.a_lon_mps2), 4) if gt_k else None
            st_list[idx]["l2_displacement_vs_logged_gt_m"] = l2_err

    for st_list in (steps_dry, steps_wet):
        st_list[0]["gt_x_m"] = 0.0
        st_list[0]["gt_y_m"] = 0.0
        st_list[0]["gt_heading_rad"] = 0.0
        st_list[0]["gt_heading_deg"] = 0.0
        st_list[0]["gt_speed_mps"] = round(float(artifact.ego_initial_speed_mps), 4)
        st_list[0]["gt_a_lon_mps2"] = round(float(artifact.ego_initial_accel_mps2), 4)
        st_list[0]["l2_displacement_vs_logged_gt_m"] = 0.0

    obs_lead = scene_meta.get("observed_in_lane_lead_obstacle")
    first_exit_step = next((s["step"] for s in steps_dry[1:] if not s["within_longitudinal_corridor"]), None)
    first_exit_tau_s = steps_dry[first_exit_step]["t_s"] if first_exit_step is not None else None

    return {
        "condition_id": condition_id,
        "condition_label": condition_label,
        "condition_role": condition_role,
        "is_canonical": is_canonical,
        "scene_id": artifact.scene_id,
        "frame_token": artifact.frame_token,
        "driving_command": artifact.driving_command,
        "prompt_text": artifact.prompt_text,
        "action_codebook_indices": list(artifact.action_codebook_indices),
        "ego_initial_speed_mps": round(float(artifact.ego_initial_speed_mps), 4),
        "ego_initial_speed_kmh": round(mps_to_kmh(float(artifact.ego_initial_speed_mps)), 3),
        "ego_initial_accel_mps2": round(float(artifact.ego_initial_accel_mps2), 4),
        "observed_accel_norm_mps2": round(float(scene_meta["ego_state"]["accel_norm_mps2"]), 4),
        "observed_in_lane_lead_obstacle": obs_lead,
        "counterfactual_obstacle_distances_m": list(scene_meta.get("counterfactual_obstacle_distances_m", [])),
        "gt_comparison_meaningful": gt_comparison_meaningful,
        "gt_comparison_note": gt_comparison_note,
        "ade_vs_logged_gt_m": round(ade_m, 4),
        "fde_vs_logged_gt_m": round(fde_m, 4),
        "first_corridor_exit_step": first_exit_step,
        "first_corridor_exit_tau_s": first_exit_tau_s,
        "comparison_counterpart_id": comparison_counterpart_id,
        "feasibility_dry_mu1_0": feas_dry.to_dict(),
        "feasibility_wet_mu0_5": feas_wet.to_dict(),
        "steps_dry_mu1_0": steps_dry,
        "steps_wet_mu0_5": steps_wet,
    }


def build_trajectory_explorer_catalog(
    manifest_path: str | Path = DEFAULT_DATA_DIR / "scenes_manifest.json",
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
    command_sensitivity_dir: str | Path = DEFAULT_COMMAND_SENSITIVITY_DIR,
    ablation_scene_05_path: str | Path = EXT_ROOT / "artifacts" / "ablation_scene_05_signed_accel.json",
) -> dict[str, Any]:
    """Assemble the complete, provenance-verified catalog of 10 trajectory conditions across all 7 scenes."""
    verify_canonical_predictions_unchanged(predictions_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    scene_by_id = {s["scene_id"]: s for s in manifest["scenes"]}
    pred_root = Path(predictions_dir)
    cmd_root = Path(command_sensitivity_dir)
    abl_path = Path(ablation_scene_05_path)

    # Verify action tokenizer decodes all 10 conditions cleanly
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)

    conditions: dict[str, dict[str, Any]] = {}
    scene_condition_map: dict[str, list[str]] = {s["scene_id"]: [] for s in manifest["scenes"]}

    for scene_meta in manifest["scenes"]:
        sid = scene_meta["scene_id"]
        canon_art = load_prediction_artifact(pred_root / f"{sid}_fast.json")
        # Verify codebook decoding matches stored waypoints
        decoded = tokenizer.decode_indices_to_waypoints(canon_art.action_codebook_indices)
        assert len(decoded) == len(canon_art.predicted_waypoints)

        is_leak_turn = sid in ("scene_02_stationary_lead_obstacle", "scene_06_intersection_turn_maneuver")
        counterpart = (
            f"{sid}__intervention_keep_forward"
            if is_leak_turn
            else (f"{sid}__ablation_signed_accel" if sid == "scene_05_active_braking_deceleration" else None)
        )
        gt_note = (
            "Command-conditioned evaluation ('turn left' matches the logged human left-turn maneuver; subject to EXT-VLA-C06 future-displacement command leakage boundary)."
            if is_leak_turn
            else (
                "Active-braking scenario where logged human driver brakes for t <= 2.5 s (to x = 6.92 m) and then accelerates to x = 15.65 m; canonical prompt passes unsigned ||a(0)|| = 1.56 m/s^2."
                if sid == "scene_05_active_braking_deceleration"
                else "Direct ego-frame comparison between genuine AutoVLA rollout and logged human driving trajectory."
            )
        )
        cond_id = f"{sid}__canonical"
        conditions[cond_id] = _build_condition_entry(
            condition_id=cond_id,
            condition_label=f"Canonical AutoVLA Output (cmd='{canon_art.driving_command}')",
            condition_role="CANONICAL_GENUINE_AUTOVLA",
            is_canonical=True,
            gt_comparison_meaningful=True,
            gt_comparison_note=gt_note,
            scene_meta=scene_meta,
            artifact=canon_art,
            comparison_counterpart_id=counterpart,
        )
        scene_condition_map[sid].append(cond_id)

        # Add Scene 02 / Scene 06 controlled `keep forward` intervention if applicable
        if sid in ("scene_02_stationary_lead_obstacle", "scene_06_intersection_turn_maneuver"):
            short_prefix = "scene_02" if sid.startswith("scene_02") else "scene_06"
            intv_path = cmd_root / f"{short_prefix}_keep_forward.json"
            if intv_path.exists():
                intv_art = load_prediction_artifact(intv_path)
                intv_id = f"{sid}__intervention_keep_forward"
                conditions[intv_id] = _build_condition_entry(
                    condition_id=intv_id,
                    condition_label="Experimental Intervention: cmd='keep forward' (RQ1 EXT-VLA-C07)",
                    condition_role="CONTROLLED_COMMAND_INTERVENTION",
                    is_canonical=False,
                    gt_comparison_meaningful=False,
                    gt_comparison_note=(
                        "CRITICAL INTERPRETATION BOUNDARY (EXT-VLA-C07): The logged human trajectory is a left-turn "
                        "maneuver and is NOT a valid ground-truth target for a deliberately different 'keep forward' "
                        "command. Displacement differences against the logged turn quantify command sensitivity only, "
                        "NOT policy quality or driving safety."
                    ),
                    scene_meta=scene_meta,
                    artifact=intv_art,
                    comparison_counterpart_id=cond_id,
                )
                scene_condition_map[sid].append(intv_id)

        # Add Scene 05 signed-acceleration OOD diagnostic ablation if applicable
        if sid == "scene_05_active_braking_deceleration" and abl_path.exists():
            abl_art = load_prediction_artifact(abl_path)
            abl_id = f"{sid}__ablation_signed_accel"
            conditions[abl_id] = _build_condition_entry(
                condition_id=abl_id,
                condition_label="Experimental OOD Diagnostic: Signed Prompt '-1.55 m/s^2' (EXT-VLA-C03)",
                condition_role="CONTROLLED_OOD_DIAGNOSTIC_ABLATION",
                is_canonical=False,
                gt_comparison_meaningful=True,
                gt_comparison_note=(
                    "OUT-OF-DISTRIBUTION (OOD) DIAGNOSTIC BOUNDARY (EXT-VLA-C03): AutoVLA was trained on unsigned "
                    "acceleration norms (||a|| >= 0). Passing '-1.55 m/s^2' is a single-scene diagnostic intervention "
                    "that restores braking over t = 0.0..2.0 s (ADE 1.21 -> 0.14 m) and stops at x = 6.93 m, while the "
                    "logged human driver releases the brake after t = 2.5 s and accelerates to 15.65 m."
                ),
                scene_meta=scene_meta,
                artifact=abl_art,
                comparison_counterpart_id=cond_id,
            )
            scene_condition_map[sid].append(abl_id)

    parity_cases = generate_r3b_browser_parity_reference_cases()
    parity_out_path = EXT_ROOT / "artifacts" / "r3b_browser_python_parity_cases.json"
    parity_out_path.parent.mkdir(parents=True, exist_ok=True)
    parity_out_path.write_text(json.dumps(parity_cases, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "total_scenes": len(manifest["scenes"]),
        "total_conditions": len(conditions),
        "scene_condition_map": scene_condition_map,
        "conditions": conditions,
        "epa_coastdown_table": load_epa_drag_table_rows(),
        "supported_aero_drag_modes": SUPPORTED_AERO_DRAG_MODES,
        "r3b_frozen_parameters": PARAMETERS,
        "r3b_success_criteria": SUCCESS,
        "r3b_policy_metadata": POLICY_METADATA,
        "presentation_mapping_spec": PRESENTATION_MAPPING_SPEC,
        "corridor_bounds": {
            "lateral_half_width_m": LATERAL_CORRIDOR_HALF_WIDTH_M,
            "max_heading_rad": MAX_LONGITUDINAL_HEADING_RAD,
            "max_heading_deg": round(math.degrees(MAX_LONGITUDINAL_HEADING_RAD), 2),
            "min_applicable_speed_mps": MIN_APPLICABLE_SPEED_MPS,
            "max_takeover_request_tau_s": 3.0,
        },
        "r3b_browser_parity_reference_cases": parity_cases,
    }


def generate_r3b_browser_parity_reference_cases() -> dict[str, Any]:
    """Generate deterministic Python R3B reference cases to validate browser-side R3B parity.

    Covers:
    1. Vehicle speed (`v0_mps` & `v0_kmh`) and obstacle distance (`d0_m`) across all 7 scenes + R3B grid speeds.
    2. Road friction (`mu` across dry 1.0, damp 0.85, wet 0.70, rain 0.50, snow 0.35, ice 0.20).
    3. Human reaction delay (`t1_s`), hydraulic system latency (`t2_s`), and brake ramp (`t3_s`),
       including standstill inside pre-control (`t1`) and standstill inside the linear brake ramp (`t3`).
    4. Policy branches (`P0`, `P1`, `P2`) and chassis / support bounds (`a_max_mps2`, `a_sup_mps2`).
    5. Supported aerodynamic coastdown drag modes (`epa_midpoint`, `epa_p05`, `epa_median`,
       `epa_p95`, `epa_bev_median`, and `custom` `a_drag_custom_mps2`).
    6. Road gradient (`road_grade_pct = 0.0` level road vs non-zero out-of-slice `NOT_APPLICABLE` vs invalid `> 25%`).
    7. Corridor boundaries (`|y| > 1.75 m`, `|heading| > 0.35 rad`, `d_rem <= 0 m`), stationary speed
       (`v <= 0.05 m/s`), missing obstacle (`NONE_INSUFFICIENT_EVIDENCE`), boundary proximity (`EPSILON_S = 0.01 s`),
       and invalid input rejection (`valid_inputs = False`).
    """
    raw_specs: list[tuple[str, str, dict[str, Any]]] = [
        # --- A. Nominal & Scene-Matched Baseline Cases ---
        (
            "RC01_scene01_high_speed_p1_dry",
            "Scene 01 t0 v0=13.58 m/s, counterfactual d0=45m, P1 dry mu=1.0",
            dict(v0_mps=13.5825, obstacle_distance_d0_m=45.0, mu=1.0, selected_branch="P1"),
        ),
        (
            "RC02_scene01_high_speed_p0_dry",
            "Scene 01 t0 v0=13.58 m/s, counterfactual d0=45m, P0 dry mu=1.0",
            dict(v0_mps=13.5825, obstacle_distance_d0_m=45.0, mu=1.0, selected_branch="P0"),
        ),
        (
            "RC03_scene01_high_speed_p2_dry",
            "Scene 01 t0 v0=13.58 m/s, counterfactual d0=45m, P2 dry mu=1.0",
            dict(v0_mps=13.5825, obstacle_distance_d0_m=45.0, mu=1.0, selected_branch="P2"),
        ),
        (
            "RC04_scene02_observed_static_lead_t0",
            "Scene 02 t0 v0=6.95 m/s, observed stationary obstacle d0=55.49m",
            dict(
                v0_mps=6.9491,
                obstacle_distance_d0_m=55.489,
                mu=1.0,
                selected_branch="P1",
                obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
                observed_lead_speed_mps=0.0,
            ),
        ),
        (
            "RC05_scene02_keep_forward_tau1p5s",
            "Scene 02 keep_forward intervention at tau_req=1.5s inside 1D corridor",
            dict(
                v0_mps=7.5162,
                obstacle_distance_d0_m=55.489,
                mu=1.0,
                selected_branch="P1",
                tau_req_s=1.5,
                ego_x_at_req_m=10.8923,
                ego_y_at_req_m=0.4158,
                ego_heading_at_req_rad=0.1149,
                obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
                observed_lead_speed_mps=0.0,
            ),
        ),
        (
            "RC06_scene03_urban_moving_lead_wet",
            "Scene 03 t0 v0=13.05 m/s, moving lead d0=37.34m on wet road mu=0.5",
            dict(
                v0_mps=13.0475,
                obstacle_distance_d0_m=37.343,
                mu=0.5,
                selected_branch="P1",
                obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
                observed_lead_speed_mps=11.12,
            ),
        ),
        (
            "RC07_scene04_arterial_lead_tau2s",
            "Scene 04 at tau_req=2.0s with moving lead d0=68.04m",
            dict(
                v0_mps=6.3941,
                obstacle_distance_d0_m=68.041,
                mu=1.0,
                selected_branch="P2",
                tau_req_s=2.0,
                ego_x_at_req_m=12.631,
                ego_y_at_req_m=0.042,
                ego_heading_at_req_rad=0.008,
                obstacle_source=ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION,
                observed_lead_speed_mps=11.79,
            ),
        ),
        (
            "RC08_scene05_active_braking_cf20m",
            "Scene 05 t0 v0=4.31 m/s, counterfactual d0=20m",
            dict(v0_mps=4.3103, obstacle_distance_d0_m=20.0, mu=1.0, selected_branch="P1"),
        ),
        # --- B. Speed Unit Conversion (km/h Input Parity) ---
        (
            "RC09_kmh_60_alks_limit",
            "UN R157 60 km/h speed input with d0=50m, mu=1.0",
            dict(v0_kmh=60.0, obstacle_distance_d0_m=50.0, mu=1.0, selected_branch="P1"),
        ),
        (
            "RC10_kmh_100_motorway",
            "D003 100 km/h speed input with d0=95m, mu=0.7",
            dict(v0_kmh=100.0, obstacle_distance_d0_m=95.0, mu=0.7, selected_branch="P2"),
        ),
        (
            "RC11_kmh_130_alks_rev1",
            "UN R157 Rev.1 130 km/h speed input with d0=140m, mu=1.0",
            dict(v0_kmh=130.0, obstacle_distance_d0_m=140.0, mu=1.0, selected_branch="P0"),
        ),
        # --- C. Friction Saturation & Surface Sweep ---
        (
            "RC12_friction_damp_0p85",
            "Damp road mu=0.85 where mu*g=8.3385 > a_max=8.00 (chassis limited)",
            dict(v0_mps=15.0, obstacle_distance_d0_m=50.0, mu=0.85, a_max_mps2=8.0, selected_branch="P1"),
        ),
        (
            "RC13_friction_wet_0p70",
            "Wet road mu=0.70 where mu*g=6.867 < a_max=8.00 (friction capped)",
            dict(v0_mps=15.0, obstacle_distance_d0_m=50.0, mu=0.70, a_max_mps2=8.0, selected_branch="P1"),
        ),
        (
            "RC14_friction_snow_0p35",
            "Snow surface mu=0.35 where mu*g=3.4335 caps braking strongly",
            dict(v0_mps=15.0, obstacle_distance_d0_m=50.0, mu=0.35, a_max_mps2=8.5, selected_branch="P1"),
        ),
        (
            "RC15_friction_ice_0p20",
            "Ice surface mu=0.20 where mu*g=1.962 m/s^2",
            dict(v0_mps=12.0, obstacle_distance_d0_m=45.0, mu=0.20, a_max_mps2=9.1, selected_branch="P2"),
        ),
        # --- D. Reaction Delay t1, System Latency t2, Brake Ramp t3 & Phase-Stop Regimes ---
        (
            "RC16_short_reaction_attentive_1p15s",
            "Lower R3B corner t1=1.15s, t2=0.05s, t3=0.30s, a_max=9.10 m/s^2",
            dict(
                v0_mps=20.0,
                obstacle_distance_d0_m=60.0,
                mu=1.0,
                t1_s=1.15,
                t2_s=0.05,
                t3_s=0.30,
                a_max_mps2=9.10,
                selected_branch="P1",
            ),
        ),
        (
            "RC17_long_reaction_conservative_3p00s",
            "Upper R3B corner t1=3.00s, t2=0.17s, t3=1.20s, a_max=6.43 m/s^2",
            dict(
                v0_mps=20.0,
                obstacle_distance_d0_m=60.0,
                mu=1.0,
                t1_s=3.00,
                t2_s=0.17,
                t3_s=1.20,
                a_max_mps2=6.43,
                selected_branch="P0",
            ),
        ),
        (
            "RC18_standstill_inside_pre_control_phase",
            "Vehicle reaches standstill inside pre-control t1 under P2 (v0=3.5 m/s, a_sup=2.5 m/s^2, t1=2.0s)",
            dict(
                v0_mps=3.5,
                obstacle_distance_d0_m=15.0,
                mu=1.0,
                t1_s=2.0,
                t2_s=0.12,
                t3_s=0.80,
                a_max_mps2=8.0,
                a_sup_mps2=2.5,
                selected_branch="P2",
            ),
        ),
        (
            "RC19_standstill_inside_linear_brake_ramp",
            "Vehicle reaches standstill inside linear brake ramp t3 (v_after_t1 <= 0.5 * a_eff * t3)",
            dict(
                v0_mps=4.2,
                obstacle_distance_d0_m=18.0,
                mu=1.0,
                t1_s=1.2,
                t2_s=0.10,
                t3_s=1.40,
                a_max_mps2=8.5,
                selected_branch="P1",
            ),
        ),
        (
            "RC20_zero_delay_zero_ramp_step_braking",
            "Instantaneous brake buildup t2=0.0s, t3=0.0s (R0 reference profile)",
            dict(
                v0_mps=18.0,
                obstacle_distance_d0_m=55.0,
                mu=1.0,
                t1_s=1.50,
                t2_s=0.0,
                t3_s=0.0,
                a_max_mps2=8.0,
                selected_branch="P0",
            ),
        ),
        # --- E. Supported Aerodynamic / Coastdown Drag Modes ---
        (
            "RC21_aero_drag_epa_p05",
            "EPA 5th percentile low aerodynamic/rolling drag mode at 25 m/s (90 km/h)",
            dict(
                v0_mps=25.0,
                obstacle_distance_d0_m=85.0,
                mu=1.0,
                a_drag_mode="epa_p05",
                selected_branch="P1",
            ),
        ),
        (
            "RC22_aero_drag_epa_median",
            "EPA 50th percentile median drag mode at 25 m/s (90 km/h)",
            dict(
                v0_mps=25.0,
                obstacle_distance_d0_m=85.0,
                mu=1.0,
                a_drag_mode="epa_median",
                selected_branch="P1",
            ),
        ),
        (
            "RC23_aero_drag_epa_p95",
            "EPA 95th percentile high aerodynamic/rolling drag mode at 25 m/s (90 km/h)",
            dict(
                v0_mps=25.0,
                obstacle_distance_d0_m=85.0,
                mu=1.0,
                a_drag_mode="epa_p95",
                selected_branch="P1",
            ),
        ),
        (
            "RC24_aero_drag_epa_bev_median",
            "EPA Battery Electric median coastdown drag mode (road-load only, no regen)",
            dict(
                v0_mps=25.0,
                obstacle_distance_d0_m=85.0,
                mu=1.0,
                a_drag_mode="epa_bev_median",
                selected_branch="P1",
            ),
        ),
        (
            "RC25_aero_drag_custom_0p32",
            "Custom coastdown drag a_drag=0.32 m/s^2 at 22 m/s",
            dict(
                v0_mps=22.0,
                obstacle_distance_d0_m=72.0,
                mu=0.9,
                a_drag_mode="custom",
                a_drag_custom_mps2=0.32,
                selected_branch="P1",
            ),
        ),
        # --- F. Boundary Proximity (EPSILON_S = 0.01 s) ---
        (
            "RC26_boundary_proximity_epsilon_band",
            "Obstacle distance tuned so conservative time margin lies inside +-0.01s boundary band",
            dict(
                v0_mps=10.0,
                obstacle_distance_d0_m=46.15,
                mu=1.0,
                selected_branch="P0",
            ),
        ),
        # --- G. Road Gradient Applicability Boundaries ---
        (
            "RC27_road_grade_downhill_minus3pct_not_applicable",
            "Downhill grade -3.0% is outside level-road R3A/R3B analytical slice -> NOT_APPLICABLE",
            dict(
                v0_mps=15.0,
                obstacle_distance_d0_m=50.0,
                mu=1.0,
                road_grade_pct=-3.0,
                selected_branch="P1",
            ),
        ),
        (
            "RC28_road_grade_uphill_plus4pct_not_applicable",
            "Uphill grade +4.0% is outside level-road R3A/R3B analytical slice -> NOT_APPLICABLE",
            dict(
                v0_mps=15.0,
                obstacle_distance_d0_m=50.0,
                mu=1.0,
                road_grade_pct=4.0,
                selected_branch="P1",
            ),
        ),
        # --- H. Corridor Restrictions, Stationary Ego & Insufficient Evidence ---
        (
            "RC29_corridor_lateral_exit_scene02_turn_left",
            "Scene 02 canonical turn-left at tau_req=1.5s exits +-1.75m lateral corridor -> NOT_APPLICABLE",
            dict(
                v0_mps=7.6481,
                obstacle_distance_d0_m=55.489,
                mu=1.0,
                tau_req_s=1.5,
                ego_x_at_req_m=10.674,
                ego_y_at_req_m=1.961,
                ego_heading_at_req_rad=0.415,
                selected_branch="P1",
            ),
        ),
        (
            "RC30_corridor_heading_exit_only",
            "Heading |psi|=0.39 rad > 0.35 rad even with |y|=1.10 m <= 1.75 m -> NOT_APPLICABLE",
            dict(
                v0_mps=9.0,
                obstacle_distance_d0_m=40.0,
                mu=1.0,
                tau_req_s=1.0,
                ego_x_at_req_m=8.5,
                ego_y_at_req_m=1.10,
                ego_heading_at_req_rad=0.39,
                selected_branch="P1",
            ),
        ),
        (
            "RC31_stationary_ego_scene07",
            "Scene 07 stationary ego v0=0.0019 m/s <= 0.05 m/s -> NOT_APPLICABLE",
            dict(
                v0_mps=0.0019,
                obstacle_distance_d0_m=20.0,
                mu=1.0,
                selected_branch="P1",
            ),
        ),
        (
            "RC32_obstacle_already_passed_d_rem_nonpositive",
            "Ego x=32.0m >= d0=30.0m (d_rem = -2.0m <= 0) -> NOT_APPLICABLE",
            dict(
                v0_mps=12.0,
                obstacle_distance_d0_m=30.0,
                mu=1.0,
                tau_req_s=2.5,
                ego_x_at_req_m=32.0,
                selected_branch="P1",
            ),
        ),
        (
            "RC33_missing_obstacle_insufficient_evidence",
            "Open-road scene with no observed 3D obstacle and no assumed d0 -> INSUFFICIENT_EVIDENCE",
            dict(
                v0_mps=13.5825,
                obstacle_distance_d0_m=None,
                mu=1.0,
                obstacle_source=ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE,
                selected_branch="P1",
            ),
        ),
        # --- I. Invalid Parameter Guardrails (valid_inputs = False -> NOT_APPLICABLE) ---
        (
            "RC34_invalid_negative_speed",
            "Negative speed v0=-5.0 m/s rejected",
            dict(v0_mps=-5.0, obstacle_distance_d0_m=45.0, mu=1.0, selected_branch="P1"),
        ),
        (
            "RC35_invalid_excessive_speed",
            "Excessive speed v0=72.0 m/s (> 60 m/s) rejected",
            dict(v0_mps=72.0, obstacle_distance_d0_m=100.0, mu=1.0, selected_branch="P1"),
        ),
        (
            "RC36_invalid_zero_obstacle_distance",
            "Zero obstacle distance d0=0.0 m rejected",
            dict(v0_mps=12.0, obstacle_distance_d0_m=0.0, mu=1.0, selected_branch="P1"),
        ),
        (
            "RC37_invalid_friction_zero",
            "Zero friction mu=0.0 rejected",
            dict(v0_mps=12.0, obstacle_distance_d0_m=45.0, mu=0.0, selected_branch="P1"),
        ),
        (
            "RC38_invalid_friction_above_1p2",
            "Excessive friction mu=1.35 (> 1.2) rejected",
            dict(v0_mps=12.0, obstacle_distance_d0_m=45.0, mu=1.35, selected_branch="P1"),
        ),
        (
            "RC39_invalid_negative_reaction_t1",
            "Negative reaction delay t1=-0.4 s rejected",
            dict(v0_mps=12.0, obstacle_distance_d0_m=45.0, mu=1.0, t1_s=-0.4, selected_branch="P1"),
        ),
        (
            "RC40_invalid_tau_req_above_3s",
            "Takeover request timing tau_req=3.5 s (> 3.0 s) rejected",
            dict(v0_mps=12.0, obstacle_distance_d0_m=45.0, mu=1.0, tau_req_s=3.5, selected_branch="P1"),
        ),
        (
            "RC41_invalid_custom_drag_negative",
            "Negative custom aerodynamic drag a_drag=-0.15 m/s^2 rejected",
            dict(
                v0_mps=12.0,
                obstacle_distance_d0_m=45.0,
                mu=1.0,
                a_drag_mode="custom",
                a_drag_custom_mps2=-0.15,
                selected_branch="P1",
            ),
        ),
        (
            "RC42_invalid_extreme_road_grade",
            "Extreme road gradient +35.0% (> 25.0%) rejected",
            dict(
                v0_mps=12.0,
                obstacle_distance_d0_m=45.0,
                mu=1.0,
                road_grade_pct=35.0,
                selected_branch="P1",
            ),
        ),
    ]

    cases_out: list[dict[str, Any]] = []
    for case_id, description, kwargs in raw_specs:
        serializable_inputs = {
            k: (v.value if isinstance(v, ObstacleSourceType) else v)
            for k, v in kwargs.items()
        }
        expected = evaluate_interactive_r3b(**kwargs)
        cases_out.append(
            {
                "case_id": case_id,
                "description": description,
                "inputs": serializable_inputs,
                "expected": expected,
            }
        )

    return {
        "schema_version": "1.0.0",
        "total_cases": len(cases_out),
        "numerical_tolerance_unrounded": 1e-9,
        "numerical_tolerance_rounded_display": 1e-4,
        "cases": cases_out,
    }

