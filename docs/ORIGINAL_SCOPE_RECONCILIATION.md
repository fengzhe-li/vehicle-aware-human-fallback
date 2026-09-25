# Original Scope Reconciliation & Research-Question Coverage Audit (Branch H0)

**Date:** 2026-09-21  
**Repository:** `vehicle-aware-human-fallback`  
**Milestone:** **Branch H0 — Original Scope Reconciliation**  
**Frozen Baseline:** `phase0-frozen` (`bc21fbce8b9b9518919fcaecd6a301785a1fee0d`)  
**Current Audit Classification (WITHDRAWN 2026-09-22):** ~~`H0-B: CORE PHYSICAL SPINE COMPLETE, HUMAN / COUPLED QUESTIONS REMAIN`~~  
**Programme Status (WITHDRAWN 2026-09-22):** ~~`PAPER-READY, PROGRAMME-INCOMPLETE`~~ → current stage **EXPLORATORY** (see `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`)

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This document is retained as the historical H0 record, but several of its statements are superseded:
> 1. **Historical structure.** The original project (charter v1.0, README at `559ff13`) was **one mother question plus four mechanism layers**, not four top-level RQs. The RQ1–RQ4 structure below was **constructed in this H0 document** (commit `c09f682`).
> 2. **Fabricated quotation.** The "Original Wording" given for RQ4 below ("How does automation withdrawal policy (immediate withdrawal W1 vs cruise-maintenance W0 vs staged withdrawal W2) interact with …") **does not appear in the charter or in any file before `c09f682`**. W0/W1/W2 terminology first appears in `bc21fbc` (Phase 0.4, `docs/CAUSAL_MODEL.md`); the first commit mentions only "immediate vs staged" withdrawal in the identifiability matrix. The RQ2 "quote" splices charter §4.1 with Gate A text.
> 3. **Status labels.** "RQ1 partially answered", "RQ2 answered", "RQ4 partially answered", `H0-B`, `P1-B: READY` and "paper-ready" are withdrawn. The system-level synthesis is **NOT STARTED / GATED**; the vehicle-response layer is **PARTIAL** (saturated braking only); transition is **NOT STARTED** beyond the W0/W1 abstraction.
> 4. **Layers demoted to outcomes.** The charter's handover layer (§4.3) included control reacquisition and stabilisation as a *mechanism layer*; this document treated them as outcomes. The charter's internal-model layer (§4.2) defines a *generic* mismatch M; this document narrowed it to EV/ICE familiarity.
> 5. **Human data.** The D003 description below (lane deviation as a direct signal; "fully addressable") is superseded by `research/data_matrix/D003_KNOWN_BLOCKERS.md`.
>
> Current architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

---

## 1. Executive Summary & Audit Orientation

The purpose of this audit is to rigorously compare the **original project charter and research architecture** against what has **actually been established** across the repository.

Implementation branches ($A1, B0, C0, D0, E0, F0, G0$) were formed through an iterative process of hypothesis testing, analytical reduction, and identifiability filtering. They are **not automatically equivalent** to the project's original research questions. To avoid revisionist drift, this audit reconstructs the research programme strictly from the earliest authoritative Phase 0 project documents:
- `research/project_charter.md` (v1.0)
- `README.md` (Initial Commit)
- `docs/DECISIONS.md` (Decisions D001–D008)
- `research/PHASE0_1_REPORT.md` through `research/PHASE0_4_REPORT.md`
- `docs/RESEARCH_ARCHITECTURE_V1.md`
- `docs/CAUSAL_MODEL.md`
- `experiments/A_brake_response/control_ownership_timeline.md`
- `experiments/A_brake_response/metric_definitions.md`

### Core Finding:
The project has successfully derived, verified, and evidence-bounded the **deterministic physical vehicle-response recoverability boundary** ($T_{required}$). However, the original charter's broad ambition of modeling a **coupled human–vehicle cognitive system**—specifically including driver familiarity priors, vehicle-switch mismatch, dynamic closed-loop stabilization, and a probabilistic safety envelope—was previously simplified or deferred.

*Phase 2A Audit Update:* A forensic audit of public datasets established a critical distinction:
- **Generic Closed-Loop Human Data:** **AVAILABLE** in public open data. The TU Delft Conditionally Automated Driving Dataset (D003) provides 513 full 20 Hz continuous trials with continuous brake force (in Newtons), accelerator displacement, steering angle, lateral lane deviation, and obstacle distance. ADAS-TO (D001) provides 15,659+ disengagements with continuous steering angle/torque. Generic closed-loop human fallback modeling is assigned to gate **`H2A: PUBLIC DATA SUFFICIENT FOR REACTION + CLOSED-LOOP HUMAN MODEL`**.
- **Driver Familiarity / Mismatch Data:** ~~UNAVAILABLE in public open data ($M0\text{-}C$).~~ **[AUDIT 2026-09-22: Direct vehicle-response familiarity × takeover response is not identifiable from verified public data checked; repeated-exposure learning is identifiable in D003; experience is associational only.]** No public dataset records driver EV-vs-ICE prior experience or cross-vehicle response transitions.

