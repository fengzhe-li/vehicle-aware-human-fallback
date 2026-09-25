# Phase 2A — Public Human Takeover Data Exploitation Audit

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This audit overstated D003's readiness. Superseded: (1) the `H2A: PUBLIC DATA SUFFICIENT FOR REACTION + CLOSED-LOOP HUMAN MODEL` gate is not established; D003 has open blockers (multiple TOR values, unparsed `lane_gap`, unresolved brake-channel and authority semantics, road-dependent lane numbering, invalid collision proxy, factorial cells aliased with scenario state). (2) `laneGap` is not a documented direct signal: the raw header is `"...laneGap.0,time"`, each cell is a quoted pair, the current loaders parse it as 100% NaN, and "lane-centre offset" is only an inference. (3) "1,953 samples per trial" is false. (4) `M0-C` is narrowed: direct vehicle-response familiarity is not identifiable from verified public data checked; repeated-exposure learning is identifiable in D003; experience is associational only. (5) The dataset owners have already published takeover-time, button-time, minimum-TTC, maximum-deceleration and steering analyses of D003; this audit did not cite them. D003 blockers and the dataset owners' prior analyses: `research/data_matrix/D003_KNOWN_BLOCKERS.md`. Measurement rules: `docs/OBSERVATION_LAYER.md`. Status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Milestone:** Phase 2A — Public Human Takeover Data Exploitation Audit  
**Date:** 2026-09-21  
**Repository:** `vehicle-aware-human-fallback`  
**Current Baseline Commit:** `c09f682`  
**Frozen Baseline Tag:** `phase0-frozen` (`bc21fbce8b9b9518919fcaecd6a301785a1fee0d`)  
**Test Suite Status:** 39 passed (`pytest -q`)  

---

## 1. Executive Summary & Epistemic Scope Correction

### 1.1 The Central Misunderstanding Corrected
Prior project reviews (specifically within Branch C0 and the initial framing of H0) conflated two fundamentally distinct empirical questions:
1. **Question A (Generic Closed-Loop Human Takeover):** Do public datasets contain time-resolved, continuous human control inputs (steering, braking, accelerator) and vehicle trajectories during and after an automated driving takeover request (TOR)?
2. **Question B (Driver Familiarity & Internal-Model Mismatch):** Do public datasets identify driver prior vehicle experience (EV vs. ICE, one-pedal driving familiarity) and measure motor errors caused by a mismatch $M = D(\hat{f}_{\text{driver}}, f_{\text{vehicle}})$ across vehicle transitions?

Earlier notes observed that no public dataset labels driver EV-vs-ICE familiarity or manipulates vehicle braking response across trials for the same driver, and hastily summarized this as *"human experimental data is unavailable."* This conclusion was **false for Question A**.

Forensic inspection of released data files confirms that **public datasets provide rich, continuous, time-resolved human control trajectories during L3 takeovers**. Specifically, the **TU Delft Conditionally Automated Driving Takeover Dataset (D003)** provides **513 complete 20 Hz takeover trials** containing continuous brake pedal force in Newtons ($N$), continuous accelerator pedal displacement, continuous steering wheel angle, lateral lane deviation, continuous Time-to-Collision (TTC), and distance to a collision obstacle. In addition, **ADAS-TO (D001)** provides over 15,600 real-world naturalistic disengagements with continuous steering angle, steering torque, and millimeter-wave radar lead trajectories.

### 1.2 Dual Gate Classification
The human data feasibility is therefore formally separated into two distinct gates:
- **Generic Human Fallback Gate:**  
  $$\mathbf{H2A:}\quad \text{\textbf{PUBLIC DATA SUFFICIENT FOR REACTION + CLOSED-LOOP HUMAN MODEL}}$$  
  *(Public data directly supports reaction latency, initial action magnitude, closed-loop steering/braking correction, and post-takeover stabilization).*
- **Driver Familiarity / Mismatch Gate:**  
  $$\mathbf{M0\text{-}C:}\quad \text{\textbf{NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA}}$$  
  *(No public dataset contains driver prior vehicle experience labels or cross-vehicle response transitions; mismatch $M$ remains deferred as unresolved future work).*

