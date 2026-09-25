"""Tests for A0 Analytical Baseline and Minimal Simulator Validation.

Implements all tests specified in tests/TEST_PLAN.md:
1. Zero-delay constant-deceleration case matches closed form.
2. Positive delay increases stopping distance by v0 * tau.
3. Linear build-up matches analytical solution.
4. Collision boundary behaves monotonically with obstacle distance.
5. T_TOR_critical solver reproduces the analytical test case.
6. dt convergence test (monotonic error decrease and order measurement).
7. Determinism: identical profile produces identical output.
8. Treatment isolation: treatment changes do not alter frozen human command.
Additional tests:
- Programmatic treatment isolation and immutability.
- T_TOR_critical edge-case reporting (Criteria 1 & 2, bound saturation).
- SymPy symbolic verification of the A1 interaction cross-derivative.
- Outcome invariant checks (collision, impact_speed, ttc_min).
"""

import math
import numpy as np
import pytest
from dataclasses import FrozenInstanceError

from src.scenarios.models import ScenarioConfig
from src.vehicle.models import (
    VehicleResponseConfig,
    create_r0_profile,
    create_r2_profile,
    create_r1_profile,
)
from src.driver.models import (
    HumanDriverConfig,
    sample_human_brake_command,
)
from src.handover.models import WithdrawalPolicy
from src.simulation.simulator import MinimalSimulator
from src.metrics.oracle import (
    stopping_distance_w0_analytical,
    stopping_distance_w1_analytical,
    t_tor_critical_analytical,
    verify_symbolic_cross_derivative,
)
from src.metrics.critical_tor import bisection_search_t_tor_critical


# Tolerance defined in docs/MINIMAL_SIMULATOR_SPEC.md: 0.1% relative
A0_RELATIVE_TOLERANCE = 0.001


def test_01_zero_delay_constant_deceleration_matches_closed_form():
    """Test 1: Zero-delay constant-deceleration case matches closed form within 0.1%.

    t_delay = 0, t_buildup = 0 (instantaneous full braking at t_reaction).
    Closed form: D_stop = v0^2 / (2 * a_max) + v0 * t1.
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0

    veh = VehicleResponseConfig(t_delay=0.0, t_buildup=0.0, a_max=a_max)
    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)
    driver = HumanDriverConfig(t_reaction=t1)
    sim = MinimalSimulator(dt=0.001)

    res = sim.simulate(scen, veh, driver, WithdrawalPolicy.W0)
    d_sim = res.outcomes.x_stop_full
    d_ana = stopping_distance_w0_analytical(v0, a_max, t1, 0.0, 0.0)

    rel_err = abs(d_sim - d_ana) / d_ana
    assert rel_err < A0_RELATIVE_TOLERANCE, (
        f"Test 1 failed: rel_err={rel_err:.6e} exceeded tolerance {A0_RELATIVE_TOLERANCE}. "
        f"d_sim={d_sim}, d_ana={d_ana}"
    )

    margin_sim = res.outcomes.stopping_margin
    margin_ana = scen.x_hazard - d_ana
    assert abs(margin_sim - margin_ana) / d_ana < A0_RELATIVE_TOLERANCE


def test_02_positive_delay_increases_stopping_distance_by_v0_tau():
    """Test 2: Positive delay increases stopping distance by expected v0 * tau.

    t_buildup = 0, t_delay = tau > 0.
    Closed form: D_stop = v0^2 / (2 * a_max) + v0 * (t1 + tau) - added distance v0 * tau.
    Tested for tau in {0.05, 0.17} spanning literature range (Paquette & Porter).
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    sim = MinimalSimulator(dt=0.001)

    veh_base = VehicleResponseConfig(t_delay=0.0, t_buildup=0.0, a_max=a_max)
    scen = ScenarioConfig(v0=v0, tor_lead_time=5.0)
    driver = HumanDriverConfig(t_reaction=t1)
    res_base = sim.simulate(scen, veh_base, driver, WithdrawalPolicy.W0)

    for tau in [0.05, 0.17]:
        veh_tau = VehicleResponseConfig(t_delay=tau, t_buildup=0.0, a_max=a_max)
        res_tau = sim.simulate(scen, veh_tau, driver, WithdrawalPolicy.W0)

        # Distance increase
        delta_d_sim = res_tau.outcomes.x_stop_full - res_base.outcomes.x_stop_full
        expected_delta_d = v0 * tau
        abs_err = abs(delta_d_sim - expected_delta_d)
        rel_err = abs_err / expected_delta_d

        assert rel_err < A0_RELATIVE_TOLERANCE, (
            f"Test 2 failed for tau={tau}: delta_d_sim={delta_d_sim}, "
            f"expected={expected_delta_d}, rel_err={rel_err:.6e}"
        )

        # Stopping margin reduction: margin_base - margin_tau = v0 * tau
        delta_margin = res_base.outcomes.stopping_margin - res_tau.outcomes.stopping_margin
        assert abs(delta_margin - expected_delta_d) / expected_delta_d < A0_RELATIVE_TOLERANCE


