"""R3B model corrections: friction limit (A), authority timing (B), braking command path (C),
legacy reproduction, and closed-form vs simulator agreement for the generalised model."""

import numpy as np
import pytest

from src.driver.models import HumanDriverConfig
from src.handover.models import (ControlAuthority, HandoverTimeline, PreControlProfile, WithdrawalPolicy,
                                 get_control_authority, legacy_equivalent)
from src.metrics.oracle import (stopping_distance_r3b_analytical, stopping_distance_w0_analytical,
                                stopping_distance_w1_analytical)
from src.scenarios.models import ScenarioConfig
from src.simulation.simulator import MinimalSimulator
from src.vehicle.models import GRAVITY, VehicleResponseConfig, calculate_acceleration, effective_braking_deceleration

VEH = VehicleResponseConfig(t_delay=0.10, t_buildup=0.50, a_max=8.5, a_coast=2.0)
SIM = MinimalSimulator(dt=0.001)
REL_TOL = 1e-3  # A0 tolerance, reused


# --- A. friction ----------------------------------------------------------------------------


def test_friction_non_binding_reproduces_previous_result():
    assert effective_braking_deceleration(8.5, 1.0, 1.0) == 8.5          # 9.81 > 8.5
    assert effective_braking_deceleration(8.5, 1.0, None) == 8.5         # legacy: no cap
    scen = ScenarioConfig(v0=27.8, tor_lead_time=6.0, road_friction=1.0)
    d = SIM.simulate(scen, VEH).outcomes.x_stop_full
    assert d == pytest.approx(stopping_distance_w0_analytical(27.8, 8.5, 1.0, 0.1, 0.5), rel=REL_TOL)


def test_friction_binding_caps_deceleration():
    assert effective_braking_deceleration(8.5, 1.0, 0.5) == pytest.approx(0.5 * GRAVITY)
    scen = ScenarioConfig(v0=27.8, tor_lead_time=9.0, road_friction=0.5)
    res = SIM.simulate(scen, VEH)
    assert res.accelerations.min() == pytest.approx(-0.5 * GRAVITY)
    d_expected = stopping_distance_r3b_analytical(27.8, 8.5, 1.0, 0.1, 0.5, 1.0, 0.0, 0.0, 1.0, 0.5)
    assert res.outcomes.x_stop_full == pytest.approx(d_expected, rel=REL_TOL)


def test_braking_capability_monotone_in_friction():
    mus = np.linspace(0.1, 1.2, 23)
    caps = [effective_braking_deceleration(8.5, 1.0, m) for m in mus]
    assert all(b >= a for a, b in zip(caps, caps[1:]))
    d = [stopping_distance_r3b_analytical(27.8, 8.5, 1.5, 0.1, 0.6, 1.5, 0, 0, 1.0, m) for m in mus]
    assert all(b <= a + 1e-12 for a, b in zip(d, d[1:]))


def test_units_and_sign_convention():
    assert GRAVITY == 9.81
    a = calculate_acceleration(5.0, 20.0, VEH, road_friction=0.3)  # steady braking phase
    assert a == pytest.approx(-0.3 * 9.81) and a < 0
    with pytest.raises(ValueError):
        effective_braking_deceleration(8.5, 1.0, 0.0)


# --- B. authority timing ------------------------------------------------------------------


def test_timeline_invariants():
    HandoverTimeline(t_authority=0.0, t_effective=1.5)          # authority at TOR
    HandoverTimeline(t_authority=1.0, t_effective=1.5, t_first_input=0.3)  # delayed
    for bad in (dict(t_authority=-0.1, t_effective=1.0), dict(t_authority=2.0, t_effective=1.0),
                dict(t_authority=0.5, t_effective=1.0, t_first_input=1.2)):
        with pytest.raises(ValueError):
            HandoverTimeline(**bad)


def test_authority_is_separate_from_tor_and_effective_control():
    tl = HandoverTimeline(t_authority=0.8, t_effective=2.0)
    assert get_control_authority(0.5, tl.t_effective, tl.t_authority) == ControlAuthority.AUTOMATION
    assert get_control_authority(1.0, tl.t_effective, tl.t_authority) == ControlAuthority.HUMAN
    assert get_control_authority(1.0, 2.0) == ControlAuthority.AUTOMATION  # legacy call unchanged
    pc = PreControlProfile(a_before_authority=2.0, a_after_authority=0.3)
    res = SIM.simulate(ScenarioConfig(v0=27.8, tor_lead_time=8.0), VEH, timeline=tl, pre_control=pc)
    t, a = res.times, res.accelerations
    assert np.allclose(a[(t > 0.01) & (t < 0.79)], -2.0)      # policy command before authority
    assert np.allclose(a[(t > 0.81) & (t < 1.99)], -0.3)      # vehicle-only after authority
    assert res.commands[t < 1.99].max() == 0.0 and res.commands[t > 2.0].min() == 1.0