---

## 2. Priority Dataset Forensic Audit

Every priority dataset was audited by inspecting actual published files, repository schemas, or remote archive contents rather than relying on paper abstracts.

| Dataset ID | Name | Source / Repository | Access Status | Scale & Population | Measured Sampling Rate | Primary Signals Present | Primary Signals Absent |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D001** | ADAS-TO | Hugging Face Hub (`HenryYHW/ADAS-TO`) / OpenLKA | Gated (CC BY-NC 4.0; manual approval) | 15,659 clips (paper) / 16,446 clips (HF); 327–364 drivers; 163–179 car models | Mixed: 61.7% at 10 Hz (`qlog`), 38.3% at 100 Hz (`rlog`) | `steeringAngleDeg`, `steeringTorque`, `vEgo`, `aEgo`, `radarState.leadOne.dRel/vRel`, `brakePressed` (bool), `gasPressed` (bool) | Continuous pedal position or force; driver demographics; vehicle familiarity |
| **D002** | TD2D | Zenodo (`10.5281/zenodo.14185964`); Nature Sci. Data 12:539 (2025) | Open Public (16.7 GB zip) | 50 participants; 500 cases; 10 secondary tasks | 130 Hz (ECG), 64 Hz (PPG), 4 Hz (EDA), 1 Hz (HR), 200 Hz (eye); scalar event log | Scalar `reactionTime` (ms), `takeoverSuccess` (Success/Fail), `criticalEventType`, `drivingExperience` (years), NASA-TLX | **Continuous steering, pedal, and vehicle trajectory time series are NOT present in the public Zenodo release** |
| **D003** | TU Delft Takeover Dataset | 4TU.ResearchData (`10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB`) | Open Public (450 MB zip) | 57 participants; 513 trials (9 scenarios per driver: 3 density $\times$ 3 workload) | **20.0 Hz constant** ($\Delta t = 0.050\text{ s}$ across 1,953 rows per trial) | Continuous `car_brake` (N), continuous `car_accelerator` [0:1], continuous `steeringWheelAngle` (rad), `steeringWheelSpeed` (rad/s), `speed_x/y`, `accel_x/y`, `laneGap`, `Time_Takeover_Request`, `Time_Manual_Start`, `Distance_to_Construction`, `Time_TTC` | Driver EV/ICE familiarity; vehicle response mapping was held constant across scenarios |
| **D004** | OpenLKA EV Dataset | GitHub (`OpenLKA/EV_Dataset`) | Open Public (direct Git repo) | Multiple routes / driver hashes (e.g. `bdda168c0c35fad7`) | ~100 Hz class (measured ~128 Hz from `wallTimeCentiseconds`) | Continuous `state_gas_pos` [0:1], `vEgo`, `aEgo`, `vLead1`, `lead1_spacing`, `op_enable` | Takeover/TOR events (highway cruising only); hard braking events unverified in sample |
| **D005** | OpenLKA Acceleration Dataset | GitHub (`OpenLKA/Acceleration_Dataset`) | Open Public (direct Git repo) | 12 EV models; 3 driver hashes for inspected Ioniq 5 | **~10 Hz measured** ($\Delta t \approx 0.10\text{ s}$, contradicts 100 Hz claim) | Continuous `v`, `a`, `padel` (accelerator) | **No brake channel exists in schema**; no steering; not a takeover dataset |

---

## 3. The 11 Core Forensic Questions Answered

### Q1: Which public datasets contain time-resolved human control?
- **TU Delft (D003):** Fully time-resolved at 20 Hz. **[AUDIT 2026-09-22: FALSE: row counts range 1,190–3,760, median 1,585]** ~~Every trial contains 1,953 time-stamped samples (~97 s)~~ capturing human pedal force, accelerator position, and steering wheel angle continuously before, during, and after the TOR.
- **ADAS-TO (D001):** Fully time-resolved at 10 Hz (61.7%) and 100 Hz (38.3%). Captures continuous steering wheel angle and steering torque throughout real-world disengagements.

