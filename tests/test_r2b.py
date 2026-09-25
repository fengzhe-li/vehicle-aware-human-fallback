"""Phase R2B tests: exposure order, balance, estimator, sensitivity population,
handback windows, provenance, and absence of deprecated human-attribution code."""

import ast
import json
import os

import numpy as np
import pandas as pd
import pytest

from tests.provenance_dependencies import assert_dependencies_unchanged

from src.experiments.r2b_repeated_exposure import (
    conclusion,
    early_late,
    fe_exposure_model,
    reconstruct_order,
    separable,
)

R2B_DIR = "results/R2B_repeated_exposure"
ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
needs_archive = pytest.mark.skipif(not os.path.exists(ARCHIVE), reason=f"D003 archive not present at {ARCHIVE}")


def test_reconstruct_order_by_recording_start():
    df = pd.DataFrame({"participant_id": [1, 1, 1, 2, 2], "record_start_epoch": [30.0, 10.0, 20.0, 5.0, 1.0],
                       "record_end_epoch": [35.0, 15.0, 25.0, 6.0, 2.0]})
    out = reconstruct_order(df)
    assert out[out.participant_id == 1].sort_values("record_start_epoch").exposure.tolist() == [1, 2, 3]
    assert out[out.participant_id == 2].sort_values("record_start_epoch").exposure.tolist() == [1, 2]
    assert out.loc[(out.participant_id == 1) & (out.exposure == 2), "gap_from_previous_trial_min"].iloc[0] == pytest.approx(5 / 60)


def test_reconstruct_order_fails_on_ties():
    df = pd.DataFrame({"participant_id": [1, 1], "record_start_epoch": [1.0, 1.0], "record_end_epoch": [2.0, 2.0]})
    with pytest.raises(ValueError, match="not reconstructable"):
        reconstruct_order(df)


def test_fe_model_recovers_known_slope_with_cell_controls():
    rng = np.random.default_rng(0)
    rows = []
    cells = [f"c{i}" for i in range(9)]
    for pid in range(40):
        order = rng.permutation(9)
        for exposure, ci in enumerate(order, start=1):
            y = 2.0 + 0.3 * pid % 5 + 0.5 * ci - 0.05 * exposure + rng.normal(0, 0.05)
            rows.append({"participant_id": pid, "cell": cells[ci], "exposure": exposure, "y": y})
    m = fe_exposure_model(pd.DataFrame(rows), "y")
    assert m["exposure_slope_per_trial"] == pytest.approx(-0.05, abs=0.01)
    assert m["ci95_low"] < -0.05 < m["ci95_high"]
    assert conclusion(m["ci95_low"], m["ci95_high"]).startswith("decrease")


def test_separability_rule():
    ok = {"cramer_v_cell_exposure": 0.05, "cell_x_exposure_min": 4, "vif_exposure_given_participant_and_cell": 1.01}
    assert separable(ok)
    assert not separable({**ok, "cramer_v_cell_exposure": 0.9})
    assert not separable({**ok, "cell_x_exposure_min": 0})


def test_early_late_uses_within_participant_differences():
    df = pd.DataFrame({"participant_id": [1] * 9 + [2] * 9, "exposure": list(range(1, 10)) * 2,
                       "y": [5] * 3 + [4] * 3 + [3] * 3 + [2] * 3 + [2] * 3 + [2] * 3})
    out = early_late(df, "y")
    assert out["n_participants"] == 2 and out["median_late_minus_early"] == pytest.approx(-1.0)


def test_r2b_module_uses_no_deprecated_human_attribution_code():
    tree = ast.parse(open("src/experiments/r2b_repeated_exposure.py", encoding="utf-8").read())
    mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not any(m.startswith("src.experiments.h1_") or m == "src.data.d003_loader" for m in mods)
    src = open("src/experiments/r2b_repeated_exposure.py", encoding="utf-8").read()
    for banned in ("T_stable", "brake_first", "steer_first", "first_brake", "reversal", "brake_peak"):
        assert banned not in src


