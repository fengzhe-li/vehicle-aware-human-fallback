"""Minimal longitudinal numerical simulator.

Implements docs/MINIMAL_SIMULATOR_SPEC.md:
- Deterministic, inspectable, minimal physics.
- Piecewise-constant-acceleration integration within step:
    v[k+1] = max(0, v[k] + a[k]*dt)
    x[k+1] = x[k] + v[k]*dt + 0.5*a[k]*dt^2
- Three classes of events:
  1. A-priori known phase transitions (t_reaction, t_delay, t_buildup).
  2. State-dependent threshold crossing (v_rolloff).
  3. Outcome-defining events (hazard crossing / collision, full stop v=0).
- Sub-step kinematic interpolation for exact outcome-defining event times/positions.
"""

from dataclasses import dataclass
from typing import List, Optional
import math
import numpy as np

from src.scenarios.models import ScenarioConfig
from src.vehicle.models import (
    VehicleResponseConfig,
    calculate_acceleration,
)
from src.driver.models import HumanDriverConfig
from src.handover.models import HandoverTimeline, PreControlProfile, WithdrawalPolicy
from src.metrics.outcomes import Outcomes


@dataclass(frozen=True)
class SimulationState:
    """State of the ego vehicle at discrete timestamp t."""

    t: float
    x: float
    v: float
    a: float
    u_brake: float = 0.0  # applied braking command (0 before effective human control)


@dataclass(frozen=True)
class SimulationResult:
    """Full result of a simulation run including trajectory and outcomes."""

    scenario: ScenarioConfig
    vehicle: VehicleResponseConfig
    driver: HumanDriverConfig
    withdrawal: WithdrawalPolicy
    dt: float
    trajectory: List[SimulationState]
    outcomes: Outcomes
    timeline: Optional[HandoverTimeline] = None
    pre_control: Optional[PreControlProfile] = None
    u_brake: float = 1.0
    road_friction: Optional[float] = None

    @property
    def times(self) -> np.ndarray:
        return np.array([s.t for s in self.trajectory], dtype=np.float64)

    @property
    def positions(self) -> np.ndarray:
        return np.array([s.x for s in self.trajectory], dtype=np.float64)

    @property
    def velocities(self) -> np.ndarray:
        return np.array([s.v for s in self.trajectory], dtype=np.float64)

    @property
    def accelerations(self) -> np.ndarray:
        return np.array([s.a for s in self.trajectory], dtype=np.float64)

    @property
    def commands(self) -> np.ndarray:
        """Applied braking command u_brake(t) along the trajectory."""
        return np.array([s.u_brake for s in self.trajectory], dtype=np.float64)