### Q2: Which contain continuous pedal?
- **TU Delft (D003):** Contains **both** continuous brake pedal force in Newtons (`[00].VehicleUpdate-brake`, range 0 to $>500\text{ N}$) and continuous accelerator pedal displacement (`[00].VehicleUpdate-accelerator`, range 0.0 to 1.0).
- **OpenLKA EV Dataset (D004):** Contains continuous accelerator pedal position (`state_gas_pos`, 26 distinct values, 0.0 to 0.235 in cruise).
- **ADAS-TO (D001):** Pedal inputs are strictly **binary press flags** (`brakePressed`, `gasPressed`). Continuous pedal force or displacement is **not present**.
- **TD2D (D002):** **No pedal signals of any kind** are present in the public Zenodo release.
- **OpenLKA Acceleration (D005):** Contains continuous accelerator pedal (`padel`), but **zero brake channels**.

### Q3: Which contain continuous steering?
- **TU Delft (D003):** Full continuous bilateral steering wheel angle in radians (`[00].VehicleUpdate-steeringWheelAngle`), steering wheel angular velocity (`steeringWheelSpeed` in rad/s), and steering column torque (`steeringTorq` in $\text{N}\cdot\text{m}$).
- **ADAS-TO (D001):** Continuous steering wheel angle in degrees (`steeringAngleDeg`), angular velocity (`steeringRateDeg`), and steering column torque (`steeringTorque`).

### Q4: Which preserve trial order and repeated measures?
- **TU Delft (D003):** Strict repeated-measures Latin Square design. 57 participants completed all 9 factorial scenarios (3 traffic densities $\times$ 3 cognitive n-back workload levels). Trial execution order is documented in `1. data_dictionary.csv` and directory structure.
- **TD2D (D002):** 50 participants completed 10 repeated secondary-task scenarios each.
- **ADAS-TO (D001):** Contains multiple disengagement clips per unique `dongle_id` (vehicle/device) and `route_id` over time, but naturalistic driving lacks balanced factorial experimental ordering.

### Q5: Which support reaction-only modelling (Level H1)?
- **TU Delft (D003):** Supported with high precision. Explicit TOR timestamp (`Time_Takeover_Request`), button press disengagement timestamp (`Time_Manual_Start`), and continuous pedal/steering onset latencies.
- **TD2D (D002):** Supported. Provides scalar `reactionTime` (ms from critical event occurrence to first maneuver) across 500 cases and 10 distraction conditions.
- **ADAS-TO (D001):** Supported. Transition of `cruiseState.enabled` from `True` to `False` combined with `brakePressed` and `steeringPressed` flags yields naturalistic intervention latencies.

### Q6: Which support closed-loop correction modelling (Level H2)?
- **TU Delft (D003):** **Strongly supported**. Continuous 20 Hz recording of brake force, steering angle, and lateral lane deviation enables direct identification of secondary steering reversals, brake pedal modulations, and path corrections.
- **ADAS-TO (D001):** **Partially supported**. Supports closed-loop lateral steering corrections and yaw stabilization, but cannot model closed-loop brake force modulation due to binary pedal flags.
- **TD2D (D002):** **Not supported**. Withholding of continuous time series precludes any closed-loop correction analysis.

### Q7: Which support stabilisation analysis?
- **TU Delft (D003):** **Strongly supported**. Records vehicle speed, acceleration, yaw, ~~lane centerline offset (`roadInfo-laneGap.0`)~~ **[AUDIT 2026-09-22: `laneGap` is unparsed in current loaders and its meaning is undocumented]**, and distance to construction obstacle for tens of seconds post-takeover, directly enabling calculation of lane stabilization time, speed settling time, and minimum clearance.
- **ADAS-TO (D001):** **Partially supported**. Supports kinematic and steering stabilization relative to forward lead vehicles, but lacks fixed lane-marking geometry in the released CSVs.
- **TD2D (D002):** **Not supported**.

