"""R5A claim ledger: completeness, allowed statuses, blocked overclaims and consistency with the document."""

import collections
import csv
import re

import pytest

LEDGER = "research/R5A_CLAIM_LEDGER.csv"
DOC = "docs/R5A_FINAL_CLAIM_LEDGER.md"
STATUSES = {"SUPPORTED", "SUPPORTED_WITH_QUALIFIER", "PROVISIONAL", "BLOCKED", "WITHDRAWN"}
FIELDS = ["claim_id", "claim", "status", "permitted_wording", "forbidden_stronger_wording", "evidence_basis",
          "required_qualifier", "scope", "phase_source"]


@pytest.fixture(scope="module")
def ledger():
    return list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))


def by_claim(ledger):
    return {r["claim"]: r for r in ledger}


def test_fields_and_statuses(ledger):
    assert list(ledger[0].keys()) == FIELDS
    assert len({r["claim_id"] for r in ledger}) == len(ledger)
    for r in ledger:
        assert r["status"] in STATUSES, r["claim_id"]
        for f in ("permitted_wording", "forbidden_stronger_wording", "evidence_basis", "phase_source"):
            assert r[f].strip(), (r["claim_id"], f)


def test_required_claims_present(ledger):
    required = {
        "repeated exposure vs t_button", "participant covariates vs t_button", "t_button as driver reaction time",
        "t_button as R3B t1", "D003 brake onset", "D003 braking strength",
        "Manual_Start as longitudinal authority transfer",
        "Manual_Start as switch to manual mode / manual-input enablement", "steering onset timing",
        "steering authorship", "steering torque", "indicator timing", "lane crossing timing",
        "hazard distance at steering onset", "hazard distance at lane crossing", "target-lane gap descriptors",
        "R3B classification results", "TTC effect", "speed effect", "friction effect", "a_max effect",
        "P0/P1/P2 comparison", "authority-timing effect", "t1 sensitivity", "t1 = 4 s supplement",
        "D003-like 100 km/h / TTC 7 s result", "full takeover recoverability", "combined braking+steering synthesis",
        "production safety claim", "causal learning claim", "EV / one-pedal familiarity effect",
        "steering onset relative to the R3B assumed t1 window", "hazard distance at TOR"}
    assert required <= set(by_claim(ledger))


def test_overclaims_are_blocked_or_withdrawn(ledger):
    c = by_claim(ledger)
    for name in ("t_button as driver reaction time", "t_button as R3B t1", "D003 brake onset", "D003 braking strength",
                 "Manual_Start as longitudinal authority transfer", "steering torque", "full takeover recoverability",
                 "combined braking+steering synthesis", "production safety claim", "causal learning claim",
                 "EV / one-pedal familiarity effect"):
        assert c[name]["status"] == "BLOCKED", name
    for name in ("steering onset timing", "steering authorship", "indicator timing", "target-lane gap descriptors"):
        assert c[name]["status"] == "PROVISIONAL", name


def test_permitted_wording_avoids_banned_phrases(ledger):
    banned = ("first ever", "novel closed-form", "validated system-level", "p(safe", " is safe", "unsafe",
              "reaction time is", "intention time is")
    for r in ledger:
        text = r["permitted_wording"].lower()
        assert not any(b in text for b in banned), r["claim_id"]


def test_summary_counts_match_csv(ledger):
    counts = collections.Counter(r["status"] for r in ledger)
    doc = open(DOC, encoding="utf-8").read()
    for status, n in counts.items():
        assert re.search(rf"\| {status} \| {n} \|", doc), (status, n)


def test_no_new_result_files():
    """R5A is consolidation only: the ledger cites phases that exist."""
    phases = {"R0 baseline", "R1", "R2A", "R2B", "R2C", "R2C-lite", "R3B", "R4", "R4 internal audit", "R4V", "R4V-D"}
    for r in csv.DictReader(open(LEDGER, newline="", encoding="utf-8")):
        for p in (x.strip() for x in r["phase_source"].split(";")):
            assert p in phases, (r["claim_id"], p)


def test_amendment_claims_l41_l42(ledger):
    c = by_claim(ledger)
    l41 = c["steering onset relative to the R3B assumed t1 window"]
    assert l41["claim_id"] == "L41" and l41["status"] == "SUPPORTED_WITH_QUALIFIER"
    q = l41["required_qualifier"].lower()
    assert "assumption" in q and "unverified" in q and "4 s" in q and "no braking timing" in q
    assert "steering follows effective braking" in l41["forbidden_stronger_wording"].lower()
    # the underlying onset timing stays provisional
    assert c["steering onset timing"]["status"] == "PROVISIONAL"
    l42 = c["hazard distance at TOR"]
    assert l42["claim_id"] == "L42" and l42["status"] == "SUPPORTED_WITH_QUALIFIER"
    assert "directly logged" in l42["required_qualifier"].lower() and "d0_n1" in l42["required_qualifier"]
    assert "435" in l42["scope"]


def test_amendment_numbers_match_stored_outputs(ledger):
    import json
    import pandas as pd
    s = json.load(open("results/R4V_steering_sequence/summary.json", encoding="utf-8"))["r3b_relation"]
    assert s["r3b_t1_assumption_interval_s"] == [1.15, 3.0]
    assert round(s["fraction_steer_onset_after_t1_hi"], 2) == 0.75 and s["fraction_steer_onset_before_t1_lo"] == 0.0
    e = pd.read_csv("results/R4V_steering_sequence/event_table.csv")
    for c in [c for c in e.columns if c.startswith("onset_") and c.endswith("_rel_ms_s")]:
        y = (e.tor_to_ms_s + e[c]).dropna()
        assert (y > 3.0).mean() > 0.5, c                 # "predominantly after" for every detector
    y = e.tor_to_steer_onset_s.dropna()
    assert (y > 4.0).mean() < 0.5                         # not predominantly after the 4 s supplement bound
    h = e.loc[e.hazard_station_state == "CONSISTENT", "hazard_distance_at_tor_m"]
    assert len(h) == 435 and round(h.median()) == 178
    assert (e.loc[e.cell == "d0_n1", "hazard_station_state"] != "CONSISTENT").all()