The project is therefore classified as:
> ~~`H0-B: CORE PHYSICAL SPINE COMPLETE, HUMAN / COUPLED QUESTIONS REMAIN`~~  
> ~~Operating under: `PAPER-READY (PHYSICAL SPINE), PROGRAMME-ACTIVE (PHASE 2 HUMAN FALLBACK)`~~  
> **[AUDIT 2026-09-22: both WITHDRAWN. Current stage: EXPLORATORY.]**

---

## 2. Earliest Authoritative Project Foundation

### 2.1 The Motivating Problem and Core Axiom
From `research/project_charter.md` (§1) and `README.md`:
> *"Automation may hand control authority to a human when it reaches a difficult state, but authority transfer does not necessarily mean that the human–vehicle system has recovered enough capability to avoid the hazard."*

The project was founded on the principle that takeover safety cannot be evaluated by takeover request (TOR) lead time alone, but is governed by the physical interaction between the vehicle's deceleration response, the automation withdrawal policy, the human driver's capability, and the scenario geometry.

### 2.2 The Foundational Mother Question
From `research/project_charter.md` (§2) and `README.md`:
> *"Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?"*

### 2.3 The Original Working Thesis & Envisioned Safety Envelope
From `research/project_charter.md` (§3):
> *"Human fallback safety should be treated as a joint recoverability property of the human, vehicle and automation rather than as a function of TOR lead time alone. A conceptual form is:*
> $$P(\text{safe fallback}) = f(\text{vehicle state}, \text{braking response}, \text{driver–vehicle mismatch}, \text{TOR budget}, \text{human response}, \text{environment/scenario criticality})$$"

---

## 3. Reconstruction of the Original Research Programme

By auditing the foundational repository documents, the original programme is deconstructed into its true **Top-Level Research Questions** and subsidiary **Mechanisms / Scenario Variables**.

### 3.1 Top-Level Research Questions

> **[AUDIT 2026-09-22]** These four "top-level RQs" are an H0 construction. The charter contains one mother question (§2) and four mechanism layers (§4.1–§4.4).

#### Top-Level RQ 1: System-Level Joint Recoverability & Safety Envelope
- **Original Wording:** *"Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?"* (`project_charter.md` §2; `README.md`)
- **Source Document:** `research/project_charter.md` §2–§3; `README.md`
- **Original Motivation:** Challenge the industry paradigm that a single scalar TOR lead time (e.g. 4 s or 7 s) ensures safety across arbitrary vehicle architectures and driver states.
- **Scientific Object:** The joint human–vehicle–automation recoverability boundary $P(\text{safe fallback} \mid \text{state})$.
- **Intended Independent Variables:** Initial speed $v_0$, initial TTC / hazard distance, TOR lead time, human reaction time distribution, vehicle response parameters, driver mismatch $M$, withdrawal policy.
- **Intended Outcome Variables:** `collision`, `TTC_min`, `stopping_margin`, `impact_speed`, `stabilisation_time`, `secondary_correction_count`.
- **Intended Evidence / Experiment:** Multi-layer simulation combining vehicle dynamics, driver models, and scenario grids (originally Phases 4–5).
- **Intended Claim Level:** TYPE 3 (Empirically Constrained) / TYPE 4 (Real-World Safety Envelope).

#### Top-Level RQ 2: Vehicle Longitudinal-Response Architecture Effect
- **Original Wording:** *"Study the mapping from control input to actual longitudinal response, including: progressive friction-dominant braking, regenerative braking, one-pedal-like response, blended/nonlinear braking, response latency, deceleration build-up, jerk, maximum deceleration, road friction... Does realistic braking-response changes materially alter recovery metrics?"* (`project_charter.md` §4.1, Gate A; `README.md` §4; `PHASE0_2_REPORT.md` §1)
- **Source Document:** `research/project_charter.md` §4.1; `experiments/A_brake_response/vehicle_response_model.md`
- **Original Motivation:** Braking literature proves vehicle control architectures alter deceleration transients, yet takeover models conventionally treat braking as point-mass constant deceleration.
- **Scientific Object:** Transient longitudinal vehicle response ($a_{pre}, t_2, t_3$) isolated from maximum capability ($a_{max}$).
- **Intended Independent Variables:** Actuator delay $t_2$, build-up time $t_3$, pre-effective deceleration $a_{pre}$ (regen/engine drag), low-speed roll-off $v_{rolloff}$, held-constant $a_{max}$.
- **Intended Outcome Variables:** Stopping distance $D_{stop}$, stopping margin, impact speed, critical lead time $T_{TOR\_critical}$.
- **Intended Evidence / Experiment:** Factorial longitudinal simulation and closed-form kinematic derivation (originally Phase 1A / Experiment A).
- **Intended Claim Level:** TYPE 1 (Kinematic Deduction) / TYPE 2 (Counterfactual Simulation) / TYPE 3 (Empirically Anchored Parameters).

