# R2A: observation-safe D003 descriptives (event timing and vehicle state)

**Interpretation rule (B17):** accelerator, brake and steering channels are not driver-only channels. Nothing here is a driver action, driver command or human input. No model fitted; no causal claim; no stabilisation metric. Scenario cells are descriptive only: they are aliased with road, speed, hazard state, lane configuration, run timing and automation-transition behaviour (B11).

Source archive sha256 `6e85e5365d0ae5e356559d20cf0b95cf81d60f9bd3ba5a52ec36021f664ca212`; code commit `9d1c41d01a5a141f07020610c58879b76b214d11` (src/ dirty at generation: False).

## Populations

| population | n | rule |
|---|---|---|
| RAW | 513 | every simulator CSV in the archive |
| TOR_PRESENT | 498 | TOR column present in the file header |
| TOR_ANCHORED | 492 | TOR anchor resolved (single value, or unique value at TTC 7.0 ± 0.25 s) |
| OWNER_WINDOW_ELIGIBLE | 478 | TOR_ANCHORED and lane change VALIDATED against lane_id and TOR < lane change (owners' published window; not handback-bounded) |
| LANE_CHANGE_ANCHORED | 477 | OWNER_WINDOW_ELIGIBLE and lane change < handback |
| MANUAL_WINDOW_ELIGIBLE | 492 | TOR_ANCHORED and single Manual_Start and handback defined and TOR < handback and Manual_Start < handback |
| OWNER_ANALYSIS_SET | UNKNOWN / NOT RECONSTRUCTED | UNKNOWN / NOT RECONSTRUCTED (owner per-trial list not public) |

There is no universal clean denominator. A trial can be eligible for one metric and not another: e.g. the 6 multi-TOR-unresolved trials have valid Manual_Start/Manual_Stop events but no TOR anchor, so they enter no TOR-anchored metric; the 13 trials without a lane-change channel (plus 1 lane-change clock exception) have TOR-anchored manual windows but no lane-change window; one trial (lane change after handback) is in the owners' window but not in the manual-interval lane-change window.

## Windows

| window | definition |
|---|---|
| POST_TOR_MANUAL | [TOR, handback) where handback = first Manual_Stop after Manual_Start |
| POST_BUTTON_MANUAL | [Manual_Start, handback); Manual_Start authority semantics UNRESOLVED |
| OWNER_TOR_TO_LANE_CHANGE | [TOR, validated lane change] as published by the owners; requires OWNER_WINDOW_ELIGIBLE; not handback-bounded |
| MANUAL_TOR_TO_LANE_CHANGE | [TOR, validated lane change] with lane change < handback; requires LANE_CHANGE_ANCHORED |

Handback (first Manual_Stop after Manual_Start) is a protocol-driven competing event, not independent censoring. The owners' published window and the handback-bounded window are stored separately (`owner_*` and `manual_*` columns).

## Event timing and vehicle-state quantities

| Quantity | Window | Denominator | Result |
|---|---|---|---|
| t_button (Manual_Start − TOR) | event difference | TOR_ANCHORED with Manual_Start | n=492; median 1.65 (IQR 1.25–2) s |
| TOR → lane change | owners' published | OWNER_WINDOW_ELIGIBLE | n=478; median 6.43 (IQR 5.45–7.7) s |
| TOR → lane change | manual-interval | LANE_CHANGE_ANCHORED | n=477; median 6.4 (IQR 5.45–7.7) s |
| minimum TTC, approach domain | owners' published | OWNER_WINDOW_ELIGIBLE | n=478; median 2.45 (IQR 1.62–3.22) s |
| minimum TTC, approach domain | manual-interval | LANE_CHANGE_ANCHORED | n=477; median 2.45 (IQR 1.62–3.22) s |
| vehicle max longitudinal acceleration | owners' published | OWNER_WINDOW_ELIGIBLE | n=478; median 0.738 (IQR 0.151–2.28) m/s² |
| vehicle max longitudinal deceleration | owners' published | OWNER_WINDOW_ELIGIBLE | n=478; median 3.81 (IQR 1.49–7.82) m/s² |
| vehicle max longitudinal deceleration | manual-interval | LANE_CHANGE_ANCHORED | n=477; median 3.8 (IQR 1.49–7.83) m/s² |
| vehicle speed at TOR | TOR sample | TOR_ANCHORED | n=492; median 25 (IQR 24.4–27) m/s |
| hazard-station crossing after TOR | first distance ≤ 0 | TOR_ANCHORED with a crossing | n=492; median 8.92 (IQR 7.8–11.1) s |

The owners (arXiv 2507.22252) report 'maximum deceleration' and 'maximum acceleration' as takeover-quality indicators. Here they are **vehicle kinematics** only: under B17, automation or simulator activity may contribute, so they are not evidence of driver braking. The sources read gave no owner numerical values, so these are definition-compatible measurements, not numerical replications.

## Control-channel observations around TOR (B17 evidence; authorship UNRESOLVED)

Denominator: MANUAL_WINDOW_ELIGIBLE (n=492). Within 0.3 s of TOR (before plausible human reaction):

| density | nback | n_trials | accelerator_channel_drops_to_zero_within_0p3s | brake_channel_active_within_0p3s | steering_channel_moving_before_tor | earliest_channel_activity_within_0p3s |
|---|---|---|---|---|---|---|
| 0 | 0 | 56 | 0 | 0 | 0 | 0 |
| 0 | 1 | 57 | 57 | 1 | 57 | 0 |
| 0 | 2 | 54 | 53 | 0 | 0 | 0 |
| 10 | 0 | 53 | 53 | 53 | 53 | 53 |
| 10 | 1 | 57 | 0 | 0 | 0 | 0 |
| 10 | 2 | 57 | 57 | 0 | 0 | 0 |
| 20 | 0 | 50 | 0 | 0 | 50 | 0 |
| 20 | 1 | 51 | 51 | 24 | 50 | 4 |
| 20 | 2 | 57 | 50 | 29 | 28 | 21 |

The pattern is scenario-cell-specific. It is **consistent with** different automation-transition behaviours across cells (for example, accelerator actuation released at TOR in some cells and held in others), but the controller semantics are undocumented and no transition policy is inferred.

- Earliest brake/steering channel activity after TOR: n=492; median 1.15 (IQR 0.4–1.25) s; relative to Manual_Start: n=492; median -0.601 (IQR -1.25–-0.2) s. These are channel observations, not human first inputs.
- Steering-wheel-angle channel maximum in the owners' window (owners' 'maximum steering angle'): n=478; median 0.194 (IQR 0.143–0.298) rad (authorship UNRESOLVED).

