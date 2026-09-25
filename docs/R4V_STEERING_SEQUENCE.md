# R4V-D: D003 descriptive steering sequence

**Status:** 2026-09-24. Descriptive only. No synthesis. No longitudinal t1 or braking strength is inferred. Nothing is substituted into R3B.
**Code:** `src/experiments/r4v_steering_sequence.py`.
**Outputs:** `results/R4V_steering_sequence/`:
- `event_table.csv` (one row per trial)
- `interval_summary.csv`
- `onset_detector_sensitivity.csv`
- `cell_summary.csv`
- `participant_summary.csv`
- `hazard_reconstruction.csv`
- `gap_semantics.csv`
- `exposure_association.csv`
- `summary.json`
- `provenance.json`

**Tests:** `tests/test_r4v_steering_sequence.py`.

The raw D003 archive is read only. The repeated-exposure index is taken from the R2B trial table.

## 1. Frozen event semantics

| Event | Meaning used here |
|---|---|
| TOR | shared clock origin |
| Manual_Start (MS) | switch to manual mode; manual inputs enabled (documented design intent) |
| steering activity onset | derived from the steering-wheel angle; authorship **PLAUSIBLE_BUT_UNVERIFIED** (R4V) |
| indicator onset | derived; the channel is undocumented; +1 = left is inferred |
| lane crossing | the validated `Time_Lane_Change` event |
| Manual_Stop | switch back to automated mode (end of the first manual episode) |

These are kept distinct:
- MS is not steering onset.
- Steering onset is not lane crossing.
- Lane crossing is not manoeuvre completion.
- Manual_Stop is not recovery completion.

## 2. Steering activity onset: definition and detector comparison

**Signal facts.**
- Sampling is 20 Hz (dt 0.05 s).
- Baseline noise just before MS is small: the range of the angle over [MS−0.5 s, MS) has a p95 of 0.011 rad and a p99 of 0.015 rad.
- The baseline also carries **cell-scripted content** (R4V): the angle is cell-locked before TOR, and in some cells a negative drift continues for about 1 s after MS. In d0_n1 the median change is −0.023 rad at MS+1 s.
- Torque is excluded (§5).
- The wheel-speed channel matches the numerical derivative of the angle (median r = 0.95).

**Primary definition (`angle_rise_0.05_s5`).** Onset is the first sample of a run of 5 samples (0.25 s) in which the signed angle rises more than 0.05 rad above its running minimum since MS.

Properties:
- **Causal.** An onset depends only on samples in [MS, onset + 0.25 s]. The search horizon is fixed at MS + 15 s. Lane crossing and Manual_Stop are never used; this is tested by truncation and perturbation.
- **Robust to drift.** A monotone scripted drift never triggers the detector. A rise after a drift is measured from the trough.
- **Direction.** The sign convention is +1, the direction of the first post-MS excursion beyond 0.05 rad in 418 of 492 trials. It is set without lane crossing. The "+1 = left" mapping is inferred.
- The threshold is about 3× the p99 pre-MS range.

**Secondary descriptor:** the *excursion start*, the last running-minimum time before the onset. It is reported separately.

| Detector | n | Missing | MS→onset median (s) | IQR (s) | After lane crossing | ICC(1) | Cell η² | Min cell IQR (s) |
|---|---|---|---|---|---|---|---|---|
| rise 0.02 rad, 5 samples | 492 | 0 | 1.43 | 1.00–2.15 | 0 % | 0.23 | 0.04 | 0.55 |
| **rise 0.05 rad, 5 samples (primary)** | 491 | 1 | **2.10** | **1.30–3.13** | 1.7 % | 0.19 | 0.08 | 1.05 |
| rise 0.10 rad, 5 samples | 477 | 15 | 3.00 | 1.90–4.55 | 13.2 % | 0.25 | 0.03 | 1.40 |
| signed change from MS value, 0.05 rad | 475 | 17 | 2.35 | 1.30–3.50 | 0.4 % | 0.18 | 0.10 | 1.16 |
| \|change\| from MS value, 0.05 rad (R4V) | 492 | 0 | 2.00 | 1.15–3.16 | 1.3 % | 0.16 | 0.09 | 1.16 |
| signed wheel speed > 0.10 rad/s, 3 samples | 487 | 5 | 1.95 | 1.15–3.20 | 4.7 % | 0.09 | 0.04 | 1.25 |

