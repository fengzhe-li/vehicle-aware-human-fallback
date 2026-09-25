"""Tests for Experiment A1: Withdrawal Policy x Vehicle-Response Architecture.

Covers:
- Design-matrix invariant enforcement.
- W0 vs W1 policy semantics and trajectory behavior.
- Invariance and immutability of frozen human/scenario parameters.
- Rejection of W2 (excluded by design).
- Accurate T_TOR_critical computation for W1 conditions.
- Analytical interaction contrast match.
"""

import math
import numpy as np
import pytest

from src.scenarios.models import ScenarioConfig
from src.vehicle.models import VehicleResponseConfig
from src.driver.models import HumanDriverConfig, sample_human_brake_command
from src.handover.models import WithdrawalPolicy
from src.simulation.simulator import MinimalSimulator
from src.metrics.critical_tor import bisection_search_t_tor_critical
from src.metrics.oracle import (
    stopping_distance_w0_analytical,
    stopping_distance_w1_analytical,
    t_tor_critical_analytical,
)
from src.experiments.a1_runner import (
    ExperimentCondition,
    assert_design_matrix_invariants,
)


def test_design_matrix_invariants_pass():
    """Verify that invariant assertion passes when only allowed treatments differ."""
    scen = ScenarioConfig(v0=20.0, tor_lead_time=2.5)
    driver = HumanDriverConfig(t_reaction=1.0)
    veh1 = VehicleResponseConfig(t_delay=0.10, t_buildup=0.0, a_max=8.5, a_coast=0.0)
    veh2 = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=2.0)

    cond_w0 = ExperimentCondition(scen, veh1, driver, WithdrawalPolicy.W0, "R0", "W0_R0")
    cond_w1 = ExperimentCondition(scen, veh2, driver, WithdrawalPolicy.W1, "R2", "W1_R2")

    # Should pass when treatment fields are declared
    assert_design_matrix_invariants(
        cond_w0, cond_w1,
        allowed_differing_fields=["withdrawal", "a_coast", "t_buildup", "profile_name", "condition_id"]
    )


def test_design_matrix_invariants_fail_on_frozen_violation():
    """Verify that invariant assertion fails if any frozen non-treatment variable changes."""
    scen1 = ScenarioConfig(v0=20.0, tor_lead_time=2.5)
    scen2 = ScenarioConfig(v0=25.0, tor_lead_time=2.5)  # Altered v0!
    driver1 = HumanDriverConfig(t_reaction=1.0)
    driver2 = HumanDriverConfig(t_reaction=1.2)  # Altered t_reaction!
    veh = VehicleResponseConfig(t_delay=0.10, t_buildup=0.0, a_max=8.5, a_coast=0.0)

    cond1 = ExperimentCondition(scen1, veh, driver1, WithdrawalPolicy.W0, "R0", "C1")
    cond2 = ExperimentCondition(scen2, veh, driver1, WithdrawalPolicy.W1, "R0", "C2")

    # Fails due to v0 difference
    with pytest.raises(AssertionError, match="v0 differs"):
        assert_design_matrix_invariants(cond1, cond2, allowed_differing_fields=["withdrawal"])

    # Fails due to driver difference
    cond3 = ExperimentCondition(scen1, veh, driver2, WithdrawalPolicy.W1, "R0", "C3")
    with pytest.raises(AssertionError, match="t_reaction differs"):
        assert_design_matrix_invariants(cond1, cond3, allowed_differing_fields=["withdrawal"])


def test_w0_w1_policy_semantics():
    """Verify physical trajectory semantics of W0 vs W1 during [0, t_reaction).

    Under W0: automation holds v0 -> v(t_reaction) == v0, a(t) == 0.
    Under W1: automation withdraws -> a(t) == -a_coast, v(t_reaction) == v0 - a_coast * t_reaction.
    If a_coast == 0: W1 produces identical trajectory to W0.
    """
    v0 = 20.0
    t1 = 1.0
    a_coast = 2.0
    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)
    driver = HumanDriverConfig(t_reaction=t1)
    veh_coast = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=a_coast)
    veh_nocoast = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=0.0)
    sim = MinimalSimulator(dt=0.001)

    res_w0 = sim.simulate(scen, veh_coast, driver, WithdrawalPolicy.W0)
    res_w1 = sim.simulate(scen, veh_coast, driver, WithdrawalPolicy.W1)
    res_w1_nocoast = sim.simulate(scen, veh_nocoast, driver, WithdrawalPolicy.W1)

    # Find state at t = t1 (1.0s)
    idx_t1_w0 = np.argmin(np.abs(res_w0.times - t1))
    idx_t1_w1 = np.argmin(np.abs(res_w1.times - t1))

    # W0 speed at t_reaction is exactly v0
    assert math.isclose(res_w0.velocities[idx_t1_w0], v0, abs_tol=1e-6)
    # W1 speed at t_reaction is v0 - a_coast * t1 = 18.0 m/s
    expected_v1 = v0 - a_coast * t1
    assert math.isclose(res_w1.velocities[idx_t1_w1], expected_v1, abs_tol=1e-6)

    # When a_coast == 0, W1 must match W0 bit-for-bit
    assert math.isclose(res_w1_nocoast.outcomes.x_stop_full, res_w0.outcomes.x_stop_full, abs_tol=1e-9)


def test_no_accidental_w2_path():
    """Verify that W2 is excluded and cannot be specified."""
    assert "W2" not in WithdrawalPolicy.__members__
    with pytest.raises(ValueError):
        WithdrawalPolicy("W2")


