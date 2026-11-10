"""Additive assessment of two candidate manoeuvres, with no action ranking."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math

from src.metrics.oracle import stopping_distance_r3b_analytical
from src.experiments.r3b_braking_bounds import classify
from .model import LateralResult, assess_lateral
from .schema import Outcome, Scenario, State, Vehicle, finite


@dataclass(frozen=True)
class BrakingAssumptions:
    """Explicit R3B inputs, independent of measured steering onset or steering delay."""
    a_max_mps2: float
    t_effective_s: float
    t_authority_s: float
    brake_delay_s: float
    brake_buildup_s: float
    a_before_authority_mps2: float = 0.0
    a_after_authority_mps2: float = 0.0
    u_brake: float = 1.0
    standstill_margin_m: float = 2.0
    source: str = "explicit counterfactual R3B assumptions"

    def __post_init__(self):
        for name, value in vars(self).items():
            if name != "source":
                finite(value, name, 0)
        if self.a_max_mps2 <= 0 or not 0 <= self.u_brake <= 1:
            raise ValueError("braking capability must be positive and u_brake in [0,1]")
        if self.t_authority_s > self.t_effective_s or not self.source:
            raise ValueError("need authority <= effective time and explicit provenance")


@dataclass(frozen=True)
class LongitudinalResult:
    outcome: Outcome
    r3b_label: str | None
    reasons: tuple[str, ...]
    metrics: dict[str, float] = field(default_factory=dict)
    assumptions: dict = field(default_factory=dict)


def assess_stopping(state: State, scenario: Scenario,
                    braking: BrakingAssumptions | None) -> LongitudinalResult:
    assumptions = dict(braking=None if braking is None else asdict(braking),
                       scenario=asdict(scenario), state=asdict(state))
    def unknown(reason):
        return LongitudinalResult(Outcome.UNKNOWN, None, (reason,), assumptions=assumptions)
    if braking is None:
        return unknown("missing_explicit_braking_assumptions")
    if not state.speed_mps.usable:
        return unknown("speed:"+state.speed_mps.evidence.value)
    if scenario.road_curvature_per_m != 0:
        return unknown("curved_or_unknown_road_requires_joint_grip_model_for_braking")
    # Straight-road R3B has no lateral tyre-force budget or steering transient.
    if not state.front_steering_rad.usable:
        return unknown("steering:"+state.front_steering_rad.evidence.value)
    steering = state.front_steering_rad.bounds
    if max(abs(steering.low), abs(steering.high)) > 1e-9:
        return unknown("nonzero_or_uncertain_steering_requires_joint_braking_model")
    if scenario.available_distance_m is None or scenario.friction is None:
        return unknown("missing_longitudinal_distance_or_friction")
    v, mu = state.speed_mps.bounds, scenario.friction
    if v.low <= 0 or mu.low <= 0 or braking.u_brake == 0:
        return unknown("outside_supported_positive_speed_and_braking_domain")

    def stopping(speed, friction):
        return stopping_distance_r3b_analytical(
            speed, braking.a_max_mps2, braking.t_effective_s, braking.brake_delay_s,
            braking.brake_buildup_s, braking.t_authority_s,
            braking.a_before_authority_mps2, braking.a_after_authority_mps2,
            braking.u_brake, friction)

    # For fixed nonnegative pre-control decelerations/timeline, stopping distance
    # increases with initial speed and decreases with braking capability/friction.
    # Constant-speed sensor latency is consumed separately, before TOR.
    try:
        d_low = v.low*state.latency_s.low+stopping(v.low, mu.high)
        d_high = v.high*state.latency_s.high+stopping(v.high, mu.low)
    except (OverflowError, ZeroDivisionError):
        return unknown("nonfinite_R3B_result")
    if not all(math.isfinite(x) for x in (d_low, d_high)):
        return unknown("nonfinite_R3B_result")
    margin_low = scenario.available_distance_m-braking.standstill_margin_m-d_high
    margin_high = scenario.available_distance_m-braking.standstill_margin_m-d_low
    # Interval division; conservative even if distance margin changes sign.
    margins_s = [m/s for m in (margin_low, margin_high) for s in (v.low, v.high)]
    if not all(math.isfinite(x) for x in margins_s):
        return unknown("nonfinite_R3B_time_margin")
    label = classify(min(margins_s), max(margins_s))
    outcome = {"ROBUSTLY SATISFIED": Outcome.FEASIBLE,
               "ROBUSTLY UNSATISFIED": Outcome.INFEASIBLE,
               "PARAMETER-SENSITIVE": Outcome.UNKNOWN}[label]
    return LongitudinalResult(outcome, label, ("unchanged_R3B_conditional_braking_model",), dict(
        stopping_distance_low_m=d_low, stopping_distance_high_m=d_high,
        distance_margin_low_m=margin_low, distance_margin_high_m=margin_high,
        time_margin_low_s=min(margins_s), time_margin_high_s=max(margins_s)), assumptions)


@dataclass(frozen=True)
class Decision:
    longitudinal: LongitudinalResult
    lateral: LateralResult
    assessment: str
    collision_avoidance: str = "not_validated"
    recommendation: str = "none; candidates are assessed, not ranked or commanded"


def combine(longitudinal: LongitudinalResult, lateral: LateralResult) -> Decision:
    outcomes = longitudinal.outcome, lateral.outcome
    if outcomes == (Outcome.INFEASIBLE, Outcome.INFEASIBLE):
        assessment = "neither_evaluated_candidate_feasible_under_assumptions"
    elif outcomes == (Outcome.FEASIBLE, Outcome.FEASIBLE):
        assessment = "both_candidates_conditionally_feasible_no_safety_ranking"
    elif Outcome.FEASIBLE in outcomes:
        assessment = ("longitudinal" if outcomes[0] == Outcome.FEASIBLE else "lateral") + "_conditionally_feasible"
    else:
        assessment = "insufficient_evidence_or_uncertainty"
    return Decision(longitudinal, lateral, assessment)


def assess_options(vehicle: Vehicle, scenario: Scenario, state: State,
                   braking: BrakingAssumptions | None) -> Decision:
    return combine(assess_stopping(state, scenario, braking), assess_lateral(vehicle, scenario, state))


@dataclass(frozen=True)
class CombinedResult:
    """Explicit unsupported simultaneous manoeuvre; never inferred from two certificates."""
    outcome: Outcome = Outcome.UNKNOWN
    reasons: tuple[str, ...] = ("simultaneous_braking_steering_requires_joint_grip_and_transient_model",)
    collision_avoidance: str = "not_validated"


def assess_combined_braking_steering() -> CombinedResult:
    """Neither separate candidate supplies a coupled force/path evolution model.

    Even a friction-circle necessary check would not certify a coupled trajectory.
    No inputs can presently turn this unsupported request into a certificate.
    """
    return CombinedResult()