#### Top-Level RQ 3: Driver Internal-Model & Familiarity Mismatch
- **Original Wording:** *"Let $\hat{f}_{driver}$ represent the driver's expected input $\to$ vehicle-response mapping and $f_{vehicle}$ the actual mapping. Define a generic mismatch term: $M = D(\hat{f}_{driver}, f_{vehicle})$. Phase 1 fixes $M = 0$. Later phases test whether mismatch changes first control action, secondary corrections, TTC, stopping margin and stabilisation."* (`project_charter.md` §4.2, Gate C; `README.md` Phase 2; `DECISIONS.md` D003, D004)
- **Source Document:** `research/project_charter.md` §4.2; `docs/DECISIONS.md`
- **Original Motivation:** Drivers transitioning between vehicles with different pedal dynamics (e.g. ICE coastdown vs EV aggressive one-pedal regenerative braking) may possess miscalibrated control expectations, leading to inappropriate pedal inputs or delayed braking.
- **Scientific Object:** Cognitive and motor mismatch $M$ between expected and actual vehicle dynamics.
- **Intended Independent Variables:** Mismatch magnitude $M$, driver prior (ICE-familiar vs EV-familiar), pedal gain distortion.
- **Intended Outcome Variables:** Initial pedal press delay, corrective pedal modulations ($N_{correction}$), stabilization time ($T_{stable}$), stopping margin.
- **Intended Evidence / Experiment:** Human-in-the-loop or empirical dataset evaluation comparing familiar vs unfamiliar driver responses (originally Phase 2).
- **Intended Claim Level:** TYPE 3 (Empirical Human Factors).

#### Top-Level RQ 4: Automation Handover & Withdrawal Policy
- **[AUDIT 2026-09-22: NOT ORIGINAL. The quoted wording below was written in H0 (`c09f682`) and is not in the charter. The charter lists only "automation withdrawal policy" as a Phase-1 variable (§5) and a handover layer covering T_authority / T_effective / T_stable (§4.3).]**
- **Original Wording (as asserted by H0; not verifiable in the charter):** *"How does automation withdrawal policy (immediate withdrawal W1 vs cruise-maintenance W0 vs staged withdrawal W2) interact with vehicle response architecture and driver reaction latency to determine safe takeover time budget?"* (`project_charter.md` §4.3, §5; `CAUSAL_MODEL.md` Task 2; `control_ownership_timeline.md`)
- **Source Document:** `research/project_charter.md` §4.3; `docs/CAUSAL_MODEL.md`
- **Original Motivation:** Disengagement is not instantaneous capability recovery. What the vehicle does during human reaction latency $[0, t_{reaction})$ directly alters kinetic energy at the moment of human control takeover.
- **Scientific Object:** Control ownership timeline and vehicle state evolution during human reaction latency.
- **Intended Independent Variables:** Withdrawal policy $\{W0, W1, W2\}$, reaction time $t_1$.
- **Intended Outcome Variables:** Speed at reaction time $v(t_1)$, critical lead time $T_{TOR\_critical}$, stopping margin.
- **Intended Evidence / Experiment:** Factorial simulation sweep and cross-partial interaction derivation (originally Phase 1A / Phase 3).
- **Intended Claim Level:** TYPE 1 (Interaction Proof) / TYPE 2 (Simulation Mapping).

---

### 3.2 Subsidiary Mechanisms, Scenario Variables, and Examples

The earliest materials explicitly treat the following items as **mechanisms, scenario variables, or examples**, NOT as independent top-level research questions:

1. **High-Performance Acceleration Authority (Gate B):**
   - *Role:* A **scenario-escalation variable**, not a standalone question.
   - *Source:* `research/project_charter.md` §4.1, Gate B; `docs/DECISIONS.md` D005.
   - *Clarification:* D005 explicitly directed: *"Do not test acceleration capability in a fixed-speed braking experiment. Use a separate risk-state-escalation scenario in which identical-duration acceleration commands produce different hazard-entry states."*
2. **Low-Speed Regenerative Roll-off ($v_{rolloff}$):**
   - *Role:* An **actuator modeling mechanism** introduced in Phase 0.2 (`vehicle_response_model.md`) to represent physical motor fade near standstill and avoid trivial linear time-shift identities.
3. **Staged Automation Withdrawal (W2):**
   - *Role:* A **handover policy variant** involving blended control transfer, excluded in Phase 0.4 (`CAUSAL_MODEL.md`) because blending shape was unconstrained.
4. **EV vs ICE Comparison:**
   - *Role:* A **motivating real-world example**, explicitly barred from being a scientific label.
   - *Source:* `docs/DECISIONS.md` D001, D002; `project_charter.md` §1, §8.

---

## 4. Central Scope Coverage Matrix

