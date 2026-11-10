"""Explicit CAN signal binding and evidence gates without changing automotive_can."""
from __future__ import annotations

from dataclasses import dataclass
import math

from automotive_can.dbc import VehicleState
from .schema import Evidence, Interval, Observation, State, finite


@dataclass(frozen=True)
class Bindings:
    speed_signal: str = "VehicleSpeed"
    speed_unit: str = "m/s"
    steering_signal: str = "FrontWheelSteering"
    steering_unit: str = "rad"
    steering_reference: str = "road_wheel"
    steering_ratio: float | None = None

    def __post_init__(self):
        if self.speed_unit not in ("m/s", "km/h") or self.steering_unit not in ("rad", "deg"):
            raise ValueError("unsupported units: supply declared m/s or km/h and rad or deg")
        if self.steering_reference not in ("road_wheel", "steering_wheel"):
            raise ValueError("steering reference must be explicit")
        if self.steering_reference == "steering_wheel" and self.steering_ratio is None:
            raise ValueError("steering-wheel signals require a calibrated steering ratio")
        if self.steering_ratio is not None:
            finite(self.steering_ratio, "steering_ratio")
            if self.steering_ratio <= 0:
                raise ValueError("steering ratio must be positive")


def _observation(state: VehicleState, name: str, scale: float, error: float,
                 now_ns: int, max_age_ns: int, source: str) -> Observation:
    item = state.signals.get(name)
    provenance = f"{source}:{name}"
    if item is None:
        return Observation(None, Evidence.MISSING, provenance)
    if type(item.timestamp_ns) is not int or not 0 <= item.timestamp_ns <= 2**63-1:
        return Observation(None, Evidence.INVALID, provenance)
    if item.timestamp_ns > now_ns:
        return Observation(None, Evidence.FUTURE, provenance)
    age = (now_ns-item.timestamp_ns)/1e9
    try:
        finite(item.physical, "CAN physical value")
    except ValueError:
        return Observation(None, Evidence.INVALID, provenance, age)
    if item.valid is not True:
        return Observation(None, Evidence.INVALID, provenance, age)
    if now_ns-item.timestamp_ns > max_age_ns:
        return Observation(None, Evidence.STALE, provenance, age)
    value = item.physical*scale
    if not all(math.isfinite(x) for x in (value, value-error, value+error)):
        return Observation(None, Evidence.INVALID, provenance, age)
    return Observation(Interval(value-error, value+error), Evidence.MEASURED, provenance, age)


def _fuse(primary: Observation, secondary: Observation | None) -> Observation:
    if secondary is None:
        return primary
    if not primary.usable:
        return primary
    if not secondary.usable:
        return secondary
    p, s = primary.bounds, secondary.bounds
    provenance = primary.source+"; "+secondary.source
    age = max(primary.age_s, secondary.age_s)
    if max(p.low, s.low) > min(p.high, s.high):
        return Observation(None, Evidence.DISAGREEMENT, provenance, age)
    # Hull rather than an unjustified independent-error variance reduction.
    return Observation(Interval(min(p.low, s.low), max(p.high, s.high)),
                       Evidence.MEASURED, provenance, age)


def from_can(state: VehicleState, *, now_ns: int, max_age_ns: int, bindings: Bindings = Bindings(),
             speed_error_mps: float = 0.0, steering_error_rad: float = 0.0,
             redundant: VehicleState | None = None) -> State:
    """Convert declared units to SI; uncertainties are absolute error bounds in SI.

    Signal timestamps, not the adapter's aggregate valid flag, determine evidence.
    A supplied redundant sensor must be usable and agree within the given bounds.
    Road geometry, grip, footprint clearance and driver delays remain external.
    """
    if type(now_ns) is not int or type(max_age_ns) is not int or not (0 <= now_ns <= 2**63-1 and 0 <= max_age_ns <= 2**63-1):
        raise ValueError("now_ns and max_age_ns must be nonnegative integers on one monotonic clock")
    finite(speed_error_mps, "speed_error_mps", 0)
    finite(steering_error_rad, "steering_error_rad", 0)
    speed_scale = 1/3.6 if bindings.speed_unit == "km/h" else 1.0
    steering_scale = math.pi/180 if bindings.steering_unit == "deg" else 1.0
    if bindings.steering_reference == "steering_wheel":
        steering_scale /= bindings.steering_ratio
    observations = []
    for name, scale, error in ((bindings.speed_signal, speed_scale, speed_error_mps),
                               (bindings.steering_signal, steering_scale, steering_error_rad)):
        p = _observation(state, name, scale, error, now_ns, max_age_ns, "primary_CAN")
        s = None if redundant is None else _observation(
            redundant, name, scale, error, now_ns, max_age_ns, "redundant_CAN")
        observations.append(_fuse(p, s))
    speed, steering = observations
    if speed.usable and speed.bounds.low < 0:
        speed = Observation(None, Evidence.INVALID, speed.source, speed.age_s)
    if steering.usable and max(abs(steering.bounds.low), abs(steering.bounds.high)) >= math.pi/2:
        steering = Observation(None, Evidence.INVALID, steering.source, steering.age_s)
    # Consume the oldest channel age as a conservative delay before response.
    age = max(speed.age_s, steering.age_s)
    return State(speed, steering, Interval.point(age))