def test_delayed_authority_changes_outcome_only_through_pre_control():
    base = dict(v0=27.8, a_max=8.5, t_effective=2.0, t_delay=0.1, t_buildup=0.6, u_brake=1.0, road_friction=1.0)
    same = [stopping_distance_r3b_analytical(**base, t_authority=ta, a_before_authority=0.3, a_after_authority=0.3)
            for ta in (0.0, 1.0, 2.0)]
    assert max(same) - min(same) < 1e-9  # identical profiles: authority timing has no longitudinal effect
    hold = [stopping_distance_r3b_analytical(**base, t_authority=ta, a_before_authority=0.0, a_after_authority=0.3)
            for ta in (0.0, 1.0, 2.0)]
    assert hold[0] < hold[1] < hold[2]


# --- C. braking command ---------------------------------------------------------------------


def test_command_propagates_to_vehicle_response():
    scen = ScenarioConfig(v0=20.0, tor_lead_time=20.0)
    half = SIM.simulate(scen, VEH, HumanDriverConfig(t_reaction=1.0, u_target=0.5))
    full = SIM.simulate(scen, VEH, HumanDriverConfig(t_reaction=1.0, u_target=1.0))
    assert half.accelerations.min() == pytest.approx(-4.25)
    assert full.accelerations.min() == pytest.approx(-8.5)
    assert half.u_brake == 0.5 and {s.u_brake for s in half.trajectory} <= {0.0, 0.5}
    assert half.outcomes.x_stop_full > full.outcomes.x_stop_full
    assert effective_braking_deceleration(8.5, 0.5, 0.5) == pytest.approx(4.25)  # min(u*a_max, mu*g)
    assert effective_braking_deceleration(8.5, 0.0, 1.0) == 0.0


# --- legacy reproduction --------------------------------------------------------------------


@pytest.mark.parametrize("withdrawal", [WithdrawalPolicy.W0, WithdrawalPolicy.W1])
def test_legacy_nominal_case_reproduced_by_corrected_model(withdrawal):
    scen = ScenarioConfig(v0=20.0, tor_lead_time=5.0)
    drv = HumanDriverConfig(t_reaction=1.0)
    legacy = SIM.simulate(scen, VEH, drv, withdrawal)
    tl, pc = legacy_equivalent(withdrawal, drv.t_reaction, VEH.a_coast)
    new = SIM.simulate(scen, VEH, drv, withdrawal, timeline=tl, pre_control=pc)
    assert np.array_equal(legacy.positions, new.positions)
    assert np.array_equal(legacy.velocities, new.velocities)
    assert legacy.outcomes.stopping_margin == new.outcomes.stopping_margin
    closed = (stopping_distance_w0_analytical(20.0, 8.5, 1.0, 0.1, 0.5) if withdrawal == WithdrawalPolicy.W0
              else stopping_distance_w1_analytical(20.0, 8.5, 1.0, 0.1, 0.5, 2.0))
    general = stopping_distance_r3b_analytical(20.0, 8.5, 1.0, 0.1, 0.5, tl.t_authority,
                                               pc.a_before_authority, pc.a_after_authority)
    assert general == pytest.approx(closed, abs=1e-9)


# --- closed form vs simulator ---------------------------------------------------------------


@pytest.mark.parametrize("v0,mu,t1,ta,a_b,a_a,t3", [
    (16.7, 1.0, 1.15, 1.15, 0.0, 0.13, 0.3), (27.8, 0.5, 3.0, 0.0, 0.0, 0.40, 1.2),
    (36.1, 1.0, 2.0, 1.2, 3.0, 0.59, 0.6), (16.7, 0.5, 3.0, 3.0, 3.0, 0.13, 1.2),
])
def test_general_closed_form_matches_simulator(v0, mu, t1, ta, a_b, a_a, t3):
    veh = VehicleResponseConfig(t_delay=0.17, t_buildup=t3, a_max=9.1)
    res = SIM.simulate(ScenarioConfig(v0=v0, tor_lead_time=30.0, road_friction=mu), veh,
                       timeline=HandoverTimeline(t_authority=ta, t_effective=t1),
                       pre_control=PreControlProfile(a_b, a_a))
    d = stopping_distance_r3b_analytical(v0, 9.1, t1, 0.17, t3, ta, a_b, a_a, 1.0, mu)
    assert res.outcomes.x_stop_full == pytest.approx(d, rel=REL_TOL)


def test_closed_form_handles_standstill_inside_ramp_and_pre_control():
    d_ramp = stopping_distance_r3b_analytical(2.0, 8.5, 0.5, 0.0, 1.0, 0.5, 0.0, 0.0)
    res = SIM.simulate(ScenarioConfig(v0=2.0, tor_lead_time=30.0), VehicleResponseConfig(t_delay=0.0, t_buildup=1.0, a_max=8.5),
                       timeline=HandoverTimeline(0.5, 0.5), pre_control=PreControlProfile(0.0, 0.0))
    assert res.outcomes.x_stop_full == pytest.approx(d_ramp, rel=REL_TOL)
    assert stopping_distance_r3b_analytical(5.0, 8.5, 3.0, 0.1, 0.5, 3.0, 3.0, 0.0) == pytest.approx(25 / 6.0)