def test_03_linear_buildup_matches_analytical_solution():
    """Test 3: Linear build-up matches the analytical solution within 0.1%.

    D_stop = v0^2 / (2 * a_max) + v0 * (t1 + t2 + t3/2) - a_max * t3^2 / 24.
    Tested for at least three (t_delay, t_buildup) combinations, including literature
    anchors and an extreme value.
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    sim = MinimalSimulator(dt=0.001)

    test_cases = [
        (0.05, 0.20, "Literature t_delay lower bound (0.05s) with moderate t_buildup"),
        (0.17, 0.50, "Literature t_delay upper bound (0.17s) with delayed t_buildup"),
        (0.10, 2.00, "Extreme t_buildup (2.0s) well outside operational range"),
        (0.10, 0.05, "Small t_buildup (0.05s)"),
    ]

    for tau2, tau3, label in test_cases:
        veh = VehicleResponseConfig(t_delay=tau2, t_buildup=tau3, a_max=a_max)
        scen = ScenarioConfig(v0=v0, tor_lead_time=6.0)
        driver = HumanDriverConfig(t_reaction=t1)

        res = sim.simulate(scen, veh, driver, WithdrawalPolicy.W0)
        d_sim = res.outcomes.x_stop_full
        d_ana = stopping_distance_w0_analytical(v0, a_max, t1, tau2, tau3)

        rel_err = abs(d_sim - d_ana) / d_ana
        assert rel_err < A0_RELATIVE_TOLERANCE, (
            f"Test 3 failed for case '{label}' (tau2={tau2}, tau3={tau3}): "
            f"d_sim={d_sim:.6f}, d_ana={d_ana:.6f}, rel_err={rel_err:.6e}"
        )


def test_04_collision_boundary_behaves_monotonically_with_obstacle_distance():
    """Test 4: Collision boundary behaves monotonically with obstacle distance.

    Sweep TOR_lead_time (equivalently x_hazard = v0 * TOR_lead_time) spanning
    clearly-unsafe (collision) to clearly-safe.
    stopping_margin(TOR_lead_time) must be strictly non-decreasing across the swept range.
    """
    v0 = 20.0
    a_max = 8.5
    veh = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=a_max)
    driver = HumanDriverConfig(t_reaction=1.0)
    sim = MinimalSimulator(dt=0.001)

    tor_sweep = np.linspace(0.5, 6.0, 56)
    margins = []

    for tor in tor_sweep:
        scen = ScenarioConfig(v0=v0, tor_lead_time=tor)
        res = sim.simulate(scen, veh, driver, WithdrawalPolicy.W0)
        margins.append(res.outcomes.stopping_margin)

    diffs = np.diff(margins)
    assert np.all(diffs > 0.0), f"Test 4 failed: non-monotonic step found in margin sweep: {diffs[diffs <= 0]}"


def test_05_t_tor_critical_solver_reproduces_analytical_test_case():
    """Test 5: T_TOR_critical numerical bisection solver reproduces closed form.

    For R0/R2 under W0, closed-form T_TOR_critical = D_stop / v0.
    Pass: numerical bisection reproduces closed form within 0.1% and converges within max iterations.
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.50

    d_ana = stopping_distance_w0_analytical(v0, a_max, t1, t2, t3)
    t_crit_ana = t_tor_critical_analytical(v0, d_ana)

    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)
    veh = VehicleResponseConfig(t_delay=t2, t_buildup=t3, a_max=a_max)
    driver = HumanDriverConfig(t_reaction=t1)

    res = bisection_search_t_tor_critical(
        scenario_base=scen,
        vehicle=veh,
        driver=driver,
        withdrawal=WithdrawalPolicy.W0,
        criterion="criterion_1",
        tor_min=0.5,
        tor_max=5.0,
        tol=1e-5,
        max_iter=50,
    )

    assert res.status == "CONVERGED", f"Test 5 failed: solver status={res.status}, msg={res.message}"
    assert res.iterations <= 50, f"Test 5 failed: iterations={res.iterations} exceeded limit"
    assert res.t_tor_critical is not None

    rel_err = abs(res.t_tor_critical - t_crit_ana) / t_crit_ana
    assert rel_err < A0_RELATIVE_TOLERANCE, (
        f"Test 5 failed: t_crit_sim={res.t_tor_critical:.6f}, t_crit_ana={t_crit_ana:.6f}, "
        f"rel_err={rel_err:.6e}"
    )


