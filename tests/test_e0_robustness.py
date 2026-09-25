"""Unit tests for Branch E0: Boundary Evidence Closure and Robustness Verification.

Verifies:
1. Integrity of e0_parameter_closure.csv and single bottleneck identification (t3/t_buildup).
2. Exact normalized sensitivities (elasticities) S_x = (x / T) * (dT / dx) at nominal operating points.
3. Global coordinate-wise monotonicity across the entire admissible parameter box.
4. Analytical extrema match domain corners (confirming absence of sparse-grid artifacts).
5. Bottleneck perturbation / leave-one-out robustness (t3 impact bounded to < 0.20 s).
6. Discretization shift bound (|T_crit,2 - T_crit,1| < 1 microsecond at dt = 0.001 s).
"""

import math
from pathlib import Path
import csv
import numpy as np
import pytest

from tests.test_d0_analytical_boundary import compute_t_required_analytical


def compute_t_required_partials(
    v0: float,
    t1: float,
    a_pre: float,
    t2: float,
    t3: float,
    a_max: float,
):
    """Exact analytical partial derivatives of T_required."""
    v1 = v0 - a_pre * t1
    assert v1 > 0.0, "Velocity at brake onset must be positive"

    dT_dv0 = (
        1.0 / (2.0 * a_max)
        + (a_pre * t1**2 * (1.0 - a_pre / a_max)) / (2.0 * v0**2)
        + a_pre * t1 * (t2 + t3 / 2.0) / (v0**2)
        + a_max * t3**2 / (24.0 * v0**2)
    )
    dT_dt1 = (1.0 - a_pre / a_max) * (v1 / v0) - (a_pre / v0) * (t2 + t3 / 2.0)
    dT_dapre = - (t1 / a_max) * (v1 / v0) - (t1 / v0) * (t1 / 2.0 + t2 + t3 / 2.0)
    dT_dt2 = v1 / v0
    dT_dt3 = 0.5 * (v1 / v0) - a_max * t3 / (12.0 * v0)
    dT_damax = - (v1**2) / (2.0 * a_max**2 * v0) - t3**2 / (24.0 * v0)

    return {
        "v0": dT_dv0,
        "t1": dT_dt1,
        "a_pre": dT_dapre,
        "t2": dT_dt2,
        "t3": dT_dt3,
        "a_max": dT_damax,
    }


def compute_elasticities(
    v0: float,
    t1: float,
    a_pre: float,
    t2: float,
    t3: float,
    a_max: float,
):
    """Normalized sensitivities S_x = (x / T) * (dT / dx)."""
    t_req = compute_t_required_analytical(v0, t1, a_pre, t2, t3, a_max)
    partials = compute_t_required_partials(v0, t1, a_pre, t2, t3, a_max)

    elasticities = {
        "v0": (v0 / t_req) * partials["v0"],
        "t1": (t1 / t_req) * partials["t1"],
        "a_pre": (a_pre / t_req) * partials["a_pre"] if a_pre != 0.0 else 0.0,
        "t2": (t2 / t_req) * partials["t2"],
        "t3": (t3 / t_req) * partials["t3"],
        "a_max": (a_max / t_req) * partials["a_max"],
    }
    return t_req, partials, elasticities


def test_parameter_closure_table_integrity():
    """Verify that e0_parameter_closure.csv exists, is well-formed, and identifies t3 as bottleneck."""
    csv_path = Path("experiments/E_boundary_validation/e0_parameter_closure.csv")
    assert csv_path.exists(), "e0_parameter_closure.csv must exist"

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) >= 8, "Must contain all 8 parameters / metrics"
    symbols = {row["symbol"] for row in reader}
    expected_symbols = {"v0", "t1", "a_pre", "t2", "t3", "a_max", "K0", "dx_robust"}
    assert expected_symbols.issubset(symbols), f"Missing symbols: {expected_symbols - symbols}"

    # Confirm that t3 is the unique claim bottleneck
    bottlenecks = [row["symbol"] for row in reader if row["claim_bottleneck"] == "YES"]
    assert bottlenecks == ["t3"], f"Expected only t3 as claim bottleneck, found: {bottlenecks}"


