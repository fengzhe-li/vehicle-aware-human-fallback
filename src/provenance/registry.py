"""Validation of the R3A evidence tables and the parameter provenance registry.

No parameter may enter a later synthesis without provenance. These checks make
that rule mechanical:

- every table row has a unique id and a status from the allowed vocabulary;
- every cited source id resolves to `research/R3A_SOURCE_REGISTER.csv`;
- numeric registry values parse and are ordered low <= central <= high;
- a parameter marked as used in code names an existing file and symbol;
- a NOT IDENTIFIABLE or LOW-confidence parameter cannot be marked ready for synthesis;
- identifiability rows reference existing registry and matrix ids.

The functions return lists of error strings (empty = valid) so tests can show all
problems at once.
"""

from __future__ import annotations

import csv
import os
import re
from typing import Dict, Iterable, List, Sequence

SOURCES = "research/R3A_SOURCE_REGISTER.csv"
REGISTRY = "research/PARAMETER_PROVENANCE_REGISTRY.csv"
VEHICLE = "research/data_matrix/VEHICLE_RESPONSE_EVIDENCE_MATRIX.csv"
TRANSITION = "research/data_matrix/TRANSITION_EVIDENCE_MATRIX.csv"
HAZARD = "research/data_matrix/HAZARD_STATE_MATRIX.csv"
IDENTIFIABILITY = "research/identifiability/identifiability_matrix_R3A.csv"
EVENTS = "research/SYSTEM_EVENT_REGISTRY.csv"

PARAMETER_STATUS = {"FIXED", "DISTRIBUTION", "BOUNDED", "CONTEXT-DEPENDENT", "NOT IDENTIFIABLE"}
REGISTRY_STATUS = PARAMETER_STATUS | {"EXTERNALLY PARAMETERISED"}
TRANSITION_STATUS = PARAMETER_STATUS | {"POLICY VARIABLE"}
IDENTIFIABILITY_STATUS = {"IDENTIFIABLE", "PARTIALLY IDENTIFIABLE", "BOUNDED", "EXTERNALLY PARAMETERISED",
                          "NOT IDENTIFIABLE"}
ACCESS_LEVELS = {"FULL_TEXT_READ", "ABSTRACT_OR_SUMMARY", "SECONDARY_QUOTATION", "DATASET_PROCESSED",
                 "REPO_EXISTING", "FIRST_PRINCIPLES", "PROJECT_RESULT", "NAVIGATION_ONLY"}
VERIFICATION = {"FULL TEXT VERIFIED", "ABSTRACT OR PUBLIC SUMMARY ONLY", "SECONDARY ONLY", "NOT VERIFIED",
                "DATASET VERIFIED", "PRIOR PHASE RECORD", "NOT APPLICABLE"}
VERIFIED = {"FULL TEXT VERIFIED", "DATASET VERIFIED", "NOT APPLICABLE"}
SOURCE_ROLE = {"PRIMARY", "SECONDARY", "NAVIGATION_ONLY"}
FRICTION_SYMBOLS = {"mu", "a_max_wet", "a_y_max"}
REQUIRED_EVENTS = {"E_TOR", "E_authority_transfer", "E_first_human_input", "E_effective_human_control",
                   "E_lane_change", "E_handback", "E_hazard_boundary", "E_MRM_start", "E_MRM_complete"}
OBSERVABILITY = {"OBSERVABLE", "LATENT", "DERIVED", "OBSERVABLE (in systems that log it)"}
VALUE_TYPES = {"POINT", "RANGE", "DISTRIBUTION", "BOUND", "NONE"}
SYNTHESIS_ENTRY = {"YES", "CONDITIONAL", "NO"}
YES_NO_PARTIAL = {"YES", "NO", "PARTIAL"}

REGISTRY_FIELDS = ["param_id", "symbol", "definition", "unit", "layer", "source_ids", "source_year",
                   "source_population_or_vehicle_class", "scenario", "value_type", "value_low", "value_central",
                   "value_high", "value_text", "confidence", "assumptions", "status",
                   "transferable_to_current_model", "currently_used_in_code", "code_reference", "code_value",
                   "synthesis_entry", "source_quality_flag", "interval_readiness"]
