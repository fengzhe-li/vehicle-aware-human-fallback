"""Analytical closed-form oracle functions for A0 and A1 validation.

These closed-form equations are derived and SymPy-verified in:
- experiments/A_brake_response/analytical_sanity_check.md
- docs/CAUSAL_MODEL.md
- experiments/A_brake_response/metric_definitions.md
"""

import sympy as sp


def stopping_distance_w0_analytical(
    v0: float,
    a_max: float,
    t_reaction: float = 1.0,
    t_delay: float = 0.0,
    t_buildup: float = 0.0,
) -> float:
    """Compute exact analytical stopping distance under withdrawal policy W0.

    Equation:
    D_stop = v0^2 / (2 * a_max) + v0 * (t_reaction + t_delay + t_buildup / 2) - a_max * t_buildup^2 / 24

    Parameters
    ----------
    v0 : float
        Initial velocity in m/s.
    a_max : float
        Maximum deceleration magnitude in m/s^2.
    t_reaction : float
        Reaction time in seconds (t1).
    t_delay : float
        Actuation delay time in seconds (t2).
    t_buildup : float
        Linear deceleration ramp build-up time in seconds (t3).

    Returns
    -------
    float
        Exact analytical stopping distance in metres.
    """
    return float(
        (v0**2) / (2.0 * a_max)
        + v0 * (t_reaction + t_delay + t_buildup / 2.0)
        - (a_max * (t_buildup**2)) / 24.0
    )


def stopping_distance_w1_analytical(
    v0: float,
    a_max: float,
    t_reaction: float = 1.0,
    t_delay: float = 0.0,
    t_buildup: float = 0.0,
    a_coast: float = 0.0,
) -> float:
    """Compute exact analytical stopping distance under withdrawal policy W1.

    Equations:
    v1 = v0 - a_coast * t_reaction
    x1 = v0 * t_reaction - 0.5 * a_coast * t_reaction^2
    D_stop = x1 + v1^2 / (2 * a_max) + v1 * (t_delay + t_buildup / 2) - a_max * t_buildup^2 / 24

    Parameters
    ----------
    v0 : float
        Initial velocity in m/s.
    a_max : float
        Maximum deceleration magnitude in m/s^2.
    t_reaction : float
        Reaction time in seconds (t1).
    t_delay : float
        Actuation delay time in seconds (t2).
    t_buildup : float
        Linear deceleration ramp build-up time in seconds (t3).
    a_coast : float
        Coast deceleration magnitude in m/s^2.

    Returns
    -------
    float
        Exact analytical stopping distance in metres.
    """
    v1 = v0 - a_coast * t_reaction
    if v1 < 0.0:
        # Vehicle stopped during coast phase before t_reaction
        return float(v0**2 / (2.0 * a_coast)) if a_coast > 0 else 0.0

    x1 = v0 * t_reaction - 0.5 * a_coast * (t_reaction**2)
    d_after = (
        (v1**2) / (2.0 * a_max)
        + v1 * (t_delay + t_buildup / 2.0)
        - (a_max * (t_buildup**2)) / 24.0
    )
    return float(x1 + d_after)


def stopping_margin_analytical(
    x_hazard: float,
    d_stop: float,
) -> float:
    """Compute exact analytical stopping margin.

    stopping_margin = x_hazard - D_stop
    """
    return float(x_hazard - d_stop)


def t_tor_critical_analytical(
    v0: float,
    d_stop: float,
) -> float:
    """Compute exact analytical T_TOR_critical for pure friction profiles under W0.

    Setting stopping_margin = 0:
    v0 * T_TOR_critical - D_stop = 0  =>  T_TOR_critical = D_stop / v0
    """
    return float(d_stop / v0)


def verify_symbolic_cross_derivative() -> bool:
    """Symbolically verify the withdrawal-policy x vehicle-response interaction derivative.

    Verifies d^2(D_stop) / (d a_coast d t_buildup) == -t_reaction / 2 using SymPy.
    """
    v0, a_max, t1, t2, t3, a_c = sp.symbols("v0 a_max t1 t2 t3 a_c", positive=True)
    v1 = v0 - a_c * t1
    x1 = v0 * t1 - sp.Rational(1, 2) * a_c * (t1**2)
    d_stop = x1 + (v1**2) / (2 * a_max) + v1 * (t2 + t3 / 2) - a_max * (t3**2) / 24

    cross_partial = sp.diff(d_stop, a_c, t3)
    expected = -t1 / 2
    return bool(sp.simplify(cross_partial - expected) == 0)


def stopping_distance_r3b_analytical(
    v0: float,
    a_max: float,
    t_effective: float,
    t_delay: float,
    t_buildup: float,
    t_authority: float,
    a_before_authority: float,
    a_after_authority: float,
    u_brake: float = 1.0,
    road_friction: float = None,
) -> float:
    """Exact stopping distance for the R3B braking slice (no roll-off), in metres.

    Phases (t measured from TOR):
      [0, t_authority)            constant deceleration a_before_authority (policy)
      [t_authority, t_effective)  constant deceleration a_after_authority (vehicle only)
      [t_effective, +t_delay)     zero acceleration (actuation delay; as in the legacy model)
      [.., +t_buildup)            linear ramp to a_eff = min(u_brake * a_max, road_friction * g)
      afterwards                  constant a_eff until standstill
    Standstill inside any phase is handled exactly (including inside the ramp).
    With t_authority = t_effective and zero pre-control deceleration this is the legacy W0
    closed form; with t_authority = 0 and a_after_authority = a_coast it is legacy W1.
    """
    from src.vehicle.models import effective_braking_deceleration

    if v0 <= 0.0:
        return 0.0
    if not (0.0 <= t_authority <= t_effective):
        raise ValueError("need 0 <= t_authority <= t_effective")
    x, v = 0.0, float(v0)
    for dur, dec in ((t_authority, a_before_authority), (t_effective - t_authority, a_after_authority)):
        if dur <= 0.0:
            continue
        if dec > 0.0 and v - dec * dur <= 0.0:
            return float(x + v * v / (2.0 * dec))  # stops before effective human braking
        x += v * dur - 0.5 * dec * dur * dur
        v -= dec * dur
    x += v * t_delay
    a_eff = effective_braking_deceleration(a_max, u_brake, road_friction)
    if a_eff <= 0.0:
        return float("inf")
    if t_buildup > 0.0:
        dv_ramp = 0.5 * a_eff * t_buildup
        if v <= dv_ramp:  # standstill inside the ramp: v - a_eff*tau^2/(2 t3) = 0
            tau = (2.0 * v * t_buildup / a_eff) ** 0.5
            return float(x + v * tau - a_eff * tau ** 3 / (6.0 * t_buildup))
        return float(x + v * v / (2.0 * a_eff) + v * t_buildup / 2.0 - a_eff * t_buildup ** 2 / 24.0)
    return float(x + v * v / (2.0 * a_eff))


def braking_t_required(d_stop: float, v0: float, standstill_margin: float = 0.0) -> float:
    """T_required^brake under the constant-velocity reference convention: (D_stop + margin) / v0."""
    if v0 <= 0.0:
        raise ValueError("v0 must be positive")
    return float((d_stop + standstill_margin) / v0)
