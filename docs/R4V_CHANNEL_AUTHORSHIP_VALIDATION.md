# R4V: D003 control-channel authorship validation

**Status:** 2026-09-24. Validation only. No synthesis, no model changes, and no substitution into R3B.
**Code:** `src/experiments/r4v_channel_authorship.py`.
**Outputs:** `results/R4V_channel_authorship/`, containing:
- `trial_features.csv`
- `cell_stereotypy.csv`
- `event_structure.csv`
- `summary.json`
- `provenance.json` (archive sha256 and git state)

**Tests:** `tests/test_r4v_channel_authorship.py`.
**Question:** is the signal behaviour consistent with the documented design intent that Manual_Start (MS) enables manual control? The answer is given per channel, without assuming that post-MS channels are driver-generated.

**Data:** 492 anchorable trials (TOR and MS both present), 57 participants, 9 scenario cells (`dX_nY`: density X, n-back Y), 20 Hz.

**Windows:**

| Window | Span |
|---|---|
| pre-TOR | [TOR−4, TOR−0.2) |
| TOR→MS | [TOR, MS) |
| immediately post-MS | [MS, MS+2) |
| later manual | [MS+2, handback) |
| after handback | [handback+1, handback+4) |

**Thresholds:**
- brake > 15, as in ingestion;
- steering-angle change > 0.05 rad relative to the value at MS;
- accelerator > 0.02.

**Methods (consistency checks, not authorship tests):**
- **Cell stereotypy:** an event is flagged in a cell when it occurs in ≥ 90 % of the cell's trials with IQR ≤ 0.10 s. A human latency is not expected to do this; a scripted one is.
- **Structure:** participant ICC(1) and cell η².
- **Coupling:** lagged brake → deceleration coupling. It shows consistency only; correlation is not authorship.

## 1. Channels examined

