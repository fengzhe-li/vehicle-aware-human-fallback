"""Phase R3B-0 tests: source-quality rules, event-definition uniqueness and aliasing,
registry consistency, and friction-parameter provenance. No synthesis is tested
because none exists."""

import copy
import csv
import re

import pytest

from src.provenance import registry as reg


@pytest.fixture(scope="module")
def t():
    return {
        "sources": reg.load(reg.SOURCES),
        "registry": reg.load(reg.REGISTRY),
        "events": reg.load(reg.EVENTS),
        "vehicle": reg.load(reg.VEHICLE),
        "transition": reg.load(reg.TRANSITION),
        "hazard": reg.load(reg.HAZARD),
    }


def _cited(t):
    out = set()
    for name in ("vehicle", "transition", "hazard"):
        for r in t[name]:
            out |= set(reg._ids(r["evidence_source_ids"]))
    for p in t["registry"]:
        out |= set(reg._ids(p["source_ids"]))
    for e in t["events"]:
        out |= set(reg._ids(e["source_ids"]))
    return out


# --- source quality ---------------------------------------------------------------------


def test_navigation_only_sources_are_never_cited(t):
    nav = {s["source_id"] for s in t["sources"] if s["primary_or_secondary"] == "NAVIGATION_ONLY"}
    assert {"S29", "S30"} <= nav  # Wikipedia and the certification summary
    assert not (nav & _cited(t))


def test_r157_is_backed_by_official_text(t):
    src = {s["source_id"]: s for s in t["sources"]}
    for sid in ("S02", "S31"):
        assert src[sid]["verification_status"] == "FULL TEXT VERIFIED"
        assert len(src[sid]["document_sha256"]) == 64
    for r in t["transition"]:
        if "R157" in r["reported_value_or_rule"] or "R157" in r["context"]:
            assert {"S02", "S31"} & set(reg._ids(r["evidence_source_ids"])), r["row_id"]


def test_corrected_r157_wording_is_not_reintroduced(t):
    text = " ".join(" ".join(r.values()) for name in ("vehicle", "transition", "hazard", "registry") for r in t[name])
    assert not re.search(r"10 s transition period(?!'? was an oversimplification)", text)
    mrm = next(r for r in t["transition"] if r["row_id"] == "T09")
    assert "aim" in mrm["reported_value_or_rule"] and "not a hard maximum" in mrm["notes"]


def test_standards_access_status_is_explicit(t):
    src = {s["source_id"]: s for s in t["sources"]}
    assert src["S14"]["verification_status"] == "SECONDARY ONLY"                    # ISO 15622
    assert src["S15"]["verification_status"] == "ABSTRACT OR PUBLIC SUMMARY ONLY"    # ISO 23793-1
    assert src["S15"]["used_quantitatively"] == "NO"
    assert src["S01"]["verification_status"] == "FULL TEXT VERIFIED"                # R13-H


def test_no_synthesis_ready_parameter_rests_only_on_weak_sources(t):
    for p in t["registry"]:
        if p["synthesis_entry"] == "YES":
            assert reg.quality_flag(reg._ids(p["source_ids"]), t["sources"]) == "OK", p["param_id"]
    iso_acc = next(p for p in t["registry"] if p["symbol"].startswith("a_auto_max"))
    assert iso_acc["synthesis_entry"] == "NO"


def test_validator_flags_weak_synthesis_ready_parameter(t):
    rows = copy.deepcopy(t["registry"])
    p = next(r for r in rows if r["symbol"] == "TOT")
    p["synthesis_entry"], p["confidence"] = "YES", "MEDIUM"
    errs = reg.validate_registry(rows, reg.citable(t["sources"]), ".", t["sources"])
    assert any("abstract/secondary" in e for e in errs)


def test_validator_rejects_citing_navigation_only_source(t):
    rows = copy.deepcopy(t["transition"])
    rows[0]["evidence_source_ids"] = "S29"
    errs = reg.validate_matrix(rows, reg.citable(t["sources"]), reg.TRANSITION_STATUS, "status", "transition")
    assert any("S29" in e for e in errs)


# --- events -------------------------------------------------------------------------------


def test_event_registry_is_unique_and_complete(t):
    ids = [e["event_id"] for e in t["events"]]
    assert len(ids) == len(set(ids))
    assert reg.REQUIRED_EVENTS <= set(ids)
    assert reg.validate_events(t["events"], reg.citable(t["sources"])) == []


def test_no_tor_or_manual_start_alias_for_authority_transfer(t):
    ev = {e["event_id"]: e for e in t["events"]}
    a = ev["E_authority_transfer"]
    assert a["observability"] == "LATENT" and a["d003_proxy"] == ""
    assert {"E_TOR", "E_driver_acknowledgement"} <= set(reg._ids(a["must_not_alias"]))
    assert "Manual_Start" in ev["E_driver_acknowledgement"]["d003_proxy"]
    assert "E_first_channel_activity" in reg._ids(ev["E_first_human_input"]["must_not_alias"])
    assert ev["E_first_human_input"]["d003_proxy"] == ""


def test_validator_catches_authority_alias(t):
    rows = copy.deepcopy(t["events"])
    a = next(e for e in rows if e["event_id"] == "E_authority_transfer")
    a["d003_proxy"], a["observability"] = "Time_Manual_Start", "OBSERVABLE"
    errs = reg.validate_events(rows, reg.citable(t["sources"]))
    assert any("authority transfer" in e for e in errs)


# --- friction provenance ------------------------------------------------------------------


def test_friction_parameters_have_unit_range_and_source(t):
    for p in t["registry"]:
        if p["symbol"] in reg.FRICTION_SYMBOLS and p["synthesis_entry"] != "NO":
            assert p["unit"] and p["value_low"] and p["value_high"] and p["source_ids"], p["param_id"]
            assert float(p["value_low"]) <= float(p["value_high"])


def test_validator_rejects_friction_parameter_without_range(t):
    rows = copy.deepcopy(t["registry"])
    p = next(r for r in rows if r["symbol"] == "mu")
    p["value_high"] = ""
    errs = reg.validate_registry(rows, reg.citable(t["sources"]), ".", t["sources"])
    assert any("friction parameter" in e for e in errs)
