# H1 Operational Measurement Ledger: Empirical Takeover Quantities & Epistemic Specification

> **R2A NOTICE (2026-09-22).** D003 accelerator, brake and steering channels are not driver-only channels (blocker B17: structured, scenario-cell-specific changes within 0.3 s of TOR). All human first-input quantities in this document (`T_first`, first brake/steering input, brake-first vs steer-first, negative handover lag, brake-rise latency, driver-attributed maximum braking or steering) are **INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS**. They are preserved for audit history; see `results/HISTORICAL_OUTPUTS_MANIFEST.md` and `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §9.

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This ledger is retained (it is referenced by tests) but several entries are superseded: `T_stable` is withdrawn as a human stabilisation metric; `DERIVED_COLLISION_PROXY` is withdrawn; brake-reapplication and full-record steering-reversal counts are invalid as computed (windows include automation); `T_first_brake` and `T_first_ctrl` depend on unresolved brake-channel semantics; `T_manual_start` authority semantics are unresolved; `Time_Lane_Change` needs per-trial validation and is not a `lane_id` 2→3 flip in general. "Allowed Wording" entries for withdrawn quantities no longer apply. D003 blockers and the dataset owners' prior analyses: `research/data_matrix/D003_KNOWN_BLOCKERS.md`. Measurement rules: `docs/OBSERVATION_LAYER.md`. Status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Document Version:** 1.0  
**Phase:** Phase 2B-1.2 Measurement Semantics & Identification Cleanup  
**Dataset:** TU Delft Conditionally Automated Driving Takeover Dataset (D003; $N=513$ trials, 57 participants)  
**Classification:** Epistemic Definition Ledger & Claim Boundaries  

---

## 1. Overview & Purpose

This ledger defines the operational measurement semantics, mathematical detectors, signal provenance, causal constraints, and permissible wording for all empirical quantities extracted in Phase 2B-1. Its primary objective is to prevent epistemic drift, category errors (e.g., conflating human motor input with physical plant response, or uncalibrated detector latency with mechanical actuator lag), and unwarranted causal assertions ahead of Phase 2B-2 model-class comparison.

---

## 2. Summary Matrix: The 12 Core Quantities

| # | Quantity Symbol / Key | Conceptual Meaning | Primary Source Signal | Direct / Derived / Proxy | Sensitivity Status | Causal Ordering Constraint |
| :-: | :--- | :--- | :--- | :-: | :-: | :--- |
| **1** | $T_{\text{request}}$ | TOR alert issuance | Simulator event channel 72 | Direct | Fixed Ground-Truth | Root Anchor ($t = 0$) |
| **2** | $T_{\text{manual\_start}}$ | Button-press acknowledgement | Simulator event channel 73 | Direct | Fixed Ground-Truth | $T_{\text{manual\_start}} \ge T_{\text{request}}$ |
| **3** | $T_{\text{first\_brake}}$ | First detected brake input | Continuous brake force (N) | Direct | Moderately Sensitive | $T_{\text{first\_brake}} \ge T_{\text{request}}$ |
| **4** | $T_{\text{first\_steer}}$ | First detected steer input | Continuous wheel angle (rad) | Direct | Moderately Sensitive | $T_{\text{first\_steer}} \ge T_{\text{request}}$ |
| **5** | $T_{\text{first\_ctrl}}$ | First detected human control input | $\min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$ | Derived | Robust ($0.80 - 1.40\text{ s}$) | $T_{\text{first\_ctrl}} \ge T_{\text{request}}$ |
| **6** | $T_{\text{effective\_dec}}$ | First deceleration response onset | Longitudinal acceleration ($a_x$) | Derived | Moderately Sensitive | $T_{\text{effective\_dec}} \ge T_{\text{first\_brake}}$ |
| **7** | $T_{\text{effective\_lat}}$ | Effective lateral-response onset | Lateral acceleration ($a_y$) | Derived | Highly Sensitive | $T_{\text{effective\_lat}} \ge T_{\text{first\_steer}}$ |
| **8** | $T_{\text{clear}}$ | Acute hazard clearance instant | Obstacle distance & speed | Derived | Robust ($8.95\text{ s}$ median) | $T_{\text{clear}} > T_{\text{first\_ctrl}}$ |
| **9** | $T_{\text{stable}}$ | Behavioral & control stabilization | Steering speed & brake rate | Derived | Robust to Anchor ($21.5 - 23.3\text{ s}$) | Search start $\ge t_{\text{anchor}}$ |
| **10** | `DERIVED_COLLISION_PROXY` | Hazard impact failure proxy | Obstacle distance, speed, lane | Proxy | Robust ($N=6$, 1.17%) | Acute encounter phase |
| **11** | Steering Reversal | Corrective steering direction change | Filtered wheel angle ($2\text{ Hz}$) | Derived | Highly Threshold-Dependent | Post-TOR manual phase |
| **12** | Brake Reapplication | Secondary closed-loop braking pulse | Continuous brake force (N) | Derived | Robust across prominences | $t > T_{\text{first\_brake}}$ |

---

## 3. Comprehensive Quantity Specifications

```
================================================================================
QUANTITY 1: T_request
================================================================================
Conceptual Meaning:
    The precise simulation timestamp at which the automated system withdraws
    operational authority and issues the multimodal Takeover Request (TOR)
    warning (auditory chime + visual dashboard display).

