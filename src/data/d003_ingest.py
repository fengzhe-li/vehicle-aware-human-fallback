"""Strict, auditable ingestion of D003 simulator CSVs (Phase R1).

This module replaces the legacy loader (`src/data/d003_loader.py`) for all new
work. Unlike the legacy loader it:

- reads cells as text and never coerces unknown tokens silently;
- recognises the three known header variants and fails on any other;
- parses the composite ``"<laneGap value>,<relative time>"`` cell into two
  components and keeps the raw cell;
- detects the trailing export-channel footer row and cross-checks it instead of
  treating it as telemetry;
- never selects a TOR silently: every distinct TOR value is kept, and a value is
  selected only by the documented protocol rule (TOR at TTC ~ 7 s), otherwise
  the anchor is marked unresolved;
- validates event clocks and lane-change timing per trial and reports
  exceptions as QA notices.

Semantics that are not documented officially are labelled as such. In
particular, the physical meaning of the first ``laneGap`` component, the brake
channel, the zero values of the adjacent-lane distance channels, and whether
``Time_Manual_Start`` is the authority transfer all remain UNRESOLVED. See
``research/data_matrix/D003_KNOWN_BLOCKERS.md`` and ``docs/OBSERVATION_LAYER.md``.
"""

from __future__ import annotations

import csv
import io
import math
import os
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.data.d003_loader import RAW_TO_CANONICAL_COLUMNS, TrialMeta, parse_trial_filename

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

TIME_COLUMN = "time"
LANE_GAP_COMPOSITE_COLUMN = "[00].VehicleUpdate-roadInfo-laneGap.0,time"
TOR_COLUMN = "[72 (Time/Time_Takeover_Request)].ExportChannel-val"
MANUAL_START_COLUMN = "[73 (Time/Time_Manual_Start)].ExportChannel-val"
MANUAL_STOP_COLUMN = "[74 (Time/Time_Manual_Stop)].ExportChannel-val"
TTC_COLUMN = "[77 (Time/Time_TTC)].ExportChannel-val"
LANE_CHANGE_COLUMN = "[78 (Time/Time_Lane_Change)].ExportChannel-val"

VEHICLE_COLUMNS: Tuple[str, ...] = (
    TIME_COLUMN,
    "[00].VehicleUpdate-pos.001",
    "[00].VehicleUpdate-pos.002",
    "[00].VehicleUpdate-pos.003",
    "[00].VehicleUpdate-pos.004",
    "[00].VehicleUpdate-pos.005",
    "[00].VehicleUpdate-pos.006",
    "[00].VehicleUpdate-COGPos.001",
    "[00].VehicleUpdate-COGPos.002",
    "[00].VehicleUpdate-COGPos.003",
    "[00].VehicleUpdate-speed.001",
    "[00].VehicleUpdate-speed.002",
    "[00].VehicleUpdate-speed.003",
    "[00].VehicleUpdate-speed.004",
    "[00].VehicleUpdate-speed.005",
    "[00].VehicleUpdate-speed.006",
    "[00].VehicleUpdate-accel.001",
    "[00].VehicleUpdate-accel.002",
    "[00].VehicleUpdate-accel.003",
    "[00].VehicleUpdate-accel.004",
    "[00].VehicleUpdate-accel.005",
    "[00].VehicleUpdate-accel.006",
    "[00].VehicleUpdate-state",
    "[00].VehicleUpdate-lights",
    "[00].VehicleUpdate-steeringWheelAngle",
    "[00].VehicleUpdate-steeringWheelSpeed",
    "[00].VehicleUpdate-steeringTorq",
    "[00].VehicleUpdate-accelerator",
    "[00].VehicleUpdate-brake",
    "[00].VehicleUpdate-indicators",
    "[00].VehicleUpdate-roadInfo-roadId.0",
    "[00].VehicleUpdate-roadInfo-roadAbscissa.0",
    "[00].VehicleUpdate-roadInfo-roadGap.0",
    "[00].VehicleUpdate-roadInfo-roadAngle.0",
    "[00].VehicleUpdate-roadInfo-laneId.0",
)

EXPORT_COLUMNS: Tuple[str, ...] = (
    TOR_COLUMN,
    MANUAL_START_COLUMN,
    MANUAL_STOP_COLUMN,
    TTC_COLUMN,
    LANE_CHANGE_COLUMN,
    "[82 (Distance/Distance_to_Following_Vehicle)].ExportChannel-val",
    "[83 (Distance/Distance_to_Leading_Vehicle_Next_Lane)].ExportChannel-val",
    "[84 (Distance/Distance_to_Following_Vehicle_Next_Lane)].ExportChannel-val",
    "[85 (Distance/Distance_to_Construction)].ExportChannel-val",
)

