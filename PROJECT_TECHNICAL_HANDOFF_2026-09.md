# Technical Project Handoff & Scientific Audit Dossier
**Project:** Vehicle-Aware Human Fallback (`vehicle-aware-human-fallback`)  
**Date:** September 2026  
**Document Type:** Self-Contained Technical Handoff & Epistemic Audit  
**Target Audience:** Independent Scientific Reviewer / Incoming Lead Investigator  
**Repository State:** Main HEAD `1ad1951`, Tag `phase0-frozen` (`bc21fbc`), 55 Unit Tests Passing

---

> ## AUDIT CORRECTION NOTICE (2026-09-22, Phase R0)
>
> This dossier was **untracked** at `main@1ad1951`. Its pre-audit content is preserved verbatim at tag `pre-audit-2026-09-22` (commit `7f918fcc269ce734f6434f069a9c2c35b0269aac`). An independent audit found that it **overstates what has been established**. Corrections are marked inline as **[AUDIT 2026-09-22: …]**; withdrawn text is struck through where it is retained for traceability.
>
> **Authoritative documents now:** `docs/RESEARCH_ARCHITECTURE_V2.md` (architecture), `docs/OBSERVATION_LAYER.md` (measurement rules), `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` (status), `research/data_matrix/D003_KNOWN_BLOCKERS.md` (D003 blockers and the dataset owners' prior analyses).
>
> **Principal corrections:**
> 1. **Stage:** EXPLORATORY. "Paper-ready", `P1-B: READY`, `PAPER-READY, PROGRAMME-INCOMPLETE` and "100% complete" are **withdrawn**.
> 2. **Novelty:** "first exact closed form" and novelty based on `t1 + t2 + t3/2` or `−a·t3²/24` are **withdrawn** (prior-art-compatible mechanics). The remaining candidate (layer separation and coupling; recoverability framework) is **not established**.
> 3. **History:** the original project was one mother question plus mechanism layers. The "four original top-level RQs" and the quoted RQ4 "Original Charter Wording" were constructed in H0 (`c09f682`). W0/W1/W2 first appear in Phase 0.4 (`bc21fbc`).
> 4. **`T_stable` ≈ 22–23 s, "100% settled", "0% censored": withdrawn.** About 81% of nominal `T_stable` values occur after `Time_Manual_Stop`, when the driver has handed control back to automation. Within the human-control window only about 18% of trials settle.
> 5. **Correction counts:** invalid as currently computed (windows include automation).
> 6. **D003 factorial effects:** causal language withdrawn. Cells are aliased with road, speed, distance and hazard state; differences are descriptive and condition-associated only.
> 7. **D003 semantics:** `lane_gap` is unparsed (100% NaN) and its meaning is only inferred; brake-channel and authority semantics are unresolved; lane numbering varies by road; the collision proxy is invalid; 26 trials have multiple TOR values.
> 8. **System-level recoverability:** NOT STARTED / GATED. **Vehicle response:** PARTIAL (saturated braking only). **Transition:** NOT STARTED beyond W0/W1. **Hazard state:** NOT STARTED as a layer. **Familiarity:** direct vehicle-response familiarity is not identifiable from verified public data checked; repeated-exposure learning is identifiable in D003; experience is associational only.
> 9. **Prior work:** the D003 owners (Liang, Calvert, van Lint et al.) have published analyses of button time, takeover time, minimum TTC, maximum deceleration and steering on this dataset. Several H1 metrics are replications, not new findings.
> 10. **R2A (control-channel authorship, B17):** D003 accelerator, brake and steering channels are not driver-only channels; they change in a scenario-cell-specific way within 0.3 s of TOR. Every human first-input quantity below (T_first, brake-first/steer-first, negative handover lag, brake rise, driver-attributed braking/steering) is INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS.

---

## 0. Executive Summary & Reviewer Orientation

This document provides a completely self-contained, forensic technical handoff of the **Vehicle-Aware Human Fallback** research programme. It is written for an independent technical auditor or researcher who has never interacted with this codebase. It reconstructs the project from its foundational 2026 research charter through its analytical mechanics phase, its novelty reclassification, its scope reconciliation, and its empirical human trajectory audit on open public datasets.

### Core Scientific Bottom Line:
1. ~~**The Physical Spine is Solved and Paper-Ready:**~~ **[AUDIT 2026-09-22: PARTIAL / MODEL-VALID; not paper-ready. Correct inside a deterministic open-loop 1-D model; not empirical validation.]**  
   The project has derived, verified against numerical oracles, and sensitivity-audited a closed-form longitudinal stopping requirement (standard kinematics):
   $$T_{\text{required}}(v_0, t_1, a_{\text{pre}}, t_2, t_3, a_{\text{max}})$$
   This boundary models the minimum takeover request (TOR) lead time necessary to prevent a collision with a stationary hazard during an emergency longitudinal stop. It decomposes the authority transition into pre-effective deceleration during driver reaction latency ($a_{\text{pre}}$), actuator delay ($t_2$), and deceleration build-up ramp ($t_3$).
2. **Prior-Art Novelty Scoping (Gate P1-B):** **[AUDIT 2026-09-22: P1-B withdrawn]**  
   Prior art (notably **Papadimitriou et al., 2024** and **Eclipse SUMO / TransAID, 2018–2026**) established that takeover safety requires maneuver execution time and speed-dependent stopping distance. ~~This project's residual novelty is strictly scoped to the closed-form analytical integration of authority-transition deceleration transients ($a_{\text{pre}}, t_2, t_3$) and the resulting sensitivity hierarchy.~~ **[AUDIT 2026-09-22: WITHDRAWN. The reaction + response-delay + half-build-up decomposition is standard accident-reconstruction practice and `−a·t3²/24` follows directly from a linear ramp. The remaining novelty candidate is framing/synthesis and is not established.]**
3. **The Original Coupled Programme is Incomplete:**  
   The original research architecture envisioned a coupled human–vehicle cognitive system incorporating driver familiarity priors ($M$), vehicle-switch mismatch, and a probabilistic safety envelope. ~~Familiarity mismatch is unidentifiable from public open datasets (Gate `M0-C`).~~ **[AUDIT 2026-09-22: Direct vehicle-response familiarity (EV / one-pedal / regen) × takeover response is not identifiable from the verified public data checked. Repeated-exposure learning is identifiable in D003; driving and ADAS experience are only associational.]**
4. ~~**Generic Human Recovery is Unlocked from Public Data (Gate H1-B):**~~ **[AUDIT 2026-09-22: PARTIAL / RESTRUCTURE. D003 measurement semantics are unresolved; the dataset owners have already published analyses of several of these metrics.]**  
   Public trajectory data from the **TU Delft Takeover Dataset (D003: 57 participants, 513 trials at 20 Hz)** provides brake, accelerator, steering angle, and vehicle state telemetry (brake-channel semantics unresolved). ~~Empirical analysis demonstrates that takeover recovery is multimodal, oscillatory, and closed-loop, requiring ≈ 22–23 s to settle into steady cruising.~~ **[AUDIT 2026-09-22: WITHDRAWN: about 81% of the nominal `T_stable` values occur after the driver has handed control back to automation.]**
5. **Epistemic Classification:**  
   ~~The project is `PAPER-READY, PROGRAMME-INCOMPLETE` (Milestone `H0-B`). The physical vehicle-response spine is ready for publication, while the human-in-the-loop recovery modeling continues actively in Phase 2B.~~ **[AUDIT 2026-09-22: Current stage: EXPLORATORY, with a potentially thesis-capable / paper-shaped core after repairs. Not manuscript-ready or submission-ready.]**

---

## 1. Reconstruction of the Original Project

### 1.1 The Motivating Problem & Core Axiom
From `research/project_charter.md` (§1) and `README.md`:
> *"Automation may hand control authority to a human when it reaches a difficult state, but authority transfer does not necessarily mean that the human–vehicle system has recovered enough capability to avoid the hazard."*

The industry standard approach to Level 3 automated driving has historically treated takeover safety as a scalar time-budget problem: if an automated driving system (ADS) issues a TOR 4 to 7 seconds before an operational design domain (ODD) exit, the handover is assumed safe. This project was founded on the rejection of that scalar assumption: safety is a **joint recoverability property** governed by the physical interaction between vehicle response kinematics, automation disengagement policy, human driver cognitive/motor capability, and scenario geometry.

### 1.2 The Foundational Mother Question
From `research/project_charter.md` (§2):
> *"Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?"*

### 1.3 The Working Thesis & Envisioned Joint Safety Envelope
From `research/project_charter.md` (§3):
> *"Human fallback safety should be treated as a joint recoverability property of the human, vehicle and automation rather than as a function of TOR lead time alone. A conceptual form is:*
> $$P(\text{safe fallback}) = f(\text{vehicle state}, \text{braking response}, \text{driver–vehicle mismatch}, \text{TOR budget}, \text{human response}, \text{environment/scenario criticality})"$$

### 1.4 ~~The Original Four Top-Level Research Questions~~ The H0 Four-RQ Construction (not original)
**[AUDIT 2026-09-22: The charter contains **one mother question (§2) and four mechanism layers (§4.1–§4.4)**, not four top-level RQs. The RQ1–RQ4 structure below was constructed in H0 (`c09f682`). The quoted RQ1 text is the mother question; the RQ2 "quote" splices §4.1 with Gate A; **the RQ4 "Original Charter Wording" does not appear in the charter or any pre-H0 file.** See `docs/RESEARCH_ARCHITECTURE_V2.md` §1.]**

~~Auditing `research/project_charter.md` (§4) and `docs/RESEARCH_ARCHITECTURE_V1.md` reveals four original top-level research questions:~~ As constructed in H0:

1. **RQ1 — System-Level Joint Recoverability & Safety Envelope:**  
   *Original Charter Wording:* *"Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?"* (§2, §3).  
   *Focus:* Multi-layer stochastic coupling producing a probabilistic recovery boundary $P(\text{safe fallback} \mid \text{state})$.
2. **RQ2 — Vehicle Longitudinal-Response Architecture Effect:**  
   *Original Charter Wording:* *"Study the mapping from control input to actual longitudinal response, including: progressive friction-dominant braking, regenerative braking, one-pedal-like response, blended/nonlinear braking, response latency, deceleration build-up, jerk, maximum deceleration, road friction... Does realistic braking-response changes materially alter recovery metrics?"* (§4.1, Gate A).  
   *Focus:* Decoupling transient deceleration parameters ($a_{\text{pre}}, t_2, t_3$) from maximum steady-state deceleration ($a_{\text{max}}$).
3. **RQ3 — Driver Internal-Model & Familiarity Mismatch:**  
   *Original Charter Wording:* *"Let $\hat{f}_{\text{driver}}$ represent the driver's expected input $\to$ vehicle-response mapping and $f_{\text{vehicle}}$ the actual mapping. Define a generic mismatch term: $M = D(\hat{f}_{\text{driver}}, f_{\text{vehicle}})$. Phase 1 fixes $M = 0$. Later phases test whether mismatch changes first control action, secondary corrections, TTC, stopping margin and stabilisation."* (§4.2, Gate C).  
   *Focus:* Cognitive/motor errors caused by driver unfamiliarity when switching between vehicle response mappings (e.g. conventional ICE coastdown vs aggressive EV one-pedal regeneration).
4. **RQ4 — Automation Handover & Withdrawal Policy:**  
   **[AUDIT 2026-09-22: NOT CHARTER WORDING. Written in H0; W0/W1/W2 first appear in Phase 0.4 (`bc21fbc`). The charter's handover layer (§4.3) is about T_authority, T_effective and T_stable.]**  
   ~~*Original Charter Wording:*~~ *Wording as asserted by H0:* *"How does automation withdrawal policy (immediate withdrawal W1 vs cruise-maintenance W0 vs staged withdrawal W2) interact with vehicle response architecture and driver reaction latency to determine safe takeover time budget?"* (§4.3, §5; `docs/CAUSAL_MODEL.md`).  
   *Focus:* The evolution of kinetic energy during the human reaction interval $[0, t_1)$ prior to active human braking.

---

## 2. Core Conceptual Model & Temporal Architecture

### 2.1 The Conceptual Decomposition
The project decomposes the human fallback problem into four interacting components:
```
+-----------------------------------------------------------------------------------+
| 1. SCENARIO / CRITICALITY STATE                                                    |
|    - Initial velocity: v_0                                                        |
|    - Initial spatial clearance: d_0 (or initial TTC_0)                            |
|    - Road-tire surface friction: mu                                               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 2. AUTOMATION WITHDRAWAL / HANDOVER POLICY                                         |
|    - W0: System maintains longitudinal speed until driver active input          |
|    - W1: System cuts propulsion immediately at TOR (permits uncommanded coast)    |
|    - W2: Staged / ramped authority withdrawal (unconstrained; excluded)           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 3. HUMAN DRIVER RESPONSE LAYER                                                    |
|    - Reaction latency: t_reaction (t_1)                                           |
|    - Action selection: Multimodal (Brake-first vs Steer-first vs Both)            |
|    - Cognitive mismatch: M = D(f_hat_driver, f_vehicle)                           |
|    - Closed-loop modulation: Multi-peak corrective control                        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 4. VEHICLE TRANSIENT RESPONSE LAYER                                               |
|    - Pre-effective deceleration: a_pre (powertrain drag / regenerative braking)    |
|    - Mechanical/transport delay: t_2 (actuator dead time)                        |
|    - Hydraulic/pressure build-up: t_3 (finite deceleration ramp / jerk)           |
|    - Saturated capability: a_max (friction-limited steady-state deceleration)     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| SYSTEM RECOVERABILITY OUTCOME                                                     |
| Stopping Margin: Delta d = d_0 - D_stop >= 0   <===>   T_available >= T_required  |
+-----------------------------------------------------------------------------------+
```

### 2.2 Authority Transfer $\ne$ Capability Recovery
A foundational principle of this project is the strict distinction between legal/nominal authority and physical/dynamic capability:
- **Authority Transfer:** The discrete digital event where the automated driving system relinquishes supervisory control and commands the driver to resume manual driving.
- **Capability Recovery:** The continuous, multi-second physiological and physical process through which the driver perceives the hazard, moves their limbs, depresses the pedals, overcomes mechanical and hydraulic response delays, and executes stabilizing steering/braking actions.

### 2.3 The Intended Temporal Sequence: Conceptual vs Observed Variables
The project defines a rigorous temporal sequence:

```
t = 0                  t = T_first            t = T_effective          t = T_pass              t = T_stable
  |--------------------------|----------------------|-----------------------|-----------------------|
  |   Reaction Latency t_1   |   Actuator Lag t_2   |   Active Maneuver     |   Settling Transients |
TOR Issued             First Human Input     Plant Deceleration       Obstacle Station       Steady Highway
(T_request)            Detected (Pedal/Wheel) Response Detected       Crossed Longitudinally  Cruise Reclaimed
```

| Milestone | Conceptual Meaning | Directly Observed Variable (D003) | Epistemic Status / Formula |
| :--- | :--- | :--- | :--- |
| **$T_{\text{request}}$** | The digital instant the TOR is sounded to the driver. | `[72 (Time_Takeover_Request)].val` | Direct ground-truth timestamp ($t = 0$). |
| **$T_{\text{manual\_start}}$** | The instant the driver depresses the steering-wheel disengagement button. | `[73 (Time_Manual_Start)].val` | Direct event (mode-switch button; owners: "enabling manual inputs"). **[AUDIT 2026-09-22: The "60.2% brake before button" figure depends on unresolved brake-channel semantics; whether this event is the authority transfer is UNRESOLVED (D003 blockers B6, B7).]** |
| **$T_{\text{authority}}$** | The true physical transfer of vehicle control authority. | Not a separate physical sensor channel. | Operationally anchored to $T_{\text{request}}$ under W1, or $T_{\text{first\_ctrl}}$ under W0. **[AUDIT 2026-09-22: In D003 the authority window is UNRESOLVED.]** |
| **$T_{\text{first\_ctrl}}$** | First detected human active physical intervention. | Brake channel $F_b > 15\text{ N}$ or steering deviation $|\Delta \delta| > 0.05\text{ rad}$. **[AUDIT 2026-09-22: brake channel may not be pure driver pedal input; 80/498 detections fall within 0.3 s of TOR.]** | Operational detector: $\min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$. |
| **$T_{\text{effective}}$** | First subsequent physical vehicle-state response. | Longitudinal deceleration $\Delta a_x \ge 0.5\text{ m/s}^2$ or lateral $|\Delta a_y| \ge 0.3\text{ m/s}^2$. | Causally constrained: must occur at or after $T_{\text{first\_channel}}$. Median delay $0.05 - 0.10\text{ s}$. |
| **$\text{Time\_Lane\_Change}$** | Discrete simulator lane-boundary crossing. | `[78 (Time_Lane_Change)].val` | ~~Discrete event when `lane_id` flips from 2 → 3 (Row 44 of data dictionary).~~ **[AUDIT 2026-09-22: The dictionary says only "the time when the car changed to the left lane during takeover". Lane numbering varies by road (2→3, 6→5, 7→6); timing requires per-trial validation.]** Not maneuver completion. |
| **$T_{\text{pass}}$** | Ego front bumper crosses obstacle longitudinal coordinate. | $d_{\text{obstacle}}(t) \le 0.0\text{ m}$ | Pure geometric longitudinal passage. **Does not establish safe clearance.** |
| **$T_{\text{safe\_clear}}$** | Vehicle safely clears obstacle with non-zero lateral margin. | **UNRECORDED IN D003 TELEMETRY.** | Not directly observed: D003 lacks obstacle lateral bounds. **[AUDIT 2026-09-22: A lane-level proxy may become possible after `lane_gap`/`lane_id` repair.]** |
| **$T_{\text{stable}}$** | Control derivatives and dynamic states settle into steady cruise. | $|\dot{\delta}_{\text{sw}}| \le 0.05\text{ rad/s}$ and $|\dot{F}_b| \le 20\text{ N/s}$ sustained for $1.5\text{ s}$. | ~~Operational kinematic settling metric. Median ≈ 22.2–23.0 s across candidate anchors.~~ **[AUDIT 2026-09-22: WITHDRAWN as a human metric: about 81% of values occur after `Time_Manual_Stop` (automation re-engaged).]** |

### 2.4 Driver Internal-Model Mismatch ($M$) and Identifiability
- **Mathematical Formulation:**  
  Let $\hat{f}_{\text{driver}}: \mathcal{U} \to \mathcal{Y}$ represent the driver's cognitive expectation of vehicle deceleration given a pedal input $u$, and let $f_{\text{vehicle}}$ represent the actual physical mapping. The mismatch is:
  $$M = \mathcal{D}(\hat{f}_{\text{driver}}, f_{\text{vehicle}})$$
- **Why It Is Severed in Phase 1:**  
  Under panic emergency braking, the driver commands step emergency braking ($u = 1.0$). At $u = 1.0$, the brake system requests maximum physical capability $a_{\text{max}}$. Thus, $\frac{\partial a_{\text{ego}}}{\partial M} \equiv 0$.  
  **[AUDIT 2026-09-22: WITHDRAWN as an argument. This is true by construction once u ≡ 1 is assumed, and its premise (step braking) is contradicted by D003's gradual, non-step braking (subject to brake-channel semantics). It says nothing about M under real driver inputs.]**
- ~~**Why It Is Unidentifiable in Public Data (Gate `M0-C`):**~~ **[AUDIT 2026-09-22: M is generic (charter §4.2) and belongs at the human↔vehicle interface. Split: (A) direct EV/ICE, one-pedal or regen familiarity is not identifiable from the verified public data checked; (B) generic prior expectation is descriptive only; (C) repeated-exposure learning **is identifiable** in D003 (trial order recoverable, Latin square balanced); (D) driving and ADAS experience are associational only. "Not found in checked data" ≠ "does not exist".]**  
  Public datasets (D001–D005) do not record driver prior vehicle exposure, EV vs ICE ownership history, or habituation to regenerative braking. Identifying direct vehicle-specific $M$ requires a bespoke experiment with controlled pre-exposure and cross-vehicle transitions.

---

## 3. Chronological Research History & Gate Decisions

The following ledger documents every phase in the project's development. No phases are collapsed.

```
PHASE 0 (Scoping & Architecture: bc21fbc)
  │
  ├──> A0 (Analytical Baseline: e038dab) ────────────────────────── PASS
  │
  ├──> A1 (Withdrawal x Response: 58c3665, aed0e30) ────────────── NARROW / COMPLETE
  │
  ├──> B0 (Risk-State Escalation: 4e97f1e, 324e215) ────────────── ANALYTICAL ONLY (B1 KILLED)
  │
  ├──> C0 (Internal-Model Mismatch: ccc1b56, 4778f22) ──────────── DEFER (C1 NOT AUTHORIZED)
  │
  ├──> D0 (State-Dependent Boundary: 76f539e, 387f964) ─────────── D0-B COMPLETE (D1 NOT REQUIRED)
  │
  ├──> E0 (Boundary Robustness: 9321851, 3cd7673) ──────────────── E0-A COMPLETE (V1 VALIDATION)
  │
  ├──> F0 / G0 (Scientific Synthesis: 5da8b69, e45b55f) ────────── P0-B -> P1-B RECLASSIFICATION
  │
  ├──> G0.1 (Prior-Art Recheck: 3f146aa) ───────────────────────── PAPADIMITRIOU / SUMO INTEGRATION
  │
  ├──> G0.2 (Quantitative Claim Audit: a13ff7f) ────────────────── NUM-01 to NUM-11 FROZEN
  │
  ├──> H0 (Original Scope Reconciliation: c09f682) ─────────────── H0-B (PROGRAMME ACTIVE)
  │
  └──> PHASE 2 (Human Fallback Data Exploitation)
        │
        ├──> Phase 2A (Public Data Audit: 13e3189) ─────────────── H2A (UNLOCKED) / M0-C (DEFERRED)
        │
        ├──> Phase 2B-1 (Empirical Extraction: e9b8629) ────────── D003 513 TRIALS EXTRACTED
        │
        ├──> Phase 2B-1.1 (Method Integrity Audit: d908fa1) ────── H1-B GATE (CAUSAL REPAIR, PROXIES)
        │
        ├──> Phase 2B-1.2 (Measurement Semantics: 569f68e) ─────── T_first IS HUMAN INPUT; HYDRAULIC RETIRED
        │
        ├──> Phase 2B-1.3 (Anchor Consistency Patch: 7eca2eb) ──── min(brake, steer) ANCHOR REPAIR
        │
        └──> Phase 2B-1.4 (Hazard-Clearance Semantics: 1ad1951) ─── T_pass ADOPTED; T_safe_clear UNIDENTIFIABLE
```

### Detailed Phase Specifications:

#### Phase 0 — Research Architecture & Scoping
- **Commit:** `bc21fbce8b9b9518919fcaecd6a301785a1fee0d` (tag: `phase0-frozen`)
- **RQ Addressed:** Research scoping, kill-gate criteria, and causal variable decomposition.
- **Method:** Literature matrix construction (25+ papers), parameter provenance tracking, and formal derivation of the causal DAG.
- **Input Evidence:** Literature review and open dataset inventory (`dataset_inventory.csv`).
- **Main Result:** Established `project_charter.md`, `RESEARCH_ARCHITECTURE_V1.md`, and `CAUSAL_MODEL.md`. Defined independent kill-gates A through E.
- **Gate Decision:** **`COMPLETE`**. Tagged as `phase0-frozen`.
- **What Was NOT Established:** No simulator code existed; analytical equations were not yet integrated.

#### Branch A0 — Simulator Baseline & Closed-Form Analytical Validation
- **Commit:** `e038dab`
- **RQ Addressed:** Simulation infrastructure verification.
- **Method:** Forward Euler numerical integration ($dt = 0.001\text{ s}$) validated against an exact symbolic kinematic oracle.
- **Input Evidence:** Synthetic kinematic test battery (`tests/test_analytical_oracle.py`).
- **Main Result:** Proved numerical integration truncation error matches closed form to $< 10^{-12}\text{ m}$ (machine double precision).
- **Gate Decision:** **`PASS`**. Infrastructure certified for scientific experiments.
- **What Was NOT Established:** Did not represent an empirical finding; purely mathematical verification.

#### Branch A1 — Withdrawal Policy $\times$ Vehicle-Response Architecture
- **Commits:** `58c3665`, `aed0e30`
- **RQ Addressed:** RQ2 (Vehicle response) & RQ4 (Withdrawal policy interaction).
- **Method:** 2×2 factorial simulation sweep cross-classifying withdrawal policy ($\{W0, W1\}$) with vehicle deceleration architecture ($a_{\text{coast}} = 0$ vs $a_{\text{coast}} > 0$).
- **Input Evidence:** Literature-bounded parameters ($v_0 \in \{20, 30\}\text{ m/s}, a_{\text{coast}} \in [1, 4]\text{ m/s}^2$).
- **Main Result:** Confirmed non-zero algebraic cross-term $\frac{\partial^2 D_{\text{stop}}}{\partial a_{\text{coast}} \partial t_3} = -\frac{t_1}{2}$. Proved that the first-order pre-effective deceleration effect ($0.30 - 0.58\text{ s}$, saving $6 - 17\text{ m}$) dwarfs the $W \times R$ cross-term interaction ($|I_{T_{\text{crit}}}| \le 0.070\text{ s}$).
- **Gate Decision:** **`NARROW / COMPLETE`**. Claim narrowed to counterfactual parameter mapping.
- **What Was NOT Established:** Did not model human behavioral adaptation to withdrawal timing.

#### Branch B0 / B1 — High-Acceleration Risk-State Escalation
- **Commits:** `4e97f1e`, `324e215`
- **RQ Addressed:** Scenario escalation mechanism (Gate B).
- **Method:** Formal Markovian state-space derivation.
- **Input Evidence:** OpenLKA Acceleration Dataset (D005) forensics.
- **Main Result:** Proved that within a deterministic longitudinal Markov framework, pre-TOR acceleration history $a(t)$ for $t < t_{\text{TOR}}$ has identically zero independent causal influence on post-TOR stopping distance once the state $(x_{\text{TOR}}, v_{\text{TOR}})$ is fixed.
- **Gate Decision:** **`B0: ANALYTICAL ONLY`**; **`B1 (Dynamic Simulation): KILLED`**.
- **What Was NOT Established:** Does not address socio-technical driver speed choice or risk compensation.

#### Branch C0 / C1 — Driver Internal-Model & Familiarity Mismatch
- **Commits:** `ccc1b56`, `4778f22`
- **RQ Addressed:** RQ3 (Driver familiarity mismatch).
- **Method:** Identifiability audit and sensitivity derivation.
- **Input Evidence:** Forensic audit of public datasets D001–D005.
- **Main Result:** Proved that under step emergency braking, $\frac{\partial a_{\text{ego}}}{\partial M} \equiv 0$ due to brake saturation. Proved that no public dataset contains driver vehicle-familiarity history or EV-vs-ICE transition labels. **[AUDIT 2026-09-22: The severance result is true by construction and is withdrawn as evidence. "No public dataset" should read "none found in the datasets checked".]**
- **Gate Decision:** **`C0: DEFER — HUMAN DATA REQUIRED`**; **`C1: NOT AUTHORIZED`**.
- **What Was NOT Established:** Mismatch effects on modulated pedal braking or steering avoidance remain unknown.

#### Branch D0 / D1 — State-Dependent Handover Boundary Derivation
- **Commits:** `76f539e`, `387f964`
- **RQ Addressed:** Analytical solution of the physical recoverability boundary.
- **Method:** Exact algebraic integration of 4-phase longitudinal deceleration kinematics.
- **Input Evidence:** Closed-form calculus verified by SymPy.
- **Main Result:** Derived exact closed-form equation for $T_{\text{required}}(v_0, t_1, a_{\text{pre}}, t_2, t_3, a_{\text{max}})$. Established that required lead time spans $1.15\text{ s}$ to $3.58\text{ s}$ across the core domain ($1.07\text{ s}$ to $4.98\text{ s}$ wet).
- **Gate Decision:** **`D0-B: COMPLETE (ANALYTICAL + MAPPING)`**; **`D1: NOT REQUIRED`**. **[AUDIT 2026-09-22: PARTIAL / MODEL-VALID: one longitudinal slice of the deterministic precursor, not a completed layer.]**
- **What Was NOT Established:** Boundary is purely longitudinal; does not account for lateral swerving.

#### Branch E0 — Robustness Audit & Parameter Closure
- **Commits:** `9321851`, `3cd7673`
- **RQ Addressed:** Gate E (Robustness) & Validation Hierarchy.
- **Method:** Global coordinate-wise gradient sign verification and leave-one-out parameter sensitivity sweep.
- **Input Evidence:** Parameter closure matrix (`e0_parameter_closure.csv`).
- **Main Result:** Proved $\nabla T_{\text{required}}$ is signed everywhere in the admissible domain $\Omega$ (no interior extrema). Proved a 5-fold variation in build-up ramp $t_3 \in [0.10, 0.50]\text{ s}$ shifts $T_{\text{required}}$ by $< 0.20\text{ s}$ ($< 4.5\%$). Bounded validation level at Level 2 / V1 (parameter-level consistency).
- **Gate Decision:** **`E0-A: COMPLETE`**; Validation level **`V1`**. **[AUDIT 2026-09-22: Monotonicity is MODEL-VALID within the stated domain; no empirical validation of the boundary exists.]**
- **What Was NOT Established:** Trajectory-level (Level 3) and crash outcome (Level 4) empirical validation.

#### Branch F0 / G0 — Scientific Synthesis & Initial Novelty Audit
- **Commits:** `5da8b69`, `040b13f`, `e45b55f`
- **RQ Addressed:** Scientific claim synthesis and wording audit.
- **Method:** Comprehensive internal claim audit and literature cross-referencing.
- **Main Result:** Formulated `FINAL_SCIENTIFIC_SYNTHESIS.md`. Excised hyperbolic claims. Assigned provisional readiness `P0-B` $\to$ `P1-B`.

#### Branch G0.1 — High-Threat Prior-Art Recheck & Novelty Downgrade
- **Commit:** `3f146aa`
- **RQ Addressed:** External citation integrity and novelty defense.
- **Method:** Detailed equation-level comparison against **Papadimitriou et al. (2024)** and **Eclipse SUMO / TransAID (2018–2026)**.
- **Main Result:** Acknowledged that prior work already established maneuver execution time ($TC = TOT + t_{\text{action}}$) and speed-dependent stopping distance. Downgraded problem framing from N3 to **N1** and model formulation to **N2**. Scoped novelty strictly to the closed-form integration of deceleration transients ($a_{\text{pre}}, t_2, t_3$).
- **Gate Decision:** ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN.]**

#### Branch G0.2 — Quantitative Claim Integrity Audit
- **Commit:** `a13ff7f`
- **RQ Addressed:** Numerical consistency across repository deliverables.
- **Method:** Systematic audit of all quantitative claims; corrected erroneous sensitivity values.
- **Main Result:** Formulated `QUANTITATIVE_CLAIM_LEDGER.md` (claims NUM-01 to NUM-11). Replaced erroneous $\sim 0.83\text{ s/(m/s}^2)$ sensitivity claim with the exact derivative $\left.\frac{\partial T}{\partial a_{\text{pre}}}\right|_{\text{nom}} = -0.155\text{ s/(m/s}^2)$ (domain span $[-0.422, -0.083]$). Corrected order-of-magnitude dominance claims to a factor of $\approx 3.7\times$.

#### Branch H0 — Original Scope Reconciliation
- **Commit:** `c09f682`
- **RQ Addressed:** Programmatic reconciliation against original research charter.
- **Method:** Detailed audit of charter commitments against established codebase.
- **Main Result:** Formulated `ORIGINAL_SCOPE_RECONCILIATION.md`. ~~Established that while the physical spine is complete and paper-ready, the original research programme is incomplete. Formally classified as `H0-B`.~~ **[AUDIT 2026-09-22: H0 constructed the RQ1–RQ4 structure and a quoted RQ4 "original wording" that is not in the charter. `H0-B` is withdrawn.]**

#### Phase 2A — Public Human Takeover Data Exploitation Audit
- **Commit:** `13e3189`
- **RQ Addressed:** Feasibility of public human takeover data exploitation.
- **Method:** Forensic inspection of raw files and data dictionaries for D001, D002, D003, D004, and D005.
- **Main Result:** Corrected the misconception that human experimental data was unavailable. ~~Unlocked generic closed-loop human fallback modeling via TU Delft (D003: 513 trials at 20 Hz).~~ **[AUDIT 2026-09-22: D003 is usable only after its blockers are resolved (`research/data_matrix/D003_KNOWN_BLOCKERS.md`); its owners have already published analyses of it.]** Formally separated feasibility into:
  - **`H2A: PUBLIC DATA SUFFICIENT FOR REACTION + CLOSED-LOOP HUMAN MODEL`**
  - **`M0-C: NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA`**

#### Phase 2B-1 — Empirical Takeover Recovery Characterization
- **Commit:** `e9b8629`
- **RQ Addressed:** Empirical characterization of human takeover recovery trajectories.
- **Method:** Full-pipeline extraction of all 513 trials in D003 across 57 participants.
- **Main Result:** Generated `d003_trial_qa.csv` and 7 empirical result tables. Reported non-step braking (rise rate 91.7 N/s over 0.75 s), oscillation (median 2.0 brake reapplications, 2.0 acute steering reversals), and evasion (lane change in 499/513 trials; speed drop 8.3 m/s). **[AUDIT 2026-09-22: Brake metrics depend on unresolved brake-channel semantics; reapplication counts use windows that include automation (invalid as computed). These outputs are retained as pre-audit artifacts.]**

#### Phase 2B-1.1 — Empirical Recovery Methodology & Claim-Integrity Audit
- **Commit:** `d908fa1`
- **RQ Addressed:** Methodological integrity, causal ordering, and signal processing.
- **Method:** Telemetry cross-correlation, causal filtering, and sensitivity sweeps.
- **Main Result:** Identified and repaired 196 causal violations ($39.4\%$) where unconstrained $T_{\text{effective}} < T_{\text{first\_ctrl}}$, enforcing causal monotonicity ($T_{\text{eff}} \ge T_{\text{first}}$) and revealing true actuator delay of $0.05 - 0.10\text{ s}$. Replaced raw zero-crossing counts with McLean & Hoffmann (1975) amplitude-hysteresis steering reversals ($2.0^\circ$ gap). Relabeled 6 collision cases as `DERIVED_COLLISION_PROXY`.
- **Gate Decision:** Reclassified from H1-A to **`H1-B: CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT / STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE`**. **[AUDIT 2026-09-22: Superseded: human reacquisition is PARTIAL / RESTRUCTURE; observation windows, channel semantics and authority windows are unresolved.]**

#### Phase 2B-1.2 — Measurement Semantics & Identification Cleanup
- **Commit:** `569f68e`
- **RQ Addressed:** Operational terminology consistency.
- **Method:** Semantic audit across documentation and ledger.
- **Main Result:** Clarified that $T_{\text{first\_ctrl}}$ is detected human control input, NOT vehicle plant disturbance. Removed "hydraulic" terminology from generic Phase 1 actuator delay ($t_2$). Confirmed $T_{\text{manual\_start}}$ is a button-press flag that lags initial human foot braking by a median of $-0.65\text{ s}$. **[AUDIT 2026-09-22: Not established: whether the brake channel is driver pedal input or includes automation braking is unresolved, so "first control is human input" and the −0.65 s lag are provisional.]**

#### Phase 2B-1.3 — Final Event-Semantics Consistency Patch
- **Commit:** `7eca2eb`
- **RQ Addressed:** Anchor logic repair and missingness handling.
- **Method:** Code refactoring in `src/experiments/h1_sensitivity_analysis.py` and sensitivity grid re-execution.
- **Main Result:** Repaired the anchor selection bug that prioritized brake onset over steering. Enforced $T_{\text{first\_ctrl}} = \min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$. Eliminated synthetic fallbacks ($T_{\text{TOR}} + 1.2\text{ s}$) in favor of NaN missingness. ~~Proved `T_stable` nominal medians are robust across post-maneuver anchors (22.18 s – 22.95 s).~~ **[AUDIT 2026-09-22: WITHDRAWN: robustness across anchors does not rescue a metric whose window extends into automation.]**

#### Phase 2B-1.4 — Hazard-Clearance Semantics Patch
- **Commit:** `1ad1951` (Current HEAD)
- **RQ Addressed:** Clearance semantics and spatial landmark definitions.
- **Method:** Empirical audit of collision trials and data dictionary verification.
- **Main Result:** Renamed purely longitudinal crossing to **$T_{\text{pass}}$** (geometric station passage), which remains valid. **[AUDIT 2026-09-22: WITHDRAWN: the "6/6 (100%) collision failure" result (the collision proxy is invalid: 12 in-lane hazard-station passages vs 6 labels, overlap 4); the "Row 44 / lane_id 2→3" description of `Time_Lane_Change` (not in the dictionary; lane numbering varies by road); and the anchor-span conclusions (built on the withdrawn `T_stable`).]**

---

## 4. ~~Completed~~ Physical-Spine Results **[AUDIT 2026-09-22: PARTIAL / MODEL-VALID]**

### 4.1 The Exact Closed-Form Recoverability Boundary
The deterministic physical spine is governed by the exact required lead-time equation derived in Branch D0:

$$\boxed{T_{\text{required}}(v_0, t_1, a_{\text{pre}}, t_2, t_3, a_{\text{max}}) = \frac{v_0}{2 a_{\text{max}}} + t_1 \left(1 - \frac{a_{\text{pre}}}{a_{\text{max}}}\right)\left(1 - \frac{a_{\text{pre}} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{\text{pre}} t_1}{v_0}\right) - \frac{a_{\text{max}} t_3^2}{24 v_0}}$$

Multiplying by initial velocity $v_0$ yields the total physical stopping distance:
$$D_{\text{stop}} = v_0 t_1 - \frac{1}{2} a_{\text{pre}} t_1^2 + v_1 t_2 + v_1 \frac{t_3}{2} - \frac{a_{\text{max}} t_3^2}{24} + \frac{v_1^2}{2 a_{\text{max}}}$$
where $v_1 = v_0 - a_{\text{pre}} t_1$ is the vehicle speed at the completion of the human reaction delay.

### 4.2 Underlying Physical Assumptions
1. **Longitudinal Kinematics:** Motion is purely one-dimensional along a flat road.
2. **Step Driver Command:** Human driver applies a step emergency demand ($u_{\text{brake}} = 1.0$) after reaction latency $t_1$.
3. **Four-Phase Deceleration Profile:**
   - *Phase 1 ($t \in [0, t_1)$):* Pre-effective deceleration $a(t) = a_{\text{pre}}$ (constant powertrain drag or regenerative braking under Policy W1).
   - *Phase 2 ($t \in [t_1, t_1 + t_2)$):* Actuator dead-time delay where $a(t) = a_{\text{pre}}$.
   - *Phase 3 ($t \in [t_1 + t_2, t_1 + t_2 + t_3)$):* Linear deceleration ramp from $a_{\text{pre}}$ to $a_{\text{max}}$ with constant jerk $j = (a_{\text{max}} - a_{\text{pre}}) / t_3$.
   - *Phase 4 ($t \ge t_1 + t_2 + t_3$):* Saturated maximum braking $a(t) = a_{\text{max}}$ until standstill ($v = 0$).
4. **Stationary In-Lane Obstacle:** The threat is a zero-velocity obstacle at initial clearance distance $d_0$.

### 4.3 Key Analytical Findings & Derivative Properties
- **Coordinate Monotonicity (Proved in E0):**  
  Across the admissible domain $\Omega = \{v_0 \in [10, 35]\text{ m/s}, t_1 \in [0.7, 1.5]\text{ s}, a_{\text{pre}} \in [0, 3]\text{ m/s}^2, t_2 \in [0.05, 0.17]\text{ s}, t_3 \in [0.15, 0.45]\text{ s}, a_{\text{max}} \in [3.5, 9.0]\text{ m/s}^2\}$:
  $$\frac{\partial T_{\text{required}}}{\partial v_0} > 0, \quad \frac{\partial T_{\text{required}}}{\partial t_1} > 0, \quad \frac{\partial T_{\text{required}}}{\partial t_2} > 0, \quad \frac{\partial T_{\text{required}}}{\partial t_3} > 0$$
  $$\frac{\partial T_{\text{required}}}{\partial a_{\text{pre}}} < 0, \quad \frac{\partial T_{\text{required}}}{\partial a_{\text{max}}} < 0$$
  The gradient is strictly signed everywhere; there are zero interior extrema.
- **Exact Marginal Sensitivity to $a_{\text{pre}}$ (NUM-08):**  
  $$\frac{\partial T_{\text{required}}}{\partial a_{\text{pre}}} = -\frac{t_1}{v_0}\left[\frac{v_1}{a_{\text{max}}} + \frac{t_1}{2} + t_2 + \frac{t_3}{2}\right]$$
  At nominal cruising conditions ($v_0 = 20\text{ m/s}, t_1 = 1.0\text{ s}, a_{\text{pre}} = 0, t_2 = 0.10\text{ s}, t_3 = 0.30\text{ s}, a_{\text{max}} = 8.5\text{ m/s}^2$):
  $$\left.\frac{\partial T_{\text{required}}}{\partial a_{\text{pre}}}\right|_{\text{nom}} = -0.155\text{ s / (m/s}^2) \quad (\text{Domain span: } [-0.422, -0.083])$$
- **Non-Additive Cross-Term Interaction (NUM-03):**  
  In Branch A1, the mixed partial derivative between pre-effective deceleration and build-up ramp under Policy W1 was derived as:
  $$\frac{\partial^2 D_{\text{stop}}}{\partial a_{\text{pre}} \partial t_3} = -\frac{t_1}{2} \ne 0 \implies \frac{\partial^2 T_{\text{required}}}{\partial a_{\text{pre}} \partial t_3} = -\frac{t_1}{2 v_0} \ne 0$$
  This proved that vehicle response architecture and handover policy interact non-trivially.
- **Normalized Elasticity Hierarchy (NUM-06):**  
  At nominal conditions, normalized elasticities ($S_x = \frac{x}{T} \frac{\partial T}{\partial x}$) rank:
  $$S_{v_0} (+0.58) > S_{a_{\text{max}}} (-0.45) > S_{t_1} (+0.31) > S_{a_{\text{pre}}} (-0.13) > S_{t_3} (+0.06) > S_{t_2} (+0.04)$$
  Initial speed and maximum friction capability dominate global sensitivity, while actuator lag and ramp time are secondary.
- **Markov State Mediation (Proved in B0):**  
  Given the state at TOR $(x_{\text{TOR}}, v_{\text{TOR}})$ and post-TOR parameters, pre-TOR acceleration history has identically zero independent effect on post-TOR stopping distance.

---

## 5. Novelty Audit & Prior-Art Corrections (G0 / G0.1)

### 5.1 High-Threat Prior Art Analysis
During the G0.1 audit, major prior work was evaluated to prevent overclaiming:

1. **Papadimitriou et al. (2024, *Traffic Safety Research*, DOI: 10.55329/fkix6369):**  
   - *What they established:* Argued that conventional Takeover Time ($TOT$) is insufficient because it omits physical maneuver execution time. Introduced Time to Control ($TC = TOT + t_{\text{action}}$) and Safe Time Budget ($STB$).
   - *Impact on this project:* Completely eliminates any claim that this project is the "first" to propose that takeover evaluation must include maneuver execution time or state-dependent stopping requirements.
2. **Eclipse SUMO / EU H2020 TransAID (2018–2026):**  
   - *What they established:* Implemented dynamic speed-dependent TOR triggering in an open-source microscopic simulation platform:
     $$\text{Threshold} = (\text{dynamicToCThreshold} \times v) + \frac{v^2}{2 a_{\text{MRM}}}$$
   - *Impact on this project:* Establishes that point-mass speed-dependent stopping distance has been standard engineering practice in simulation since at least 2018.

### 5.2 Algebraic Reduction to Classical Point-Mass Model
When setting authority-transition deceleration transients to zero:
$$a_{\text{pre}} = 0, \quad t_2 = 0, \quad t_3 = 0$$
our governing equation reduces exactly to:
$$T_{\text{required}} = t_1 + \frac{v_0}{2 a_{\text{max}}} \iff D_{\text{stop}} = v_0 t_1 + \frac{v_0^2}{2 a_{\text{max}}}$$
This algebraically recovers the classical point-mass stopping model and the SUMO TransAID triggering threshold.

### 5.3 Novelty Reclassification & Residual Contribution
Following G0.1, the scientific contribution was formally reclassified:
- **Problem Framing:** **`N1`** (Rigorous analytical extension of known engineering concepts).
- **Model Formulation:** ~~`N2` (Distinct closed-form integration of authority-transition transients).~~ **[AUDIT 2026-09-22: withdrawn; prior-art-compatible mechanics]**
- **Analytical Derivation:** ~~`N2` (Exact closed-form solution incorporating $a_{\text{pre}}, t_2, t_3$).~~ **[AUDIT 2026-09-22: withdrawn; standard kinematics]**
- **Methodological Epistemics:** **`N1`** (Exemplary negative-result reporting and claim-ladder discipline).
- ~~**Residual Distinct Contribution:** The project provides the first exact closed-form analytical stopping boundary that integrates pre-effective deceleration ($a_{\text{pre}}$) during reaction latency with mechanical actuator dead time ($t_2$) and deceleration build-up ramps ($t_3$), proving that pre-effective powertrain deceleration exerts a bounded effect size (ΔT ≈ 0.44 s) that is 3.7× larger than mechanical actuator delay (ΔT ≈ 0.12 s).~~
  **[AUDIT 2026-09-22: WITHDRAWN. "First exact closed form" is unsupportable. Reaction + response delay + half build-up (`t1 + t2 + t3/2`) is standard accident-reconstruction stopping-distance practice (Ansprechzeit, Schwellzeit), and `−a·t3²/24` follows directly from a linear ramp. The `a_pre` term is a piecewise-constant extension; it is kept as a model parameter / candidate coupling term but is not standalone novelty. The 3.7× ratio depends on the chosen parameter ranges. Remaining novelty candidate (NOT established): causal separation and later coupling of vehicle, human, transition and hazard layers; a recoverability framework; the possible role of pre-control vehicle response within it.]**
- **Permanent Language Constraint:** All hyperbolic terminology ("first", "unique", "unprecedented", "paradigm shift") is permanently prohibited.

---

## 6. Original Scope Reconciliation (Branch H0)

The H0 audit (`docs/ORIGINAL_SCOPE_RECONCILIATION.md`) reconciled the original Phase 0 charter against the established repository.

**[AUDIT 2026-09-22: The status column below is superseded. Corrected: RQ1 → NOT STARTED / GATED; RQ2 → PARTIAL (saturated braking only); RQ3 → RESTRUCTURE (four sub-questions; direct vehicle-response familiarity not identifiable from verified public data checked); RQ4 → NOT STARTED beyond the W0/W1 abstraction; stabilisation and corrections → `T_stable` WITHDRAWN, correction counts INVALID AS COMPUTED; validation → no empirical validation of the boundary. See `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`.]**

| Research Question / Component | Status | Evidence Produced | What Remains Unanswered |
| :--- | :---: | :--- | :--- |
| **RQ1: Joint Recoverability Envelope** | ~~PARTIALLY ANSWERED~~ **NOT STARTED / GATED** | Exact closed-form $T_{\text{required}}$; coordinate monotonicity; parameter closure table. | Probabilistic envelope $P(\text{safe fallback} \mid \text{state})$; stochastic human reaction distributions. |
| **RQ2: Vehicle Response Architecture** | ~~ANSWERED WITHIN CURRENT MODEL~~ **PARTIAL / MODEL-VALID** | Exact derivative $\frac{\partial T}{\partial a_{\text{pre}}} = -0.155\text{ s/(m/s}^2)$; bounded effect sizes $\Delta T(a_{\text{pre}}) \approx 0.44\text{ s}$, $\Delta T(t_2) \approx 0.12\text{ s}$. | Human behavioral adaptation to different vehicle deceleration profiles; physical pressure telemetry. |
| **RQ3: Driver Familiarity Mismatch ($M$)** | **DEFERRED — DATA REQUIRED** | Analytical proof that $\frac{\partial a_{\text{ego}}}{\partial M} = 0$ under panic step; forensic audit proving absence in public data. | Impact of familiarity priors on modulated pedal braking, hesitation, or steering swerve. |
| **RQ4: Handover & Withdrawal Policy** | ~~PARTIALLY ANSWERED~~ **NOT STARTED beyond W0/W1** | Proof of non-trivial interaction $\frac{\partial^2 D_{\text{stop}}}{\partial a_{\text{pre}} \partial t_3} = -\frac{t_1}{2}$; W0 vs W1 factorial sweep; D0 integration. | Staged/blended withdrawal (W2); behavioral adaptation to withdrawal timing. |
| **High Acceleration Risk Escalation** | **ANALYTICALLY RESOLVED** | Mathematical proof that pre-TOR acceleration history has zero independent effect once $(x_{\text{TOR}}, v_{\text{TOR}})$ is fixed. | Socio-technical speed choice and risk compensation prior to takeover. |
| **Outcomes: $T_{\text{stable}}$ and $N_{\text{correction}}$** | **ADDRESSED IN PHASE 2B** | Empirical extraction across 513 trials of D003; McLean & Hoffmann hysteresis reversals; anchor sensitivity. | Coupling of empirical settling metrics into closed-form vehicle physics. |
| **Lateral Avoidance Dynamics** | **OUT OF SCOPE AFTER REFINEMENT** | Scoped out in Phase 0.1 to maintain a tractable, provable 1D boundary. | Combined emergency swerving and braking safety envelopes. |
| **Validation Level** | **V1 (PARAMETER-LEVEL ONLY)** | Parameter plausibility bounded (Level 2); trajectory (Level 3) and crash outcome (Level 4) unidentifiable on open data. | Fleet-level real-world crash validation across production vehicle models. |

### Paper vs Full-Programme Distinction:
- ~~**Paper 1 (Deterministic Physical Recoverability):** READY (`P1-B`). Self-contained, analytically complete, and evidence-bounded.~~ **[AUDIT 2026-09-22: WITHDRAWN; not paper-ready.]**
- ~~**Original Full Programme:** PROGRAMME-INCOMPLETE (`H0-B`). Active in Phase 2.~~ **[AUDIT 2026-09-22: Current stage: EXPLORATORY.]**

---

## 7. Human-Data Feasibility ~~& The Phase 2A Breakthrough~~ **[AUDIT 2026-09-22: framing withdrawn; D003 has known blockers and prior owner analyses]**

### 7.1 The Critical Distinction: Generic Recovery vs Familiarity Mismatch
Prior to Phase 2A, the project conflated the absence of driver familiarity labels with the total absence of human takeover data. Phase 2A resolved this:
- **Generic Human Fallback (Level H1 & H2):** Public takeover data exist. **[AUDIT 2026-09-22: Their measurement semantics must be validated before use (`docs/OBSERVATION_LAYER.md`). For D003, stabilisation trajectories are NOT documented within the human-control window, and the dataset owners have already published takeover-time, button-time, minimum-TTC, maximum-deceleration and steering analyses.]**
- **Driver Familiarity / Mismatch (Level H3):** ~~UNAVAILABLE IN PUBLIC DATA.~~ **[AUDIT 2026-09-22: Direct EV/ICE, one-pedal or regen familiarity × takeover response was not found in the verified public data checked. Repeated-exposure learning is identifiable in D003; experience variables are associational only.]** No public dataset checked records driver prior EV/ICE ownership or evaluates cross-vehicle switching.

### 7.2 Audit of Candidate Public Datasets

| Dataset | Access | Size & Structure | Signals Present | Signals Absent / Reason Insufficient for H3 |
| :--- | :---: | :--- | :--- | :--- |
| **D001: ADAS-TO** | Gated (CC BY-NC 4.0) | 15,659 naturalistic disengagements (10–100 Hz) | Continuous steering angle, torque, $v_{\text{ego}}, a_{\text{ego}}$, radar lead tracking. | Pedal inputs are **binary flags only** (`brakePressed`); no continuous pedal force; no familiarity labels. **[AUDIT 2026-09-22: ADAS-TO (arXiv 2603.06986) spans 327 drivers and 22 vehicle brands: between-vehicle variation, not switching. The binary-pedal statement has not been re-verified against the published `carState` fields.]** |
| **D002: TD2D** | Open (Zenodo) | 50 participants, 500 cases | Physiological signals (ECG, PPG, eye tracking), scalar reaction time. | **Continuous steering, pedal, and vehicle trajectories are NOT included in the public release.** |
| **D003: TU Delft Takeover** | **Open Public (4TU)** | **57 participants, 513 trials, 20 Hz constant** | Brake (semantics unresolved), gas pedal [0:1], steering angle (rad), steering speed, $v, a$, obstacle distance, TTC. **[AUDIT 2026-09-22: `lane_gap` is unparsed (100% NaN in current loaders) and its meaning is inferred only.]** | Single simulated vehicle mapping. Repeated exposures (9 per driver, order recoverable) and self-reported driving/ADAS experience are present. |
| **D004: OpenLKA EV** | Open (GitHub) | Multi-route EV highway driving (~100 Hz) | Continuous accelerator position, speed, acceleration. | Cruising data only; no takeover requests or emergency braking events. |
| **D005: OpenLKA Acceleration** | Open (GitHub) | 12 EV models, ~10 Hz | Accelerator pedal displacement, speed, acceleration. | **Zero brake channels exist in schema**; not a takeover dataset. |

**Verdict:** **TU Delft (D003)** is the primary empirical foundation for Phase 2B. **[AUDIT 2026-09-22: Conditional on resolving `research/data_matrix/D003_KNOWN_BLOCKERS.md`.]**

---

## 8. D003 Dataset — Forensic Status & Signal Provenance

### 8.1 Experimental Design & Dataset Characteristics
- **Source:** 4TU.ResearchData (DOI: [10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB](https://doi.org/10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB)).
- **Population:** 57 valid licensed drivers.
- **Trial Structure:** Balanced 3×3 repeated-measures Latin Square design (9 trials per driver = 513 total trials):
  - *Traffic Density (3 levels):* $0\text{ veh/km}$ (open road), $10\text{ veh/km}$ (medium), $20\text{ veh/km}$ (dense traffic jam).
  - *Cognitive Workload (3 levels):* 0-back (baseline), 1-back (moderate), 2-back (high cognitive distraction).
- **Sampling Rate:** Strictly constant **20.0 Hz** ($\Delta t = 0.050\text{ s}$). ~~exactly 1,953 rows per ~97 s trial~~ **[AUDIT 2026-09-22: Row counts range 1,190–3,760 (median 1,585). 42 trials end with a row whose `time` is empty; [R1 correction:] that row is not empty but a left-shifted export-channel footer whose event values agree with the body (benign; see D003 blocker B3). `time` is Unix epoch; event values are seconds since the first row, logged about 0.1 s late.]**
- **Scenario:** Ego vehicle in automated mode encounters a stationary construction hazard blocking the cruising lane. A TOR is issued at TTC ≈ 7 s (7.04 ± 0.03 s). **[AUDIT 2026-09-22: Speed at TOR is NOT ~25 m/s throughout: it is fixed per cell and ranges 19.3–27.8 m/s. Each density × n-back cell is a distinct road segment, so hazard state is aliased with condition. Protocol (owners): take over, change lanes, hand control back to automation (`Time_Manual_Stop`). 26 trials contain multiple TOR values; 15 have no TOR column.]**

### 8.2 Direct Source Signals vs Derived Quantities
- **Direct Source Signals:**
  - `[00].VehicleUpdate-brake`: ~~Continuous brake pedal force in Newtons (N).~~ **[AUDIT 2026-09-22: Dictionary: "brake force, N"; owners' paper: "braking pedal positions". Active after handback to automation in ~76% of trials. Driver-input vs actuated/automation semantics UNRESOLVED.]**
  - `[00].VehicleUpdate-accelerator`: Continuous accelerator pedal displacement ($[0.0, 1.0]$).
  - `[00].VehicleUpdate-steeringWheelAngle`: Continuous steering wheel angle in radians.
  - `[00].VehicleUpdate-steeringWheelSpeed`: Steering wheel angular velocity in rad/s.
  - `[00].VehicleUpdate-speed.001`: Longitudinal speed in m/s.
  - `[00].VehicleUpdate-accel.001`: Longitudinal acceleration in $\text{m/s}^2$.
  - `[00].VehicleUpdate-roadInfo-laneGap.0`: ~~Lateral displacement from lane centerline in meters.~~ **[AUDIT 2026-09-22: The actual header is `"...laneGap.0,time"` and each cell is a quoted pair `"<value>,<relative time>"`. Current loaders parse it as 100% NaN. The dictionary gives no definition; "signed offset from lane centre" is an inference (bounded ±1.75 m, jumps ~3.4 m at lane changes).]**
  - `[72 (Time_Takeover_Request)].val`: Digital TOR trigger timestamp.
  - `[73 (Time_Manual_Start)].val`: Hardware button-press disengagement timestamp.
  - `[78 (Time_Lane_Change)].val`: Lane-change event ("changed to the left lane during takeover"). **[AUDIT 2026-09-22: Requires per-trial validation; one trial shows a 0.95 s inconsistency.]**
  - `[85 (Distance_to_Construction)].val`: 1D longitudinal distance to obstacle in meters.
- **Derived Quantities (Operational Metrics):**
  - $T_{\text{first\_ctrl}}$: First active driver input ($\min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$).
  - $T_{\text{effective}}$: First subsequent causal vehicle-state response satisfying $\Delta a_x \ge 0.5\text{ m/s}^2$ or $|\Delta a_y| \ge 0.3\text{ m/s}^2$.
  - $T_{\text{pass}}$: Instant $d_{\text{obstacle}} \le 0.0\text{ m}$.
  - $T_{\text{stable}}$: Multi-channel kinematic derivative settling time.
  - ~~`DERIVED_COLLISION_PROXY`: Heuristic classification based on $d_{\text{obstacle}} \le 0$ without lane change.~~ **[AUDIT 2026-09-22: WITHDRAWN: disagrees with lane occupancy at the hazard station (12 in-lane passages vs 6 labels, overlap 4).]**

---

## 9. Human Recovery Empirical Results (Phase 2B-1)

~~The empirical findings from D003 (513 trials, 498 valid TOR trials) that remain valid after all integrity audits are summarized below.~~ **[AUDIT 2026-09-22: The findings below are PRE-AUDIT ARTIFACTS, retained for traceability. None is a current finding. Brake-derived quantities depend on unresolved brake-channel semantics. Button time and takeover time replicate metrics already published by the dataset owners (arXiv 2507.22252, which used 466 takeovers). The factorial effects are descriptive and condition-associated only.]**

### 9.1 Summary of Timeline & Action Ordering ($N = 498$ valid TOR trials)

| Metric | Scientific Object | Median | IQR | Mean $\pm$ SD | Epistemic Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| $\Delta T_{\text{manual\_start}}$ | Button-press disengagement latency | **$1.650\text{ s}$** | $0.750\text{ s}$ | $1.717 \pm 0.769\text{ s}$ | **DIRECT** (Hardware flag) |
| $T_{\text{first\_ctrl}} - T_{\text{req}}$ | First active motor input (pedal or steer) | **$1.125\text{ s}$** | $0.850\text{ s}$ | $1.018 \pm 0.644\text{ s}$ | **THRESHOLD-DEPENDENT** ($15\text{N} / 0.05\text{rad}$) |
| $T_{\text{first\_brake}} - T_{\text{req}}$ | Brake pedal onset latency ($F_b > 15\text{ N}$) | **$1.200\text{ s}$** | $1.200\text{ s}$ | $4.812 \pm 10.348\text{ s}$ | **THRESHOLD-DEPENDENT** ($15\text{ N}$) |
| $T_{\text{first\_steer}} - T_{\text{req}}$ | Steering onset latency ($|\Delta \delta| > 0.05\text{ rad}$) | **$3.000\text{ s}$** | $3.437\text{ s}$ | $3.034 \pm 2.235\text{ s}$ | **THRESHOLD-DEPENDENT** ($0.05\text{ rad}$) |
| $T_{\text{first\_ctrl}} - T_{\text{man\_start}}$ | Motor input relative to button press | **$-0.650\text{ s}$** | $1.087\text{ s}$ | $-0.699 \pm 0.998\text{ s}$ | **DERIVED** (Difference of observed) |
| Causal Longitudinal Delay | $T_{\text{eff\_dec}} - T_{\text{first\_brake}}$ | **$0.050 - 0.100\text{ s}$** | $0.550\text{ s}$ | $1.429 \pm 4.834\text{ s}$ | **DERIVED** (Causally constrained) |
| Causal Lateral Delay | $T_{\text{eff\_lat}} - T_{\text{first\_steer}}$ | **$0.900\text{ s}$** | $1.950\text{ s}$ | $1.781 \pm 4.115\text{ s}$ | **DERIVED** (Causally constrained) |
| $T_{\text{pass}} - T_{\text{req}}$ | Obstacle station crossing ($d \le 0$) | **$8.950\text{ s}$** | $3.300\text{ s}$ | $10.676 \pm 7.012\text{ s}$ | **DERIVED** (Geometric crossing) |
| ~~$T_{\text{stable}} - T_{\text{req}}$~~ | ~~Control derivative stabilization~~ | ~~22.2–23.0 s~~ | — | — | **[AUDIT 2026-09-22: WITHDRAWN]** |

### 9.2 Robust Empirical Takeover Characteristics
1. **Multimodal Action Ordering:** Drivers exhibit distinct action ordering profiles:
   - **Brake-First:** $65.3\%$ of trials (nominal).
   - **Steer-First:** $32.9\%$ of trials.
   - **Simultaneous ($< 50\text{ ms}$):** $1.8\%$ of trials.
2. **Negative Handover Lag ($T_{\text{first\_ctrl}} < T_{\text{manual\_start}}$):**  
   In **$60.2\%$** of trials, active pedal braking precedes the steering-wheel disengagement button press (median lead of **$-0.650\text{ s}$**). Drivers physically hit the brake pedal first and click the button during or after foot movement.
3. **Non-Step Braking Dynamics:**  
   Drivers do not apply step deceleration. Brake force rises with a median rate of **$91.73\text{ N/s}$** (mean: $143.99\text{ N/s}$), reaching initial peak force ($53.08\text{ N}$) after a median rise time of **$0.750\text{ s}$**.
4. **Closed-Loop Oscillatory Cycles:** **[AUDIT 2026-09-22: INVALID AS COMPUTED: the brake-extrema and reapplication windows run over the full post-TOR record, including automation after `Time_Manual_Stop` (median brake peaks 3 over full record vs 1 within the manual window). The "13 reversals" figure also includes automation. The acute 8 s steering window lies within manual control in 99% of trials but begins before the button press.]**  
   Takeover recovery is inherently closed-loop. Across the manual takeover phase, drivers exhibit:
   - Median **3.0 brake extrema**.
   - Median **2.0 brake reapplications** ($68.3\%$ of trials exhibit $\ge 1$ reapplication).
   - Median **2.0 acute steering reversals** ($13.0$ across the entire 60s run) under McLean & Hoffmann ($2.0^\circ$) hysteresis filtering.
5. **Incomplete Stop (Evasive Maneuver):**  
   Drivers do not brake to a standstill. Speed drops by a median of only **$8.31\text{ m/s}$** from an initial $25.04\text{ m/s}$, reaching a minimum post-TOR speed of median **$16.95\text{ m/s}$**. In 499 of 513 trials, drivers execute an evasive lane change.
6. **Repeated-Measures Factorial Effects (95% CIs and Holm-Adjusted $p$-values):** **[AUDIT 2026-09-22: CAUSAL LANGUAGE WITHDRAWN. Each cell is a distinct road segment with its own fixed speed (19.3–27.8 m/s), distance, starting lane and pre-TOR automation duration; density 20 / 1-back also carries the multi-TOR anomaly. The contrasts below are descriptive, condition-associated differences, not workload or density effects. The mechanism "because escape gaps in adjacent lanes are blocked" is untested.]**
   - *Cognitive Workload (2-back vs 0-back):* Delays button press latency by $+0.400\text{ s}$ ($95\%\text{ CI: } [0.264, 0.536]$, $p_{\text{adj}} = 1.1 \times 10^{-6}$); increases brake-first prevalence from $33.3\%$ to $84.8\%$ ($+51.5\%$, $p_{\text{adj}} = 9.6 \times 10^{-24}$).
   - *Traffic Density (20 vs 0 veh/km):* Nearly triples mean peak brake force ($+109.6\text{ N}$, $95\%\text{ CI: } [96.0, 123.3]$, $p_{\text{adj}} = 4.8 \times 10^{-31}$) because escape gaps in adjacent lanes are blocked.

---

## 10. Important Findings That Were Later Corrected

This section documents all major scientific and methodological corrections made across the project.

```
CORRECTION TIMELINE:
─────────────────────────────────────────────────────────────────────────────
Phase 0.2 / 0.4:
  • Retired unconstrained "brake gain" curves & W2 staged withdrawal.
Branch B0:
  • Proved pre-TOR acceleration history has ZERO independent effect (Markov mediation).
Branch C0:
  • Proved driver familiarity mismatch M is causally severed under panic braking.
Branch G0.1:
  • Downgraded novelty claims after discovering Papadimitriou et al. (2024) & SUMO.
Branch G0.2:
  • Corrected dT/da_pre sensitivity from ~0.83 to -0.155 s/(m/s^2).
  • Replaced "order-of-magnitude dominance" with true ~3.7x bounded effect ratio.
Phase 2A:
  • Corrected belief that public human takeover data was unavailable (unlocked D003). [AUDIT 2026-09-22: availability ≠ validity; see D003 blockers]
Phase 2B-1.1:
  • Repaired 196 causal violations where T_effective < T_first_ctrl.
  • Replaced raw zero-crossing reversals (70.5) with McLean & Hoffmann hysteresis (2.0).
  • Relabeled 6 collision outcomes as DERIVED_COLLISION_PROXY.
Phase 2B-1.2:
  • Clarified T_first_ctrl is human motor input, NOT plant response.
  • Excised "hydraulic" terminology from generic Phase 1 actuator delay (t_2).
Phase 2B-1.3:
  • Fixed T_stable anchor bug that selected brake onset over min(brake, steer).
Phase 2B-1.4:
  • Replaced T_clear with T_pass (6/6 collision trials falsely triggered old condition).
  • Declared T_safe_clear NOT IDENTIFIABLE from D003 telemetry.
  • Clarified Time_Lane_Change is discrete simulator lane transition, not completion.
─────────────────────────────────────────────────────────────────────────────
```

### Correction Inventory:

#### A. Availability of Public Human Continuous Takeover Data
- **Old Claim:** Human experimental data is unavailable in public repositories; Phase 2 cannot proceed without new human participant recruitment.
- **Why Wrong:** Conflated the absence of driver familiarity labels (EV vs ICE experience) with the absence of generic human takeover trajectories.
- **Corrected Claim:** Public continuous human takeover data is abundantly available (TU Delft D003: 513 trials at 20 Hz; ADAS-TO D001: 15,659 disengagements).
- **Current Status:** Phase 2 active; participant recruitment canceled. **[AUDIT 2026-09-22: Availability ≠ validity. D003 carries documented blockers, and its owners have published prior analyses that must be cited.]**

#### B. Conflation of $T_{\text{request}}$ with $T_{\text{authority}}$
- **Old Claim:** Handover authority transfer occurs instantaneously at the moment of human physical input.
- **Why Wrong:** Authority transfer is a system-level policy event governed by the disengagement logic (W0 vs W1), whereas human input is a motor response.
- **Corrected Claim:** $T_{\text{authority}}$ represents the moment automation control is withdrawn, which equals $T_{\text{request}}$ under Policy W1, but extends to $T_{\text{first\_ctrl}}$ under Policy W0.
- **Current Status:** Formalized in `docs/CAUSAL_MODEL.md` and the Measurement Ledger.

#### C. Promotion of `Time_Manual_Start` to Physical Authority Transfer
- **Old Claim:** The logged signal `Time_Manual_Start` marks when the human takes physical control.
- **Why Wrong:** `Time_Manual_Start` in D003 records a button press on the steering wheel spoke. In $60.2\%$ of trials, drivers press the brake pedal *before* pressing this button (median lead of $-0.65\text{ s}$).
- **Corrected Claim:** `Time_Manual_Start` is an operational button-press flag ($T_{\text{manual\_start}}$); true initial human control is $T_{\text{first\_ctrl}} = \min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$.
- **Current Status:** ~~Permanently corrected in Phase 2B-1.2.~~ **[AUDIT 2026-09-22: UNRESOLVED. The owners describe the button as "enabling manual inputs"; braking before it is physically effective, but whether the brake channel reflects driver input or automation braking is unresolved.]**

#### D. Unconstrained Causal Violations in $T_{\text{effective}}$ Detection
- **Old Claim:** $T_{\text{effective}}$ can be detected by running an acceleration threshold detector forward from $T_{\text{request}}$.
- **Why Wrong:** In $196 / 498$ trials ($39.36\%$), the detector triggered *before* the driver touched the pedals, caused by automated throttle cut and pre-takeover road curvature.
- **Corrected Claim:** $T_{\text{effective}}$ must be causally constrained: $T_{\text{effective\_channel}} \ge T_{\text{first\_channel}}$. This eliminates all causal violations and reveals true actuator delay of $0.05 - 0.10\text{ s}$.
- **Current Status:** Enforced in code (`src/experiments/h1_sensitivity_analysis.py`).

#### E. Inflation of Steering Reversals by Raw Zero-Crossings
- **Old Claim:** Human drivers exhibit an average of $70.5$ steering reversals during takeover recovery.
- **Why Wrong:** Counting raw zero-crossings of steering wheel velocity treated every sensor noise jitter and neuromuscular tremor as a macroscopic steering reversal.
- **Corrected Claim:** Applying the McLean & Hoffmann (1975) amplitude-hysteresis detector ($2.0^\circ$ gap) reveals median **2.0 reversals in the acute 8-second maneuver** and **13.0 reversals across the full 60-second record**.
- **Current Status:** Standardized in Phase 2B-1.1.

#### F. Anchor Selection Bug in $T_{\text{stable}}$ Sensitivity Analysis
- **Old Claim:** Stabilization anchor selection evaluated brake onset whenever brake data was present: `t_ref = t_brake if available else t_steer`.
- **Why Wrong:** Contradicted the project definition $T_{\text{first\_ctrl}} = \min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$, causing steer-first trials ($32.9\%$) to anchor search windows to secondary brake presses seconds later.
- **Corrected Claim:** Search start strictly enforces $T_{\text{first\_ctrl}} = \min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$.
- **Current Status:** Fixed in Phase 2B-1.3 (`tests/test_h1_sensitivity_and_audit.py`).

#### G. Treating Obstacle Longitudinal Passage as Safe Clearance ($T_{\text{clear}}$)
- **Old Claim:** The condition `distance_to_obstacle <= 0` and `speed > 10 m/s` marks safe obstacle clearance ($T_{\text{clear}}$).
- **Why Wrong:** Crashing vehicles also cross the obstacle's longitudinal coordinate. In **6 out of 6 (100%)** collision failure trials, this condition falsely declared that the vehicle had "cleared" the hazard.
- **Corrected Claim:** Renamed to **$T_{\text{pass}}$** (geometric longitudinal station passage). Declared **$T_{\text{safe\_clear}}$ NOT IDENTIFIABLE** because D003 lacks lateral obstacle coordinates.
- **Current Status:** Fixed in Phase 2B-1.4. **[AUDIT 2026-09-22: `T_pass` retained. The "6 out of 6 collision trials" evidence is withdrawn with the collision proxy.]**

#### H. Claiming D003 Directly Validates Physical/Hydraulic Brake Delay
- **Old Claim:** D003 telemetry validates physical vehicle hydraulic brake delay ($t_2$).
- **Why Wrong:** D003 is a fixed-base driving simulator running a software vehicle dynamics model. Software state updates cannot empirically validate physical automotive hydraulic pressure transport.
- **Corrected Claim:** D003 provides parameter-level consistency (V1) for simulator response, not hardware-level hydraulic validation.
- **Current Status:** Scoped in Phase 2B-1.2.

#### I. Claiming D003 Telemetry "Dictates" a Specific 4-Phase or PD Controller
- **Old Claim:** Empirical data proves that human takeover behavior follows a specific 4-phase controller structure.
- **Why Wrong:** Human behavior is continuous and stochastic. While empirical trajectories exhibit phases (reaction, rise, correction, cruise), fitting any specific mathematical model (PD, optimal preview, neuromorphic) is a modeling choice, not an empirical given.
- **Corrected Claim:** Empirical data establishes closed-loop recovery characteristics; controller structure identification is a hypothesis to be evaluated in Phase 2B-2.
- **Current Status:** Guardrail enforced for Phase 2B-2.

#### J. Erroneous Sensitivity Derivative $\sim 0.83\text{ s/(m/s}^2)$
- **Old Claim:** Required lead time decreases by $\sim 0.83\text{ s}$ per $\text{m/s}^2$ of pre-effective deceleration.
- **Why Wrong:** Typographical error or misinterpretation of simulation grid points.
- **Corrected Claim:** The exact nominal derivative is $\left.\frac{\partial T}{\partial a_{\text{pre}}}\right|_{\text{nom}} = -0.155\text{ s / (m/s}^2)$, with a global domain span of $[-0.422, -0.083]\text{ s / (m/s}^2)$.
- **Current Status:** Frozen in `docs/QUANTITATIVE_CLAIM_LEDGER.md` (NUM-08).

---

## 11. Operational Measurement Ledger Summary

From `experiments/H_human_internal_model/H1_OPERATIONAL_MEASUREMENT_LEDGER.md`. **[AUDIT 2026-09-22: Rows for `Time_Lane_Change` (lane_id 2→3), `T_stable`, `DERIVED_COLLISION_PROXY` and brake reapplication are superseded; see the ledger's own audit notice and `docs/OBSERVATION_LAYER.md`.]**

| Quantity | Conceptual Meaning | Detector / Formula | Threshold & Persistence | Epistemic Status & Allowed Wording |
| :--- | :--- | :--- | :--- | :--- |
| **$T_{\text{request}}$** | Instant TOR alarm sounds | `[72 (Time_Takeover_Request)].val` | Digital flag transition | Direct source event. Allowed: "Takeover request timestamp". |
| **$T_{\text{manual\_start}}$** | Disengagement button click | `[73 (Time_Manual_Start)].val` | Digital flag transition | Direct hardware event. Must NOT be called "authority transfer". |
| **$T_{\text{authority}}$** | Authority transfer | Anchored to $T_{\text{req}}$ (W1) or $T_{\text{first}}$ (W0) | Policy definition | Derived system state. |
| **$T_{\text{first\_brake}}$** | Human pedal braking onset | $\inf \{ t \ge T_{\text{req}} \mid F_b(t) > 15\text{ N} \}$ | $15.0\text{ N}$, 1 sample ($50\text{ ms}$) | Threshold-dependent input. Allowed: "Brake input onset". |
| **$T_{\text{first\_steer}}$** | Human steering input onset | $\inf \{ t \ge T_{\text{req}} \mid \|\Delta \delta_{\text{sw}}(t)\| > 0.05\text{ rad} \}$ | $0.05\text{ rad}$ ($2.86^\circ$), 1 sample | Threshold-dependent input. Allowed: "Steering input onset". |
| **$T_{\text{first\_ctrl}}$** | First detected human action | $\min(T_{\text{first\_brake}}, T_{\text{first\_steer}})$ | Minimum of active channels | Derived human motor event. Must NOT be called "plant response". |
| **$T_{\text{effective\_dec}}$** | Causal vehicle deceleration | $\inf \{ t \ge T_{\text{first\_brake}} \mid a_x(t) \le a_{\text{ref}} - 0.5 \}$ | $\Delta a_x \ge 0.5\text{ m/s}^2$, $100\text{ ms}$ | Causally constrained kinematic event. |
| **$T_{\text{effective\_lat}}$** | Causal vehicle lateral accel | $\inf \{ t \ge T_{\text{first\_steer}} \mid \|\Delta a_y(t)\| \ge 0.3 \}$ | $\Delta a_y \ge 0.3\text{ m/s}^2$, $100\text{ ms}$ | Causally constrained kinematic event. |
| **$\text{Time\_Lane\_Change}$**| Discrete lane crossing | `[78 (Time_Lane_Change)].val` | Discrete `lane_id` flip ($2 \to 3$) | Discrete simulator event. Must NOT be called "maneuver completion". |
| **$T_{\text{pass}}$** | Obstacle station crossing | $\min \{ t \ge T_{\text{req}} \mid d_{\text{obs}}(t) \le 0.0\text{ m} \}$ | $d \le 0.0\text{ m}$, 1 sample | Geometric longitudinal landmark. Must NOT be called "safe clearance". |
| **$T_{\text{safe\_clear}}$** | Safe lateral clearance | **NOT IDENTIFIABLE** | No lateral obstacle bounds | **UNIDENTIFIABLE.** Prohibited from quantitative claims. |
| **$T_{\text{stable}}$** | Trajectory control settling | $\|\dot{\delta}\| \le 0.05 \land \|\dot{F}_b\| \le 20$ sustained | $1.5\text{ s}$ persistence ($30$ samples) | Derived settling metric. Operational quantity, not physiological constant. |
| **`DERIVED_COLLISION_PROXY`**| Crash outcome classification| $d_{\text{obs}} \le 0 \land \text{no lane change}$ | Heuristic kinematic boundary | Proxy outcome. 6 trials classified ($1.17\%$). |
| **Steering Reversal** | Corrective steering cycle | McLean & Hoffmann (1975) hysteresis | $2.0^\circ$ ($0.035\text{ rad}$) gap, $2\text{ Hz}$ filter | Signal-processed behavioral metric. |
| **Brake Reapplication** | Secondary brake cycle | Local minimum $\to$ rise $\ge 15\text{ N}$ | $15\text{ N}$ re-rise, $100\text{ ms}$ separation | Signal-processed behavioral metric. |

---

## 12. ~~$T_{\text{stable}}$ Final Post-Audit Result~~ **[AUDIT 2026-09-22: WITHDRAWN]**

**[AUDIT 2026-09-22: The entire section below is withdrawn as a human-stabilisation result. `Time_Manual_Stop` marks the driver pressing the switch to return to **automated** mode (data dictionary; owners' protocol). Median `Manual_Stop − TOR` ≈ 18.9 s (IQR 15.2–24.1 s); nominal `T_stable` median ≈ 22.47 s; about **81%** of nominal `T_stable` values occur after `Time_Manual_Stop`; the detector's condition is met in ~90% of pre-TOR automation samples; restricted to the human-control window, only about **18%** of trials settle. "100% settled" and "0% censored" are artifacts of an observation window that extends into automation. Any replacement must be time-to-event data within the human-control window, with handback as a competing event.]**

### 12.1 Operational Detector & Invariant Properties
Stabilization time is evaluated across the 498 valid TOR trials using candidate operational criteria:
- **Detector Form:**
  $$T_{\text{stable}} = \min \{ t \ge t_{\text{anchor}} \mid |\dot{\delta}_{\text{sw}}(\tau)| \le \omega_{\text{th}} \;\land\; |\dot{F}_{\text{brake}}(\tau)| \le r_{\text{th}} \quad \forall \tau \in [t, t + \tau_p] \}$$
- **Nominal Thresholds:** Steering speed $\omega_{\text{th}} = 0.05\text{ rad/s}$ ($2.86^\circ/\text{s}$), brake rate $r_{\text{th}} = 20.0\text{ N/s}$, persistence window $\tau_p = 1.5\text{ s}$ (30 samples at 20 Hz).
- **Settled Fraction:** Strictly **$100.00\%$** across all 498 trials.
- **Right-Censoring:** Strictly **$0.00\%$** within $3\text{ s}$ of record termination.

### 12.2 Search-Anchor Sensitivity & Distinct Subset Spans
Audited across five candidate operational search anchors:

| Search Anchor Condition | Eligible Trials | Settled Fraction | Median $T_{\text{stable}}$ (s post-TOR) | IQR (s) | Mean (s) | Censored ($\le 3\text{s}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$T_{\text{first}} + 1.0\text{ s}$** | 498 | 100.0% | **$22.18\text{ s}$** | $7.89\text{ s}$ | $23.58\text{ s}$ | 0.00% |
| **$T_{\text{first}} + 2.0\text{ s}$** (Nominal) | 498 | 100.0% | **$22.47\text{ s}$** | $7.79\text{ s}$ | $24.39\text{ s}$ | 0.00% |
| **$T_{\text{first}} + 3.0\text{ s}$** | 498 | 100.0% | **$22.55\text{ s}$** | $7.79\text{ s}$ | $24.46\text{ s}$ | 0.00% |
| **$\text{Time\_Lane\_Change}$** | 484 | 100.0% | **$22.55\text{ s}$** | $7.45\text{ s}$ | $24.42\text{ s}$ | 0.00% |
| **$T_{\text{pass}}$ (Obstacle Station)** | 498 | 100.0% | **$22.95\text{ s}$** | $7.51\text{ s}$ | $24.97\text{ s}$ | 0.00% |

#### Anchor Span Disambiguation:
- **Subset A ($T_{\text{first}} + 2.0\text{ s}$, $T_{\text{first}} + 3.0\text{ s}$, $\text{Time\_Lane\_Change}$):**  
  $$\text{Span} = 22.55\text{ s} - 22.47\text{ s} = \mathbf{0.08\text{ s}} \quad (80\text{ milliseconds})$$
  Across all active maneuver entry points, settling time is invariant within 80 ms.
- **Subset B (Subset A $+ T_{\text{pass}}$):**  
  $$\text{Span} = 22.95\text{ s} - 22.47\text{ s} = \mathbf{0.48\text{ s}}$$
- **Complete 5-Anchor Set ($T_{\text{first}} + 1.0\text{ s}$ through $T_{\text{pass}}$):**  
  $$\text{Span} = 22.95\text{ s} - 22.18\text{ s} = \mathbf{0.78\text{ s}}$$

### 12.3 Epistemic Status: Operational Quantity vs Physiological Constant
$T_{\text{stable}}$ is **an operational engineering metric**, NOT a natural physiological constant. It is moderately sensitive to the required persistence duration ($19.4\text{ s}$ at $\tau_p = 1.0\text{ s}$; $24.2\text{ s}$ at $\tau_p = 2.0\text{ s}$). However, the conclusion that post-takeover stabilization requires $\approx 22 - 23\text{ s}$ is **completely robust across all candidate search anchors**.

---

## 13. Current Scientific Gates

### 13.1 Human Branch Gate: H1-B **[AUDIT 2026-09-22: superseded by PARTIAL / RESTRUCTURE; items 1–4 under "permits" below are not established pending `docs/OBSERVATION_LAYER.md` validation]**
- **Gate Formulation:**  
  $$\mathbf{H1\text{-}B:}\quad \text{\textbf{CLOSED-LOOP STRUCTURE IDENTIFIABLE, BUT EVENT / STABILISATION DEFINITIONS REMAIN PARTIALLY SENSITIVE}}$$
- **What H1-B Permits Scientifically:**
  1. Concluding that human takeover recovery is multimodal, oscillatory, and closed-loop.
  2. Rejecting one-shot open-loop step-braking as an empirically complete representation of human drivers.
  3. Fitting a minimal closed-loop controller (Phase 2B-2) to empirical input-output trajectories.
  4. Reporting scenario-level repeated-measures modulations (workload delays button press; density triples brake force).
- **What H1-B PROHIBITS Scientifically:**
  1. Claiming $T_{\text{stable}} \approx 22.5\text{ s}$ is a unique, threshold-invariant physiological constant.
  2. Claiming safe clearance was achieved based on $T_{\text{pass}}$.
  3. Claiming D003 validates physical automotive hydraulic response.
  4. Asserting a specific four-phase controller without formal model comparison.

### 13.2 Driver Familiarity / Mismatch Gate: M0-C **[AUDIT 2026-09-22: narrowed: direct vehicle-response familiarity × takeover response is not identifiable from verified public data checked; repeated-exposure learning is identifiable in D003; experience is associational only]**
- **Gate Formulation:**  
  $$\mathbf{M0\text{-}C:}\quad \text{\textbf{NOT IDENTIFIABLE FROM CURRENT PUBLIC DATA}}$$
- **Scientific Meaning:** No public open dataset records driver vehicle-familiarity history or cross-vehicle switching. Mismatch $M$ is deferred to future human-in-the-loop experimental trials.

---

## 14. Handover & Withdrawal Policy Status (W0, W1, W2)

1. **W0 (Cruise Maintenance):** Automation maintains set cruising speed until active driver input. Fully integrated into A0 and the baseline boundary.
2. **W1 (Immediate Propulsion Cut):** Automation cuts drive torque at TOR, permitting pre-effective deceleration $a_{\text{pre}}$. Fully derived and integrated into D0.
3. **Causal Equivalence:** The semantic labels "W0" and "W1" have **zero independent causal power** in the physical model beyond their induced vehicle acceleration trajectory $a(t)$.
4. **W2 (Staged / Blended Withdrawal):** Removed by design in Phase 0.4 (`docs/CAUSAL_MODEL.md`) because blending curves introduce unevidenced free parameters.
5. **[AUDIT 2026-09-22: W0/W1/W2 are not original charter RQs; the labels first appear in Phase 0.4 (`bc21fbc`). The transition layer (continued automation support, shared control, MRM, time budget) is NOT STARTED beyond this abstraction, and the TOR budget has never been varied empirically. Regulated L3 systems (UN Regulation No. 157, ALKS) keep operating during a transition demand and must be able to perform an MRM, so W1 is a counterfactual, not a representative regulated policy.]**

---

## 15. Risk-State Escalation Status (B0)

1. **The Markov Mediation Result:** Pre-TOR acceleration history $a(t)$ has zero independent effect on post-TOR stopping distance once the state $(x_{\text{TOR}}, v_{\text{TOR}})$ is fixed.
2. **Strict Governing Assumptions:**
   - Vehicle kinematics are deterministic and Markovian.
   - Post-TOR braking capability $a_{\text{max}}$ is unconditioned on prior thermal/actuator history.
   - Driver reaction latency $t_1$ is independent of pre-TOR acceleration.
3. **Guardrail:** Do not generalize B0 beyond these deterministic physical assumptions.

---

## 16. Validation & Epistemic Hierarchy

The project adheres to a strict six-level epistemic validation hierarchy:

```
Level 0: Conceptual / Speculative Hypothesis
   │
Level 1: Analytical Closed-Form Derivation (TYPE 1) ────────── [PASSED: Exact Form Derived]
   │
Level 2: Parameter-Level Empirical Grounding (TYPE 2 / V1) ──── [PASSED: Literature Bounded]
   │
Level 3: Continuous Trajectory Matching (V2) ────────────────── [NOT STARTED — AUDIT 2026-09-22: D003 samples a non-critical 7 s regime with an unparameterised simulator vehicle]
   │
Level 4: Crash Outcome Statistical Validation (V3) ──────────── [BLOCKED: Open Crash Data Unavailable]
   │
Level 5: Fleet-Level Real-World Generalization (V4) ─────────── [UNREACHABLE on Open Data]
```

- **Current Repository Status:** **Level 2 / V1 (Parameter-Level Consistency Only)**.
- **Prohibited Overclaim:** The model must **never** be described as "real-world validated" or "crash-predictive."

---

## 17. Unresolved Problems & Technical Blockers

| Unresolved Problem | Scientific Reason Unresolved | Method / Evidence Required | Blocks Phase 2B-2? |
| :--- | :--- | :--- | :---: |
| **Driver Familiarity Mismatch ($M$)** | Public datasets do not record driver familiarity history (M0-C). | Human-in-the-loop simulator study with controlled EV/ICE pre-exposure. | **NO** (Deferred) |
| **Minimal Human Model Identification** | ~~Empirical recovery established in H1-B~~ **[AUDIT 2026-09-22: Not established; observation semantics unresolved]**; mathematical model class unselected. | Phase 2B-2 model-class comparison (PID vs Preview vs Neuromorphic). | ~~CURRENT FOCUS~~ **DEFERRED** |
| **Human $\times$ Vehicle Dynamic Coupling** | Human empirical model not yet coupled to physical vehicle braking equations. | Couple Phase 2B-2 identified controller to Phase 1 longitudinal physics. | **YES** (Follows 2B-2) |
| **Probabilistic Safety Envelope** | Joint probability distributions over driver reaction time and friction uncalibrated. | Monte Carlo simulation over empirical parameter distributions. | **NO** (Future work) |
| **Staged Withdrawal Policy (W2)** | Blending curves introduce arbitrary free parameters. | Empirical OEM transition telemetry. | **NO** (Optional) |
| **Lateral Avoidance Dynamics** | Scoped out to preserve a tractable 1D boundary. | Combined bicycle model with tire saturation dynamics. | **NO** (Future work) |
| **External Fleet Crash Validation** | Naturalistic crash data with high-frequency CAN telemetry is proprietary. | OEM fleet crash telemetry. | **NO** (Epistemic limit) |

---

## 18. Current Branch & Parallel Engineering Status

### 18.1 Main Scientific Line
The authoritative scientific commit history on branch `main` is:
```
1ad1951 (HEAD -> main) Correct obstacle-passage and clearance semantics
7eca2eb Fix takeover event semantics before model identification
569f68e Clarify human recovery measurement semantics
d908fa1 Audit empirical human recovery definitions and robustness
e9b8629 Characterize empirical human takeover recovery trajectories
13e3189 Audit public human takeover data for Phase 2
c09f682 Reconcile original research scope with completed work
a13ff7f Audit final quantitative and novelty claims
3f146aa Correct novelty audit against authority-transition safety prior work
```

### 18.2 Parallel Engineering Branches
- Parallel D003 ingestion-hardening branch: Currently identical to `main` at `1ad1951`.
- Parallel D003 ingestion-QA branch: Branches off `13e3189` with commit `9bef347` ("Add D003 ingestion and QA infrastructure"). Contains unintegrated parallel data ingestion scripts.
- **Scientific Protocol:** Unmerged work on parallel branches is treated as external engineering until formally audited and merged into `main`.
- **[AUDIT 2026-09-22: SHAs at the pre-audit snapshot: ingestion-QA branch = `9bef3474bae6dcb82d40ca1b8c25f8e16440ae37`; ingestion-hardening branch = `1ad19510edf567db1522772cdae2ae2f52afeff1`. Archive: `archive/pre-audit-2026-09-22` / tag `pre-audit-2026-09-22` = `7f918fcc269ce734f6434f069a9c2c35b0269aac`. Restructuring branch: `audit/research-baseline-restructure`. The QA branch would wrongly fail the 42 benign trailing-row trials and must be revised before any merge.]**

---

## 19. Current Programme Status Matrix

| Original Charter Component | Current Status | Available Evidence | Remaining Work |
| :--- | :---: | :--- | :--- |
| **RQ1: Joint Recoverability Envelope** | ~~PARTIALLY COMPLETE~~ **NOT STARTED / GATED** | Deterministic boundary $T_{\text{required}}$; D003 empirical settling. | Couple human controller to vehicle physics; probabilistic Monte Carlo envelope. |
| **RQ2: Vehicle Response Architecture** | ~~COMPLETE (1D KINEMATICS)~~ **PARTIAL / MODEL-VALID** | Exact sensitivities $\frac{\partial T}{\partial a_{\text{pre}}} = -0.155$; elasticity ranking. | Multi-axle dynamic load transfer; empirical brake pressure telemetry. |
| **RQ3: Driver Familiarity Mismatch** | **RESTRUCTURE** (direct familiarity DEFERRED) | Analytical proof of panic severance; D003 dataset audit. | Human-in-the-loop cross-vehicle transition experiment. |
| **RQ4: Handover & Withdrawal Policy** | ~~PARTIALLY COMPLETE~~ **NOT STARTED beyond W0/W1** | Analytical interaction term; W0 vs W1 factorial comparison. | Staged withdrawal W2; behavioral anticipation of torque cuts. |

### Programme Completion Fraction:
~~Qualitatively, the Deterministic Physical Recoverability Spine is 100% complete. The Original Full Research Programme … is approximately 40–50% complete.~~ **[AUDIT 2026-09-22: WITHDRAWN. No numeric completion fraction is defensible. The spine is PARTIAL / MODEL-VALID; the project stage is EXPLORATORY.]**

---

## 20. Next Logical Phases

**[AUDIT 2026-09-22: Section superseded. Phase 2B-2 and the steps below are DEFERRED. Next proposed phase: R1 (ingestion and observation-semantics repair), not started. See `docs/DECISIONS.md` D015.]**

### ~~Immediate Next Step (Phase 2B-2):~~ (deferred)
- **Task:** **Model-Class Comparison & Minimal Human Controller Identification**.
- **Scope:** Compare competing interpretable model structures (proportional-derivative error feedback, lookahead visual preview, optimal control) against D003 continuous trajectories.
- **Constraints:** Do NOT recruit human subjects. Do NOT implement arbitrary deep-learning black-box models. Do NOT modify the frozen Phase 1 physical spine.

### Subsequent Future Steps:
1. **Phase 2C:** Couple the identified minimal human controller to Phase 1 longitudinal vehicle dynamics.
2. **Phase 2D:** Formulate the probabilistic human fallback recoverability envelope $P(\text{safe fallback} \mid \text{state})$.
3. **Phase 3:** Address 2D lateral avoidance envelopes and external experimental mismatch trials as future work.

---
*End of Technical Handoff Dossier. Verified against repository baseline `phase0-frozen` (`bc21fbc`) and current main HEAD `1ad1951`.*