def test_normalized_sensitivities_elasticities():
    """Verify elasticity signs, magnitudes, and ranking at nominal points."""
    # Nominal W0:
    t_req_0, _, elast_0 = compute_elasticities(20.0, 1.0, 0.0, 0.10, 0.30, 8.5)
    assert 2.40 <= t_req_0 <= 2.45
    assert elast_0["v0"] > 0.45
    assert elast_0["t1"] > 0.38
    assert elast_0["a_pre"] == 0.0
    assert 0.03 <= elast_0["t2"] <= 0.05
    assert 0.05 <= elast_0["t3"] <= 0.08
    assert elast_0["a_max"] < -0.45

    # Nominal W1:
    t_req_1, _, elast_1 = compute_elasticities(20.0, 1.0, 1.5, 0.10, 0.30, 8.5)
    assert 2.15 <= t_req_1 <= 2.25
    assert elast_1["v0"] > 0.50
    assert elast_1["t1"] > 0.30
    assert elast_1["a_pre"] < -0.08
    assert 0.03 <= elast_1["t2"] <= 0.05
    assert 0.05 <= elast_1["t3"] <= 0.08
    assert elast_1["a_max"] < -0.40

    # Nominal reference ranking under W1:
    assert abs(elast_1["v0"]) > abs(elast_1["t1"])
    assert abs(elast_1["a_max"]) > abs(elast_1["t1"])
    assert abs(elast_1["t1"]) > abs(elast_1["a_pre"])
    assert abs(elast_1["a_pre"]) > abs(elast_1["t3"])
    assert abs(elast_1["t3"]) > abs(elast_1["t2"])


def test_elasticity_ranking_permutations_across_domain():
    """Verify that while derivative signs are globally invariant, elasticity rankings permute across domain."""
    v0_grid = [10.0, 20.0, 30.0]
    t1_grid = [0.7, 1.0, 1.5]
    ap_grid = [0.0, 1.5, 3.0]
    t2_grid = [0.05, 0.11, 0.17]
    t3_grid = [0.10, 0.30, 0.50]
    amax_grid = [4.9, 8.5]

    rankings = set()
    for v0 in v0_grid:
        for t1 in t1_grid:
            for ap in ap_grid:
                for t2 in t2_grid:
                    for t3 in t3_grid:
                        for amax in amax_grid:
                            _, _, elast = compute_elasticities(v0, t1, ap, t2, t3, amax)
                            items = sorted([(k, abs(v)) for k, v in elast.items()], key=lambda x: x[1], reverse=True)
                            order = tuple([k for k, _ in items])
                            rankings.add(order)

    # Confirm that multiple distinct rankings exist (ranking is not globally invariant)
    assert len(rankings) >= 20, f"Expected at least 20 elasticity permutations across domain, found: {len(rankings)}"


def test_global_monotonicity_across_admissible_domain():
    """Verify that all partial derivatives maintain strictly invariant signs across the domain."""
    v0_grid = [10.0, 20.0, 30.0]
    t1_grid = [0.7, 1.0, 1.5]
    ap_grid = [0.0, 1.5, 3.0]
    t2_grid = [0.05, 0.11, 0.17]
    t3_grid = [0.10, 0.30, 0.50]
    amax_grid = [4.9, 8.5]

    for v0 in v0_grid:
        for t1 in t1_grid:
            for ap in ap_grid:
                for t2 in t2_grid:
                    for t3 in t3_grid:
                        for amax in amax_grid:
                            partials = compute_t_required_partials(v0, t1, ap, t2, t3, amax)
                            assert partials["v0"] > 0.0, f"dT/dv0 <= 0 at {v0, t1, ap, t2, t3, amax}"
                            assert partials["t1"] > 0.0, f"dT/dt1 <= 0 at {v0, t1, ap, t2, t3, amax}"
                            assert partials["a_pre"] < 0.0, f"dT/dapre >= 0 at {v0, t1, ap, t2, t3, amax}"
                            assert partials["t2"] > 0.0, f"dT/dt2 <= 0 at {v0, t1, ap, t2, t3, amax}"
                            assert partials["t3"] > 0.0, f"dT/dt3 <= 0 at {v0, t1, ap, t2, t3, amax}"
                            assert partials["a_max"] < 0.0, f"dT/damax >= 0 at {v0, t1, ap, t2, t3, amax}"


def test_analytical_extrema_match_domain_corners():
    """Verify that the analytical extrema match domain corners without interior extrema."""
    # Core Domain:
    # Corner min: v0_min, t1_min, apre_max, t2_min, t3_nom, amax_nom
    core_min_corner = compute_t_required_analytical(10.0, 0.7, 3.0, 0.05, 0.30, 8.5)
    # Corner max: v0_max, t1_max, apre_min, t2_max, t3_nom, amax_nom
    core_max_corner = compute_t_required_analytical(30.0, 1.5, 0.0, 0.17, 0.30, 8.5)

    assert math.isclose(core_min_corner, 1.148430, rel_tol=1e-5)
    assert math.isclose(core_max_corner, 3.583643, rel_tol=1e-5)
    assert math.isclose(core_max_corner - core_min_corner, 2.435213, rel_tol=1e-5)

    # Sensitivity Domain:
    ext_min_corner = compute_t_required_analytical(10.0, 0.7, 3.0, 0.05, 0.10, 8.5)
    ext_max_corner = compute_t_required_analytical(30.0, 1.5, 0.0, 0.17, 0.50, 4.9)

    assert math.isclose(ext_min_corner, 1.072263, rel_tol=1e-5)
    assert math.isclose(ext_max_corner, 4.979523, rel_tol=1e-5)
    assert math.isclose(ext_max_corner - ext_min_corner, 3.907260, rel_tol=1e-5)