### Q8: Which support driver familiarity / mismatch (Level H3)?
- **None of the public datasets.** No public dataset records driver prior long-term vehicle ownership (EV vs. ICE), one-pedal driving habituation, or systematically manipulates vehicle deceleration response across trials for the same driver.

### Q9: Which signals are direct vs. proxies?
- **Direct Signals:**
  - $T_{TOR}$: Direct event marker in D003 (`Time_Takeover_Request`).
  - $T_{\text{manual\_start}}$: Direct button press in D003 (`Time_Manual_Start`).
  - Human inputs: Direct physical measurements in D003 (`car_brake` in N, `car_accelerator` [0:1], `steeringWheelAngle` in rad) and D001 (`steeringAngleDeg`, `steeringTorque`).
  - Kinematics: Direct sensor values in D003 and D001 ($v$, $a$, lane gap, obstacle distance).
- **Proxy Signals:**
  - Collision outcome in D001: Curated 749 safety-critical events serve as near-crash proxies; real crashes are absent.
  - Driver competence in D003: Survey scores (`takeover_skill`, `takeover_style`) are self-reported proxies for motor control skill.
  - Urgency in D002: Scenario category (L/R/F) is a proxy for visual looming demand.

### Q10: What human model complexity is currently identifiable?
- The public data from D003 and D001 directly identifies a **Piecewise Interpretable Closed-Loop Controller**:
  1. *Perception & Reaction Latency:* $t_1 \sim \mathcal{D}_{\text{reaction}}(\text{urgency, workload})$
  2. *Initial Open-Loop Action:* Initial steering rate and brake force ramp ($t_2, t_3$)
  3. *Closed-Loop State-Feedback Correction:* Proportional-derivative feedback on TTC, hazard distance, and lane offset:
     $$u_{\text{brake}}(t) = K_p (d_{\text{hazard}} - d_{\text{desired}}) + K_d \dot{d}_{\text{hazard}}$$
     $$u_{\text{steer}}(t) = -K_y y_{\text{lane}} - K_{\psi} \psi$$
  4. *Stabilisation Regime:* Asymptotic convergence to lane center and target following distance.

### Q11: What remains impossible from public data?
- Identifying parameters of driver cognitive miscalibration $\Delta K = \hat{K}_{\text{vehicle}} - K_{\text{vehicle}}$ arising from driving an EV after habituation to an ICE vehicle.
- Fitting proprietary OEM brake-by-wire hydraulic blending curves.

---

## 4. Separation of Three Human-Modelling Levels

```
+---------------------------------------------------------------------------------------+
| LEVEL H1: REACTION / FIRST ACTION                                                     |
| Signals: T_TOR, T_first_brake, T_first_steer, Reaction Latency Distribution           |
| Data Sources: TU Delft (D003), ADAS-TO (D001), TD2D (D002)                            |
| Feasibility: FULLY IDENTIFIABLE FROM PUBLIC DATA                                      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| LEVEL H2: CLOSED-LOOP RECOVERY & STABILISATION                                        |
| Signals: Continuous Brake Force (N), Steering Angle (rad), Lane Gap (m), Settling Time|
| Data Sources: TU Delft (D003) [Full Longitudinal + Lateral], ADAS-TO (D001) [Lateral] |
| Feasibility: FULLY IDENTIFIABLE FROM PUBLIC DATA (D003 Breakthrough)                  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| LEVEL H3: INTERNAL-MODEL / FAMILIARITY MISMATCH                                       |
| Signals: Prior Vehicle Exposure, Cross-Vehicle Transfer Error, Regen Expectation      |
| Data Sources: None in current public inventory                                        |
| Feasibility: NOT IDENTIFIABLE (M0-C) — DEFERRED TO FUTURE HUMAN EXPERIMENTS          |
+---------------------------------------------------------------------------------------+
```

---

## 5. Temporal Recovery Taxonomy: Grounded Operational Definitions

The project charter distinguished three nominal milestones: $T_{\text{authority}}$, $T_{\text{effective}}$, and $T_{\text{stable}}$. Using the signals available in D003 and D001, we formulate mathematically observable definitions:

