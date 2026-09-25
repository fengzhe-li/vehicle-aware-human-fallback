"""Phase R2C-lite tests: participant aggregation, slope reconstruction, covariate
joins, carry-over construction, first-trial handling, estimators, provenance, and
absence of deprecated human-attribution code."""

import ast
import json
import os

import numpy as np
import pandas as pd
import pytest

from tests.provenance_dependencies import assert_dependencies_unchanged

from src.experiments.r2c_lite import (
    add_previous_cell,
    fe_cr1,
    holm,
    join_covariates,
    participant_table,
    reml_random_intercept,
    wald_block,
)

R2B_DIR = "results/R2B_repeated_exposure"
R2C_DIR = "results/R2C_lite"
ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
MODULE = "src/experiments/r2c_lite.py"
needs_archive = pytest.mark.skipif(not os.path.exists(ARCHIVE), reason=f"D003 archive not present at {ARCHIVE}")


def _toy(n_part=3, slope=-0.1):
    rows = []
    for p in range(1, n_part + 1):
        for e in range(1, 10):
            rows.append({"participant_id": p, "exposure": e, "cell": f"c{(e + p) % 9}",
                         "density": ((e + p) % 3) * 10, "nback": (e + p) % 3,
                         "t_button_s": 2.0 + 0.1 * p + slope * e})
    return pd.DataFrame(rows)


# --- unit ------------------------------------------------------------------------------


def test_participant_aggregation_median_mean_and_counts():
    d = _toy()
    d.loc[(d.participant_id == 1) & (d.exposure == 9), "t_button_s"] = np.nan
    pt = participant_table(d).set_index("participant_id")
    assert pt.loc[1, "n_trials"] == 8 and pt.loc[2, "n_trials"] == 9
    g = d[d.participant_id == 2].t_button_s
    assert pt.loc[2, "median_t_button_s"] == pytest.approx(g.median())
    assert pt.loc[2, "mean_t_button_s"] == pytest.approx(g.mean())


def test_slope_reconstruction_and_minimum_points():
    d = _toy(slope=-0.1)
    pt = participant_table(d)
    assert np.allclose(pt.slope_t_button_s_per_exposure, -0.1)
    d.loc[(d.participant_id == 3) & (d.exposure > 4), "t_button_s"] = np.nan  # 4 points < 5
    assert pd.isna(participant_table(d).set_index("participant_id").loc[3, "slope_t_button_s_per_exposure"])


def test_covariate_join_is_one_to_one_and_strict():
    part = pd.DataFrame({"participant_id": [1, 2, 3], "x": [1, 2, 3]})
    cov = pd.DataFrame({"participant_id": [3, 1, 2], "accu_years": [30, 10, 20]})
    out = join_covariates(part, cov).set_index("participant_id")
    assert out.loc[1, "accu_years"] == 10 and out.loc[3, "accu_years"] == 30
    with pytest.raises(ValueError, match="differ"):
        join_covariates(part, cov[cov.participant_id != 2])
    with pytest.raises(ValueError, match="duplicate"):
        join_covariates(part, pd.concat([cov, cov.iloc[[0]]]))


def test_carryover_construction_and_first_trial_missing():
    d = _toy().sample(frac=1, random_state=0)  # order must come from exposure, not row order
    t = add_previous_cell(d)
    assert t[t.exposure == 1].prev_cell.isna().all()
    assert t[t.exposure > 1].prev_cell.notna().all()
    for p, g in t.groupby("participant_id"):
        g = g.sort_values("exposure")
        assert g.prev_cell.iloc[1:].tolist() == g.cell.iloc[:-1].tolist()
        assert g.prev_density.iloc[1:].tolist() == g.density.iloc[:-1].tolist()


def test_carryover_rejects_gapped_sequence():
    d = _toy()
    with pytest.raises(ValueError, match="gaps"):
        add_previous_cell(d[d.exposure != 5])


def test_fe_and_random_intercept_recover_slope_and_null_carryover():
    rng = np.random.default_rng(1)
    rows = []
    for p in range(40):
        u = rng.normal(0, 0.4)
        order = rng.permutation(9)
        for e, c in enumerate(order, start=1):
            rows.append({"participant_id": p, "exposure": e, "cell": f"c{c}",
                         "t_button_s": 2 + u + 0.05 * c - 0.04 * e + rng.normal(0, 0.2)})
    d = add_previous_cell(pd.DataFrame(rows).assign(density=0, nback=0))
    d = d[d.prev_cell.notna()]
    fit = fe_cr1(d, ["cell", "prev_cell"])
    assert fit["beta"][fit["names"].index("exposure")] == pytest.approx(-0.04, abs=0.01)
    assert wald_block(fit, ["prev_cell"])["wald_p"] > 0.01
    ri = reml_random_intercept(d, ["cell"])
    assert ri["exposure_slope_per_trial"] == pytest.approx(-0.04, abs=0.01)
    assert ri["participant_var"] == pytest.approx(0.16, rel=0.6)


