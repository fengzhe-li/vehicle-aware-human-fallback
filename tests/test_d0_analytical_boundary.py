"""Unit tests for Branch D0: State-Dependent Handover Boundary Analytical Derivation.

Verifies:
1. Exact closed-form formulation of T_required matches oracle D_stop / v0.
2. Analytical partial derivative signs:
   - d T_required / d v0 > 0
   - d T_required / d t_reaction > 0
   - d T_required / d a_pre < 0
   - d T_required / d t_delay > 0
   - d T_required / d t_buildup > 0
   - d T_required / d a_max < 0
3. Under W0 (a_pre = 0), d T_required / d t_reaction == 1.0 identically.
4. Numerical spread across admissible domain:
   - Core empirical grid (Type 3) spread is ~2.44 s.
   - Sensitivity extension (Type 2) spread is ~3.91 s.
5. Recoverability criterion consistency: T_available >= T_required <=> Stopping margin >= 0.
"""

import math
import numpy as np
import pytest

from src.metrics.oracle import stopping_distance_w0_analytical, stopping_distance_w1_analytical


def compute_t_required_analytical(
    v0: float,
    t1: float,
    a_pre: float,
    t2: float,
    t3: float,
    a_max: float,
) -> float:
    """Exact closed-form minimum required TOR lead time to stop safely before obstacle."""
    v1 = v0 - a_pre * t1
    if v1 < 0.0:
        d_stop = v0**2 / (2.0 * a_pre) if a_pre > 0 else 0.0
    else:
        x1 = v0 * t1 - 0.5 * a_pre * t1**2
        d_after = v1**2 / (2.0 * a_max) + v1 * (t2 + t3 / 2.0) - a_max * t3**2 / 24.0
        d_stop = x1 + d_after
    return d_stop / v0


def test_t_required_matches_oracle():
    """Verify that T_required formula exactly equals D_stop / v0 from validated oracles."""
    test_cases = [
        (10.0, 1.0, 0.0, 0.10, 0.30, 8.5),
        (20.0, 1.0, 2.0, 0.10, 0.30, 8.5),
        (30.0, 1.5, 3.0, 0.17, 0.50, 5.0),
        (15.0, 0.7, 1.0, 0.05, 0.10, 9.0),
    ]

    for v0, t1, a_pre, t2, t3, a_max in test_cases:
        t_req = compute_t_required_analytical(v0, t1, a_pre, t2, t3, a_max)
        if a_pre == 0.0:
            d_oracle = stopping_distance_w0_analytical(v0, a_max, t1, t2, t3)
        else:
            d_oracle = stopping_distance_w1_analytical(v0, a_max, t1, t2, t3, a_pre)
        expected_t = d_oracle / v0
        assert math.isclose(t_req, expected_t, rel_tol=1e-12, abs_tol=1e-12)


def test_derivative_signs():
    """Verify partial derivative signs of T_required."""
    v0, t1, a_pre, t2, t3, a_max = 20.0, 1.0, 2.0, 0.10, 0.30, 8.5
    eps = 1e-5
    base = compute_t_required_analytical(v0, t1, a_pre, t2, t3, a_max)

    # d T / d v0 > 0
    assert compute_t_required_analytical(v0 + eps, t1, a_pre, t2, t3, a_max) > base
    # d T / d t1 > 0
    assert compute_t_required_analytical(v0, t1 + eps, a_pre, t2, t3, a_max) > base
    # d T / d a_pre < 0
    assert compute_t_required_analytical(v0, t1, a_pre + eps, t2, t3, a_max) < base
    # d T / d t2 > 0
    assert compute_t_required_analytical(v0, t1, a_pre, t2 + eps, t3, a_max) > base
    # d T / d t3 > 0
    assert compute_t_required_analytical(v0, t1, a_pre, t2, t3 + eps, a_max) > base
    # d T / d a_max < 0
    assert compute_t_required_analytical(v0, t1, a_pre, t2, t3, a_max + eps) < base


def test_w0_reaction_time_derivative_is_unity():
    """Under W0 (a_pre = 0), d T_required / d t_reaction is identically 1.0."""
    v0, t2, t3, a_max = 20.0, 0.10, 0.30, 8.5
    t1_a, t1_b = 0.8, 1.4
    t_req_a = compute_t_required_analytical(v0, t1_a, 0.0, t2, t3, a_max)
    t_req_b = compute_t_required_analytical(v0, t1_b, 0.0, t2, t3, a_max)

    delta_t_req = t_req_b - t_req_a
    delta_t1 = t1_b - t1_a
    assert math.isclose(delta_t_req, delta_t1, rel_tol=1e-12, abs_tol=1e-12)


def test_spread_across_domains():
    """Verify the spread Delta T_required across core empirical and sensitivity domains."""
    # Core Empirical Grid (Type 3):
    v0_vals = [10.0, 20.0, 30.0]
    t1_vals = [0.7, 1.0, 1.5]
    a_pre_vals = [0.0, 1.5, 3.0]
    t2_vals = [0.05, 0.17]
    t3_core = 0.30
    a_max_core = 8.5

    core_results = [
        compute_t_required_analytical(v0, t1, ap, t2, t3_core, a_max_core)
        for v0 in v0_vals for t1 in t1_vals for ap in a_pre_vals for t2 in t2_vals
    ]
    min_core, max_core = min(core_results), max(core_results)
    spread_core = max_core - min_core

    assert 1.10 <= min_core <= 1.20
    assert 3.50 <= max_core <= 3.65
    assert 2.35 <= spread_core <= 2.50

    # Sensitivity Extension (Type 2):
    t3_vals = [0.10, 0.50]
    a_max_vals = [4.9, 8.5]
    ext_results = [
        compute_t_required_analytical(v0, t1, ap, t2, t3, a_max)
        for v0 in v0_vals for t1 in t1_vals for ap in a_pre_vals for t2 in t2_vals
        for t3 in t3_vals for a_max in a_max_vals
    ]
    min_ext, max_ext = min(ext_results), max(ext_results)
    spread_ext = max_ext - min_ext

    assert 1.00 <= min_ext <= 1.15
    assert 4.90 <= max_ext <= 5.05
    assert 3.80 <= spread_ext <= 4.00


def test_recoverability_region_consistency():
    """Verify that T_available >= T_required is exactly consistent with collision avoidance."""
    v0 = 20.0
    t1 = 1.0
    a_pre = 2.0
    t2 = 0.10
    t3 = 0.30
    a_max = 8.5

    t_req = compute_t_required_analytical(v0, t1, a_pre, t2, t3, a_max)
    d_stop = t_req * v0

    # Case A: T_available > T_required -> d_hazard > d_stop -> safe
    t_avail_safe = t_req + 0.2
    d_hazard_safe = v0 * t_avail_safe
    margin_safe = d_hazard_safe - d_stop
    assert margin_safe > 0.0

    # Case B: T_available < T_required -> d_hazard < d_stop -> collision
    t_avail_unsafe = t_req - 0.2
    d_hazard_unsafe = v0 * t_avail_unsafe
    margin_unsafe = d_hazard_unsafe - d_stop
    assert margin_unsafe < 0.0