class MinimalSimulator:
    """Minimal longitudinal simulator for A0 validation and A1 experiments.

    Parameters
    ----------
    dt : float
        Default nominal integration timestep in seconds. Default is 0.001 s (1 ms).
    max_sim_time : float
        Safety bound against infinite loops in seconds. Default is 100.0 s.
    """

    def __init__(self, dt: float = 0.001, max_sim_time: float = 100.0) -> None:
        if dt <= 0.0:
            raise ValueError(f"dt must be strictly positive, got {dt}")
        if max_sim_time <= 0.0:
            raise ValueError(f"max_sim_time must be strictly positive, got {max_sim_time}")
        self.dt = dt
        self.max_sim_time = max_sim_time

    def simulate(
        self,
        scenario: ScenarioConfig,
        vehicle: VehicleResponseConfig,
        driver: HumanDriverConfig = HumanDriverConfig(),
        withdrawal: WithdrawalPolicy = WithdrawalPolicy.W0,
        *,
        timeline: Optional[HandoverTimeline] = None,
        pre_control: Optional[PreControlProfile] = None,
    ) -> SimulationResult:
        """Execute a forward simulation run.

        Parameters
        ----------
        scenario : ScenarioConfig
            Scenario settings (v0, tor_lead_time, road_friction).
        vehicle : VehicleResponseConfig
            Vehicle response profile parameters.
        driver : HumanDriverConfig
            Human driver parameters (frozen open-loop step command).
        withdrawal : WithdrawalPolicy
            Withdrawal policy (W0 or W1).

        Returns
        -------
        SimulationResult
        """
        t = 0.0
        x = 0.0
        v = scenario.v0
        x_hazard = scenario.x_hazard
        # R3B: explicit timeline (authority transfer is an input assumption, never inferred)
        if (timeline is None) != (pre_control is None):
            raise ValueError("timeline and pre_control must be given together")
        t_reaction = driver.t_reaction if timeline is None else timeline.t_effective
        t_authority = None if timeline is None else timeline.t_authority
        u_brake = driver.u_target
        road_friction = scenario.road_friction

        def accel(tt: float, vv: float) -> float:
            return calculate_acceleration(tt, vv, vehicle, withdrawal, t_reaction, u_brake=u_brake,
                                          road_friction=road_friction, t_authority=t_authority,
                                          pre_control=pre_control)

        def command(tt: float) -> float:
            return u_brake if tt >= t_reaction else 0.0

        # A-priori scheduled event times strictly after t=0
        scheduled_events = [t_reaction]
        if t_authority is not None:
            scheduled_events.append(t_authority)
        if vehicle.t_delay > 0.0:
            scheduled_events.append(t_reaction + vehicle.t_delay)
        if vehicle.t_buildup > 0.0:
            scheduled_events.append(t_reaction + vehicle.t_delay + vehicle.t_buildup)
        scheduled_events = sorted(list(set(e for e in scheduled_events if e > 0.0)))

        a = accel(t, v)
        trajectory: List[SimulationState] = [SimulationState(t=t, x=x, v=v, a=a, u_brake=command(t))]

        recorded_t_collision: Optional[float] = None
        recorded_impact_speed: Optional[float] = None

        eps = 1e-12

        while v > 0.0 and t < self.max_sim_time:
            # 1. Start with nominal timestep
            step = self.dt

            # 2. Check a-priori scheduled events (Event Class 1)
            for ev in scheduled_events:
                if t < ev - eps and (t + step) > ev - eps:
                    step = ev - t
                    break

            a_k = accel(t, v)

            is_stopping = False

            # 3. Check full-stop event v -> 0 (Event Class 3)
            if a_k < -eps:
                v_tentative = v + a_k * step
                if v_tentative <= 0.0:
                    step_stop = -v / a_k
                    if step_stop <= step:
                        step = step_stop
                        is_stopping = True
                elif vehicle.v_rolloff and (v > vehicle.v_threshold > v_tentative):
                    # State-dependent threshold crossing for v_rolloff (Event Class 2)
                    step_thresh = (vehicle.v_threshold - v) / a_k
                    if 0.0 < step_thresh < step:
                        step = step_thresh

            # Step integration (piecewise-constant a_k)
            x_next = x + v * step + 0.5 * a_k * (step**2)
            if is_stopping:
                v_next = 0.0
            else:
                v_next = max(0.0, v + a_k * step)
            t_next = t + step

            # 4. Check hazard crossing / collision (Event Class 3)
            if recorded_t_collision is None and (x < x_hazard <= x_next + eps):
                dx_cross = x_hazard - x
                if abs(a_k) < eps:
                    v_cross = v
                    dt_cross = dx_cross / v if v > 0 else 0.0
                else:
                    v_sq = v**2 + 2.0 * a_k * dx_cross
                    v_cross = math.sqrt(max(0.0, v_sq))
                    dt_cross = (v_cross - v) / a_k

                recorded_t_collision = t + dt_cross
                recorded_impact_speed = v_cross

            # Advance state
            t = t_next
            x = x_next
            v = v_next

            if v <= 0.0 or is_stopping:
                v = 0.0
                a = 0.0
                trajectory.append(SimulationState(t=t, x=x, v=v, a=a, u_brake=command(t)))
                break

            a = accel(t, v)
            trajectory.append(SimulationState(t=t, x=x, v=v, a=a, u_brake=command(t)))

        # Outcome calculations
        x_stop_full = x
        t_stop = t
        stopping_margin = x_hazard - x_stop_full
        collision = stopping_margin < 0.0

        if collision:
            impact_speed = recorded_impact_speed if recorded_impact_speed is not None else 0.0
            t_collision = recorded_t_collision
            t_stop_or_collision = min(t_stop, t_collision) if t_collision is not None else t_stop
            ttc_min = 0.0
        else:
            impact_speed = float("nan")
            t_collision = None
            t_stop_or_collision = t_stop

            # Compute TTC_min over [t_reaction, t_stop_or_collision] for v > 0
            ttc_candidates: List[float] = []
            for i in range(len(trajectory) - 1):
                s1 = trajectory[i]
                s2 = trajectory[i + 1]

                if s1.t >= t_reaction - eps and s1.t <= t_stop_or_collision + eps and s1.v > eps:
                    ttc_candidates.append((x_hazard - s1.x) / s1.v)

                # Analytical intra-step stationary point check where d(TTC)/dt = 0
                # d(TTC)/dt = 0 <=> v^2 + a*(x_hazard - x) = 0
                a_seg = s1.a
                if a_seg < -eps and s1.v > eps and s2.v > eps:
                    gap1 = x_hazard - s1.x
                    gap2 = x_hazard - s2.x
                    val1 = s1.v**2 + a_seg * gap1
                    val2 = s2.v**2 + a_seg * gap2
                    if val1 < 0.0 and val2 > 0.0:
                        # Derivative crossed zero within this segment
                        dx_star = - (s1.v**2 + a_seg * gap1) / a_seg
                        if 0.0 <= dx_star <= (s2.x - s1.x):
                            v_star_sq = s1.v**2 + 2.0 * a_seg * dx_star
                            if v_star_sq > 0.0:
                                v_star = math.sqrt(v_star_sq)
                                gap_star = gap1 - dx_star
                                ttc_candidates.append(gap_star / v_star)

            if trajectory[-1].t >= t_reaction - eps and trajectory[-1].v > eps:
                ttc_candidates.append((x_hazard - trajectory[-1].x) / trajectory[-1].v)

            ttc_min = min(ttc_candidates) if ttc_candidates else float("inf")

        outcomes = Outcomes(
            stopping_margin=stopping_margin,
            collision=collision,
            ttc_min=ttc_min,
            impact_speed=impact_speed,
            x_stop_full=x_stop_full,
            t_stop=t_stop,
            t_collision=t_collision,
        )

        return SimulationResult(
            scenario=scenario,
            vehicle=vehicle,
            driver=driver,
            withdrawal=withdrawal,
            dt=self.dt,
            trajectory=trajectory,
            outcomes=outcomes,
            timeline=timeline,
            pre_control=pre_control,
            u_brake=u_brake,
            road_friction=road_friction,
        )
