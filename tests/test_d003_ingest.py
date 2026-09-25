"""Phase R1 tests for strict D003 ingestion (`src/data/d003_ingest.py`).

Unit tests use small synthetic CSVs that reproduce the observed D003 file format
(composite laneGap cell, export channels, trailing export footer). Integration
tests check the verified counts on the real archive and are skipped, visibly,
only when the archive is absent.
"""

import csv
import io
import os
from collections import Counter

import numpy as np
import pytest

from src.data.d003_ingest import (
    FULL_HEADER,
    HEADER_VARIANTS,
    LANE_CHANGE_COLUMN,
    LANE_GAP_COMPOSITE_COLUMN,
    MANUAL_START_COLUMN,
    MANUAL_STOP_COLUMN,
    TOR_COLUMN,
    TTC_COLUMN,
    UNRESOLVED,
    D003ParseError,
    D003SchemaError,
    audit_trial,
    check_footer,
    check_lane_gap_clock,
    classify_adjacent_lane_values,
    event_clock_checks,
    identify_header_variant,
    lane_transitions,
    observation_events,
    parse_trial_text,
    resolve_handback,
    resolve_tor,
    validate_lane_change,
)

NAME = "4. simulator_data/density_20_nback_1_id_7_simulator_data.csv"
DT = 0.05
EPOCH0 = 1_699_708_675.0
DIST0 = 250.0
SPEED = 25.0
FOLLOW = "[82 (Distance/Distance_to_Following_Vehicle)].ExportChannel-val"
LEAD_NEXT = "[83 (Distance/Distance_to_Leading_Vehicle_Next_Lane)].ExportChannel-val"
DIST = "[85 (Distance/Distance_to_Construction)].ExportChannel-val"


def make_csv(
    n=400,
    header=FULL_HEADER,
    tor_values=(3.0,),
    manual_start=4.0,
    manual_stops=(12.0,),
    lane_change=6.0,
    lane_change_first_row_time=None,
    lanes=((0.0, 2, 15), (6.05, 3, 15)),
    footer=False,
    footer_override=None,
    lane_gap_time_offset=0.0,
    cell_overrides=None,
):
    """Synthetic D003-format CSV text.

    `lanes`: list of (start_time, lane_id, road_id). Event channels become
    non-null 0.1 s after their value (as observed), unless overridden.
    """
    rows = []
    t = [i * DT for i in range(n)]
    for i, ti in enumerate(t):
        dist = DIST0 - SPEED * ti
        lane, road = 0, 0
        for start, lid, rid in lanes:
            if ti >= start:
                lane, road = lid, rid
        r = {c: "" for c in header}
        r["time"] = repr(EPOCH0 + ti)
        if i == 0:
            r[LANE_GAP_COMPOSITE_COLUMN] = "null,0"
            rows.append(r)
            continue
        for c in header[1:35]:
            r[c] = "0.0"
        r["[00].VehicleUpdate-speed.001"] = repr(SPEED)
        r["[00].VehicleUpdate-roadInfo-laneId.0"] = repr(float(lane))
        r["[00].VehicleUpdate-roadInfo-roadId.0"] = repr(float(road))
        # component 1: +1.7 before and -1.6 after a lane change (a 3.3 m jump, as observed)
        c1 = 1.7 if lane in (2, 6, 7) else -1.6
        r[LANE_GAP_COMPOSITE_COLUMN] = f"{c1},{ti + lane_gap_time_offset}"
        r[TTC_COLUMN] = repr(dist / SPEED)
        r[DIST] = repr(dist)
        r[FOLLOW] = "0.0"
        r[LEAD_NEXT] = "0.0" if ti < 2 else "40.0"
        r["[84 (Distance/Distance_to_Following_Vehicle_Next_Lane)].ExportChannel-val"] = "12.5"
        if TOR_COLUMN in header:
            current = [v for v in tor_values if ti >= v + 0.1]
            if current:
                r[TOR_COLUMN] = repr(current[-1])
        if ti >= manual_start + 0.1:
            r[MANUAL_START_COLUMN] = repr(manual_start)
        stops = [v for v in manual_stops if ti >= v + 0.1]
        if stops:
            r[MANUAL_STOP_COLUMN] = repr(stops[-1])
        if LANE_CHANGE_COLUMN in header and lane_change is not None:
            first = lane_change + 0.1 if lane_change_first_row_time is None else lane_change_first_row_time
            if ti >= first - 1e-9:
                r[LANE_CHANGE_COLUMN] = repr(lane_change)
        rows.append(r)
    for (ri, col), val in (cell_overrides or {}).items():
        rows[ri][col] = val
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow([r[c] for c in header])
    if footer:
        export_cols = [c for c in header if c.endswith("ExportChannel-val")]
        last = rows[-1]
        values = [str(100 + j) for j in range(len(export_cols))]
        values += [last[c] if last[c] else "0.0" for c in export_cols]
        if footer_override:
            values = footer_override(values)
        w.writerow([""] + values + [""] * (len(header) - 1 - len(values)))
    return buf.getvalue()