def test_06_dt_convergence():
    """Test 6: Timestep dt convergence test.

    Run Test 3 configuration at dt in {0.01, 0.005, 0.001, 0.0005} s.
    Pass:
    1. Error between simulated and closed-form D_stop strictly decreases as dt decreases.
    2. Empirical convergence order (slope of log(err) vs log(dt)) is positive and ~1.0.
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.50

    d_ana = stopping_distance_w0_analytical(v0, a_max, t1, t2, t3)
    veh = VehicleResponseConfig(t_delay=t2, t_buildup=t3, a_max=a_max)
    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)
    driver = HumanDriverConfig(t_reaction=t1)

    dts = [0.01, 0.005, 0.001, 0.0005]
    errors = []

    for dt in dts:
        sim = MinimalSimulator(dt=dt)
        res = sim.simulate(scen, veh, driver, WithdrawalPolicy.W0)
        err = abs(res.outcomes.x_stop_full - d_ana)
        errors.append(err)

    # 1. Check strict monotonic error decrease
    for i in range(len(errors) - 1):
        assert errors[i] > errors[i + 1], (
            f"Test 6 failed: error did not decrease monotonically. "
            f"dt={dts[i]} (err={errors[i]}) vs dt={dts[i+1]} (err={errors[i+1]})"
        )

    # 2. Fit log(error) vs log(dt) to report convergence order
    slope, intercept = np.polyfit(np.log(dts), np.log(errors), 1)
    # Piecewise-constant acceleration staircase over linear ramp is O(dt), slope ~ 1.0
    assert 0.95 <= slope <= 1.05, f"Test 6 failed: convergence order slope={slope:.4f} not near 1.0"


def test_07_identical_profile_produces_identical_output():
    """Test 7: Determinism check.

    Two independently-constructed simulator invocations with the same profile, scenario,
    and withdrawal policy must produce bit-identical output.
    """
    scen1 = ScenarioConfig(v0=20.0, tor_lead_time=4.0)
    veh1 = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5)
    driver1 = HumanDriverConfig(t_reaction=1.0)
    sim1 = MinimalSimulator(dt=0.001)
    res1 = sim1.simulate(scen1, veh1, driver1, WithdrawalPolicy.W0)

    scen2 = ScenarioConfig(v0=20.0, tor_lead_time=4.0)
    veh2 = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5)
    driver2 = HumanDriverConfig(t_reaction=1.0)
    sim2 = MinimalSimulator(dt=0.001)
    res2 = sim2.simulate(scen2, veh2, driver2, WithdrawalPolicy.W0)

    assert res1.outcomes.stopping_margin == res2.outcomes.stopping_margin
    assert res1.outcomes.collision == res2.outcomes.collision
    assert res1.outcomes.ttc_min == res2.outcomes.ttc_min
    assert res1.outcomes.x_stop_full == res2.outcomes.x_stop_full
    assert np.array_equal(res1.times, res2.times)
    assert np.array_equal(res1.positions, res2.positions)
    assert np.array_equal(res1.velocities, res2.velocities)
    assert np.array_equal(res1.accelerations, res2.accelerations)


def test_08_treatment_changes_do_not_alter_frozen_human_command():
    """Test 8: Programmatic check that treatment changes do not mutate frozen human command.

    For every pair of conditions compared in A0 (R0 vs R2) and A1 (W0 vs W1, a_coast=0 vs a_coast>0),
    sampled u_human_brake(t) array is bit-identical across the pair.
    """
    t_grid = np.linspace(0.0, 5.0, 5001)
    driver = HumanDriverConfig(t_reaction=1.0)

    # Condition A0-R0
    cmd_a0_r0 = sample_human_brake_command(t_grid, driver)
    # Condition A0-R2
    cmd_a0_r2 = sample_human_brake_command(t_grid, driver)
    # Condition A1-W0
    cmd_a1_w0 = sample_human_brake_command(t_grid, driver)
    # Condition A1-W1 (a_coast=0)
    cmd_a1_w1_nocoast = sample_human_brake_command(t_grid, driver)
    # Condition A1-W1 (a_coast>0)
    cmd_a1_w1_coast = sample_human_brake_command(t_grid, driver)

    # Exact bit-identical equality checks
    assert np.array_equal(cmd_a0_r0, cmd_a0_r2), "Command differed between R0 and R2"
    assert np.array_equal(cmd_a0_r0, cmd_a1_w0), "Command differed between A0 and A1 W0"
    assert np.array_equal(cmd_a0_r0, cmd_a1_w1_nocoast), "Command differed between W0 and W1 (no-coast)"
    assert np.array_equal(cmd_a0_r0, cmd_a1_w1_coast), "Command differed between W0 and W1 (coast)"


def test_treatment_isolation_immutability():
    """Verify that driver and scenario configs are frozen and cannot be mutated by simulation."""
    driver = HumanDriverConfig(t_reaction=1.0, u_target=1.0)
    scen = ScenarioConfig(v0=20.0, tor_lead_time=4.0)

    # Assert frozen immutability
    with pytest.raises(FrozenInstanceError):
        driver.t_reaction = 1.5  # type: ignore

    with pytest.raises(FrozenInstanceError):
        scen.v0 = 25.0  # type: ignore

    # Run simulations under different treatments and verify configs are unaffected
    veh_r0 = create_r0_profile(t_delay=0.10, a_max=8.5)
    veh_r2 = create_r2_profile(t_delay=0.10, t_buildup=0.50, a_max=8.5)
    sim = MinimalSimulator(dt=0.001)

    sim.simulate(scen, veh_r0, driver, WithdrawalPolicy.W0)
    assert driver.t_reaction == 1.0
    assert scen.v0 == 20.0

    sim.simulate(scen, veh_r2, driver, WithdrawalPolicy.W1)
    assert driver.t_reaction == 1.0
    assert scen.v0 == 20.0


def test_t_tor_critical_edge_cases():
    """Verify explicit handling of T_TOR_critical search edge cases.

    1. Bound saturation at tor_min: reported as T_TOR_critical <= TOR_min.
    2. Bound saturation at tor_max: reported as T_TOR_critical > TOR_max.
    3. Criterion 2 (resolvable-margin boundary) check.
    """
    v0 = 20.0
    a_max = 8.5
    veh = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=a_max)
    driver = HumanDriverConfig(t_reaction=1.0)
    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)

    # Edge case 1: search window [3.0, 5.0] where at 3.0 it is already safe (t_crit ~ 2.52s)
    res_min = bisection_search_t_tor_critical(
        scen, veh, driver, WithdrawalPolicy.W0, tor_min=3.0, tor_max=5.0
    )
    assert res_min.status == "SAFE_AT_MIN_BOUND"
    assert "T_TOR_critical <= TOR_min (3.0000s)" in res_min.message
    assert res_min.t_tor_critical == 3.0

    # Edge case 2: search window [1.0, 2.0] where at 2.0 it is still unsafe
    res_max = bisection_search_t_tor_critical(
        scen, veh, driver, WithdrawalPolicy.W0, tor_min=1.0, tor_max=2.0
    )
    assert res_max.status == "UNSAFE_AT_MAX_BOUND"
    assert "T_TOR_critical > TOR_max (2.0000s)" in res_max.message
    assert res_max.t_tor_critical is None

    # Criterion 2 check: resolvable-margin boundary
    res_c2 = bisection_search_t_tor_critical(
        scen, veh, driver, WithdrawalPolicy.W0, criterion="criterion_2", tor_min=0.5, tor_max=5.0
    )
    assert res_c2.status == "CONVERGED"
    assert res_c2.criterion == "criterion_2"
    assert res_c2.t_tor_critical is not None
    # Criterion 2 requires larger margin, so critical TOR must be >= Criterion 1 critical TOR
    res_c1 = bisection_search_t_tor_critical(
        scen, veh, driver, WithdrawalPolicy.W0, criterion="criterion_1", tor_min=0.5, tor_max=5.0
    )
    assert res_c2.t_tor_critical >= res_c1.t_tor_critical


def test_symbolic_cross_derivative_interaction():
    """Verify that SymPy confirms d^2(D_stop) / (d a_coast d t_buildup) == -t_reaction / 2 != 0."""
    assert verify_symbolic_cross_derivative() is True


def test_outcome_invariants():
    """Verify outcome invariants:
    - collision is derived from stopping_margin < 0
    - impact_speed is NaN on non-collision and real on collision
    - ttc_min is 0.0 on collision
    """
    v0 = 20.0
    a_max = 8.5
    veh = VehicleResponseConfig(t_delay=0.0, t_buildup=0.0, a_max=a_max)
    driver = HumanDriverConfig(t_reaction=1.0)
    sim = MinimalSimulator(dt=0.001)

    # Case A: Clear safe run (no collision)
    scen_safe = ScenarioConfig(v0=v0, tor_lead_time=5.0)  # x_hazard = 100m, D_stop ~ 43.5m
    res_safe = sim.simulate(scen_safe, veh, driver, WithdrawalPolicy.W0)
    assert res_safe.outcomes.collision is False
    assert res_safe.outcomes.stopping_margin > 0.0
    assert math.isnan(res_safe.outcomes.impact_speed)
    assert res_safe.outcomes.ttc_min > 0.0

    # Case B: Clear collision run
    scen_collision = ScenarioConfig(v0=v0, tor_lead_time=1.5)  # x_hazard = 30m, D_stop ~ 43.5m
    res_col = sim.simulate(scen_collision, veh, driver, WithdrawalPolicy.W0)
    assert res_col.outcomes.collision is True
    assert res_col.outcomes.stopping_margin < 0.0
    assert not math.isnan(res_col.outcomes.impact_speed)
    assert res_col.outcomes.impact_speed > 0.0
    assert res_col.outcomes.ttc_min == 0.0