FULL_HEADER: Tuple[str, ...] = VEHICLE_COLUMNS + (LANE_GAP_COMPOSITE_COLUMN,) + EXPORT_COLUMNS

# The three header variants observed in all 513 public trial files (Phase R1 audit).
HEADER_VARIANTS: Dict[str, Tuple[str, ...]] = {
    "FULL_45": FULL_HEADER,
    "NO_TOR_44": tuple(c for c in FULL_HEADER if c != TOR_COLUMN),
    "NO_LANE_CHANGE_44": tuple(c for c in FULL_HEADER if c != LANE_CHANGE_COLUMN),
}

# Canonical names. Legacy names are reused where the legacy loader defined them;
# columns the legacy loader left unmapped get neutral names (semantics undocumented).
_EXTRA_CANONICAL = {
    "[00].VehicleUpdate-speed.004": "speed_004_undocumented",
    "[00].VehicleUpdate-speed.005": "speed_005_undocumented",
    "[00].VehicleUpdate-speed.006": "speed_006_undocumented",
    "[00].VehicleUpdate-accel.004": "accel_004_undocumented",
    "[00].VehicleUpdate-accel.005": "accel_005_undocumented",
    "[00].VehicleUpdate-accel.006": "accel_006_undocumented",
}
CANONICAL_NAMES: Dict[str, str] = {}
for _col in VEHICLE_COLUMNS[1:] + EXPORT_COLUMNS:
    if _col in RAW_TO_CANONICAL_COLUMNS:
        CANONICAL_NAMES[_col] = RAW_TO_CANONICAL_COLUMNS[_col]
    else:
        CANONICAL_NAMES[_col] = _EXTRA_CANONICAL[_col]

# ---------------------------------------------------------------------------
# Documented rules and thresholds
# ---------------------------------------------------------------------------

# Owners' protocol (Liang, Calvert & van Lint, arXiv 2507.22252): "a takeover
# request is triggered seven seconds before the ego vehicle would collide".
TOR_PROTOCOL_TTC_S = 7.0
TOR_PROTOCOL_TTC_TOLERANCE_S = 0.25
TTC_LOOKUP_WINDOW_S = 0.2

# Event channels become non-null about 2 samples after their stated value.
EVENT_LAG_MIN_S = 0.0
EVENT_LAG_MAX_S = 0.2

LANE_GAP_RELTIME_TOLERANCE_S = 1e-4
LANE_CHANGE_MATCH_TOLERANCE_S = 0.15
# Inferred check only: a same-road lane transition is consistent with a
# lane-width jump of the first laneGap component (observed median ~3.4 m).
LANE_GAP_JUMP_RANGE_M = (3.0, 4.0)

BRAKE_CANDIDATE_THRESHOLD = 15.0  # channel units (dictionary: "brake force, N")
STEER_CANDIDATE_THRESHOLD_RAD = 0.05
BASELINE_WINDOW_S = (4.0, 0.2)  # [TOR - 4.0, TOR - 0.2]
IMPLAUSIBLY_FAST_INPUT_S = 0.3
START_TRANSIENT_S = 1.0

UNRESOLVED = "UNRESOLVED"


class D003SchemaError(ValueError):
    """Raised for unknown header variants or malformed rows."""


class D003ParseError(ValueError):
    """Raised for cell values that are neither numeric, empty nor a known token."""


@dataclass(frozen=True)
class QANotice:
    code: str
    severity: str  # "INFO", "WARNING", "ERROR"
    detail: str = ""


@dataclass
class D003Trial:
    meta: TrialMeta
    header_variant: str
    header: Tuple[str, ...]
    telemetry: pd.DataFrame
    footer: Optional[Dict[str, object]]
    null_token_counts: Dict[str, int]
    notices: List[QANotice] = field(default_factory=list)

    def has(self, column: str) -> bool:
        return column in self.header

    def column(self, raw_name: str) -> np.ndarray:
        return self.telemetry[CANONICAL_NAMES[raw_name]].to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