def load(**kw):
    return parse_trial_text(make_csv(**kw), NAME)


# --- header variants ---------------------------------------------------------


@pytest.mark.parametrize("variant", sorted(HEADER_VARIANTS))
def test_known_header_variants_are_recognised(variant):
    header = HEADER_VARIANTS[variant]
    trial = load(header=header)
    assert trial.header_variant == variant
    assert identify_header_variant(header) == variant


def test_unknown_header_variant_fails_loudly():
    header = FULL_HEADER + ("extra",)
    with pytest.raises(D003SchemaError, match="Unknown D003 header variant"):
        identify_header_variant(header)
    reordered = (FULL_HEADER[1], FULL_HEADER[0]) + FULL_HEADER[2:]
    with pytest.raises(D003SchemaError):
        identify_header_variant(reordered)


# --- lane_gap composite ------------------------------------------------------


def test_lane_gap_composite_parsed_into_two_components_with_raw_kept():
    trial = load()
    tel = trial.telemetry
    assert tel["lane_gap_raw"].iloc[0] == "null,0"
    assert np.isnan(tel["lane_gap_component1"].iloc[0])
    assert trial.null_token_counts["laneGap.component1"] == 1
    assert tel["lane_gap_component1"].iloc[1:].notna().all()
    assert tel["lane_gap_raw"].iloc[5].count(",") == 1
    err, notices = check_lane_gap_clock(trial)
    assert err < 1e-6 and notices == []  # epoch-magnitude float rounding is ~1e-7 s, as in the real data
    assert "lane_center_offset" not in tel.columns  # meaning is not asserted


def test_lane_gap_reltime_mismatch_is_an_error():
    trial = load(lane_gap_time_offset=0.05)
    err, notices = check_lane_gap_clock(trial)
    assert err == pytest.approx(0.05, abs=1e-6)
    assert [n.code for n in notices] == ["LANE_GAP_RELTIME_MISMATCH"]
    assert "LANE_GAP_RELTIME_MISMATCH" in audit_trial(trial)["qa_errors"]


def test_lane_gap_cell_without_pair_fails():
    with pytest.raises(D003ParseError, match="not a '<value>,<time>' pair"):
        load(cell_overrides={(5, LANE_GAP_COMPOSITE_COLUMN): "0.5"})


def test_unknown_token_is_not_silently_coerced():
    with pytest.raises(D003ParseError, match="Unparseable"):
        load(cell_overrides={(5, "[00].VehicleUpdate-brake"): "abc"})


# --- trailing footer / empty timestamps -------------------------------------