### 5.1 $T_{\text{authority}}$ (Authority Transfer Instant)
- **Direct Definition:** The precise timestamp at which the automated system issues the TOR or transitions control ownership to the human:
  $$T_{\text{authority}} \equiv t_{\text{TOR}}$$
- **Observable Channel:** D003 `[72 (Time/Time_Takeover_Request)].ExportChannel-val`; D001 transition `cruiseState.enabled: True -> False`.
- **Threshold Dependence:** Exact digital flag transition; zero threshold ambiguity.

### 5.2 $T_{\text{first}}$ (First Detectable Human Input)
- **Direct Definition:** The earliest timestamp after $T_{\text{authority}}$ at which either human steering input or human pedal input exceeds sensor noise thresholds:
  $$T_{\text{first}} \equiv \min \left( t_{\text{steer\_onset}}, t_{\text{brake\_onset}}, t_{\text{accel\_release}} \right)$$
  where:
  - $t_{\text{steer\_onset}} = \inf \{ t > t_{\text{TOR}} \mid |\delta_{\text{sw}}(t) - \delta_{\text{sw}}(t_{\text{TOR}})| > \epsilon_{\delta} \}$ (with $\epsilon_{\delta} = 0.035\text{ rad} \approx 2^\circ$)
  - $t_{\text{brake\_onset}} = \inf \{ t > t_{\text{TOR}} \mid F_{\text{brake}}(t) > \epsilon_{F} \}$ (with $\epsilon_{F} = 15\text{ N}$)
- **Observable Channel:** D003 `[00].VehicleUpdate-steeringWheelAngle`, `[00].VehicleUpdate-brake`; D001 `brakePressed == True`, `steeringPressed == True`.

### 5.3 $T_{\text{effective}}$ (First Effective Trajectory Modification)
- **Direct Definition:** The timestamp at which human-commanded actuation causes realized vehicle deceleration or lateral curvature to exceed baseline drift:
  $$T_{\text{effective}} \equiv \inf \{ t > T_{\text{first}} \mid a_x(t) \le a_{\text{baseline}} - \Delta a_{\text{eff}} \quad \text{or} \quad |\ddot{y}(t)| > \Delta a_{y,\text{eff}} \}$$
  with operational thresholds $\Delta a_{\text{eff}} = 0.5\text{ m/s}^2$, $\Delta a_{y,\text{eff}} = 0.3\text{ m/s}^2$.
- **Physical Interpretation:** Directly corresponds to $t_1 + t_2$ in the Phase 1 analytical model, where $t_2$ represents physical actuator transport and build-up delay.
- **Observable Channel:** D003 `[00].VehicleUpdate-accel.001`, `accel.002`; D001 `carState.aEgo`.

### 5.4 $T_{\text{stable}}$ (Trajectory Stabilization)
- **Direct Definition:** The earliest timestamp after which vehicle trajectory and control activity remain bounded within steady-state driving tolerances for at least $T_{\text{window}} = 2.0\text{ s}$:
  $$T_{\text{stable}} \equiv \inf \left\{ t > T_{\text{effective}} \;\middle|\; \forall \tau \in [t, t + T_{\text{window}}]: |y_{\text{lane}}(\tau)| \le \epsilon_y \land |\dot{\delta}_{\text{sw}}(\tau)| \le \epsilon_{\dot{\delta}} \land a_x(\tau) \ge -\epsilon_a \right\}$$
  with $\epsilon_y = 0.30\text{ m}$, $\epsilon_{\dot{\delta}} = 0.10\text{ rad/s}$, $\epsilon_a = 0.5\text{ m/s}^2$.
- **Observable Channel:** D003 `[00].VehicleUpdate-roadInfo-laneGap.0`, `steeringWheelSpeed`, `accel.001`.

---

## 6. Correction and Stabilization Metrics Evaluation

The 12 candidate metrics specified for post-takeover performance are audited against public dataset signals:

