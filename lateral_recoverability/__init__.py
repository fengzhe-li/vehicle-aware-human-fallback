"""Conditional lateral path feasibility; never a collision-avoidance guarantee."""

from .model import assess_lateral
from .schema import (
    Clearance, Evidence, Interval, Observation, Outcome, Scenario, State, Vehicle,
)

__all__ = [
    "assess_lateral", "Clearance", "Evidence", "Interval", "Observation",
    "Outcome", "Scenario", "State", "Vehicle",
]