def test_trailing_export_footer_is_informational_when_consistent():
    trial = load(footer=True)
    assert trial.footer is not None
    assert len(trial.telemetry) == 400  # footer excluded from telemetry
    assert [n.code for n in check_footer(trial)] == ["FOOTER_EVENTS_CONSISTENT"]
    row = audit_trial(trial)
    assert "TRAILING_EXPORT_FOOTER" in row["qa_info"]
    assert row["qa_errors"] == ""


def test_footer_with_inconsistent_event_value_is_an_error():
    def corrupt(values):
        k = len(values) // 2
        values[k] = "99.0"  # TOR slot of the export block
        return values

    trial = load(footer=True, footer_override=corrupt)
    assert [n.code for n in check_footer(trial)] == ["FOOTER_EVENT_MISMATCH"]


def test_footer_with_unexpected_shape_fails():
    with pytest.raises(D003SchemaError, match="export footer"):
        load(footer=True, footer_override=lambda v: v[:-1])


def test_empty_timestamp_before_final_row_fails():
    with pytest.raises(D003SchemaError, match="empty timestamp"):
        load(cell_overrides={(10, "time"): ""})


def test_row_count_is_not_assumed():
    assert len(load(n=137).telemetry) == 137


# --- TOR handling -------------------------------------------------------------


def test_single_tor():
    res = resolve_tor(load(tor_values=(10.0 - 7.0,)))
    assert res.state == "SINGLE" and res.selected == 3.0 and res.protocol_consistent


def test_missing_tor_column():
    res = resolve_tor(load(header=HEADER_VARIANTS["NO_TOR_44"]))
    assert res.state == "MISSING_TOR_COLUMN" and res.selected is None


def test_multi_tor_resolved_only_by_protocol_ttc():
    # TTC = (250 - 25 t) / 25 = 10 - t: TOR at t=3 has TTC 7 (protocol), t=4 has TTC 6.
    trial = load(tor_values=(3.0, 4.0))
    res = resolve_tor(trial)
    assert res.state == "MULTI_RESOLVED_BY_PROTOCOL_TTC"
    assert res.raw_values == [3.0, 4.0]
    assert res.selected == 3.0
    assert "MULTI_TOR_RESOLVED_BY_PROTOCOL" in audit_trial(trial)["qa_warnings"]


def test_multi_tor_without_unique_protocol_match_stays_unresolved():
    # Both values near TTC 7 -> no unique protocol match -> never pick the first.
    trial = load(tor_values=(2.9, 3.1))
    res = resolve_tor(trial)
    assert res.state == "MULTI_UNRESOLVED"
    assert res.selected is None
    ev = observation_events(trial)
    assert ev.t_tor is None and ev.window_tor_to_handback is None
    assert "MULTI_TOR_UNRESOLVED" in audit_trial(trial)["qa_errors"]


def test_multi_tor_with_no_protocol_match_stays_unresolved():
    res = resolve_tor(load(tor_values=(5.0, 6.0)))
    assert res.state == "MULTI_UNRESOLVED" and res.selected is None


# --- clocks ------------------------------------------------------------------


def test_event_clock_lag_within_expected_range():
    checks = event_clock_checks(load())
    assert {c.event for c in checks} == {"TOR", "MANUAL_START", "MANUAL_STOP", "LANE_CHANGE"}
    assert all(c.ok for c in checks)
    assert all(0.09 <= c.lag_s <= 0.16 for c in checks)


def test_known_lane_change_clock_exception_is_surfaced():
    # Channel appears 0.95 s before its stated value (as in density_10_nback_1_id_8).
    trial = load(lane_change=7.0, lane_change_first_row_time=6.05)
    lc = validate_lane_change(trial, lane_transitions(trial))
    assert lc.state == "CLOCK_EXCEPTION"
    assert lc.offset_s == pytest.approx(-0.95)
    row = audit_trial(trial)
    assert "EVENT_CLOCK_EXCEPTION_LANE_CHANGE" in row["qa_warnings"]
    assert "LANE_CHANGE_CLOCK_EXCEPTION" in row["qa_warnings"]


