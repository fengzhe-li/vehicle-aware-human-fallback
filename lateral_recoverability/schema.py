"""SI-only validated input schema. None means unavailable, never a default estimate."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


def finite(value: float, name: str, minimum: float | None = None) -> None:
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


class Outcome(str, Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"


class Evidence(str, Enum):
    ASSUMED = "assumed"
    MEASURED = "measured"
    MISSING = "missing"
    STALE = "stale"
    INVALID = "invalid"
    DISAGREEMENT = "sensor_disagreement"
    FUTURE = "future_timestamp"


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    def __post_init__(self):
        finite(self.low, "interval.low")
        finite(self.high, "interval.high")
        if self.low > self.high:
            raise ValueError("interval.low must be <= interval.high")

    @classmethod
    def point(cls, value: float) -> Interval:
        return cls(value, value)


@dataclass(frozen=True)
class Observation:
    bounds: Interval | None
    evidence: Evidence
    source: str
    age_s: float = 0.0

    def __post_init__(self):
        finite(self.age_s, "age_s", 0.0)
        if not isinstance(self.evidence, Evidence) or not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("observation needs an Evidence enum and a nonempty source")
        if self.bounds is not None and not isinstance(self.bounds, Interval):
            raise ValueError("observation bounds must be an Interval or None")
        if self.evidence in (Evidence.ASSUMED, Evidence.MEASURED) and self.bounds is None:
            raise ValueError("usable evidence needs bounds")

    @property
    def usable(self) -> bool:
        return self.bounds is not None and self.evidence in (Evidence.ASSUMED, Evidence.MEASURED)


@dataclass(frozen=True)
class State:
    speed_mps: Observation
    front_steering_rad: Observation
    latency_s: Interval

    def __post_init__(self):
        if not isinstance(self.latency_s, Interval) or not all(
            isinstance(o, Observation) for o in (self.speed_mps, self.front_steering_rad)
        ):
            raise ValueError("state requires observations and a latency Interval")
        if self.latency_s.low < 0:
            raise ValueError("latency must be nonnegative")
        if self.latency_s.low+1e-12 < max(self.speed_mps.age_s, self.front_steering_rad.age_s):
            raise ValueError("latency must include the oldest observation age")
        if self.speed_mps.usable and self.speed_mps.bounds.low < 0:
            raise ValueError("reverse motion is outside the model")
        if self.front_steering_rad.usable and max(
            abs(self.front_steering_rad.bounds.low), abs(self.front_steering_rad.bounds.high)
        ) >= math.pi / 2:
            raise ValueError("front road-wheel steering must be strictly inside +/- pi/2")


@dataclass(frozen=True)
class Vehicle:
    wheelbase_m: float
    max_steering_rad: float
    max_steering_rate_rad_s: float
    max_lateral_accel_mps2: float

    def __post_init__(self):
        for name, value in vars(self).items():
            finite(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_steering_rad >= math.pi / 2:
            raise ValueError("steering limit must be strictly below pi/2")


@dataclass(frozen=True)
class Clearance:
    """External vehicle-centre corridor, already eroded for footprint and margins.

    These are explicit scenario assumptions, not a perception/collision checker.
    The corridor must cover the entire delay, path, and terminal continuation.
    """
    center_min_m: float
    center_max_m: float
    required_offset_m: float
    longitudinal_buffer_m: float
    corridor_available: bool | None
    source: str

    def __post_init__(self):
        finite(self.center_min_m, "center_min_m")
        finite(self.center_max_m, "center_max_m")
        finite(self.required_offset_m, "required_offset_m", 0)
        finite(self.longitudinal_buffer_m, "longitudinal_buffer_m", 0)
        if self.center_min_m > self.center_max_m or not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("clearance needs an ordered corridor and provenance")
        if self.corridor_available is not None and type(self.corridor_available) is not bool:
            raise ValueError("corridor_available must be true, false or null")


@dataclass(frozen=True)
class Scenario:
    road_curvature_per_m: float | None
    available_distance_m: float | None
    target_offset_m: float
    driver_delay_s: Interval
    steering_delay_s: Interval
    friction: Interval | None
    clearance: Clearance | None
    source: str

    def __post_init__(self):
        if self.road_curvature_per_m is not None:
            finite(self.road_curvature_per_m, "road_curvature_per_m")
        if self.available_distance_m is not None:
            finite(self.available_distance_m, "available_distance_m", 0)
        finite(self.target_offset_m, "target_offset_m")
        if not all(isinstance(x, Interval) for x in (self.driver_delay_s, self.steering_delay_s)):
            raise ValueError("driver and steering delays require explicit Intervals")
        if self.friction is not None and not isinstance(self.friction, Interval):
            raise ValueError("friction must be an Interval or None")
        if self.clearance is not None and not isinstance(self.clearance, Clearance):
            raise ValueError("clearance must be a Clearance or None")
        if self.driver_delay_s.low < 0 or self.steering_delay_s.low < 0:
            raise ValueError("delays must be nonnegative")
        if self.friction is not None and self.friction.low < 0:
            raise ValueError("friction must be nonnegative")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("scenario provenance is required")


def _load_config(data: dict) -> tuple[Vehicle, Scenario, State]:
    """Strict constructor; unknown keys and missing keys raise, rather than default."""
    if set(data) != {"vehicle", "scenario", "state"}:
        raise ValueError("configuration requires exactly vehicle, scenario and state")
    scenario = dict(data["scenario"])
    for field in ("driver_delay_s", "steering_delay_s", "friction"):
        scenario[field] = Interval(**scenario[field]) if scenario[field] is not None else None
    scenario["clearance"] = Clearance(**scenario["clearance"]) if scenario["clearance"] is not None else None
    state = dict(data["state"])
    for field in ("speed_mps", "front_steering_rad"):
        observation = dict(state[field])
        observation["bounds"] = Interval(**observation["bounds"]) if observation["bounds"] is not None else None
        observation["evidence"] = Evidence(observation["evidence"])
        state[field] = Observation(**observation)
    state["latency_s"] = Interval(**state["latency_s"])
    return Vehicle(**data["vehicle"]), Scenario(**scenario), State(**state)


def load_config(data: dict) -> tuple[Vehicle, Scenario, State]:
    """Reject malformed configuration explicitly, including missing nested fields."""
    try:
        return _load_config(data)
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError(f"malformed configuration: {exc}") from exc
