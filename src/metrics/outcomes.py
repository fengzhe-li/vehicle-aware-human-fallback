"""Phase 1 outcome metric definitions.

Per metric_definitions.md:
- collision: derived from stopping_margin < 0.
- TTC_min: minimum TTC over [t_reaction, t_stop_or_collision], 0.0 if collision.
- stopping_margin: x_hazard - x_stop_full (continued counterfactual integration).
- impact_speed: speed at x_hazard crossing if collision, else float('nan').
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass(frozen=True)
class Outcomes:
    """Container for simulation outcome metrics.

    Parameters
    ----------
    stopping_margin : float
        x_hazard - x_stop_full (m). Positive = stopped short; negative = overshoot (collision).
    collision : bool
        Derived strictly as (stopping_margin < 0.0).
    ttc_min : float
        Minimum time-to-collision in seconds over [t_reaction, t_stop_or_collision].
        0.0 if collision occurs.
    impact_speed : float
        Vehicle speed at x_hazard crossing in m/s if collision = True.
        Must be float('nan') when collision = False.
    x_stop_full : float
        Ego position where v reaches 0 (m).
    t_stop : float
        Timestamp when v reaches 0 (s).
    t_collision : Optional[float]
        Timestamp when x_ego reaches x_hazard (s) if collision, else None.
    """

    stopping_margin: float
    collision: bool
    ttc_min: float
    impact_speed: float
    x_stop_full: float
    t_stop: float
    t_collision: Optional[float] = None

    def __post_init__(self) -> None:
        expected_collision = self.stopping_margin < 0.0
        if self.collision != expected_collision:
            raise ValueError(
                f"Invariant violation: collision ({self.collision}) must match "
                f"(stopping_margin < 0) ({expected_collision})"
            )
        if not self.collision and not math.isnan(self.impact_speed):
            raise ValueError(
                f"Invariant violation: impact_speed must be NaN when collision=False, "
                f"got {self.impact_speed}"
            )
        if self.collision and math.isnan(self.impact_speed):
            raise ValueError(
                "Invariant violation: impact_speed must be a real number when collision=True, "
                "got NaN"
            )