def test_lane_change_validated_against_lane_id():
    trial = load()
    lc = validate_lane_change(trial, lane_transitions(trial))
    assert lc.state == "VALIDATED"
    assert (lc.matched.lane_from, lc.matched.lane_to) == (2, 3)


def test_lane_change_without_matching_transition():
    trial = load(lanes=((0.0, 2, 15),))
    assert validate_lane_change(trial, lane_transitions(trial)).state == "NO_MATCHING_TRANSITION"


def test_absent_lane_change_column():
    trial = load(header=HEADER_VARIANTS["NO_LANE_CHANGE_44"])
    assert validate_lane_change(trial, lane_transitions(trial)).state == "ABSENT_COLUMN"


# --- lane numbering ------------------------------------------------------------


def test_lane_numbering_varies_and_road_renumbering_is_not_a_lane_change():
    trial = load(lanes=((0.0, 2, 15), (1.0, 6, 24), (6.05, 5, 24)))
    tr = lane_transitions(trial)
    assert [(x.lane_from, x.lane_to, x.same_road) for x in tr] == [(2, 6, False), (6, 5, True)]
    lc = validate_lane_change(trial, tr)
    assert lc.state == "VALIDATED" and (lc.matched.lane_from, lc.matched.lane_to) == (6, 5)


def test_seven_to_six_transition_supported():
    trial = load(lanes=((0.0, 7, 23), (6.05, 6, 23)))
    lc = validate_lane_change(trial, lane_transitions(trial))
    assert lc.state == "VALIDATED" and (lc.matched.lane_from, lc.matched.lane_to) == (7, 6)


# --- adjacent-lane zeros --------------------------------------------------------


def test_adjacent_lane_zero_values_are_not_interpreted():
    values = np.array([np.nan, 0.0, 12.5, 0.0])
    assert list(classify_adjacent_lane_values(values)) == [
        "missing", "zero_semantics_unresolved", "value", "zero_semantics_unresolved"]
    trial = load()
    raw = trial.telemetry["distance_to_following"].to_numpy()
    assert (raw[1:] == 0.0).all()  # zeros preserved as recorded
    row = audit_trial(trial)
    assert row["distance_to_following__n_zero_semantics_unresolved"] == 399
    assert row["distance_to_following__n_value"] == 0


# --- observation window / authority ---------------------------------------------


def test_observation_events_keep_authority_and_human_input_unresolved():
    ev = observation_events(load())
    assert ev.manual_start_authority_semantics == UNRESOLVED
    assert ev.first_validated_human_input is None
    assert "unresolved" in ev.first_validated_human_input_reason
    assert ev.t_manual_start == 4.0
    assert ev.window_tor_to_handback == (3.0, 12.0)
    assert ev.window_manual_start_to_handback == (4.0, 12.0)


def test_implausibly_fast_first_input_is_flagged():
    trial = load(cell_overrides={(int(3.1 / DT), "[00].VehicleUpdate-brake"): "40.0"})
    ev = observation_events(trial)
    assert ev.first_input_candidate_implausibly_fast is True
    assert "FIRST_INPUT_CANDIDATE_UNDER_0P3S" in audit_trial(trial)["qa_warnings"]


def test_multiple_manual_stop_values_are_kept_and_flagged():
    trial = load(manual_stops=(12.0, 15.0))
    hb = resolve_handback(trial)
    assert hb.raw_values == [12.0, 15.0]
    assert hb.state == "MULTI_FIRST_TAKEN_AS_END_OF_FIRST_MANUAL_EPISODE"
    assert hb.first_manual_episode_end == 12.0
    assert "HANDBACK_MULTI" in audit_trial(trial)["qa_warnings"]


def test_brake_semantics_reported_as_unresolved():
    row = audit_trial(load())
    assert row["brake_semantics"] == UNRESOLVED


# --- integration on the real archive ------------------------------------------------

ARCHIVE = "data/external/d003/tu_delft_takeover.zip"


