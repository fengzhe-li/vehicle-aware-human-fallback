# Research Architecture V2 (post-audit baseline)

**Status:** Adopted 2026-09-22 (Phase R0) as the research-status baseline after the independent audit.
**Supersedes:** the RQ1–RQ4 structure in `docs/ORIGINAL_SCOPE_RECONCILIATION.md` (H0) and `PROJECT_TECHNICAL_HANDOFF_2026-09.md`.
**Does not supersede:** `research/project_charter.md` v1.0, which remains the historical source of the project's intent.
**Pre-audit state:** preserved at tag `pre-audit-2026-09-22` (commit `7f918fcc269ce734f6434f069a9c2c35b0269aac`).
**Companion documents:** `docs/OBSERVATION_LAYER.md`, `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`, `research/data_matrix/D003_KNOWN_BLOCKERS.md`.

This document defines structure only. It does not claim that any layer, interface, or synthesis has been established. Status lives in `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`.

---

## 1. Historical basis (what the project originally meant)

The original project (charter v1.0, README at commit `559ff13`, `docs/DECISIONS.md` D001–D008) consisted of **one mother question and four mechanism layers**, not four peer research questions:

| Original element | Source | Original meaning |
|---|---|---|
| Mother question | Charter §2 | "Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?" |
| Vehicle-response layer | Charter §4.1; D002 | The mapping from control input to actual longitudinal response: friction braking, regenerative braking, one-pedal response, blended/nonlinear braking, latency, build-up, jerk, maximum deceleration, road friction, propulsion authority. EV/ICE are contextual labels, not explanatory variables. |
| Driver internal-model layer | Charter §4.2; D003–D004 | A **generic** mismatch `M = D(f_hat_driver, f_vehicle)`. ICE-like vs EV-like learned priors (D004) are one later instance, not the definition. |
| Handover layer | Charter §4.3; README layer 3 | TOR time budget, automation withdrawal, effective control reacquisition (`T_authority`, `T_effective`), and stabilisation (`T_stable`). "Must not equate hand on wheel or automation disengagement with safe control reacquisition." Transition and reacquisition were **bundled** in this one layer. |
| System-level layer | Charter §4.4; Architecture V1 branch E | "Mechanisms that survive individual tests are coupled into a Human Fallback Safety Envelope." A **gated synthesis**, marked PREMATURE until its inputs survived their own gates. |
| Scenario criticality | Charter §2 and §5; README layer 4 | **Not a layer.** Named in the mother question, and listed as Phase-1 inputs (`v0`, TTC/hazard distance, road friction). |

**Later constructions that were presented as original (corrected in R0):**

- W0/W1/W2 labels first appear in commit `bc21fbc` (Phase 0.4, `docs/CAUSAL_MODEL.md`). The first commit contains only the phrase "Can test immediate vs staged" in `research/identifiability/identifiability_matrix.csv`. The charter lists "automation withdrawal policy" only as a Phase-1 variable.
- The "Original Charter Wording" quoted for RQ4 in H0 ("How does automation withdrawal policy (immediate withdrawal W1 vs cruise-maintenance W0 vs staged withdrawal W2) interact with …") is **not present in the charter or any pre-H0 file**. It first appears in commit `c09f682` (H0).
- The "four original top-level RQs" (RQ1–RQ4) were constructed in H0. The charter has one mother question and mechanism layers.

**What V2 changes relative to the original (named, not hidden):**

1. Transition (C) and human reacquisition (B) are **split** into separate layers. This is a restructuring, not a restoration.
2. Scenario/hazard state (D) is **promoted** to a causal layer. This is justified by evidence: `v0` and `a_max` carry the two largest elasticities of the deterministic boundary, and in D003 the hazard state is aliased with the experimental condition. It is not claimed as original structure.
3. The internal model M is placed at the **B↔A interface**, restoring the charter's generic definition.
4. A non-causal **observation layer** is added (`docs/OBSERVATION_LAYER.md`).

---

## 2. Mother question

> Under what combinations of vehicle response, human control reacquisition, automation transition behaviour, and hazard state does human fallback remain an effective and safe recovery mechanism in time-critical automated-driving handovers?

This keeps the charter's standard ("effective and safe") and its factor structure, with "driver capability" made explicit as control reacquisition and "handover policy" widened to transition behaviour.

---

## 3. Causal layers

### A. Vehicle response: `u(t) -> a(t)`
The mapping from control command (human or automation) to realised longitudinal (and later lateral) vehicle response:
- propulsion authority
- pre-control deceleration `a_pre` (coast, drag, regeneration, or automation deceleration before effective human input)
- response delay `t2`
- deceleration build-up `t3` and jerk
- saturated capability `a_max`
- braking response to *partial* commands
- regenerative/friction blending
- one-pedal behaviour
- friction limits

**R3A refinement (2026-09-23):** `a_pre` is not a vehicle-only quantity. It is selected first by the transition state (continued automation control, automation deceleration, or propulsion release) and takes a vehicle-dependent magnitude (drag, engine braking, lift-off regen) only in the release branch. It therefore sits at the **A↔C interaction**. Build-up `t3` is dominated by human pedal application in measured emergency stops and sits at the **A↔B interaction**. Evidence: `docs/R3A_VEHICLE_TRANSITION_HAZARD_REPORT.md` §3–4.

### B. Human control reacquisition
The human process from request to recovered control:
1. TOR perception
2. situation reconstruction
3. first input
4. effective input
5. manoeuvre choice (brake / steer / combined)
6. corrections
7. manoeuvre completion
8. stabilisation **or** handback, whichever the protocol ends with; handback is a competing event, not a stabilisation

