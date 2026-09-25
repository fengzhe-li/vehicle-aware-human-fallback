"""Handover and control ownership models.

Per control_ownership_timeline.md and docs/CAUSAL_MODEL.md:
- w_authority(t) in {automation, human}.
- Legacy (pre-R3B) path: authority switches at t_reaction, and the Phase-0 documentation
  placed nominal authority at TOR. This is superseded: since R3B, authority transfer is an
  explicit input (HandoverTimeline.t_authority, 0 <= t_authority <= t_effective), never
  equal to TOR by definition and never inferred from data.
- T_effective = t_reaction (human control takes over longitudinal command).
- Legacy withdrawal policies (kept for reproducibility; R3B uses PreControlProfile branches):
  - W0: Automation holds v0 during [0, t_reaction) (baseline policy B).
  - W1: Automation withdraws immediately at t=0; vehicle coasts at a_coast during [0, t_reaction).
  - W2: Excluded by design (Phase 0.4 decision).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WithdrawalPolicy(str, Enum):
    """Automation withdrawal policies under evaluation.

    W0: Automation maintains steady-state speed v0 until human brake onset at t_reaction.
    W1: Automation withdraws longitudinal propulsion immediately at TOR (t=0).
    """

    W0 = "W0"
    W1 = "W1"


class ControlAuthority(str, Enum):
    """Binary control ownership state at time t."""

    AUTOMATION = "automation"
    HUMAN = "human"


@dataclass(frozen=True)
class HandoverTimeline:
    """Longitudinal takeover timeline (R3B correction C), seconds after TOR (t_TOR = 0).

    TOR, authority transfer, first human input and effective human control are
    distinct events (docs/SYSTEM_EVENT_STATE_SPECIFICATION.md). Authority transfer is
    an explicit scenario assumption: it is not identified from D003.

    Invariants: 0 <= t_authority <= t_effective and 0 <= t_first_input <= t_effective.
    First human input is not ordered relative to authority transfer (R157 allows
    inputs below the override threshold before deactivation).
    """

    t_authority: float
    t_effective: float
    t_first_input: Optional[float] = None

    T_TOR = 0.0

    def __post_init__(self) -> None:
        if self.t_effective < 0.0:
            raise ValueError(f"t_effective must be >= 0 (TOR), got {self.t_effective}")
        if not (0.0 <= self.t_authority <= self.t_effective):
            raise ValueError(f"need 0 <= t_authority <= t_effective, got {self.t_authority}, {self.t_effective}")
        if self.t_first_input is not None and not (0.0 <= self.t_first_input <= self.t_effective):
            raise ValueError(f"need 0 <= t_first_input <= t_effective, got {self.t_first_input}")


@dataclass(frozen=True)
class PreControlProfile:
    """Longitudinal behaviour between TOR and effective human control (deceleration magnitudes, m/s^2).

    a_before_authority: net deceleration while the automation still has authority
        [0, t_authority) -- set by the transition policy (0 = speed held).
    a_after_authority: deceleration after authority transfer but before effective human
        braking [t_authority, t_effective) -- no automation command, vehicle response only.
    Each interval has exactly one source of deceleration, so a_pre is never counted twice.
    """

    a_before_authority: float
    a_after_authority: float
    label: str = ""

    def __post_init__(self) -> None:
        if self.a_before_authority < 0.0 or self.a_after_authority < 0.0:
            raise ValueError("pre-control deceleration magnitudes must be non-negative")


def legacy_equivalent(withdrawal: "WithdrawalPolicy", t_reaction: float, a_coast: float):
    """(HandoverTimeline, PreControlProfile) reproducing the legacy W0 / W1 behaviour exactly.

    W0: automation holds speed until effective control (authority at t_reaction).
    W1: authority at TOR, vehicle coasts at a_coast until effective control.
    """
    if withdrawal == WithdrawalPolicy.W0:
        return (HandoverTimeline(t_authority=t_reaction, t_effective=t_reaction),
                PreControlProfile(0.0, 0.0, "legacy W0"))
    if withdrawal == WithdrawalPolicy.W1:
        return (HandoverTimeline(t_authority=0.0, t_effective=t_reaction),
                PreControlProfile(0.0, a_coast, "legacy W1"))
    raise ValueError(f"Unknown withdrawal policy: {withdrawal}")


def get_control_authority(t: float, t_reaction: float, t_authority: Optional[float] = None) -> ControlAuthority:
    """Determine longitudinal control authority at time t.

    Parameters
    ----------
    t : float
        Current time in seconds relative to TOR.
    t_reaction : float
        Effective human control time in seconds (legacy switch time).
    t_authority : Optional[float]
        Explicit authority-transfer time (R3B). If None, the legacy behaviour applies:
        authority switches at t_reaction.

    Returns
    -------
    ControlAuthority
        AUTOMATION before the switch time, else HUMAN.
    """
    switch = t_reaction if t_authority is None else t_authority
    if t < switch:
        return ControlAuthority.AUTOMATION
    return ControlAuthority.HUMAN