Observed Source Signal:
    Simulator export channel: [72 (Time/Time_Takeover_Request)].ExportChannel-val
    Mapped to DataFrame column: "TOR_request".

Operational Detector:
    First timestamp where the export channel transitions from NaN to a valid
    floating-point scalar.

Threshold:
    Non-null float value.

Persistence:
    Instantaneous discrete event (single timestamp).

Sampling Resolution:
    20 Hz nominal telemetry rate (Δt = 50 ms time bins).

Causal Ordering Constraint:
    Root reference instant for all subsequent human and vehicle actions:
        t >= T_request for all reaction and response metrics.
    In 15 of 513 trials, manual authority was preemptively resumed prior to
    scheduled TOR issuance; these trials lack T_request.

Direct / Derived / Proxy:
    Direct simulator system log event.

Sensitivity Status:
    Insensitive. Exact ground-truth timestamp recorded by the simulation core.

Allowed Wording:
    - "Takeover Request (TOR) issuance timestamp"
    - "System alert onset"
    - "TOR trigger instant"

Prohibited Overclaim:
    - Must NOT be claimed as the instant of driver conscious perception
      (sensory transduction, cortical processing, and cognitive appraisal
      introduce an unmeasured neuro-sensory latency).
```

```
================================================================================
QUANTITY 2: T_manual_start
================================================================================
Conceptual Meaning:
    The timestamp when the participant depresses the physical manual takeover
    acknowledgement button located on the steering wheel spoke.

Observed Source Signal:
    Simulator export channel: [73 (Time/Time_Manual_Start)].ExportChannel-val
    Mapped to DataFrame column: "manual_start".

Operational Detector:
    First timestamp where the export channel transitions from NaN to a valid
    floating-point scalar.

Threshold:
    Non-null float value.

Persistence:
    Instantaneous discrete event.

Sampling Resolution:
    20 Hz nominal telemetry rate (Δt = 50 ms time bins).

Causal Ordering Constraint:
    T_manual_start >= T_request (in scheduled TOR trials).
    Does NOT constrain human motor pedal or steering interaction:
    in 80.7% of valid TOR trials, human motor input precedes button depression.

Direct / Derived / Proxy:
    Direct simulator system log event (digital switch actuation).

Sensitivity Status:
    Insensitive. Exact ground-truth switch trigger.

Allowed Wording:
    - "Manual takeover button-press timestamp"
    - "Tactile acknowledgement switch event"
    - "Manual authority transition button trigger"

Prohibited Overclaim:
    - Must NOT be equated with the onset of physical human control or takeover
      initiation.
    - Must NOT be described as plant authority transfer instant without
      noting that mechanical wheel and pedal actions occur prior to it.
```

```
================================================================================
QUANTITY 3: T_first_brake
================================================================================
Conceptual Meaning:
    The earliest detectable onset of human foot contact applying significant
    force to the brake pedal following TOR issuance.

Observed Source Signal:
    Continuous brake pedal force channel:
    [00].VehicleUpdate-brake (measured in Newtons, N).
    Mapped to DataFrame column: "brake_force".

Operational Detector:
    min { t >= T_request | F_brake(t) > F_th }

