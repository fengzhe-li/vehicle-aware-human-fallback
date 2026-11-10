"""Reproduce reason attribution without treating multi-label counts as a partition."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
import itertools
import json
from pathlib import Path

from .decision import assess_options, assess_combined_braking_steering
from .experiments import AXES, synthetic_inputs, write_csv
from .schema import Interval

CATEGORIES = (
    "missing_sensor_evidence", "stale_or_invalid_vehicle_state", "sensor_disagreement",
    "steering_uncertainty", "missing_road_or_obstacle_geometry",
    "combined_braking_steering_uncertainty", "missing_model_assumptions",
    "overlapping_constraint_bounds", "uncertain_remaining_distance", "r3b_parameter_sensitive", "other",
)


def category(reason: str) -> str:
    if reason in ("speed:missing", "steering:missing"):
        return "missing_sensor_evidence"
    if reason.startswith(("speed:", "steering:")):
        return "sensor_disagreement" if "disagreement" in reason else "stale_or_invalid_vehicle_state"
    if "joint" in reason or "simultaneous_braking" in reason:
        return "combined_braking_steering_uncertainty"
    if "initial_steering" in reason:
        return "steering_uncertainty"
    if "clearance" in reason or "road_geometry" in reason or "corridor_availability" in reason:
        return "missing_road_or_obstacle_geometry"
    if "missing_" in reason:
        return "missing_model_assumptions"
    if reason == "unchanged_R3B_conditional_braking_model":
        return "r3b_parameter_sensitive"
    if reason == "bounds_overlap_constraints_or_numerical_boundary":
        return "overlapping_constraint_bounds"
    if reason == "uncertainty_crosses_zero_remaining_distance":
        return "uncertain_remaining_distance"
    return "other"


def attribution(cases: list[dict], candidate: str) -> dict:
    unknown = [c for c in cases if c[candidate]["outcome"] == "unknown"]
    primary, overlapping, raw_primary, raw_overlap = Counter(), Counter(), Counter(), Counter()
    combinations = Counter()
    representatives = {}
    for case in unknown:
        reasons = case[candidate]["reasons"]
        # First emitted reason is operational gate order, not causal importance.
        primary[category(reasons[0])] += 1
        raw_primary[reasons[0]] += 1
        raw_overlap.update(set(reasons))
        overlapping.update({category(r) for r in reasons})
        combinations[";".join(reasons)] += 1
        for reason in reasons:
            representatives.setdefault(reason, case)
    def counts(counter, keys):
        return {key: dict(count=counter[key], percent_unknown=round(100*counter[key]/len(unknown), 6) if unknown else 0,
                          percent_all=round(100*counter[key]/len(cases), 6) if cases else 0)
                for key in keys}
    return dict(total=len(cases), unknown=len(unknown),
                primary_categories=counts(primary, CATEGORIES),
                overlapping_categories=counts(overlapping, CATEGORIES),
                primary_reasons=counts(raw_primary, sorted(raw_primary)),
                overlapping_reasons=counts(raw_overlap, sorted(raw_overlap)),
                combinations=dict(sorted(combinations.items())), representatives=representatives)


def collect() -> list[dict]:
    cases = []
    for case_id, values in enumerate(itertools.product(*AXES.values()), 1):
        parameters = dict(zip(AXES, values))
        decision = assess_options(*synthetic_inputs(parameters))
        cases.append(dict(case_id=case_id, parameters=parameters, **asdict(decision)))
    return cases


def boundary_cases() -> dict:
    v, scenario, state, braking = synthetic_inputs({})
    exact = replace(state, speed_mps=replace(state.speed_mps, bounds=Interval.point(20)))
    horizon = 5+20*(1.5+.2)
    variants = {
        "missing_road": (replace(scenario, road_curvature_per_m=None), state, braking),
        "missing_distance": (replace(scenario, available_distance_m=None), state, braking),
        "missing_clearance": (replace(scenario, clearance=None), state, braking),
        "unknown_corridor": (replace(scenario, clearance=replace(scenario.clearance, corridor_available=None)), state, braking),
        "missing_grip": (replace(scenario, friction=None), state, braking),
        "missing_braking_assumptions": (scenario, state, None),
        "zero_remaining_distance": (replace(scenario, available_distance_m=horizon), exact, braking),
        "tiny_positive_horizon": (replace(scenario, available_distance_m=horizon+1e-5), exact, braking),
        "zero_speed": (scenario, replace(exact, speed_mps=replace(exact.speed_mps, bounds=Interval.point(0))), braking),
    }
    results = {name: asdict(assess_options(v, s, x, b)) for name, (s, x, b) in variants.items()}
    results["simultaneous_braking_steering"] = asdict(assess_combined_braking_steering())
    return results


def report() -> tuple[dict, list[dict]]:
    cases = collect()
    result = dict(
        interpretation="Synthetic scenario frequencies, not probabilities. Primary=first emitted reason; overlaps count a case once per reason/category. Early returns can mask later gates; no counterfactual reasons are invented.",
        lateral=attribution(cases, "lateral"), longitudinal=attribution(cases, "longitudinal"),
        counts={name: dict(Counter(c[name]["outcome"] for c in cases)) for name in ("lateral", "longitudinal")},
        decision_counts=dict(Counter(c["assessment"] for c in cases)),
        unknown_input_conditions={axis: dict(Counter(str(c["parameters"][axis]) for c in cases
            if c["lateral"]["outcome"] == "unknown")) for axis in ("data_mode", "sensor_latency_s")},
        simultaneous=dict(count=len(cases), percent_all=100, **asdict(assess_combined_braking_steering())),
        coverage_gaps="Original grid has no missing road/clearance/grip, invalid/future signal or missing braking assumptions; zero reason counts do not establish coverage. Supplementary boundaries are outside the 8,748 denominator.",
        supplementary_boundaries=boundary_cases(),
    )
    return result, cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("lateral_recoverability/verification/audit"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result, cases = report()
    (args.output/"unknown_analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    write_csv(args.output/"case_reasons.csv", [dict(case_id=c["case_id"], **c["parameters"],
        lateral=c["lateral"]["outcome"], lateral_primary=c["lateral"]["reasons"][0],
        lateral_reasons=";".join(c["lateral"]["reasons"]),
        longitudinal=c["longitudinal"]["outcome"], longitudinal_reasons=";".join(c["longitudinal"]["reasons"]),
        assessment=c["assessment"], collision_avoidance=c["collision_avoidance"]) for c in cases])
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