READINESS = {"READY AS FIXED / DIRECTLY SUPPORTED", "READY AS BOUNDED INTERVAL", "CONDITIONAL / SCENARIO-SPECIFIC",
             "BLOCKED", "NOT IDENTIFIABLE"}


def load(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ids(value: str) -> List[str]:
    return [s.strip() for s in value.split(";") if s.strip()]


def _unique(rows: Sequence[Dict[str, str]], key: str, table: str) -> List[str]:
    seen, errors = set(), []
    for r in rows:
        if r[key] in seen:
            errors.append(f"{table}: duplicate {key} {r[key]}")
        seen.add(r[key])
    return errors


def validate_sources(sources: Sequence[Dict[str, str]]) -> List[str]:
    errors = _unique(sources, "source_id", "sources")
    for s in sources:
        if s["access_level"] not in ACCESS_LEVELS:
            errors.append(f"sources: {s['source_id']} has unknown access_level {s['access_level']!r}")
        if not s["citation"].strip():
            errors.append(f"sources: {s['source_id']} has no citation")
        if s["verification_status"] not in VERIFICATION:
            errors.append(f"sources: {s['source_id']} has unknown verification_status {s['verification_status']!r}")
        if s["primary_or_secondary"] not in SOURCE_ROLE:
            errors.append(f"sources: {s['source_id']} has unknown primary_or_secondary {s['primary_or_secondary']!r}")
        if s["used_quantitatively"] not in ("YES", "NO"):
            errors.append(f"sources: {s['source_id']} used_quantitatively must be YES/NO")
        if (s["access_level"] == "NAVIGATION_ONLY") != (s["primary_or_secondary"] == "NAVIGATION_ONLY"):
            errors.append(f"sources: {s['source_id']} navigation-only flags inconsistent")
        if s["access_level"] == "FULL_TEXT_READ" and s["verification_status"] not in ("FULL TEXT VERIFIED", "DATASET VERIFIED"):
            errors.append(f"sources: {s['source_id']} read in full but not marked verified")
        if s["verification_status"] == "FULL TEXT VERIFIED" and s["access_level"] != "FULL_TEXT_READ":
            errors.append(f"sources: {s['source_id']} marked full-text verified without full-text access")
    return errors


def citable(sources: Sequence[Dict[str, str]]) -> List[str]:
    """Source ids that may be cited as evidence (navigation-only aids are excluded)."""
    return [s["source_id"] for s in sources if s["primary_or_secondary"] != "NAVIGATION_ONLY"]


def quality_flag(source_ids: Sequence[str], sources: Sequence[Dict[str, str]]) -> str:
    ver = {s["source_id"]: s["verification_status"] for s in sources}
    return "OK" if any(ver.get(i) in VERIFIED for i in source_ids) else "ABSTRACT/SECONDARY/PRIOR-PHASE ONLY"


def validate_matrix(rows: Sequence[Dict[str, str]], source_ids: Iterable[str], status_vocab: set,
                    status_field: str, table: str) -> List[str]:
    known = set(source_ids)
    errors = _unique(rows, "row_id", table)
    for r in rows:
        if r[status_field] not in status_vocab:
            errors.append(f"{table}: {r['row_id']} has status {r[status_field]!r}")
        cited = _ids(r["evidence_source_ids"])
        if not cited:
            errors.append(f"{table}: {r['row_id']} cites no source")
        errors += [f"{table}: {r['row_id']} cites unknown source {s}" for s in cited if s not in known]
    return errors


def _num(v: str):
    return float(v) if v.strip() else None


def validate_registry(registry: Sequence[Dict[str, str]], source_ids: Iterable[str],
                      repo_root: str = ".", sources: Sequence[Dict[str, str]] = ()) -> List[str]:
    known = set(source_ids)
    errors = _unique(registry, "param_id", "registry")
    if registry and list(registry[0].keys()) != REGISTRY_FIELDS:
        errors.append("registry: columns differ from REGISTRY_FIELDS")
    for p in registry:
        pid = p["param_id"]
        if p["status"] not in REGISTRY_STATUS:
            errors.append(f"registry: {pid} status {p['status']!r}")
        if p["value_type"] not in VALUE_TYPES:
            errors.append(f"registry: {pid} value_type {p['value_type']!r}")
        if p["synthesis_entry"] not in SYNTHESIS_ENTRY:
            errors.append(f"registry: {pid} synthesis_entry {p['synthesis_entry']!r}")
        for f in ("transferable_to_current_model", "currently_used_in_code"):
            if p[f] not in YES_NO_PARTIAL:
                errors.append(f"registry: {pid} {f} {p[f]!r}")
        cited = _ids(p["source_ids"])
        if not cited:
            errors.append(f"registry: {pid} has no source")
        errors += [f"registry: {pid} cites unknown source {s}" for s in cited if s not in known]
        try:
            vals = [_num(p[k]) for k in ("value_low", "value_central", "value_high")]
        except ValueError:
            errors.append(f"registry: {pid} has a non-numeric value column")
            continue
        present = [v for v in vals if v is not None]
        if present != sorted(present):
            errors.append(f"registry: {pid} values not ordered low <= central <= high")
        if p["value_type"] == "NONE" and present:
            errors.append(f"registry: {pid} value_type NONE but numeric values given")
        if p["value_type"] != "NONE" and not present and not p["value_text"].strip():
            errors.append(f"registry: {pid} has no value")
        if p["synthesis_entry"] == "YES" and (p["status"] == "NOT IDENTIFIABLE" or p["confidence"].startswith("LOW")):
            errors.append(f"registry: {pid} marked synthesis-ready but is {p['status']} / {p['confidence']}")
        if p["currently_used_in_code"] in ("YES", "PARTIAL"):
            errors += _check_code_reference(pid, p["code_reference"], repo_root)
        if sources:
            flag = quality_flag(cited, sources)
            if p["source_quality_flag"] != flag:
                errors.append(f"registry: {pid} source_quality_flag {p['source_quality_flag']!r} != computed {flag!r}")
            if p["synthesis_entry"] == "YES" and flag != "OK":
                errors.append(f"registry: {pid} synthesis-ready but rests only on abstract/secondary/prior-phase sources")
        ready = p["interval_readiness"]
        if ready not in READINESS:
            errors.append(f"registry: {pid} interval_readiness {ready!r}")
        if ready.startswith("READY") and (p["synthesis_entry"] != "YES" or p["source_quality_flag"] != "OK"):
            errors.append(f"registry: {pid} READY but not synthesis-entry YES with verified sources")
        if p["synthesis_entry"] == "YES" and not ready.startswith("READY"):
            errors.append(f"registry: {pid} synthesis-entry YES but readiness {ready!r}")
        if ready == "READY AS BOUNDED INTERVAL" and not (p["value_low"].strip() and p["value_high"].strip()):
            errors.append(f"registry: {pid} bounded interval without both bounds")
        if p["synthesis_entry"] == "NO" and ready not in ("BLOCKED", "NOT IDENTIFIABLE"):
            errors.append(f"registry: {pid} synthesis-entry NO but readiness {ready!r}")
        if p["symbol"] in FRICTION_SYMBOLS and p["synthesis_entry"] != "NO":
            if not (p["unit"].strip() and p["value_low"].strip() and p["value_high"].strip() and cited):
                errors.append(f"registry: {pid} friction parameter entering synthesis without unit/range/source")
    return errors


def _check_code_reference(pid: str, ref: str, repo_root: str) -> List[str]:
    if not ref.strip():
        return [f"registry: {pid} used in code but has no code_reference"]
    errors = []
    for part in _ids(ref):
        path, _, symbol = part.partition(":")
        full = os.path.join(repo_root, path.strip())
        if not os.path.exists(full):
            errors.append(f"registry: {pid} code_reference file missing: {path}")
            continue
        if symbol:
            name = re.split(r"[ (]", symbol.strip())[0].split(".")[-1]
            if name and name not in open(full, encoding="utf-8").read():
                errors.append(f"registry: {pid} symbol {name!r} not found in {path}")
    return errors


def validate_identifiability(rows: Sequence[Dict[str, str]], registry_ids: Iterable[str],
                             matrix_ids: Iterable[str]) -> List[str]:
    reg, mat = set(registry_ids), set(matrix_ids)
    errors = []
    for r in rows:
        if r["r3a_identifiability"] not in IDENTIFIABILITY_STATUS:
            errors.append(f"identifiability: {r['quantity']} status {r['r3a_identifiability']!r}")
        errors += [f"identifiability: {r['quantity']} unknown param {i}" for i in _ids(r["registry_param_ids"]) if i not in reg]
        errors += [f"identifiability: {r['quantity']} unknown matrix row {i}" for i in _ids(r["matrix_row_ids"]) if i not in mat]
        if not _ids(r["matrix_row_ids"]):
            errors.append(f"identifiability: {r['quantity']} has no evidence row")
    return errors


def validate_events(events: Sequence[Dict[str, str]], source_ids: Iterable[str]) -> List[str]:
    known = set(source_ids)
    ids = [e["event_id"] for e in events]
    errors = [f"events: duplicate event_id {i}" for i in set(ids) if ids.count(i) > 1]
    errors += [f"events: required event missing {i}" for i in sorted(REQUIRED_EVENTS - set(ids))]
    by_id = {e["event_id"]: e for e in events}
    for e in events:
        if e["observability"] not in OBSERVABILITY:
            errors.append(f"events: {e['event_id']} observability {e['observability']!r}")
        errors += [f"events: {e['event_id']} cites unknown source {s}" for s in _ids(e["source_ids"]) if s not in known]
        for other in _ids(e["must_not_alias"]):
            if other not in by_id:
                errors.append(f"events: {e['event_id']} must_not_alias unknown event {other}")
            elif e["d003_proxy"].strip() and e["d003_proxy"] == by_id[other]["d003_proxy"]:
                errors.append(f"events: {e['event_id']} and {other} share a D003 proxy")
    # explicit semantic rules
    if "E_authority_transfer" in by_id:
        a = by_id["E_authority_transfer"]
        if a["observability"] != "LATENT" or "Manual_Start" in a["d003_proxy"] or "Takeover_Request" in a["d003_proxy"]:
            errors.append("events: authority transfer must be latent and must not use TOR or Manual_Start as proxy")
        for x in ("E_TOR", "E_driver_acknowledgement"):
            if x not in _ids(a["must_not_alias"]):
                errors.append(f"events: E_authority_transfer must declare must_not_alias {x}")
    if "E_first_human_input" in by_id and "E_first_channel_activity" not in _ids(by_id["E_first_human_input"]["must_not_alias"]):
        errors.append("events: first human input must not alias first channel activity")
    return errors


def validate_all(repo_root: str = ".") -> List[str]:
    j = lambda p: os.path.join(repo_root, p)
    sources = load(j(SOURCES))
    sid = citable(sources)
    registry = load(j(REGISTRY))
    vehicle, transition, hazard = load(j(VEHICLE)), load(j(TRANSITION)), load(j(HAZARD))
    errors = validate_sources(sources)
    errors += validate_matrix(vehicle, sid, PARAMETER_STATUS, "status", "vehicle")
    errors += validate_matrix(transition, sid, TRANSITION_STATUS, "status", "transition")
    errors += validate_matrix(hazard, sid, IDENTIFIABILITY_STATUS, "identifiability", "hazard")
    errors += validate_registry(registry, sid, repo_root, sources)
    errors += validate_events(load(j(EVENTS)), sid)
    errors += validate_identifiability(load(j(IDENTIFIABILITY)), [p["param_id"] for p in registry],
                                       [r["row_id"] for r in vehicle + transition + hazard])
    return errors
