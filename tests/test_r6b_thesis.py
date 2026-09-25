"""Test suite for Phase R6B: Full Thesis Drafting verification.

Checks:
- All required chapter draft files exist.
- Master thesis.md exists and is non-empty.
- Abstract length is strictly 250-300 words.
- Abstract, contribution paragraph, and conclusion contain the exact traced sentences.
- All 12 frozen figures (F1-F10, FA1, FA2) are placed and referenced.
- All 14 frozen tables (T1-T11, TA1-TA3) are present.
- All 42 claims (L01-L42) from research/R5A_CLAIM_LEDGER.csv are cited and grounded.
- Banned overclaim wording is absent from prose.
- Navigation-only sources S29 and S30 are never cited.
"""

import csv
import os
import re
import pytest

DRAFT_DIR = "thesis/draft"
MASTER_THESIS = os.path.join(DRAFT_DIR, "thesis.md")
BLUEPRINT_FILE = "docs/R5B_THESIS_BLUEPRINT.md"
LEDGER_FILE = "research/R5A_CLAIM_LEDGER.csv"

if not os.path.exists(DRAFT_DIR):
    pytest.skip("thesis/draft is held locally / embargoed pending institutional examination", allow_module_level=True)


CHAPTER_FILES = [
    "front_matter.md",
    "ch01_introduction.md",
    "ch02_background.md",
    "ch03_framework.md",
    "ch04_dataset_audit.md",
    "ch05_human_response.md",
    "ch06_vehicle_automation.md",
    "ch07_braking_model.md",
    "ch08_braking_results.md",
    "ch09_steering_sequence.md",
    "ch10_integration_boundary.md",
    "ch11_discussion.md",
    "ch12_limitations.md",
    "ch13_future_work.md",
    "ch14_conclusion.md",
    "appendices.md",
    "references.md",
]

FIGURE_IDS = [f"F{i}" for i in range(1, 11)] + ["FA1", "FA2"]
TABLE_IDS = [f"T{i}" for i in range(1, 12)] + ["TA1", "TA2", "TA3"]


