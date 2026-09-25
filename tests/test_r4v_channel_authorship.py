"""R4V control-channel authorship validation: helpers, classification rules and saved-output invariants."""

import json

import numpy as np
import pandas as pd
import pytest

from src.experiments import r4v_channel_authorship as r4v

SUMMARY = "results/R4V_channel_authorship/summary.json"
CLASSES = set(r4v.ORDER)


@pytest.fixture(scope="module")
def summary():
    return json.load(open(SUMMARY, encoding="utf-8"))


def test_first_crossing_respects_window():
    t = np.arange(0, 5, 0.05)
    x = (t > 2.0).astype(float)
    assert r4v.first_crossing(t, x, 0.0, 5.0, lambda v: v > 0.5) == pytest.approx(2.05)
    assert r4v.first_crossing(t, x, 0.0, 2.0, lambda v: v > 0.5) is None


def test_eta2_and_icc_limits():
    g = pd.Series(["a"] * 5 + ["b"] * 5)
    assert r4v.eta2(pd.Series([1.0] * 5 + [2.0] * 5), g) == pytest.approx(1.0)
    assert r4v.eta2(pd.Series([1.0] * 10), g) is None


def test_classification_rules():
    c = r4v.classify_channel
    assert c(False, False, 0.5, 0.0, True, True) == "NOT_IDENTIFIABLE"
    assert c(True, True, 0.5, 0.0, True, True) == "MIXED_OR_AMBIGUOUS"
    assert c(True, False, 0.5, 0.0, True, True) == "DRIVER_AUTHORSHIP_SUPPORTED"
    assert c(True, False, 0.05, 0.0, True, True) == "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED"
    assert c(True, False, 0.5, 0.0, None, True) == "DRIVER_AUTHORSHIP_PLAUSIBLE_BUT_UNVERIFIED"


def test_review_only_downgrades(summary):
    rule, final = summary["authorship_classification_rule"], summary["authorship_classification"]
    for ch, cls in final.items():
        assert cls in CLASSES
        assert r4v.ORDER.index(cls) <= r4v.ORDER.index(rule[ch]), ch


def test_no_channel_upgraded_to_supported(summary):
    final = summary["authorship_classification"]
    assert "DRIVER_AUTHORSHIP_SUPPORTED" not in final.values()
    assert final["brake"] == final["accelerator"] == "MIXED_OR_AMBIGUOUS"
    assert final["steering_torque"] == final["state_flag"] == "NOT_IDENTIFIABLE"
    assert summary["brake_magnitude"]["class"] == "NOT_IDENTIFIABLE"


def test_state_flag_is_constant(summary):
    assert summary["state_flag_values"] == ["2.0"]


def test_automation_content_straddles_manual_start(summary):
    s = summary["straddle"]
    assert s["brake_active_at_ms_fraction"] > 0.4
    assert s["accel_active_at_ms_by_cell"]["d20_n0"] > 0.8


def test_steering_onset_is_not_lane_crossing(summary):
    es = summary["event_structure"]
    assert "steer_onset_after_ms_rel_ms_s" in es and "steer_onset_to_lane_crossing_s" in es
    assert es["steer_onset_to_lane_crossing_s"]["median_s"] > 1.0


def test_no_probability_or_safety_language():
    text = open("docs/R4V_CHANNEL_AUTHORSHIP_VALIDATION.md", encoding="utf-8").read().lower()
    for banned in ("p(safe", "safe fallback probability", "monte carlo run", "recoverability score"):
        assert banned not in text