The following matrix audits every original research question, mechanism, and requirement against what was actually executed in the repository.

| Original Research Question / Component | Original Intended Evidence / Experiment | What Was Actually Done | Current Status | Evidence Produced | What Remains Unanswered | Final Disposition |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **RQ 1: System-Level Joint Recoverability Envelope** | Multi-layer coupled simulation yielding $P(\text{safe fallback} \mid \text{state})$ across human & vehicle distributions | Derived exact closed-form deterministic stopping boundary $T_{required}$; proved coordinate monotonicity; audited parameter closure | ~~PARTIALLY ANSWERED~~ **[AUDIT 2026-09-22: NOT STARTED / GATED — only a deterministic longitudinal vehicle-side slice exists]** | Closed-form equation; automated unit tests (39 passed); parameter closure table (`e0_parameter_closure.csv`) | Probabilistic envelope $P(\text{safe fallback})$; human reaction distributions; multi-layer stochastic coupling | Precursor boundary completed; full probabilistic envelope deferred to future work |
| **RQ 2: Vehicle Longitudinal-Response Architecture** | Factorial simulation isolating transients ($t_2, t_3, a_{pre}$) from $a_{max}$ across scenario grids | Executed A1 factorial sweep; derived exact analytical partial derivatives $\partial T / \partial x_i$; evaluated bounded effect sizes | ~~ANSWERED~~ **[AUDIT 2026-09-22: PARTIAL — saturated emergency braking only; u→a mapping untested]** | Exact analytical derivative $\partial T/\partial a_{pre} = -0.155\text{ s/(m/s}^2)$; bounded effect sizes $\Delta T(a_{pre}) \approx 0.44\text{ s}$, $\Delta T(t_2) \approx 0.12\text{ s}$; Claim Ledger NUM-01 to NUM-11 | Human behavioral adaptation to vehicle dynamics; empirical physical pressure telemetry | Fully answered for deterministic longitudinal stopping kinematics |
| **RQ 3: Driver Internal-Model & Familiarity Mismatch** | Human simulator / naturalistic takeover data testing familiarity prior $M = D(\hat{f}_d, f_v)$ on braking performance | Conducted theoretical sensitivity derivation and empirical dataset forensics in Branch C0 | **DEFERRED — DATA REQUIRED** | Analytical proof that $\partial a_{ego}/\partial M = 0$ under full-brake step; forensic audit showing public datasets lack familiarity labels | Does familiarity mismatch alter modulated pedal braking, reaction time, or path stabilization? | Deferred; requires dedicated human-in-the-loop experiment |
| **RQ 4: Automation Handover & Withdrawal Policy** | Comparison of W0, W1, and W2 across vehicle architectures and reaction times | Derived analytical interaction term $\partial^2 D_{stop}/\partial a_{pre}\partial t_3 = -t_1/2$; executed A1 2×2 factorial sweep; integrated into D0 boundary | ~~PARTIALLY ANSWERED~~ **[AUDIT 2026-09-22: NOT STARTED beyond the narrow W0/W1 abstraction; TOR budget never varied]** | Symbolic proof of non-trivial cross-term; simulation sweep in `a1_core_sweep.csv`; closed-form integration in D0 | Staged/blended withdrawal (W2); driver behavioral adaptation to withdrawal timing | W0 vs W1 resolved; W2 removed by design due to unconstrained parameters |
| **Mechanism: High Acceleration Risk Escalation** | Scenario-escalation experiment testing rate of fallback margin consumption from identical throttle commands | Formulated Markovian state proof in Branch B0 | **ANALYTICALLY RESOLVED** | Mathematical proof that pre-TOR acceleration history has zero independent effect once $(x_0, v_0)$ is fixed | Broader socio-technical impact of performance on driver anticipation and speed selection | Kinematic mechanism resolved; dynamic simulation killed |
| **Mechanism: Low-Speed Regen Roll-off ($v_{rolloff}$)** | Nonlinear simulation of electric motor torque fade near standstill | Evaluated in early Phase 0; retained as counterfactual sensitivity; excluded from primary analytical boundary | **REMOVED BY DESIGN** | Bounded sensitivity checks showing $< 0.1\text{ m}$ impact on emergency stopping distance | Exact empirical fade curve of production EV inverters | Dropped from core boundary to preserve exact closed-form solvability |
| **Policy: Staged Withdrawal (W2)** | Blended automation-to-human control transfer modeling | Audited in Phase 0.4 (`CAUSAL_MODEL.md`) and Branch D0 | **REMOVED BY DESIGN** | Formal justification that blending ramp introduces unevidenced free parameters | Safety implications of ramped handover | Excluded to prevent unconstrained free parameterization |
| **Outcomes: Stabilization ($T_{stable}$) & Corrections ($N_{corr}$)** | Measurement of time to recover stable driving and count of corrective pedal/steering modulations | Dropped in Phase 0.2 (`metric_definitions.md`) when open-loop step driver was frozen | **NOT YET ADDRESSED** [AUDIT 2026-09-22: the later Phase 2B `T_stable` and full-record correction counts are WITHDRAWN / INVALID AS COMPUTED] | None (deliberately omitted to prevent reporting structural non-results) | Closed-loop control recovery; multi-stage pedal modulation; yaw stabilization | Retained as future work requiring closed-loop human controller |
| **Dynamics: Lateral Avoidance & Steering Recovery** | Simulation of steering swerve around stationary obstacle | Restricted in Phase 0.1 to pure longitudinal braking | **OUT OF SCOPE AFTER REFINEMENT** | None (deliberately scoped out) | Combined braking and swerving fallback envelopes | Scoped out of current project; belongs in future 2D extensions |
| **Validation: Multi-Vehicle Outcome Validation** | Validation of fallback safety envelope against fleet crash/takeover records | Forensic audit of datasets D001–D005 in Branch E0 | **DEFERRED — DATA REQUIRED** | Level 2 / V1 parameter-level closure table; identification of Level 3–5 data barriers | Fleet crash probabilities; direct trajectory matching | Acknowledged as fundamental epistemic bound of public data |