@pytest.fixture(scope="module")
def blueprint():
    with open(BLUEPRINT_FILE, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def master_text():
    assert os.path.exists(MASTER_THESIS), f"Missing master thesis: {MASTER_THESIS}"
    with open(MASTER_THESIS, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def ledger_claims():
    claims = {}
    with open(LEDGER_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            claims[row["claim_id"]] = row
    return claims


def test_all_chapter_files_exist():
    """Verify that all component draft files exist and have substantial content."""
    for fname in CHAPTER_FILES:
        path = os.path.join(DRAFT_DIR, fname)
        assert os.path.exists(path), f"Missing draft file: {path}"
        assert os.path.getsize(path) > 500, f"Draft file too small: {path}"


def test_master_thesis_exists_and_assembled(master_text):
    """Verify that master thesis.md exists and has expected minimum word count (> 20,000 words)."""
    words = master_text.split()
    assert len(words) >= 20000, f"Master thesis has {len(words)} words, expected >= 20000"


def test_abstract_exactness_and_length(master_text, blueprint):
    """Abstract must be 250-300 words and match the traced abstract in the blueprint."""
    # Extract abstract from blueprint
    bp_abstract = blueprint.split("<!-- ABSTRACT:START -->")[1].split("<!-- ABSTRACT:END -->")[0].strip()
    bp_words = bp_abstract.split()
    assert 250 <= len(bp_words) <= 300, f"Blueprint abstract word count {len(bp_words)} out of range"

    # Check that the abstract in master_text matches blueprint abstract text
    assert bp_abstract in master_text, "Abstract in master thesis does not match frozen blueprint abstract"


def test_contribution_exactness(master_text, blueprint):
    """Contribution paragraph must match traced contribution in blueprint."""
    bp_contrib = blueprint.split("<!-- CONTRIBUTION:START -->")[1].split("<!-- CONTRIBUTION:END -->")[0].strip()
    assert bp_contrib in master_text, "Contribution paragraph does not match frozen blueprint contribution"


def test_conclusion_exactness(master_text, blueprint):
    """Conclusion must match traced conclusion in blueprint."""
    bp_conclusion = blueprint.split("<!-- CONCLUSION:START -->")[1].split("<!-- CONCLUSION:END -->")[0].strip()
    # Normalize whitespace
    bp_norm = " ".join(bp_conclusion.split())
    master_norm = " ".join(master_text.split())
    assert bp_norm in master_norm, "Conclusion does not match frozen blueprint conclusion"


def test_all_frozen_figures_placed(master_text):
    """Verify that all frozen figures F1-F10, FA1, FA2 are referenced and placed."""
    for fid in FIGURE_IDS:
        pattern = rf"\bFigure\s+{fid}\b|\b{fid}\b"
        assert re.search(pattern, master_text), f"Figure {fid} not referenced in master thesis"
        # Check image link exists
        assert f"{fid}_" in master_text or f"{fid}." in master_text, f"Image link for {fid} not found in master thesis"


def test_all_frozen_tables_placed(master_text):
    """Verify that all frozen tables T1-T11, TA1-TA3 are referenced and placed."""
    for tid in TABLE_IDS:
        pattern = rf"\bTable\s+{tid}\b"
        assert re.search(pattern, master_text), f"Table {tid} not referenced in master thesis"


def test_all_42_claims_referenced(master_text, ledger_claims):
    """Verify that all 42 claims L01-L42 from the ledger are cited in the thesis."""
    for cid in ledger_claims:
        pattern = rf"\b{cid}\b"
        assert re.search(pattern, master_text), f"Claim ID {cid} not cited in master thesis"


def test_no_navigation_sources_cited(master_text):
    """Ensure S29 and S30 navigation-only entries are never cited."""
    assert "S29" not in master_text, "Navigation-only source S29 cited in master thesis"
    assert "S30" not in master_text, "Navigation-only source S30 cited in master thesis"


def test_verbatim_claim_l41_block(master_text, ledger_claims):
    """Verify that Claim L41 is included with its required verbatim wording and qualifier."""
    l41 = ledger_claims["L41"]
    permitted = l41["permitted_wording"].strip()
    qualifier = l41["required_qualifier"].strip()

    assert permitted in master_text, "L41 permitted wording not found verbatim in master thesis"
    assert qualifier in master_text, "L41 required qualifier not found verbatim in master thesis"


def test_verbatim_claim_l42_block(master_text, ledger_claims):
    """Verify that Claim L42 is included with its required verbatim wording and qualifier."""
    l42 = ledger_claims["L42"]
    permitted = l42["permitted_wording"].strip()
    qualifier = l42["required_qualifier"].strip()

    assert permitted in master_text, "L42 permitted wording not found verbatim in master thesis"
    assert qualifier in master_text, "L42 required qualifier not found verbatim in master thesis"


def test_no_banned_overclaims(master_text):
    """Ensure strictly banned overclaim phrases do not appear in an unhedged/affirmative context."""
    banned_phrases = [
        "first ever",
        "novel closed-form",
        "validated system-level",
        "p(safe",
    ]
    lower_text = master_text.lower()
    for phrase in banned_phrases:
        assert phrase not in lower_text, f"Banned phrase '{phrase}' found in master thesis"


def test_no_absolute_user_paths():
    """Ensure zero hardcoded /Users/... paths exist anywhere in thesis drafts."""
    import glob
    for path in glob.glob(os.path.join(DRAFT_DIR, "*.md")):
        with open(path, encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                assert "/Users/" not in line, f"Absolute user path found in {path}:{idx}: {line.strip()}"


def test_all_figure_links_resolve(master_text):
    """Ensure all markdown figure links in master thesis resolve to existing canonical image files."""
    embeds = re.findall(r"!\[(.*?)\]\((.*?)\)", master_text)
    assert len(embeds) == 12, f"Expected 12 figure embeds, found {len(embeds)}"
    for alt, link in embeds:
        assert os.path.exists(link), f"Figure embed target does not exist on disk: {link} (alt: {alt})"


def test_f7_f8_captions_distinct_and_correct(master_text):
    """Ensure Figure F7 and F8 have distinct, correct captions and no duplicate F7 caption exists."""
    embeds = re.findall(r"!\[(.*?)\]\((.*?)\)", master_text)
    f7_embeds = [m for m in embeds if "F7" in m[0] or "F7" in m[1]]
    f8_embeds = [m for m in embeds if "F8" in m[0] or "F8" in m[1]]
    assert len(f7_embeds) == 1, f"Expected exactly 1 F7 embed, found {len(f7_embeds)}"
    assert len(f8_embeds) == 1, f"Expected exactly 1 F8 embed, found {len(f8_embeds)}"
    assert "F7_r3b_sensitivity" in f7_embeds[0][1]
    assert "F8_transition_branch_comparison" in f8_embeds[0][1]
    assert "Figure F8: Transition Policy Comparison" in f8_embeds[0][0]
    assert "Figure F7: Parameter Sensitivity Tornado" in f7_embeds[0][0]


def test_table_t11_matches_canonical_hazard_reconstruction(master_text):
    """Verify Table T11 matches results/R4V_steering_sequence/hazard_reconstruction.csv."""
    hz_csv = "results/R4V_steering_sequence/hazard_reconstruction.csv"
    assert os.path.exists(hz_csv)
    with open(hz_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cell = row["cell"]
            road = f"{float(row['road_id']):.1f}"
            station = f"{float(row['station_median_m']):.1f}"
            assert cell in master_text, f"Cell {cell} missing in master thesis"
            assert road in master_text, f"Road ID {road} for {cell} missing in Table T11"
            assert station in master_text, f"Station {station} for {cell} missing in Table T11"
    # Ensure d0_n1 is explicitly marked as excluded
    assert "d0_n1" in master_text
    assert "NO (excluded)" in master_text


def test_table_ta2_matches_canonical_r3b_outputs(master_text):
    """Verify Table TA2 matches canonical R3B bounds and classifications."""
    bounds_csv = "results/R3B_braking_bounds/t_required_bounds.csv"
    assert os.path.exists(bounds_csv)
    with open(bounds_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t_min = f"{float(row['t_required_min_s']):.4f}"
            t_max = f"{float(row['t_required_max_s']):.4f}"
            t_mid = f"{float(row['t_required_mid_s']):.4f}"
            assert t_min in master_text, f"T_req_min {t_min} missing in Table TA2"
            assert t_max in master_text, f"T_req_max {t_max} missing in Table TA2"
            assert t_mid in master_text, f"T_req_mid {t_mid} missing in Table TA2"


def test_claim_l14_timing_values_in_chapter_4(master_text):
    """Verify Chapter 4 reports exact Claim L14 timing values and no stale 6.25 s."""
    assert "6.40 s" in master_text, "Claim L14 TOR->LC median 6.40 s missing in thesis"
    assert "5.45–7.70" in master_text, "Claim L14 TOR->LC IQR 5.45–7.70 missing in thesis"
    assert "4.80 s" in master_text, "Claim L14 MS->LC median 4.80 s missing in thesis"
    assert "3.75–5.94" in master_text, "Claim L14 MS->LC IQR 3.75–5.94 missing in thesis"
    assert "6.25 s" not in master_text, "Stale 6.25 s timing still present in thesis"


def test_friction_cap_exactness(master_text):
    """Ensure the friction limit is consistently cited as 4.905 m/s² and never 4.9033 m/s²."""
    assert "4.905" in master_text, "Canonical friction limit 4.905 m/s² missing in thesis"
    assert "4.9033" not in master_text, "Obsolete 4.9033 m/s² still present in thesis"


def test_assurance_framework_citations_present(master_text):
    """Verify assurance framework tags [A01]–[A07] are all cited in Chapter 2."""
    for i in range(1, 8):
        tag = f"[A0{i}]"
        assert tag in master_text, f"Assurance citation tag {tag} missing in thesis"


def test_no_orphan_bibliography_entries():
    """Verify every reference entry defined in references.md is cited in the thesis body."""
    ref_path = os.path.join(DRAFT_DIR, "references.md")
    master_path = os.path.join(DRAFT_DIR, "thesis.md")
    with open(ref_path, encoding="utf-8") as f:
        ref_text = f.read()
    with open(master_path, encoding="utf-8") as f:
        body_text = f.read().split("# References")[0]

    ref_keys = re.findall(r"- \*\*\[(.*?)\]\*\*", ref_text)
    assert len(ref_keys) >= 25, f"Unexpectedly few reference keys: {len(ref_keys)}"
    for key in ref_keys:
        assert f"[{key}]" in body_text or f"{key}" in body_text, f"Orphan reference key: {key}"