class D003Archive:
    """Read-only access to D003 simulator CSVs in a zip archive or directory."""

    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"D003 source not found: {path}")
        self.path = path
        self._zip = zipfile.ZipFile(path) if zipfile.is_zipfile(path) else None

    def trial_names(self) -> List[str]:
        if self._zip is not None:
            names = self._zip.namelist()
        else:
            names = [
                os.path.relpath(os.path.join(root, f), self.path)
                for root, _, files in os.walk(self.path)
                for f in files
            ]
        return sorted(
            n for n in names
            if n.endswith("_simulator_data.csv") and "__MACOSX" not in n
            and not os.path.basename(n).startswith("._")
        )

    def read_text(self, name: str) -> str:
        if self._zip is not None:
            return self._zip.read(name).decode("utf-8")
        with open(os.path.join(self.path, name), encoding="utf-8") as fh:
            return fh.read()

    def load(self, name: str) -> "D003Trial":
        return parse_trial_text(self.read_text(name), name)

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()


def identify_header_variant(header: Sequence[str]) -> str:
    header = tuple(header)
    for name, variant in HEADER_VARIANTS.items():
        if header == variant:
            return name
    raise D003SchemaError(f"Unknown D003 header variant ({len(header)} columns)")


def _parse_cell(value: str, column: str, row: int, null_counts: Dict[str, int]) -> float:
    value = value.strip()
    if value == "":
        return math.nan
    if value == "null":
        null_counts[column] = null_counts.get(column, 0) + 1
        return math.nan
    try:
        return float(value)
    except ValueError as exc:
        raise D003ParseError(f"Unparseable value {value!r} in column {column!r}, row {row}") from exc


def _parse_footer(row: List[str], export_cols: Sequence[str]) -> Dict[str, object]:
    values = [v for v in row if v.strip() != ""]
    k = len(export_cols)
    if len(values) != 2 * k:
        raise D003SchemaError(
            f"Trailing row with empty time has {len(values)} values; expected {2 * k} (export footer)"
        )
    first_block = [float(v) for v in values[:k]]
    export_values = [float(v) for v in values[k:]]
    return {
        "raw_values": values,
        "unknown_block": dict(zip(export_cols, first_block)),  # semantics undocumented
        "export_values": dict(zip(export_cols, export_values)),
    }


def parse_trial_text(text: str, name: str) -> D003Trial:
    """Parse one simulator CSV strictly. Raises on unknown schema or tokens."""
    meta = parse_trial_filename(name)
    if meta is None:
        raise D003SchemaError(f"Unrecognised trial filename: {name}")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise D003SchemaError(f"Empty file: {name}")
    header = tuple(rows[0])
    variant = identify_header_variant(header)
    body = rows[1:]
    notices: List[QANotice] = []

    footer = None
    if body and body[-1] and body[-1][0].strip() == "":
        export_cols = [c for c in header if c in EXPORT_COLUMNS]
        footer = _parse_footer(body[-1], export_cols)
        body = body[:-1]
    for i, r in enumerate(body):
        if len(r) != len(header):
            raise D003SchemaError(f"Row {i + 1} has {len(r)} cells; header has {len(header)}")
        if r[0].strip() == "":
            raise D003SchemaError(f"Row {i + 1} has an empty timestamp before the final row")

    null_counts: Dict[str, int] = {}
    idx = {c: j for j, c in enumerate(header)}
    data: Dict[str, List[float]] = {}
    for col in header:
        if col == LANE_GAP_COMPOSITE_COLUMN:
            continue
        j = idx[col]
        data[col] = [_parse_cell(r[j], col, i + 1, null_counts) for i, r in enumerate(body)]

    lg_raw, lg_c1, lg_c2 = [], [], []
    j = idx[LANE_GAP_COMPOSITE_COLUMN]
    for i, r in enumerate(body):
        cell = r[j]
        lg_raw.append(cell)
        if cell.count(",") != 1:
            raise D003ParseError(f"laneGap cell {cell!r} in row {i + 1} is not a '<value>,<time>' pair")
        a, b = cell.split(",")
        lg_c1.append(_parse_cell(a, "laneGap.component1", i + 1, null_counts))
        lg_c2.append(_parse_cell(b, "laneGap.component2", i + 1, null_counts))

    time_epoch = np.asarray(data[TIME_COLUMN], dtype=float)
    frame = {"time_epoch": time_epoch, "t_rel": time_epoch - time_epoch[0]}
    for col in header:
        if col in (TIME_COLUMN, LANE_GAP_COMPOSITE_COLUMN):
            continue
        frame[CANONICAL_NAMES[col]] = np.asarray(data[col], dtype=float)
    frame["lane_gap_raw"] = lg_raw
    frame["lane_gap_component1"] = np.asarray(lg_c1, dtype=float)  # meaning INFERRED only
    frame["lane_gap_reltime"] = np.asarray(lg_c2, dtype=float)
    telemetry = pd.DataFrame(frame)

    trial = D003Trial(meta, variant, header, telemetry, footer, null_counts, notices)
    if footer is not None:
        notices.append(QANotice("TRAILING_EXPORT_FOOTER", "INFO",
                                "final row has empty time and holds export-channel values; excluded from telemetry"))
    if variant != "FULL_45":
        notices.append(QANotice(f"HEADER_VARIANT_{variant}", "INFO", "column absent from file header"))
    return trial


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _distinct_in_order(values: np.ndarray) -> List[Tuple[float, int]]:
    """Distinct non-NaN values with the row index of their first occurrence."""
    out: List[Tuple[float, int]] = []
    seen = set()
    for i, v in enumerate(values):
        if not np.isnan(v) and v not in seen:
            seen.add(v)
            out.append((float(v), i))
    return out


