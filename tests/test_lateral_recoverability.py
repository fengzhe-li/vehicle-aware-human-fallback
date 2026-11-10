"""Independent geometry references, bound checks, evidence gates and R3B integration."""
from dataclasses import asdict, replace
import json
import math
from pathlib import Path

import numpy as np
import pytest

from automotive_can import Dbc, Frame, Replay
from automotive_can.dbc import Decoded, VehicleState
from lateral_recoverability import (
    Clearance, Evidence, Interval, Observation, Outcome, Scenario, State, Vehicle, assess_lateral,
)
from lateral_recoverability.can_adapter import Bindings, from_can
from lateral_recoverability.decision import BrakingAssumptions, assess_options, assess_stopping, combine, LongitudinalResult
from lateral_recoverability.experiments import sweep, synthetic_inputs, write_csv
from lateral_recoverability.kinematics import demand_bounds, path_point, smoothstep
from lateral_recoverability.model import LateralResult
from lateral_recoverability.schema import load_config
from src.metrics.oracle import stopping_distance_r3b_analytical


def nominal():
    vehicle, scenario, state, braking = synthetic_inputs({})
    # Exact reference state for analytical tests.
    state = replace(state, speed_mps=Observation(Interval.point(20), Evidence.ASSUMED, "test"))
    return vehicle, scenario, state, braking


def test_quintic_endpoints_and_derivatives():
    assert smoothstep(0) == (0, 0, 0, 60)
    assert smoothstep(1) == (1, 0, 0, 60)
    assert smoothstep(.5) == pytest.approx((.5, 1.875, 0, -30))
    u = (3-math.sqrt(3))/6
    assert smoothstep(u)[2] == pytest.approx(10/math.sqrt(3))


@pytest.mark.parametrize("k", [-.02, 0, 1e-12, .02])
def test_circle_reference_without_lane_shift(k):
    p = path_point(.5, 100, 0, k)
    assert p["curvature_per_m"] == pytest.approx(k, abs=1e-14)
    assert p["curvature_derivative_per_m2"] == 0
    assert p["path_metric"] == 1
    assert p["heading_rad"] == pytest.approx(50*k)
    if abs(k) > 1e-9:
        assert p["x_m"] == pytest.approx(math.sin(50*k)/k)
        assert p["y_m"] == pytest.approx((1-math.cos(50*k))/k)
    else:
        assert p["x_m"] == pytest.approx(50)
        assert p["y_m"] == pytest.approx(k*50**2/2, abs=1e-10)


@pytest.mark.parametrize("k,h", [(0, 3.5), (.02, 3.5), (-.02, 3.5), (.02, -3.5)])
def test_curvature_matches_cartesian_finite_difference(k, h):
    u, length, du = .37, 60, 1e-4
    left, center, right = [path_point(q, length, h, k) for q in (u-du, u, u+du)]
    x1, y1 = [(right[key]-left[key])/(2*du*length) for key in ("x_m", "y_m")]
    x2, y2 = [(right[key]-2*center[key]+left[key])/(du*length)**2 for key in ("x_m", "y_m")]
    expected = (x1*y2-y1*x2)/(x1*x1+y1*y1)**1.5
    assert center["curvature_per_m"] == pytest.approx(expected, rel=2e-6, abs=1e-9)
    kp = (right["curvature_per_m"]-left["curvature_per_m"])/(2*du*length)
    assert center["curvature_derivative_per_m2"] == pytest.approx(kp, rel=2e-6, abs=1e-9)


@pytest.mark.parametrize("k,h", [(0, 3.5), (.02, 3.5), (-.02, 3.5), (.02, -3.5), (.01, 0)])
def test_analytic_bounds_enclose_dense_path_and_uncertainty(k, h):
    bounds = demand_bounds(35, 70, h, k, 2.8, 10, 25)
    for length in np.linspace(35, 70, 9):
        points = [path_point(float(u), float(length), h, k) for u in np.linspace(0, 1, 501)]
        max_k = max(abs(p["curvature_per_m"]) for p in points)
        assert bounds["curvature_lower_per_m"] <= max_k+1e-12
        assert max_k <= bounds["curvature_upper_per_m"]+1e-12
        for v in (10, 17, 25):
            max_rate = max(abs(2.8*p["curvature_derivative_per_m2"]*v /
                               (p["path_metric"]*(1+(2.8*p["curvature_per_m"])**2))) for p in points)
            assert bounds["steering_rate_lower_rad_s"] <= max_rate+1e-12
            assert max_rate <= bounds["steering_rate_upper_rad_s"]+1e-12


