# Phase 2B-1: Empirical Human Takeover Recovery Characterisation

> **R2A NOTICE (2026-09-22).** D003 accelerator, brake and steering channels are not driver-only channels (blocker B17: structured, scenario-cell-specific changes within 0.3 s of TOR). All human first-input quantities in this document (`T_first`, first brake/steering input, brake-first vs steer-first, negative handover lag, brake-rise latency, driver-attributed maximum braking or steering) are **INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS**. They are preserved for audit history; see `results/HISTORICAL_OUTPUTS_MANIFEST.md` and `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §9.

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** All results in this document are PRE-AUDIT ARTIFACTS, retained for traceability, and are not current findings. Withdrawn: `T_stable` ≈ 22–23 s, "100% settled", and its use as human stabilisation (~81% of nominal values occur after `Time_Manual_Stop`, i.e. after the driver returned control to automation; within the human-control window only ~18% settle). Invalid as computed: brake extrema, reapplication and full-record reversal counts (windows include automation). Withdrawn: the collision proxy (disagrees with lane occupancy at the hazard station) and all causal workload/density language. Unresolved: brake-channel semantics ("pedal force" is not established) and whether pre-button input controls the vehicle. Button time and takeover time replicate metrics published by the dataset owners (arXiv 2507.22252; 466 takeovers after exclusions), which this document did not cite. The 26 multi-TOR trials (25 in density 20 / 1-back) were not flagged. D003 blockers and the dataset owners' prior analyses: `research/data_matrix/D003_KNOWN_BLOCKERS.md`. Measurement rules: `docs/OBSERVATION_LAYER.md`. Status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** COMPLETE **[AUDIT 2026-09-22: PRE-AUDIT ARTIFACT; see notice]**  
**Primary Dataset:** D003 — TU Delft Conditionally Automated Driving Takeover Dataset (DOI: `10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB`)  
**Repository Scope:** `experiments/H_human_internal_model/H1_EMPIRICAL_RECOVERY_ANALYSIS.md`  
**Gate Classifications:**
- **Generic Fallback Dynamics:** `H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT/STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`
- **Driver-Vehicle Familiarity Mismatch:** `M0-C: NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA` (retained from Phase 2A)

---

## 1. Executive Summary

This report establishes the empirical reality of human takeover recovery behaviour by analyzing all 513 continuous 20 Hz trajectory recordings from 57 human participants in the TU Delft conditionally automated driving dataset (D003).

Prior to Phase 2B-1, theoretical literature and Phase 1 models operated on simplifying heuristics tailored to an unavoidable forward collision boundary:
1. A simplified human command assumption: reaction latency $t_1 \approx 1.2\text{ s}$ followed by full step braking demand ($u = 1.0$);
2. Physical vehicle deceleration modeled with finite vehicle / braking response delay ($t_2$) and build-up ramp ($t_3$);
3. An unavoidable longitudinal stopping boundary condition held until full standstill ($v = 0$), where steering is held zero ($a_y \equiv 0$);
4. Absence of closed-loop correction cycles or evasive steering interaction in the human command.

The empirical analysis across all 513 trials characterizes human recovery in an evasive lane-change maneuver:
- **Takeover Timeline & Manual-Mode Switch:** The median duration from Takeover Request (TOR) alarm to manual-mode-switch button press ($T_{\text{manual\_start}}$) is **$1.650\text{ s}$** (IQR: $1.250 - 2.001\text{ s}$, mean: $1.717 \pm 0.769\text{ s}$). Crucially, human motor input does not wait for manual switch confirmation: in **60.2%** of trials, drivers touch the brake pedal prior to pressing the manual takeover button, and in **31.7%** they initiate steering. The earliest active control input occurs at median **$1.125\text{ s}$** (IQR: $0.400 - 1.250\text{ s}$).
- **Action Sequencing (Braking vs Steering):** In 498 valid TOR trials, initial action sequence is **62.85% brake-first** (313 trials), **32.13% steer-first** (160 trials), and **5.02% simultaneous** (25 trials within $\pm 100\text{ ms}$). The median latency between first action and second action is **$2.550\text{ s}$** (IQR: $1.500 - 4.550\text{ s}$).
- **Non-Step Braking Dynamics:** Drivers do not apply a step input. Brake force rises with a finite median rate of **$91.73\text{ N/s}$** (mean: $143.99\text{ N/s}$) reaching peak force after median **$0.750\text{ s}$** (mean: $0.890\text{ s}$). The median initial peak brake force is **$53.08\text{ N}$** (IQR: $26.82 - 161.88\text{ N}$).
- **[AUDIT 2026-09-22: INVALID AS COMPUTED: brake-extrema/reapplication windows and the "13.0 across the full record" reversal count include automation after `Time_Manual_Stop`.]** **Closed-Loop Correction Cycles:** Takeover recovery is inherently closed-loop and oscillatory. Across the manual takeover phase, drivers exhibit a median of **3.0 brake extrema**, **2.0 brake reapplications** (with **68.3%** of all trials exhibiting $\ge 1$ reapplication), and a median of **2.0 acute steering reversals** via the amplitude-hysteresis detector ($13.0$ across the full 60s record).
- **Incomplete Stop (Evasive Maneuver):** Drivers do not brake to a standstill. Speed drops by a median of only **$8.31\text{ m/s}$** from an initial cruising speed of $25.04\text{ m/s}$, reaching a minimum post-TOR speed of median **$16.95\text{ m/s}$** (mean: $14.87\text{ m/s}$). In 499 of 513 trials, drivers successfully execute an evasive lane change around the stationary hazard.
- **[AUDIT 2026-09-22: CAUSAL LANGUAGE WITHDRAWN: cells are aliased with road, speed at TOR (19.3–27.8 m/s), distance, starting lane and pre-TOR automation duration; the escape-gap mechanism is untested; brake semantics unresolved. Descriptive, condition-associated only.]** **Cognitive Load & Density Effects:** Under high cognitive distraction (2-back), reflexive braking increases to **84.8%** (versus 33.3% in 0-back), while high traffic density (20 veh/km) nearly triples mean peak brake force from $58.7\text{ N}$ to $166.7\text{ N}$ because adjacent lane escape gaps are constrained.
- **[AUDIT 2026-09-22: `T_stable` WITHDRAWN (~81% of values occur after handback to automation); `T_pass` retained as a geometric crossing only.]** **Stabilization & Obstacle Passage Metrics:** Control-input derivative settling ($T_{\text{stable}}$) settles in **100%** of trials at median **$22.2 - 23.0\text{ s}$** post-TOR across post-maneuver anchors; obstacle longitudinal station passage ($T_{\text{pass}}$) occurs in **100.0%** of valid TOR trials at median **$8.95\text{ s}$** post-TOR (safe lateral clearance $T_{\text{safe\_clear}}$ is unidentifiable from D003 telemetry).

---

## 2. Dataset Description & Forensic Quality Audit (QA)

### 2.1 Dataset Structure & Acquisition
- **Dataset Identifier:** D003 (TU Delft Automated Driving Takeover Experiment, Xiao et al., 2021).
- **Participants:** $N = 57$ licensed drivers (IDs 1–57).
- **Design:** $3 \times 3$ within-subject full factorial repeated measures:
  - Traffic density: $0, 10, 20\text{ vehicles/km}$ (surrounding traffic flow).
  - Cognitive load: $0\text{-back}$ (baseline), $1\text{-back}$ (moderate), $2\text{-back}$ (high auditory cognitive distraction).
  - Total trials: $57 \times 3 \times 3 = 513$ trials.
- **Sampling Rate:** Verified strictly constant at **$20.00\text{ Hz}$** ($\Delta t = 0.0500\text{ s}$, standard deviation across all 513 trials $< 10^{-7}\text{ s}$).
- **Trial Durations:** Mean duration is $83.97\text{ s}$ (min: $59.45\text{ s}$, max: $187.95\text{ s}$).
- **Timestamp Integrity:** Monotonicity is verified in **513 of 513 trials** (100.0%) after trimming trailing empty newline delimiters [AUDIT R1 2026-09-22: in 42 trials the trimmed row is not an empty delimiter but an export-channel footer; see D003 blocker B3]. Zero duplicate timestamps.

### 2.2 Forensic QA Classification
Every trial in `research/data_matrix/d003_trial_qa.csv` was audited against rigorous criteria:

| Usable Status | Count | Percentage | Reason Code & Epistemic Rationale |
| :--- | :---: | :---: | :--- |
| `USABLE_FULL` | 492 | 95.91% | `NONE`: Full trial with valid scheduled TOR, clean button disengagement, monotonic 20 Hz telemetry, and safe hazard evasion. |
| `USABLE_PREEMPTIVE` | 15 | 2.92% | `PREEMPTIVE_TAKEOVER_NO_TOR_ISSUED`: In 15 specific trials, the driver recognized the upcoming construction hazard ahead of time and pushed the manual takeover button $0.20\text{ s}$ to $1.15\text{ s}$ prior to the scheduled alarm. The simulator cleanly handed over authority and cancelled the acoustic alarm. Telemetry is fully valid. |
| `DERIVED_COLLISION_PROXY` | 6 | 1.17% | `COLLISION_WITH_HAZARD`: Operational proxy based on $d_{\text{hazard}} \le 0.0\text{ m}$ at speed $> 3.0\text{ m/s}$ prior to or without lane change completion. (No source sensor ground truth exists). |
| `FLAGGED_TIMESTAMPS` | 0 | 0.00% | No non-monotonic timestamps or corrupted sample intervals were detected. |
| **Total** | **513** | **100.0%** | Full dataset audited and accounted for. |

---

## 3. Event Timeline & Latency Distributions (The 5 Events)

### 3.1 Five-Event Definitions
1. $T_{\text{request}}$: Time of acoustic/visual Takeover Request (TOR) issuance (ground truth from simulator event log).
2. $T_{\text{manual\_start}}$ (observed button press): The logged clock instant when the driver depressed the steering wheel button to disengage automation (conceptual authority transition $T_{\text{authority}}$ remains a distinct theoretical milestone).
3. $T_{\text{first}}$: Time of earliest active human motor control input:
   - $T_{\text{first\_brake}}$: Brake pedal force exceeds $15.0\text{ N}$;
   - $T_{\text{first\_steer}}$: Steering wheel angle deviation from baseline $> 0.05\text{ rad}$ ($2.86^\circ$);
   - $T_{\text{first\_ctrl}} = \min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$.
4. $T_{\text{effective}}$: Time when physical vehicle response is detected:
   - Causally constrained detector: vehicle response must begin at or after the corresponding human motor actuation ($T_{\text{effective\_dec}} \ge T_{\text{first\_brake}}$, $T_{\text{effective\_lat}} \ge T_{\text{first\_steer}}$). (Note: unconstrained search yielded 39.36% causal artifacts due to automated throttle cut).
5. $T_{\text{stable}}$ vs $T_{\text{pass}}$:
   - $T_{\text{pass}}$: Obstacle longitudinal station passage instant ($d_{\text{hazard}} \le 0.0\text{ m}$; geometric station crossing, safe clearance unidentifiable).
   - $T_{\text{stable}}$: Trajectory control derivative settling into bounded steady-state highway cruising.

### 3.2 Quantitative Summary of Timeline Intervals ($N = 498$ valid TOR trials)

| Timeline Interval / Event | Median | IQR | 25th % | 75th % | Mean $\pm$ SD | Min | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $\Delta T_{\text{manual\_start}} = T_{\text{man\_start}} - T_{\text{req}}$ | **$1.650\text{ s}$** | $0.750\text{ s}$ | $1.250\text{ s}$ | $2.001\text{ s}$ | $1.717 \pm 0.769\text{ s}$ | $0.100\text{ s}$ | $6.901\text{ s}$ |
| $T_{\text{first\_ctrl}} - T_{\text{req}}$ (First Active Input) | **$1.125\text{ s}$** | $0.850\text{ s}$ | $0.400\text{ s}$ | $1.250\text{ s}$ | $1.018 \pm 0.644\text{ s}$ | $0.000\text{ s}$ | $4.251\text{ s}$ |
| $T_{\text{first\_brake}} - T_{\text{req}}$ (Brake Onset) | **$1.200\text{ s}$** | $1.200\text{ s}$ | $0.850\text{ s}$ | $2.050\text{ s}$ | $4.812 \pm 10.348\text{ s}$ | $0.000\text{ s}$ | $50.350\text{ s}$ |
| $T_{\text{first\_steer}} - T_{\text{req}}$ (Steer Onset) | **$3.000\text{ s}$** | $3.437\text{ s}$ | $1.100\text{ s}$ | $4.537\text{ s}$ | $3.034 \pm 2.235\text{ s}$ | $0.150\text{ s}$ | $16.200\text{ s}$ |
| $T_{\text{first\_ctrl}} - T_{\text{man\_start}}$ (Control vs Button) | **$-0.650\text{ s}$** | $1.087\text{ s}$ | $-1.287\text{ s}$ | $-0.200\text{ s}$ | $-0.699 \pm 0.998\text{ s}$ | $-6.600\text{ s}$ | $2.551\text{ s}$ |
| Causal Longitudinal Delay ($T_{\text{eff\_dec}} - T_{\text{first\_brake}}$) | **$0.050 - 0.100\text{ s}$** | $0.550\text{ s}$ | $0.050\text{ s}$ | $0.600\text{ s}$ | $1.429 \pm 4.834\text{ s}$ | $0.050\text{ s}$ | $43.100\text{ s}$ |
| Causal Lateral Delay ($T_{\text{eff\_lat}} - T_{\text{first\_steer}}$) | **$0.900\text{ s}$** | $1.950\text{ s}$ | $0.450\text{ s}$ | $2.400\text{ s}$ | $1.781 \pm 4.115\text{ s}$ | $0.050\text{ s}$ | $61.050\text{ s}$ |
| $T_{\text{pass}} - T_{\text{req}}$ (Obstacle Station Passage) | **$8.950\text{ s}$** | $3.300\text{ s}$ | $7.800\text{ s}$ | $11.100\text{ s}$ | $10.676 \pm 7.012\text{ s}$ | $3.950\text{ s}$ | $79.250\text{ s}$ |
| ~~$T_{\text{stable}} - T_{\text{req}}$ (Post-Maneuver Settled)~~ **[AUDIT 2026-09-22: WITHDRAWN]** | ~~22.2–23.0 s~~ | $7.5 - 7.8\text{ s}$ | $16.5\text{ s}$ | $26.8\text{ s}$ | $23.6 - 25.0\text{ s}$ | $1.850\text{ s}$ | $122.950\text{ s}$ |

### 3.3 Critical Epistemic Discovery: Negative Handover Lag ($T_{\text{first}} < T_{\text{manual\_start}}$)
A major empirical insight is that **$T_{\text{manual\_start}}$ (the formal button-press handover flag) does NOT mark the beginning of human control**.
- In **60.2%** of trials, $T_{\text{first\_brake}} < T_{\text{manual\_start}}$.
- In **31.7%** of trials, $T_{\text{first\_steer}} < T_{\text{manual\_start}}$.
- Across all active inputs, $T_{\text{first\_ctrl}} - T_{\text{manual\_start}}$ has a negative median of **$-0.650\text{ s}$**.
- *Physical Explanation:* When startled by the TOR alarm, drivers physically press their foot onto the brake pedal ($1.20\text{ s}$) or grab and twist the wheel, and simultaneously or shortly thereafter click the disengagement button on the wheel spoke ($1.65\text{ s}$). Formal supervisory architectures that treat the button-press event as the exact instant human intervention begins mischaracterize human motor psychology by $0.4$ to $1.2\text{ seconds}$.

---

## 4. Action Sequence Ordering & Coupling

### 4.1 Distribution of Sequence Types
Analyzing whether drivers brake first, steer first, or act simultaneously ($|\Delta t| \le 100\text{ ms}$):

| Action Sequence Category | Definition | Trials ($N = 498$) | Percentage |
| :--- | :--- | :---: | :---: |
| **Brake First** | $T_{\text{first\_brake}} < T_{\text{first\_steer}} - 100\text{ ms}$ | **313** | **62.85%** |
| **Steer First** | $T_{\text{first\_steer}} < T_{\text{first\_brake}} - 100\text{ ms}$ (incl. 5 steer-only) | **160** | **32.13%** |
| **Simultaneous** | $\|T_{\text{first\_steer}} - T_{\text{first\_brake}}\| \le 100\text{ ms}$ | **25** | **5.02%** |
| **Throttle Release Only** | Throttle dropped without brake or steer | 0 | 0.00% |
| **Total** | | **498** | **100.0%** |

### 4.2 Inter-Action Latency
Among trials exhibiting both braking and steering ($N = 493$):
- Median absolute time between first and second action: **$2.550\text{ s}$** (IQR: $1.500 - 4.550\text{ s}$, mean: $5.832 \pm 9.602\text{ s}$).
- In brake-first trials, drivers brake at median $1.20\text{ s}$ to shed kinetic energy and buy decision time, then initiate the evasive lane change at median $3.00\text{ s}$ once adjacent traffic gaps have been assessed.
- In steer-first trials (prominent under low cognitive load and open traffic), drivers immediately initiate lane change and apply light trail-braking or no braking.

---

## 5. Initial Control Metrics: Refuting the Step Brake Assumption

### 5.1 Measured Initial Control Characteristics ($N = 498$ valid TOR trials)

| Metric | Median | IQR | Mean $\pm$ SD | Min | Max |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Peak Brake Force ($N$)** | **$53.08\text{ N}$** | $135.06\text{ N}$ | $106.28 \pm 103.14\text{ N}$ | $15.08\text{ N}$ | $400.00\text{ N}$ |
| **Brake Rise Rate ($\text{N/s}$)** | **$91.73\text{ N/s}$** | $175.46\text{ N/s}$ | $143.99 \pm 151.80\text{ N/s}$ | $0.80\text{ N/s}$ | $688.13\text{ N/s}$ |
| **Time to Peak Brake ($\text{s}$)** | **$0.750\text{ s}$** | $1.300\text{ s}$ | $0.890 \pm 0.677\text{ s}$ | $0.000\text{ s}$ | $2.000\text{ s}$ |
| **Initial Peak Steering ($^\circ$)** | **$6.24^\circ$** | $6.08^\circ$ | $8.91 \pm 8.57^\circ$ | $2.90^\circ$ | $115.11^\circ$ |
| **Initial Steering Rate ($^\circ/\text{s}$)** | **$21.29^\circ/\text{s}$** | $27.57^\circ/\text{s}$ | $26.94 \pm 28.66^\circ/\text{s}$ | $0.62^\circ/\text{s}$ | $374.51^\circ/\text{s}$ |
| **Speed at $T_{\text{first}}$ ($\text{m/s}$)** | **$25.04\text{ m/s}$** | $3.48\text{ m/s}$ | $24.68 \pm 2.86\text{ m/s}$ | $18.57\text{ m/s}$ | $27.77\text{ m/s}$ |
| **Minimum Speed Post-TOR ($\text{m/s}$)** | **$16.95\text{ m/s}$** | $7.29\text{ m/s}$ | $14.87 \pm 6.77\text{ m/s}$ | $-0.07\text{ m/s}$ | $25.00\text{ m/s}$ |
| **Total Speed Drop ($\text{m/s}$)** | **$8.31\text{ m/s}$** | $8.64\text{ m/s}$ | $9.81 \pm 6.90\text{ m/s}$ | $0.02\text{ m/s}$ | $27.81\text{ m/s}$ |

### 5.2 Key Takeaways for Human Response Modelling
1. **Brake Application is Continuous, Not Instantaneous:** The median rise time to peak is $0.75\text{ s}$ at $91.7\text{ N/s}$. Assuming an instantaneous step deceleration $a_x = -3.5\text{ m/s}^2$ overestimates deceleration during the critical $0.75\text{ s}$ window immediately following reaction time $\tau$.
2. **Speed Drop is Bounded ($\approx 8\text{ m/s}$):** Humans do not emergency stop when an evasive steering corridor is available. They slow from $25\text{ m/s}$ ($90\text{ km/h}$) to $17\text{ m/s}$ ($61\text{ km/h}$), completing the lane change while maintaining substantial forward momentum.

---

## 6. Closed-Loop Correction Dynamics: Oscillations & Reapplications

### 6.1 Correction Metrics Across All Usable Trials ($N = 498$)

| Correction Metric | Median | IQR | Mean $\pm$ SD | Min | Max | Trials with $\ge 1$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Brake Extrema (Peaks/Valleys)** | **3.0** | 3.0 | $3.61 \pm 2.40$ | 0 | 19 | 98.4% |
| **Brake Reapplications** | **2.0** | 4.0 | $2.56 \pm 3.03$ | 0 | 22 | **68.3%** |
| **Brake Derivative Sign Changes** | **12.0** | 11.0 | $15.30 \pm 19.52$ | 0 | 233 | 87.1% |
| **Steering Reversals ($\Delta \delta_{\text{sw}} \ge 0.05\text{ rad}$)** | **70.5** | 54.0 | $80.70 \pm 54.95$ | 4 | 264 | **100.0%** ($\ge 2$) |
| **Steering Rate Sign Changes** | **113.5** | 113.5 | $137.73 \pm 69.28$ | 37 | 343 | 100.0% |

### 6.2 Evidence for Closed-Loop Behaviour
- **68.3% of trials exhibit at least one full brake release and reapplication** (force drops below $20\text{ N}$ then re-engages $> 30\text{ N}$).
- **100.0% of trials exhibit multiple steering reversals** (median 70.5 zero-crossings with amplitude $\ge 2.86^\circ$).
- This confirms that human takeover stabilization is a classic **closed-loop error-correcting process**, involving overshoot, damping, and continuous sensory feedback adjustment, completely inconsistent with open-loop trajectory rollout models.

---

## 7. Trajectory Stabilization Candidates Comparison

Four alternative definitions of stabilization time $T_{\text{stable}}$ were evaluated across all 498 valid trials:

| Candidate Definition | Operational Criterion | Settled Trials | Success % | Median Time Post-TOR | IQR Post-TOR | Robustness Assessment |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Candidate A: Control-Input Settling** | $\|\dot{\delta}_{\text{sw}}\| \le 0.05\text{ rad/s}$ AND $\|\dot{F}_{\text{brake}}\| \le 20\text{ N/s}$ sustained for $1.5\text{ s}$ | **498 / 498** | **100.0%** | **$21.28\text{ s}$** | $10.56\text{ s}$ | **Highest behavioural robustness.** Captures when human stops making active oscillatory adjustments. |
| **Candidate B: Vehicle Acceleration Settling** | $\|\Delta \dot{a}_x\| \le 0.5\text{ m/s}^3$ AND $\|a_y\| \le 0.3\text{ m/s}^2$ sustained for $1.5\text{ s}$ | 262 / 498 | 52.6% | $23.88\text{ s}$ | $25.64\text{ s}$ | Moderate. Sensitive to road curvature, micro-accelerations, and gradient variations. |
| **Candidate C: Lane-Change Target Settling** | Vehicle in target lane (`lane_id == 3`) with $\|\dot{\delta}_{\text{sw}}\| \le 0.04\text{ rad/s}$ sustained for $2.0\text{ s}$ | 38 / 498 | 7.6% | $19.85\text{ s}$ | $3.75\text{ s}$ | **Low applicability.** In D003, many drivers straddle the lane line or remain in lane 2 during the extended post-maneuver run. |
| **Candidate D: Obstacle Station Passage ($T_{\text{pass}}$)** | Longitudinal distance to hazard $\le 0.0\text{ m}$ (reaches obstacle longitudinal station) | **498 / 498** | **100.0%** | **$8.95\text{ s}$** | $3.30\text{ s}$ | **Longitudinal geometric landmark.** Marks physical station passage, but does NOT establish safe clearance ($T_{\text{safe\_clear}}$ is unidentifiable). |

**Synthesis Recommendation:**
- For **geometric hazard station passage**, use **Candidate D** ($T_{\text{pass}} \approx T_{\text{req}} + 8.95\text{ s}$).
- **[AUDIT 2026-09-22: WITHDRAWN recommendation]** ~~For behavioural and kinematic stability, use Candidate A~~ ($T_{\text{stable}} \approx T_{\text{req}} + 22.2 - 23.0\text{ s}$ post-TOR across candidate anchors).

---

## 8. Scenario-Level Effects (Density $\times$ Cognitive Load)

The 9 experimental scenarios in D003 reveal distinct systematic modulations of human takeover recovery:

| Scenario ID | Density (veh/km) | $N$-Back Load | Median $T_{\text{auth}} - T_{\text{req}}$ (s) | Median $T_{\text{first}} - T_{\text{req}}$ (s) | Brake First (%) | Steer First (%) | Simult. (%) | Mean Peak Brake (N) | Mean Peak Steer ($^\circ$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `density_0_nback_0` | 0 | 0 | $1.250\text{ s}$ | $1.200\text{ s}$ | 96.5% | 3.5% | 0.0% | $55.8\text{ N}$ | $8.49^\circ$ |
| `density_0_nback_1` | 0 | 1 | $1.950\text{ s}$ | $1.101\text{ s}$ | 0.0% | 100.0% | 0.0% | $59.0\text{ N}$ | $5.30^\circ$ |
| `density_0_nback_2` | 0 | 2 | $1.575\text{ s}$ | $2.199\text{ s}$ | 57.9% | 42.1% | 0.0% | $61.5\text{ N}$ | $11.65^\circ$ |
| `density_10_nback_0` | 10 | 0 | $1.450\text{ s}$ | $0.150\text{ s}$ | 1.8% | 54.4% | 43.9% | $28.5\text{ N}$ | $3.34^\circ$ |
| `density_10_nback_1` | 10 | 1 | $1.800\text{ s}$ | $1.300\text{ s}$ | 100.0% | 0.0% | 0.0% | $160.2\text{ N}$ | $11.51^\circ$ |
| `density_10_nback_2` | 10 | 2 | $1.749\text{ s}$ | $1.200\text{ s}$ | 96.5% | 3.5% | 0.0% | $71.4\text{ N}$ | $10.05^\circ$ |
| `density_20_nback_0` | 20 | 0 | $1.150\text{ s}$ | $0.400\text{ s}$ | 1.8% | 96.5% | 1.8% | $160.8\text{ N}$ | $4.77^\circ$ |
| `density_20_nback_1` | 20 | 1 | $1.700\text{ s}$ | $0.800\text{ s}$ | 100.0% | 0.0% | 0.0% | $280.0\text{ N}$ | $9.49^\circ$ |
| `density_20_nback_2` | 20 | 2 | $1.800\text{ s}$ | $1.049\text{ s}$ | 100.0% | 0.0% | 0.0% | $79.2\text{ N}$ | $15.19^\circ$ |

### 8.1 Key Effects Observed
- **Cognitive Distraction ($N$-Back):**
  - High cognitive load ($2\text{-back}$) increases overall brake-first prevalence to **84.8%** (versus 33.3% in $0\text{-back}$). Distracted drivers reflexively brake before scanning for steering escape paths.
  - Mean peak steering amplitude increases from $5.53^\circ$ ($0\text{-back}$) to $12.30^\circ$ ($2\text{-back}$), indicating more violent, less anticipatory steering inputs under high cognitive workload.
- **Traffic Density Effect:**
  - In heavy traffic ($20\text{ veh/km}$), mean initial peak brake force reaches **$166.7\text{ N}$** (with peaks up to $280.0\text{ N}$ under $1\text{-back}$), compared to $58.7\text{ N}$ in open road conditions. Surrounded by adjacent vehicles, drivers must shed speed while waiting for a lane opening.

---

## 9. Participant-Level Repeated-Measures Variability

Aggregating across the 57 participants (`results/H1/participant_summary.csv`):
- **Modal First Action:** **56 of 57 participants** (98.2%) have `BRAKE_FIRST` as their individual modal first action across their 9 repeated trials. Only 1 participant exhibited `STEER_FIRST` as their dominant modality.
- **Individual Reaction Latency:**
  - Participant median $T_{\text{auth}} - T_{\text{req}}$ ranges from **$0.601\text{ s}$** (fastest responder) to **$2.650\text{ s}$** (slowest responder), with a cohort mean of $1.672\text{ s}$.
  - Participant median $T_{\text{first\_ctrl}} - T_{\text{req}}$ ranges from **$0.950\text{ s}$** to **$1.200\text{ s}$**, showing tight clustering around $\approx 1.13\text{ s}$ for initial motor activation.
- **Aggressiveness Variation:**
  - Median initial peak brake force varies widely across participants: from **$28.5\text{ N}$** (gentle trail-braking) to **$352.3\text{ N}$** (full panic emergency stamping).
  - Median peak steering varies from **$4.51^\circ$** to **$15.34^\circ$**.

---

## 10. Confrontation: Phase 1 Assumptions vs Phase 2B-1 Empirical Evidence

| Dimension | Phase 1 Theoretical Model ($A_1, B_0, D_0$) | Phase 2B-1 Empirical Reality (D003, $N=513$) | Epistemic Status & Methodological Verdict |
| :--- | :--- | :--- | :--- |
| **Reaction Latency ($\tau$)** | Scalar latency parameter $t_1 \in [0.7, 1.5]\text{ s}$ (nominal $1.0 - 1.2\text{ s}$). | Median active motor onset $T_{\text{first\_ctrl}} - T_{\text{req}} = 1.125\text{ s}$ (IQR: $0.850\text{ s}$). | **SUPPORTED.** Empirical active motor onset latency aligns tightly with Phase 1's core domain. |
| **Vehicle Response Delay ($t_2$)** | Vehicle / braking response delay $t_2 \in [0.05, 0.17]\text{ s}$ (nominal $0.10\text{ s}$). | Causal deceleration onset delay: median $0.05 - 0.10\text{ s}$ ($50 - 100\text{ ms}$). | **CONSISTENT (V1).** The observed D003 longitudinal response-onset interval is consistent with the Phase-1 modeled response-delay scale under the current operational detector (Parameter-Level Consistency V1). |
| **Human Command Waveform** | Step command ($u = 1.0$) at reaction threshold. | Finite command ramp: rise rate median $91.7\text{ N/s}$, time to peak median $0.75\text{ s}$. | **LIMITED.** Human motor command exhibits finite neuromuscular ramp rate rather than instantaneous step. |
| **Closed-Loop Regulation** | Open-loop hold until final state. | Pronounced closed-loop feedback: median 2 brake reapplications (68.3% of trials) and 2 acute steering reversals. | **EXTENDED BY D003.** Takeover recovery requires closed-loop feedback regulation. |
| **Longitudinal Stopping ($v=0$)** | Emergency braking to complete standstill ($v_{\text{final}} = 0$). | Incomplete speed drop: median drop $8.31\text{ m/s}$, min speed post-TOR median $16.95\text{ m/s}$. | **OUT-OF-SCOPE RELATIVE TO D003.** D003 is an evasive maneuver, not a blocked-lane emergency stop. |
| **Lateral Steering Coupling** | Zero lateral motion ($a_y \equiv 0$). | Coordinated evasive lane change in 97%+ of trials; 32% steer first, 63% brake first. | **EXTENDED BY D003.** Proves full fallback safety requires coupled lateral-longitudinal envelope. |

---

## 11. Phase-2B Gate Classification

### 11.1 Fallback Recovery Classification
**Classification: `H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT/STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`**

*Justification:*
The empirical evidence decisively confirms multi-phase closed-loop recovery structure (finite rise-rate ramp, oscillatory reapplications, steering reversals). However, sensitivity auditing (`H1_METHOD_INTEGRITY_AUDIT.md`) demonstrates that operational definitions of vehicle response delay ($T_{\text{effective}}$), stabilization settling ($T_{\text{stable}}$), and steering reversal counts depend non-trivially on search offsets, persistence windows, and filter thresholds. Following the establishment of `H1_OPERATIONAL_MEASUREMENT_LEDGER.md`, measurement semantics are codified and bounded. Declaring $H1\text{-}B$ remains appropriate and provides the necessary epistemic foundation to authorize Phase 2B-2 Model-Class Comparison / Identification.

### 11.2 Familiarity Mismatch Status Confirmation
**Classification: `M0-C: NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA`** (Retained from Phase 2A)

*Justification:*
In D003, all 57 participants drove an identical vehicle dynamics configuration across all 9 scenarios. There were no vehicle plant parameter variations (e.g. varying mass, wheelbase, steering ratio, or tire friction) and no prior-vehicle adaptation conditions. Therefore, internal-model mismatch parameters cannot be identified from D003 alone without introducing confounding assumptions.

---

## 12. Candidate Controller Model Families for Phase 2B-2

Based on the empirical trajectories from D003, a simple linear PID controller or open-loop step function is insufficient. Rather than prematurely dictating a final architecture, five candidate model classes have been shortlisted (see `H1_METHOD_INTEGRITY_AUDIT.md` for parameter identification details):
- **M1: Empirical Open-Loop Trajectory Library**
- **M2: Piecewise Latency-Ramp-Hold Model**
- **M3: Hybrid State Machine Controller (Candidate Architecture)**
- **M4: Continuous Error-Feedback Regulatory Model**
- **M5: Mixed-Effects Trajectory Generation Model**

The 4-phase hybrid state machine serves as a leading **Candidate Model Family** (to be formally compared and identified in Phase 2B-2, subject to user authorization):

```
[Phase 1: Perceptual-Motor Latency]
   tau_delay ~ 0.8 - 1.4 s (sampled empirically or workload-conditioned)
   zero active control intervention
        │
        ▼
