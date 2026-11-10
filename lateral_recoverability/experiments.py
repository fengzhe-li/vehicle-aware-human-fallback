"""Reproducible synthetic scenario sweeps, OAT sensitivity, and diagnostic plots."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform

import numpy as np

from automotive_can.dbc import Decoded, VehicleState
from .can_adapter import from_can
from .decision import BrakingAssumptions, assess_options
from .kinematics import path_point
from .schema import Clearance, Interval, Scenario, Vehicle, load_config

AXES = {
    "speed_mps": [10.0, 20.0, 30.0],
    "road_curvature_per_m": [-0.01, 0.0, 0.01],
    "available_distance_m": [30.0, 60.0, 100.0],
    "max_steering_rad": [0.04, 0.2, 0.4],
    "friction": [0.3, 0.6, 0.9],
    "driver_delay_s": [0.5, 1.5, 3.0],
    "sensor_latency_s": [0.0, 0.1, 0.4],
    "data_mode": ["complete", "missing_steering", "speed_disagreement", "uncertain_steering"],
}
BASE = dict(speed_mps=20.0, road_curvature_per_m=0.0, available_distance_m=90.0,
            max_steering_rad=0.35, friction=0.8, driver_delay_s=1.5,
            sensor_latency_s=0.0, data_mode="complete")


def synthetic_inputs(parameters: dict):
    """CAN-compatible synthetic observations with known timestamp and provenance."""
    p = dict(BASE, **parameters)
    now = 10_000_000_000
    stamp = now-round(p["sensor_latency_s"]*1e9)
    steering = math.atan(2.8*p["road_curvature_per_m"])
    signals = dict(VehicleSpeed=Decoded(0, p["speed_mps"], stamp, True),
                   FrontWheelSteering=Decoded(0, steering, stamp, True))
    if p["data_mode"] == "missing_steering":
        signals.pop("FrontWheelSteering")
    redundant = None
    if p["data_mode"] == "speed_disagreement":
        redundant = VehicleState(stamp, dict(signals, VehicleSpeed=Decoded(0, p["speed_mps"]+4, stamp, True)))
    state = from_can(VehicleState(stamp, signals), now_ns=now, max_age_ns=250_000_000,
                     speed_error_mps=0.5,
                     steering_error_rad=0.01 if p["data_mode"] == "uncertain_steering" else 0,
                     redundant=redundant)
    vehicle = Vehicle(2.8, p["max_steering_rad"], 0.5, 4.0)
    scenario = Scenario(
        p["road_curvature_per_m"], p["available_distance_m"], 3.5,
        Interval.point(p["driver_delay_s"]), Interval.point(0.2), Interval.point(p["friction"]),
        Clearance(-1.0, 5.0, 3.5, 5.0, True,
                  "synthetic eroded free corridor including delay and terminal continuation"),
        "synthetic constant-curvature stationary-obstacle scenario")
    # This sweep explicitly sets braking and steering response delays equal;
    # that is a scenario choice, not inference from steering telemetry.
    braking = BrakingAssumptions(8.0, p["driver_delay_s"], p["driver_delay_s"], 0.1, 0.5)
    return vehicle, scenario, state, braking


def row(parameters: dict) -> dict:
    p = dict(BASE, **parameters)
    vehicle, scenario, state, braking = synthetic_inputs(p)
    assessment = assess_options(vehicle, scenario, state, braking)
    return dict(p, synthetic_only=True, lateral=assessment.lateral.outcome.value,
                geometry=assessment.lateral.geometry.value, dynamics=assessment.lateral.dynamics.value,
                longitudinal=assessment.longitudinal.outcome.value,
                assessment=assessment.assessment, speed_evidence=state.speed_mps.evidence.value,
                steering_evidence=state.front_steering_rad.evidence.value,
                reasons=";".join(assessment.lateral.reasons),
                collision_avoidance=assessment.collision_avoidance)


def sweep(axes: dict = AXES) -> list[dict]:
    return [row(dict(zip(axes, values))) for values in itertools.product(*axes.values())]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sensitivity() -> list[dict]:
    ranges = dict(speed_mps=np.linspace(5, 40, 25), road_curvature_per_m=np.linspace(-0.03, 0.03, 25),
                  available_distance_m=np.linspace(20, 160, 25), max_steering_rad=np.linspace(0.01, 0.5, 25),
                  friction=np.linspace(0.05, 1.0, 25), driver_delay_s=np.linspace(0, 4, 25),
                  sensor_latency_s=np.linspace(0, 0.5, 25))
    results = []
    for parameter, values in ranges.items():
        for value in values:
            parameters = dict(BASE, **{parameter: float(value)})
            result = row(parameters)
            results.append(dict(parameter=parameter, value=float(value), **result))
    return results


def plots(output: Path, sensitivities: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    labels = {"infeasible": 0, "unknown": 1, "feasible": 2}
    colors = ["#bd4f46", "#e0ba61", "#407eab"]
    speeds, distances = np.linspace(5, 40, 50), np.linspace(20, 160, 70)
    values = [[labels[row(dict(speed_mps=float(v), available_distance_m=float(d)))["lateral"]]
               for d in distances] for v in speeds]
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    im = ax.imshow(values, origin="lower", aspect="auto",
                   extent=[distances[0], distances[-1], speeds[0], speeds[-1]],
                   cmap=ListedColormap(colors), vmin=-0.5, vmax=2.5, interpolation="nearest")
    ax.set(xlabel="Available road distance (m)", ylabel="Initial speed (m/s)",
           title="Synthetic lateral candidate: conservative feasibility")
    bar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2])
    bar.ax.set_yticklabels(["Infeasible", "Unknown", "Conditionally feasible"])
    fig.text(0.01, -0.04, "Straight road; 3.5 m shift; 1.5 s driver delay; μ=0.8. No collision-avoidance validation.", fontsize=9)
    fig.savefig(output/"feasibility_map.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(4, 2, figsize=(11, 10), constrained_layout=True)
    for ax, parameter in zip(axes.flat, dict.fromkeys(item["parameter"] for item in sensitivities)):
        subset = [item for item in sensitivities if item["parameter"] == parameter]
        ax.scatter([r["value"] for r in subset], [labels[r["lateral"]] for r in subset],
                   c=[colors[labels[r["lateral"]]] for r in subset], s=22)
        ax.set(xlabel=parameter, yticks=[0, 1, 2], yticklabels=["Infeasible", "Unknown", "Feasible"], ylim=(-.4, 2.4))
        ax.grid(alpha=.2)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0, .8, "Synthetic one-at-a-time sensitivity\nOther inputs held at BASE.\nFeasible = conditional path certificate.\nMissing/stale evidence remains unknown.\nCurvature sweep assumes road-following\ninitial steering for each road.", va="top")
    fig.suptitle("Lateral candidate sensitivity — model assumptions only")
    fig.savefig(output/"sensitivity.png", dpi=150)
    plt.close(fig)

    samples = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for k in (-.01, 0, .01):
        points = [path_point(float(u), 60.0, 3.5, k) for u in np.linspace(0, 1, 301)]
        samples.extend(dict(synthetic_only=True, road_curvature_per_m=k, **point) for point in points)
        axes[0].plot([p["x_m"] for p in points], [p["y_m"] for p in points], label=f"κ road={k:g}/m")
        axes[1].plot([p["road_station_m"] for p in points],
                     [p["curvature_per_m"] for p in points], label=f"κ road={k:g}/m")
    axes[0].set(xlabel="x (m)", ylabel="y (m)", title="Rear-axle paths; no obstacle map")
    axes[0].axis("equal")
    axes[1].set(xlabel="Road station (m)", ylabel="Path curvature (1/m)", title="Exact geometric curvature")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.savefig(output/"path_geometry.png", dpi=150)
    plt.close(fig)
    write_csv(output/"path_samples.csv", samples)


def run(output: Path, config: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    vehicle, scenario, state = load_config(json.loads(config.read_text()))
    example = assess_options(vehicle, scenario, state, None)
    (output/"example_result.json").write_text(json.dumps(asdict(example), indent=2, allow_nan=False)+"\n")
    rows, sensitivities = sweep(), sensitivity()
    write_csv(output/"scenarios.csv", rows)
    write_csv(output/"sensitivity.csv", sensitivities)
    plots(output, sensitivities)
    package = Path(__file__).parent
    produced = ("example_result.json", "scenarios.csv", "sensitivity.csv", "path_samples.csv",
                "feasibility_map.png", "sensitivity.png", "path_geometry.png")
    summary = dict(
        synthetic_only=True, collision_avoidance="not_validated",
        n_scenarios=len(rows), lateral_counts=dict(sorted(Counter(r["lateral"] for r in rows).items())),
        longitudinal_counts=dict(sorted(Counter(r["longitudinal"] for r in rows).items())),
        decision_counts=dict(sorted(Counter(r["assessment"] for r in rows).items())),
        axes=AXES, fixed_baseline=BASE, example_config=json.loads(config.read_text()),
        heatmap_grid=dict(speed_mps=[5, 40, 50], distance_m=[20, 160, 70],
                          convention="[minimum, maximum, number of evenly spaced points]"),
        sweep_constants=dict(wheelbase_m=2.8, max_lateral_accel_mps2=4.0,
                             steering_rate_rad_s=0.5, steering_delay_s=0.2, target_offset_m=3.5,
                             speed_error_mps=0.5, freshness_limit_s=0.25, longitudinal_buffer_m=5.0,
                             corridor_center_bounds_m=[-1.0, 5.0], braking_a_max_mps2=8.0,
                             brake_delay_s=0.1, brake_buildup_s=0.5, standstill_margin_m=2.0),
        method="analytic conservative curvature and steering-rate bounds; no sampled feasibility certification",
        environment=dict(python=platform.python_version(), numpy=np.__version__),
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.glob("*.py"))},
        artifact_sha256={name: hashlib.sha256((output/name).read_bytes()).hexdigest()
                         for name in sorted(produced)},
    )
    (output/"summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("lateral_recoverability/artifacts"))
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("example.json"),
                        help="single example configuration; sweep axes and BASE are recorded separately")
    args = parser.parse_args()
    summary = run(args.output, args.config)
    print(json.dumps({key: summary[key] for key in ("n_scenarios", "lateral_counts", "longitudinal_counts")}, indent=2))


if __name__ == "__main__":
    main()
