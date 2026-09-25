"""Phase R2A tests: canonical pipeline, populations, windows, neutral channel
diagnostics, collision-proxy retirement, historical-output labelling, provenance."""

import ast
import hashlib
import json
import os
import warnings

import pandas as pd
import pytest

from tests.provenance_dependencies import assert_dependencies_unchanged

from src.data.d003_ingest import HEADER_VARIANTS, parse_trial_text
from src.data.d003_populations import (
    MANUAL_INTERVAL_WINDOWS,
    ObservationWindowError,
    classify_trial,
    window_bounds,
)
from tests.test_d003_ingest import NAME, make_csv

ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
R2A_DIR = "results/R2A_event_vehicle_descriptives"
R1_DIR = "results/R1_ingestion_validation"
ACTIVE_MODULES = [
    "src/data/d003_ingest.py",
    "src/data/d003_populations.py",
    "src/metrics/control_activity.py",
    "src/experiments/r1_ingestion_validation.py",
    "src/experiments/r2a_event_vehicle_descriptives.py",
]
FORBIDDEN_AUTHORSHIP_TERMS = ("driver", "human", "first_input", "first_brake_input", "first_steer_input",
                              "brake_first", "steer_first", "reaction")

needs_archive = pytest.mark.skipif(not os.path.exists(ARCHIVE), reason=f"D003 archive not present at {ARCHIVE}")


def pop_of(**kw):
    return classify_trial(parse_trial_text(make_csv(**kw), NAME))


# --- canonical ingestion path ----------------------------------------------------


