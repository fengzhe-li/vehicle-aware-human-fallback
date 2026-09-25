"""R4 synthesis-readiness audit: completeness and the prohibited cross-layer aliases."""

import csv

import pytest

MATRIX = "research/R4_SYNTHESIS_READINESS_MATRIX.csv"
LINKS = "research/R4_CROSS_LAYER_LINKS.csv"
CLASSES = {"IDENTIFIED", "PARTIALLY IDENTIFIED", "ASSUMPTION-DEPENDENT", "NOT IDENTIFIABLE"}


@pytest.fixture(scope="module")
def matrix():
    return {r["variable"]: r for r in csv.DictReader(open(MATRIX, newline="", encoding="utf-8"))}


@pytest.fixture(scope="module")
def links():
    return {r["link"]: r for r in csv.DictReader(open(LINKS, newline="", encoding="utf-8"))}


def test_matrix_covers_required_variables(matrix):
    required = {"TOR time", "t_button", "t1", "t2", "t3", "first human input", "effective human control",
                "authority transfer", "braking command magnitude", "a_pre", "a_max", "friction μ", "speed", "TTC",
                "hazard distance", "lane-change onset", "manoeuvre completion", "Manual_Stop / handback",
                "steering escape-path availability"}
    assert required <= set(matrix)
    for r in matrix.values():
        assert r["observable_in_d003"] in {"YES", "NO", "PARTIAL"}
        assert r["provenance_source"] and r["uncertainty_representation"]


def test_latent_quantities_are_not_treated_as_observed(matrix):
    for v in ("t1", "first human input", "effective human control", "authority transfer", "braking command magnitude"):
        assert matrix[v]["observable_in_d003"] == "NO" and matrix[v]["directly_measured"] == "NO", v
    assert matrix["t1"]["explicit_assumption"] == "YES"
    assert matrix["t_button"]["usable_in_r3b"] == "NO"          # t_button is not t1
    assert matrix["first human input"]["usable_in_future_synthesis"] == "NO"
    assert matrix["manoeuvre completion"]["usable_in_future_synthesis"] == "NO"


def test_prohibited_aliases_are_not_identifiable(links):
    assert set(r["classification"] for r in links.values()) <= CLASSES
    for link in ("t_button → t1", "first human input → effective control", "P2 support → D003 automation behaviour",
                 "participant familiarity → braking strength", "TTC → full takeover recoverability",
                 "Manual_Stop → recovery completion", "first channel activity → first human input",
                 "lane change → effective longitudinal control"):
        assert links[link]["classification"] == "NOT IDENTIFIABLE", link
    assert links["TOR → authority transfer"]["classification"] == "ASSUMPTION-DEPENDENT"
    assert links["TTC → braking-only recoverability"]["classification"] == "ASSUMPTION-DEPENDENT"


def test_no_probability_or_score_introduced():
    text = open("docs/R4_SYNTHESIS_READINESS.md", encoding="utf-8").read().lower()
    for banned in ("recoverability score", "p(safe", "safe fallback probability"):
        assert banned not in text
