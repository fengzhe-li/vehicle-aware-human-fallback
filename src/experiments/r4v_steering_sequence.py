"""Phase R4V-D: descriptive lateral-control sequence around Manual_Start in D003.

Descriptive only. Nothing here is a driver-response latency, an authorship claim
or an input to R3B. Event semantics are frozen as in R4V:

- TOR: shared clock origin
- Manual_Start (MS): switch to manual mode (manual inputs enabled)
- steering activity onset: derived from the steering-wheel angle (authorship
  PLAUSIBLE_BUT_UNVERIFIED)
- indicator onset: derived; channel undocumented, +1 = left inferred
- lane crossing: the validated Time_Lane_Change event
- Manual_Stop: switch back to automated mode (the end of the first manual episode)

Steering onset detectors are causal. An onset at time t depends only on samples
in [MS, t + sustain]. The search horizon is fixed (MS + 15 s) and never uses
lane crossing or Manual_Stop. The sign convention (+1: the direction of the
first post-MS excursion in most trials) is a fixed constant, stated in
SIGN_CONVENTION.

Usage: python -m src.experiments.r4v_steering_sequence [archive] [output_dir] [r2b_trial_table]
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.data.d003_ingest import D003Archive, observation_events
from src.experiments.r2a_event_vehicle_descriptives import archive_sha256, git_state
from src.experiments.r2b_repeated_exposure import fe_exposure_model
from src.experiments.r4v_channel_authorship import BRAKE_T, COL, eta2, icc1

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_OUTPUT = "results/R4V_steering_sequence"
DEFAULT_R2B_TRIALS = "results/R2B_repeated_exposure/trial_table.csv"

SEARCH_HORIZON_S = 15.0
SIGN_CONVENTION = {
    "value": +1,
    "basis": "in 418 of 492 trials the first post-MS angle excursion beyond 0.05 rad (either sign) is positive; "
             "negative first excursions concentrate in cells with a pre-MS negative drift (e.g. d0_n1). "
             "Lane crossing is NOT used to set it; the +1 = left mapping is inferred, not documented.",
}
# detector name -> (signal, threshold, sustain samples, reference)
#   reference "running_min": signed rise above the running minimum of the signed angle since MS
#   (robust to the cell-specific drift that continues after MS); "ms": signed change from the
#   value at MS; "ms_abs": |change| from the value at MS (the R4V detector); "rate": signed wheel speed.
DETECTORS = {
    "angle_rise_0.02_s5": ("angle", 0.02, 5, "running_min"),
    "angle_rise_0.05_s5": ("angle", 0.05, 5, "running_min"),   # primary
    "angle_rise_0.10_s5": ("angle", 0.10, 5, "running_min"),
    "angle_signed_0.05_s5": ("angle", 0.05, 5, "ms"),
    "angle_abs_0.05_s1": ("angle", 0.05, 1, "ms_abs"),
    "rate_signed_0.10_s3": ("rate", 0.10, 3, "rate"),
}
PRIMARY = "angle_rise_0.05_s5"
NEAR_M, FAR_M = 2.0, 20.0
STATION_RESID_OK_M, STATION_RATE_BAND = 2.0, (0.95, 1.05)

INTERVALS = {
    "tor_to_ms_s": ("TOR", "Manual_Start"),
    "ms_to_steer_onset_s": ("Manual_Start", "steering onset (primary)"),
    "steer_onset_to_indicator_s": ("steering onset", "left-indicator onset"),
    "steer_onset_to_lane_crossing_s": ("steering onset", "lane crossing"),
    "ms_to_lane_crossing_s": ("Manual_Start", "lane crossing"),
    "lane_crossing_to_manual_stop_s": ("lane crossing", "Manual_Stop"),
    "ms_to_manual_stop_s": ("Manual_Start", "Manual_Stop"),
    "ms_to_indicator_s": ("Manual_Start", "left-indicator onset"),
    "indicator_to_lane_crossing_s": ("left-indicator onset", "lane crossing"),
    "ms_to_excursion_start_s": ("Manual_Start", "start of the primary excursion (secondary)"),
}


# ---------------------------------------------------------------------------
# detectors
# ---------------------------------------------------------------------------


def detect_onset(t: np.ndarray, x: np.ndarray, t_start: float, t_end: float, threshold: float,
                 sustain: int = 1, sign: Optional[int] = SIGN_CONVENTION["value"],
                 reference: str = "ms") -> Optional[float]:
    """First time a run of `sustain` samples has deviation > threshold.

    reference "ms": deviation = sign*(x - x(t_start)); sign=None uses |x - x(t_start)|.
    reference "running_min": deviation = sign*x - min(sign*x over [t_start, t]).
    Returns the first sample of the qualifying run. Causal: the result depends only on
    samples up to onset + sustain.
    """
    idx = np.where((t >= t_start) & (t < t_end))[0]
    if not len(idx):
        return None
    if reference == "running_min":
        v = (1 if sign is None else sign) * x[idx]
        dev = v - np.minimum.accumulate(v)
    else:
        x0 = x[idx[0]]
        dev = np.abs(x[idx] - x0) if sign is None else sign * (x[idx] - x0)
    run = 0
    for j, ok in enumerate(dev > threshold):
        run = run + 1 if ok else 0
        if run >= sustain:
            return float(t[idx[j - sustain + 1]])
    return None


def detect_rate_onset(t, rate, t_start, t_end, threshold, sustain=3, sign=SIGN_CONVENTION["value"]):
    idx = np.where((t >= t_start) & (t < t_end))[0]
    run = 0
    for j, ok in enumerate(sign * rate[idx] > threshold):
        run = run + 1 if ok else 0
        if run >= sustain:
            return float(t[idx[j - sustain + 1]])
    return None


def excursion_start(t, x, t_start, t_onset, sign=SIGN_CONVENTION["value"]) -> Optional[float]:
    """Last time of the signed minimum of x in [t_start, t_onset]: where the detected excursion begins."""
    if t_onset is None:
        return None
    idx = np.where((t >= t_start) & (t <= t_onset))[0]
    if not len(idx):
        return None
    v = sign * x[idx]
    return float(t[idx[np.where(v == v.min())[0][-1]]])


def first_value(t, x, t0, t1, value) -> Optional[float]:
    idx = np.where((t >= t0) & (t < t1) & (x == value))[0]
    return float(t[idx[0]]) if len(idx) else None


# ---------------------------------------------------------------------------
# hazard and gap reconstruction
# ---------------------------------------------------------------------------


def hazard_station(t, s, road, dist, t_tor) -> Dict[str, object]:
    """s_h = s + dir * D on the road segment containing TOR, with D > 0 and t >= TOR - 15 s.

    dir = sign of ds/dt on that segment. Consistent if the within-trial residual p95
    is <= STATION_RESID_OK_M after TOR and dD/ds is within STATION_RATE_BAND.
    """
    i = int(np.argmin(np.abs(t - t_tor)))
    same = (road == road[i]) & (dist > 0) & (t >= t_tor - 15.0) & np.isfinite(s) & np.isfinite(dist)
    seg = np.where(same)[0]
    if len(seg) < 10:
        return {"station_state": "INSUFFICIENT"}
    direction = float(np.sign(np.median(np.diff(s[seg]))))
    h = s[seg] + direction * dist[seg]
    after = t[seg] >= t_tor
    station = float(np.median(h[~after])) if (~after).sum() >= 5 else float(np.median(h))
    resid = np.abs(h[after] - station) if after.any() else np.abs(h - station)
    ds, dd = np.diff(s[seg]), np.diff(dist[seg])
    ok = np.abs(ds) > 1e-6
    rate = float(np.median(-dd[ok] / (direction * ds[ok]))) if ok.sum() > 5 else float("nan")
    consistent = bool(np.percentile(resid, 95) <= STATION_RESID_OK_M
                      and STATION_RATE_BAND[0] <= rate <= STATION_RATE_BAND[1])
    return {"station_state": "CONSISTENT" if consistent else "NOT_CONSISTENT", "road_id": float(road[i]),
            "direction": direction, "station_m": station, "resid_p95_m": float(np.percentile(resid, 95)),
            "resid_max_m": float(resid.max()), "dD_per_ds": rate}


def gap_zero_context(t: np.ndarray, x: np.ndarray, partner: Optional[np.ndarray] = None,
                     t_lc: Optional[float] = None) -> np.ndarray:
    """Tag each sample of a gap channel. Tags describe context only; no zero is resolved to a distance.

    value | missing | negative | zero_after_lane_crossing | zero_handoff (partner channel appears
    at < NEAR_M in the same or next sample) | zero_after_near_value (< NEAR_M) | zero_after_far_value
    (>= FAR_M) | zero_after_mid_value | zero_from_recording_start (no earlier finite value)
    """
    tags = np.full(x.shape, "value", dtype=object)
    tags[np.isnan(x)] = "missing"
    tags[x < 0] = "negative"
    z = x == 0
    i = 0
    n = len(x)
    while i < n:
        if not z[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and z[j + 1]:
            j += 1
        k = i - 1
        while k >= 0 and not np.isfinite(x[k]):
            k -= 1
        prev = x[k] if k >= 0 else np.nan
        if t_lc is not None and t[i] >= t_lc - 0.1 and (i == 0 or t[i - 1] < t_lc + 0.5):
            tag = "zero_after_lane_crossing"
        elif not np.isfinite(prev):
            tag = "zero_from_recording_start"
        elif prev < NEAR_M:
            appear = partner is not None and any(
                0 < partner[k] < NEAR_M + 1.0 and (k == 0 or partner[k - 1] == 0) for k in range(i, min(i + 2, n)))
            tag = "zero_handoff" if appear else "zero_after_near_value"
        elif prev >= FAR_M:
            tag = "zero_after_far_value"
        else:
            tag = "zero_after_mid_value"
        tags[i:j + 1] = tag
        i = j + 1
    return tags


# ---------------------------------------------------------------------------
# per-trial sequence
# ---------------------------------------------------------------------------


def _interp(t, x, at):
    return float(np.interp(at, t, x)) if at is not None else None


def trial_sequence(tr) -> Optional[Dict[str, object]]:
    ev = observation_events(tr)
    if ev.t_tor is None or ev.t_manual_start is None:
        return None
    t = tr.telemetry["t_rel"].to_numpy()
    col = lambda k: tr.column(COL[k])
    ang, rate, torque, ind = col("steer_angle"), col("steer_speed"), col("steer_torque"), col("indicators")
    tor, ms = ev.t_tor, ev.t_manual_start
    lc = ev.lane_change.value if ev.lane_change.state == "VALIDATED" else None
    stop = ev.handback.first_manual_episode_end
    horizon = ms + SEARCH_HORIZON_S

    f: Dict[str, object] = {
        "trial_id": tr.meta.trial_id, "participant_id": tr.meta.participant_id,
        "cell": f"d{tr.meta.density}_n{tr.meta.nback}", "t_tor": tor, "t_ms": ms, "t_lane_crossing": lc,
        "lane_crossing_state": ev.lane_change.state, "t_manual_stop": stop, "manual_stop_state": ev.handback.state}
    onsets = {}
    for name, (sig, thr, sus, ref) in DETECTORS.items():
        if sig == "angle":
            o = detect_onset(t, ang, ms, horizon, thr, sus, None if ref == "ms_abs" else SIGN_CONVENTION["value"],
                             "running_min" if ref == "running_min" else "ms")
        else:
            o = detect_rate_onset(t, rate, ms, horizon, thr, sus)
        onsets[name] = o
        f[f"onset_{name}_rel_ms_s"] = (o - ms) if o is not None else None
    on = onsets[PRIMARY]
    f["t_steer_onset"] = on
    ex = excursion_start(t, ang, ms, on)
    f["t_excursion_start"] = ex
    # movement between TOR and MS by the primary rule, relative to the TOR value
    f["primary_rule_met_tor_to_ms"] = detect_onset(t, ang, tor, ms, DETECTORS[PRIMARY][1], DETECTORS[PRIMARY][2],
                                                   reference="running_min") is not None
    # indicator (+1 = left inferred; -1 = right inferred)
    f["indicator_left_before_tor"] = bool(((t < tor) & (ind == 1)).any())
    f["indicator_left_tor_to_ms"] = bool(((t >= tor) & (t < ms) & (ind == 1)).any())
    ind_on = first_value(t, ind, ms, horizon, 1)
    f["t_indicator_left"] = ind_on
    right = first_value(t, ind, lc, t[-1] + 1.0, -1) if lc is not None else None
    f["indicator_right_after_lc_rel_lc_s"] = (right - lc) if right is not None else None

    def d(a, b):
        return (b - a) if (a is not None and b is not None) else None

    f.update({"tor_to_ms_s": ms - tor, "ms_to_steer_onset_s": d(ms, on), "steer_onset_to_indicator_s": d(on, ind_on),
              "steer_onset_to_lane_crossing_s": d(on, lc), "ms_to_lane_crossing_s": d(ms, lc),
              "lane_crossing_to_manual_stop_s": d(lc, stop), "ms_to_manual_stop_s": d(ms, stop),
              "ms_to_indicator_s": d(ms, ind_on), "indicator_to_lane_crossing_s": d(ind_on, lc),
              "ms_to_excursion_start_s": d(ms, ex), "tor_to_steer_onset_s": d(tor, on)})
    f["order_ms_le_onset"] = (on >= ms) if on is not None else None
    f["order_onset_before_lc"] = (on < lc) if (on is not None and lc is not None) else None
    f["order_lc_before_stop"] = (lc < stop) if (lc is not None and stop is not None) else None
    # torque audit (manual window; lag in samples of best |corr| with angle, positive = torque leads)
    w = (t >= ms) & (t < min(stop if stop is not None else horizon, ms + 12.0))
    pre = (t >= tor - 10.0) & (t < tor - 0.2)
    f["torque_sd_pre_tor"] = float(np.nanstd(torque[pre])) if pre.any() else None
    f["torque_sd_manual"] = float(np.nanstd(torque[w])) if w.any() else None
    best = (None, None)
    if w.sum() > 20:
        q, a = torque[w], ang[w]
        for lag in range(-10, 11):
            qa = q[max(0, -lag):len(q) - max(0, lag)]
            aa = a[max(0, lag):len(a) - max(0, -lag)]
            if np.std(qa) > 1e-9 and np.std(aa) > 1e-9:
                c = float(np.corrcoef(qa, aa)[0, 1])
                if best[0] is None or abs(c) > abs(best[0]):
                    best = (c, lag)
    f["torque_angle_corr_manual"], f["torque_leads_angle_samples"] = best
    # co-activity (descriptive only; the brake channel is MIXED_OR_AMBIGUOUS, R4V)
    br = col("brake")
    f["brake_channel_active_at_steer_onset"] = bool(np.interp(on, t, br) > BRAKE_T) if on is not None else None
    # hazard
    road = tr.column("[00].VehicleUpdate-roadInfo-roadId.0")
    dist, s = col("d_construction"), col("abscissa")
    hz = hazard_station(t, s, road, dist, tor)
    f.update({f"hazard_{k}": v for k, v in hz.items()})
    for ev_name, at in (("steer_onset", on), ("lane_crossing", lc), ("tor", tor)):
        f[f"hazard_distance_at_{ev_name}_m"] = _interp(t, dist, at)
    # gaps: value at onset and at the last sample before the crossing, with zero context
    chans = {"d_follow": col("d_follow"), "d_lead_next": col("d_lead_next"), "d_follow_next": col("d_follow_next")}
    partner = {"d_lead_next": chans["d_follow_next"], "d_follow_next": chans["d_lead_next"], "d_follow": None}
    for k, x in chans.items():
        tags = gap_zero_context(t, x, partner[k], lc)
        for ev_name, at in (("steer_onset", on), ("pre_lane_crossing", (lc - 0.1) if lc is not None else None)):
            if at is None:
                f[f"{k}_at_{ev_name}_m"] = f[f"{k}_at_{ev_name}_tag"] = None
                continue
            j = int(np.searchsorted(t, at, side="right") - 1)
            f[f"{k}_at_{ev_name}_m"] = float(x[j]) if tags[j] == "value" else None
            f[f"{k}_at_{ev_name}_tag"] = str(tags[j])
        vals, counts = np.unique(tags, return_counts=True)
        for v, c in zip(vals, counts):
            f[f"{k}_tagcount_{v}"] = int(c)
    return f


# ---------------------------------------------------------------------------
# summaries
# ---------------------------------------------------------------------------


def variance_split(df: pd.DataFrame, col: str) -> Dict[str, Optional[float]]:
    d = df[["participant_id", col]].dropna()
    if len(d) < 10:
        return {"between_participant_sd": None, "within_participant_sd": None}
    means = d.groupby("participant_id")[col].transform("mean")
    return {"between_participant_sd": float(d.groupby("participant_id")[col].mean().std()),
            "within_participant_sd": float(np.sqrt(((d[col] - means) ** 2).sum() / (len(d) - d.participant_id.nunique())))}


def describe(df: pd.DataFrame, col: str) -> Dict[str, object]:
    x = df[col].dropna().astype(float)
    out = {"interval": col, "from": INTERVALS.get(col, ("", ""))[0], "to": INTERVALS.get(col, ("", ""))[1],
           "n": int(len(x)), "missing": int(df[col].isna().sum())}
    if len(x):
        q = x.quantile([.05, .25, .5, .75, .95])
        out.update({"median_s": float(q[.5]), "q25_s": float(q[.25]), "q75_s": float(q[.75]),
                    "p05_s": float(q[.05]), "p95_s": float(q[.95]),
                    "participant_icc1": icc1(df[col], df.participant_id), "cell_eta2": eta2(df[col], df.cell),
                    **variance_split(df, col)})
    return out


def detector_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in DETECTORS:
        c = f"onset_{name}_rel_ms_s"
        x = df[c]
        lc_rel = df.ms_to_lane_crossing_s
        g = df.groupby("cell")[c]
        rows.append({"detector": name, "primary": name == PRIMARY, "n": int(x.notna().sum()),
                     "missing": int(x.isna().sum()), "median_s": float(x.median()),
                     "q25_s": float(x.quantile(.25)), "q75_s": float(x.quantile(.75)),
                     "fraction_after_lane_crossing": float((x > lc_rel).sum() / (x.notna() & lc_rel.notna()).sum()),
                     "participant_icc1": icc1(x, df.participant_id), "cell_eta2": eta2(x, df.cell),
                     "min_cell_iqr_s": float((g.quantile(.75) - g.quantile(.25)).min())})
    return pd.DataFrame(rows)


DESCRIPTORS = {
    "ms_to_steer_onset": ("PROVISIONAL_DESCRIPTOR",
                          "derived event; authorship PLAUSIBLE_BUT_UNVERIFIED; median depends on the detector "
                          "(see onset_detector_sensitivity.csv); not a driver-response latency"),
    "steer_onset_to_lane_crossing": ("PROVISIONAL_DESCRIPTOR",
                                     "lane crossing is validated; the onset end inherits the detector and authorship "
                                     "caveats"),
    "steering_duration_proxy": ("BLOCKED",
                                "no documented manoeuvre-completion event; lane crossing is not completion and "
                                "Manual_Stop is not recovery completion; any end event would be invented"),
    "indicator_lead_lag_vs_steering": ("PROVISIONAL_DESCRIPTOR",
                                       "indicator channel undocumented (+1 = left inferred); not an intention time"),
    "target_lane_gap_at_steer_onset": ("PROVISIONAL_DESCRIPTOR",
                                       "channel names documented; the 'next lane' = target lane mapping is inferred; "
                                       "only non-zero values are reported; zero semantics unresolved"),
    "target_lane_gap_at_lane_crossing": ("PROVISIONAL_DESCRIPTOR",
                                         "taken at the last sample before crossing (next-lane channels become 0 at "
                                         "crossing in all trials); zero semantics unresolved"),
    "hazard_distance_at_steer_onset": ("VALIDATED_DESCRIPTOR",
                                       "logged, documented distance; -dD/dt matches speed; station reconstructs "
                                       "in station-consistent cells. Validated only for trials with station_state "
                                       "CONSISTENT; the reference point on the construction zone is undocumented"),
    "hazard_distance_at_lane_crossing": ("VALIDATED_DESCRIPTOR", "as hazard_distance_at_steer_onset"),
}


def _q(x: pd.Series) -> Dict[str, object]:
    x = x.dropna().astype(float)
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "median": float(x.median()), "q25": float(x.quantile(.25)), "q75": float(x.quantile(.75)),
            "p05": float(x.quantile(.05)), "p95": float(x.quantile(.95))}


def descriptor_values(df: pd.DataFrame) -> Dict[str, object]:
    ok = df.hazard_station_state == "CONSISTENT"
    out = {"hazard_distance_at_steer_onset_m (station-consistent trials)": _q(df.loc[ok, "hazard_distance_at_steer_onset_m"]),
           "hazard_distance_at_lane_crossing_m (station-consistent trials)": _q(df.loc[ok, "hazard_distance_at_lane_crossing_m"]),
           "hazard_distance_at_steer_onset_m (d0_n1, not station-consistent)":
               _q(df.loc[df.cell == "d0_n1", "hazard_distance_at_steer_onset_m"])}
    for k in ("d_lead_next", "d_follow_next", "d_follow"):
        for ev in ("steer_onset", "pre_lane_crossing"):
            out[f"{k}_at_{ev}_m (value-tagged samples only)"] = _q(df[f"{k}_at_{ev}_m"])
    g = df.groupby("cell").ms_to_indicator_s
    out["indicator_min_cell_iqr_s"] = float((g.quantile(.75) - g.quantile(.25)).min())
    out["indicator_presence_by_cell"] = df.assign(_p=df.t_indicator_left.notna()).groupby("cell")._p.mean().to_dict()
    return out


def run(archive_path: str = DEFAULT_ARCHIVE, output_dir: str = DEFAULT_OUTPUT,
        r2b_trials_path: str = DEFAULT_R2B_TRIALS) -> Dict[str, object]:
    arc = D003Archive(archive_path)
    names = arc.trial_names()
    rows = [r for r in (trial_sequence(arc.load(n)) for n in names) if r is not None]
    arc.close()
    df = pd.DataFrame(rows)
    exposure = pd.read_csv(r2b_trials_path, usecols=["trial_id", "exposure"])
    df = df.merge(exposure, on="trial_id", how="left")
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "event_table.csv"), index=False)

    stats_ = pd.DataFrame([describe(df, c) for c in INTERVALS])
    stats_.to_csv(os.path.join(output_dir, "interval_summary.csv"), index=False)
    sens = detector_sensitivity(df)
    sens.to_csv(os.path.join(output_dir, "onset_detector_sensitivity.csv"), index=False)
    cells = df.groupby("cell")[list(INTERVALS)].median()
    cells.insert(0, "n_trials", df.groupby("cell").size())
    cells.to_csv(os.path.join(output_dir, "cell_summary.csv"))
    parts = df.groupby("participant_id")[["ms_to_steer_onset_s", "steer_onset_to_lane_crossing_s",
                                          "ms_to_indicator_s"]].agg(["count", "median"])
    parts.columns = ["_".join(c) for c in parts.columns]
    parts.to_csv(os.path.join(output_dir, "participant_summary.csv"))

    haz = df.groupby("cell").agg(n=("trial_id", "size"),
                                 consistent=("hazard_station_state", lambda s: float((s == "CONSISTENT").mean())),
                                 road_id=("hazard_road_id", "median"), station_median_m=("hazard_station_m", "median"),
                                 station_sd_across_trials_m=("hazard_station_m", "std"),
                                 resid_p95_median_m=("hazard_resid_p95_m", "median"),
                                 dD_per_ds_median=("hazard_dD_per_ds", "median"),
                                 hazard_distance_at_tor_median_m=("hazard_distance_at_tor_m", "median"))
    haz.to_csv(os.path.join(output_dir, "hazard_reconstruction.csv"))

    gap_rows = []
    for k in ("d_follow", "d_lead_next", "d_follow_next"):
        tag_cols = [c for c in df.columns if c.startswith(f"{k}_tagcount_")]
        tot = df[tag_cols].fillna(0).sum()
        for c, v in tot.items():
            gap_rows.append({"channel": k, "tag": c.replace(f"{k}_tagcount_", ""), "samples": int(v),
                             "fraction": float(v / tot.sum())})
        for ev_name in ("steer_onset", "pre_lane_crossing"):
            vc = df[f"{k}_at_{ev_name}_tag"].value_counts()
            for tag, n in vc.items():
                gap_rows.append({"channel": k, "tag": f"at_{ev_name}:{tag}", "samples": int(n),
                                 "fraction": float(n / vc.sum())})
    pd.DataFrame(gap_rows).to_csv(os.path.join(output_dir, "gap_semantics.csv"), index=False)

    # repeated exposure (association only; participant-clustered)
    expo = []
    for outcome in ("ms_to_steer_onset_s", "steer_onset_to_lane_crossing_s"):
        for label, d in (("all", df), ("exclude_exposure_1", df[df.exposure > 1])):
            for cc in (True, False):
                m = fe_exposure_model(d.dropna(subset=["exposure"]), outcome, cell_controls=cc)
                expo.append({"population": label, **m})
    pd.DataFrame(expo).to_csv(os.path.join(output_dir, "exposure_association.csv"), index=False)

    t1_lo, t1_hi = 1.15, 3.0   # R3B assumption interval, quoted for comparison only
    x = df.tor_to_steer_onset_s.dropna()
    r3b = {"note": "comparison only; nothing is substituted into R3B",
           "r3b_t1_assumption_interval_s": [t1_lo, t1_hi],
           "tor_to_steer_onset_median_s": float(x.median()),
           "tor_to_steer_onset_iqr_s": [float(x.quantile(.25)), float(x.quantile(.75))],
           "fraction_steer_onset_before_t1_lo": float((x < t1_lo).mean()),
           "fraction_steer_onset_within_t1": float(((x >= t1_lo) & (x <= t1_hi)).mean()),
           "fraction_steer_onset_after_t1_hi": float((x > t1_hi).mean()),
           "fraction_brake_channel_active_at_steer_onset": float(df.brake_channel_active_at_steer_onset.dropna().mean())}

    summary = {
        "n_trials_total": len(names), "n_eligible": int(len(df)), "n_participants": int(df.participant_id.nunique()),
        "eligibility": "TOR resolved and a single Manual_Start; no event is imputed",
        "primary_detector": PRIMARY, "detectors": {k: list(v) for k, v in DETECTORS.items()},
        "search_horizon_s": SEARCH_HORIZON_S, "sign_convention": SIGN_CONVENTION,
        "missing": {"steer_onset": int(df.t_steer_onset.isna().sum()),
                    "lane_crossing": int(df.t_lane_crossing.isna().sum()),
                    "indicator_left": int(df.t_indicator_left.isna().sum()),
                    "manual_stop": int(df.t_manual_stop.isna().sum())},
        "ordering": {"onset_before_ms": int((df.order_ms_le_onset == False).sum()),  # noqa: E712
                     "onset_before_lc_fraction": float(df.order_onset_before_lc.dropna().mean()),
                     "primary_rule_met_tor_to_ms": int(df.primary_rule_met_tor_to_ms.sum())},
        "indicator": {"left_before_tor_trials": int(df.indicator_left_before_tor.sum()),
                      "left_tor_to_ms_trials": int(df.indicator_left_tor_to_ms.sum()),
                      "right_after_lc_median_s": float(df.indicator_right_after_lc_rel_lc_s.median()),
                      "indicator_before_steer_onset_fraction": float((df.steer_onset_to_indicator_s.dropna() < 0).mean())},
        "torque": {"corr_with_angle_manual_median": float(df.torque_angle_corr_manual.median()),
                   "corr_abs_ge_0.9_fraction": float((df.torque_angle_corr_manual.abs() >= 0.9).mean()),
                   "leads_angle_samples_median": float(df.torque_leads_angle_samples.median()),
                   "sd_pre_tor_median": float(df.torque_sd_pre_tor.median()),
                   "sd_manual_median": float(df.torque_sd_manual.median()),
                   "verdict": "NOT_IDENTIFIABLE as driver torque; excluded from onset definition",
                   "reason": "undocumented channel; in the manual window it is almost a linear function of the "
                             "angle (opposite sign), so it adds little independent information and cannot "
                             "distinguish driver torque from a restoring/feedback torque"},
        "hazard": {"formula": "s_h = roadAbscissa + dir * Distance_to_Construction on the TOR road segment, "
                              "D > 0, t >= TOR - 15 s; dir = sign(d roadAbscissa / dt)",
                   "consistent_fraction": float((df.hazard_station_state == "CONSISTENT").mean()),
                   "consistent_by_cell": haz.consistent.to_dict()},
        "r3b_relation": r3b,
        "descriptor_values": descriptor_values(df),
        "descriptors": {k: {"class": c, "reason": r} for k, (c, r) in DESCRIPTORS.items()},
        "steering_authorship": "PLAUSIBLE_BUT_UNVERIFIED (unchanged from R4V)",
        "claims": "descriptive timing only; no causal driver-response latency; no synthesis",
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
        fh.write("\n")
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump({"archive_sha256": archive_sha256(archive_path), **git_state(),
                   "code": "src/experiments/r4v_steering_sequence.py", "r2b_trial_table": r2b_trials_path},
                  fh, indent=2)
        fh.write("\n")
    return {"events": df, "summary": summary, "intervals": stats_, "sensitivity": sens}


if __name__ == "__main__":
    run(*sys.argv[1:4])