| Metric | Scientific Object | TU Delft (D003) | ADAS-TO (D001) | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Brake reapplication count** | Secondary foot modulations / hesitation | Measured from continuous $F_{\text{brake}}(t)$ peaks | Binary flag transitions only | **COMPUTABLE WITH THRESHOLD** (D003: force valleys $> 30\text{ N}$) |
| **Accelerator correction count** | Inappropriate throttle inputs post-TOR | Measured from continuous accelerator [0:1] | Binary `gasPressed` pulses | **COMPUTABLE WITH THRESHOLD** (D003, D004) |
| **Sign changes in control derivative** | Oscillatory steering or pedal pumping | Direct zero-crossings of `steeringWheelSpeed` | Direct zero-crossings of `steeringRateDeg` | **DIRECTLY COMPUTABLE** (D003, D001) |
| **Peak steering correction** | Maximum evasive steering amplitude | $\max |\delta_{\text{sw}}(t) - \delta_{\text{sw}}(t_{\text{TOR}})|$ | $\max |\text{steeringAngleDeg}(t)|$ | **DIRECTLY COMPUTABLE** (D003, D001) |
| **Peak braking correction** | Maximum deceleration demand | $\max F_{\text{brake}}(t)$ (Newtons) | Not available (binary press only) | **DIRECTLY COMPUTABLE** (D003) |
| **Control-input settling time** | Time until human inputs cease oscillating | Time to $|\dot{\delta}_{\text{sw}}| \le 0.05\text{ rad/s} \land \dot{F}_{\text{brake}} \approx 0$ | Steering rate settling only | **COMPUTABLE WITH THRESHOLD** (D003, D001) |
| **Acceleration settling time** | Time until vehicle jerk subsides | Time to $|\dot{a}_x| \le 0.5\text{ m/s}^3$ | Time to $|\dot{a}_{\text{Ego}}| \le 0.5\text{ m/s}^3$ | **COMPUTABLE WITH THRESHOLD** (D003, D001, D004) |
| **Lane stabilisation time** | Time to settle within lane boundaries | Time to $|y_{\text{lane}}| \le 0.30\text{ m}$ for $2\text{ s}$ | Not available (no lane gap field) | **COMPUTABLE WITH THRESHOLD** (D003) |
| **TTC recovery time** | Time until TTC turns positive / safe | Time until $\text{TTC} > 4.0\text{ s}$ or $\dot{d}_{\text{lead}} \ge 0$ | Time until lead closing speed $\le 0$ | **COMPUTABLE WITH THRESHOLD** (D003, D001) |
| **Minimum gap** | Minimum physical clearance to obstacle | $\min (\text{Distance\_to\_Construction})$ | $\min (\text{leadOne.dRel})$ | **DIRECTLY COMPUTABLE** (D003, D001) |
| **Stopping margin** | Residual clearance when $v \to 0$ | Distance to construction at standstill | Clearance when lead/ego stops | **DIRECTLY COMPUTABLE** (D003, D001) |
| **Takeover success / failure** | Accident avoidance indicator | Collision flag or min gap $> 0$ | Curated safety-critical subset | **DIRECTLY COMPUTABLE** (D003; D002 scalar; D001 proxy) |

---

## 7. Human Controller Complexity Support

To ground the future Phase 2B modeling work, candidate controller classes were evaluated:

| Model Class | Mathematical Description | Identified from Public Data? | Scientific Verdict |
| :--- | :--- | :--- | :--- |
| **Class A: Delay + First-Action Magnitude** | Open-loop step: $u(t) = U_0 \cdot \mathbb{I}(t \ge t_1)$ | Yes (TD2D, TU Delft, ADAS-TO) | **Sufficient for Phase 1 analytical boundary**, but misses all post-takeover correction and stabilization dynamics. |
| **Class B: Piecewise State Machine** | Latency $\to$ Initial Ramp $\to$ Closed-Loop Correction $\to$ Stabilization | **Yes (TU Delft D003)** | **RECOMMENDED FOR PHASE 2B**. Minimally parameterized, fully identifiable, directly mirrors observed phases in D003 telemetry. |
| **Class C: Simple State-Feedback** | $u(t) = -K_p e(t - \tau) - K_d \dot{e}(t - \tau)$ | **Yes (TU Delft D003, ADAS-TO)** | **VIABLE ALTERNATIVE**. Identifies human feedback gains on gap and lane offset with perceptual delay $\tau$. |
| **Class D: Mixed-Effects Behavioral Model** | $\theta_i = \bar{\theta} + u_i$, $u_i \sim \mathcal{N}(0, \Sigma)$ | **Yes (TU Delft D003: 57 drivers $\times$ 9 trials)** | **RECOMMENDED AS EXTENSION**. Captures inter-individual driver variance without unconstrained overfitting. |
| **Class E: Deep Neural Networks / RL** | End-to-end black-box policy | Unconstrained / Non-identifiable | **EXCLUDED**. Violates interpretability and epistemic constraints of the research charter. |