# --- outputs ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def summary():
    with open(os.path.join(R2B_DIR, "summary.json"), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def trials():
    return pd.read_csv(os.path.join(R2B_DIR, "trial_table.csv"))


def test_exposure_order_and_participant_counts(summary, trials):
    b = summary["order_balance"]
    assert b["n_participants"] == 57
    assert b["trials_per_participant"] == {"9": 57}
    assert b["distinct_cells_per_participant"] == {"9": 57}
    assert sorted(trials.exposure.unique()) == list(range(1, 10))
    assert (trials.groupby("participant_id").exposure.apply(sorted).apply(list) == [list(range(1, 10))] * 57).all()
    assert summary["order_reconstructable"] is True


def test_scenario_exposure_balance(summary):
    b = summary["order_balance"]
    assert b["cell_x_exposure_min"] >= 4 and b["cell_x_exposure_max"] <= 8
    assert b["cramer_v_cell_exposure"] < 0.1
    assert b["vif_exposure_given_participant_and_cell"] < 1.1
    assert summary["exposure_separable_from_cell"] is True


def test_populations_and_multitor_sensitivity(summary, trials):
    p = summary["populations"]
    assert (p["RAW"], p["TOR_ANCHORED"], p["TOR_ANCHORED_single_raw_TOR"], p["LANE_CHANGE_ANCHORED"]) == (513, 492, 472, 477)
    sens = pd.read_csv(os.path.join(R2B_DIR, "multitor_sensitivity_t_button.csv"))
    assert sens.n_trials.tolist() == [492, 472]
    sub = trials[trials.TOR_ANCHORED & (trials.n_raw_tor_values == 1)]
    assert len(sub) == 472 and (sub.tor_state == "SINGLE").all()
    assert summary["multitor_sensitivity_materially_changes_conclusion"] is False


def test_handback_window_and_lane_change_classification(summary, trials):
    hb = summary["handback"]
    assert hb["lane_change_vs_handback_counts"]["BEFORE_HANDBACK"] == 477
    assert hb["lane_change_vs_handback_counts"]["AT_OR_AFTER_HANDBACK"] == 1
    assert hb["lane_change_after_handback_trials"] == ["density_0_nback_2_id_29"]
    a = trials[trials.TOR_ANCHORED]
    assert (a.tor_to_handback_s > 0).all() and (a.manual_start_to_handback_s > 0).all()
    lc = trials[trials.LANE_CHANGE_ANCHORED]
    assert (lc.tor_to_lane_change_s < lc.tor_to_handback_s).all()
    assert trials[~trials.LANE_CHANGE_ANCHORED].tor_to_lane_change_s.isna().all()


def test_r2b_provenance(summary):
    with open(os.path.join(R2B_DIR, "provenance.json"), encoding="utf-8") as fh:
        prov = json.load(fh)
    assert prov["archive_sha256"] == "6e85e5365d0ae5e356559d20cf0b95cf81d60f9bd3ba5a52ec36021f664ca212"
    assert prov["src_tree_dirty"] is False
    deps = ["src/data/d003_ingest.py", "src/data/d003_loader.py", "src/data/d003_populations.py",
            "src/experiments/r2a_event_vehicle_descriptives.py", "src/experiments/r2b_repeated_exposure.py"]
    assert_dependencies_unchanged("R2B", prov, deps)
    assert any("B17" in x for x in prov["known_semantic_limitations"])
    for oc, meta in summary["outcomes"].items():
        assert {"definition", "population", "window", "role"} <= set(meta)
    assert "B17" in summary["outcomes"]["vehicle_max_decel_mps2"]["definition"]


@needs_archive
def test_r2b_outputs_reproduce(tmp_path):
    from src.experiments.r2b_repeated_exposure import run

    run(ARCHIVE, str(tmp_path))
    for f in os.listdir(R2B_DIR):
        if f.endswith(".csv") or f == "summary.json":
            assert (tmp_path / f).read_bytes() == open(os.path.join(R2B_DIR, f), "rb").read(), f