@dataclass
class EventClockCheck:
    event: str
    value: float
    first_row_t_rel: float
    lag_s: float
    ok: bool


def check_footer(trial: D003Trial) -> List[QANotice]:
    """The footer's export values must equal the latest body value of each event channel."""
    if trial.footer is None:
        return []
    bad = []
    for col, fv in trial.footer["export_values"].items():
        if col in (TTC_COLUMN,) or "Time_" not in col:
            continue
        vals = [v for v, _ in _distinct_in_order(trial.column(col))]
        if not vals or abs(fv - vals[-1]) > 1e-6:
            bad.append(col)
    if bad:
        return [QANotice("FOOTER_EVENT_MISMATCH", "ERROR", "; ".join(bad))]
    return [QANotice("FOOTER_EVENTS_CONSISTENT", "INFO", "footer event values equal latest body values")]


def check_lane_gap_clock(trial: D003Trial) -> Tuple[float, List[QANotice]]:
    tel = trial.telemetry
    err = np.nanmax(np.abs(tel["lane_gap_reltime"].to_numpy() - tel["t_rel"].to_numpy()))
    if not err <= LANE_GAP_RELTIME_TOLERANCE_S:
        return err, [QANotice("LANE_GAP_RELTIME_MISMATCH", "ERROR", f"max |component2 - t_rel| = {err:.3g} s")]
    return err, []


def event_clock_checks(trial: D003Trial) -> List[EventClockCheck]:
    """Lag between each event value and the first row carrying it (expected ~0.05-0.15 s)."""
    t = trial.telemetry["t_rel"].to_numpy()
    checks = []
    for col, label in ((TOR_COLUMN, "TOR"), (MANUAL_START_COLUMN, "MANUAL_START"),
                       (MANUAL_STOP_COLUMN, "MANUAL_STOP"), (LANE_CHANGE_COLUMN, "LANE_CHANGE")):
        if not trial.has(col):
            continue
        for value, row in _distinct_in_order(trial.column(col)):
            lag = float(t[row] - value)
            checks.append(EventClockCheck(label, value, float(t[row]), lag,
                                          EVENT_LAG_MIN_S <= lag <= EVENT_LAG_MAX_S))
    return checks


@dataclass
class TorResolution:
    state: str  # MISSING_TOR_COLUMN | MISSING_TOR_VALUE | SINGLE | MULTI_RESOLVED_BY_PROTOCOL_TTC | MULTI_UNRESOLVED
    raw_values: List[float]
    ttc_at_values: List[float]
    selected: Optional[float]
    rule: str
    protocol_consistent: Optional[bool]


def _ttc_at(trial: D003Trial, value: float) -> float:
    t = trial.telemetry["t_rel"].to_numpy()
    ttc = trial.column(TTC_COLUMN)
    mask = (t >= value) & (t <= value + TTC_LOOKUP_WINDOW_S) & ~np.isnan(ttc)
    return float(ttc[mask][0]) if mask.any() else math.nan