@pytest.fixture(scope="module")
def real_audit():
    if not os.path.exists(ARCHIVE):
        pytest.skip(f"D003 archive not present at {ARCHIVE}")
    import pandas as pd
    from src.data.d003_ingest import D003Archive

    archive = D003Archive(ARCHIVE)
    rows = [audit_trial(archive.load(n)) for n in archive.trial_names()]
    archive.close()
    return pd.DataFrame(rows)


def test_real_archive_header_variants(real_audit):
    assert len(real_audit) == 513
    assert real_audit.header_variant.value_counts().to_dict() == {
        "FULL_45": 484, "NO_TOR_44": 15, "NO_LANE_CHANGE_44": 14}


def test_real_archive_tor_states(real_audit):
    assert real_audit.tor_state.value_counts().to_dict() == {
        "SINGLE": 472, "MULTI_RESOLVED_BY_PROTOCOL_TTC": 20,
        "MISSING_TOR_COLUMN": 15, "MULTI_UNRESOLVED": 6}
    multi = real_audit[real_audit.tor_state.str.startswith("MULTI")]
    assert Counter(multi.density.astype(str) + "/" + multi.nback.astype(str)) == Counter({"20/1": 25, "20/2": 1})


def test_real_archive_footers_and_clock(real_audit):
    assert int(real_audit.has_export_footer.sum()) == 42
    assert (real_audit[real_audit.has_export_footer].qa_info.str.contains("FOOTER_EVENTS_CONSISTENT")).all()
    assert real_audit.lane_gap_reltime_max_abs_err_s.max() < 1e-6
    assert (real_audit.lane_gap_null_tokens == 1).all()
    assert (real_audit.dt_max_s < 0.051).all()


def test_real_archive_lane_change_validation(real_audit):
    assert real_audit.lane_change_state.value_counts().to_dict() == {
        "VALIDATED": 498, "ABSENT_COLUMN": 14, "CLOCK_EXCEPTION": 1}
    exc = real_audit[real_audit.lane_change_state == "CLOCK_EXCEPTION"]
    assert exc.trial_id.tolist() == ["density_10_nback_1_id_8"]
    assert set(real_audit.lane_change_transition.dropna()) == {"2->3", "6->5", "7->6"}


# --- R1 validation helpers --------------------------------------------------------


def test_owner_window_metrics_require_validated_lane_change_and_tor():
    from src.experiments.r1_ingestion_validation import owner_window_metrics

    ok = owner_window_metrics(load())
    assert ok["window_status"] == "OK"
    assert ok["t_button_s"] == pytest.approx(1.0)
    assert ok["min_ttc_s"] == pytest.approx(10.0 - 6.0, abs=0.06)  # TTC = 10 - t at lane change t=6
    assert ok["brake_semantics"] == UNRESOLVED

    no_lc = owner_window_metrics(load(header=HEADER_VARIANTS["NO_LANE_CHANGE_44"]))
    assert no_lc["window_status"].startswith("NO_VALIDATED_LANE_CHANGE") and no_lc["min_ttc_s"] is None

    no_tor = owner_window_metrics(load(tor_values=(2.9, 3.1)))
    assert no_tor["window_status"].startswith("NO_TOR_ANCHOR") and no_tor["t_button_s"] is None


def test_min_ttc_excludes_samples_outside_documented_formula_domain():
    from src.experiments.r1_ingestion_validation import owner_window_metrics

    # A stopped vehicle produces a huge negative TTC sample; it must not become the minimum.
    row = int(5.0 / DT)
    trial = load(cell_overrides={(row, TTC_COLUMN): "-238247312.0",
                                 (row, "[00].VehicleUpdate-speed.001"): "-0.003"})
    out = owner_window_metrics(trial)
    assert out["min_ttc_s"] > 0
    assert out["n_ttc_samples_excluded"] == 1
    assert out["vehicle_stopped_in_window"] is True
