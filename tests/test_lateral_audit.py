"""Acceptance cases added after the original 51-case lateral suite."""
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from automotive_can.dbc import Decoded, VehicleState
from lateral_recoverability.audit import attribution, collect, boundary_cases
from lateral_recoverability.can_adapter import from_can
from lateral_recoverability.decision import assess_options, assess_stopping, assess_combined_braking_steering
from lateral_recoverability.experiments import synthetic_inputs
from lateral_recoverability.kinematics import demand_bounds, path_point
from lateral_recoverability.schema import Evidence, Interval, Observation, State, load_config


@pytest.mark.parametrize("value", [None, "20", True, float("nan"), float("inf"), -float("inf"), 10**400])
def test_invalid_physical_values_become_unknown(value):
    raw = VehicleState(signals={"VehicleSpeed": Decoded(0, value, 100, True),
                               "FrontWheelSteering": Decoded(0, 0, 100, True)})
    state = from_can(raw, now_ns=100, max_age_ns=10)
    assert state.speed_mps.evidence == Evidence.INVALID
    v, s, _, b = synthetic_inputs({})
    result = assess_options(v, s, state, b)
    assert result.longitudinal.outcome == result.lateral.outcome == "unknown"
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("evidence", [Evidence.MISSING, Evidence.STALE, Evidence.INVALID, Evidence.FUTURE, Evidence.DISAGREEMENT])
def test_critical_steering_evidence_also_gates_braking(evidence):
    v, s, state, b = synthetic_inputs({})
    state = replace(state, front_steering_rad=Observation(None, evidence, "fault"))
    result = assess_options(v, s, state, b)
    assert result.longitudinal.outcome == result.lateral.outcome == "unknown"
    assert result.assessment == "insufficient_evidence_or_uncertainty"


@pytest.mark.parametrize("steering", [Interval(-.01, .01), Interval.point(.02)])
def test_steering_requires_joint_braking_model(steering):
    _, s, state, b = synthetic_inputs({})
    state = replace(state, front_steering_rad=replace(state.front_steering_rad, bounds=steering))
    result = assess_stopping(state, s, b)
    assert result.outcome == "unknown"
    assert result.reasons == ("nonzero_or_uncertain_steering_requires_joint_braking_model",)


@pytest.mark.parametrize("mutator", [
    lambda d: d["scenario"].update(driver_delay_s=None),
    lambda d: d["state"].update(speed_mps=None),
    lambda d: d["scenario"].update(clearance=[]),
    lambda d: d["scenario"].update(source=123),
    lambda d: d["state"]["speed_mps"].update(bounds={"low":2,"high":1}),
    lambda d: d["vehicle"].update(wheelbase_m=float("nan")),
])
def test_malformed_config_has_explicit_validation_error(mutator):
    data = json.loads(Path("lateral_recoverability/example.json").read_text())
    mutator(data)
    with pytest.raises(ValueError):
        load_config(data)


def test_direct_schema_types_and_nonfinite_helpers_reject():
    with pytest.raises(ValueError):
        Observation([1, 2], Evidence.MEASURED, "bad")
    with pytest.raises(ValueError):
        State(None, None, None)
    for value in (float("nan"), float("inf"), 1e-300):
        with pytest.raises(ValueError):
            path_point(.5, value, 3.5, 0)
        with pytest.raises(ValueError):
            demand_bounds(value, 100, 3.5, 0, 2.8, 10, 20)
    with pytest.raises(ValueError):
        demand_bounds(50, 100, 3.5, 0, 2.8, 20, 10)


def test_freshness_boundary_and_individual_validity():
    raw = VehicleState(signals={"VehicleSpeed": Decoded(0, 20, 100, True),
                               "FrontWheelSteering": Decoded(0, 0, 100, True)})
    assert from_can(raw, now_ns=110, max_age_ns=10).speed_mps.usable
    assert from_can(raw, now_ns=111, max_age_ns=10).speed_mps.evidence == Evidence.STALE
    raw.signals["FrontWheelSteering"] = Decoded(0, 0, 100, False)
    assert from_can(raw, now_ns=110, max_age_ns=10).front_steering_rad.evidence == Evidence.INVALID


def test_cross_candidate_cases_and_combined_request():
    cases = collect()
    for pair in [("feasible", "infeasible"), ("infeasible", "feasible"), ("infeasible", "infeasible"),
                 ("unknown", "feasible"), ("unknown", "unknown")]:
        assert any((c["longitudinal"]["outcome"], c["lateral"]["outcome"]) == pair for c in cases)
    assert all(c["collision_avoidance"] == "not_validated" and c["recommendation"].startswith("none") for c in cases)
    combined = assess_combined_braking_steering()
    assert combined.outcome == "unknown" and combined.collision_avoidance == "not_validated"
    missing = boundary_cases()["missing_clearance"]
    assert missing["lateral"]["outcome"] == "unknown"
    assert missing["collision_avoidance"] == "not_validated"


def test_unknown_attribution_and_historical_lateral_counts():
    cases = collect()
    result = attribution(cases, "lateral")
    baseline = json.loads(Path("lateral_recoverability/verification/pre_audit.json").read_text())
    assert result["unknown"] == 7366
    assert result["combinations"] == baseline["unknown_reason_combinations"]
    assert sum(c["count"] for c in result["primary_categories"].values()) == 7366
    assert result["primary_categories"]["missing_sensor_evidence"]["count"] == 1458
    assert result["overlapping_categories"]["missing_sensor_evidence"]["count"] == 2187
    assert result["primary_categories"]["stale_or_invalid_vehicle_state"]["count"] == 2916
    assert result["primary_categories"]["missing_road_or_obstacle_geometry"]["count"] == 0


@pytest.mark.parametrize("fault", ["duplicate_exposure", "missing_row", "extra_row", "wrong_participant"])
def test_corrected_r2b_assertion_still_rejects_bad_data(fault):
    spec = importlib.util.spec_from_file_location("r2b_acceptance", "tests/test_r2b.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = json.loads((Path(module.R2B_DIR)/"summary.json").read_text())
    trials = pd.read_csv(Path(module.R2B_DIR)/"trial_table.csv")
    module.test_exposure_order_and_participant_counts(summary, trials)
    if fault == "duplicate_exposure":
        trials.loc[0, "exposure"] = trials.loc[1, "exposure"]
    elif fault == "missing_row":
        trials = trials.iloc[1:]
    elif fault == "extra_row":
        trials = pd.concat([trials, trials.iloc[:1]])
    else:
        trials.loc[0, "participant_id"] = int(trials.participant_id.max())+1
    with pytest.raises(AssertionError):
        module.test_exposure_order_and_participant_counts(summary, trials)