def resolve_tor(trial: D003Trial) -> TorResolution:
    """Never silently picks a TOR. Selection only by the documented TTC ~ 7 s protocol."""
    rule = f"select the unique TOR value with TTC within {TOR_PROTOCOL_TTC_S}±{TOR_PROTOCOL_TTC_TOLERANCE_S} s (owner protocol)"
    if not trial.has(TOR_COLUMN):
        return TorResolution("MISSING_TOR_COLUMN", [], [], None, "no TOR column in file", None)
    values = [v for v, _ in _distinct_in_order(trial.column(TOR_COLUMN))]
    if not values:
        return TorResolution("MISSING_TOR_VALUE", [], [], None, "TOR column empty", None)
    ttcs = [_ttc_at(trial, v) for v in values]
    ok = [not np.isnan(x) and abs(x - TOR_PROTOCOL_TTC_S) <= TOR_PROTOCOL_TTC_TOLERANCE_S for x in ttcs]
    if len(values) == 1:
        return TorResolution("SINGLE", values, ttcs, values[0], "single TOR value", ok[0])
    if sum(ok) == 1:
        sel = values[ok.index(True)]
        return TorResolution("MULTI_RESOLVED_BY_PROTOCOL_TTC", values, ttcs, sel, rule, True)
    return TorResolution("MULTI_UNRESOLVED", values, ttcs, None, rule + f"; {sum(ok)} candidates qualified", None)


@dataclass
class LaneTransition:
    t_rel: float
    lane_from: int
    lane_to: int
    road_from: float
    road_to: float
    same_road: bool


def lane_transitions(trial: D003Trial) -> List[LaneTransition]:
    """Every lane_id change. Changes across a road_id boundary are renumbering, not lane changes."""
    t = trial.telemetry["t_rel"].to_numpy()
    lane = trial.column("[00].VehicleUpdate-roadInfo-laneId.0")
    road = trial.column("[00].VehicleUpdate-roadInfo-roadId.0")
    out = []
    for i in range(1, len(lane)):
        if np.isnan(lane[i]) or np.isnan(lane[i - 1]) or lane[i] == lane[i - 1]:
            continue
        out.append(LaneTransition(float(t[i]), int(lane[i - 1]), int(lane[i]),
                                  float(road[i - 1]), float(road[i]), bool(road[i] == road[i - 1])))
    return out


@dataclass
class LaneChangeValidation:
    state: str  # ABSENT_COLUMN | NO_VALUE | VALIDATED | CLOCK_EXCEPTION | NO_MATCHING_TRANSITION | MULTI_VALUE
    value: Optional[float]
    matched: Optional[LaneTransition]
    offset_s: Optional[float]


def validate_lane_change(trial: D003Trial, transitions: List[LaneTransition]) -> LaneChangeValidation:
    if not trial.has(LANE_CHANGE_COLUMN):
        return LaneChangeValidation("ABSENT_COLUMN", None, None, None)
    values = [v for v, _ in _distinct_in_order(trial.column(LANE_CHANGE_COLUMN))]
    if not values:
        return LaneChangeValidation("NO_VALUE", None, None, None)
    if len(values) > 1:
        return LaneChangeValidation("MULTI_VALUE", None, None, None)
    value = values[0]
    same = [tr for tr in transitions if tr.same_road]
    if not same:
        return LaneChangeValidation("NO_MATCHING_TRANSITION", value, None, None)
    best = min(same, key=lambda tr: abs(tr.t_rel - value))
    offset = best.t_rel - value
    lag_ok = all(c.ok for c in event_clock_checks(trial) if c.event == "LANE_CHANGE")
    if not lag_ok:
        return LaneChangeValidation("CLOCK_EXCEPTION", value, best, offset)
    if abs(offset) > LANE_CHANGE_MATCH_TOLERANCE_S:
        return LaneChangeValidation("NO_MATCHING_TRANSITION", value, best, offset)
    return LaneChangeValidation("VALIDATED", value, best, offset)


def lane_gap_jump_check(trial: D003Trial, transitions: List[LaneTransition]) -> Dict[str, int]:
    """Inferred-semantics check: |jump| of component 1 at same-road lane transitions."""
    t = trial.telemetry["t_rel"].to_numpy()
    c1 = trial.telemetry["lane_gap_component1"].to_numpy()
    n_in = n_out = 0
    for tr in transitions:
        if not tr.same_road:
            continue
        i = int(np.searchsorted(t, tr.t_rel))
        if i < 1 or np.isnan(c1[i]) or np.isnan(c1[i - 1]):
            continue
        jump = abs(c1[i] - c1[i - 1])
        if LANE_GAP_JUMP_RANGE_M[0] <= jump <= LANE_GAP_JUMP_RANGE_M[1]:
            n_in += 1
        else:
            n_out += 1
    return {"same_road_transitions_jump_in_range": n_in, "same_road_transitions_jump_out_of_range": n_out}