def test_zero_shift_straight_road_has_no_lateral_demand():
    vehicle, scenario, state, _ = nominal()
    scenario = replace(scenario, target_offset_m=0,
                       clearance=replace(scenario.clearance, required_offset_m=0))
    result = assess_lateral(vehicle, scenario, state)
    assert result.outcome == Outcome.FEASIBLE
    assert result.metrics["curvature_upper_per_m"] == 0


def test_geometric_feasibility_does_not_certify_dynamics():
    vehicle, scenario, state, _ = nominal()
    result = assess_lateral(vehicle, replace(scenario, available_distance_m=45), state)
    assert result.geometry == Outcome.FEASIBLE
    assert result.outcome != Outcome.FEASIBLE
    assert result.collision_avoidance == "not_validated"


def test_clearance_and_missing_geometry_gates():
    vehicle, scenario, state, _ = nominal()
    for altered in (replace(scenario, clearance=None),
                    replace(scenario, road_curvature_per_m=None),
                    replace(scenario, available_distance_m=None),
                    replace(scenario, clearance=replace(scenario.clearance, corridor_available=None))):
        assert assess_lateral(vehicle, altered, state).outcome == Outcome.UNKNOWN
    for altered in (replace(scenario, target_offset_m=2),
                    replace(scenario, clearance=replace(scenario.clearance, center_max_m=3)),
                    replace(scenario, clearance=replace(scenario.clearance, corridor_available=False))):
        assert assess_lateral(vehicle, altered, state).geometry == Outcome.INFEASIBLE


def test_delay_and_speed_uncertainty_consumes_distance():
    vehicle, scenario, state, _ = nominal()
    state = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval(15, 25)),
                    latency_s=Interval(.1, .3))
    scenario = replace(scenario, driver_delay_s=Interval(1, 2))
    result = assess_lateral(vehicle, scenario, state)
    assert result.metrics["path_length_low_m"] == pytest.approx(90-5-25*(2+.2+.3))
    assert result.metrics["path_length_high_m"] == pytest.approx(90-5-15*(1+.2+.1))
    crossed = assess_lateral(vehicle, replace(scenario, available_distance_m=40), state)
    assert crossed.outcome == Outcome.UNKNOWN
    assert "uncertainty_crosses_zero_remaining_distance" in crossed.reasons
    assert assess_lateral(vehicle, replace(scenario, available_distance_m=10), state).outcome == Outcome.INFEASIBLE


def test_limit_equality_stays_unknown_and_small_perturbations_are_stable():
    vehicle, scenario, state, _ = nominal()
    state = replace(state, front_steering_rad=replace(state.front_steering_rad,
                    bounds=Interval.point(math.atan(2.8*.01))))
    scenario = replace(scenario, road_curvature_per_m=.01, target_offset_m=0,
                       clearance=replace(scenario.clearance, required_offset_m=0))
    vehicle = replace(vehicle, max_lateral_accel_mps2=4.0)
    assert assess_lateral(vehicle, scenario, state).outcome == Outcome.UNKNOWN  # v²*k = 4
    assert assess_lateral(replace(vehicle, max_lateral_accel_mps2=4.01), scenario, state).outcome == Outcome.FEASIBLE
    assert assess_lateral(replace(vehicle, max_lateral_accel_mps2=3.99), scenario, state).outcome == Outcome.INFEASIBLE


def test_initial_steering_uncertainty_and_mismatch_are_explicit_unknowns():
    vehicle, scenario, state, _ = nominal()
    for interval in (Interval(-.01, .01), Interval.point(.05)):
        changed = replace(state, front_steering_rad=replace(state.front_steering_rad, bounds=interval))
        result = assess_lateral(vehicle, scenario, changed)
        assert result.outcome == Outcome.UNKNOWN
        assert "transient_model" in result.reasons[0]


def test_steering_rate_constraint_is_checked():
    vehicle, scenario, state, _ = nominal()
    result = assess_lateral(replace(vehicle, max_steering_rate_rad_s=.001), scenario, state)
    assert result.dynamics == Outcome.INFEASIBLE
    assert "certified_constraint_violation:steering_rate" in result.reasons


@pytest.mark.parametrize("mu", [None, Interval(0, .8)])
def test_unknown_grip_or_grip_uncertainty_cannot_certify_feasibility(mu):
    vehicle, scenario, state, _ = nominal()
    assert assess_lateral(vehicle, replace(scenario, friction=mu), state).outcome == Outcome.UNKNOWN