---

## 5. Detailed Audits of Core Subsystems

### 5.1 Audit of the Driver Internal-Model Question (Prompt §4)
- **Original Intent:** The charter (§4.2) and `README.md` (Phase 2) explicitly intended to investigate whether driver familiarity priors (e.g. EV-experienced vs EV-naive drivers used to ICE coastdown, one-pedal driving familiarity) alter takeover safety via an internal model mismatch $M = D(\hat{f}_{driver}, f_{vehicle})$.
- **What Was Actually Done:** Branch C0 performed an identifiability audit and mathematical sensitivity analysis.
- **Why It Was Deferred:**
  1. *Causal Severance under Panic Braking:* In the frozen open-loop model, the driver applies a step command to full braking ($u_{brake} = 1.0$). Under this panic step, the physical brake system immediately saturates to maximum deceleration capability $a_{max}$. Consequently, pedal-gain mismatch $M$ has **zero mathematical pathway** to alter vehicle deceleration ($\partial a_{ego} / \partial M = 0$).
  2. *Data Non-Identifiability of Mismatch:* Direct inspection of public naturalistic driving and simulator datasets confirms that none record driver vehicle-familiarity history, one-pedal habituation, or prior EV exposure.
- **Critical Epistemic Distinction (Phase 2A):**
  - **Familiarity Mismatch ($M$):** Requires dedicated human-in-the-loop experimental trials featuring controlled pre-trial driver familiarization (EV one-pedal vs conventional ICE) and cross-vehicle transitions. Mismatch is non-identifiable on current public data (**`M0-C`**).
  - **Generic Closed-Loop Human Control:** **IS AVAILABLE** in public data. The TU Delft Takeover Dataset (D003) provides 513 full 20 Hz continuous trials with continuous brake force (N), gas pedal, steering wheel angle, lateral lane deviation, and obstacle distance, enabling closed-loop human modeling without new human subject recruitment (**`H2A`**).
- **Classification:** Familiarity mismatch $M$ is **`DEFERRED (M0-C)`**; generic closed-loop human fallback is ~~`UNLOCKED VIA PUBLIC DATA (H2A)`~~ **[AUDIT 2026-09-22: not established; D003 has open blockers]** and active in Phase 2B.