@dataclass
class HandbackResolution:
    state: str  # SINGLE | MULTI_FIRST_TAKEN_AS_END_OF_FIRST_MANUAL_EPISODE | MISSING
    raw_values: List[float]
    first_manual_episode_end: Optional[float]


def resolve_handback(trial: D003Trial) -> HandbackResolution:
    """Time_Manual_Stop = switch back to automated mode (data dictionary).

    With several values, the first value after Manual_Start ends the first manual
    episode; later values are kept but their meaning is unresolved.
    """
    values = [v for v, _ in _distinct_in_order(trial.column(MANUAL_STOP_COLUMN))]
    if not values:
        return HandbackResolution("MISSING", [], None)
    starts = [v for v, _ in _distinct_in_order(trial.column(MANUAL_START_COLUMN))]
    after = sorted(v for v in values if not starts or v >= starts[0])
    first = after[0] if after else None
    state = "SINGLE" if len(values) == 1 else "MULTI_FIRST_TAKEN_AS_END_OF_FIRST_MANUAL_EPISODE"
    return HandbackResolution(state, values, first)


ADJACENT_LANE_COLUMNS = (
    "[82 (Distance/Distance_to_Following_Vehicle)].ExportChannel-val",
    "[83 (Distance/Distance_to_Leading_Vehicle_Next_Lane)].ExportChannel-val",
    "[84 (Distance/Distance_to_Following_Vehicle_Next_Lane)].ExportChannel-val",
)


def classify_adjacent_lane_values(values: np.ndarray) -> np.ndarray:
    """Per-sample class: 'missing' (NaN), 'zero_semantics_unresolved' (== 0), 'value'.

    A zero may be a measured zero distance or a no-vehicle sentinel; the data
    dictionary does not say, so zeros are never converted to either.
    """
    out = np.full(values.shape, "value", dtype=object)
    out[np.isnan(values)] = "missing"
    out[values == 0] = "zero_semantics_unresolved"
    return out


def adjacent_lane_profile(trial: D003Trial) -> Dict[str, Dict[str, int]]:
    profile = {}
    for col in ADJACENT_LANE_COLUMNS:
        cls = classify_adjacent_lane_values(trial.column(col))
        profile[CANONICAL_NAMES[col]] = {
            "n_value": int((cls == "value").sum()),
            "n_zero_semantics_unresolved": int((cls == "zero_semantics_unresolved").sum()),
            "n_missing": int((cls == "missing").sum()),
        }
    return profile


@dataclass
class ObservationEvents:
    """Event and window semantics for later analysis. No stabilisation metric is defined."""

    tor: TorResolution
    t_tor: Optional[float]
    brake_input_candidate: Optional[float]
    steer_input_candidate: Optional[float]
    first_input_candidate: Optional[float]
    first_input_candidate_implausibly_fast: Optional[bool]
    first_validated_human_input: Optional[float]
    first_validated_human_input_reason: str
    t_manual_start: Optional[float]
    manual_start_authority_semantics: str
    lane_change: LaneChangeValidation
    handback: HandbackResolution
    window_tor_to_handback: Optional[Tuple[float, float]]
    window_manual_start_to_handback: Optional[Tuple[float, float]]