Threshold:
    Nominal: F_th = 15.0 N.
    Audited sensitivity range: F_th in [5.0, 10.0, 15.0, 20.0, 30.0] N.

Persistence:
    1 sample (50 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    T_first_brake >= T_request.

Direct / Derived / Proxy:
    Direct physical measurement from the simulator pedal load cell.

Sensitivity Status:
    Moderately sensitive to threshold:
    Median latency shifts from 0.45 s at 5 N to 1.15 s at 15 N and 1.20 s at 30 N.

Allowed Wording:
    - "First detected brake input"
    - "Brake pedal contact onset (at 15 N threshold)"
    - "Initial brake pedal force exceedance"

Prohibited Overclaim:
    - Must NOT be described as braking deceleration onset.
    - Must NOT be attributed to vehicle brake line pressure build-up or
      pad-rotor contact.
```

```
================================================================================
QUANTITY 4: T_first_steer
================================================================================
Conceptual Meaning:
    The earliest detectable voluntary hand input deflecting the steering wheel
    away from the pre-TOR automated lane-keeping baseline.

Observed Source Signal:
    Continuous steering wheel angle channel:
    [00].VehicleUpdate-steeringWheelAngle (radians).
    Mapped to DataFrame column: "steering_angle".

Operational Detector:
    min { t >= T_request | |delta_sw(t) - delta_base| > delta_th }
    where delta_base is the mean steering angle during the 4.0 s pre-TOR window.

Threshold:
    Nominal: delta_th = 0.05 rad (2.86 deg).
    Audited sensitivity range: delta_th in [0.02, 0.03, 0.05, 0.07] rad
    (1.15 deg to 4.01 deg).

Persistence:
    1 sample (50 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    T_first_steer >= T_request.

Direct / Derived / Proxy:
    Direct physical measurement from the simulator steering wheel optical encoder.

Sensitivity Status:
    Moderately sensitive to threshold:
    Median latency shifts from 0.45 s at 0.02 rad to 1.125 s at 0.05 rad.

Allowed Wording:
    - "First detected steering wheel deflection"
    - "Steering input onset (at 0.05 rad / 2.86 deg threshold)"
    - "Initial steering wheel angle deviation"

Prohibited Overclaim:
    - Must NOT be equated with tire slip angle generation or front-wheel angle
      displacement.
    - Must NOT be called vehicle lateral motion onset.
```

```
================================================================================
QUANTITY 5: T_first_ctrl
================================================================================
Conceptual Meaning:
    The earliest detected intentional human motor control action on either
    primary vehicular control interface (brake pedal or steering wheel).

Observed Source Signal:
    min(T_first_brake, T_first_steer) under nominal thresholds (15 N, 0.05 rad).

Operational Detector:
    min { t >= T_request | (F_brake(t) > 15.0 N) OR (|delta_sw(t) - delta_base| > 0.05 rad) }

Threshold:
    F_brake > 15.0 N OR |Delta delta_sw| > 0.05 rad.

Persistence:
    1 sample (50 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    Strictly precedes physical plant response within the scheduled-TOR analysis set (N = 498):
        T_request <= T_first_ctrl <= T_effective
    Preemptive takeovers (N = 15 trials, 2.92%) where human control action or manual button
    press preceded scheduled TOR are separately classified and excluded from post-TOR causal metrics.

Direct / Derived / Proxy:
    Derived compound metric from direct primary sensor channels.

Sensitivity Status:
    Robust across defensible operational thresholds (median spans 0.80 s to 1.40 s;
    nominal median = 1.125 s, IQR = 0.850 s).

Allowed Wording:
    - "First detected human control input"
    - "Initial human motor action onset"
    - "Earliest active control intervention"

Prohibited Overclaim:
    - Must NOT be called "physical plant disturbance".
    - Must NOT be conflated with vehicle deceleration or lateral movement.
    - Must NOT be claimed as instantaneous control authority handover.
```

```
================================================================================
QUANTITY 6: T_effective_dec
================================================================================
Conceptual Meaning:
    The first subsequent longitudinal vehicle deceleration response satisfying
    an operational detection threshold causally following human brake application.

Observed Source Signal:
    Longitudinal vehicle acceleration:
    [00].VehicleUpdate-accel.001 (m/s^2).
    Mapped to DataFrame column: "longitudinal_acceleration".

Operational Detector:
    min { t >= T_first_brake | a_x(t) <= a_x(T_first_brake) - Delta a_{x,th}
          for k consecutive samples }

Threshold:
    Nominal: Delta a_{x,th} = 0.5 m/s^2, persistence k = 2 samples (100 ms).
    Audited sensitivity range: Delta a in [0.3, 0.5, 0.8, 1.0] m/s^2;
    persistence k in [1, 2, 3] samples (50 ms, 100 ms, 150 ms).

Persistence:
    2 consecutive samples (100 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization). Minimum resolvable interval is 50 ms.

Causal Ordering Constraint:
    STRICTLY T_effective_dec >= T_first_brake.
    Unconstrained search starting at T_request falsely triggers in 59.8% of trials
    due to natural automated throttle roll-off and aerodynamic drag (-0.6 m/s^2).

Direct / Derived / Proxy:
    Derived vehicle dynamic response metric from simulation vehicle state node.

Sensitivity Status:
    Moderately threshold-dependent:
    Median response latency post-input spans 50 ms (at 0.3 m/s^2) to 200 ms
    (at 1.0 m/s^2); nominal median = 100 ms (IQR = 950 ms).

Allowed Wording:
    - "Longitudinal vehicle response onset under operational detector (Delta a_x <= -0.5 m/s^2)"
    - "The observed D003 longitudinal response-onset interval is consistent with
       the Phase-1 modeled response-delay scale under the current operational detector"
    - "Causally constrained deceleration onset"

Prohibited Overclaim:
    - Must NOT be called "direct physical validation of hydraulic brake latency".
    - Must NOT be described as purely mechanical brake dead time (20 Hz sampling
      imposes +/- 50 ms binning uncertainty; D003 is a fixed-base driving simulator).
    - Validation level must be explicitly stated as Parameter-Level Consistency (V1).
```

```
================================================================================
QUANTITY 7: T_effective_lat
================================================================================
Conceptual Meaning:
    The first subsequent lateral vehicle acceleration response satisfying an
    operational detection threshold causally following human steering input.

Observed Source Signal:
    Lateral vehicle acceleration:
    [00].VehicleUpdate-accel.002 (m/s^2).
    Mapped to DataFrame column: "lateral_acceleration".

Operational Detector:
    min { t >= T_first_steer | |a_y(t) - a_y(T_first_steer)| >= Delta a_{y,th}
          for k consecutive samples }

Threshold:
    Nominal: Delta a_{y,th} = 0.4 m/s^2, persistence k = 2 samples (100 ms).
    Audited sensitivity range: Delta a in [0.2, 0.4, 0.6] m/s^2;
    persistence k in [1, 2, 3] samples.

Persistence:
    2 consecutive samples (100 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    STRICTLY T_effective_lat >= T_first_steer.

Direct / Derived / Proxy:
    Derived vehicle dynamic response metric.

Sensitivity Status:
    Highly threshold-dependent:
    Median delay post-steer spans 0.90 s (at 0.2 m/s^2) to 1.90 s (at 0.4 m/s^2)
    and 2.80 s (at 0.6 m/s^2).

Allowed Wording:
    - "Threshold-defined task-level effective lateral-response interval"
    - "Task-level lateral acceleration onset interval"
    - "Interval to operational lateral acceleration threshold exceedance depending on steering trajectory, threshold, persistence, and 20 Hz sampling"

Prohibited Overclaim:
    - Must NOT be termed "actuator delay" or "steering system dead time".
    - Must NOT be mechanistically attributed to front-wheel yaw accumulation, tire mechanics,
      steering-rack dynamics, or chassis inertia (unidentifiable from D003 telemetry).
    - Must NOT be treated as a pure hardware transport delay.
```

```
================================================================================
QUANTITY 8: T_pass (Obstacle Longitudinal Station Passage)
================================================================================
Conceptual Meaning:
    The geometric spatial instant at which the front bumper / reference point of
    the ego-vehicle translates longitudinally past the stationary construction
    hazard coordinate (d_obstacle <= 0.0 m).

    CRITICAL EPISTEMIC AND METHODOLOGICAL DISTINCTIONS:
    1. GEOMETRIC PASSAGE VS. SAFE CLEARANCE:
       This event denotes longitudinal coordinate translation only. It does NOT
       establish safe obstacle clearance or successful evasive bypass.
       In D003 source telemetry, the obstacle is recorded solely via 1D longitudinal
       distance ([85 (Distance/Distance_to_Construction)]); there are NO recorded
       lateral obstacle coordinates, barrier bounding polygons, or vehicle-obstacle
       lateral clearance margins.
       Consequently, safe clearance (T_safe_clear) is NOT IDENTIFIABLE from source
       data without imposing ungrounded, arbitrary lateral assumptions.
    2. COLLISION-PROXY EMPIRICAL CROSS-CHECK:
       [AUDIT 2026-09-22: WITHDRAWN. The collision proxy itself is invalid: 12 TOR trials
       pass the hazard station in their TOR lane vs 6 labels, overlap 4; 2 labelled
       collisions were in the adjacent lane at the hazard station.]
       An audit of all 6 collision-failure trials (DERIVED_COLLISION_PROXY) reveals
       that 100% (6/6) of collision trajectories crossed the obstacle longitudinal
       station and falsely satisfied the legacy "clearance" condition
       (d_obstacle <= 0 and v_x > 10 m/s), despite 5/6 never changing lanes and
       colliding directly into the virtual hazard.
    3. REMOVAL OF AD-HOC SPEED THRESHOLD:
       The legacy condition required v_x > 10 m/s. This arbitrarily delayed the
       station passage timestamp in 47 trials where drivers decelerated below 10 m/s
       during evasion and reaccelerated later. T_pass removes this ad-hoc speed rule,
       measuring the true physical station passage instant.

Observed Source Signal:
    Longitudinal distance to obstacle:
    [85 (Distance/Distance_to_Construction)].ExportChannel-val (meters).

Operational Detector:
    min { t >= T_request | d_obstacle(t) <= 0.0 m }

Threshold:
    d_obstacle <= 0.0 m.

Persistence:
    1 sample (50 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    T_pass > T_first_ctrl.
    In successful evasive trials with lane change:
        T_request < T_first_ctrl < Time_Lane_Change < T_pass < T_stable.
    (Note: Time_Lane_Change corresponds to discrete simulator lane-boundary crossing,
    as defined in data dictionary Row 44, not steering onset or maneuver completion).
    [AUDIT 2026-09-22: the dictionary says only "the time when the car changed to the
    left lane during takeover"; the "Row 44 / lane_id 2->3" description is not in it.
    Lane numbering varies by road (2->3, 6->5, 7->6); per-trial validation required.]

Direct / Derived / Proxy:
    Derived kinematic geometric longitudinal event.

Sensitivity Status:
    Robust. Median = 8.950 s post-TOR (IQR = 3.300 s across all 498 valid TOR trials).

Allowed Wording:
    - "Obstacle longitudinal station passage timestamp"
    - "Geometric obstacle longitudinal coordinate crossing (T_pass)"
    - "Longitudinal hazard station passage"

Prohibited Overclaim:
    - Must NOT be called "safe clearance", "hazard clearance", or "obstacle bypass".
    - Safe clearance is NOT IDENTIFIABLE from D003 telemetry.
    - Longitudinal passage must NOT be interpreted as evasive safety success (crashing
      vehicles also pass the obstacle station).
    - Must NOT be conflated with behavioral or control stabilization (T_stable).
```

```
================================================================================
QUANTITY 9: T_stable
================================================================================
Conceptual Meaning:
    The instant in time after evasive maneuver execution where driver control
    rates and vehicle dynamic states settle into steady-state highway cruising.

Observed Source Signal:
    Continuous steering wheel speed: [00].VehicleUpdate-steeringWheelSpeed (rad/s).
    Derivative of brake force: d/dt(brake_force) (N/s).

Operational Detector:
    min { t >= t_anchor | |omega_sw(t)| <= omega_th AND |dF_brake/dt| <= r_th
          continuously for persistence window tau_p }

Threshold:
    Nominal: omega_th = 0.05 rad/s (2.86 deg/s), r_th = 20.0 N/s, tau_p = 1.5 s.
    Audited rate ranges: omega_th in [0.03, 0.05, 0.08] rad/s;
    r_th in [10.0, 20.0, 30.0] N/s; tau_p in [1.0, 1.5, 2.0] s.

Persistence:
    1.5 s (30 consecutive samples at 20 Hz).

Sampling Resolution:
    20 Hz (Δt = 50 ms quantization).

Causal Ordering Constraint:
    Search anchor t_anchor must be placed post-reaction (t_anchor >= T_first + 1.0 s,
    T_pass, or Time_Lane_Change) to prevent false detection during passive delay.

Direct / Derived / Proxy:
    Derived multi-channel kinematic settling metric.

Sensitivity Status:
    [AUDIT 2026-09-22: WITHDRAWN AS A HUMAN METRIC. ~81% of nominal T_stable values occur
    after Time_Manual_Stop (driver returned control to automation). Within the human-control
    window only ~18% of trials settle. "Robust", "negligible censoring" and the anchor
    spans below are artifacts of a window that extends into automation.]
    Robust across search anchors (nominal medians = 22.18 s to 22.95 s across all 5 audited
    anchors: T_first + 1.0s [22.18s], T_first + 2.0s [22.47s], T_first + 3.0s [22.55s],
    Time_Lane_Change [22.55s], T_pass [22.95s]).
    Span across Subset A (T_first + 2.0s, T_first + 3.0s, Time_Lane_Change) is only 0.08 s (22.47s - 22.55s).
    Span across Subset B (Subset A + T_pass) is 0.48 s (22.47s - 22.95s).
    Complete 5-anchor span (including T_first + 1.0s) is 0.78 s (22.18s - 22.95s).
    Right-censoring is negligible (<= 0.4% within 3 s of record end).
    Moderately sensitive to persistence duration (19.4 s at 1.0 s; 24.2 s at 2.0 s under nominal rates).

Allowed Wording:
    - "Post-takeover control stabilization latency"
    - "Kinematic settling timestamp under candidate operational criteria"
    - "Steady-state cruising recovery time"

Prohibited Overclaim:
    - Must NOT be claimed as an absolute physiological constant.
    - Must NOT be described as independent of road geometry or traffic context.
```

```
================================================================================
QUANTITY 10: DERIVED_COLLISION_PROXY
================================================================================
Conceptual Meaning:
    A derived classification indicating that the vehicle penetrated the spatial
    zone of the stationary construction hazard at significant speed without
    executing a successful evasive maneuver.

Observed Source Signal:
    Distance to obstacle: [85 (Distance/Distance_to_Construction)].ExportChannel-val.
    Speed: [00].VehicleUpdate-speed.001.
    Lane position: [00].VehicleUpdate-roadInfo-laneId.0 and channel 78.

Operational Detector:
    d_obstacle <= 0.0 m AND v_x > 3.0 m/s while remaining in hazard lane (lane <= 2)
    or where lane change occurs after obstacle coordinate.

Threshold:
    d_obstacle <= 0.0 m, v_x > 3.0 m/s.

Persistence:
    1 sample (50 ms).

Sampling Resolution:
    20 Hz (Δt = 50 ms).

Causal Ordering Constraint:
    Evaluated over the acute hazard encounter window (T_request to T_request + 15 s).

Direct / Derived / Proxy:
    PROXY. No direct crash or contact switch exists in the D003 telemetry.

Sensitivity Status:
    Robust. Identifies exactly 6 trials (1.17% of 513 trials).

Allowed Wording:
    - "DERIVED_COLLISION_PROXY"
    - "Derived collision failure proxy"
    - "Estimated obstacle impact event based on spatial-speed threshold"

Prohibited Overclaim:
    - Must NOT be called "recorded collision ground truth" or "physical crash sensor trigger".
    - Must NOT imply that physical vehicle deformation or simulator crash physics were logged.
```

```
================================================================================
QUANTITY 11: Steering Wheel Reversals (Amplitude-Hysteresis)
================================================================================
Conceptual Meaning:
    A counted sequence of significant direction changes in steering wheel angle,
    filtered to remove voluntary micro-tremor and sensor noise, capturing active
    closed-loop lateral path correction.

Observed Source Signal:
    Steering wheel angle filtered with a 2nd-order zero-phase Butterworth filter
    at 2.0 Hz cutoff.

Operational Detector:
    Project operational amplitude-hysteresis steering-reversal detector
    (methodological precedent: McLean & Hoffmann 1975):
    Commits to an extremum (peak/valley) only after the steering angle reverses
    by at least the hysteresis gap threshold.

Threshold:
    Nominal gap threshold: 2.0 deg (0.035 rad).
    Audited sensitivity range: 1.0 deg, 2.0 deg, 3.0 deg, 5.0 deg.

Persistence:
    Hysteresis state-transition rule.

Sampling Resolution:
    20 Hz raw data, filtered at 2.0 Hz.

Causal Ordering Constraint:
    Evaluated in acute evasive window (T_req to T_req + 8.0 s) and full manual phase.

Direct / Derived / Proxy:
    Derived signal-processing metric.

Sensitivity Status:
    Highly sensitive to signal filtering and hysteresis threshold:
    Raw zero-crossings yield 70.5 reversals; 2 Hz filtered 2.0 deg hysteresis
    yields median 2.0 acute reversals (IQR = 2.0) and 13.0 full-trial reversals.

Allowed Wording:
    - "Project operational amplitude-hysteresis steering-reversal detector (2.0 deg gap, 2 Hz low-pass filter)"
    - "Steering reversals detected via McLean & Hoffmann (1975) algorithmic precedent"
    - "Directional steering control frequency and wheel movement oscillation"

Prohibited Overclaim:
    - Must NOT claim standardized status under SAE J2944 (unless specific section/table applies).
    - Must NOT be referred to as an "ISO gap-threshold algorithm" (no ISO standard
      defines this specific algorithm name).
    - Must NOT claim that reversals represent conscious cognitive decisions or deliberate
      re-planning stages; counting reversals measures directional steering control frequency.
```

```
================================================================================
QUANTITY 12: Brake Reapplication
================================================================================
Conceptual Meaning:
    A discrete event indicating that the driver, having initiated braking and
    subsequently relaxed pedal force, applied a secondary or tertiary brake force
    pulse during the recovery trajectory.

Observed Source Signal:
    Continuous brake pedal force: [00].VehicleUpdate-brake (N).

Operational Detector:
    Topographic peak/valley detection (scipy.signal.find_peaks):
    Identifies valleys where F_brake drops below 20.0 N followed by subsequent
    force rise exceeding 30.0 N with prominence >= 10.0 N.

Threshold:
    Prominence >= 10.0 N, minimum separation = 0.5 s (10 samples).
    Audited prominence range: [5.0, 10.0, 15.0, 20.0] N.

Persistence:
    10 samples (0.5 s) minimum peak-to-peak distance.

Sampling Resolution:
    20 Hz (Δt = 50 ms).

Causal Ordering Constraint:
    Occurs strictly after first brake application: t > T_first_brake.

Direct / Derived / Proxy:
    Derived metric from continuous physical load cell telemetry.

Sensitivity Status:
    Robust across prominence thresholds (median = 2.0 to 4.0 reapplications;
    68.3% of trials exhibit >= 1 reapplication).

Allowed Wording:
    - "Secondary brake force reapplications"
    - "Intermittent closed-loop brake force modulation"
    - "Multi-pulse braking behavior"

Prohibited Overclaim:
    - Must NOT be claimed as proof of ABS cycling or hydraulic pressure release.
    - Must NOT be asserted as panic pumping without modeling driver workload state.
```

---

## 4. Epistemic Protocol for Phase 2B-2

All future analyses, model-class comparisons, and manuscript texts must adhere to the boundaries specified in this ledger:
1. **Human Input vs. Plant Response:** Never label $T_{\text{first\_ctrl}}$ as plant disturbance; never label $T_{\text{effective\_lat}} - T_{\text{first\_steer}}$ as actuator delay.
2. **Architecture Neutrality:** Describe Phase-1 $t_2$ as *vehicle / braking response delay*; do not attribute D003 simulator response latencies to hydraulic mechanisms.
3. **Calibrated Validation Status:** Characterize longitudinal timing consistency with Phase 1 as **Parameter-Level Consistency (V1)** under operational detector constraints, bounded by $20\text{ Hz}$ ($50\text{ ms}$) sampling quantization.
4. **Descriptive Model Comparison:** Treat information criteria (AIC/BIC) and distribution fittings as descriptive comparisons of pooled sample properties, explicitly acknowledging unmodeled participant and scenario heterogeneity.