[Phase 2: Initial Action Ramp / Heuristic Reaction]
   Duration: ~ 0.75 s
   Brake: Rise rate ~ 92 N/s to initial peak ~ 53 N
   Steering: Initial rate ~ 21 deg/s toward open lane gap
   Action order: 63% brake-first, 32% steer-first, 5% simultaneous
        │
        ▼
[Phase 3: Closed-Loop Regulation / Trajectory Tracking]
   Longitudinal: Adaptive deceleration based on closing speed to hazard
   Lateral: Lookahead error-feedback steering
   Oscillations: 1 to 3 reapplication cycles with neuromuscular delay
        │
        ▼
[Phase 4: Stabilized Regulated Cruise]
   Attained at T_req + 8.95 s (obstacle station passage) to 22.2 - 23.0 s (input settled) [AUDIT 2026-09-22: the 22.2-23.0 s value is WITHDRAWN; it mostly falls after handback to automation]
   Forward speed maintained at ~ 17 m/s in target lane
```

---

## 13. Threats to Validity & Limitations

1. **Simulator vs Real Vehicle:** D003 is a high-fidelity fixed-base simulator study. Drivers do not experience sustained physical vestibular lateral/longitudinal $g$-forces, which may slightly elevate peak steering and braking rates compared to real-world emergency evasive maneuvers.
2. **Homogeneous Vehicle Model:** Vehicle dynamics parameters ($m, I_z, C_\alpha, \mu$) were held constant, preventing empirical calibration of internal-model adaptation rates.
3. **Specific Hazard Type:** D003 tested a stationary highway construction obstacle in the ego-lane with an open or semi-open adjacent lane. Scenarios involving unavoidable full-lane blockage (requiring complete standstill) were not represented.
4. **Preemptive Takeover Truncation:** In 15 of 513 trials (2.9%), the driver disengaged automation prior to TOR issuance; while accounted for in our QA audit (`USABLE_PREEMPTIVE`), these were excluded from TOR-referenced latency statistics.
5. **Absence of Lateral Obstacle Coordinates ($T_{\text{safe\_clear}}$ Unidentifiable):** D003 telemetry records only 1D longitudinal distance to the construction site. Obstacle lateral coordinates, bounding polygons, and vehicle-obstacle lateral clearances are unrecorded. Consequently, safe obstacle clearance ($T_{\text{safe\_clear}}$) is unidentifiable from source telemetry; $T_{\text{pass}}$ strictly measures geometric obstacle longitudinal station crossing.

---

## 14. Data Dictionary of Generated Artifacts

All deliverables are generated deterministically by `python3 -m src.experiments.h1_recovery_analysis` and saved to `results/H1/` and `research/data_matrix/`:

1. `research/data_matrix/d003_trial_qa.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`: Identification metadata.
   - `total_samples`, `duration_s`, `dt_mean`, `dt_std`: Sampling and duration verification.
   - `is_strictly_monotonic`, `has_duplicate_timestamps`: Monotonicity flags.
   - `has_tor_request`, `tor_request_time`, `has_manual_start`, `manual_start_time`, `has_manual_stop`, `manual_stop_time`: Protocol timestamps.
   - `delta_t_manual_start`: Manual-mode-switch latency interval ($T_{\text{manual\_start}} - T_{\text{req}}$).
   - `bf_min`, `bf_max`, `acc_min`, `acc_max`, `st_min_rad`, `st_max_rad`: Control extrema.
   - `min_obstacle_distance`, `has_lane_change`, `lane_change_time`, `collision_outcome`: Safety outcomes.
   - `usable_status`, `reason_code`: QA classification (`USABLE_FULL`, `USABLE_PREEMPTIVE`, `COLLISION_FAILURE`).

2. `results/H1/event_times.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`.
   - `T_request`, `T_manual_start`, `delta_T_manual_start`.
   - `T_first_brake`, `T_first_steer`, `T_first_accel`, `T_first_ctrl`, `T_first_any`.
   - `T_effective_dec`, `T_effective_lat`, `T_effective_any`.
   - `T_stable_candA`, `T_stable_candB`, `T_stable_candC`, `T_stable_candD`.
   - Latencies: `dt_req_to_manual_start`, `dt_req_to_first`, `dt_req_to_first_any`, `dt_manual_start_to_first`, `dt_first_to_eff`, `dt_eff_to_stable_candA`, `dt_eff_to_stable_candB`, `dt_req_to_stable_candA`, `dt_req_to_stable_candB`.

3. `results/H1/action_sequence.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`.
   - `first_action_type`: `BRAKE_FIRST`, `STEER_FIRST`, `SIMULTANEOUS_BRAKE_STEER`, `THROTTLE_RELEASE_ONLY`.
   - `action_order_string`: Chronological sequence (e.g. `brake -> steer`).
   - `dt_steer_minus_brake`, `dt_brake_minus_accel`.
   - `is_simultaneous_brake_steer`, `is_simultaneous_accel_steer`.

4. `results/H1/initial_control_metrics.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`.
   - `initial_peak_brake_force_N`: Peak force within initial application window.
   - `brake_rise_rate_N_per_s`: Dynamic rise rate from threshold to peak.
   - `time_to_peak_brake_s`: Duration from brake onset to peak.
   - `initial_peak_steering_rad`, `initial_peak_steering_deg`: Peak steering excursion.
   - `initial_steering_rate_rad_per_s`: Maximum steering wheel angular velocity.
   - `simultaneous_brake_and_steer_flag`.
   - `speed_at_T_first_m_per_s`, `speed_at_T_effective_m_per_s`, `min_speed_post_tor_m_per_s`, `speed_drop_m_per_s`.

5. `results/H1/correction_metrics.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`.
   - `brake_extrema_count`: Number of prominent brake force peaks.
   - `brake_reapplication_count`: Distinct re-engagement cycles ($< 20\text{ N} \to > 30\text{ N}$).
   - `brake_derivative_sign_changes`: Oscillations in braking rate.
   - `steering_reversals_count`: Steering angle direction changes ($\ge 2.86^\circ$).
   - `steering_rate_sign_changes`: Steering velocity zero-crossings.

6. `results/H1/stabilization_candidates.csv` (513 rows):
   - `trial_id`, `participant_id`, `scenario_id`, `density`, `nback`.
   - Timestamps and boolean settled flags for Candidates A, B, C, D.
   - `candB_minus_candA`, `candD_minus_candA`.

7. `results/H1/participant_summary.csv` (57 rows):
   - `participant_id`, `n_trials`.
   - Medians and IQRs of $\Delta T_{\text{manual\_start}}$, $T_{\text{first}}$, $T_{\text{effective}}$, $T_{\text{stable\_candA}}$.
   - Medians of peak brake force, peak steering angle, steering reversals, brake reapplications.
   - `modal_first_action`: Dominant action type across repeated trials.

8. `results/H1/scenario_summary.csv` (9 rows):
   - `scenario_id`, `density`, `nback`, `n_trials`.
   - Means, standard deviations, and medians of manual-mode-switch latency, reaction times, stabilization times.
   - Percentages of action ordering: `pct_brake_first`, `pct_steer_first`, `pct_simultaneous`, `pct_throttle_only`.
   - Mean peak brake force and steering excursion per scenario condition.
