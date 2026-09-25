"""Phase R3A tests: evidence tables, parameter provenance registry, EPA coast-down
conversion, and the scope limits of the R3A phase (no synthesis, no simulator)."""

import copy
import csv
import json
import os

import numpy as np
import pytest

from src.provenance import registry as reg
from src.experiments.r3a_coastdown_epa import road_load_decel_mps2

EPA = "data/external/epa/24-testcar-2025-05.xlsx"
COAST = "research/data_matrix/r3a_epa_coastdown_deceleration.csv"
needs_epa = pytest.mark.skipif(not os.path.exists(EPA), reason=f"EPA file not present at {EPA}")


@pytest.fixture(scope="module")
def tables():
    return {
        "sources": reg.load(reg.SOURCES),
        "registry": reg.load(reg.REGISTRY),
        "vehicle": reg.load(reg.VEHICLE),
        "transition": reg.load(reg.TRANSITION),
        "hazard": reg.load(reg.HAZARD),
        "ident": reg.load(reg.IDENTIFIABILITY),
    }


def _sid(t):
    return reg.citable(t["sources"])


# --- committed tables are valid --------------------------------------------------------


def test_all_r3a_tables_validate():
    assert reg.validate_all() == []


def test_vehicle_matrix_covers_required_phenomena(tables):
    params = {r["parameter"] for r in tables["vehicle"]}
    for p in ("a_pre", "t2", "t3", "j", "a_liftoff", "a_regen_max", "a_one_pedal", "blend", "t2_bbw", "a_drag"):
        assert p in params, p
    assert any(p.startswith("a_max") for p in params)
    assert {"FIXED", "DISTRIBUTION", "BOUNDED", "CONTEXT-DEPENDENT", "NOT IDENTIFIABLE"} >= {r["status"] for r in tables["vehicle"]}


def test_identifiability_covers_required_quantities(tables):
    q = {r["quantity"] for r in tables["ident"]}
    for name in ("a_pre", "t2", "t3", "a_max", "jerk", "regen / one-pedal", "blending", "TOR timing",
                 "authority transfer", "continued automation support", "withdrawal", "MRM", "v0", "TTC",
                 "distance", "mu", "escape-path availability"):
        assert name in q, name


def test_hazard_matrix_separates_state_environment_constraints(tables):
    classes = {r["class"].split(" (")[0] for r in tables["hazard"]}
    assert {"STATE", "ENVIRONMENT", "MANOEUVRE CONSTRAINT"} <= classes


def test_key_semantic_rules_are_encoded(tables):
    vehicle = {r["row_id"]: r for r in tables["vehicle"]}
    assert "INTERACTION" in vehicle["V01"]["layer_assignment"]  # a_pre is not vehicle-only
    assert vehicle["V17"]["status"] == "NOT IDENTIFIABLE"       # blending is proprietary
    assert vehicle["V21"]["status"] == "NOT IDENTIFIABLE"       # D003 vehicle model undocumented
    transition = {r["row_id"]: r for r in tables["transition"]}
    assert transition["T05"]["status"] == "NOT IDENTIFIABLE"    # TOR != authority transfer
    params = {p["symbol"]: p for p in tables["registry"]}
    assert params["T_authority"]["synthesis_entry"] == "NO"
    assert params["u_eff"]["synthesis_entry"] == "NO"


def test_registry_code_usage_matches_code(tables):
    used = {p["symbol"] for p in tables["registry"] if p["currently_used_in_code"] == "YES"}
    assert {"v0", "t1", "t2", "t3", "a_max_dry", "T_TOR", "a_coast"} <= used
    # Historical note: in R3A the braking command did not reach the vehicle model (full braking was
    # hard-coded; documented in docs/R3A_VEHICLE_TRANSITION_HAZARD_REPORT.md). R3B activated the command
    # path; the former source-token assertion is superseded by the behavioural tests below.


def test_command_path_full_braking_reproduces_legacy_saturated_case():
    from src.metrics.oracle import stopping_distance_w0_analytical
    from src.scenarios.models import ScenarioConfig
    from src.simulation.simulator import MinimalSimulator
    from src.vehicle.models import VehicleResponseConfig

    veh = VehicleResponseConfig(t_delay=0.1, t_buildup=0.5, a_max=8.5)
    res = MinimalSimulator(dt=0.001).simulate(ScenarioConfig(v0=27.8, tor_lead_time=8.0), veh)
    assert res.accelerations.min() == pytest.approx(-8.5)
    assert res.outcomes.x_stop_full == pytest.approx(stopping_distance_w0_analytical(27.8, 8.5, 1.0, 0.1, 0.5), rel=1e-3)


def test_command_path_partial_braking_scales_deceleration_and_is_recorded():
    from src.driver.models import HumanDriverConfig
    from src.scenarios.models import ScenarioConfig
    from src.simulation.simulator import MinimalSimulator
    from src.vehicle.models import VehicleResponseConfig, effective_braking_deceleration

    veh = VehicleResponseConfig(t_delay=0.1, t_buildup=0.5, a_max=8.5)
    for u in (0.25, 0.5, 0.75):
        res = MinimalSimulator(dt=0.001).simulate(ScenarioConfig(v0=20.0, tor_lead_time=30.0), veh,
                                                  HumanDriverConfig(t_reaction=1.0, u_target=u))
        assert res.accelerations.min() == pytest.approx(-effective_braking_deceleration(8.5, u, 1.0))
        assert res.u_brake == u and set(np.unique(res.commands)) <= {0.0, u}  # command provenance