def test_missing_stale_future_invalid_can_signals_and_disagreement():
    stamp = 1_000_000_000
    base = VehicleState(stamp, dict(VehicleSpeed=Decoded(0, 20, stamp, True),
                                   FrontWheelSteering=Decoded(0, 0, stamp, True)))
    def convert(s, **kwargs):
        return from_can(s, now_ns=stamp+100, max_age_ns=200, **kwargs)
    assert convert(base).speed_mps.evidence == Evidence.MEASURED
    stale = from_can(base, now_ns=stamp+201, max_age_ns=200)
    assert stale.speed_mps.evidence == Evidence.STALE
    assert convert(VehicleState()).speed_mps.evidence == Evidence.MISSING
    bad = VehicleState(signals=dict(base.signals, VehicleSpeed=Decoded(0, float("nan"), stamp, True)))
    assert convert(bad).speed_mps.evidence == Evidence.INVALID
    future = VehicleState(signals=dict(base.signals, VehicleSpeed=Decoded(0, 20, stamp+101, True)))
    assert convert(future).speed_mps.evidence == Evidence.FUTURE
    other = VehicleState(signals=dict(base.signals, VehicleSpeed=Decoded(0, 23, stamp, True)))
    assert convert(base, redundant=other, speed_error_mps=.5).speed_mps.evidence == Evidence.DISAGREEMENT
    overlapping = convert(base, redundant=other, speed_error_mps=2)
    assert overlapping.speed_mps.bounds == Interval(18, 25)


def test_real_dbc_adapter_explicit_units_and_steering_ratio():
    dbc = Dbc.parse('''BO_ 512 Dynamics: 4 ECU
 SG_ Speed : 0|16@1+ (0.01,0) [0|200] "km/h" ECU
 SG_ SWA : 16|16@1- (0.01,0) [-720|720] "deg" ECU
''')
    # 72 km/h; steering wheel 15 degrees, ratio 15 -> road wheel 1 degree.
    frame = Frame(512, bytes([0x20, 0x1c, 0xdc, 0x05]), 100)
    state = Replay(dbc, 1000).feed(frame)
    bindings = Bindings("Speed", "km/h", "SWA", "deg", "steering_wheel", 15)
    converted = from_can(state, now_ns=200, max_age_ns=100, bindings=bindings)
    assert converted.speed_mps.bounds.low == 20
    assert converted.front_steering_rad.bounds.low == pytest.approx(math.pi/180)
    with pytest.raises(ValueError):
        Bindings(steering_reference="steering_wheel")


def test_r3b_exact_parity_and_speed_friction_bounds():
    vehicle, scenario, state, braking = nominal()
    result = assess_stopping(state, scenario, braking)
    expected = stopping_distance_r3b_analytical(20, 8, 1.5, .1, .5, 1.5, 0, 0, 1, .8)
    assert result.metrics["stopping_distance_low_m"] == expected
    assert result.metrics["stopping_distance_high_m"] == expected
    state = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval(10, 30)))
    scenario = replace(scenario, friction=Interval(.2, 1.0))
    result = assess_stopping(state, scenario, braking)
    for v in np.linspace(10, 30, 13):
        for mu in np.linspace(.2, 1, 13):
            d = stopping_distance_r3b_analytical(v, 8, 1.5, .1, .5, 1.5, 0, 0, 1, mu)
            assert result.metrics["stopping_distance_low_m"] <= d <= result.metrics["stopping_distance_high_m"]
    assert assess_stopping(state, replace(scenario, road_curvature_per_m=.01), braking).outcome == Outcome.UNKNOWN


def test_neither_candidate_and_no_automatic_recommendation():
    vehicle, scenario, state, braking = nominal()
    result = assess_options(vehicle, replace(scenario, available_distance_m=20), state, braking)
    assert result.assessment == "neither_evaluated_candidate_feasible_under_assumptions"
    assert result.collision_avoidance == "not_validated"
    assert result.recommendation.startswith("none")


@pytest.mark.parametrize("longitudinal", list(Outcome))
@pytest.mark.parametrize("lateral", list(Outcome))
def test_decision_table_preserves_unknowns(longitudinal, lateral):
    result = combine(LongitudinalResult(longitudinal, None, ()),
                     LateralResult(lateral, lateral, lateral, ()))
    assert result.longitudinal.outcome == longitudinal and result.lateral.outcome == lateral
    assert result.collision_avoidance == "not_validated"
    if Outcome.FEASIBLE not in (longitudinal, lateral) and Outcome.UNKNOWN in (longitudinal, lateral):
        assert result.assessment == "insufficient_evidence_or_uncertainty"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_input_validation(value):
    with pytest.raises(ValueError):
        Vehicle(value, .3, .5, 4)
    with pytest.raises(ValueError):
        Interval(1, value)


def test_schema_example_roundtrip_and_unknown_key_rejected():
    data = json.loads(Path("lateral_recoverability/example.json").read_text())
    vehicle, scenario, state = load_config(data)
    result = assess_lateral(vehicle, scenario, state)
    assert result.outcome == Outcome.FEASIBLE
    assert json.loads(json.dumps(asdict(result), allow_nan=False))["collision_avoidance"] == "not_validated"
    data["unexpected"] = 1
    with pytest.raises(ValueError):
        load_config(data)


