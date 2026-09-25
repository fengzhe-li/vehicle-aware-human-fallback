"""Frozen human driver command model for Phase 1.

Per control_input_definition.md and control_ownership_timeline.md:
- Open-loop step-command driver.
- u_human_accel(t) = 0.0 identically for all t (L3 out-of-loop framing).
- u_human_brake(t) is a step from 0.0 to u_target (1.0) at t = t_reaction.
- The command signal is identical bit-for-bit across all vehicle-response profiles.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class HumanDriverConfig:
    """Frozen human driver configuration.

    Parameters
    ----------
    t_reaction : float
        Reaction time in seconds from TOR issuance to brake pedal onset.
        Default is 1.0 s (frozen choice within literature range 0.7-1.5 s).
    u_target : float
        Target normalized brake pedal demand [0, 1]. Default is 1.0 (emergency step).
    """

    t_reaction: float = 1.0
    u_target: float = 1.0

    def __post_init__(self) -> None:
        if self.t_reaction < 0.0:
            raise ValueError(f"t_reaction must be non-negative, got {self.t_reaction}")
        if not (0.0 <= self.u_target <= 1.0):
            raise ValueError(f"u_target must be in [0, 1], got {self.u_target}")


def get_human_command(t: float, config: HumanDriverConfig = HumanDriverConfig()) -> Tuple[float, float]:
    """Evaluate open-loop human driver commands at time t.

    Parameters
    ----------
    t : float
        Current simulation time in seconds relative to TOR issuance (t=0).
    config : HumanDriverConfig
        Driver configuration parameters.

    Returns
    -------
    Tuple[float, float]
        (u_accel, u_brake) commands in normalized [0, 1] range.
        u_accel is identically 0.0 for all t per L3 out-of-loop framing.
        u_brake is 0.0 for t < t_reaction, and u_target (1.0) for t >= t_reaction.
    """
    u_accel = 0.0
    u_brake = 0.0 if t < config.t_reaction else config.u_target
    return u_accel, u_brake


def sample_human_brake_command(
    t_array: np.ndarray,
    config: HumanDriverConfig = HumanDriverConfig(),
) -> np.ndarray:
    """Sample the human brake command over an array of timestamps.

    Used specifically for programmatic treatment-isolation checks (Test 8)
    to verify bit-identical command trajectories across treatments.

    Parameters
    ----------
    t_array : np.ndarray
        1D array of timestamps (seconds).
    config : HumanDriverConfig
        Driver configuration parameters.

    Returns
    -------
    np.ndarray
        1D array of float64 sampled brake commands (0.0 or u_target).
    """
    return np.where(t_array < config.t_reaction, 0.0, config.u_target).astype(np.float64)
