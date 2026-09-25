"""R5B thesis blueprint: every cited claim exists, drafted text is traced sentence by sentence,
provisional claims are hedged, and no overclaim wording appears."""

import csv
import re

import pytest

DOC = "docs/R5B_THESIS_BLUEPRINT.md"
LEDGER = "research/R5A_CLAIM_LEDGER.csv"
SECTIONS = ("abstract", "contribution", "conclusion")
PROSE = {"abstract": "ABSTRACT", "contribution": "CONTRIBUTION", "conclusion": "CONCLUSION"}
HEDGES = ("provisional", "unverified", "descriptive", "plausible")
BANNED = ("first ever", "novel closed-form", "reaction time", "intention time", "drivers learned", "is safe",
          "unsafe", "safety envelope", "p(safe", "validated system-level", "gap acceptance", "predicts")


@pytest.fixture(scope="module")
def doc():
    return open(DOC, encoding="utf-8").read()


@pytest.fixture(scope="module")
def ledger():
    return {r["claim_id"]: r for r in csv.DictReader(open(LEDGER, newline="", encoding="utf-8"))}


def block(doc, start, end):
    return doc.split(f"<!-- {start} -->")[1].split(f"<!-- {end} -->")[0]


def trace_rows(doc, name):
    rows = []
    for line in block(doc, f"TRACE:{name}:START", f"TRACE:{name}:END").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"[A-Z]\d+", cells[0]):
            rows.append({"id": cells[0], "type": cells[1], "claims": re.findall(r"L\d\d", cells[2]),
                         "contribution_refs": re.findall(r"R5A-C[1-5]", cells[2]), "sentence": cells[3]})
    return rows


def test_all_cited_claim_ids_exist(doc, ledger):
    cited = set(re.findall(r"\bL\d\d\b", doc))
    assert cited and cited <= set(ledger), cited - set(ledger)


@pytest.mark.parametrize("name", SECTIONS)
def test_every_claim_sentence_is_traced(doc, name):
    rows = trace_rows(doc, name)
    assert rows
    for r in rows:
        assert r["type"] in {"context", "claim", "limit"}, r["id"]
        if r["type"] != "context":
            assert r["claims"], r["id"]


@pytest.mark.parametrize("name", SECTIONS)
def test_prose_is_exactly_the_traced_sentences(doc, name):
    prose = " ".join(block(doc, f"{PROSE[name]}:START", f"{PROSE[name]}:END").split())
    sentences = " ".join(r["sentence"] for r in trace_rows(doc, name))
    assert prose == " ".join(sentences.split())


@pytest.mark.parametrize("name", SECTIONS)
def test_provisional_claims_are_hedged(doc, ledger, name):
    for r in trace_rows(doc, name):
        if r["type"] == "claim" and any(ledger[c]["status"] == "PROVISIONAL" for c in r["claims"]):
            assert any(h in r["sentence"].lower() for h in HEDGES), r["id"]


@pytest.mark.parametrize("name", SECTIONS)
def test_no_overclaim_wording(doc, name):
    text = block(doc, f"{PROSE[name]}:START", f"{PROSE[name]}:END").lower()
    for b in BANNED:
        assert b not in text, (name, b)


def test_blocked_or_withdrawn_claims_only_as_limits(doc, ledger):
    """A 'claim' sentence needs a supporting ledger id, or an R5A contribution reference (R5A §4)
    when it states a contribution; BLOCKED/WITHDRAWN ids alone never ground a claim."""
    for name in SECTIONS:
        for r in trace_rows(doc, name):
            if r["type"] == "claim":
                statuses = {ledger[c]["status"] for c in r["claims"]}
                assert (statuses - {"BLOCKED", "WITHDRAWN"}) or r["contribution_refs"], r["id"]


def test_abstract_length(doc):
    n = len(block(doc, "ABSTRACT:START", "ABSTRACT:END").split())
    assert 250 <= n <= 300, n


# --- R5B final revision / freeze (D034) -------------------------------------------------------


def test_no_stale_reopen_items(doc):
    for stale in ("T-1", "must first be reopened", "would need R5A to be reopened", "Traceability note"):
        assert stale not in doc, stale


def test_l41_l42_used_verbatim(doc, ledger):
    for cid in ("L41", "L42"):
        assert cid in doc
        assert ledger[cid]["permitted_wording"] in doc, cid
        assert ledger[cid]["required_qualifier"] in doc, cid
        assert ledger[cid]["forbidden_stronger_wording"] in doc, cid


def test_l41_always_marked_as_assumption_and_l42_scoped(doc):
    for line in doc.splitlines():
        if "L41" in line:
            assert "assum" in line.lower(), line[:80]
        if "L42" in line:
            assert "d0_n1" in line or "station-consistent" in line, line[:80]


def test_f9_band_label(doc):
    f9 = [l for l in doc.splitlines() if l.startswith("| **F9** |")]
    assert len(f9) == 1
    assert '"R3B assumed braking-delay interval"' in f9[0]
    assert "driver braking time" not in f9[0].lower()
    assert "authorship unverified" in f9[0]


def test_results_claim_lines(doc, ledger):
    results = doc.split("## 4. Results chapter blueprint")[1].split("## 5. Discussion structure")[0]
    lines = [l for l in results.splitlines() if "**Claims" in l]
    assert len(lines) == 8
    for l in lines:
        ids = re.findall(r"\bL\d\d\b", l.split("**Claims")[1])
        assert ids and set(ids) <= set(ledger), l
        if {ledger[i]["status"] for i in ids} <= {"BLOCKED", "WITHDRAWN"}:
            assert "boundary" in l.lower(), l


def test_frozen_figure_and_table_lists(doc):
    rows = {l.split("|")[1].strip().strip("*") for l in doc.splitlines() if l.startswith("| ")}
    figures = {f"F{i}" for i in range(1, 11)} | {"FA1", "FA2"}
    tables = {f"T{i}" for i in range(1, 12)} | {"TA1", "TA2", "TA3"}
    assert figures <= rows and tables <= rows
    assert "FA3" not in rows
    assert "**Frozen**" in doc