def test_t_tor_critical_calculations_for_a1_conditions():
    """Verify T_TOR_critical solver reproduces analytical closed-form for W1 conditions within 0.1%."""
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    t3 = 0.50
    a_coast = 2.0

    scen = ScenarioConfig(v0=v0, tor_lead_time=3.0)
    veh = VehicleResponseConfig(t_delay=t2, t_buildup=t3, a_max=a_max, a_coast=a_coast)
    driver = HumanDriverConfig(t_reaction=t1)

    # Analytical W1 stopping distance & critical TOR
    d_ana_w1 = stopping_distance_w1_analytical(v0, a_max, t1, t2, t3, a_coast)
    t_crit_ana_w1 = t_tor_critical_analytical(v0, d_ana_w1)

    # Numerical bisection
    res_crit = bisection_search_t_tor_critical(
        scen, veh, driver, WithdrawalPolicy.W1,
        criterion="criterion_1", tor_min=0.5, tor_max=5.0, tol=1e-5,
    )

    assert res_crit.status == "CONVERGED"
    rel_err = abs(res_crit.t_tor_critical - t_crit_ana_w1) / t_crit_ana_w1
    assert rel_err < 0.001, f"Relative error {rel_err:.6e} exceeded 0.1%"


def test_a1_interaction_contrast_reproduces_analytical_prediction():
    """Verify numerical interaction contrast reproduces the analytical cross-derivative prediction.

    I = [D(W1, R2) - D(W0, R2)] - [D(W1, R0) - D(W0, R0)]
    Theoretical: -0.5 * a_coast * t_reaction * t_buildup
    """
    v0 = 20.0
    a_max = 8.5
    t1 = 1.0
    t2 = 0.10
    tb = 0.50
    ac = 2.0

    scen = ScenarioConfig(v0=v0, tor_lead_time=4.0)
    driver = HumanDriverConfig(t_reaction=t1)
    sim = MinimalSimulator(dt=0.001)

    veh_r0 = VehicleResponseConfig(t_delay=t2, t_buildup=0.0, a_max=a_max, a_coast=ac)
    veh_r2 = VehicleResponseConfig(t_delay=t2, t_buildup=tb, a_max=a_max, a_coast=ac)

    r_w0_r0 = sim.simulate(scen, veh_r0, driver, WithdrawalPolicy.W0)
    r_w0_r2 = sim.simulate(scen, veh_r2, driver, WithdrawalPolicy.W0)
    r_w1_r0 = sim.simulate(scen, veh_r0, driver, WithdrawalPolicy.W1)
    r_w1_r2 = sim.simulate(scen, veh_r2, driver, WithdrawalPolicy.W1)

    d_w0_r0 = r_w0_r0.outcomes.x_stop_full
    d_w0_r2 = r_w0_r2.outcomes.x_stop_full
    d_w1_r0 = r_w1_r0.outcomes.x_stop_full
    d_w1_r2 = r_w1_r2.outcomes.x_stop_full

    simulated_interaction = (d_w1_r2 - d_w0_r2) - (d_w1_r0 - d_w0_r0)
    expected_interaction = -0.5 * ac * t1 * tb  # -0.5 * 2.0 * 1.0 * 0.5 = -0.50 m

    assert math.isclose(simulated_interaction, expected_interaction, abs_tol=0.01), (
        f"Simulated interaction {simulated_interaction} did not match analytical {expected_interaction}"
    )


def test_policy_label_has_no_independent_physical_effect():
    """Verify that semantic policy label has no independent physical effect.

    Scientific principle: If the physical trajectory/acceleration input is identical,
    the semantic policy label itself must not change stopping outcomes.
    When a_coast = 0 under W1, the physical acceleration during [0, t_reaction) is 0.0,
    identical to W0. Outcomes must be bit-identical.
    """
    v0 = 20.0
    tor = 2.5
    scen = ScenarioConfig(v0=v0, tor_lead_time=tor)
    driver = HumanDriverConfig(t_reaction=1.0)
    sim = MinimalSimulator(dt=0.001)

    # Comparison 1: W0 vs W1 with a_coast = 0.0
    veh_zero_coast = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=0.0)
    res_w0 = sim.simulate(scen, veh_zero_coast, driver, WithdrawalPolicy.W0)
    res_w1_nocoast = sim.simulate(scen, veh_zero_coast, driver, WithdrawalPolicy.W1)

    assert res_w0.outcomes.stopping_margin == res_w1_nocoast.outcomes.stopping_margin
    assert res_w0.outcomes.collision == res_w1_nocoast.outcomes.collision
    assert res_w0.outcomes.x_stop_full == res_w1_nocoast.outcomes.x_stop_full
    assert np.array_equal(res_w0.positions, res_w1_nocoast.positions)
    assert np.array_equal(res_w0.velocities, res_w1_nocoast.velocities)
    assert np.array_equal(res_w0.accelerations, res_w1_nocoast.accelerations)

    # Comparison 2: Under W0, varying a_coast has zero physical effect
    veh_coast_2 = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=2.0)
    res_w0_coast2 = sim.simulate(scen, veh_coast_2, driver, WithdrawalPolicy.W0)

    assert res_w0.outcomes.stopping_margin == res_w0_coast2.outcomes.stopping_margin
    assert np.array_equal(res_w0.accelerations, res_w0_coast2.accelerations)