def test_r3b_command_magnitude_in_provenance_and_driver_strength_blocked(tables):
    from src.experiments import r3b_braking_bounds as r3b

    summary = json.load(open("results/R3B_braking_bounds/summary.json"))
    assert summary["success_definition"]["u_brake"] == 1.0
    assert "MODEL CONDITION" in summary["success_definition"]["class_u_brake"]  # not evidence
    assert "u_eff" in r3b.BLOCKED_INPUTS and "u_eff" in summary["blocked_inputs_not_used"]
    assert not any("u_eff" in b["params"] for b in r3b.BRANCHES.values())
    u_eff = next(p for p in tables["registry"] if p["symbol"] == "u_eff")
    assert u_eff["synthesis_entry"] == "NO" and u_eff["interval_readiness"] == "BLOCKED"


def test_every_source_is_cited_somewhere(tables):
    cited = set()
    for t in ("vehicle", "transition", "hazard"):
        for r in tables[t]:
            cited |= set(reg._ids(r["evidence_source_ids"]))
    for p in tables["registry"]:
        cited |= set(reg._ids(p["source_ids"]))
    for e in reg.load(reg.EVENTS):
        cited |= set(reg._ids(e["source_ids"]))
    assert set(reg.citable(tables["sources"])) - cited == set()  # navigation-only aids are excluded (R3B-0)


# --- the validator catches errors ------------------------------------------------------


def test_validator_rejects_unknown_source_and_bad_status(tables):
    rows = copy.deepcopy(tables["vehicle"])
    rows[0]["evidence_source_ids"] = "S99"
    rows[1]["status"] = "PROBABLY"
    errs = reg.validate_matrix(rows, _sid(tables), reg.PARAMETER_STATUS, "status", "vehicle")
    assert any("S99" in e for e in errs) and any("PROBABLY" in e for e in errs)


def test_validator_rejects_unordered_values_and_premature_synthesis(tables):
    rows = copy.deepcopy(tables["registry"])
    p = next(r for r in rows if r["symbol"] == "t2")
    p["value_low"], p["value_high"] = "0.5", "0.1"
    q = next(r for r in rows if r["symbol"] == "T_authority")
    q["synthesis_entry"] = "YES"
    errs = reg.validate_registry(rows, _sid(tables))
    assert any("not ordered" in e for e in errs)
    assert any("synthesis-ready" in e for e in errs)


def test_validator_rejects_missing_code_symbol(tables):
    rows = copy.deepcopy(tables["registry"])
    p = next(r for r in rows if r["symbol"] == "t2")
    p["code_reference"] = "src/vehicle/models.py:VehicleResponseConfig.no_such_field"
    assert any("no_such_field" in e for e in reg.validate_registry(rows, _sid(tables)))


def test_validator_rejects_dangling_identifiability_reference(tables):
    rows = copy.deepcopy(tables["ident"])
    rows[0]["matrix_row_ids"] = "V99"
    errs = reg.validate_identifiability(rows, [p["param_id"] for p in tables["registry"]], ["V01"])
    assert any("V99" in e for e in errs)


# --- EPA coast-down conversion -----------------------------------------------------------


def test_road_load_conversion_is_deterministic():
    # 30 lbf constant road load on a 3000 lb test weight: 133.45 N / 1360.78 kg
    assert road_load_decel_mps2(30.0, 0.0, 0.0, 3000.0, 100.0) == pytest.approx(0.098067, rel=1e-5)
    # quadratic term: 0.02 lbf/mph^2 at 100 km/h (62.137 mph)
    v = 100 / 3.6 / 0.44704
    assert road_load_decel_mps2(0.0, 0.0, 0.02, 3000.0, 100.0) == pytest.approx(0.02 * v ** 2 * 4.4482216152605 / (3000 * 0.45359237))
    a = road_load_decel_mps2(np.array([30.0, 30.0]), 0.2, 0.02, 3500.0, np.array([60.0, 130.0]))
    assert a[1] > a[0]


def test_coastdown_summary_consistent_with_registry(tables):
    with open(COAST, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["group"] == "all" and r["speed_kmh"] == "100"]
    p = next(p for p in tables["registry"] if p["symbol"] == "a_drag")
    assert float(p["value_low"]) == pytest.approx(float(rows[0]["p05_mps2"]), abs=1e-3)
    assert float(p["value_central"]) == pytest.approx(float(rows[0]["median_mps2"]), abs=1e-3)
    assert float(p["value_high"]) == pytest.approx(float(rows[0]["p95_mps2"]), abs=1e-3)
    prov = json.load(open(COAST.replace(".csv", "_provenance.json")))
    assert prov["source_sha256"] == "e3a5378fa5e6820861d705e36fd2f2046234be8d050026bcfde29f0b8e63a6f9"
    assert "excludes engine braking" in prov["scope_limitation"]


@needs_epa
def test_coastdown_output_reproduces(tmp_path):
    from src.experiments.r3a_coastdown_epa import run

    out = tmp_path / "c.csv"
    run(EPA, str(out))
    assert out.read_bytes() == open(COAST, "rb").read()


# --- scope limits ------------------------------------------------------------------------


def test_r3a_introduces_no_synthesis_or_simulation_code():
    for path in ("src/experiments/r3a_coastdown_epa.py", "src/provenance/registry.py"):
        text = open(path, encoding="utf-8").read()
        for banned in ("monte", "Monte", "P(safe", "random", "simulate", "MinimalSimulator"):
            assert banned not in text, (path, banned)