### 5.2 Audit of the Vehicle-Response Question (Prompt §5)
The vehicle-response question must be strictly separated into its physical vehicle-side and human behavioral components:
- **A. Physical Vehicle-Side Response:** ~~`ANSWERED / ANALYTICALLY RESOLVED`~~ **[AUDIT 2026-09-22: PARTIAL / MODEL-VALID — correct inside the deterministic open-loop 1-D saturated-braking model; not empirical validation; not a completed vehicle-response layer]**.
  - The project derived the exact analytical required lead time equation:
    $$T_{required} = \frac{v_0}{2 a_{max}} + t_1 \left(1 - \frac{a_{pre}}{a_{max}}\right)\left(1 - \frac{a_{pre} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right) - \frac{a_{max} t_3^2}{24 v_0}$$
  - Established exact marginal sensitivities ($\partial T / \partial a_{pre} = -0.155\text{ s/(m/s}^2)$ at nominal baseline; domain span $[-0.422, -0.083]\text{ s/(m/s}^2)$).
  - Computed bounded effect sizes ($\Delta T(a_{pre} \in [0, 3]) \approx -0.44\text{ s}$, saving $8.8\text{ m}$ at nominal speed; $\Delta T(t_2) \approx +0.12\text{ s}$; $\Delta T(t_3) \approx +0.15\text{ s}$).
- **B. Human Behavioural Response to Vehicle Mappings:** **`NOT YET ADDRESSED`**.
  - The project has **not** investigated how human reaction time $t_1$, pedal depression speed, or initial urgency change when drivers anticipate or experience different vehicle deceleration profiles (e.g. whether aggressive regenerative deceleration causes drivers to brake more slowly or hesitate).
- **C. Pedal-Behaviour Effect:** **`NOT YET ADDRESSED`**.
  - Modulated pedal displacement, foot transfer trajectories, and closed-loop corrections were deliberately frozen out of Phase 1.

### 5.3 Audit of the High-Acceleration Question (Prompt §6)
- **Role in Original Architecture:** High acceleration capability was **never a top-level research question**. It was introduced in `project_charter.md` §4.1 (Gate B) and `docs/DECISIONS.md` (D005) as a **scenario-escalation mechanism**—specifically, asking whether high-powered vehicles accelerate more rapidly into hazardous kinetic states prior to TOR issuance.
- **What Branch B0 Established:**
  - In Branch B0, an analytical proof demonstrated that within a deterministic longitudinal Markov state space, pre-TOR acceleration history $a(t)$ for $t < t_{TOR}$ has **identically zero independent causal effect** on post-TOR stopping distance or required lead time once the state at TOR $(x_{TOR}, v_{TOR})$ and post-TOR physical parameters are fixed. The state $(x_{TOR}, v_{TOR})$ acts as a complete mathematical mediator.
- **What B0 DOES NOT Answer:**
  - It does **not** answer whether operating a high-acceleration vehicle alters driver vigilance, forward headway choice, cognitive workload, or speed expectancy prior to handover.
  - It does **not** address ADS operational design domain (ODD) boundaries or speed-governing policies for high-performance vehicles.
- **Classification:** Kinematic mechanism **`ANALYTICALLY RESOLVED`**; broader behavioral implications **`OUT OF SCOPE AFTER REFINEMENT`**.

### 5.4 Audit of the Handover / Fallback Boundary Question (Prompt §7)
- **Original Meaning of Authority vs Capability:**
  The charter (§4.3) coined the axiom *"authority transfer != capability recovery"*, defining three distinct milestones:
  - $T_{authority}$: Nominal handover instant (TOR issued).
  - $T_{effective}$: First effective human control action.
  - $T_{stable}$: Dynamic stabilization of the vehicle trajectory.
- **What Is Implemented in Current Model:**
  - $T_{authority} = 0$ (TOR issuance).
  - Reaction latency $t_1$, separating nominal transfer from human action ($T_{effective} = t_1 + t_2$).
  - Actuation delay $t_2$ and deceleration build-up ramp $t_3$.
  - Complete longitudinal stopping boundary $T_{required}$.
- **What Is NOT Implemented:**
  - Closed-loop steering and pedal corrections ($N_{correction}$).
  - Lateral path recovery and yaw stabilization ($T_{stable}$).
  - Partial or graduated braking.
  - Staged/blended authority transfer (Policy W2).
- **Classification:** ~~`PARTIALLY ANSWERED`~~ **[AUDIT 2026-09-22: human reacquisition PARTIAL / RESTRUCTURE; transition NOT STARTED beyond W0/W1]**. The longitudinal stopping component is model-valid only; dynamic stabilization and capability reacquisition remain unestablished.

### 5.5 Audit of the Coupled-System Question (Prompt §8)
- **Original Intent:** The charter (§4.4) envisioned a unified, coupled multi-layer model simultaneously evaluating:
  $$\text{Vehicle Response} \times \text{Driver Internal Model} \times \text{Handover Timing} \times \text{Scenario Criticality}$$
- **Actual Establishment:**
  - The project did **not** produce a coupled model where dynamic human behavior, cognitive mismatch, and vehicle physics interact adaptively.
  - Instead, the project produced a **deterministic vehicle-side recoverability boundary with human behavior frozen as a one-shot open-loop step response**.
  - The only coupling present is the physical interaction between automation withdrawal ($W0$ vs $W1$), pre-effective deceleration ($a_{pre}$), actuation transients ($t_2, t_3$), and reaction latency ($t_1$) within a deterministic 1D kinematic stopping equation.
- **Classification:** ~~`PARTIALLY ANSWERED`~~ **[AUDIT 2026-09-22: NOT STARTED / GATED]**.

### 5.6 Audit of the Human Fallback Safety Envelope (Prompt §9)
- **Original Intent:** A probabilistic envelope:
  $$P(\text{safe fallback} \mid \text{state}) = f(v_0, a_{pre}, M, t_1, t_2, t_3, a_{max}, \text{scenario})$$
  reflecting stochastic distributions of human reaction times, surface friction, and driver error.
- **Actual Establishment:**
  - The project established a **deterministic kinematic recoverability boundary**:
    $$T_{available} \ge T_{required}(v_0, t_1, a_{pre}, t_2, t_3, a_{max})$$
  - This boundary is a **deterministic precursor** and a **vehicle-side physical slice** of the originally envisioned envelope.
  - It does **not** compute collision probabilities because input joint probability distributions across the population have not been empirically identified.
- **Classification:** Deterministic precursor completed; probabilistic envelope **`NOT YET ADDRESSED`**.

---

## 6. Structural Reconciliation: Original vs Current Repository

The following table maps the original charter structure directly to the later implementation branches:

| Original Charter Structure (`project_charter.md`) | Later Implementation Branch | Actual Structural Relationship |
| :--- | :--- | :--- |
| **Layer 4.1: Vehicle-Response Layer** | **Branch A0, A1, D0, E0** | Fully subsumed and analytically completed into closed-form equation $T_{required}$ and bounded parameter sweeps. |
| **Layer 4.2: Driver Internal-Model Layer** | **Branch C0** | Converted into an identifiability audit; proved causally severed under full-brake step; deferred pending empirical human data. |
| **Layer 4.3: Handover & Withdrawal Layer** | **Branch A1, D0** | W0 vs W1 factorial comparison completed in A1 and integrated into D0 closed form; W2 removed by design due to unconstrained parameters. |
| **Layer 4.4: System-Level Safety Envelope** | **Branch D0, E0** | Reduced from a probabilistic $P(\text{safe fallback})$ envelope to a deterministic kinematic recoverability boundary ($T_{required}$). |
| **Mechanism: Acceleration Authority (Gate B)** | **Branch B0** | Analytically resolved via Markov mediation proof; dynamic simulation branch (B1) killed. |
| **Outcomes: $T_{stable}$ & $N_{correction}$** | Dropped in Phase 0.2 | Excluded from simulation code to prevent reporting structural non-results under open-loop step braking. |
| **Phase 4 & 5: Coupled Simulation & Envelope** | **Branch D0, E0** | Replaced by direct analytical derivation and numerical parameter mapping ($D0\text{-}B, E0\text{-}A$), eliminating the need for dynamic bisection loops. |
| **Phase 6: Multi-Vehicle Real-World Validation** | **Branch E0 / Dataset Audit** | Bounded at Level 2 / V1 (Parameter-Level Evidence); trajectory (L3) and outcome (L4) validation proven unidentifiable on open data. |

---

## 7. Original Requirements Not Yet Satisfied

The following original requirements from `project_charter.md`, `README.md`, and Phase 0 plans remain unsatisfied:

1. **Driver Familiarity & Vehicle-Switch Mismatch ($M$):**
   - *What it was:* Testing whether drivers accustomed to ICE vehicles make errors when taking over an EV with aggressive regenerative braking.
   - *Why it disappeared from Phase 1:* Proved to have zero causal pathway under open-loop full-brake step commands; unidentifiable in public open datasets ($M0\text{-}C$).
   - *Disposition:* Requires future dedicated human-in-the-loop experimental trials with cross-vehicle transitions; remains unresolved in public data.
2. **Dynamic Stabilization ($T_{stable}$) and Closed-Loop Corrections ($N_{correction}$):**
   - *What it was:* Measuring the time required to regain steady lane-keeping and the count of pedal/steering corrections post-TOR.
   - *Phase 2A Finding:* **UNLOCKED VIA PUBLIC DATA.** Forensic audit of TU Delft (D003) revealed 513 complete 20 Hz trials with continuous brake force (N), gas pedal, steering wheel angle, lateral lane deviation, and obstacle distance.
   - *Disposition:* ~~Fully addressable without new human participant recruitment!~~ **[AUDIT 2026-09-22: Not established. The Phase 2B `T_stable` metric is WITHDRAWN (81% of values fall after handback to automation) and correction counts are INVALID AS COMPUTED. See `research/data_matrix/D003_KNOWN_BLOCKERS.md`.]**
3. **Lateral Avoidance and Steering Dynamics:**
   - *What it was:* Modeling evasive steering around obstacles as an alternative to emergency braking.
   - *Why it disappeared:* Excluded in Phase 0.1 to maintain a tractable, provably robust longitudinal boundary.
   - *Disposition:* Retain as a post-paper research direction.
4. **Staged / Blended Automation Withdrawal (W2):**
   - *What it was:* Modeling gradual transitions of control authority rather than discrete steps.
   - *Why it disappeared:* Excluded in Phase 0.4 because blending curves introduce arbitrary, unevidenced free parameters.
   - *Disposition:* Outside the scope of the current paper.
5. **Probabilistic Safety Envelope $P(\text{safe fallback} \mid \text{state})$:**
   - *What it was:* A population-level probability distribution of collision risk conditional on driver and vehicle states.
   - *Why it disappeared:* Replaced by the exact deterministic boundary $T_{required}$ because joint probability distributions over driver reaction time and friction are unidentified.
   - *Disposition:* Retain deterministic boundary as precursor; probabilistic envelope belongs in future work.
6. **Empirical Continuous Trajectory (Level 3) and Crash Outcome (Level 4) Validation:**
   - *What it was:* Validating the model against continuous real-world L3 takeover telemetry and crash records across diverse vehicle models.
   - *Phase 2A Finding:* High-frequency continuous takeover trajectory data **does exist in simulation (TU Delft D003: 20 Hz, 513 trials)** and naturalistic steering disengagements (ADAS-TO D001: 100 Hz subset). However, multi-vehicle production crash records (Level 4) and proprietary OEM brake blending maps remain unidentifiable.
   - *Disposition:* ~~Level 3 continuous trajectory validation is unlocked for simulation benchmarks;~~ **[AUDIT 2026-09-22: not established; D003 samples a non-critical 7 s regime with an unparameterised simulator vehicle]** production crash outcome validation remains a formal epistemic limit (V1).

---

## 8. Project Stage Classification

Based on this audit, the project is formally classified as:

### Primary Classification:
> ~~`H0-B: CORE PHYSICAL SPINE COMPLETE, HUMAN / COUPLED QUESTIONS REMAIN`~~ **[AUDIT 2026-09-22: WITHDRAWN. Current stage: EXPLORATORY.]**

### Justification and Secondary Nuance:
- **Why `H0-B` (historical reasoning; WITHDRAWN 2026-09-22 — the boundary is model-valid only and is one slice of the vehicle-response layer, not "absolute completion"):** The project has brought its core physical vehicle-response and kinematic fallback boundary to absolute completion:
  - Exact closed-form solution derived and verified against analytical oracles ($D0$).
  - Monotonicity and robustness proven everywhere in the admissible domain ($E0$).
  - Correct marginal sensitivities and bounded effect sizes established ($G0.2$, [`docs/QUANTITATIVE_CLAIM_LEDGER.md`](QUANTITATIVE_CLAIM_LEDGER.md)).
  - Epistemic evidence boundaries strictly audited and anchored (Level 2 / V1).
  However, the original human cognitive questions (internal model mismatch, familiarity adaptation, closed-loop stabilization) and the coupled probabilistic safety envelope remain open.
- **Secondary Nuance (`H0-D` Alignment):** The original charter was deliberately broad and exploratory. Through Phase 0 and subsequent branches, the scope was systematically and defensibly narrowed: killing unevidenced branches (B1, D1), deferring unidentifiable human factors (C0), and focusing on the core physical recoverability spine.

---

## 9. Paper vs Full-Programme Decision

The audit establishes a strict distinction between manuscript readiness and full-programme completion:

1. **Is the Current Narrowed Result Sufficient for One Defensible Paper?**
   - ~~**YES.** … constitute a complete, rigorous, and novel scientific contribution. Paper readiness is confirmed as `P1-B: READY, NOVELTY CLAIM MUST BE NARROW`.~~ **[AUDIT 2026-09-22: WITHDRAWN. The `t1 + t2 + t3/2` decomposition and the `−a·t3²/24` term are prior-art-compatible mechanics (accident-reconstruction stopping distance; linear build-up). The remaining novelty candidate is framing/synthesis and is not established. Paper readiness withdrawn.]**
2. **Is the Original Full Research Programme Complete?**
   - **NO.** The comprehensive coupled programme involving human familiarity mismatch, closed-loop stabilization, and probabilistic fleet safety envelopes is incomplete.

### Definitive Status:
> ~~`PAPER-READY, PROGRAMME-INCOMPLETE`~~ **[AUDIT 2026-09-22: WITHDRAWN → EXPLORATORY]**

---

## 10. Final Recommendation and Next Action

### Formal Path Recommendation:
> **`PATH 3: SEQUENCED PROGRAMME — PAPER 1 (DETERMINISTIC PHYSICAL RECOVERABILITY) + PHASE 2 (GENERIC HUMAN CLOSED-LOOP FALLBACK)`**

*(The user has explicitly chosen to continue the original full research programme via public dataset exploitation without participant recruitment).*

### Scientific Rationale:
- **Paper 1 (Deterministic Physical Recoverability):** ~~Fully mature … (`P1-B`)~~ **[AUDIT 2026-09-22: model-valid only; not paper-ready]**. It establishes the physical limits of human fallback under emergency braking without relying on uncalibrated driver models.
- **Phase 2 (Generic Closed-Loop Human Fallback):** Forensic audit (Phase 2A, `H2A`) established that 513 full 20 Hz continuous trials with brake force, accelerator, and steering are openly available in the TU Delft Takeover Dataset (D003). This allows building a minimal interpretable closed-loop human fallback controller directly from empirical data without participant recruitment.
- **Familiarity Mismatch ($M$):** Retained as an unresolved, explicitly deferred boundary (`M0-C`), requiring future external human-subject experiments.

### Exact Next Action:
1. Conduct **Phase 2B — Build Minimal Interpretable Human Fallback Model** from TU Delft (D003) public trajectory data.
2. Maintain `phase0-frozen` and unit test integrity.
3. Do not recruit participants or purchase hardware.
4. Keep manuscript drafting held pending Phase 2 modeling synthesis.
