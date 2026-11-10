"""Conservative feasibility certificates for one specified quintic path family."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math

from src.vehicle.models import GRAVITY
from .kinematics import demand_bounds
from .schema import Outcome, Scenario, State, Vehicle


@dataclass(frozen=True)
class LateralResult:
    outcome: Outcome
    geometry: Outcome
    dynamics: Outcome
    reasons: tuple[str, ...]
    metrics: dict[str, float] = field(default_factory=dict)
    collision_avoidance: str = "not_validated"
    scope: str = "specified quintic path; constant speed; conditional on stated assumptions"
    evidence: dict = field(default_factory=dict)


def assess_lateral(vehicle: Vehicle, scenario: Scenario, state: State) -> LateralResult:
    reasons: list[str] = []
    metrics: dict[str, float] = {}
    evidence = dict(state=asdict(state), scenario=asdict(scenario), vehicle=asdict(vehicle))

    def result(geometry=Outcome.UNKNOWN, dynamics=Outcome.UNKNOWN):
        outcome = (Outcome.INFEASIBLE if Outcome.INFEASIBLE in (geometry, dynamics) else
                   Outcome.FEASIBLE if geometry == dynamics == Outcome.FEASIBLE else Outcome.UNKNOWN)
        return LateralResult(outcome, geometry, dynamics, tuple(reasons), metrics, evidence=evidence)

    geometry = Outcome.UNKNOWN
    clearance = scenario.clearance
    if clearance is None:
        reasons.append("missing_clearance_assumptions")
    else:
        h = scenario.target_offset_m
        if (min(0, h) < clearance.center_min_m or max(0, h) > clearance.center_max_m
                or abs(h) < clearance.required_offset_m or clearance.corridor_available is False):
            reasons.append("specified_path_violates_clearance")
            geometry = Outcome.INFEASIBLE
        elif clearance.corridor_available is None:
            reasons.append("corridor_availability_unknown")
        else:
            geometry = Outcome.FEASIBLE

    for name, observation in (("speed", state.speed_mps), ("steering", state.front_steering_rad)):
        if not observation.usable:
            reasons.append(f"{name}:{observation.evidence.value}")
    if not state.speed_mps.usable or not state.front_steering_rad.usable:
        return result(geometry)
    if scenario.road_curvature_per_m is None or scenario.available_distance_m is None:
        reasons.append("missing_road_geometry")
        return result(Outcome.INFEASIBLE if geometry == Outcome.INFEASIBLE else Outcome.UNKNOWN)
    if clearance is None:
        return result()
    v = state.speed_mps.bounds
    delta = state.front_steering_rad.bounds
    k, h = scenario.road_curvature_per_m, scenario.target_offset_m
    if v.low <= 0:
        reasons.append("stationary_or_zero_crossing_speed_outside_model")
        return result(geometry)
    expected = math.atan(vehicle.wheelbase_m*k)
    # No initial-state transient model: uncertainty must not silently imply exact tracking.
    if max(abs(delta.low-expected), abs(delta.high-expected)) > 1e-9:
        reasons.append("initial_steering_uncertainty_or_mismatch_requires_transient_model")
        return result(geometry)
    if min(1.0, 1-k*h) < 0.1:
        reasons.append("frenet_coordinates_outside_supported_domain")
        return result(Outcome.UNKNOWN)

    low_delay = scenario.driver_delay_s.low + scenario.steering_delay_s.low + state.latency_s.low
    high_delay = scenario.driver_delay_s.high + scenario.steering_delay_s.high + state.latency_s.high
    distance = scenario.available_distance_m-clearance.longitudinal_buffer_m
    length_low, length_high = distance-v.high*high_delay, distance-v.low*low_delay
    if not all(math.isfinite(x) for x in (length_low, length_high, low_delay, high_delay)):
        reasons.append("nonfinite_numerical_horizon")
        return result(geometry)
    metrics.update(path_length_low_m=length_low, path_length_high_m=length_high,
                   delay_low_s=low_delay, delay_high_s=high_delay)
    if length_high <= 0:
        reasons.append("no_distance_after_delay_for_specified_path")
        return result(Outcome.INFEASIBLE)
    if length_low <= 0:
        reasons.append("uncertainty_crosses_zero_remaining_distance")
        return result(Outcome.INFEASIBLE if geometry == Outcome.INFEASIBLE else Outcome.UNKNOWN)
    # Curvature bounds near zero length can overflow before any useful physical interpretation.
    if length_low < 1e-3 or max(v.high, abs(k), abs(h), length_high) > 1e6:
        reasons.append("outside_numerically_supported_domain")
        return result(geometry)
    if scenario.friction is None:
        reasons.append("missing_tyre_grip")
        return result(geometry)

    try:
        bounds = demand_bounds(length_low, length_high, h, k, vehicle.wheelbase_m, v.low, v.high)
    except (OverflowError, ZeroDivisionError, ValueError):
        reasons.append("nonfinite_numerical_demand")
        return result(geometry)
    if not all(math.isfinite(value) for value in bounds.values()):
        reasons.append("nonfinite_numerical_demand")
        return result(geometry)
    metrics.update(bounds)
    low_capacity = min(vehicle.max_lateral_accel_mps2, GRAVITY*scenario.friction.low)
    high_capacity = min(vehicle.max_lateral_accel_mps2, GRAVITY*scenario.friction.high)
    metrics.update(lateral_capacity_low_mps2=low_capacity, lateral_capacity_high_mps2=high_capacity)
    constraints = [
        ("steering", bounds["steering_lower_rad"], bounds["steering_upper_rad"],
         vehicle.max_steering_rad, vehicle.max_steering_rad),
        ("lateral_acceleration_or_grip", bounds["lateral_accel_lower_mps2"],
         bounds["lateral_accel_upper_mps2"], low_capacity, high_capacity),
        ("steering_rate", bounds["steering_rate_lower_rad_s"], bounds["steering_rate_upper_rad_s"],
         vehicle.max_steering_rate_rad_s, vehicle.max_steering_rate_rad_s),
    ]
    # A scale-relative guard leaves equality/boundary cases UNKNOWN.
    def tol(*values):
        return 1e-9*max(1.0, *map(abs, values))
    failed = [name for name, lo, _, _, cap_hi in constraints if lo > cap_hi+tol(lo, cap_hi)]
    if failed:
        reasons.extend(f"certified_constraint_violation:{name}" for name in failed)
        return result(geometry, Outcome.INFEASIBLE)
    if all(hi < cap_lo-tol(hi, cap_lo) for _, _, hi, cap_lo, _ in constraints):
        reasons.append("conservative_bounds_satisfy_all_constraints")
        return result(geometry, Outcome.FEASIBLE)
    reasons.append("bounds_overlap_constraints_or_numerical_boundary")
    return result(geometry)
