"""Phase R2A: analysis populations and enforced observation windows for D003.

Built only on the canonical strict ingestion (`src/data/d003_ingest.py`).

Populations (each trial gets a membership flag and, when excluded, a reason):

- RAW: every simulator file (513).
- TOR_PRESENT: the file contains TOR information (TOR column present).
- TOR_ANCHORED: a usable TOR anchor was resolved (single value, or unique value
  matching the owners' documented TTC ~ 7 s protocol).
- OWNER_WINDOW_ELIGIBLE: TOR_ANCHORED, lane change VALIDATED against lane_id, and
  TOR < lane change. Eligible for the owners' published window [TOR, lane change],
  which is not bounded by handback.
- LANE_CHANGE_ANCHORED: OWNER_WINDOW_ELIGIBLE and lane change < end of the first
  manual episode (handback). Eligible for lane-change-anchored manual-interval
  metrics.
- MANUAL_WINDOW_ELIGIBLE: TOR_ANCHORED, one Manual_Start value, a defined end of
  the first manual episode, and TOR < end and Manual_Start < end.
- OWNER_ANALYSIS_SET: UNKNOWN / NOT RECONSTRUCTED. The owners' 466-trial set
  (arXiv 2507.22252) cannot be rebuilt from public information; no repo
  population is equal to it.

Windows (no human-control quantity may use data at or after the end of the
first manual episode, i.e. after Time_Manual_Stop / handback):

- POST_TOR_MANUAL: [TOR, handback)
- POST_BUTTON_MANUAL: [Manual_Start, handback)   (authority semantics UNRESOLVED)
- OWNER_TOR_TO_LANE_CHANGE: [TOR, lane change], the owners' published window
  (arXiv 2507.22252); requires OWNER_WINDOW_ELIGIBLE; NOT handback-bounded.
- MANUAL_TOR_TO_LANE_CHANGE: [TOR, lane change] restricted to lane change <
  handback; requires LANE_CHANGE_ANCHORED. Used when a metric is meant to describe
  the manual-control interval.

The two lane-change windows differ only for trials whose lane change occurs after
handback (one trial in the public archive); they are stored separately and never
mixed.

Control channels (accelerator, brake, steering) are NOT treated as driver-only
channels anywhere in this module (blocker B17).

Handback is a protocol-driven competing event (participants were instructed to
hand control back after the lane change); it is not independent censoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from src.data.d003_ingest import D003Trial, ObservationEvents, observation_events

POPULATION_RULES: Dict[str, str] = {
    "RAW": "every simulator CSV in the archive",
    "TOR_PRESENT": "TOR column present in the file header",
    "TOR_ANCHORED": "TOR anchor resolved (single value, or unique value at TTC 7.0 ± 0.25 s)",
    "OWNER_WINDOW_ELIGIBLE": "TOR_ANCHORED and lane change VALIDATED against lane_id and TOR < lane change (owners' published window; not handback-bounded)",
    "LANE_CHANGE_ANCHORED": "OWNER_WINDOW_ELIGIBLE and lane change < handback",
    "MANUAL_WINDOW_ELIGIBLE": "TOR_ANCHORED and single Manual_Start and handback defined and TOR < handback and Manual_Start < handback",
    "OWNER_ANALYSIS_SET": "UNKNOWN / NOT RECONSTRUCTED (owner per-trial list not public)",
}

WINDOW_DEFINITIONS: Dict[str, str] = {
    "POST_TOR_MANUAL": "[TOR, handback) where handback = first Manual_Stop after Manual_Start",
    "POST_BUTTON_MANUAL": "[Manual_Start, handback); Manual_Start authority semantics UNRESOLVED",
    "OWNER_TOR_TO_LANE_CHANGE": "[TOR, validated lane change] as published by the owners; requires OWNER_WINDOW_ELIGIBLE; not handback-bounded",
    "MANUAL_TOR_TO_LANE_CHANGE": "[TOR, validated lane change] with lane change < handback; requires LANE_CHANGE_ANCHORED",
}


class ObservationWindowError(ValueError):
    """Raised when a window would extend beyond handback or lacks its anchors."""


@dataclass
class TrialPopulation:
    trial_id: str
    events: ObservationEvents
    tor_present: bool
    tor_anchored: bool
    owner_window_eligible: bool
    lane_change_anchored: bool
    manual_window_eligible: bool
    reasons: Dict[str, str]

    @property
    def handback(self) -> Optional[float]:
        return self.events.handback.first_manual_episode_end


def classify_trial(trial: D003Trial) -> TrialPopulation:
    ev = observation_events(trial)
    reasons: Dict[str, str] = {}
    tor_present = ev.tor.state != "MISSING_TOR_COLUMN"
    if not tor_present:
        reasons["TOR_PRESENT"] = ev.tor.state
    tor_anchored = ev.t_tor is not None
    if not tor_anchored:
        reasons["TOR_ANCHORED"] = ev.tor.state
    end = ev.handback.first_manual_episode_end

    owner_ok = tor_anchored and ev.lane_change.state == "VALIDATED" and ev.lane_change.value > ev.t_tor
    if not tor_anchored:
        reasons["OWNER_WINDOW_ELIGIBLE"] = f"no TOR anchor ({ev.tor.state})"
    elif ev.lane_change.state != "VALIDATED":
        reasons["OWNER_WINDOW_ELIGIBLE"] = f"lane change {ev.lane_change.state}"
    elif not owner_ok:
        reasons["OWNER_WINDOW_ELIGIBLE"] = "lane change not after TOR"
    lc_ok = owner_ok and end is not None and ev.lane_change.value < end
    if not owner_ok:
        reasons["LANE_CHANGE_ANCHORED"] = reasons["OWNER_WINDOW_ELIGIBLE"]
    elif not lc_ok:
        reasons["LANE_CHANGE_ANCHORED"] = "lane change at or after handback" if end is not None else "no handback"

    manual_ok = (
        tor_anchored and ev.t_manual_start is not None and end is not None
        and ev.t_tor < end and ev.t_manual_start < end
    )
    if not manual_ok:
        if not tor_anchored:
            reasons["MANUAL_WINDOW_ELIGIBLE"] = f"no TOR anchor ({ev.tor.state})"
        elif ev.t_manual_start is None:
            reasons["MANUAL_WINDOW_ELIGIBLE"] = "Manual_Start missing or ambiguous"
        elif end is None:
            reasons["MANUAL_WINDOW_ELIGIBLE"] = "no handback"
        else:
            reasons["MANUAL_WINDOW_ELIGIBLE"] = "TOR or Manual_Start not before handback"
    return TrialPopulation(trial.meta.trial_id, ev, tor_present, tor_anchored, owner_ok, lc_ok, manual_ok, reasons)


def window_bounds(pop: TrialPopulation, window: str) -> Tuple[float, float]:
    """Return (start, end) for a named window, enforcing the handback rule."""
    ev = pop.events
    end_manual = pop.handback
    if window == "POST_TOR_MANUAL":
        if not pop.manual_window_eligible:
            raise ObservationWindowError(f"{pop.trial_id}: not MANUAL_WINDOW_ELIGIBLE")
        start, end = ev.t_tor, end_manual
    elif window == "POST_BUTTON_MANUAL":
        if not pop.manual_window_eligible:
            raise ObservationWindowError(f"{pop.trial_id}: not MANUAL_WINDOW_ELIGIBLE")
        start, end = ev.t_manual_start, end_manual
    elif window == "OWNER_TOR_TO_LANE_CHANGE":
        # Owners' published definition: deliberately not handback-bounded.
        if not pop.owner_window_eligible:
            raise ObservationWindowError(f"{pop.trial_id}: not OWNER_WINDOW_ELIGIBLE")
        return float(ev.t_tor), float(ev.lane_change.value)
    elif window == "MANUAL_TOR_TO_LANE_CHANGE":
        if not pop.lane_change_anchored:
            raise ObservationWindowError(f"{pop.trial_id}: not LANE_CHANGE_ANCHORED")
        start, end = ev.t_tor, ev.lane_change.value
    else:
        raise ObservationWindowError(f"unknown window {window!r}")
    if end_manual is None or end > end_manual:
        raise ObservationWindowError(f"{pop.trial_id}: window {window} extends beyond handback")
    return float(start), float(end)


MANUAL_INTERVAL_WINDOWS = ("POST_TOR_MANUAL", "POST_BUTTON_MANUAL", "MANUAL_TOR_TO_LANE_CHANGE")


def window_mask(t: np.ndarray, pop: TrialPopulation, window: str) -> np.ndarray:
    """Boolean sample mask for a window. Manual windows are half-open at handback."""
    start, end = window_bounds(pop, window)
    if window in ("OWNER_TOR_TO_LANE_CHANGE", "MANUAL_TOR_TO_LANE_CHANGE"):
        return (t >= start) & (t <= end)
    return (t >= start) & (t < end)