def observation_events(trial: D003Trial) -> ObservationEvents:
    tor = resolve_tor(trial)
    transitions = lane_transitions(trial)
    lc = validate_lane_change(trial, transitions)
    hb = resolve_handback(trial)
    starts = [v for v, _ in _distinct_in_order(trial.column(MANUAL_START_COLUMN))]
    t_ms = starts[0] if len(starts) == 1 else None
    t = trial.telemetry["t_rel"].to_numpy()

    brake_c = steer_c = first_c = None
    fast = None
    if tor.selected is not None:
        t0 = tor.selected
        base = (t >= t0 - BASELINE_WINDOW_S[0]) & (t <= t0 - BASELINE_WINDOW_S[1])
        post = t >= t0
        brake = trial.column("[00].VehicleUpdate-brake")
        steer = trial.column("[00].VehicleUpdate-steeringWheelAngle")
        b = np.where(post & (brake > BRAKE_CANDIDATE_THRESHOLD))[0]
        brake_c = float(t[b[0]]) if len(b) else None
        if base.any():
            s = np.where(post & (np.abs(steer - np.nanmean(steer[base])) > STEER_CANDIDATE_THRESHOLD_RAD))[0]
            steer_c = float(t[s[0]]) if len(s) else None
        cands = [x for x in (brake_c, steer_c) if x is not None]
        first_c = min(cands) if cands else None
        fast = None if first_c is None else (first_c - t0) < IMPLAUSIBLY_FAST_INPUT_S

    end = hb.first_manual_episode_end
    return ObservationEvents(
        tor=tor,
        t_tor=tor.selected,
        brake_input_candidate=brake_c,
        steer_input_candidate=steer_c,
        first_input_candidate=first_c,
        first_input_candidate_implausibly_fast=fast,
        first_validated_human_input=None,
        first_validated_human_input_reason=(
            "not validatable: brake-channel source (driver vs automation) and steering source are unresolved"
        ),
        t_manual_start=t_ms,
        manual_start_authority_semantics=UNRESOLVED,
        lane_change=lc,
        handback=hb,
        window_tor_to_handback=(tor.selected, end) if tor.selected is not None and end is not None else None,
        window_manual_start_to_handback=(t_ms, end) if t_ms is not None and end is not None else None,
    )


def brake_channel_facts(trial: D003Trial, t_tor: Optional[float], t_handback: Optional[float]) -> Dict[str, object]:
    """Observable facts only. The channel's meaning stays UNRESOLVED."""
    t = trial.telemetry["t_rel"].to_numpy()
    brake = trial.column("[00].VehicleUpdate-brake")
    ax = trial.column("[00].VehicleUpdate-accel.001")
    facts: Dict[str, object] = {
        "brake_semantics": UNRESOLVED,
        "brake_dictionary_description": "car_brake: brake force, N",
        "brake_max_start_transient": float(np.nanmax(brake[t <= START_TRANSIENT_S])),
    }
    if t_tor is not None:
        pre = (t > START_TRANSIENT_S) & (t < t_tor)
        facts["brake_n_above_threshold_pre_tor"] = int((brake[pre] > BRAKE_CANDIDATE_THRESHOLD).sum())
        if t_handback is not None:
            win = (t >= t_tor) & (t < t_handback) & ~np.isnan(brake) & ~np.isnan(ax)
            if win.sum() > 2 and np.nanstd(brake[win]) > 0 and np.nanstd(ax[win]) > 0:
                facts["brake_vs_longitudinal_accel_corr_manual_window"] = float(
                    pd.Series(brake[win]).corr(pd.Series(ax[win]), method="spearman"))
    if t_handback is not None:
        facts["brake_n_above_threshold_after_handback"] = int(
            (brake[t >= t_handback] > BRAKE_CANDIDATE_THRESHOLD).sum())
    return facts


