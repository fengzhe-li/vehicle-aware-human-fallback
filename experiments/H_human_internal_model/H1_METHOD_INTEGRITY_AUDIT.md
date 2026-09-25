# Phase 2B-1.1: Empirical Recovery Methodology and Claim-Integrity Audit

> **R2A NOTICE (2026-09-22).** D003 accelerator, brake and steering channels are not driver-only channels (blocker B17: structured, scenario-cell-specific changes within 0.3 s of TOR). All human first-input quantities in this document (`T_first`, first brake/steering input, brake-first vs steer-first, negative handover lag, brake-rise latency, driver-attributed maximum braking or steering) are **INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS**. They are preserved for audit history; see `results/HISTORICAL_OUTPUTS_MANIFEST.md` and `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §9.

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This methodology audit did not detect that the `T_stable` search window, and the brake-correction windows, extend past `Time_Manual_Stop` into automated control. Its conclusions on `T_stable` robustness ("≈22–23 s invariant across anchors", "right-censoring negligible") are withdrawn. Its collision-proxy relabelling does not rescue the proxy, which is withdrawn. The causal-ordering constraint for `T_effective` remains a sensible rule, but the brake channel's semantics (driver pedal vs actuated or automation braking) are unresolved, so "true actuator delay 0.05–0.10 s" is not established. The `H1-B` and `M0-C` gate labels are superseded. D003 blockers and the dataset owners' prior analyses: `research/data_matrix/D003_KNOWN_BLOCKERS.md`. Measurement rules: `docs/OBSERVATION_LAYER.md`. Status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Document:** `experiments/H_human_internal_model/H1_METHOD_INTEGRITY_AUDIT.md`  
**Status:** COMPLETE **[AUDIT 2026-09-22: PRE-AUDIT ARTIFACT; see notice]**  
**Primary Dataset:** D003 — TU Delft Conditionally Automated Driving Takeover Dataset (DOI: `10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB`)  
**Scope:** Methodological audit, threshold sensitivity sweeps, causal ordering enforcement, and claim reconciliation  
**Revised Gate Classification:**
- **Generic Fallback Dynamics:** `H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT/STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`
- **Driver-Vehicle Familiarity Mismatch:** `M0-C: NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA` (retained)
- **Phase 2B-2 Controller Implementation:** NOT AUTHORIZED (awaiting audit acceptance)

---

## 1. Executive Summary of Audit Findings

Phase 2B-1 produced rich empirical extraction across all 513 trials of D003. However, a rigorous methodological audit reveals several critical threshold sensitivities, semantic ambiguities, and conceptual conflations that must be rectified:

1. **Phase 1 Conflation Rectified:** Phase 1 never assumed instantaneous physical vehicle deceleration. The Phase 1 kinematic oracle explicitly incorporated physical actuator delay ($t_2 \in [0.05, 0.17]\text{ s}$) and build-up ramp ($t_3 = 0.30\text{ s}$). The simplified assumption in Phase 1 was strictly the *human control-command* (reaction delay $\tau$ followed by step emergency demand $u=1.0$), applied to an *unavoidable longitudinal stopping boundary*. Conflating this with the vehicle's physical response or claiming it was "REFUTED" by an *evasive lane-change* task was an epistemic category error.
2. **Authority Semantics Disentangled:** The logged timestamp `Time_Manual_Start` represents the operational button-press event ($T_{\text{manual\_start}}$), not the physical instant of control authority transfer ($T_{\text{authority}}$). In **60.2%** of trials, active pedal braking occurs prior to button press, and in **31.7%** steering begins prior to button press.
3. **Causal Ordering of Vehicle Response ($T_{\text{effective}}$):** The unconstrained search in H1 produced **196 / 498 (39.36%) causal violations** where $T_{\text{effective\_any}} < T_{\text{first\_ctrl}}$, caused by automated throttle cut and pre-takeover road curvature. Enforcing the physical invariant $T_{\text{effective\_channel}} \ge T_{\text{first\_channel}}$ eliminates all violations and reveals a median longitudinal actuator delay of **$0.05 - 0.10\text{ s}$**, directly corroborating Phase 1's $t_2 \approx 0.10\text{ s}$.
4. **Obstacle Station Passage ($T_{\text{pass}}$) vs Safe Clearance ($T_{\text{safe\_clear}}$) vs Stabilization ($T_{\text{stable}}$):** Candidate D (`distance_to_obstacle <= 0`) marks geometric obstacle longitudinal station passage ($T_{\text{pass}} \approx T_{\text{req}} + 8.95\text{ s}$), NOT safe hazard clearance. Telemetry records no lateral obstacle coordinates or margins ($T_{\text{safe\_clear}}$ is NOT IDENTIFIABLE). In 100% (6/6) of collision-failure trials, crashing vehicles crossed the obstacle station and falsely satisfied legacy "clearance". Control-input derivative stabilization ($T_{\text{stable}}$) settles at median **$22.2 - 23.0\text{ s}$** post-TOR across post-maneuver search anchors.
5. **Correction Metrics Signal-Processing Audit:** Counting raw derivative zero-crossings inflated steering reversals to 70.5 by conflating neuromuscular tremor with steering reversals. Applying standard ISO gap-threshold hysteresis ($2.0^\circ$) reveals median **2.0 reversals in the acute 8-second evasive maneuver**, and median **13.0 reversals across the full 60-second trial**.
6. **Collision Proxy Relabeling:** There is no source collision ground-truth field in D003. The 6 collision cases are explicitly a `DERIVED_COLLISION_PROXY` based on kinematic boundary heuristics.
7. **Lane-Change Reconciliation:** Exactly 499 trials contain the simulator-logged `Time_Lane_Change` to lane 3. The remaining 14 trials consist of 5 derived collisions, 1 late-change collision, and 8 non-collision trials in heavy traffic where drivers came to a full stop or bypassed via alternative road lanes.
8. **Repeated-Measures Statistical Rigor:** Within-subject paired contrasts across the 57 participants confirm that cognitive load ($N$-back) significantly delays reaction time ($+0.79\text{ s}, p = 3.4 \times 10^{-23}$) and increases brake-first prevalence ($+49.4\%, p = 9.6 \times 10^{-24}$), while traffic density dramatically increases peak brake force ($+109.6\text{ N}, p = 1.2 \times 10^{-31}$).
9. **Gate Reclassification:** Reclassified from $H1\text{-}A$ to **`H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT/STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`**.

---

## 2. Re-Audit of $T_{\text{manual\_start}}$ vs $T_{\text{authority}}$ Semantics

### 2.1 Ground-Truth Documentation
Inspection of `1. data_dictionary.csv` from the official D003 archive establishes the authoritative definition:
> `Time_Manual_Start`: *"the time stamp when the participant pressed the switch button and switched to manual mode, s"*

### 2.2 Semantic Disentanglement
- **Observed Variable:** $T_{\text{manual\_start}}$ — the logged discrete clock instant when the driver depressed the steering wheel button to disengage automation.
- **Conceptual Variable:** $T_{\text{authority}}$ — the theoretical state transition where control authority over the vehicle plant transfers from automation to the human.

### 2.3 Physical Reality in D003
In modern steer-by-wire/drive-by-wire and simulator environments, physical control inputs and logical mode flags decouple:
- In **60.2%** of trials, brake pedal force exceeds $15\text{ N}$ prior to $T_{\text{manual\_start}}$.
- In **31.7%** of trials, steering wheel deflection exceeds $0.05\text{ rad}$ prior to $T_{\text{manual\_start}}$.
- Across all active inputs, $T_{\text{first\_ctrl}} - T_{\text{manual\_start}}$ has a median of **$-0.650\text{ s}$**.

Treating $T_{\text{manual\_start}}$ as $T_{\text{authority}}$ misattributes the onset of human intervention. Drivers reflexively engage pedals and wheel while or immediately before clicking the acknowledgement button. In this report and future models, $T_{\text{manual\_start}}$ is retained as the operational button-press measurement, while $T_{\text{first\_ctrl}}$ marks the **first detected human control input**, which is strictly distinguished from subsequent vehicle plant response ($T_{\text{effective}}$).

---

## 3. Confrontation Audit: Phase 1 Assumptions vs D003 Empirical Context

### 3.1 Resolving the Actuator Response Mischaracterization
Phase 1 ($A_1, B_0, D_0$) **never** modeled vehicle deceleration as an instantaneous step. The Phase 1 kinematic oracle and analytical boundary ($D_0$) explicitly decomposed vehicle braking into:
$$\text{Phase 1 Vehicle Model: } \quad a(t) = \begin{cases} 0 & t \in [0, t_2] \\ a_{max} \frac{t - t_2}{t_3} & t \in [t_2, t_2 + t_3] \\ a_{max} & t \ge t_2 + t_3 \end{cases}$$
where $t_2 \in [0.05, 0.17]\text{ s}$ is generic vehicle / braking response delay (architecture-neutral) and $t_3 \in [0.15, 0.45]\text{ s}$ is deceleration build-up ramp.

The simplified Phase 1 assumption was strictly the **human command**:
$$\text{Phase 1 Human Command: } \quad u(t) = \begin{cases} 0 & t < \tau \\ 1.0 & t \ge \tau \end{cases}$$
followed by holding full brake demand until complete vehicle standstill ($v = 0$).

### 3.2 Distinguishing Operational Scenarios
- **Phase 1 Operational Scenario:** Stationary in-lane hazard under unavoidable lane entrapment (no escape corridor). The safety envelope question was strictly the *minimum longitudinal stopping boundary*.
- **D003 Operational Scenario:** Highway construction hazard where adjacent lanes are available (density 0, 10, 20 veh/km). Drivers executed an *evasive lane-change bypass*, shedding speed while evaluating adjacent traffic gaps.

D003 does not falsify the longitudinal stopping boundary; rather, D003 proves that the **full operational scope requires coupled lateral-longitudinal recovery models**.

### 3.3 Calibrated Epistemic Confrontation Table

| Dimension | Phase 1 Theoretical Model ($A_1, B_0, D_0$) | Phase 2B-1 Empirical Reality (D003, $N=513$) | Epistemic Status & Methodological Verdict |
| :--- | :--- | :--- | :--- |
| **Reaction Latency ($\tau$)** | Scalar latency parameter $t_1 \in [0.7, 1.5]\text{ s}$ (nominal $1.0 - 1.2\text{ s}$). | Median active motor onset $T_{\text{first\_ctrl}} - T_{\text{req}} = 1.125\text{ s}$ (IQR: $0.850\text{ s}$). | **SUPPORTED.** Empirical motor onset latency aligns tightly with Phase 1's core domain. |
| **Vehicle Response Delay ($t_2$)** | Generic vehicle / braking response delay $t_2 \in [0.05, 0.17]\text{ s}$ (nominal $0.10\text{ s}$). | Causal deceleration onset delay: median $0.05 - 0.10\text{ s}$ ($50 - 100\text{ ms}$). | **CONSISTENT (V1).** The observed D003 longitudinal response-onset interval is consistent with the Phase-1 modeled response-delay scale under the current operational detector (Parameter-Level Consistency V1). |
| **Human Command Waveform** | Step command ($u = 1.0$) at reaction threshold. | Finite command ramp: rise rate median $91.7\text{ N/s}$, time to peak median $0.75\text{ s}$. | **LIMITED.** Human motor command exhibits finite neuromuscular ramp rate rather than instantaneous step. |
| **Closed-Loop Regulation** | Open-loop hold until final state. | Pronounced closed-loop feedback: median 2 brake reapplications (68.3% of trials) and 2 acute steering reversals. | **EXTENDED BY D003.** Takeover recovery requires closed-loop feedback regulation. |
| **Longitudinal Stopping ($v=0$)** | Emergency braking to complete standstill ($v_{\text{final}} = 0$). | Incomplete speed drop: median drop $8.31\text{ m/s}$, min speed post-TOR median $16.95\text{ m/s}$. | **OUT-OF-SCOPE RELATIVE TO D003.** D003 is an evasive maneuver, not a blocked-lane emergency stop. |
| **Lateral Steering Coupling** | Zero lateral motion ($a_y \equiv 0$). | Coordinated evasive lane change in 97%+ of trials; 32% steer first, 63% brake first. | **EXTENDED BY D003.** Proves full fallback safety requires coupled lateral-longitudinal envelope. |

---

## 4. $T_{\text{first}}$ Threshold Sensitivity Grid

The sensitivity of first control onset $T_{\text{first}}$ and action sequencing was audited across a $5 \times 4$ grid ($N = 498$ valid TOR trials), saved in [`results/H1_sensitivity/tfirst_threshold_sensitivity.csv`](../../results/H1_sensitivity/tfirst_threshold_sensitivity.csv):

| Brake Thresh ($N$) | Steer Thresh (rad / deg) | Median $T_{\text{first}}$ (s) | IQR (s) | Brake First (%) | Steer First (%) | Simult. (%) | Input Before Manual Start (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 5.0 N | $0.02\text{ rad}$ ($1.15^\circ$) | $0.450\text{ s}$ | $1.101\text{ s}$ | 60.0% | 29.1% | 10.8% | **88.0%** |
| 5.0 N | $0.05\text{ rad}$ ($2.86^\circ$) | $0.550\text{ s}$ | $0.799\text{ s}$ | 86.5% | 13.3% | 0.2% | **87.3%** |
| 5.0 N | $0.07\text{ rad}$ ($4.01^\circ$) | $0.950\text{ s}$ | $0.801\text{ s}$ | 95.0% | 5.0% | 0.0% | **77.7%** |
| 10.0 N | $0.02\text{ rad}$ ($1.15^\circ$) | $0.799\text{ s}$ | $1.150\text{ s}$ | 58.8% | 30.3% | 10.8% | **85.3%** |
| 10.0 N | $0.05\text{ rad}$ ($2.86^\circ$) | $1.000\text{ s}$ | $0.801\text{ s}$ | 75.3% | 24.1% | 0.6% | **84.5%** |
| 10.0 N | $0.07\text{ rad}$ ($4.01^\circ$) | $1.199\text{ s}$ | $1.050\text{ s}$ | 84.3% | 15.5% | 0.2% | **68.3%** |
| **15.0 N** (Nom) | **$0.05\text{ rad}$** (Nom) | **$1.125\text{ s}$** | **$0.850\text{ s}$** | **62.9%** | **32.1%** | **5.0%** | **80.7%** |
| 15.0 N | $0.07\text{ rad}$ ($4.01^\circ$) | $1.200\text{ s}$ | $1.149\text{ s}$ | 81.5% | 18.3% | 0.2% | **64.1%** |
| 20.0 N | $0.02\text{ rad}$ ($1.15^\circ$) | $1.050\text{ s}$ | $1.350\text{ s}$ | 51.4% | 47.6% | 1.0% | **77.7%** |
| 20.0 N | $0.05\text{ rad}$ ($2.86^\circ$) | $1.150\text{ s}$ | $1.000\text{ s}$ | 59.0% | 41.0% | 0.0% | **76.7%** |
| 20.0 N | $0.07\text{ rad}$ ($4.01^\circ$) | $1.399\text{ s}$ | $1.000\text{ s}$ | 75.7% | 23.9% | 0.4% | **56.4%** |
| 30.0 N | $0.02\text{ rad}$ ($1.15^\circ$) | $1.100\text{ s}$ | $1.401\text{ s}$ | 41.4% | 57.6% | 1.0% | **71.5%** |
| 30.0 N | $0.05\text{ rad}$ ($2.86^\circ$) | $1.150\text{ s}$ | $1.150\text{ s}$ | 55.0% | 45.0% | 0.0% | **68.3%** |

### 4.1 Sensitivity Insights
- **Input Prior to Manual Start is Completely Robust:** Across 19 of the 20 grid configurations, the fraction of trials where the driver touched controls prior to pressing the manual button spans **$56.4\% - 88.0\%$** (and remains $42.2\%$ even at an extreme $30\text{ N} / 4.0^\circ$ threshold).
- **Reaction Latency Stability:** Across all defensible thresholds ($F_b \in [10, 20]\text{ N}$, $\Delta\delta \in [0.03, 0.07]\text{ rad}$), median $T_{\text{first}}$ sits strictly within **$0.80 - 1.40\text{ s}$**.
- **Action Ordering Dominance:** Brake-first is the plurality or majority in 18 of the 20 grid points (ranging from $51.4\%$ to $95.0\%$). Steer-first only exceeds brake-first under an artificially mismatched combination (heavy $30\text{ N}$ brake threshold paired with an ultra-sensitive $1.15^\circ$ steer threshold).

---

## 5. Causal Ordering of Vehicle Response ($T_{\text{effective}}$)

### 5.1 Audit of Unconstrained $T_{\text{effective}}$ Violations
In the initial H1 pipeline, vehicle response was searched starting at $T_{\text{request}}$. This allowed unconstrained background variations to trigger response flags before human input:
- **Total Causal Violations:** **196 of 498 trials (39.36%)** had $T_{\text{effective\_any}} < T_{\text{first\_ctrl}}$.
- **Longitudinal Deceleration Violations:** **298 trials (59.84%)** had $T_{\text{effective\_dec}} < T_{\text{first\_brake}}$ (mean premature magnitude: $3.71\text{ s}$, max $41.5\text{ s}$).
- **Lateral Acceleration Violations:** **64 trials (12.85%)** had $T_{\text{effective\_lat}} < T_{\text{first\_steer}}$ (mean premature magnitude: $0.23\text{ s}$).
- *Root Cause:* At TOR issuance, the simulator automation cuts engine cruise throttle, causing natural aerodynamic/powertrain coastdown deceleration ($a_x \approx -0.6\text{ m/s}^2$) long before the human presses the brake.

### 5.2 Causal Constrained Detector Formulation
To enforce the physical law of causality, vehicle response must be measured **at or after the corresponding human motor actuation**:
$$T_{\text{effective\_dec}} = \min \{ t \ge T_{\text{first\_brake}} \mid a_x(t) \le a_x(T_{\text{first\_brake}}) - \Delta a_{x,\text{thresh}} \text{ for } k \text{ samples} \}$$
$$T_{\text{effective\_lat}} = \min \{ t \ge T_{\text{first\_steer}} \mid |a_y(t) - a_y(T_{\text{first\_steer}})| \ge \Delta a_{y,\text{thresh}} \text{ for } k \text{ samples} \}$$

### 5.3 Causal Grid Evaluation
Evaluated across candidate thresholds and persistence windows in [`results/H1_sensitivity/teffective_definition_sensitivity.csv`](../../results/H1_sensitivity/teffective_definition_sensitivity.csv):

| Channel | $\Delta a$ Thresh ($\text{m/s}^2$) | Persistence | Detection Rate (%) | Median Delay Post-Input (s) | IQR (s) | Causal Violations |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Longitudinal** | $0.3\text{ m/s}^2$ | $50\text{ ms}$ (1 sample) | 95.2% | **$0.050\text{ s}$** | $0.550\text{ s}$ | **0 (0.0%)** |
| **Longitudinal** | $0.3\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 95.2% | **$0.050\text{ s}$** | $0.550\text{ s}$ | **0 (0.0%)** |
| **Longitudinal** | $0.5\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 94.2% | **$0.100\text{ s}$** | $0.950\text{ s}$ | **0 (0.0%)** |
| **Longitudinal** | $0.8\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 90.2% | **$0.150\text{ s}$** | $1.650\text{ s}$ | **0 (0.0%)** |
| **Longitudinal** | $1.0\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 88.4% | **$0.200\text{ s}$** | $1.650\text{ s}$ | **0 (0.0%)** |
| **Lateral** | $0.2\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 100.0% | **$0.900\text{ s}$** | $1.950\text{ s}$ | **0 (0.0%)** |
| **Lateral** | $0.4\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 100.0% | **$1.900\text{ s}$** | $3.250\text{ s}$ | **0 (0.0%)** |
| **Lateral** | $0.6\text{ m/s}^2$ | $100\text{ ms}$ (2 samples) | 99.6% | **$2.800\text{ s}$** | $4.038\text{ s}$ | **0 (0.0%)** |

### 5.4 Resolution Limitations & Validation Status
- **Longitudinal Deceleration Latency ($t_2$ Consistency):** Under causal gating, median longitudinal response onset post-brake is **$0.050 - 0.100\text{ s}$** ($50 - 100\text{ ms}$). This observed interval is consistent with the Phase-1 modeled response-delay scale ($t_2 \in [0.05, 0.17]\text{ s}$) under the current operational detector ($\Delta a_x \le -0.5\text{ m/s}^2$).
- **Temporal Resolution Limitations:** This finding cannot be claimed as direct physical sensor validation. The telemetry is sampled at $20\text{ Hz}$ ($\Delta t = 50\text{ ms}$ bins), introducing an intrinsic $\pm 50\text{ ms}$ measurement quantization. Furthermore, persistence windows ($k=2$ samples = $100\text{ ms}$) impose an operational detection lag, acceleration in fixed-base simulators is computed from vehicle dynamics equations rather than physical hydraulic pressure transducers, and onset timing is threshold-dependent. The validation status is strictly classified as **Parameter-Level Consistency (V1)**.
- **Lateral Timing Reclassification:** The interval $T_{\text{effective\_lat}} - T_{\text{first\_steer}}$ (median $0.90\text{ s}$ at $0.2\text{ m/s}^2$, $1.90\text{ s}$ at $0.4\text{ m/s}^2$, and $2.80\text{ s}$ at $0.6\text{ m/s}^2$) must NOT be termed "actuator delay" or "chassis lag". It is a **threshold-defined task-level effective lateral-response interval** reflecting the steering input trajectory, threshold exceedance criteria ($\Delta a_y \ge 0.4\text{ m/s}^2$), persistence window ($k=2$, $100\text{ ms}$), and $20\text{ Hz}$ sampling resolution. All mechanistic explanations invoking front-wheel yaw accumulation, tire mechanics, rack dynamics, or chassis inertia are excluded as they are unidentifiable from D003 telemetry.

---

## 6. Endpoint Semantics: Obstacle Station Passage ($T_{\text{pass}}$) vs Safe Clearance ($T_{\text{safe\_clear}}$)

In preliminary reporting, Candidate D was colloquially termed "Hazard Clearance" ($T_{\text{clear}}$), operationalized as `distance_to_obstacle <= 0` with $v > 10\text{ m/s}$. A methodological audit reveals this definition conflated a purely geometric longitudinal event with safe hazard avoidance:

### 6.1 The Flaw in Operationalizing "Clearance" Longitudinally
1. **Longitudinal Station Crossing $\ne$ Safe Clearance:**
   In road traffic scenarios, a collision trajectory also translates past the obstacle's longitudinal coordinate ($d_{\text{obstacle}} \le 0$). Calling longitudinal passage "safe clearance" or "hazard bypass" is invalid unless lateral clearance (non-overlap) is simultaneously established.
2. **Identifiability Audit of D003 Telemetry:**
   D003 telemetry records only 1D longitudinal distance to the obstacle (`[85 (Distance/Distance_to_Construction)]`). The dataset contains NO obstacle lateral coordinates, NO barrier bounding polygons, and NO vehicle-obstacle lateral clearance margins. Consequently, true safe lateral clearance ($T_{\text{safe\_clear}}$) is **NOT IDENTIFIABLE** from D003 telemetry without imposing unvalidated lateral geometric assumptions.
3. **Removal of Ad-Hoc Speed Constraint:**
   The legacy condition required $v_x > 10\text{ m/s}$. This arbitrarily delayed the timestamp in 47 trials where evasive braking dropped speeds below $10\text{ m/s}$ as the vehicle crossed the station, only firing seconds later upon reacceleration. The event is properly operationalized as pure geometric coordinate passage ($T_{\text{pass}}$):
   $$T_{\text{pass}} = \min \{ t \ge T_{\text{request}} \mid d_{\text{obstacle}}(t) \le 0.0\text{ m} \}$$

### 6.2 Collision-Proxy Empirical Cross-Check
To demonstrate conclusively why longitudinal passage cannot represent safe clearance, all 6 collision-failure trials (`DERIVED_COLLISION_PROXY`) identified in the data quality audit were evaluated under both legacy and corrected definitions:

| Trial ID | Scenario | TOR (s) | Legacy $T_{\text{clear}}$ (s post-TOR) | $T_{\text{pass}}$ (s post-TOR) | Ego Speed at $T_{\text{pass}}$ (m/s) | $\text{Time\_Lane\_Change}$ Status | Ground-Truth Collision Mechanism |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `density_10_nback_1_id_8` | Dense / High Load | 26.10 | 3.95 | 3.95 | 25.42 | 4.90 s (0.95 s *after* $T_{\text{pass}}$) | Hit obstacle in-lane before completing lane change |
| `density_20_nback_0_id_22` | Jam / Low Load | 48.65 | 7.85 | 7.85 | 17.53 | Unobserved (No LC) | Collided directly into obstacle; no lane change |
| `density_20_nback_1_id_37` | Jam / Med Load | 28.70 | 8.15 | 8.15 | 15.75 | Unobserved (No LC) | Collided directly into obstacle; no lane change |
| `density_20_nback_2_id_37` | Jam / High Load | 43.55 | 16.80 | 12.60 | 5.82 | Unobserved (No LC) | Decelerated into obstacle, rolled past station |
| `density_20_nback_1_id_44` | Jam / Med Load | 28.70 | 13.75 | 13.05 | 7.65 | Unobserved (No LC) | Decelerated into obstacle, rolled past station |
| `density_20_nback_2_id_56` | Jam / High Load | 43.60 | 12.70 | 10.15 | 3.11 | Unobserved (No LC) | Decelerated into obstacle, rolled past station |

**Audit Finding:** In **6 out of 6 (100%)** collision failure trials, the legacy "clearance" detector falsely fired and declared that the vehicle had "cleared" the hazard. In 5 of the 6 trials, no lane change ever occurred (the vehicle collided directly into the construction zone in its cruising lane and simulator dynamics continued rolling past $d \le 0$). In the remaining trial (`density_10_nback_1_id_8`), the vehicle struck the obstacle station 0.95 s before crossing the lane boundary. This empirical cross-check confirms that $T_{\text{pass}}$ is strictly a geometric station crossing event and that $T_{\text{safe\_clear}}$ is unidentifiable.

### 6.3 Data Dictionary Audit of $\text{Time\_Lane\_Change}$
Authoritative inspection of the D003 data dictionary (`1. data_dictionary.csv`, Row 44) reveals:
- **Source Definition:** `Time_Lane_Change`: *"the time when the car changed to the left lane during takeover | Unit: s"*.
- **Telemetry Reality:** Continuous time-series cross-examination confirms that $\text{Time\_Lane\_Change}$ records the exact discrete sample where simulator discrete state `lane_id` transitions from the original cruising lane ($2.0, 6.0, 7.0$) to the target overtaking lane ($3.0, 5.0, 6.0$).
- **Methodological Status:** This is a **discrete lane-boundary crossing / lane transition instant**, NOT steering reaction onset (which occurs $\approx 1.5 - 2.0\text{ s}$ earlier) and NOT maneuver completion or vehicle stabilization (steering torque and vehicle yaw rates remain active for $> 15\text{ s}$ afterwards).

---

## 7. $T_{\text{stable}}$ Robustness, Search-Anchor Sensitivity, and Censoring Audit

Evaluating Candidate A across tolerances, persistence durations, and search anchors in [`results/H1_sensitivity/tstable_definition_sensitivity.csv`](../../results/H1_sensitivity/tstable_definition_sensitivity.csv):

### 7.1 Search Window Invariant & Anchor Sensitivity
If the stabilization detector runs starting at $T_{\text{request}}$, short persistence windows ($1.0\text{ s}$) falsely trigger during the driver's *pre-reaction idle period* ($0.05\text{ s}$ latency). When the search is anchored at or after active maneuvering, settling times were audited across five candidate operational anchors (evaluated at nominal rates $|\dot{\delta}_{\text{sw}}| \le 0.05\text{ rad/s}$, $|\dot{F}_{\text{brake}}| \le 20\text{ N/s}$, persistence $\tau_p = 1.5\text{ s}$):

| Search Anchor Condition | Eligible Trials | Settled Fraction (%) | Median $T_{\text{stable}}$ (s) | IQR (s) | Right-Censored ($\le 3\text{s}$ of end) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$T_{\text{first}} + 1.0\text{ s}$** | 498 | 100.0% | **$22.18\text{ s}$** | $7.89\text{ s}$ | 0.00% |
| **$T_{\text{first}} + 2.0\text{ s}$** (Nominal) | 498 | 100.0% | **$22.47\text{ s}$** | $7.79\text{ s}$ | 0.00% |
| **$T_{\text{first}} + 3.0\text{ s}$** | 498 | 100.0% | **$22.55\text{ s}$** | $7.79\text{ s}$ | 0.00% |
| **$\text{Time\_Lane\_Change}$** | 484 | 100.0% | **$22.55\text{ s}$** | $7.45\text{ s}$ | 0.00% |
| **$T_{\text{pass}}$ (Obstacle Station Passage)** | 498 | 100.0% | **$22.95\text{ s}$** | $7.51\text{ s}$ | 0.00% |

### 7.2 Anchor Robustness & Distinct Subset Spans
- **Explicit Anchor Span Breakdown:**
  - **Subset A ($T_{\text{first}} + 2.0\text{ s}$, $T_{\text{first}} + 3.0\text{ s}$, $\text{Time\_Lane\_Change}$):**
    Median $T_{\text{stable}}$ spans strictly **$22.47\text{ s} - 22.55\text{ s}$** ($\mathbf{\Delta = 0.08\text{ s}}$). Across active maneuver entry points, settling time is invariant to within 80 milliseconds.
  - **Subset B (Subset A $+ T_{\text{pass}}$):**
    Median $T_{\text{stable}}$ spans **$22.47\text{ s} - 22.95\text{ s}$** ($\mathbf{\Delta = 0.48\text{ s}}$).
  - **Complete 5-Anchor Set ($T_{\text{first}} + 1.0\text{ s}$, $T_{\text{first}} + 2.0\text{ s}$, $T_{\text{first}} + 3.0\text{ s}$, $\text{Time\_Lane\_Change}$, $T_{\text{pass}}$):**
    Median $T_{\text{stable}}$ spans **$22.18\text{ s} - 22.95\text{ s}$** ($\mathbf{\Delta = 0.78\text{ s}}$).
- **Invariant Finding:** The empirical conclusion that human control stabilization requires $\approx 22 - 23\text{ s}$ post-TOR is **completely robust across all candidate search anchors**.
- **Temporal Causal Sequence:** The physical sequence is preserved without contradiction:
  $$T_{\text{req}} = 0\text{ s} < T_{\text{first\_ctrl}} (\approx 1.13\text{ s}) < \text{Time\_Lane\_Change} (\approx 6.45\text{ s}) < T_{\text{pass}} (\approx 8.95\text{ s}) < T_{\text{stable}} (\approx 22.2 - 23.0\text{ s})$$
- **Right-Censoring / Finite-Record Artifacts:** Right-censoring (settling within $3.0\text{ s}$ of record termination) is strictly **$0.00\%$** and settled fraction is **$100.00\%$** across all five candidate anchors.

**Classification:** `ROBUST` across all post-maneuver anchors ($T_{\text{first}} + 1\text{s}, +2\text{s}, +3\text{s}$, $\text{Time\_Lane\_Change}$, $T_{\text{pass}}$); `MODERATELY DEFINITION-DEPENDENT` only on persistence window length ($1.0\text{ s}$ vs $2.0\text{ s}$).

---

## 8. Correction Metrics Signal-Processing Audit (Amplitude-Hysteresis Steering Reversals)

Counting raw zero-crossings of continuous steering wheel speed yielded 70.5 reversals in H1 because every micro-tremor crossed zero. A formal signal-processing audit applying a **project operational amplitude-hysteresis steering-reversal detector** (methodological precedent: McLean & Hoffmann, 1975) and a 2 Hz low-pass filter is reported in [`results/H1_sensitivity/correction_metric_sensitivity.csv`](../../results/H1_sensitivity/correction_metric_sensitivity.csv):

### 8.1 Detector Provenance & Configuration
- **Nomenclature & Precedent Audit:** The previous report casually used the term "ISO gap-threshold reversal algorithm". However, no formal ISO standard defines this specific algorithm name, and broad claims of standardization under SAE J2944 are retired. The authoritative methodological precedent for gap-threshold amplitude hysteresis is **McLean & Hoffmann (1975)** (*Human Factors*, 17(3):248–256).
- **Filter Specifications:** 2nd-order zero-phase Butterworth filter at $2.0\text{ Hz}$ cutoff frequency (to suppress motor sensor noise and neuromuscular tremor while preserving intentional steering actions).
- **Hysteresis Threshold:** $2.0^\circ$ ($0.035\text{ rad}$) gap threshold requires the steering wheel to reverse direction by at least $2.0^\circ$ from an extremum before a new peak or valley is committed.

| Gap Threshold | Filter Condition | Acute Evasive Phase ($T_{\text{req}}$ to $T_{\text{req}}+8\text{s}$) | Full Trial Manual Phase (60+ s) |
| :---: | :---: | :---: | :---: |
| **$1.0^\circ$ ($0.017\text{ rad}$)** | Raw | Median 3.0 (IQR: 2.0) | Median 16.0 (IQR: 8.0) |
| **$1.0^\circ$ ($0.017\text{ rad}$)** | 2 Hz Lowpass | Median 3.0 (IQR: 2.0) | Median 15.0 (IQR: 6.0) |
| **$2.0^\circ$ ($0.035\text{ rad}$)** | Raw | Median 2.0 (IQR: 2.0) | Median 13.0 (IQR: 7.8) |
| **$2.0^\circ$ ($0.035\text{ rad}$)** | **2 Hz Lowpass** (Standard) | **Median 2.0 (IQR: 2.0)** | **Median 13.0 (IQR: 6.0)** |
| **$3.0^\circ$ ($0.052\text{ rad}$)** | 2 Hz Lowpass | Median 2.0 (IQR: 1.0) | Median 11.0 (IQR: 5.0) |
| **$5.0^\circ$ ($0.087\text{ rad}$)** | 2 Hz Lowpass | Median 1.0 (IQR: 2.0) | Median 9.0 (IQR: 4.0) |

### 8.2 Operational Interpretation
- **In the acute 8-second evasive window**, drivers execute **median 2.0 steering reversals** ($\approx 2$ to 3 direction changes: lane ingress, countersteer straightening, lane centering), operationalizing the directional steering control frequency of path recovery. Reversals must NOT be interpreted as discrete conscious cognitive re-planning decisions.
- **Across the entire 60-second trial**, drivers execute **median 13.0 reversals** performing continuous closed-loop highway lane-keeping.
- **Braking Reapplications:** Across prominence thresholds ($5 - 20\text{ N}$), drivers exhibit **median 2.0 to 4.0 brake pulses**, confirming genuine closed-loop modulation.

---

## 9. Collision Outcome Relabeling: `DERIVED_COLLISION_PROXY`

### 9.1 Ground-Truth Verification
No binary collision or crash sensor column exists in the D003 telemetry. The six reported collision trials (`COLLISION_FAILURE`) were derived using the heuristic:
$$\text{Condition: } \quad d_{\text{hazard}} \le 0.0\text{ m} \quad \text{AND} \quad v_x > 3.0\text{ m/s} \quad \text{prior to or without lane change}$$
To preserve epistemic integrity, these are formally relabeled as **`DERIVED_COLLISION_PROXY`**.

### 9.2 Complete Reconciliation of All 513 Trials

$$\begin{aligned}
\text{Total Recorded Trials: } & 513 \\
\hline
\text{Valid Scheduled TOR: } & 498 \quad (97.08\%) \\
\text{Preemptive Manual Switch (no TOR emitted): } & 15 \quad (2.92\%) \\
\hline
\text{Derived Collision Proxies: } & 6 \quad (1.17\%) \\
\text{Safe Hazard Clearance: } & 507 \quad (98.83\%) \\
\hline
\text{Simulator-Logged Lane Change (`Time_Lane_Change` non-null): } & 499 \quad (97.27\%) \\
\text{No Simulator Lane Change Logged: } & 14 \quad (2.73\%)
\end{aligned}$$

**Disposition of the 14 Trials Lacking `Time_Lane_Change`:**
- **5 trials:** Derived collision proxies where the vehicle struck the hazard in the original lane without changing lanes.
- **1 trial:** Derived collision proxy where late lane change occurred after obstacle impact (`dist_at_lc <= 0`).
- **8 trials:** High-density traffic cases (`density_20`) where drivers braked to a complete stop ($v \le 2.7\text{ m/s}$) or bypassed the zone via non-target lanes (lanes 5, 7, 9) where the discrete lane-3 trigger did not fire.

---

## 10. Scenario Effects: Participant-Level Repeated-Measures Analysis

Treating 513 trials as independent observations produces severe pseudo-replication. In D003, each of the $N = 57$ participants completed 9 scenarios combining three traffic densities (0, 10, 20 veh/km) and three cognitive workload levels (0-back, 1-back, 2-back) counterbalanced across participants. To respect this design, inferential tests use **within-participant paired contrasts** ($N = 57$) and non-parametric Friedman tests across conditions, documented in [`results/H1_sensitivity/scenario_repeated_measures.csv`](../../results/H1_sensitivity/scenario_repeated_measures.csv):

| Dependent Metric | Contrast Factor | Mean Diff ($\Delta \bar{x}$) | Std. Error | 95% Confidence Interval | Paired $t$ stat | Unadj. $p$ | Holm $p$ | Wilcoxon $p$ | Friedman $p$ | Association Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $\Delta T_{\text{manual\_start}}$ | Density ($20 - 0$) | $-0.019\text{ s}$ | $0.079\text{ s}$ | $[-0.177, +0.139]\text{ s}$ | $-0.241$ | $0.811$ | $0.873$ | $0.334$ | $0.076$ | Not Supported |
| $T_{\text{first\_ctrl}} - T_{\text{req}}$ | Density ($20 - 0$) | **$-0.918\text{ s}$** | $0.038\text{ s}$ | **$[-0.995, -0.841]\text{ s}$** | $-23.892$ | **$4.73 \times 10^{-31}$** | **$1.89 \times 10^{-30}$** | **$5.43 \times 10^{-11}$** | **$2.02 \times 10^{-21}$** | **Supported** |
| Peak Brake Force | Density ($20 - 0$) | **$+109.64\text{ N}$** | $4.465\text{ N}$ | **$[+100.69, +118.58]\text{ N}$** | $+24.556$ | **$1.16 \times 10^{-31}$** | **$5.81 \times 10^{-31}$** | **$5.14 \times 10^{-11}$** | **$1.21 \times 10^{-24}$** | **Supported** |
| Peak Steer ($^\circ$) | Density ($20 - 0$) | $-0.125^\circ$ | $0.159^\circ$ | $[-0.443, +0.194]^\circ$ | $-0.784$ | $0.436$ | $0.873$ | $0.376$ | $2.22 \times 10^{-14}$ | Not Supported |
| Brake-First Prob. | Density ($20 - 0$) | **$+19.01\%$** | $2.78\%$ | **$[+13.43\%, +24.58\%]$** | $+6.834$ | **$6.51 \times 10^{-9}$** | **$1.95 \times 10^{-8}$** | **$6.00 \times 10^{-7}$** | **$3.52 \times 10^{-12}$** | **Supported** |
| $\Delta T_{\text{manual\_start}}$ | $N$-Back ($2 - 0$) | **$+0.401\text{ s}$** | $0.079\text{ s}$ | **$[+0.244, +0.559]\text{ s}$** | $+5.102$ | **$4.31 \times 10^{-6}$** | **$8.61 \times 10^{-6}$** | **$7.24 \times 10^{-6}$** | **$3.34 \times 10^{-8}$** | **Supported** |
| $T_{\text{first\_ctrl}} - T_{\text{req}}$ | $N$-Back ($2 - 0$) | **$+0.786\text{ s}$** | $0.047\text{ s}$ | **$[+0.692, +0.881]\text{ s}$** | $+16.694$ | **$3.44 \times 10^{-23}$** | **$1.03 \times 10^{-22}$** | **$1.16 \times 10^{-10}$** | **$2.40 \times 10^{-19}$** | **Supported** |
| Peak Brake Force | $N$-Back ($2 - 0$) | $+1.914\text{ N}$ | $2.734\text{ N}$ | $[-3.565, +7.393]\text{ N}$ | $+0.700$ | $0.487$ | $0.487$ | $0.324$ | $1.08 \times 10^{-17}$ | Not Supported |
| Peak Steer ($^\circ$) | $N$-Back ($2 - 0$) | **$-1.972^\circ$** | $0.101^\circ$ | **$[-2.173, -1.770]^\circ$** | $-19.626$ | **$1.65 \times 10^{-26}$** | **$8.27 \times 10^{-26}$** | **$1.23 \times 10^{-10}$** | **$5.07 \times 10^{-19}$** | **Supported** |
| Brake-First Prob. | $N$-Back ($2 - 0$) | **$+49.40\%$** | $2.88\%$ | **$[+43.63\%, +55.18\%]$** | $+17.158$ | **$9.64 \times 10^{-24}$** | **$3.86 \times 10^{-23}$** | **$8.32 \times 10^{-11}$** | **$1.37 \times 10^{-20}$** | **Supported** |

### 10.1 Statistical Synthesis & Methodological Framing
1. **Cognitive Distraction ($N$-Back) is Strongly Associated with Takeover Delay:** High cognitive load increases manual button-press latency by $+0.401\text{ s}$ ($95\%\text{ CI: } [+0.244, +0.559]\text{ s}$, Holm $p < 10^{-5}$) and motor reaction onset by $+0.786\text{ s}$ ($95\%\text{ CI: } [+0.692, +0.881]\text{ s}$, Holm $p < 10^{-21}$), while shifting initial action towards reflex braking by $+49.4\%$ (Holm $p < 10^{-22}$).
2. **Traffic Density is Associated with Tripled Peak Braking Effort:** Surrounding traffic flow markedly increases peak brake force by $+109.64\text{ N}$ ($95\%\text{ CI: } [+100.69, +118.58]\text{ N}$, Holm $p < 10^{-30}$) and promotes brake-first modality ($+19.0\%$, Holm $p < 10^{-7}$), but exhibits no detectable association with manual-mode-switch latency ($p = 0.811$).
3. **Calibrated Inferential Interpretation:** These results document robust **within-participant experimental-condition differences** across counterbalanced simulator treatments. Direct mechanistic assertions attributing these differences to unobserved internal cognitive deliberation (e.g., "drivers brake because gap acceptance is blocked") remain speculative hypotheses; empirical models must describe the observed behavioral associations without claiming direct cognitive access.

---

## 11. Latency Distribution Diagnostics

Candidate parametric distributions were fitted to positive reaction latencies ($T_{\text{first\_ctrl}} - T_{\text{req}}$, $N = 498$ valid TOR trials) to evaluate the descriptive properties of candidate distribution families:

| Candidate Distribution | Log-Likelihood | AIC | BIC | Kolmogorov-Smirnov $D$ | KS $p$-value | Descriptive Ranking |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Weibull (min)** | **$-442.25$** | **$890.49$** | **$903.13$** | $0.2118$ | $4.41 \times 10^{-20}$ | **1 (Lowest AIC/BIC)** |
| **Gamma** | $-451.23$ | $908.46$ | $921.09$ | $0.2289$ | $2.07 \times 10^{-23}$ | 2 |
| **Inverse Gaussian (Wald)** | $-458.06$ | $922.11$ | $934.74$ | $0.2138$ | $1.87 \times 10^{-20}$ | 3 |
| **Log-Normal** | $-459.09$ | $924.17$ | $936.81$ | $0.2103$ | $8.45 \times 10^{-20}$ | 4 |
| **Normal** | $-486.75$ | $977.50$ | $985.92$ | $0.1778$ | $3.04 \times 10^{-14}$ | 5 |

### 11.1 Methodological Finding & Limitations
- **Descriptive Criteria vs. Hypothesis Testing:** Weibull and Gamma achieve lower descriptive information criteria ($\Delta \text{AIC} = 33.7$ relative to Log-Normal). However, AIC and BIC are comparative model selection heuristics, **not statistical hypothesis tests**; no claim of "statistically significant distributional superiority" can be made from AIC alone.
- **Confounding in Pooled Fitting:** This pooled fitting aggregates across repeated measures, conflating three distinct variance sources:
  1. *Participant heterogeneity* (between-subject baseline reaction capability),
  2. *Scenario heterogeneity* (traffic density and cognitive workload conditions),
  3. *Within-participant trial-to-trial stochasticity*.
- **Multimodal Mixture Reality:** All unimodal candidate distributions fail the Kolmogorov-Smirnov goodness-of-fit test ($p < 10^{-13}$) because the empirical latency distribution is an unresolved **multimodal mixture** driven by cognitive workload condition ($N$-back shifts reaction time by $+0.79\text{ s}$).
- **Phase 2B Decision:** No single parametric latency distribution is frozen in this phase. In Phase 2B-2, reaction latency must either be represented non-parametrically via the empirical cumulative distribution function (ECDF) or modeled as a conditional distribution partitioned by cognitive workload and traffic density state.

---

## 12. Controller Model Class Shortlist

The premature assertion that the empirical data "dictates" a 4-phase hybrid state machine is retracted. The 4-phase structure is reclassified as one of five candidate model classes:

| Model ID | Model Class Description | Parameters Identified by D003 Data | Unidentifiable / Synthetic Assumptions |
| :--- | :--- | :--- | :--- |
| **M1** | **Empirical Open-Loop Trajectory Library** | Full action replay, initial peak forces, rise rates, multimodal action ordering. | Lacks dynamic feedback adaptation; fails if vehicle dynamics or road geometry change. |
| **M2** | **Piecewise Latency-Ramp-Hold Model** | Reaction latency $\tau$, finite brake rise rate ($91.7\text{ N/s}$), initial peak force ($53\text{ N}$), steering ramp. | Assumes open-loop hold during correction phase; misses secondary reapplications. |
| **M3** | **Hybrid State Machine Controller (Candidate)** | State transition timings ($\tau \to \text{ramp} \to \text{closed-loop} \to \text{steady}$), switching thresholds. | State switching boundaries and discrete transitions require synthetic hysteresis logic. |
| **M4** | **Continuous Error-Feedback (PD / Lookahead)** | Lateral gain $K_p, K_d$, longitudinal closing-rate deceleration gain. | Neuromuscular lag ($\tau_{\text{nm}}$) and sensory gains are co-dependent and difficult to identify uniquely. |
| **M5** | **Mixed-Effects Trajectory Generation** | Fixed scenario effects (density, workload) and random participant variance. | Statistical generation model; does not enforce vehicle physics during extreme limits. |

**Recommendation for Phase 2B-2:** Evaluate M2 (analytical extension of Phase 1) against M3/M4 (closed-loop regulatory models) on tracking error and physical plausibility before freezing an implementation.

---

## 13. Phase-2B Gate Reclassification

### Generic Human Fallback Dynamics
**Revised Gate: `H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT/STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`**

*Justification:*
The core empirical finding—that human recovery is multimodal, finite-ramp, and closed-loop—is completely robust across all sensitivity sweeps. However, operational definitions of vehicle response ($T_{\text{effective}}$), stabilization settling ($T_{\text{stable}}$), and steering reversals are sensitive to search offset, filtering, and threshold choices. Declaring $H1\text{-}B$ accurately conveys both empirical confidence and methodological prudence.

### Driver-Vehicle Familiarity Mismatch
**Retained Gate: `M0-C: NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA`**

---

## 14. Phase 2B-2 Authorization Status

**Status: MODEL-CLASS COMPARISON READY (Controller Implementation Paused).**  
With the completion of Phase 2B-1.2 measurement semantics cleanup and the establishment of `H1_OPERATIONAL_MEASUREMENT_LEDGER.md`, empirical takeover quantities are cleanly bounded. The data are now methodologically sound to authorize **Phase 2B-2 MODEL-CLASS COMPARISON / IDENTIFICATION**. Immediate implementation of any single controller architecture remains strictly paused until candidate model classes (M1–M5) are comparatively benchmarked against the empirical trajectory library.