---

## 8. Targeted Sub-Audit: Driver Familiarity & Vehicle Mismatch ($M$)

A targeted audit was performed across published literature and open datasets to locate any empirical records of:
- Cross-vehicle transitions (e.g., driver tested in ICE vehicle, then immediately tested in EV).
- Longitudinal braking gain adaptation across repeated takeover trials.
- One-pedal driving familiarity metrics linked to takeover performance.

**Findings:**
1. While simulator studies exist on steering-gain adaptation (e.g., L012: *Sensorimotor adaptation when steering with altered vehicle dynamics*, 2018), these studies focus exclusively on lateral steering gain in manual driving, not longitudinal emergency braking during an automated TOR.
2. Studies evaluating one-pedal driving (e.g., L004: *One-pedal or two-pedal*, 2024) compare between-subject groups or single-session conditions, but **do not provide open raw time-series repositories** capturing trial-by-trial adaptation or habituation carryover.
3. No public dataset in our inventory records whether drivers regularly operate an EV or an ICE vehicle, nor does any dataset expose vehicle pedal mapping switches.

**Conclusion:**  
Estimating the cognitive/motor mismatch parameter $M = D(\hat{f}_{\text{driver}}, f_{\text{vehicle}})$ remains **strictly non-identifiable from existing public data**. It is assigned to gate **`M0-C`** and must remain an explicit, transparently disclosed boundary for future human-subject experimental research.

---

## 9. Data Acquisition, Access, and Verification Protocols

To maintain full reproducibility without committing multi-gigabyte binaries into Git:
- **TU Delft (D003):** Verified accessible via 4TU.ResearchData DOI `10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB`. Remote archive size: 450,332,391 bytes. Individual trials and data dictionary can be parsed directly via HTTP Range requests without local disk bloat.
- **ADAS-TO (D001):** Documented at Hugging Face `HenryYHW/ADAS-TO` under CC BY-NC 4.0. Gated access requires manual maintainer approval.
- **TD2D (D002):** Verified on Zenodo DOI `10.5281/zenodo.14185964`. Archive size: 16,740,790,935 bytes.
- **OpenLKA EV (D004) & Accel (D005):** Verified committed in public GitHub repositories under OpenLKA organization.

---

## 10. Phase-2 Gate Classifications & Exact Next Step

### Gate Classifications

$$\begin{aligned}
\textbf{Generic Human Fallback Gate:} &\quad \mathbf{H2A:}\; \text{\textbf{PUBLIC DATA SUFFICIENT FOR REACTION + CLOSED-LOOP MODEL}} \\
\textbf{Familiarity Mismatch Gate:} &\quad \mathbf{M0\text{-}C:}\; \text{\textbf{NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA}}
\end{aligned}$$

### Exact Next Project Step
In accordance with the decision framework:
> **Phase 2B — Build the Minimal Interpretable Human Fallback Model from Public Trajectory Data (D003).**
>
> Formulate a transparent, low-dimensional piecewise closed-loop human controller (latency $\to$ initial action ramp $\to$ proportional-derivative correction $\to$ stabilization) parameterized directly by empirical fits to the 513 trials of TU Delft (D003), while retaining familiarity mismatch ($M$) as an explicitly separated, unresolved boundary.
