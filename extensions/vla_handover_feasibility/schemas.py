"""Typed data structures and evidence-boundary enums for VLA-Informed Handover Feasibility Analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FeasibilityClassification(str, Enum):
    """Independent trajectory physical feasibility classification (Phase C).

    Refers strictly to explicitly checked kinematic and dynamic conditions on a
    VLA-predicted trajectory. Passing these checks does NOT establish collision
    avoidance, overall driving safety, or production readiness.
    """

    CONSTRAINTS_SATISFIED = "CONSTRAINTS_SATISFIED"
    CONSTRAINTS_VIOLATED = "CONSTRAINTS_VIOLATED"
    INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE = "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE"


class ObstacleSourceType(str, Enum):
    """Provenance of obstacle distance used in counterfactual R3B takeover evaluation."""

    OBSERVED_IN_LANE_ANNOTATION = "OBSERVED_IN_LANE_ANNOTATION"
    COUNTERFACTUAL_ASSUMPTION = "COUNTERFACTUAL_ASSUMPTION"
    NONE_INSUFFICIENT_EVIDENCE = "NONE_INSUFFICIENT_EVIDENCE"


class TakeoverR3BStatus(str, Enum):
    """R3B evaluation eligibility and outcome status at a candidate takeover request time."""

    EVALUATED = "EVALUATED"
    INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE = "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE"


@dataclass(frozen=True)
class TrajectoryWaypoint:
    """Single time-indexed waypoint in the ego-vehicle local coordinate frame at t0 = 0.0 s.

    Coordinate conventions:
    - +x_m: forward longitudinal displacement (meters) relative to ego at t0
    - +y_m: leftward lateral displacement (meters) relative to ego at t0
    - heading_rad: yaw angle (radians, counter-clockwise positive) relative to ego at t0
    """

    step: int
    t_s: float
    x_m: float
    y_m: float
    heading_rad: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WaypointKinematics:
    """Derived step-wise kinematic and dynamic quantities along a predicted trajectory."""

    step: int
    t_s: float
    dt_s: float
    x_m: float
    y_m: float
    heading_rad: float
    ds_m: float
    dx_m: float
    dy_m: float
    implied_speed_mps: float
    vx_local_mps: float
    vy_local_mps: float
    a_lon_mps2: float
    a_lat_mps2: float
    a_total_mps2: float
    yaw_rate_radps: float
    curvature_1pm: float
    braking_demand_mps2: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstraintCheckDetail:
    """Outcome of a single explicit physical feasibility check."""

    check_id: str
    description: str
    passed: bool
    applicable: bool
    observed_value: float | None
    limit_value: float | None
    units: str
    violation_steps: list[int] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrictionSensitivityCheck:
    """Physical feasibility check of predicted trajectory demands against a road friction coefficient mu."""

    mu: float
    mu_g_limit_mps2: float
    max_braking_demand_mps2: float
    max_total_accel_mps2: float
    braking_within_friction: bool
    total_accel_within_friction_circle: bool
    braking_margin_mps2: float
    friction_circle_margin_mps2: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrajectoryFeasibilityResult:
    """Independent physical feasibility assessment of a VLA-generated trajectory (Phase C).

    Strictly separated from the R3B braking-only human fallback necessary-condition model.
    """

    scene_id: str
    mode: str
    classification: FeasibilityClassification
    initial_speed_mps: float
    initial_accel_mps2: float
    dt_s: float
    horizon_s: float
    num_waypoints: int
    max_implied_speed_mps: float
    min_implied_speed_mps: float
    max_lon_accel_mps2: float
    min_lon_accel_mps2: float
    max_braking_demand_mps2: float
    max_abs_lat_accel_mps2: float
    max_total_accel_mps2: float
    max_abs_yaw_rate_radps: float
    total_path_length_m: float
    checks: list[ConstraintCheckDetail]
    friction_sensitivity: list[FrictionSensitivityCheck]
    violation_reasons: list[str]
    insufficient_evidence_reasons: list[str]
    scope_disclaimer: str = (
        "Classifications refer only to explicitly checked kinematic and dynamic conditions on the "
        "VLA-predicted trajectory. Passing these checks does NOT establish collision avoidance, "
        "human takeover success, overall driving safety, or production readiness."
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


@dataclass(frozen=True)
class VLAPredictionArtifact:
    """Saved genuine VLA inference output with full model, dataset, and environment provenance (Phase B)."""

    scene_id: str
    inference_mode: str  # "fast" or "cot"
    model_name: str
    checkpoint_repo: str
    checkpoint_file: str
    checkpoint_etag: str
    base_vlm_architecture: str
    dataset_source: str
    log_file: str
    frame_token: str
    scene_name: str
    map_location: str
    timestamp_us: int
    ego_initial_speed_mps: float
    ego_initial_accel_mps2: float
    ego_vx_mps: float
    ego_vy_mps: float
    ego_ax_mps2: float
    ego_ay_mps2: float
    driving_command: str
    raw_driving_command: str
    prompt_text: str
    raw_generated_text: str
    cot_reasoning_text: str | None
    action_token_ids: list[int]
    action_codebook_indices: list[int]
    prediction_valid: bool
    validity_notes: str
    coordinate_frame: str
    units: dict[str, str]
    horizon_s: float
    dt_s: float
    predicted_waypoints: list[TrajectoryWaypoint]
    ground_truth_waypoints: list[TrajectoryWaypoint]
    inference_latency_ms: float
    environment_metadata: dict[str, Any]
    predicts_human_takeover_request: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R3BBranchPointResult:
    """Single-point or interval R3B braking-only recoverability evaluation for a policy branch."""

    branch_id: str  # "P0", "P1", "P2"
    mu: float
    tau_r_lo_s: float
    tau_r_hi_s: float
    a_max_lo_mps2: float
    a_max_hi_mps2: float
    t_b_lo_s: float
    t_b_hi_s: float
    # Optimistic corner: lowest latency (tau_r_lo), highest braking capability (a_max_hi), fastest buildup (t_b_lo)
    d_stop_min_m: float
    t_req_min_s: float
    margin_max_m: float
    # Conservative corner: highest latency (tau_r_hi), lowest braking capability (a_max_lo), slowest buildup (t_b_hi)
    d_stop_max_m: float
    t_req_max_s: float
    margin_min_m: float
    # Interval classification across the parameter cell
    optimistic_classification: str
    conservative_classification: str
    interval_classification: str  # "UNIFORMLY_POSITIVE", "UNIFORMLY_VIOLATED", "PARAMETER_SENSITIVE"
    boundary_proximity_flag: bool
    t_avail_s: float = 0.0
    margin_max_s: float = 0.0
    margin_min_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TakeoverRequestEvaluation:
    """Counterfactual R3B human fallback evaluation at an assumed takeover-request time tau_req (Phase D)."""

    scene_id: str
    inference_mode: str
    tau_req_s: float
    state_source: str
    status: TakeoverR3BStatus
    obstacle_source: ObstacleSourceType
    initial_obstacle_distance_d0_m: float | None
    ego_lon_displacement_at_req_m: float
    ego_lat_displacement_at_req_m: float
    ego_heading_at_req_rad: float
    hypothetical_speed_at_req_mps: float
    remaining_obstacle_distance_m: float | None
    available_ttc_stationary_s: float | None
    available_ttc_closing_s: float | None
    observed_lead_speed_mps: float | None
    lateral_corridor_warning: bool
    insufficient_evidence_reasons: list[str]
    branch_results: list[R3BBranchPointResult]
    state_disclaimer: str = (
        "Complete scenario state provenance combines ego state and obstacle provenance: "
        "at tau_req = 0.0 s, ego kinematics are observed at t0, whereas any counterfactual d0 "
        "(or static projection of a moving lead vehicle) is an explicit assumption. "
        "For tau_req > 0.0 s, ego position and speed are hypothetical VLA planning states, "
        "NOT observed vehicle motion or empirical human takeover measurements."
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["obstacle_source"] = self.obstacle_source.value
        return d

