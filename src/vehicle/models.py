"""Vehicle response model and profile definitions.

Per vehicle_response_model.md:
- Three free parameters: t_delay, t_buildup, v_rolloff (v_threshold, floor).
- Held-constant parameter: a_max.
- a_coast: active during uncommanded withdrawal phase under W1 (docs/CAUSAL_MODEL.md).
- Derived/monitored quantity: peak ramp jerk = a_max / t_buildup.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np

from src.handover.models import PreControlProfile, WithdrawalPolicy


@dataclass(frozen=True)
class VehicleResponseConfig:
    """Configuration for vehicle transient brake-response architecture.

    All units are SI: seconds (s), metres per second squared (m/s^2),
    metres per second (m/s).

    Parameters
    ----------
    t_delay : float
        Brake actuation delay time in seconds (t2).
        Literature range for friction baseline is 0.05-0.17 s (Paquette & Porter).
    t_buildup : float
        Linear deceleration ramp build-up time in seconds (t3).
    a_max : float
        Maximum achievable deceleration magnitude (m/s^2). Must be positive.
    v_rolloff : bool
        Whether low-speed regenerative torque roll-off is active.
    v_threshold : float
        Speed threshold below which roll-off begins (m/s).
    floor : float
        Residual deceleration fraction as v -> 0 (dimensionless, in [0, 1]).
    a_coast : float
        Deceleration magnitude during uncommanded coast under W1 (m/s^2).
    """

    t_delay: float
    t_buildup: float
    a_max: float
    v_rolloff: bool = False
    v_threshold: float = 0.0
    floor: float = 1.0
    a_coast: float = 0.0

    def __post_init__(self) -> None:
        if self.t_delay < 0.0:
            raise ValueError(f"t_delay must be non-negative, got {self.t_delay}")
        if self.t_buildup < 0.0:
            raise ValueError(f"t_buildup must be non-negative, got {self.t_buildup}")
        if self.a_max <= 0.0:
            raise ValueError(f"a_max must be strictly positive, got {self.a_max}")
        if self.a_coast < 0.0:
            raise ValueError(f"a_coast must be non-negative, got {self.a_coast}")
        if self.v_rolloff:
            if self.v_threshold <= 0.0:
                raise ValueError(f"v_threshold must be positive when v_rolloff is active, got {self.v_threshold}")
            if not (0.0 <= self.floor <= 1.0):
                raise ValueError(f"floor must be in [0, 1], got {self.floor}")

    @property
    def peak_ramp_jerk(self) -> Optional[float]:
        """Nominal linear ramp jerk magnitude da/dt (m/s^3).

        Returns None if t_buildup == 0 (step transition).
        """
        if self.t_buildup > 0.0:
            return self.a_max / self.t_buildup
        return None


def calculate_rolloff(v: float, v_threshold: float, floor: float) -> float:
    """Compute low-speed roll-off multiplier rolloff(v).

    rolloff(v) = 1.0                                   if v >= v_threshold
    rolloff(v) = floor + (1.0 - floor) * v / v_threshold if v < v_threshold

    Parameters
    ----------
    v : float
        Current vehicle speed (m/s).
    v_threshold : float
        Threshold speed below which roll-off activates (m/s).
    floor : float
        Minimum deceleration fraction approaching standstill.

    Returns
    -------
    float
        Deceleration scaling multiplier in [floor, 1.0].
    """
    if v >= v_threshold:
        return 1.0
    if v <= 0.0:
        return floor
    return float(floor + (1.0 - floor) * (v / v_threshold))


GRAVITY = 9.81  # m/s^2


def effective_braking_deceleration(a_max: float, u_brake: float = 1.0, road_friction: Optional[float] = None,
                                   rolloff: float = 1.0) -> float:
    """Achievable steady braking deceleration magnitude (m/s^2), R3B corrections A and B.

    requested = u_brake * a_max * rolloff   (commanded fraction of vehicle capability)
    achieved  = min(requested, road_friction * g)   (tyre-road friction limit)

    road_friction=None means no friction cap (legacy behaviour). Returns a positive magnitude;
    the caller applies the negative sign.
    """
    if not (0.0 <= u_brake <= 1.0):
        raise ValueError(f"u_brake must be in [0, 1], got {u_brake}")
    requested = u_brake * a_max * rolloff
    if road_friction is None:
        return requested
    if road_friction <= 0.0:
        raise ValueError(f"road_friction must be positive, got {road_friction}")
    return min(requested, road_friction * GRAVITY)


def calculate_acceleration(
    t: float,
    v: float,
    vehicle: VehicleResponseConfig,
    withdrawal: WithdrawalPolicy = WithdrawalPolicy.W0,
    t_reaction: float = 1.0,
    *,
    u_brake: float = 1.0,
    road_friction: Optional[float] = None,
    t_authority: Optional[float] = None,
    pre_control: Optional["PreControlProfile"] = None,
) -> float:
    """Compute instantaneous vehicle acceleration a(t) at time t and speed v.

    Physical sign convention:
    - Deceleration / braking / coasting produces negative acceleration: a <= 0.
    - Automation cruise produces zero net longitudinal acceleration: a = 0.

    Phases:
    1. 0 <= t < t_reaction (t_reaction = effective human control):
       - legacy W0: a(t) = 0.0 (automation holds steady speed v0).
       - legacy W1: a(t) = -a_coast (immediate withdrawal coasting).
       - R3B pre_control: -a_before_authority for t < t_authority, else -a_after_authority.
    2. t_reaction <= t < t_reaction + t_delay:
       - a(t) = 0.0 (human brake command active, hydraulic/actuation delay).
    3. t_reaction + t_delay <= t < t_reaction + t_delay + t_buildup:
       - Linear ramp: s = (t - t_reaction - t_delay) / t_buildup
       - a(t) = -a_eff * s, a_eff = min(u_brake * a_max * rolloff(v), road_friction * g)
    4. t >= t_reaction + t_delay + t_buildup:
       - Steady braking: a(t) = -a_eff
    With the defaults (u_brake = 1, road_friction = None) a_eff = a_max * rolloff(v),
    i.e. the pre-R3B saturated-braking model exactly.

    Parameters
    ----------
    t : float
        Current time in seconds relative to TOR.
    v : float
        Current vehicle velocity in m/s.
    vehicle : VehicleResponseConfig
        Vehicle response parameters.
    withdrawal : WithdrawalPolicy
        Automation withdrawal policy (W0 or W1).
    t_reaction : float
        Human reaction time in seconds.

    Returns
    -------
    float
        Longitudinal acceleration in m/s^2 (non-positive during deceleration).
    """
    if v <= 0.0:
        return 0.0

    # Phase 1: Pre-reaction interval [0, t_reaction)
    if t < t_reaction:
        if pre_control is not None:
            # R3B: automation command before authority transfer, vehicle-only response after it
            if t_authority is None:
                raise ValueError("pre_control requires t_authority")
            return -(pre_control.a_before_authority if t < t_authority else pre_control.a_after_authority)
        if withdrawal == WithdrawalPolicy.W0:
            return 0.0
        elif withdrawal == WithdrawalPolicy.W1:
            return -vehicle.a_coast
        else:
            raise ValueError(f"Unknown withdrawal policy: {withdrawal}")

    # Phase 2: Actuation delay interval [t_reaction, t_reaction + t_delay)
    t_delay_end = t_reaction + vehicle.t_delay
    if t < t_delay_end:
        return 0.0

    # Phase 3 & 4: Deceleration build-up and steady braking
    if vehicle.t_buildup > 0.0:
        s = min(1.0, max(0.0, (t - t_delay_end) / vehicle.t_buildup))
    else:
        s = 1.0

    if vehicle.v_rolloff:
        r = calculate_rolloff(v, vehicle.v_threshold, vehicle.floor)
    else:
        r = 1.0

    return -effective_braking_deceleration(vehicle.a_max, u_brake, road_friction, r) * s


def create_r0_profile(
    t_delay: float = 0.10,
    a_max: float = 8.5,
) -> VehicleResponseConfig:
    """Create reference profile R0 (instantaneous build-up, pure friction, no roll-off)."""
    return VehicleResponseConfig(
        t_delay=t_delay,
        t_buildup=0.0,
        a_max=a_max,
        v_rolloff=False,
        a_coast=0.0,
    )


def create_r2_profile(
    t_delay: float = 0.10,
    t_buildup: float = 0.50,
    a_max: float = 8.5,
) -> VehicleResponseConfig:
    """Create delayed build-up profile R2 (linear ramp build-up, pure friction, no roll-off)."""
    return VehicleResponseConfig(
        t_delay=t_delay,
        t_buildup=t_buildup,
        a_max=a_max,
        v_rolloff=False,
        a_coast=0.0,
    )


def create_r1_profile(
    t_delay: float = 0.05,
    t_buildup: float = 0.0,
    a_max: float = 8.5,
    v_threshold: float = 5.0,
    floor: float = 0.2,
) -> VehicleResponseConfig:
    """Create regen-onset profile R1 (shorter delay, low-speed roll-off active)."""
    return VehicleResponseConfig(
        t_delay=t_delay,
        t_buildup=t_buildup,
        a_max=a_max,
        v_rolloff=True,
        v_threshold=v_threshold,
        floor=floor,
        a_coast=0.0,
    )
