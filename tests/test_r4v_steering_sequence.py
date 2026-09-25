"""R4V-D descriptive steering sequence: detectors, reconstruction logic and saved-output invariants."""

import json

import numpy as np
import pandas as pd
import pytest

from src.experiments import r4v_steering_sequence as sq

OUT = "results/R4V_steering_sequence"
DT = 0.05


def ramp_trial(onset=3.0, drift=0.0, t_end=15.0):
    t = np.arange(0.0, t_end, DT)
    x = 0.02 + drift * t
    x = x + np.where(t >= onset, 0.2 * (t - onset), 0.0)
    return t, x


@pytest.fixture(scope="module")
def summary():
    return json.load(open(f"{OUT}/summary.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def events():
    return pd.read_csv(f"{OUT}/event_table.csv")


# --- detector -----------------------------------------------------------------


def test_onset_detection_is_deterministic():
    t, x = ramp_trial()
    a = [sq.detect_onset(t, x, 1.0, 14.0, 0.05, 5, reference="running_min") for _ in range(3)]
    assert a[0] is not None and len(set(a)) == 1
    assert a[0] == pytest.approx(3.30, abs=DT + 1e-9)   # 0.05 rad / 0.2 rad/s after onset


def test_no_future_leakage():
    t, x = ramp_trial()
    o = sq.detect_onset(t, x, 1.0, 14.0, 0.05, 5, reference="running_min")
    x2 = x.copy()
    x2[t > o + 5 * DT] = -5.0          # anything after onset + sustain is irrelevant
    assert sq.detect_onset(t, x2, 1.0, 14.0, 0.05, 5, reference="running_min") == o
    # truncating the record after onset + sustain gives the same answer
    keep = t <= o + 5 * DT
    assert sq.detect_onset(t[keep], x[keep], 1.0, 14.0, 0.05, 5, reference="running_min") == o


def test_detector_signature_takes_no_event_times():
    import inspect
    params = set(inspect.signature(sq.detect_onset).parameters)
    assert not params & {"t_lc", "lane_crossing", "manual_stop", "t_stop"}


def test_running_min_is_robust_to_negative_drift():
    t, x = ramp_trial(onset=3.0, drift=-0.02)
    fixed = sq.detect_onset(t, x, 1.0, 14.0, 0.05, 5, reference="ms")
    rise = sq.detect_onset(t, x, 1.0, 14.0, 0.05, 5, reference="running_min")
    assert rise is not None and fixed is not None and rise < fixed


def test_threshold_sensitivity_is_monotone():
    t, x = ramp_trial()
    o = [sq.detect_onset(t, x, 1.0, 14.0, thr, 5, reference="running_min") for thr in (0.02, 0.05, 0.10)]
    assert o[0] <= o[1] <= o[2]


def test_no_onset_returns_none():
    t = np.arange(0, 10, DT)
    assert sq.detect_onset(t, np.zeros_like(t), 1.0, 9.0, 0.05, 5, reference="running_min") is None
    assert sq.excursion_start(t, np.zeros_like(t), 1.0, None) is None


# --- hazard / gaps ------------------------------------------------------------


def test_hazard_station_reconstruction_consistent_and_not():
    t = np.arange(0, 40, DT)
    s = 1000.0 - 25.0 * t                      # abscissa decreasing along travel
    road = np.full_like(t, 15.0)
    station = 200.0
    good = s - station
    hz = sq.hazard_station(t, s, road, good, t_tor=20.0)
    assert hz["station_state"] == "CONSISTENT"
    assert hz["station_m"] == pytest.approx(station) and hz["direction"] == -1.0
    bad = 0.7 * good                           # distance shrinking slower than the abscissa
    assert sq.hazard_station(t, s, road, bad, t_tor=20.0)["station_state"] == "NOT_CONSISTENT"


def test_gap_zero_context_tags():
    t = np.arange(0, 1.0, 0.1)
    x = np.array([np.nan, 0, 0, 50.0, 0, 1.0, 0, 30.0, 0, 0])
    partner = np.array([0, 0, 0, 0, 0, 0, 1.5, 0, 0, 0], dtype=float)
    tags = sq.gap_zero_context(t, x, partner, t_lc=0.8)
    assert tags[0] == "missing"
    assert tags[1] == tags[2] == "zero_from_recording_start"
    assert tags[4] == "zero_after_far_value"
    assert tags[6] == "zero_handoff"
    assert tags[8] == tags[9] == "zero_after_lane_crossing"
    assert set(tags[[3, 5, 7]]) == {"value"}


# --- saved outputs ------------------------------------------------------------


def test_event_ordering_and_missingness(events, summary):
    assert summary["n_eligible"] == len(events) == 492
    assert (events.ms_to_steer_onset_s.dropna() >= 0).all()
    assert summary["ordering"]["onset_before_ms"] == 0
    # no imputation: an interval is missing exactly when one of its events is missing
    assert events.steer_onset_to_lane_crossing_s.isna().equals(
        events.t_steer_onset.isna() | events.t_lane_crossing.isna())
    assert events.t_lane_crossing.isna().sum() == summary["missing"]["lane_crossing"]


def test_reproducible_sequence_arithmetic(events):
    d = events.dropna(subset=["t_steer_onset", "t_lane_crossing"])
    assert np.allclose(d.ms_to_steer_onset_s + d.steer_onset_to_lane_crossing_s, d.ms_to_lane_crossing_s)


def test_all_detectors_reported(summary):
    sens = pd.read_csv(f"{OUT}/onset_detector_sensitivity.csv")
    assert set(sens.detector) == set(sq.DETECTORS) and sens.primary.sum() == 1
    assert summary["primary_detector"] == sq.PRIMARY


def test_no_substitution_into_r3b(summary):
    assert summary["r3b_relation"]["note"].startswith("comparison only")
    import src.experiments.r3b_braking_bounds as r3b
    import inspect
    assert "r4v_steering_sequence" not in inspect.getsource(r3b)
    cols = pd.read_csv(f"{OUT}/event_table.csv", nrows=1).columns
    assert not any(c in {"t1", "t1_s", "u_brake", "a_max"} for c in cols)


def test_classes_and_authorship_unchanged(summary):
    assert summary["steering_authorship"].startswith("PLAUSIBLE_BUT_UNVERIFIED")
    classes = {v["class"] for v in summary["descriptors"].values()}
    assert classes <= {"VALIDATED_DESCRIPTOR", "PROVISIONAL_DESCRIPTOR", "BLOCKED"}
    assert summary["descriptors"]["steering_duration_proxy"]["class"] == "BLOCKED"
    assert summary["descriptors"]["ms_to_steer_onset"]["class"] == "PROVISIONAL_DESCRIPTOR"


def test_report_language():
    text = open("docs/R4V_STEERING_SEQUENCE.md", encoding="utf-8").read().lower()
    for banned in ("p(safe", "safe fallback probability", "recoverability score", "intention time is"):
        assert banned not in text