def test_numerical_domain_and_stationary_input():
    vehicle, scenario, state, _ = nominal()
    stationary = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval.point(0)))
    assert assess_lateral(vehicle, scenario, stationary).outcome == Outcome.UNKNOWN
    enormous = replace(scenario, driver_delay_s=Interval.point(1e308))
    result = assess_lateral(vehicle, enormous, state)
    assert result.outcome == Outcome.UNKNOWN
    json.dumps(asdict(result), allow_nan=False)
    with pytest.raises(ValueError):
        path_point(.5, 0, 3, 0)
    with pytest.raises(ValueError):
        demand_bounds(1, 10, 10, .1, 2.8, 10, 20)
    with pytest.raises(ValueError):
        replace(state, speed_mps=replace(state.speed_mps, age_s=1))


def test_replay_sweep_csv_is_deterministic(tmp_path):
    axes = dict(speed_mps=[10., 30.], available_distance_m=[30., 100.],
                data_mode=["complete", "missing_steering"])
    first, second = sweep(axes), sweep(axes)
    assert first == second
    assert all(r["synthetic_only"] for r in first)
    write_csv(tmp_path/"a.csv", first)
    write_csv(tmp_path/"b.csv", second)
    assert (tmp_path/"a.csv").read_bytes() == (tmp_path/"b.csv").read_bytes()
    assert all(r["lateral"] == "unknown" for r in first if r["data_mode"] == "missing_steering")


@pytest.mark.parametrize("ta,before,after", [(0, 0, .4), (.75, 2, .3), (1.5, 3, 0)])
def test_original_r3b_precontrol_policy_bounds_remain_valid(ta, before, after):
    _, scenario, state, braking = nominal()
    braking = replace(braking, t_authority_s=ta, a_before_authority_mps2=before,
                      a_after_authority_mps2=after)
    state = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval(1, 30)))
    scenario = replace(scenario, friction=Interval(.3, 1))
    result = assess_stopping(state, scenario, braking)
    for v in np.linspace(1, 30, 21):
        for mu in np.linspace(.3, 1, 11):
            d = stopping_distance_r3b_analytical(v, 8, 1.5, .1, .5, ta, before, after, 1, mu)
            assert result.metrics["stopping_distance_low_m"]-1e-12 <= d <= result.metrics["stopping_distance_high_m"]+1e-12


def test_sensitivity_directions_and_bicycle_steering_units():
    vehicle, scenario, state, _ = nominal()
    base = assess_lateral(vehicle, scenario, state).metrics
    short = assess_lateral(vehicle, replace(scenario, available_distance_m=75), state).metrics
    delayed = assess_lateral(vehicle, replace(scenario, driver_delay_s=Interval.point(2)), state).metrics
    longer_vehicle = assess_lateral(replace(vehicle, wheelbase_m=3.5), scenario, state).metrics
    assert short["curvature_upper_per_m"] > base["curvature_upper_per_m"]
    assert delayed["curvature_upper_per_m"] > base["curvature_upper_per_m"]
    assert longer_vehicle["steering_upper_rad"] > base["steering_upper_rad"]
    assert math.tan(base["steering_upper_rad"])/vehicle.wheelbase_m == pytest.approx(base["curvature_upper_per_m"])


@pytest.mark.parametrize("mode", ["missing_steering", "speed_disagreement", "uncertain_steering"])
def test_fault_experiments_do_not_promote_unknown_to_feasible(mode):
    vehicle, scenario, state, braking = synthetic_inputs(dict(data_mode=mode))
    result = assess_options(vehicle, scenario, state, braking)
    assert result.lateral.outcome == Outcome.UNKNOWN
    assert result.collision_avoidance == "not_validated"


def test_schema_formal_validation_when_available():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(Path("lateral_recoverability/config.schema.json").read_text())
    example = json.loads(Path("lateral_recoverability/example.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(example, schema)


def test_tiny_horizon_and_extreme_time_margin_fail_closed():
    vehicle, scenario, state, braking = nominal()
    tiny = replace(scenario, available_distance_m=5+20*1.7+1e-5)
    result = assess_lateral(vehicle, tiny, state)
    assert result.outcome == Outcome.UNKNOWN
    assert "outside_numerically_supported_domain" in result.reasons
    state = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval.point(1e-308)))
    result = assess_stopping(state, replace(scenario, available_distance_m=1e308), braking)
    assert result.outcome == Outcome.UNKNOWN
    json.dumps(asdict(result), allow_nan=False)