## Channel-activity diagnostics (withdrawn correction counts, re-examined as channel activity)

Denominator: MANUAL_WINDOW_ELIGIBLE (n=492). Medians per trial:

| observation | detector | POST_TOR_MANUAL | POST_BUTTON_MANUAL | HISTORICAL_ACUTE_8S_POST_TOR | HISTORICAL_FULL_RECORD_POST_TOR_INVALID |
|---|---|---|---|---|---|
| brake_channel_peaks | prominence15 | 1.0 | 1.0 | 1.0 | 3.0 |
| brake_channel_peaks | prominence30 | 1.0 | 1.0 | 1.0 | 2.0 |
| brake_channel_peaks | prominence5 | 2.0 | 1.0 | 2.0 | 4.0 |
| steering_channel_hysteresis_reversals | gap1deg_lowpass2Hz | 9.0 | 9.0 | 3.0 | 15.0 |
| steering_channel_hysteresis_reversals | gap1deg_raw | 9.0 | 9.0 | 3.0 | 16.0 |
| steering_channel_hysteresis_reversals | gap2deg_lowpass2Hz | 7.0 | 7.0 | 2.0 | 13.0 |
| steering_channel_hysteresis_reversals | gap2deg_raw | 7.0 | 7.0 | 2.0 | 13.0 |
| steering_channel_hysteresis_reversals | gap3deg_lowpass2Hz | 6.0 | 6.0 | 2.0 | 11.0 |
| steering_channel_hysteresis_reversals | gap3deg_raw | 6.0 | 6.0 | 2.0 | 12.0 |
| steering_channel_hysteresis_reversals | gap5deg_lowpass2Hz | 5.0 | 5.0 | 1.0 | 9.0 |
| steering_channel_hysteresis_reversals | gap5deg_raw | 5.0 | 5.0 | 1.0 | 9.0 |

Counts depend strongly on the detector (hysteresis gap, prominence) and scale with window length, which ends at a protocol-driven handback. They are not promoted to any human-correction metric. Historical pre-audit values (INVALID): median 3 brake extrema, 2 brake reapplications and 13 steering reversals over the full post-TOR record; 2 reversals in the 8 s acute window.

## Status of candidate quantities

| quantity | status | note |
|---|---|---|
| t_button = Manual_Start − TOR | VALIDATED MEASUREMENT | event timing of the mode-switch press; not authority transfer |
| TOR → validated lane change duration | VALIDATED MEASUREMENT | both events validated per trial |
| minimum TTC in the approach domain | PROVISIONAL MEASUREMENT | domain rule (distance > 0, speed > 0, TTC > 0) is ours; owners' handling not stated |
| vehicle maximum longitudinal acceleration / deceleration | VEHICLE-STATE DESCRIPTIVE | kinematics only; not attributed to the driver |
| longitudinal hazard-station crossing (T_pass) | VEHICLE-STATE DESCRIPTIVE | geometric crossing only; not clearance, not collision |
| steering-wheel-angle channel maxima (owners' 'maximum steering angle') | UNRESOLVED CHANNEL AUTHORSHIP | channel observation; not attributed to the driver |
| earliest brake/steering channel activity after TOR | UNRESOLVED CHANNEL AUTHORSHIP | not a human first input |
| window-restricted channel reversal / peak counts | UNRESOLVED CHANNEL AUTHORSHIP | diagnostic of channel activity only |
| T_first / first brake / first steering input as human response | WITHDRAWN | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS |
| brake-first vs steer-first; negative handover lag; brake-rise latency | WITHDRAWN | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS |
| maximum braking / steering attributed to the driver | WITHDRAWN | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS |
| correction counts as human corrections | WITHDRAWN | full-record windows and channel authorship |
| T_stable | WITHDRAWN | window extends past handback |
| collision proxy | WITHDRAWN | disagrees with lane evidence; hazard geometry unidentified |