**Why the primary was chosen:**
- The fixed-reference signed detector misses 17 trials, 8 of them in d0_n1. The post-MS drift pulls the angle away from its MS value, so those trials lose their onset.
- The absolute detector can fire on the drift itself: 74 first excursions are negative, 24 of them in d0_n1.
- The 0.10 rad detector places 13 % of onsets after lane crossing.

**The onset time depends on the detector.** Across defensible detectors the median ranges from 1.4 to 3.0 s. No detector is cell-stereotyped (every cell IQR is ≥ 0.55 s).

## 3. Event sequences (492 eligible trials, 57 participants)

**Eligibility:** TOR resolved and a single Manual_Start. Nothing is imputed.

**Missing events:**
- steering onset: 1
- lane crossing: 14 (13 absent column, 1 clock exception)
- left indicator: 126
- Manual_Stop: 0

| Interval | n | Median (s) | IQR (s) | 5–95 % (s) | ICC(1) | Cell η² | SD between / within participant (s) |
|---|---|---|---|---|---|---|---|
| TOR → MS | 492 | 1.65 | 1.25–2.00 | 0.65–2.92 | 0.13 | 0.14 | 0.36 / 0.71 |
| MS → steering onset | 491 | 2.10 | 1.30–3.13 | 0.75–5.43 | 0.19 | 0.08 | 0.94 / 1.58 |
| MS → excursion start (secondary) | 491 | 0.85 | 0.25–1.55 | 0.05–3.98 | 0.12 | 0.06 | 0.66 / 1.30 |
| steering onset → indicator | 365 | −0.35 | −0.85 to 0.60 | −3.43 to 4.13 | 0.14 | 0.05 | 1.47 / 2.31 |
| steering onset → lane crossing | 477 | 2.45 | 2.00–3.30 | 1.50–8.52 | 0.06 | 0.11 | 2.57 / 6.13 |
| MS → lane crossing | 478 | 4.80 | 3.75–5.94 | 2.79–12.18 | 0.09 | 0.12 | 2.99 / 6.54 |
| lane crossing → Manual_Stop | 478 | 11.80 | 8.96–15.04 | 5.38–25.61 | 0.28 | 0.02 | 5.42 / 7.67 |
| MS → Manual_Stop | 492 | 16.95 | 13.55–22.40 | 9.63–38.37 | 0.28 | 0.09 | 7.11 / 10.15 |
| MS → indicator | 366 | 2.03 | 1.40–3.20 | 0.10–6.53 | 0.18 | 0.08 | 1.43 / 2.15 |
| indicator → lane crossing | 354 | 2.80 | 2.30–3.85 | 1.05–9.62 | 0.12 | 0.13 | 3.92 / 6.77 |

**Ordering:**
- no onset falls before MS;
- the primary rule is never met between TOR and MS;
- onset precedes lane crossing in 98.3 % of trials.

**Variation.** Within-participant variation exceeds between-participant variation for every interval. Participant structure is weak (ICC ≤ 0.19 for the steering intervals). Cell effects are small (η² ≤ 0.14).

**Per-cell medians** (`cell_summary.csv`):

| Measure | Range of cell medians (s) |
|---|---|
| MS → onset | 1.48 (d0_n2) to 2.92 (d20_n0) |
| onset → lane crossing | 2.00 to 3.32 |

These are timing descriptions, not driver-response latencies.

## 4. Indicator audit

- **Before MS:** the left indicator (+1) is never on between TOR and MS. It is on before TOR in 2 trials, far earlier.
- **Presence:** 69–83 % of trials per cell.
- **Timing:** onset is MS + 2.03 s (median), 2.80 s before lane crossing, and 0.35 s before the primary steering onset. The indicator comes first in 63 % of trials.
- **Structure:** weakly participant-structured (ICC 0.18); not scenario-scripted (cell η² 0.08; smallest cell IQR 1.10 s).
- **Right indicator:** −1 occurs a median of 5.1 s after lane crossing. That fits −1 = right, for the return lane change, but this is inferred.