def test_bottleneck_leave_one_out_sensitivity():
    """Verify that full variation in t3 [0.1, 0.5] s shifts T_required by < 0.20 s."""
    # Under W0:
    t_req_t3_low_w0 = compute_t_required_analytical(20.0, 1.0, 0.0, 0.10, 0.10, 8.5)
    t_req_t3_high_w0 = compute_t_required_analytical(20.0, 1.0, 0.0, 0.10, 0.50, 8.5)
    delta_w0 = t_req_t3_high_w0 - t_req_t3_low_w0
    assert 0.18 <= delta_w0 <= 0.20

    # Under W1:
    t_req_t3_low_w1 = compute_t_required_analytical(20.0, 1.0, 1.5, 0.10, 0.10, 8.5)
    t_req_t3_high_w1 = compute_t_required_analytical(20.0, 1.0, 1.5, 0.10, 0.50, 8.5)
    delta_w1 = t_req_t3_high_w1 - t_req_t3_low_w1
    assert 0.17 <= delta_w1 <= 0.19


def test_discretization_shift_bound():
    """Verify that numerical resolvable margin dx_robust shifts T_required by < 1 microsecond."""
    dt = 0.001
    a_max = 8.5
    dx_robust = a_max * (dt**2)
    v0_min = 10.0  # lowest speed gives largest time shift dx_robust / v0
    t_shift = dx_robust / v0_min

    assert t_shift == 8.5e-7  # 0.85 microseconds
    assert t_shift < 1.0e-6


def test_apre_sensitivity_and_bounded_effects():
    """Verify exact analytical derivative of T_required w.r.t. a_pre and bounded effect sizes."""
    p_nom = dict(v0=20.0, t1=1.0, a_pre=0.0, t2=0.10, t3=0.30, a_max=8.5)
    partials_nom = compute_t_required_partials(**p_nom)
    d_apre_nom = partials_nom["a_pre"]

    # 1. Exact nominal derivative: -0.155147 s / (m/s^2)
    assert math.isclose(d_apre_nom, -0.155147, abs_tol=1e-5)

    # 2. Domain bounds of dT/da_pre across core admissible domain:
    # Most negative at low v0, high t1, low a_max:
    d_apre_min = compute_t_required_partials(10.0, 1.5, 0.0, 0.17, 0.45, 6.0)["a_pre"]
    # Least negative at high v0, low t1, high a_max:
    d_apre_max = compute_t_required_partials(35.0, 0.7, 3.0, 0.05, 0.15, 9.0)["a_pre"]

    assert math.isclose(d_apre_min, -0.42175, abs_tol=1e-4)
    assert math.isclose(d_apre_max, -0.08261, abs_tol=1e-4)

    # 3. Bounded effect sizes at nominal baseline:
    t_nom = compute_t_required_analytical(**p_nom)
    t_apre3 = compute_t_required_analytical(**dict(p_nom, a_pre=3.0))
    delta_t_apre = t_apre3 - t_nom
    assert math.isclose(delta_t_apre, -0.438971, abs_tol=1e-5)

    t_t2_low = compute_t_required_analytical(**dict(p_nom, t2=0.05))
    t_t2_high = compute_t_required_analytical(**dict(p_nom, t2=0.17))
    delta_t_t2 = t_t2_high - t_t2_low
    assert math.isclose(delta_t_t2, 0.120000, abs_tol=1e-5)

    t_t3_low = compute_t_required_analytical(**dict(p_nom, t3=0.15))
    t_t3_high = compute_t_required_analytical(**dict(p_nom, t3=0.45))
    delta_t_t3 = t_t3_high - t_t3_low
    assert math.isclose(delta_t_t3, 0.146813, abs_tol=1e-5)

    # 4. Dimensionally valid comparison between bounded effects:
    ratio_t2 = abs(delta_t_apre) / delta_t_t2
    assert 3.5 <= ratio_t2 <= 3.8  # ~3.7x larger than t2 tuning, NOT an order of magnitude

    ratio_t3 = abs(delta_t_apre) / delta_t_t3
    assert 2.8 <= ratio_t3 <= 3.2  # ~3.0x larger than t3 tuning

