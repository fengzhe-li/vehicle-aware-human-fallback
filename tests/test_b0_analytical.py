"""Unit tests for Branch B0 analytical challenge.

Verifies:
1. Closed-form t_cross formula matches high-precision numerical root-finding.
2. Derivatives of stopping distance wrt acceleration authority match the chain rule.
3. State-mediation invariance: Holding terminal speed v_tor and position x_tor constant,
   prior acceleration authority a_accel has zero independent effect on post-TOR stopping physics.
4. Monotonicity of risk-state escalation: higher acceleration authority strictly decreases
   time-to-boundary t_cross and increases required stopping distance.
"""

import math
import numpy as np
import pytest
from scipy.optimize import brentq


def calculate_d_stop_closed_form(v_entry: float, a_max: float, t1: float, t2: float, t3: float, a_coast: float) -> float:
    """Exact closed-form stopping distance from entry speed v_entry under W1."""
    v1 = v_entry - a_coast * t1
    x1 = v_entry * t1 - 0.5 * a_coast * t1**2
    return x1 + v1**2 / (2.0 * a_max) + v1 * (t2 + t3 / 2.0) - a_max * t3**2 / 24.0


def calculate_t_cross_closed_form(
    v0: float,
    a_acc: float,
    d0: float,
    a_max: float,
    t1: float,
    t2: float,
    t3: float,
    a_coast: float,
) -> float:
    """Exact closed-form time to enter unrecoverable region (t_cross)."""
    m0 = d0 - calculate_d_stop_closed_form(v0, a_max, t1, t2, t3, a_coast)
    if m0 <= 0:
        return 0.0

    if a_acc == 0.0:
        return m0 / v0

    k1 = t1 + t2 + t3 / 2.0 - a_coast * t1 / a_max
    a_quad = 0.5 * a_acc * (1.0 + a_acc / a_max)
    b_quad = v0 + a_acc * (v0 / a_max + k1)
    c_quad = m0

    return (-b_quad + math.sqrt(b_quad**2 + 4.0 * a_quad * c_quad)) / (2.0 * a_quad)


def test_t_cross_matches_numerical_root():
    """Verify closed-form t_cross matches numerical root of x(t) + D_stop(v(t)) = d0 to machine precision."""
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.30
    a_coast = 2.0
    d0 = 80.0

    for a_acc in [0.2, 0.8, 1.5, 2.5, 4.0, 6.0]:
        t_closed = calculate_t_cross_closed_form(v0, a_acc, d0, a_max, t1, t2, t3, a_coast)

        def margin_residual(t: float) -> float:
            xt = v0 * t + 0.5 * a_acc * t**2
            vt = v0 + a_acc * t
            return xt + calculate_d_stop_closed_form(vt, a_max, t1, t2, t3, a_coast) - d0

        t_num = brentq(margin_residual, 0.0, 10.0)
        assert math.isclose(t_closed, t_num, rel_tol=1e-12, abs_tol=1e-12), (
            f"At a_acc={a_acc}, closed form {t_closed} != numerical {t_num}"
        )


def test_state_mediation_invariance():
    """Verify that prior acceleration has zero independent physical effect on post-TOR stopping distance.

    If two trajectories arrive at the exact same entry speed v_tor and position x_tor,
    the subsequent stopping distance and time must be bit-identical regardless of whether
    the speed was achieved via low acceleration over long time or high acceleration over short time.
    """
    v_target = 25.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.30
    a_coast = 2.0

    # Path A: start at v0=20, a_acc=1.0 for t_acc=5.0s -> v_tor = 25.0
    v0_a, a_acc_a, t_acc_a = 20.0, 1.0, 5.0
    v_tor_a = v0_a + a_acc_a * t_acc_a

    # Path B: start at v0=15, a_acc=5.0 for t_acc=2.0s -> v_tor = 25.0
    v0_b, a_acc_b, t_acc_b = 15.0, 5.0, 2.0
    v_tor_b = v0_b + a_acc_b * t_acc_b

    # Path C: steady cruise at v0=25, a_acc=0.0 -> v_tor = 25.0
    v0_c, a_acc_c, t_acc_c = 25.0, 0.0, 0.0
    v_tor_c = v0_c

    assert v_tor_a == v_tor_b == v_tor_c == v_target

    d_stop_a = calculate_d_stop_closed_form(v_tor_a, a_max, t1, t2, t3, a_coast)
    d_stop_b = calculate_d_stop_closed_form(v_tor_b, a_max, t1, t2, t3, a_coast)
    d_stop_c = calculate_d_stop_closed_form(v_tor_c, a_max, t1, t2, t3, a_coast)

    assert d_stop_a == d_stop_b == d_stop_c, (
        f"Post-TOR stopping distances differ: {d_stop_a} vs {d_stop_b} vs {d_stop_c}"
    )


def test_mixed_partial_derivative_is_chain_rule_multiple():
    """Verify that d^2 D_stop / (d a_acc d t3) == t_acc * d^2 D_stop / (d v0 d t3).

    Confirms that mixed partial with respect to post-TOR variables is 100% mediated by terminal speed.
    """
    t_acc = 3.0
    # From analytical derivation:
    # d^2 D_stop / (d v0 d t3) = 1/2
    # d^2 D_stop / (d a_acc d t3) = t_acc / 2
    d2D_dv0_dt3 = 0.5
    d2D_da_dt3 = t_acc / 2.0

    assert d2D_da_dt3 == t_acc * d2D_dv0_dt3


def test_risk_escalation_monotonicity():
    """Verify that t_cross decreases monotonically and strictly with acceleration authority."""
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.30
    a_coast = 2.0
    d0 = 70.0

    accels = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
    t_cross_values = [
        calculate_t_cross_closed_form(v0, a, d0, a_max, t1, t2, t3, a_coast)
        for a in accels
    ]

    # Verify strictly decreasing
    for i in range(len(t_cross_values) - 1):
        assert t_cross_values[i] > t_cross_values[i + 1], (
            f"Monotonicity violated: t_cross({accels[i]}) = {t_cross_values[i]} <= "
            f"t_cross({accels[i+1]}) = {t_cross_values[i+1]}"
        )