**Class: PLAUSIBLE_BUT_UNVERIFIED.** It is not called an intention time.

## 5. Steering torque audit

- **Signal structure:** there is usable structure. The SD rises from 0.03 before TOR to 0.28 in the manual window.
- **Relation to the angle:** in the manual window torque is almost a linear function of the angle, with the **opposite sign**. The median lagged correlation is −0.987, and |r| ≥ 0.9 in 83 % of trials. Torque leads the angle by about 2 samples (0.1 s).
- **Interpretation:** this pattern fits a restoring or feedback torque as well as a driver torque. The channel is undocumented, so its sign convention and semantics cannot separate the two.

**Verdict:** NOT_IDENTIFIABLE as driver torque. It adds little information beyond the angle and is **excluded from the onset definition**.

## 6. Hazard position reconstruction

**Formula:** `s_h = roadAbscissa + dir · Distance_to_Construction`, applied on the road segment (`roadId`) containing TOR, with D > 0 and t ≥ TOR − 15 s. Here `dir` is the sign of d(roadAbscissa)/dt; travel runs in the negative abscissa direction in 277 of 492 trials.

**Validation:**
- **Within a trial:** the residual after TOR must have a p95 ≤ 2 m, and dD/ds must lie in 0.95–1.05.
- **Across trials:** the station should be the same within a cell.

| Cell | Road | Station (m) | SD across trials (m) | Median residual p95 (m) | dD/ds | Consistent |
|---|---|---|---|---|---|---|
| d0_n0 | 15 | 79.7 | 0.39 | 0.74 | 1.00 | 100 % |
| d0_n1 | 37 | 788.9 | 0.36 | **99.1** | **0.78** | **0 %** |
| d0_n2 | 23 | 205.1 | 0.36 | 0.20 | 1.00 | 100 % |
| d10_n0 | 24 | 1189.3 | 0.41 | 0.66 | 0.99 | 100 % |
| d10_n1 | 31 | 74.4 | 0.42 | 0.32 | 1.00 | 100 % |
| d10_n2 | 15 | 79.4 | 0.33 | 0.81 | 1.00 | 100 % |
| d20_n0 | 24 | 93.7 | 0.34 | 0.44 | 1.00 | 100 % |
| d20_n1 | 24 | 1189.7 | 1.66 | 0.35 | 1.00 | 100 % |
| d20_n2 | 15 | 1200.8 | 0.37 | 0.49 | 1.00 | 100 % |

**Verdict:** a **fixed longitudinal station is reconstructed in 8 of 9 cells** (435 of 492 trials). Across the whole trial set, −dD/dt matches vehicle speed (median ratio 0.995).

**d0_n1 is not consistent.** There, D falls at only about 0.6–0.8× the abscissa rate. The cause is not identifiable from the logged channels; D is kept only as a logged trial-relative distance.

The reference point on the construction zone, its lateral extent and lane width are not logged, and none is invented.

## 7. Target-lane gap channels

The channel names give their roles:
- 82 = following vehicle (own lane, rear);
- 83 = leading vehicle in the next lane (front);
- 84 = following vehicle in the next lane (rear).

Behaviour at lane crossing supports "next lane = left-adjacent lane, relative to the ego vehicle's current lane":
- 83 and 84 become 0 at the crossing in **100 %** of trials;
- 82 jumps by more than 5 m in 58 % of trials (re-referenced to the new lane).

**Zero contexts** (`gap_zero_context`; tags only, no zero is converted to a distance):

| Tag | Meaning | Channels |
|---|---|---|
| `zero_from_recording_start` | zero with no earlier finite value | 82: 22.5 %; 84: 29.0 % of samples |
| `zero_after_far_value` | zero after ≥ 20 m | 82: 30.3 %; 83: 4.2 %; 84: 3.0 % |
| `zero_after_lane_crossing` | zero starting at the crossing | 83: 12.3 %; 84: 7.5 % |
| `zero_handoff` | zero while the partner channel appears at a small distance | 83: 1.1 %; 84: 0.1 % |
| `zero_after_near_value` | zero after < 2 m, no handoff | 0.4–0.5 % |

