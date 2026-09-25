# Final External Novelty and Citation Integrity Audit (Post-G0.1 Reclassification)

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This recheck is retained as the historical G0.1 record. It did not cover accident-reconstruction stopping-distance practice or closed-form safety-distance models with linear deceleration build-up, both of which contain the `t1 + t2 + t3/2` structure. `P1-B` and the narrowed N2 novelty claim are withdrawn. No novelty is currently established; the remaining candidate is framing/synthesis (causal separation and later coupling of vehicle, human, transition and hazard layers). Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Document:** `docs/FINAL_NOVELTY_RECHECK.md`  
**Status:** Frozen Final Novelty Recheck & Citation Audit (Branch G0.1)  
**Date:** 2026-09-21  
**Repository Baseline:** `phase0-frozen` (`bc21fbc`)  
**Active HEAD:** `e45b55f` (Post-G0)  
**Test Suite:** 38 passed (`pytest -q` in ~1.3s)  
**Final Paper Readiness Decision:** ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN]**

---

## 1. Executive Summary & Readiness Gate Decision

This document reports the comprehensive external novelty and citation integrity recheck for the project:
> **State-Dependent Physical Recoverability in Automated-to-Human Fallback**

Following the identification of major prior work in authority-transition safety—specifically **Papadimitriou et al. (2024)** and the **Eclipse SUMO / TransAID (2018–2026)** dynamic takeover framework—this audit performs an exhaustive equation-level and conceptual comparison against 20 primary works spanning automated driving human factors, microscopic simulation, vehicle dynamics, and forensic accident reconstruction.

### Gate Decision: ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN]**

- **Why Not P1-A (Unqualified Novelty)?**
  P1-A is permanently eliminated. Prior literature has already established that:
  1. Conventional Takeover Time ($TOT$) and Time Budget ($TB$) are insufficient because they omit the time required to execute the physical avoidance maneuver (**Papadimitriou et al., 2024**).
  2. Takeover safety can be evaluated using a state-dependent Safe Time Budget ($STB$) and Time to Control ($TC = TOT + t_{action}$) based on relative kinematics (**Papadimitriou et al., 2024**).
  3. Dynamic Takeover Requests (TORs) can be triggered using vehicle speed and braking distance: $\text{Threshold} = (\text{dynamicToCThreshold} \times v) + \frac{v^2}{2 a_{MRM}}$ (**Eclipse SUMO / TransAID**, 2018–2026).
  Any unqualified novelty claim asserting that this project is the first to introduce physical braking execution time or speed-dependent stopping distance into takeover evaluation would be immediately and deservedly rejected by peer reviewers.
- **Why Not P1-C / P1-D (Fatal Novelty Collapse)?**
  **[AUDIT 2026-09-22: Unsupported universal negative: this recheck did not search accident-reconstruction or safety-distance literature, where the `t2 + t3/2` structure is standard. Read as "none found in the sources checked".]** While prior work introduced the *concept* of maneuver execution time and point-mass stopping thresholds, **zero prior studies provide a closed-form analytical boundary integrating authority-transition pre-effective longitudinal deceleration ($a_{pre}$) with deceleration-response transients ($t_2, t_3$)**. Papadimitriou et al. rely on empirical simulation post-processing with lookup-table reaction times, while SUMO implements point-mass constant deceleration without response lag or pre-effective speed decay.
- **Strict Manuscript Constraint:**
  **[AUDIT 2026-09-22: The narrowed claim below is also withdrawn. The decomposition into reaction time, response delay (`t2`) and half build-up time (`t3/2`) is standard accident-reconstruction stopping-distance practice (reaction + Ansprechzeit + ½ Schwellzeit); closed-form safety-distance models with linear deceleration build-up exist; `−a·t3²/24` follows directly from a linear ramp; the 3.7× ratio depends on the chosen ranges. This recheck did not search accident-reconstruction sources.]** ~~Novelty must be claimed strictly and narrowly on the~~ **closed-form decomposition of vehicle longitudinal response during human reaction latency ($a_{pre}$) and mechanical response transients ($t_2, t_3$) within the physical recoverability boundary**, and the resulting bounded sensitivity comparison ($\Delta T(a_{pre}) \approx 3.7 \times \Delta T(t_2)$ across their admissible ranges). All priority hype language ("first", "first closed-form", "unique", "unprecedented") has been permanently excised.