### Interface B↔A: internal expectation / familiarity `M`
`M = D(f_hat_driver, f_vehicle)`, a mismatch between the driver's expected and the actual `u -> a` mapping. It sits at the human↔vehicle interface. **EV/ICE familiarity is one instance of M, not the whole human layer.** For status and identifiability see `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §5.

### C. Automation transition
- TOR timing
- available time budget `T_available`
- authority state (who controls which channel, when)
- continued automation support during the transition
- withdrawal behaviour
- shared control
- minimum-risk manoeuvre (MRM) / fallback behaviour

**R3A refinement:** four transition events are kept distinct and never equated: request (`t_TOR`), driver acknowledgement / mode switch (`t_ack`; D003 Manual_Start), per-channel authority transfer (`t_auth`), and first effective human input (`t_eff`). `T_available` is manoeuvre-specific. **R3B-0 convention:** `T_available^m` is the constant-velocity reference time from `E_TOR` to the boundary of manoeuvre *m* (observable; TTC at TOR for a stationary obstacle). Transition policy, human and vehicle dynamics all enter `T_required^m`. Steering is defined only when an escape path exists; combined recovery is undefined. For R157 systems, authority transfer is per channel, conditional and threshold-based (§6.2.5, §6.3). Full specification: `docs/SYSTEM_EVENT_STATE_SPECIFICATION.md`.

Regulated Level-3 systems (e.g., UN Regulation No. 157, ALKS) keep operating during a transition demand and must be capable of an MRM. Immediate withdrawal (the former "W1") is therefore a counterfactual abstraction, not a representative regulated policy.

### D. Scenario / hazard state
- speed `v0`
- TTC / distance to hazard
- friction
- hazard geometry
- escape-path availability
- adjacent-lane state (occupancy, gaps)

---

## 4. Closed loop

The layers form a loop, not a chain:

```
        ┌──────────────────────────────────────────────────────────────┐
        │                                                              │
        ▼                                                              │
 D. HAZARD STATE ──(perceived state)──► B. HUMAN RECONTROL ──u(t)──► A. VEHICLE RESPONSE
   v, TTC/distance, μ,                  TOR perception → first input    u → a(t): propulsion,
   geometry, escape path,               → effective input → manoeuvre   a_pre, t2, t3, a_max,
   adjacent lane                        → corrections → completion      blending, one-pedal,
        ▲                               → stabilisation / handback      jerk, friction
        │                                     ▲         ▲                      │
        │                                     │   [M: B↔A interface]           │
        │                                     │                                │
        │                          C. AUTOMATION TRANSITION                    │
        │                          TOR timing, T_available, authority state,   │
        │                          continued support / withdrawal /            │
        │                          shared control / MRM ───u_auto(t)──────────►│
        │                                                                      │
        └────────────────────── realised motion x(t), v(t), lane ◄────────────┘

 OBSERVATION LAYER (non-causal, mandatory): event semantics, channel semantics, windows,
 authority windows, censoring/competing events, outcome labels, plausibility filters,
 dataset limitations. See docs/OBSERVATION_LAYER.md.
```

`hazard -> human -> vehicle -> hazard`: the realised motion changes the hazard state, which the human perceives again. Automation (C) acts on the vehicle (A) during the transition and determines what state and time are handed to the human.

---

## 5. System synthesis (GATED, NOT STARTED)

- **Deterministic precursor:** `T_available >= T_required`, per manoeuvre type.
  - The existing closed form `T_required(v0, t1, a_pre, t2, t3, a_max)` is **one slice** of this precursor: longitudinal, open-loop, deterministic, saturated braking, stationary in-lane hazard.
  - It is **not** the synthesis. It does not include steering/lane-change recovery. In D003, drivers change lanes in 499 of 513 trials.
  - **R3B:** the slice now runs on the corrected model (friction cap, explicit authority timeline, wired command) and is evaluated as deterministic interval bounds with policy branches P0/P1/P2 (`docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md`). Its label is "interval-bounded longitudinal braking recoverability slice"; it is still not the synthesis.
  - **R3A classification:** the slice is the *capability-bound* braking requirement (full command `u = 1`). It is a necessary, not sufficient, condition for braking-only recovery; it is optimistic in behaviour (`u = 1`) and conservative in manoeuvre (it ignores steering when an escape path exists). Recoverability must be stated per manoeuvre: `T_required^brake`, `T_required^steer`, `T_required^combined`.
- **Future target:** `P(safe fallback | vehicle, human, transition, hazard)`.

**No system-level synthesis currently exists.** It must not be described as "partially answered". Gating conditions are listed in `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §7.

---

## 6. Research questions (V2)

| ID | Question | Layer |
|---|---|---|
| RQ-A | How does the input→response mapping during and after authority transfer (pre-control deceleration, delay, build-up, saturation; later partial and regenerative braking) change the time required for recovery? | A |
| RQ-B | What are the observed sequence, timing, and manoeuvre choice of human control reacquisition up to handback, and how do they vary across drivers and repeated exposures? | B |
| RQ-C | How do transition behaviours (continued support, withdrawal, shared control, MRM, time budget) change the time available and the vehicle state handed to the human? | C |
| RQ-D | Which hazard-state features (speed, distance/TTC, friction, geometry, escape path) determine the time required and which recovery manoeuvres are feasible? | D |
| RQ-M | Does mismatch between expected and actual vehicle response change reacquisition? (Split into four sub-questions; see status baseline §5.) | B↔A |
| RQ-S | When is `T_available >= T_required` for each manoeuvre, and later, what is `P(safe fallback | A, B, C, D)`? | Synthesis (gated) |

---

## 7. Rule of passage

Empirical results may enter a causal layer **only** after their observation semantics have been validated under `docs/OBSERVATION_LAYER.md`. A number computed from telemetry is not evidence about a layer until its event definitions, channel meaning, observation window, and outcome labels are documented and checked.