def audit_trial(trial: D003Trial) -> Dict[str, object]:
    """One flat QA row per trial. Exceptions are surfaced, never silently accepted."""
    notices = list(trial.notices)
    notices += check_footer(trial)
    lg_err, lg_notices = check_lane_gap_clock(trial)
    notices += lg_notices
    clocks = event_clock_checks(trial)
    for c in clocks:
        if not c.ok:
            notices.append(QANotice(f"EVENT_CLOCK_EXCEPTION_{c.event}", "WARNING",
                                    f"value {c.value:.3f} s, first row at {c.first_row_t_rel:.3f} s (lag {c.lag_s:+.3f} s)"))
    ev = observation_events(trial)
    transitions = lane_transitions(trial)
    jumps = lane_gap_jump_check(trial, transitions)
    tor = ev.tor
    if tor.state == "MULTI_RESOLVED_BY_PROTOCOL_TTC":
        notices.append(QANotice("MULTI_TOR_RESOLVED_BY_PROTOCOL", "WARNING", str(tor.raw_values)))
    elif tor.state == "MULTI_UNRESOLVED":
        notices.append(QANotice("MULTI_TOR_UNRESOLVED", "ERROR", str(tor.raw_values)))
    elif tor.state.startswith("MISSING"):
        notices.append(QANotice(tor.state, "WARNING", "TOR-anchored analysis not possible"))
    elif tor.state == "SINGLE" and not tor.protocol_consistent:
        notices.append(QANotice("TOR_TTC_OFF_PROTOCOL", "WARNING", f"TTC at TOR = {tor.ttc_at_values[0]:.3f} s"))
    if ev.lane_change.state not in ("VALIDATED", "ABSENT_COLUMN"):
        notices.append(QANotice(f"LANE_CHANGE_{ev.lane_change.state}", "WARNING",
                                f"value={ev.lane_change.value}, offset={ev.lane_change.offset_s}"))
    if ev.handback.state != "SINGLE":
        notices.append(QANotice(f"HANDBACK_{ev.handback.state}", "WARNING", str(ev.handback.raw_values)))
    if jumps["same_road_transitions_jump_out_of_range"]:
        notices.append(QANotice("LANE_GAP_JUMP_OUT_OF_RANGE", "INFO", str(jumps)))
    if ev.first_input_candidate_implausibly_fast:
        notices.append(QANotice("FIRST_INPUT_CANDIDATE_UNDER_0P3S", "WARNING",
                                f"{ev.first_input_candidate - ev.t_tor:.3f} s after TOR"))

    tel = trial.telemetry
    lane = trial.column("[00].VehicleUpdate-roadInfo-laneId.0")
    road = trial.column("[00].VehicleUpdate-roadInfo-roadId.0")
    t = tel["t_rel"].to_numpy()
    i_tor = int(np.searchsorted(t, ev.t_tor)) if ev.t_tor is not None else None
    same_after = [tr for tr in transitions if tr.same_road and (ev.t_tor is None or tr.t_rel >= ev.t_tor)]
    row = {
        "trial_id": trial.meta.trial_id,
        "participant_id": trial.meta.participant_id,
        "density": trial.meta.density,
        "nback": trial.meta.nback,
        "header_variant": trial.header_variant,
        "n_telemetry_rows": len(tel),
        "has_export_footer": trial.footer is not None,
        "duration_s": float(t[-1]),
        "dt_median_s": float(np.median(np.diff(t))),
        "dt_max_s": float(np.max(np.diff(t))),
        "lane_gap_reltime_max_abs_err_s": float(lg_err),
        "lane_gap_null_tokens": int(trial.null_token_counts.get("laneGap.component1", 0)),
        "tor_state": tor.state,
        "tor_raw_values": ";".join(f"{v:.6f}" for v in tor.raw_values),
        "tor_ttc_at_values": ";".join(f"{v:.3f}" for v in tor.ttc_at_values),
        "tor_selected": ev.t_tor,
        "tor_protocol_consistent": tor.protocol_consistent,
        "manual_start": ev.t_manual_start,
        "manual_start_authority_semantics": ev.manual_start_authority_semantics,
        "handback_state": ev.handback.state,
        "manual_stop_raw_values": ";".join(f"{v:.6f}" for v in ev.handback.raw_values),
        "first_manual_episode_end": ev.handback.first_manual_episode_end,
        "lane_change_state": ev.lane_change.state,
        "lane_change_value": ev.lane_change.value,
        "lane_change_offset_to_lane_id_s": ev.lane_change.offset_s,
        "lane_change_transition": (f"{ev.lane_change.matched.lane_from}->{ev.lane_change.matched.lane_to}"
                                   if ev.lane_change.matched else None),
        "road_id_at_tor": float(road[i_tor]) if i_tor is not None and i_tor < len(road) else None,
        "lane_id_at_tor": float(lane[i_tor]) if i_tor is not None and i_tor < len(lane) else None,
        "same_road_transitions_after_tor": ";".join(f"{tr.lane_from}->{tr.lane_to}@{tr.t_rel:.2f}" for tr in same_after),
        "n_cross_road_renumberings": sum(1 for tr in transitions if not tr.same_road),
        **jumps,
        "brake_input_candidate": ev.brake_input_candidate,
        "steer_input_candidate": ev.steer_input_candidate,
        "first_input_candidate": ev.first_input_candidate,
        "first_input_candidate_under_0p3s": ev.first_input_candidate_implausibly_fast,
        "first_validated_human_input": ev.first_validated_human_input,
    }
    row.update(brake_channel_facts(trial, ev.t_tor, ev.handback.first_manual_episode_end))
    for ch, prof in adjacent_lane_profile(trial).items():
        for k, v in prof.items():
            row[f"{ch}__{k}"] = v
    row["n_event_clock_exceptions"] = sum(1 for c in clocks if not c.ok)
    row["qa_errors"] = ";".join(n.code for n in notices if n.severity == "ERROR")
    row["qa_warnings"] = ";".join(n.code for n in notices if n.severity == "WARNING")
    row["qa_info"] = ";".join(n.code for n in notices if n.severity == "INFO")
    return row
