"""Unit tests for Phase 2B-1 empirical recovery analysis module."""

import numpy as np
import pandas as pd
import pytest

from src.data.d003_loader import TrialMeta
from src.experiments.h1_recovery_analysis import (
    compute_trial_qa,
    extract_trial_metrics,
)


def _make_synthetic_trial(
    has_tor: bool = True,
    tor_time: float = 10.0,
    man_start_time: float = 11.5,
    collision: bool = False,
    steer_before_brake: bool = False,
) -> pd.DataFrame:
    """Generate a synthetic 20Hz trial DataFrame."""
    dt = 0.05
    n_samples = 600  # 30s at 20Hz
    t = np.linspace(0.0, (n_samples - 1) * dt, n_samples)

    df = pd.DataFrame({
        "time": t,
        "TOR_request": np.full(n_samples, tor_time if has_tor else np.nan),
        "manual_start": np.full(n_samples, man_start_time),
        "manual_stop": np.full(n_samples, 28.0),
        "lane_change_time": np.full(n_samples, 15.0),
        "lane_id": np.full(n_samples, 2.0),
        "brake_force": np.zeros(n_samples),
        "accelerator": np.full(n_samples, 0.12),
        "steering_angle": np.zeros(n_samples),
        "steering_speed": np.zeros(n_samples),
        "longitudinal_speed": np.full(n_samples, 25.0),
        "longitudinal_acceleration": np.zeros(n_samples),
        "lateral_acceleration": np.zeros(n_samples),
        "distance_to_obstacle": np.linspace(200.0, 10.0 if not collision else -5.0, n_samples),
    })

    # Add braking
    if steer_before_brake:
        # Steer at 11.0, brake at 12.0
        steer_idx = int(11.0 / dt)
        df.loc[steer_idx:, "steering_angle"] = 0.10
        df.loc[steer_idx:, "steering_speed"] = 0.20
        df.loc[steer_idx:, "lateral_acceleration"] = 0.60
        brake_idx = int(12.0 / dt)
        df.loc[brake_idx:, "brake_force"] = 60.0
        df.loc[brake_idx:, "longitudinal_acceleration"] = -2.0
    else:
        # Brake at 11.0, steer at 13.0
        brake_idx = int(11.0 / dt)
        df.loc[brake_idx:, "brake_force"] = 60.0
        df.loc[brake_idx:, "longitudinal_acceleration"] = -2.0
        steer_idx = int(13.0 / dt)
        df.loc[steer_idx:, "steering_angle"] = 0.10
        df.loc[steer_idx:, "steering_speed"] = 0.20
        df.loc[steer_idx:, "lateral_acceleration"] = 0.60

    if collision:
        df["distance_to_obstacle"] = -2.0
        df["longitudinal_speed"] = 20.0
        df["lane_change_time"] = np.nan

    return df


def test_synthetic_trial_qa_normal():
    meta = TrialMeta(
        density=0,
        nback=0,
        participant_id=1,
        scenario_id="density_0_nback_0",
        trial_id="trial_001",
        relative_path="dummy.csv",
    )
    df = _make_synthetic_trial(has_tor=True, collision=False)
    qa = compute_trial_qa(df, meta)

    assert qa["usable_status"] == "USABLE_FULL"
    assert qa["reason_code"] == "NONE"
    assert qa["is_strictly_monotonic"] is True
    assert qa["has_tor_request"] is True
    assert qa["has_manual_start"] is True
    assert np.isclose(qa["delta_t_manual_start"], 1.5, atol=0.01)


def test_synthetic_trial_qa_preemptive():
    meta = TrialMeta(
        density=0,
        nback=0,
        participant_id=2,
        scenario_id="density_0_nback_0",
        trial_id="trial_002",
        relative_path="dummy.csv",
    )
    df = _make_synthetic_trial(has_tor=False, collision=False)
    qa = compute_trial_qa(df, meta)

    assert qa["usable_status"] == "USABLE_PREEMPTIVE"
    assert qa["reason_code"] == "PREEMPTIVE_TAKEOVER_NO_TOR_ISSUED"
    assert qa["has_tor_request"] is False


def test_synthetic_trial_qa_collision():
    meta = TrialMeta(
        density=0,
        nback=0,
        participant_id=3,
        scenario_id="density_0_nback_0",
        trial_id="trial_003",
        relative_path="dummy.csv",
    )
    df = _make_synthetic_trial(has_tor=True, collision=True)
    qa = compute_trial_qa(df, meta)

    assert qa["usable_status"] == "COLLISION_FAILURE"
    assert qa["reason_code"] == "COLLISION_WITH_HAZARD"
    assert qa["collision_outcome"] is True


def test_extract_trial_metrics_brake_first():
    meta = TrialMeta(
        density=0,
        nback=0,
        participant_id=1,
        scenario_id="density_0_nback_0",
        trial_id="trial_001",
        relative_path="dummy.csv",
    )
    df = _make_synthetic_trial(has_tor=True, steer_before_brake=False)
    m = extract_trial_metrics(df, meta)

    assert m["first_action_type"] == "BRAKE_FIRST"
    assert m["T_first_brake"] < m["T_first_steer"]
    assert np.isclose(m["T_first_ctrl"], m["T_first_brake"])
    assert m["initial_peak_brake_force_N"] >= 60.0
    assert m["speed_drop_m_per_s"] >= 0.0


def test_extract_trial_metrics_steer_first():
    meta = TrialMeta(
        density=0,
        nback=0,
        participant_id=4,
        scenario_id="density_0_nback_0",
        trial_id="trial_004",
        relative_path="dummy.csv",
    )
    df = _make_synthetic_trial(has_tor=True, steer_before_brake=True)
    m = extract_trial_metrics(df, meta)

    assert m["first_action_type"] == "STEER_FIRST"
    assert m["T_first_steer"] < m["T_first_brake"]
    assert np.isclose(m["T_first_ctrl"], m["T_first_steer"])