| Channel | Raw column | Data dictionary |
|---|---|---|
| brake | `[00].VehicleUpdate-brake` | documented ("brake force", N; the owners' paper speaks of pedal position) |
| accelerator | `[00].VehicleUpdate-accelerator` | documented (gas position 0–1) |
| steering-wheel angle | `[00].VehicleUpdate-steeringWheelAngle` | documented (rad) |
| steering torque | `[00].VehicleUpdate-steeringTorq` | **not documented** |
| mode/state flag | `[00].VehicleUpdate-state` | not documented |
| left indicator | `[00].VehicleUpdate-indicators` | **not documented**; "1 = left" is inferred from the documented left lane change |
| longitudinal acceleration | `[00].VehicleUpdate-accel.001` | documented; used only for the consistency check |
| hazard/gap | `Distance_to_Construction`, `Distance_to_Following_Vehicle`, `…Leading_Vehicle_Next_Lane`, `…Following_Vehicle_Next_Lane`; `roadAbscissa`, `roadId` | distances documented; zero semantics not documented |

## 2. Mode-state flag

`VehicleUpdate-state` is **2.0 in every sample of every trial**. It carries no mode or authority information. **Verdict: NOT_IDENTIFIABLE as authority evidence.** No logged flag marks the switch to manual mode; MS is known only from the event timestamp.

## 3. Behaviour before and after Manual_Start

### Brake

**Before TOR:** the brake is active in 26.6 % of trials.

**TOR→MS:** a brake onset occurs in 59.8 % of trials.
- The pattern is cell-structured: 0 % in d0_n1 and 96 % in d10_n0.
- In some cells the onset latency is near-constant relative to TOR:
  - d0_n0: 1.200 s, IQR 0.000;
  - d20_n0: 1.900 s, IQR 0.001;
  - d0_n2: 2.05 s, IQR 0.013.
- Cell η² is 0.76 and participant ICC(1) is −0.11.
- Brake → deceleration coupling has a median of 0.987.

These onsets are **scripted and vehicle-effective braking before MS**. By design this is not driver-effective.

**Across MS:**
- The brake is **already active at MS in 53.9 % of trials** (86–96 % in the d10 cells).
- The signal continues smoothly across the switch: the median largest sample step within ±0.2 s of MS is 1.27 units.
- It releases a median **0.95 s after MS** (IQR 0.80–1.10).
- Release timing is somewhat more MS-locked than TOR-locked (SD 1.17 s relative to MS vs 1.45 s relative to TOR).

Signal content that exists before MS therefore persists after MS. The first post-MS second of the brake channel is **not driver-only**.

**Clean post-MS onsets:**
- A clean onset is the first onset after MS, or after the straddling transient has released: n = 299, median 1.20 s after MS, IQR 0.53–2.13.
- These onsets are not cell-stereotyped (cell η² 0.05), but participant structure is absent (ICC(1) 0.007).
- The rule-level "brake onset after MS" is stereotyped at 0.05 s in all three d10 cells. That is the straddle: the value is already above threshold at the first post-MS sample.

**Coupling after MS:** the median is 0.86, which is consistent with a brake channel that decelerates the vehicle. The coupling cannot tell who commanded it.

### Accelerator

**Before TOR:**
- The accelerator is active in 100 % of trials, which is automation throttle.
- Release relative to TOR is cell-stereotyped in 6 of 9 cells (≈ 0.00–0.05 s, or 1.10 s in d0_n0; IQR ≤ 0.05 s), with cell η² 0.94.

**At MS:**
- The accelerator is active at MS in 24 % of trials, and in 86 % in d20_n0, where the rule-level post-MS onset is stereotyped at 0.05 s.
- It drops a median of 0.30 s after MS.

**After handback:** the accelerator is > 0.02 in 82.5 % of trials. Automation throttle resumes, as expected.

**Mode locking** (automation content present both before TOR and after handback in > 90 % of trials) is **not met**: 100 % before TOR, 82.5 % after handback. So a4 is not established.

### Steering-wheel angle

**Before TOR:**
- The angle is **cell-locked** (cell η² 0.995). Within a cell the pre-TOR mean angle is near-identical, for example:
  - 0.0747 rad, IQR 4e-6, in d0_n0;
  - 0.1587 rad in d0_n1;
  - ≈ 0 in d0_n2 and d10_n1.
- The wheel angle therefore follows scenario/automation-driven content while automation drives.

**At TOR:** a step of > 0.03 rad occurs in **whole cells only** (d0_n1, d10_n0, d20_n0: 100 %; d20_n1: 53 %; all others: 0 %).

**TOR→MS:** the angle is quiescent (median SD 0.0011 rad). It moves by > 0.05 rad in 0.8 % of trials.

**After MS:**
- Onset, measured as change from the MS value, has a median of **2.00 s** (IQR 1.15–3.16; n = 492).
- It is not cell-stereotyped (cell η² 0.09; cell IQRs 1.16–3.45 s).
- Participant ICC(1) is 0.156.

**After handback:** the mean angle is within 0.005 rad of its cell's pre-TOR median in 14.6 % of trials (within 0.02 rad in 23.6 %). There is no general return to the pre-TOR cell value; road position differs after the lane change, so this is not interpreted further.

### Steering torque

**Before TOR:** there is an offset (|mean| > 0.1 in 61 % of trials).

**TOR→MS:** about 0 (|mean| < 0.1 in 65 %).

**After MS:** large variance.

The mode-locking criterion (both > 90 %) is not met. The channel is undocumented, so there is no way to tell driver torque from force feedback.

### Left indicator

- Never on before MS (0 of 492 trials).
- Onset a median of 2.05 s after MS (IQR 1.40–3.25; n = 372).
- ICC(1) 0.19, cell η² 0.03.
- Precedes lane crossing in 95.6 % of trials.

### Near Manual_Stop

After handback, automation throttle resumes (accelerator: 82.5 %). This is consistent with a switch back to automated mode. Torque and angle were only summarised by their means after handback; no return to automation levels is claimed for them. Handback is not recovery completion (unchanged from R4).

## 4. Brake: onset and magnitude, kept separate

**Onset: MIXED_OR_AMBIGUOUS.**
- Before MS: scripted automation braking.
- At MS: automation braking straddles the switch in 54 % of trials.
- Clean post-transient onsets (median MS + 1.20 s) are not cell-scripted, but show no participant structure. They also happen after automation braking has already slowed the vehicle, so they are not braking-from-cruise onsets.

**Magnitude: NOT_IDENTIFIABLE as human braking strength.**
- The unit conflict is unresolved (dictionary: force in N; owners' paper: pedal position).
- The automation-brake content straddles MS.
- The value 400 is reached in 0.6 % of trials, a possible cap.

**R3B t1 and u are not replaced by any measured quantity** (see §8).

## 5. Steering onset and lane crossing

These are three different events and are reported separately:

| Interval | Median | IQR | n |
|---|---|---|---|
| MS → steering-angle change onset | 2.00 s | 1.15–3.16 s | 492 |
| steering-angle change onset → validated lane crossing | 2.35 s | 1.95–3.20 s | 478 |

**Lane crossing is not steering onset.** The onset precedes the crossing in 95.9 % of trials. The onset is a *wheel-angle change* after MS; its authorship is classified in §7.

## 6. Hazard and target-lane reconstruction (logged channels only)

**Hazard distance:** `Distance_to_Construction` at TOR has a median of 177.5 m. This is consistent with the scenario TTC at TOR, but that is only a check of a documented relation.

**Hazard station:**
- `roadAbscissa + distance` varies within trials (median SD 58.5 m).
- `roadAbscissa − distance` varies less (median SD 7.8 m), but its p95 is > 100 m.
- d(distance)/d(abscissa) has a median of 0.76, not ±1.

The distance is not a simple along-road offset from a fixed station in the road coordinate. **Status: partially reconstructable.** Distance at a time point is usable. A fixed hazard station in road coordinates is not established.

**Lateral geometry and lane width:** not logged, and not inferred.

**Gap channels:**
- No negatives and no missing values in the analysed windows. **Erratum (R4V-D):** over full trials there are rare negatives (channel 82: 170 samples; 84: 125; all 20–30 s before lane crossing) and 0.24 % missing samples. See `docs/R4V_STEERING_SEQUENCE.md` §7.
- Zeros are frequent. `Distance_to_Following_Vehicle` is zero in 91–100 % of samples in density-0 cells and in 12–78 % elsewhere. This is compatible with "no vehicle present", but not documented.
- `Distance_to_Leading_Vehicle_Next_Lane` is zero in 11–22 % of samples even in density-0 cells.
- Transitions to zero come from tens of metres (median prior value 41–155 m), which is a sentinel-like jump.
- Non-zero minima reach 0.0001–0.42 m.

**Zero semantics remain ambiguous.** Zero may mean no vehicle, out of sensor range, or contact. **Status: NOT resolved.** The target-lane gap history is usable only for non-zero values, and their meaning is not validated.

## 7. Authorship classification

### Criteria

These were stated before the run, in `AUTHORSHIP_CRITERIA`:

| Criterion | Meaning |
|---|---|
| a1 | documented as a control input |
| a2 | no cell-locked stereotyped post-MS activity |
| a3 | post-MS onset has participant ICC(1) > 0.1 and cell η² < 0.5 |
| a4 | automation-like content is absent between MS and handback (mode locking) |
| a5 | vehicle response is consistent (consistency only) |

**Classes:**

| Class | Condition |
|---|---|
| A. DRIVER_AUTHORSHIP_SUPPORTED | a1–a5 all hold |
| B. PLAUSIBLE_BUT_UNVERIFIED | a1 and a2 hold, but a3 or a4 is not established |
| C. MIXED_OR_AMBIGUOUS | a2 fails, or evidence conflicts |
| D. NOT_IDENTIFIABLE | a1 fails and behaviour cannot discriminate |

**Post-rule review (disclosed as post hoc):** the review was written after the rule output was seen. It may only **downgrade** a verdict; the code rejects an upgrade.

### Verdicts

| Channel | Rule verdict | Final | Reason |
|---|---|---|---|
| brake (onset) | C | **C. MIXED_OR_AMBIGUOUS** | stereotyped post-MS activity in the d10 cells (straddling automation braking); clean onsets show no participant structure |
| brake (magnitude) | — | **D. NOT_IDENTIFIABLE** | unit conflict, straddle, possible cap |
| accelerator | C | **C. MIXED_OR_AMBIGUOUS** | automation throttle straddles MS (d20_n0 86 %), shows cell-stereotyped release, and resumes after handback |
| steering-wheel angle | A | **B. PLAUSIBLE_BUT_UNVERIFIED** | review downgrade: the channel carries cell-locked scenario/automation content while automation drives, and changes at TOR in whole cells, under undocumented logic; ICC 0.156 is only marginally above 0.1. Post-MS onset is not stereotyped, precedes lane crossing and matches the indicator |
| steering torque | D | **D. NOT_IDENTIFIABLE** | undocumented; driver torque vs force feedback cannot be distinguished |
| left indicator | A | **B. PLAUSIBLE_BUT_UNVERIFIED** | review downgrade: not in the dictionary (a1 fails). Behaviour is corroborative only |
| state flag | — | **D. NOT_IDENTIFIABLE** | constant 2.0 |

**No channel reaches class A.**

## 8. Consequences for R2, R3B and steering

| Blocker | Outcome |
|---|---|
| **B17 (channel authorship)** | **Partly resolved, negatively.** Brake and accelerator are demonstrably *not* driver-only across MS. Steering angle is B. The blocker is now characterised rather than open, but not removed. |
| **B7 (MS as authority transfer)** | **Partly supported.** The indicator never comes on before MS, steering is quiescent TOR→MS, and throttle and angle return after handback, all consistent with a manual-mode window. But longitudinal automation content continues for about 1 s after MS, so MS does not mark a clean longitudinal authority boundary. |
| **R2 (t_button)** | Unchanged. It is the HMI switch latency, not an effective-control latency. |
| **R3B t1** | **Not substituted.** The measured clean brake onset (MS + 1.20 s, class C) is not effective braking from cruise: automation braking has already acted. t1 stays an explicit assumption interval. |
| **R3B u** | Stays a capability bound (u = 1); magnitude is class D. |
| **Steering** | A descriptive steering-onset timeline is now possible at class B, labelled "wheel-angle change onset after MS (authorship plausible, unverified)". A steering-*recoverability* analysis is still blocked by lateral geometry, lane width and gap zero semantics. |
| **Hazard (B10) and gaps (B5)** | Hazard distance usable per time point; station partial; gap zeros unresolved. |

**R4 cross-layer links:** unchanged. `t_button → t1`, `first channel activity → first human input` and `first human input → effective control` stay NOT IDENTIFIABLE. `lane-change onset → steering recovery time` stays PARTIALLY IDENTIFIED. The steering-onset component now has a class-B descriptive measurement, but the authorship and geometry parts are still missing.

## 9. Claim boundaries

- No channel is claimed to be driver-generated.
- Correlation and coupling are used as consistency checks, not as evidence of authorship.
- No probability, safety or causal statement is made.
- No synthesis is started.
- Semantics of the undocumented channels (torque, indicator, state, gap zeros) were not filled in from general simulator knowledge.