**Observations:**
- **Range limit:** the maximum value is 250 m. 82 goes to 0 from 125–250 m, which fits a range limit or no-vehicle sentinel.
- **Handoffs:** 52 of 121 "lead-next < 2 m → 0" events are immediately followed by follow-next appearing at < 3 m. A vehicle passes from ahead to behind, so here zero is a role handoff, not a separation.
- **Negatives:** rare negative values (82: 170 samples; 84: 125) occur 20–30 s before lane crossing, outside the analysis windows.

**Zero semantics by class:**

| Possible meaning | Status |
|---|---|
| no vehicle / out of range | **supported** for far-value and recording-start zeros |
| no adjacent lane | **supported** after crossing |
| role handoff | **supported** where a handoff is detected |
| true zero separation | **cannot be excluded** for near-value zeros |
| clipped value | not observed (no pile-up at 250) |

**Overall: unresolved in general, context-tagged.** Only "value" samples are reported as gaps.

## 8. Descriptors

| Metric | Class | Reason |
|---|---|---|
| MS → steering onset | **B. PROVISIONAL** | authorship unverified; the value depends on the detector |
| steering onset → lane crossing | **B. PROVISIONAL** | inherits the onset caveats; lane crossing itself is validated |
| steering duration proxy | **C. BLOCKED** | no documented completion event; any end event would be invented |
| indicator lead/lag vs steering | **B. PROVISIONAL** | indicator channel undocumented |
| target-lane gap at steering onset | **B. PROVISIONAL** | lead-next is a value in 98 % of trials, median 33 m; follow-next only in 65 %, median 45 m; zeros unresolved |
| target-lane gap at lane crossing (last sample before) | **B. PROVISIONAL** | lead-next median 43 m; follow-next median 35 m (64 %) |
| hazard distance at steering onset | **A. VALIDATED** (station-consistent trials only) | median 90 m, IQR 69–109, n = 434; d0_n1 excluded (B); the reference point is undocumented |
| hazard distance at lane crossing | **A. VALIDATED** (station-consistent trials only) | median 43 m, IQR 26–58, n = 421 |

## 9. Repeated exposure

The model follows R2B: participant fixed intercepts, a linear exposure term, optional cell controls, and participant-clustered CR1 standard errors. Detection is stable enough for this: 491 of 492 onsets are found, and none is stereotyped. Results are associations, not learning.

| Outcome | Population | Slope (s/trial) | 95 % CI |
|---|---|---|---|
| MS → steering onset | all, cell controls | 0.001 | −0.045 to 0.047 |
| MS → steering onset | excluding exposure 1 | −0.018 | −0.083 to 0.047 |
| steering onset → lane crossing | all | 0.136 | −0.078 to 0.350 |
| steering onset → lane crossing | excluding exposure 1 | 0.194 | −0.053 to 0.440 |

**No clear linear association with repeated exposure**, with or without cell controls, and the result does not depend on exposure 1.

## 10. Relation to R3B (comparison only)

- **Timing:** TOR → steering onset has a median of 3.85 s (IQR 3.00–4.88). None of the onsets fall before the lower end of the R3B t1 assumption interval (1.15 s); 25 % fall inside [1.15, 3.0] s and 75 % after it. Lateral activity mostly begins **after** the t1 window assumed by the braking-only model.
- **Overlap:** the brake channel is above threshold at steering onset in 38 % of trials (12–61 % by cell). Brake and steering activity therefore **may overlap** in time. The brake channel is MIXED_OR_AMBIGUOUS (R4V), so this is channel co-activity, not driver co-activity.
- **Sufficiency:** this is **insufficient** for a combined recovery model. Braking authorship and magnitude are not identifiable. The steering onset is provisional. There is no completion event. The lateral geometry and escape-path clearance are not logged.

No combined score is produced, and nothing enters R3B.

## 11. Claim boundaries

- Descriptive timing only. No interval is a causal driver-response latency.
- Steering authorship stays PLAUSIBLE_BUT_UNVERIFIED.
- The indicator is not an intention time.
- Torque is not driver torque.
- Gap zeros are not distances.
- No synthesis.
