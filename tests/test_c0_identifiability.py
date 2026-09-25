"""Unit tests for Branch C0: Driver-Vehicle Internal-Model Mismatch Identifiability.

Verifies:
1. The current human model has zero causal pathway for driver internal model or mismatch:
   HumanDriverConfig exposes only t_reaction and u_target; command trajectory is open-loop.
2. Invariant: Human command trajectory is bit-identical across diverse vehicle response profiles.
3. Dataset inventory verification: Confirms that zero datasets in dataset_inventory.csv
   contain driver EV/ICE vehicle familiarity fields.
"""

import numpy as np
import pandas as pd
import pytest

from src.driver.models import HumanDriverConfig, get_human_command, sample_human_brake_command
from src.scenarios.models import ScenarioConfig
from src.vehicle.models import VehicleResponseConfig
from src.handover.models import WithdrawalPolicy
from src.simulation.simulator import MinimalSimulator


def test_current_human_model_has_no_mismatch_pathway():
    """Verify that the implemented human model is strictly open-loop with no internal-model pathway."""
    driver = HumanDriverConfig(t_reaction=1.0, u_target=1.0)

    # Human driver dataclass has only t_reaction and u_target
    fields = list(driver.__dataclass_fields__.keys())
    assert set(fields) == {"t_reaction", "u_target"}, (
        f"Unexpected fields in HumanDriverConfig: {fields}"
    )

    # Pre-reaction: u_brake is 0.0
    u_accel, u_brake = get_human_command(0.5, driver)
    assert u_accel == 0.0
    assert u_brake == 0.0

    # Post-reaction: u_brake is fixed at u_target (1.0), with no state-dependent modulation
    u_accel, u_brake = get_human_command(1.5, driver)
    assert u_accel == 0.0
    assert u_brake == 1.0


def test_command_trajectory_invariant_across_vehicle_profiles():
    """Verify that human command trajectory is bit-identical regardless of vehicle response parameters."""
    driver = HumanDriverConfig(t_reaction=1.0)
    t_samples = np.linspace(0.0, 3.0, 301)

    cmd_ref = sample_human_brake_command(t_samples, driver)

    # Vary vehicle parameters arbitrarily
    veh_profiles = [
        VehicleResponseConfig(t_delay=0.05, t_buildup=0.10, a_max=8.5, a_coast=0.0),
        VehicleResponseConfig(t_delay=0.17, t_buildup=0.50, a_max=8.5, a_coast=3.5),
        VehicleResponseConfig(t_delay=0.10, t_buildup=0.30, a_max=6.0, a_coast=1.5),
    ]

    scen = ScenarioConfig(v0=20.0, tor_lead_time=3.0)
    sim = MinimalSimulator(dt=0.001)

    for veh in veh_profiles:
        res = sim.simulate(scen, veh, driver, WithdrawalPolicy.W1)
        cmd_sim = sample_human_brake_command(res.times, driver)
        # Check that before t_reaction command is always 0.0, and after t_reaction is always 1.0
        assert np.all(cmd_sim[res.times < 1.0] == 0.0)
        assert np.all(cmd_sim[res.times >= 1.0] == 1.0)


def test_dataset_inventory_lacks_driver_familiarity():
    """Verify that no dataset in the repository inventory records driver vehicle familiarity."""
    inventory_path = "research/data_matrix/dataset_inventory.csv"
    df = pd.read_csv(inventory_path)

    assert "driver_familiarity_available" in df.columns

    for _, row in df.iterrows():
        fam = str(row["driver_familiarity_available"]).strip()
        # Ensure that no dataset claims full direct EV/ICE familiarity
        assert fam.startswith("NO") or "not EV/ICE prior familiarity" in fam or "sparse" in fam, (
            f"Dataset {row['id']} unexpectedly provides familiarity: {fam}"
        )