def test_holm_adjustment():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_r2c_module_uses_no_deprecated_human_attribution_code():
    src = open(MODULE, encoding="utf-8").read()
    tree = ast.parse(src)
    mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not any(m.startswith("src.experiments.h1_") or m in ("src.data.d003_loader", "src.metrics.control_activity")
                   for m in mods)
    for banned in ("T_stable", "brake_first", "steer_first", "first_brake", "reversal", "brake_peak",
                   "VehicleUpdate-", "steeringWheelAngle", "brake_", "steer_", "accel_"):
        assert banned not in src


# --- outputs ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def summary():
    with open(os.path.join(R2C_DIR, "summary.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_participant_summary_matches_r2b(summary):
    pt = pd.read_csv(os.path.join(R2C_DIR, "participant_summary.csv"))
    assert len(pt) == 57 and pt.participant_id.is_unique
    assert pt.n_trials.sum() == 492 and pt.n_trials_single_tor.sum() == 472
    r2b = pd.read_csv(os.path.join(R2B_DIR, "participant_slopes.csv"))
    r2b = r2b[r2b.outcome == "t_button_s"].set_index("participant_id").ols_slope_per_exposure
    assert np.allclose(pt.set_index("participant_id").slope_t_button_s_per_exposure, r2b.loc[pt.participant_id])
    for cv in summary["participant_level"]["covariates"]:
        assert pt[cv].notna().all()


def test_associations_family_and_multiplicity(summary):
    a = pd.read_csv(os.path.join(R2C_DIR, "participant_associations.csv"))
    prim = a[a.family == "primary"]
    assert prim.groupby("population").size().tolist() == [8, 8]
    assert set(prim.covariate) == {"accu_years", "accu_km", "driving_frequency", "assist_frequency"}
    assert (prim.p_holm >= prim.p_value - 1e-12).all() and (prim.n_participants == 57).all()
    assert (a.rho_ci95_low <= a.spearman_rho).all() and (a.spearman_rho <= a.rho_ci95_high).all()


def test_carryover_population_and_identifiability(summary):
    c = summary["carryover"]
    assert c["identifiability"]["n_trials"] == 435  # 492 TOR_ANCHORED minus exposure-1 trials
    assert c["identifiability"]["prev_cell_identifiable"] is True
    assert c["identifiability"]["interaction_identifiable"] is False
    m = pd.read_csv(os.path.join(R2C_DIR, "carryover_models.csv"))
    for pop, g in m.groupby("population"):
        assert g.n_trials.nunique() == 1  # reference and carry-over models on the same trials
    assert m.groupby("population").n_trials.first().tolist() == [435, 416]
    assert isinstance(summary["multitor_sensitivity_materially_changes_conclusion"], bool)


def test_r2c_provenance(summary):
    with open(os.path.join(R2C_DIR, "provenance.json"), encoding="utf-8") as fh:
        prov = json.load(fh)
    assert prov["archive_sha256"] == "6e85e5365d0ae5e356559d20cf0b95cf81d60f9bd3ba5a52ec36021f664ca212"
    assert prov["src_tree_dirty"] is False
    deps = ["src/experiments/r2c_lite.py", "src/experiments/r2b_repeated_exposure.py",
            "src/experiments/r2a_event_vehicle_descriptives.py"]
    assert_dependencies_unchanged("R2C", prov, deps)
    import hashlib
    assert prov["r2b_trial_table_sha256"] == hashlib.sha256(
        open(os.path.join(R2B_DIR, "trial_table.csv"), "rb").read()).hexdigest()
    assert any("B17" in x for x in prov["known_semantic_limitations"])
    assert any("Secondary re-analysis" in x for x in prov["known_semantic_limitations"])
    assert {"definition", "window", "population"} <= set(summary["outcome"])


@needs_archive
def test_r2c_outputs_reproduce(tmp_path):
    from src.experiments.r2c_lite import run

    run(ARCHIVE, os.path.join(R2B_DIR, "trial_table.csv"), str(tmp_path))
    for f in os.listdir(R2C_DIR):
        if f.endswith(".csv") or f == "summary.json":
            assert (tmp_path / f).read_bytes() == open(os.path.join(R2C_DIR, f), "rb").read(), f
