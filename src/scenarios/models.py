"""Scenario models and configuration.

Per docs/MINIMAL_SIMULATOR_SPEC.md:
- Fixed scalar per scenario: x_hazard = v0 * TOR_lead_time.
- Single fixed hazard, longitudinal-only scope.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioConfig:
    """Configuration for a longitudinal takeover scenario.

    Parameters
    ----------
    v0 : float
        Initial vehicle speed in m/s at t=0 (TOR issuance).
    tor_lead_time : float
        Warning lead time in seconds. Determines x_hazard = v0 * tor_lead_time.
    road_friction : float
        Nominal tire-road friction coefficient mu (default 1.0, dry asphalt).
    """

    v0: float
    tor_lead_time: float
    road_friction: float = 1.0

    def __post_init__(self) -> None:
        if self.v0 <= 0.0:
            raise ValueError(f"v0 must be strictly positive, got {self.v0}")
        if self.tor_lead_time <= 0.0:
            raise ValueError(f"tor_lead_time must be strictly positive, got {self.tor_lead_time}")
        if self.road_friction <= 0.0:
            raise ValueError(f"road_friction must be strictly positive, got {self.road_friction}")

    @property
    def x_hazard(self) -> float:
        """Fixed hazard position in metres along the longitudinal lane."""
        return self.v0 * self.tor_lead_time