@pytest.mark.parametrize("path", ACTIVE_MODULES)
def test_active_modules_do_not_use_legacy_ingestion(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported += [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
    assert not any(n.startswith("src.experiments.h1_") for n in imported)
    assert "src.data.d003_loader.D003Dataset" not in imported


def test_legacy_entry_points_warn(tmp_path):
    from src.data.d003_loader import D003Dataset
    from src.experiments.h1_recovery_analysis import run_full_h1_analysis
    from src.experiments.h1_sensitivity_analysis import run_sensitivity_audit

    missing = str(tmp_path / "missing.zip")
    for call in (lambda: D003Dataset(missing),
                 lambda: run_full_h1_analysis(archive_path=missing, results_dir=str(tmp_path / "h1"),
                                              qa_path=str(tmp_path / "qa" / "qa.csv")),
                 lambda: run_sensitivity_audit(archive_path=missing, output_dir=str(tmp_path / "sens"))):
        with pytest.warns(DeprecationWarning), pytest.raises(FileNotFoundError):
            call()


# --- populations and windows (synthetic) --------------------------------------------


def test_population_flags_on_regular_trial():
    p = pop_of()
    assert (p.tor_present, p.tor_anchored, p.owner_window_eligible,
            p.lane_change_anchored, p.manual_window_eligible) == (True, True, True, True, True)


def test_unresolved_tor_excluded_from_all_tor_anchored_windows():
    p = pop_of(tor_values=(2.9, 3.1))
    assert p.tor_present and not p.tor_anchored
    assert not (p.owner_window_eligible or p.lane_change_anchored or p.manual_window_eligible)
    for w in ("POST_TOR_MANUAL", "POST_BUTTON_MANUAL", "OWNER_TOR_TO_LANE_CHANGE", "MANUAL_TOR_TO_LANE_CHANGE"):
        with pytest.raises(ObservationWindowError):
            window_bounds(p, w)


def test_missing_tor_excluded():
    p = pop_of(header=HEADER_VARIANTS["NO_TOR_44"])
    assert not p.tor_present and not p.tor_anchored and "TOR_PRESENT" in p.reasons


def test_invalid_lane_change_anchor_excluded():
    p = pop_of(lane_change=7.0, lane_change_first_row_time=6.05)  # clock exception
    assert p.tor_anchored and p.manual_window_eligible
    assert not p.owner_window_eligible and not p.lane_change_anchored
    assert "CLOCK_EXCEPTION" in p.reasons["OWNER_WINDOW_ELIGIBLE"]


def test_owner_window_and_manual_window_are_separate_when_lane_change_follows_handback():
    p = pop_of(manual_stops=(5.0,))  # handback at 5 s, lane change at 6 s
    assert p.owner_window_eligible and not p.lane_change_anchored
    assert window_bounds(p, "OWNER_TOR_TO_LANE_CHANGE") == (3.0, 6.0)  # published definition, not bounded
    with pytest.raises(ObservationWindowError):
        window_bounds(p, "MANUAL_TOR_TO_LANE_CHANGE")


@pytest.mark.parametrize("window", MANUAL_INTERVAL_WINDOWS)
def test_manual_interval_windows_end_at_or_before_handback(window):
    p = pop_of()
    start, end = window_bounds(p, window)
    assert end <= p.handback


# --- neutral channel diagnostics -------------------------------------------------------


def test_control_activity_api_is_authorship_neutral():
    import src.metrics.control_activity as ca

    public = [n for n in dir(ca) if not n.startswith("_") and callable(getattr(ca, n))]
    assert {"count_hysteresis_reversals", "count_signal_peaks", "lowpass"} <= set(public)
    for n in public:
        assert not any(term in n.lower() for term in ("driver", "human", "steering", "brake", "input", "correction"))


# --- real-archive outputs -------------------------------------------------------------------


@pytest.fixture(scope="module")
def r2a_outputs():
    if not os.path.isdir(R2A_DIR):
        pytest.fail(f"R2A outputs missing: {R2A_DIR}")
    return {f: pd.read_csv(os.path.join(R2A_DIR, f)) for f in os.listdir(R2A_DIR) if f.endswith(".csv")}


def test_population_counts(r2a_outputs):
    pops = r2a_outputs["populations.csv"]
    counts = {k: int(pops[k].sum()) for k in ("RAW", "TOR_PRESENT", "TOR_ANCHORED", "OWNER_WINDOW_ELIGIBLE",
                                              "LANE_CHANGE_ANCHORED", "MANUAL_WINDOW_ELIGIBLE")}
    assert counts == {"RAW": 513, "TOR_PRESENT": 498, "TOR_ANCHORED": 492, "OWNER_WINDOW_ELIGIBLE": 478,
                      "LANE_CHANGE_ANCHORED": 477, "MANUAL_WINDOW_ELIGIBLE": 492}
    assert set(pops.OWNER_ANALYSIS_SET) == {"UNKNOWN"}
    only_owner = pops[pops.OWNER_WINDOW_ELIGIBLE & ~pops.LANE_CHANGE_ANCHORED]
    assert only_owner.trial_id.tolist() == ["density_0_nback_2_id_29"]


def test_unresolved_tor_and_invalid_lane_change_absent_from_metrics(r2a_outputs):
    pops, ev = r2a_outputs["populations.csv"], r2a_outputs["event_and_vehicle_state_metrics.csv"]
    unresolved = set(pops[pops.tor_state == "MULTI_UNRESOLVED"].trial_id)
    assert len(unresolved) == 6
    sub = ev[ev.trial_id.isin(unresolved)]
    assert sub.t_button_s.isna().all() and sub.owner_tor_to_lane_change_s.isna().all()
    assert sub.manual_tor_to_lane_change_s.isna().all()
    exc = ev[ev.trial_id == "density_10_nback_1_id_8"].iloc[0]
    assert pd.isna(exc.owner_tor_to_lane_change_s) and pd.isna(exc.manual_tor_to_lane_change_s)
    obs = r2a_outputs["control_channel_observations.csv"]
    assert not set(obs.trial_id) & unresolved


def test_manual_metrics_never_extend_past_handback(r2a_outputs):
    ev = r2a_outputs["event_and_vehicle_state_metrics.csv"]
    m = ev[ev.LANE_CHANGE_ANCHORED]
    assert (m.manual_window_end < m.t_handback).all()
    act = r2a_outputs["channel_activity_diagnostics.csv"]
    manual = act[act.window.isin(["POST_TOR_MANUAL", "POST_BUTTON_MANUAL"])]
    assert not manual.window_reaches_handback.any()
    assert act[act.window == "HISTORICAL_FULL_RECORD_POST_TOR_INVALID"].window_reaches_handback.all()


def test_no_driver_action_interpretation_or_collision_in_active_outputs(r2a_outputs):
    for name, df in r2a_outputs.items():
        for col in df.columns:
            low = col.lower()
            assert "collision" not in low, (name, col)
            assert not any(term in low for term in FORBIDDEN_AUTHORSHIP_TERMS), (name, col)
    obs = r2a_outputs["control_channel_observations.csv"]
    assert set(obs.authorship) == {"UNRESOLVED (B17)"}
    for f in os.listdir(R1_DIR):
        if f.endswith(".csv"):
            assert not any("collision" in c.lower() for c in pd.read_csv(os.path.join(R1_DIR, f), nrows=1).columns)


def test_b17_pattern_is_recorded(r2a_outputs):
    pat = r2a_outputs["channel_transition_pattern_by_cell.csv"].set_index(["density", "nback"])
    assert pat.loc[(10, 0), "earliest_channel_activity_within_0p3s"] == 53
    assert pat.loc[(0, 0), "accelerator_channel_drops_to_zero_within_0p3s"] == 0
    assert pat.loc[(10, 2), "accelerator_channel_drops_to_zero_within_0p3s"] == 57


# --- historical outputs and provenance ------------------------------------------------------------


def test_historical_outputs_manifest_hashes_and_labels():
    with open("results/historical_outputs_manifest.json", encoding="utf-8") as fh:
        man = json.load(fh)
    allowed = {"INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS", "WITHDRAWN", "HISTORICAL ONLY"}
    assert len(man["files"]) == 13
    for path, entry in man["files"].items():
        assert entry["status"] in allowed
        assert hashlib.sha256(open(path, "rb").read()).hexdigest() == entry["sha256"], path


@needs_archive
def test_historical_outputs_reproduce_byte_for_byte(tmp_path):
    from src.experiments.h1_recovery_analysis import run_full_h1_analysis
    from src.experiments.h1_sensitivity_analysis import run_sensitivity_audit

    with open("results/historical_outputs_manifest.json", encoding="utf-8") as fh:
        man = json.load(fh)["files"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        run_full_h1_analysis(ARCHIVE, results_dir=str(tmp_path / "H1"), qa_path=str(tmp_path / "d003_trial_qa.csv"))
        run_sensitivity_audit(ARCHIVE, output_dir=str(tmp_path / "H1_sensitivity"))
    for path, entry in man.items():
        regen = tmp_path / path.replace("results/", "").replace("research/data_matrix/", "")
        assert hashlib.sha256(regen.read_bytes()).hexdigest() == entry["sha256"], path


def test_r2a_provenance():
    with open(os.path.join(R2A_DIR, "provenance.json"), encoding="utf-8") as fh:
        prov = json.load(fh)
    assert prov["archive_sha256"] == "6e85e5365d0ae5e356559d20cf0b95cf81d60f9bd3ba5a52ec36021f664ca212"
    assert prov["ingestion"].startswith("src/data/d003_ingest.py")
    assert prov["src_tree_dirty"] is False
    assert set(prov["populations"]) >= {"RAW", "TOR_ANCHORED", "LANE_CHANGE_ANCHORED", "OWNER_ANALYSIS_SET"}
    assert "OWNER_TOR_TO_LANE_CHANGE" in prov["windows"] and "MANUAL_TOR_TO_LANE_CHANGE" in prov["windows"]
    assert any("B17" in d for d in prov["unresolved_semantic_dependencies"])
    # The code these outputs depend on must be unchanged since the recorded commit
    # (verified by content hash; the historical commit is not in this repository).
    deps = ["src/data/d003_ingest.py", "src/data/d003_loader.py", "src/data/d003_populations.py",
            "src/metrics/control_activity.py", "src/experiments/r2a_event_vehicle_descriptives.py"]
    assert_dependencies_unchanged("R2A", prov, deps)


@needs_archive
def test_r2a_outputs_reproduce(tmp_path):
    from src.experiments.r2a_event_vehicle_descriptives import run

    run(ARCHIVE, str(tmp_path))
    for f in os.listdir(R2A_DIR):
        if f.endswith(".csv"):
            assert (tmp_path / f).read_bytes() == open(os.path.join(R2A_DIR, f), "rb").read(), f