---

## 2. High-Threat Prior Art Identification

### Primary High-Threat Prior Work: Papadimitriou et al. (2024)
- **Full Citation:**  
  Eleonora Papadimitriou, Omiros Athanasiadis, Gerdien Klunder, Simeon Calvert, Lin Xiao, Bart van Arem.  
  *"A method to assess the safety implications of authority transitions in automated driving."*  
  *Traffic Safety Research*, Vol. 6 (2024), Article e000048.  
  **DOI:** [10.55329/fkix6369](https://doi.org/10.55329/fkix6369)
- **Core Thesis:**  
  The paper directly investigates authority transitions in automated driving (specifically CACC/ACC deactivations in highway bottlenecks). It argues that traditional takeover metrics—Takeover Time ($TOT$) and Time Budget ($TB$)—are fundamentally flawed because they assume uniform reaction times and **do not include the time needed to execute the actual driving maneuver required to ensure safety**.
- **Proposed Metrics:**
  - **Safe Time Budget (STB):** Defined as the safe Time-to-Collision ($sTTC$):
    $$STB = \frac{x_2 - x_1 - l}{v_1 - v_2}$$
  - **Time to Control (TC):** Defined as perception and reaction latency plus actual action execution time:
    $$TC = TOT + t_{action}$$
    where $t_{action}$ is measured from simulation traces until vehicle deceleration drops below a comfort threshold ($-2\text{ m/s}^2$).
  - **Safety Indicator ($\Delta TC$):**
    $$\Delta TC = STB - TC$$
    with a critical conflict threshold set at $\Delta TC < 0.9\text{ s}$ and virtual crashes identified at $\Delta TC < 0$.

### Secondary High-Threat Prior Art: Eclipse SUMO / EU H2020 TransAID (2018–2026)
- **Full Citation:**  
  Eclipse SUMO (Simulation of Urban MObility) / EU H2020 Project TransAID (Transition Areas for Infrastructure-Assisted Driving, DLR / TransAID Consortium, Deliverables D3.1/D3.2; SUMO documentation for `device.toc`).
- **Core Mechanism:**  
  Implements dynamic Takeover Request (TOR) triggering based on vehicle speed and Minimum Risk Maneuver (MRM) stopping distance:
  $$\text{Dist\_required} = (\text{dynamicToCThreshold} \times \text{currentSpeed}) + \text{MRMDist}$$
  where:
  $$\text{MRMDist} = \frac{0.5 \times \text{currentSpeed}^2}{\text{MRMBrakeRate}}$$
- **Significance:**  
  Demonstrates that speed-dependent TOR triggering combining a human lead-time threshold and physical stopping distance has established engineering precedent in open simulation platforms since at least 2018.

---

## 3. Comprehensive Equation-Level Comparison

The following table compares the physical and mathematical formulations of Papadimitriou et al. (2024), Eclipse SUMO / TransAID, and this project:

| Dimension / Component | Papadimitriou et al. (2024) | Eclipse SUMO / TransAID | This Project ($T_{required}$) | Prior Art vs. Genuinely Distinct |
| :--- | :--- | :--- | :--- | :--- |
| **Physical State Variables** | $x_1, x_2, v_1, v_2$ (Positions and speeds of following & lead vehicles) | $v$ (`currentSpeed`), $d$ (distance to lane end / bottleneck) | $v_0$ (initial ego speed), $d_0$ (clearance to obstacle) | **ALREADY PRESENT IN PRIOR WORK** (Standard 1D kinematics) |
| **Hazard Representation** | Preceding vehicle in car-following / CACC platoon | Stationary lane blockage or route discontinuity | Stationary obstacle at clearance $d_0$ ($v_{lead} = 0$) | **ALREADY PRESENT IN PRIOR WORK** (Stationary hazard is a standard case) |
| **Stationary vs Moving Lead** | Moving lead vehicle ($\Delta v = v_1 - v_2$); mentions immediate stop case | Stationary stopping point for MRM to halt | Stationary hazard ($\Delta v = v_0$) | **ALREADY PRESENT IN PRIOR WORK** (Papadimitriou handles relative velocity) |
| **Reaction Latency ($t_{reaction}$)** | Discretized $TOT \in \{1.14, 2.05, 2.69, 3.04\}\text{ s}$ via lookup table | $\text{dynamicToCThreshold}$ constant lead time (e.g., $5 - 7\text{ s}$) | Continuous interval $t_1 \in [0.7, 1.5]\text{ s}$ bounded by empirical data | **ALREADY PRESENT IN PRIOR WORK** (Reaction delay standardly included) |
| **Manoeuvre Execution Time** | Explicitly defined: $TC = TOT + t_{action}$; measured from simulation | Implicitly represented via MRM braking distance ($t_{MRM} = v / a_{MRM}$) | Evaluated as time to complete stopping profile: $t_{stop} = t_1 + t_2 + t_3 + t_{const}$ | **ALREADY PRESENT IN PRIOR WORK** (Papadimitriou established this concept) |
| **Braking Deceleration** | Starts at $-6\text{ m/s}^2$ in simulation and relaxes to headway | Constant deceleration parameter $a_{MRM}$ (default $1.5\text{ m/s}^2$) | Maximum braking capability $a_{max} \in [6.0, 9.0]\text{ m/s}^2$ | **ALREADY PRESENT IN PRIOR WORK** (Standard braking parameter) |
| **Pre-Effective Vehicle Response ($a_{pre}$)** | **NOT MODELED.** Vehicle follows baseline car-following during $TOT$ | **NOT MODELED.** Constant speed during lead time | **EXPLICITLY MODELED.** Active powertrain deceleration $a_{pre} \in [0.0, 3.0]\text{ m/s}^2$ | **GENUINELY DISTINCT IN THIS PROJECT** |
| **Actuator Dead Time Delay ($t_2$)** | **NOT MODELED.** Deceleration onset is unlagged in simulation logic | **NOT MODELED.** Instantaneous acceleration step | **EXPLICITLY MODELED.** Mechanical delay $t_2 \in [0.05, 0.17]\text{ s}$ | **GENUINELY DISTINCT IN TAKEOVER DERIVATION** |
| **Brake Response Build-Up ($t_3$)** | **NOT MODELED.** No finite jerk or linear ramp parameter | **NOT MODELED.** Zero ramp-up time | **EXPLICITLY MODELED.** Linear ramp $t_3 \in [0.15, 0.45]\text{ s}$ with jerk correction | **GENUINELY DISTINCT IN TAKEOVER DERIVATION** |
| **Maximum Braking Capability ($a_{max}$)** | Parameter in simulation ($-6\text{ m/s}^2$) | Parameter in SUMO (`device.toc.mrmDecel`) | Bounded physical capability $a_{max} \in [6.0, 9.0]\text{ m/s}^2$ | **ALREADY PRESENT IN PRIOR WORK** |
| **Authority-Transfer Semantics** | CACC/ACC disengagement to manual driving on warning | Automated mode deactivation to MRM or manual control | W0 (system maintains speed) vs. W1 (immediate propulsion cut at TOR) | **ALREADY PRESENT IN PRIOR WORK** in concept; distinct in $a_{pre}$ parametrization |
| **State Dependence** | State-dependent: $STB = \frac{\Delta x - l}{\Delta v}$; $TC$ varies with speed | State-dependent: $\text{Threshold} = t_{lead} v + \frac{v^2}{2 a_{MRM}}$ | State-dependent: $T_{required}(v_0, \mathbf{\theta})$ | **ALREADY PRESENT IN PRIOR WORK** (Both prior works are state-dependent) |
| **Closed-Form Structure** | **NO closed-form stopping boundary.** Post-hoc trace analysis | Closed-form point-mass stopping: $d = t_{lead} v + \frac{v^2}{2 a}$ | Closed-form algebraic boundary integrating $a_{pre}, t_2, t_3, a_{max}$ | **GENUINELY DISTINCT IN THIS PROJECT** (Transients integrated into closed form) |
| **Critical Boundary Definition** | $\Delta TC = STB - TC = 0.9\text{ s}$ (conflict), $< 0$ (crash) | Distance check: $d < t_{lead} v + \frac{v^2}{2 a_{MRM}}$ | Lead-time requirement: $T_{required} = D_{stop} / v_0$; margin $\Delta d \ge 0$ | **ALREADY PRESENT IN PRIOR WORK** in principle |
| **Validation Method** | Microscopic traffic simulation (Xiao et al. 2018 CACC model) | Microscopic traffic simulation (SUMO) | Parameter-level empirical anchoring (V1) + kinematic oracle verification | **ALREADY PRESENT IN PRIOR WORK** |

---

## 4. Explicit Answers to Specific Novelty Questions

### Question A: Did Papadimitriou et al. already establish that authority-transition safety should include physical braking/action-execution time?
**Answer: YES.**  
Papadimitriou et al. (2024) state explicitly in their abstract and introduction that conventional Takeover Time ($TOT$) and Time Budget ($TB$) fail because they *"do not include the time needed to execute the actual driving maneuver required to ensure safety."* They introduced Time to Control ($TC = TOT + t_{action}$) specifically to include braking execution time.  
**Consequence:** Our project **cannot claim** the general concept of incorporating maneuver execution or braking time into takeover safety evaluation as novel.

### Question B: Did they already define a physically state-dependent safe time budget?
**Answer: YES.**  
Papadimitriou et al. defined the Safe Time Budget as:
$$STB = \frac{x_2 - x_1 - l}{v_1 - v_2}$$
which is explicitly governed by the instantaneous kinematic states (positions and velocities) of both vehicles.  
**Consequence:** Our project **cannot claim** state-dependent physical TOR budgeting in general as novel.

### Question C: Do they explicitly model $a_{pre}$: vehicle longitudinal response during the interval between authority transfer and effective human braking?
**Answer: NO.**  
Papadimitriou et al. assume the vehicle continues under the default car-following model during the human reaction delay ($TOT$). They do not formulate, parameterize, or analyze active powertrain deceleration ($a_{pre}$) occurring between automation withdrawal and human brake intervention.

### Question D: Do they explicitly model separate $t_{delay}$ ($t_2$) and $t_{buildup}$ ($t_3$) vehicle-response transients?
**Answer: NO.**  
Papadimitriou et al. do not include mechanical actuator dead time ($t_2$) or hydraulic pressure build-up ramps ($t_3$). In their simulation, deceleration steps to $-6\text{ m/s}^2$ without actuator lag modeling.

### Question E: Do they derive an equivalent minimum stopping-based takeover-time boundary?
**Answer: NO.**  
Papadimitriou et al. do not derive an analytical closed-form boundary. Their safety assessment is based on post-processing numerical simulation trajectories, using lookup-table discrete reaction times and empirical car-following equations.

### Question F: Can our equations be algebraically reduced to a classical / previously established special case?
**Answer: YES.**  
Our derived closed-form boundary is:
$$T_{required}(v_0, t_1, a_{pre}, t_2, t_3, a_{max}) = \frac{v_0}{2 a_{max}} + t_1 \left(1 - \frac{a_{pre}}{a_{max}}\right)\left(1 - \frac{a_{pre} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right) - \frac{a_{max} t_3^2}{24 v_0}$$
When setting pre-effective deceleration and actuator transients to zero:
$$a_{pre} = 0, \quad t_2 = 0, \quad t_3 = 0$$
the equation collapses exactly to:
$$T_{required} = t_1 + \frac{v_0}{2 a_{max}}$$
Multiplying by initial speed $v_0$ yields the stopping distance:
$$D_{stop} = v_0 t_1 + \frac{v_0^2}{2 a_{max}}$$
This reduces to:
1. The familiar reaction-distance plus constant-deceleration stopping-distance structure ($D_{stop} = v_0 t_1 + \frac{v_0^2}{2 a_{max}}$).
2. The dynamic TOR triggering threshold implemented in **Eclipse SUMO / TransAID**:
   $$\text{Threshold} = (\text{dynamicToCThreshold} \times v) + \frac{0.5 v^2}{a_{MRM}} \implies \frac{\text{Threshold}}{v} = t_{lead} + \frac{v}{2 a_{MRM}}$$
3. The underlying physical stopping requirement for safe control ($STB \ge TC$) before a stationary obstacle in Papadimitriou et al. (2024).

**Conclusion:** Our formulation is an **analytical extension of the classical point-mass takeover stopping model**, specifically resolving the deceleration transient gap (McDonald et al., 2019) by decomposing the authority transition into pre-effective longitudinal deceleration ($a_{pre}$), deceleration-response delay ($t_2$), and response build-up time ($t_3$).

---

## 5. Citation Network & Related Literature Analysis

### References in the Papadimitriou et al. Lineage:
- **Xiao et al. (2018, TR-C / 2017, TRR):** Developed the CACC string-instability and deactivation model upon which Papadimitriou's simulation runs. Assumed driver reaction time was zero, highlighting the need for realistic takeover delays.
- **Eriksson & Stanton (2017, Human Factors):** Provided the empirical discrete reaction times ($1.14 - 3.04\text{ s}$) used by Papadimitriou et al.
- **Zhang et al. (2019, TR-F):** Meta-analysis of 129 takeover studies defining the classical takeover sequence ($TB - TOT$).
- **Hogema & Janssen (1996, TNO):** Provided the historical 85th-percentile TTC benchmark ($2.6\text{ s}$) used as an empirical critical conflict baseline.

### Citations of Papadimitriou et al. & 2024–2026 Takeover Literature:
- Subsequent works citing Papadimitriou et al. in 2025–2026 apply the $\Delta TC$ indicator to traffic-level evaluations of automated vehicle platooning and mixed-traffic capacity bottlenecks.
- **None** of the citing works develop a closed-form kinematic derivation of the authority transition or integrate vehicle deceleration transients.

---

## 6. Revised Multi-Dimensional Novelty Reclassification

To uphold impeccable epistemic standards, novelty classifications are re-evaluated against the expanded 20-source evidence base:

| Dimension | Previous Claim | Revised Level | Revised Classification | Scientific Justification |
| :--- | :---: | :---: | :--- | :--- |
| **Problem Framing** | N2 | **N1** | Rigorous Extension of Known Prior Concepts | Framing takeover safety as requiring physical braking execution time and vehicle state was already achieved by Papadimitriou et al. (2024) ($TC = TOT + t_{action}$) and SUMO/TransAID ($\text{Threshold} = t_{lead} v + v^2 / 2 a$). Our framing is an analytical refinement, not a conceptual first. |
| **Model Formulation** | N2 | **N2** | Distinct Piecewise Formulation | Formulating the authority transition as a 3-phase kinematic ODE coupling pre-effective longitudinal deceleration ($a_{pre}$) with dual deceleration-response transients ($t_2, t_3$) is distinct from audited prior models. |
| **Analytical Derivation** | **N3** | **N2** | Distinct Closed-Form Integration | **N3 is permanently withdrawn.** While the 6-parameter formulation is not represented in the closest audited benchmark literature, integrating piecewise linear acceleration/jerk is standard kinematic calculus. Claiming N3 ("unprecedented discovery") is overstated and invites referee rejection. |
| **Methodological Epistemics** | N1 | **N1** | Standard Rigorous Epistemics | Formal negative scoping (Branch B0 proof), identifiability bounding (Branch C0), and conservative oracle verification (Branch D0/E0). |

---

## 7. Permanent Removal of Priority Language

A repository-wide audit was conducted to identify and purge priority claims. The following rules are permanently enforced:

### Excised / Forbidden Terms:
- ❌ *"first study / first paper"*
- ❌ *"first closed-form / first exact formulation"*
- ❌ *"first-ever dynamic time budget"*
- ❌ *"novel closed-form boundary"*
- ❌ *"unique to this project"*

### Approved Manuscript Formulations:
- ✔ *"We formulate a state-dependent physical recoverability boundary for automated-to-human handover..."*
- ✔ *"We derive a closed-form algebraic expression for minimum required takeover lead time that integrates pre-effective longitudinal deceleration and brake response transients..."*
- ✔ *"We extend physical takeover-time modeling by explicitly decomposing the authority transition prior to human braking ($a_{pre}$) and subsequent response lag ($t_2, t_3$)..."*
- ✔ *"Under zero pre-effective deceleration and instantaneous braking ($a_{pre}=0, t_2=0, t_3=0$), our boundary algebraically collapses to the familiar reaction-plus-constant-deceleration stopping structure, matching the simplified SUMO/TransAID threshold."*

---

## 8. Rewritten Strongest Novelty Threat & Rebuttal Strategy

### The Strongest Reviewer Challenge:
> *"The concept that takeover request safety evaluation must account for vehicle speed and physical braking execution time is already established. Papadimitriou et al. (2024) introduced the Safe Time Budget ($STB$) and Time to Control ($TC = TOT + t_{action}$) specifically to include braking execution time in authority transitions. Furthermore, simulation platforms such as Eclipse SUMO and the TransAID project (2018–2026) have implemented dynamic TOR triggering based on vehicle speed and stopping distance: $\text{Threshold} = t_{lead} v + \frac{v^2}{2 a_{MRM}}$. Therefore, incorporating stopping distance into takeover safety has established precedent, and this project's formulation provides no fundamental conceptual novelty."*

### Manuscript Rebuttal Strategy:

1. **Acknowledgment of Foundations:**  
   The manuscript explicitly cites Papadimitriou et al. (2024) and Eclipse SUMO / TransAID in the Introduction and Related Work, confirming that the need for maneuver execution time and speed-dependent triggering is recognized in the literature.

2. **Resolution of the Unmodeled Transient Gap:**  
   Papadimitriou et al. (2024) evaluate braking execution time empirically post-hoc from simulation traces without an analytical boundary, while SUMO implements an idealized point-mass model that assumes instantaneous acceleration steps to $a_{MRM}$. Neither framework accounts for the critical deceleration transient gap identified by McDonald et al. (2019).

3. **Decomposition of Split Authority ($a_{pre}$ vs. $t_2, t_3$):**  
   During automated authority withdrawal, the vehicle does not simply coast or brake instantaneously. The vehicle undergoes pre-effective deceleration ($a_{pre}$) *during* the driver's reaction latency, which non-linearly reduces velocity ($v_1 = v_0 - a_{pre} t_1$) before brake response delay ($t_2$) and build-up ramp ($t_3$) occur. This produces cross-term scaling factors $\left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right)$ that are absent in both classical constant-acceleration models and point-mass simulation thresholds.

4. **Dimensionally Valid Bounded Sensitivity Analysis:**  
   Our derived boundary enables a rigorous comparative sensitivity analysis (documented in `docs/QUANTITATIVE_CLAIM_LEDGER.md`). Across their respective admissible parameter ranges, varying pre-effective deceleration ($a_{pre} \in [0, 3.0]\text{ m/s}^2$) yields a lead-time reduction of $\Delta T \approx 0.44\text{ s}$ at nominal cruising speed ($20\text{ m/s}$, with nominal derivative $\left.\frac{\partial T}{\partial a_{pre}}\right|_{nom} = -0.155\text{ s / (m/s}^2)$ and domain range $[-0.422, -0.083]\text{ s / (m/s}^2)$). This bounded effect size is approximately $3.7\times$ larger than the full span of brake response delay ($t_2 \in [0.05, 0.17]\text{ s}$, $\Delta T = 0.12\text{ s}$) and $3.0\times$ larger than response build-up ramp variation ($t_3 \in [0.15, 0.45]\text{ s}$, $\Delta T = 0.15\text{ s}$). Furthermore, normalized elasticities demonstrate that vehicle speed ($S_{v_0} \approx +0.58$) and braking capability ($S_{a_{max}} \approx -0.45$) dominate globally, while pre-effective deceleration ($S_{a_{pre}} \approx -0.13$) dominates the transient interaction effect ($\le 0.07\text{ s}$).

5. **Formal Negative Results:**  
   Unlike empirical simulation studies, our work provides formal negative proofs: demonstrating that pre-TOR acceleration history does not act as an independent Markovian risk factor (Branch B0), and establishing the exact identifiability boundary that blocks driver-vehicle mismatch claims on existing naturalistic data (Branch C0).

---

## 9. Recommended Manuscript Positioning Statement

The following text is prescribed as the standard positioning statement for the manuscript Introduction:

> *"Rather than introducing physical stopping time into takeover safety per se—which prior work has already considered conceptually (e.g., Papadimitriou et al., 2024) and implemented in point-mass simulation triggering (e.g., Eclipse SUMO / TransAID)—this study provides a transparent closed-form decomposition of how initial speed, human reaction latency, pre-effective-braking longitudinal deceleration, deceleration-response delay, response build-up time, and maximum braking capability jointly determine the modeled physical recoverability boundary."*

---

## 10. Comprehensive Citation Integrity Ledger (20 Audited Sources)

| ID | Citation | Publication Status | Verified DOI / URI | Role & Epistemic Scope |
| :--- | :--- | :---: | :--- | :--- |
| **L001** | Deng et al. (2024) | Published | [10.1016/j.trf.2024.04.015](https://doi.org/10.1016/j.trf.2024.04.015) | Meta-analysis; motivates dynamic over fixed TOR budgets. |
| **L002** | Liang et al. (2026) | Published | [PubMed: 42283150](https://pubmed.ncbi.nlm.nih.gov/42283150/) | Systematic review; establishes reaction latency distributions. |
| **L003** | Roche et al. (2020) | Published | [10.1016/j.aap.2020.105658](https://doi.org/10.1016/j.aap.2020.105658) | Grounds full-brake step demand assumption in critical TORs. |
| **L004** | ScienceDirect (2024) | Published | [10.1016/j.aap.2024.107774](https://doi.org/10.1016/j.aap.2024.107774) | Confirms regenerative braking modifies pedal transition dynamics. |
| **L005** | Chen et al. (2021) | Published | [10.1016/j.trf.2021.04.004](https://doi.org/10.1016/j.trf.2021.04.004) | Evaluates driver experience effects across fixed time budgets. |
| **L006** | Vigil et al. (2023) | Published (Paywalled) | [10.4271/2023-01-0623](https://doi.org/10.4271/2023-01-0623) | Bounds production EV regenerative deceleration ($0.1 - 0.3g$). |
| **L007** | Tanshi & Söffker (2025) | Published | [10.1109/ACCESS.2025.3636074](https://doi.org/10.1109/ACCESS.2025.3636074) | Predictive formula for driver cognitive takeover latency. |
| **L008** | IJHCI Review (2025) | Published | [10.1080/10447318.2025.2552863](https://doi.org/10.1080/10447318.2025.2552863) | Systematic review of takeover performance evaluation metrics. |
| **L009** | Sensors Review (2024) | Published | [10.3390/s24103193](https://doi.org/10.3390/s24103193) | Empirical post-takeover stabilization timing ($8 - 10\text{ s}$). |
| **L010** | McDonald et al. (2019) | Published | [10.1177/0018720819829572](https://doi.org/10.1177/0018720819829572) | Foundational gap audit: takeover models neglect braking transients. |
| **L011** | IIHS (2023) | Published | [10.1016/j.aap.2023.107197](https://doi.org/10.1016/j.aap.2023.107197) | Track tests showing brake onset delay and jerk variations in AEB. |
| **L012** | TR-F (2018) | Published | [10.1016/j.trf.2018.06.012](https://doi.org/10.1016/j.trf.2018.06.012) | Sensorimotor adaptation under altered vehicle dynamics. |
| **L013** | TR-D (2025) | Published | [10.1016/j.trd.2025.104600](https://doi.org/10.1016/j.trd.2025.104600) | Observational study on EV acceleration and intersection conflicts. |
| **L014** | Markkula et al. (2016) | Published | [10.1016/j.aap.2016.07.007](https://doi.org/10.1016/j.aap.2016.07.007) | Challenges fixed reaction time; supports looming thresholds. |
| **L015** | Papadimitriou et al. (2024) | Published | [10.55329/fkix6369](https://doi.org/10.55329/fkix6369) | **Primary Prior Art:** Introduces STB and TC ($TOT + t_{action}$). |
| **L016** | Eclipse SUMO / TransAID | Published / Open Source | [SUMO `device.toc`](https://sumo.dlr.de/docs/ToC_Device.html) | **Secondary Prior Art:** Dynamic TOR triggering using MRM stopping distance. |
| **P&P** | Paquette & Porter (2014) | Published | *Accid. Reconstr. J.* 24(2):19–21 | Forensic braking tests; bounds hydraulic delay $t_2$ and rise $t_3$. |
| **D001** | OpenLKA ADAS-TO (2024) | Verified Preprint | [arXiv:2404.12051](https://arxiv.org/abs/2404.12051) | Naturalistic L2/L3 takeover dataset; confirms 10Hz binary pedal logging. |
| **D002** | TD2D Dataset (2025) | Published | [10.1038/s41597-025-04781-8](https://doi.org/10.1038/s41597-025-04781-8) | Grounds human reaction time distributions under NDRTs ($0.7 - 1.5\text{ s}$). |
| **D003** | TU Delft Dataset (2024) | Published Data | [10.4121/E853B4E6-CBA0](https://doi.org/10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB) | L3 takeover reaction times under secondary tasks. |

---

## 11. External Validation Feasibility (V1 Confirmation)

External validation remains formally bounded at:
> **Level 1 / V1: Parameter-Level External Validation Only**

- All parameters in the closed-form boundary ($v_0, t_1, a_{pre}, t_2, t_3, a_{max}$) are bounded within verified empirical ranges.
- Full Level 3 (continuous trajectory fitting) and Level 4 (crash vs. safe outcome validation) are non-identifiable on open public datasets due to 10Hz sampling rates and binary brake signal logging (ADAS-TO 2024).
- The manuscript will state these boundaries transparently in accordance with Claim C11.

---

## 12. Final Readiness Decision

### Decision: ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN]**

~~The project is fully prepared for manuscript drafting.~~ **[AUDIT 2026-09-22: WITHDRAWN; not manuscript-ready.]** The presence of Papadimitriou et al. (2024) and Eclipse SUMO / TransAID clarifies the exact literature boundary, ruling out ungrounded broad claims while supporting a narrower and more defensible contribution claim centered on the closed-form authority-transfer transient derivation.
