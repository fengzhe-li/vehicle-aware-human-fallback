# Research Status Baseline (post-audit, 2026-09-22)

**Status:** Adopted in Phase R0 as the authoritative status of the project. It supersedes every status label, readiness decision, and novelty statement in earlier documents where they conflict. Those documents carry correction notices pointing here.
**Pre-audit state:** tag `pre-audit-2026-09-22`, commit `7f918fcc269ce734f6434f069a9c2c35b0269aac` (archive branch `archive/pre-audit-2026-09-22`).
**Architecture:** `docs/RESEARCH_ARCHITECTURE_V2.md`. **Measurement rules:** `docs/OBSERVATION_LAYER.md`. **D003 blockers:** `research/data_matrix/D003_KNOWN_BLOCKERS.md`.

Status vocabulary, used conservatively:
- **COMPLETE:** established within the stated scope.
- **PARTIAL:** some valid evidence exists; a named part is missing.
- **MODEL-VALID:** mathematically correct inside a stated model; not empirical validation.
- **INVALID / WITHDRAWN:** must not be cited as a finding.
- **NOT STARTED:** no valid evidence yet.
- **DEFERRED:** intentionally postponed.
- **GATED:** cannot begin until named prerequisites exist.

Decisions: **KEEP / NARROW / RESTRUCTURE / WITHDRAW / DEFER**.

---

## 1. Current stage

**EXPLORATORY**, with a potentially thesis-capable / paper-shaped core **after repairs**.

- Not manuscript-ready.
- Not submission-ready.
- The label "paper-ready" (`P1-B: READY`) is **withdrawn**.

The earlier `PAPER-READY, PROGRAMME-INCOMPLETE` (H0-B) classification is withdrawn, and so is the "40–50% complete" estimate.

---

## 2. Status by component

| Component | Previous status | Corrected status | Decision | Basis |
|---|---|---|---|---|
| Longitudinal analytical spine (A0/D0/E0) | "100% complete", "paper-ready", `P1-B` | **PARTIAL / MODEL-VALID.** Mathematically correct inside the deterministic, open-loop, 1-D, saturated-braking, stationary-hazard model. Not empirical vehicle validation. Not a completed vehicle-response layer. | NARROW | Tests pass; model assumptions (u ≡ 1, stationary in-lane hazard) |
| `T_required` closed form | "First exact closed form"; N2 | **MODEL-VALID.** Standard piecewise-constant/linear-ramp kinematics. | KEEP (math), NARROW (science) | §4 |
| `t1/t2/t3` decomposition | Novel element | **Prior-art-compatible mechanics.** Reaction + response delay + half build-up is standard accident-reconstruction practice. | KEEP (mechanics), WITHDRAW (novelty) | §4 |
| `a_pre` term | "Dominant vehicle-response effect", "3.7× larger than `t2`" | **Model parameter / candidate coupling term** between transition (C) and vehicle (A). The 3.7× ratio depends on the chosen ranges (`a_pre` 0–3 m/s² vs `t2` 0.05–0.17 s). Its realistic value is set by transition behaviour, which has not been studied. | NARROW | Algebra; `docs/QUANTITATIVE_CLAIM_LEDGER.md` |
| Vehicle-response layer (RQ-A) | "ANSWERED" / "COMPLETE (1D kinematics)" | **PARTIAL.** Covers saturated emergency braking only; the `u -> a` mapping (partial braking, regen, one-pedal, blending) remains largely untested. | RESTRUCTURE | u ≡ 1 in all branches |
| Human control reacquisition (RQ-B) | H1-B: "closed-loop structure identifiable" | **PARTIAL / RESTRUCTURE.** Only event timing that does not depend on control-channel authorship is usable (`t_button`, TOR → validated lane change). Human first input from accelerator, brake or steering channels is UNRESOLVED: the channels are not driver-only (R2A, B17). | RESTRUCTURE | D003 blockers B7, B9, B17 |
| `T_stable` (current metric) | "≈22–23 s robust", "100% settled", "0% censored" | **INVALID / WITHDRAWN.** See §3. | WITHDRAW | 81% after `Time_Manual_Stop` |
| Correction counts (brake extrema, reapplications, full-record steering reversals) | "Median 3 extrema, 2 reapplications, 13 reversals" | **INVALID AS CURRENTLY COMPUTED.** Windows include the automation period after handback (audit probe: median brake peaks 3 over full record vs 1 within manual window; steering reversals 13 vs 7). | RESTRUCTURE | Observation-layer window violation |
| Familiarity / internal model (RQ-M) | `M0-C: NOT IDENTIFIABLE`; C0 "∂a/∂M ≡ 0" | **RESTRUCTURE** into four sub-questions (§5). The C0 severance argument is withdrawn: it is true by construction under u ≡ 1, and its premise (step braking) is contradicted by D003's gradual, non-step braking (subject to B6). | RESTRUCTURE | §5 |
| EV/ICE / one-pedal / regen familiarity | Deferred | **Not identifiable from the verified public data checked.** | DEFER | §5 |
| Handover / transition (RQ-C) | "PARTIALLY ANSWERED" (W0 vs W1) | **NOT STARTED beyond the narrow W0/W1 abstraction.** W0/W1/W2 are not original charter RQs. The quoted H0 "Original Charter Wording" for RQ4 is not in the charter. TOR budget has not been varied empirically (D003 fixes TTC at TOR ≈ 7.04 s). Immediate withdrawal (W1) conflicts with regulated L3 behaviour (UN R157: system keeps operating during a transition demand; MRM required). | RESTRUCTURE | Git history; R157 |
| A1 (withdrawal × response) | "NARROW / COMPLETE" | **MODEL-VALID counterfactual** parameter mapping. | NARROW | — |
| B0 (risk-state escalation) | "ANALYTICALLY RESOLVED" | **Modelling remark.** True by construction under the Markov assumption; not an empirical result. | NARROW | — |
| TOR budget | Implicit in boundary | **NOT STARTED** as a studied variable. | DEFER | D003 design |
| D003 factorial analysis | Holm-adjusted causal effects ("workload delays button press +0.40 s", "density triples brake force") | **Causal language WITHDRAWN.** Narrowed to **descriptive condition-associated differences**. Cells are aliased with road, speed, distance, starting lane, pre-TOR automation duration, multi-TOR, and (R2A) automation-transition behaviour around TOR (B11, B17). | WITHDRAW (causal) / NARROW (descriptive) | B11, B17 |
| Scenario / hazard state (RQ-D) | Controlled nuisance inputs | **NOT STARTED** as a dedicated causal layer. | RESTRUCTURE | V2 architecture |
| System-level recoverability (RQ-S) | RQ1 "PARTIALLY ANSWERED" | **NOT STARTED / GATED.** Only a deterministic longitudinal vehicle-side boundary exists. | DEFER | §7 |
| D003 ingestion | "513 extracted", "100% integrity" | **PARTIAL.** R1 (strict ingestion, `src/data/d003_ingest.py`): header variants, `lane_gap` parsing and missing-TOR handling RESOLVED. Multi-TOR handling, lane-change clock validation, lane numbering, TTC domain and multiple handbacks PARTIALLY RESOLVED (6 TOR anchors unresolved; 1 lane-change clock exception). Still open: `lane_gap` meaning, brake-channel semantics, authority semantics, owner set reconciliation, the collision proxy, and the legacy loader/H1 scripts. | RESTRUCTURE | B1–B16 (R1 statuses) |
| Collision proxy (`DERIVED_COLLISION_PROXY`) | 6 trials (1.17%) | **INVALID / WITHDRAWN.** | WITHDRAW | B10 |
| `T_pass` | Adopted | **Valid as longitudinal hazard-station crossing only.** | KEEP | — |
| `T_safe_clear` | "NOT IDENTIFIABLE" | **Not directly observed.** A lane-level proxy may become possible after `lane_gap`/`lane_id` repair; obstacle geometry remains absent. | DEFER | B4, B5, B8 |
| Validation level | "V1"; "Level 3 PARTIAL (D003 Sim / D001)" | **No empirical validation of the boundary.** D003 samples a non-critical regime (7 s budget ≫ `T_required` range 1.1–3.6 s) with an unparameterised simulator vehicle. | NARROW | — |
| Novelty | N1/N2; "first exact closed form" | See §4. | WITHDRAW / NARROW | §4 |
| Paper readiness | `P1-B: READY` | **WITHDRAWN.** | WITHDRAW | §1 |
| Phase 2B-2 controller-model competition | "Current focus" | **DEFERRED.** Not required for the mother question at this stage. Its inputs (channel semantics, windows, labels) are unresolved, and D003 only samples the non-critical 7 s regime. | DEFER | — |

---

## 3. `T_stable`: withdrawal statement

The nominal `T_stable` metric (steering speed ≤ 0.05 rad/s and brake-rate ≤ 20 N/s, sustained 1.5 s, searched from `T_first + 2 s`) is **withdrawn as a measure of human stabilisation**.

- `Time_Manual_Stop` is documented as the moment the participant pressed the switch and returned to **automated** mode. The dataset owners confirm the protocol: take over, change lanes, hand control back.
- Median `Manual_Stop − TOR` ≈ 18.9 s (IQR 15.2–24.1 s). The nominal `T_stable` median is ≈ 22.47 s.
- About **81%** of nominal `T_stable` values occur **after** `Time_Manual_Stop`, i.e. predominantly under automated control.
- The detector's own condition is satisfied in about 90% of pre-TOR automation samples: it detects automation-like smoothness.
- When the search is restricted to the human-control window (before `Time_Manual_Stop`), only about **18%** of trials settle.

Explicitly withdrawn:
- "≈22–23 s" as human stabilisation time
- "100% settled"
- "0% censored"
- the anchor-invariance ("span 0.08 s / 0.48 s / 0.78 s") conclusions built on them

The results files are retained unchanged as pre-audit artifacts.

Any replacement must be defined as time-to-event data within the human-control window, with handback as a **competing event** (informative, protocol-driven), under `docs/OBSERVATION_LAYER.md`. No replacement metric is adopted in R0.

---

## 4. Novelty

**Withdrawn:**
- "first exact closed form", "first exact closed-form analytical stopping boundary", and equivalent wording
- novelty based on `t1 + t2 + t3/2`. This is standard stopping-distance practice in accident reconstruction (reaction time + brake response time [Ansprechzeit] + half the build-up time [Schwellzeit]). Closed-form safety-distance models with linearly rising deceleration also exist.
- novelty based on `-a_max·t3²/24`. This follows directly from a linear ramp: over the ramp the distance is `v·t3 − a·t3²/6` and the speed falls by `a·t3/2`; adding the remaining braking distance `(v − a·t3/2)²/(2a)` gives `v·t3/2 + v²/(2a) − a·t3²/24`.
- novelty based on the `a_pre` term alone (a piecewise-constant extension)

**Remaining novelty candidate (NOT established):**
- causal separation, and later coupling, of vehicle response, human reacquisition, automation transition, and hazard layers
- a recoverability framework built on that separation
- the possible role of pre-control vehicle response within that framework

This is framing and synthesis, not yet executed. **No novelty is claimed as established.**

---

## 5. Familiarity / internal model (RQ-M), split

**Corrected statement:**
> Direct vehicle-response familiarity (EV / one-pedal / regen familiarity) × takeover response is not identifiable from the verified public data checked. Repeated-exposure learning is identifiable in D003; driving and ADAS experience are only associational.

| Sub-question | D003 | Other verified public data | Status |
|---|---|---|---|
| M-A. Direct EV/ICE, one-pedal, regen familiarity | None (single simulated vehicle; no EV fields) | None found in the sources checked. ADAS-TO covers 22 brands with drivers in their own vehicles; this is between-vehicle variation, not switching. | Not identifiable from checked data; DEFER |
| M-B. Generic prior expectation | Per-trial self-reported familiarity (`wl_familarity`), trust items; no manipulation of the vehicle mapping | None verified | Descriptive association only |
| M-C. Repeated-exposure learning | 9 exposures per driver; order recoverable from epoch clock (57/57); Latin square balanced across cells | — | **Identifiable** (learning of the scenario, not of a vehicle mapping). NOT STARTED. |
| M-D. Driving / ADAS experience | `accu_years`, `accu_km`, `driving_frequency`, `driving_skill`, `assist_frequency` | ADAS-TO (naturalistic) | Associational only (n = 57); already analysed in part by the dataset owners (Applied Ergonomics 2025) |

"Not found in checked data" is not the same as "does not exist".

---

## 6. Historical corrections

- The original project was **one mother question plus mechanism layers** (charter v1.0; README at `559ff13`).
- H0 (`c09f682`) converted these into four peer RQs (RQ1–RQ4) and presented a quoted RQ4 wording as "Original Charter Wording". That wording does not appear in the charter or any earlier file.
- W0/W1/W2 terminology first appears in `bc21fbc` (Phase 0.4). The first commit mentions only "immediate vs staged" withdrawal, in the identifiability matrix.
- The H0 "RQ2" quote splices charter §4.1 with Gate A text.

---

## 7. Synthesis gate (RQ-S)

A system-level synthesis may begin only when:
1. layer-B observations are valid under `docs/OBSERVATION_LAYER.md` (ingestion repaired; channel, authority, and window semantics resolved; censoring handled)
2. empirical distributions exist for timing **and manoeuvre choice** (braking-only is not the observed recovery mode in D003)
3. a hazard layer exists that includes escape-path availability
4. transition behaviour is grounded in real system behaviour (continued support / MRM), defining `T_available`
5. an explicit linking assumption connects the simulator vehicle to layer A
6. valid outcome labels exist for any comparison with data
7. the scope is stated (manoeuvres, budget regime)

---

## 8. Not to be worked on until further review

- PID / lookahead / optimal-control model competition
- Monte Carlo probabilistic envelope
- CARLA
- lateral vehicle-dynamics model
- new human-subject experiments
- EV vs ICE claims
- manuscript drafting around novelty
- causal workload/density claims

---

## 9. Phase R2A classification of candidate D003 quantities

Governed by the B17 interpretation rule: accelerator, brake and steering channels are not driver-only channels. Outputs: `results/R2A_event_vehicle_descriptives/`.

| Quantity | Status | Note |
|---|---|---|
| `t_button` = Manual_Start − TOR | VALIDATED MEASUREMENT | Timing of the mode-switch press; not authority transfer; TOR_ANCHORED |
| TOR → validated lane change | VALIDATED MEASUREMENT | Both events validated per trial; owners' window (n = 478) and manual-interval window (n = 477) stored separately |
| Minimum TTC in the approach domain | PROVISIONAL MEASUREMENT | Domain rule is ours; owners' handling not stated |
| Vehicle maximum longitudinal acceleration / deceleration | VEHICLE-STATE DESCRIPTIVE | Kinematics only; not driver braking. Owners' "maximum deceleration" is their takeover-quality interpretation, not independently verified |
| Longitudinal hazard-station crossing (`T_pass`) | VEHICLE-STATE DESCRIPTIVE | Not clearance, not collision |
| Steering-wheel-angle channel maxima (owners' "maximum steering angle") | UNRESOLVED CHANNEL AUTHORSHIP | Channel observation only |
| Earliest brake / steering / accelerator channel activity after TOR | UNRESOLVED CHANNEL AUTHORSHIP | Not a human first input |
| Window-restricted channel reversal / peak counts | UNRESOLVED CHANNEL AUTHORSHIP | Detector-dependent diagnostics; not promoted |
| `T_first`, first brake input, first steering input, brake-first vs steer-first, negative handover lag, brake-rise latency, driver-attributed maximum braking or steering | WITHDRAWN | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS |
| Correction counts as human corrections | WITHDRAWN | Full-record windows; channel authorship |
| `T_stable` | WITHDRAWN | Window extends past handback |
| Collision proxy | WITHDRAWN | Retired from active outputs; historical only |

Repeated-exposure / trial-order analysis is **not started**. Its dependent variables must first be semantically valid: `t_button` qualifies; control-channel-derived response times do not.

---

## 10. Phase R2B: repeated exposure and human-layer status

Full report: `docs/R2B_REPEATED_EXPOSURE_REPORT.md`; outputs: `results/R2B_repeated_exposure/`.

- Exposure order is reconstructable (57 × 9) and separable from scenario cell (Cramér's V 0.05).
- `t_button`: a small decrease is **associated with repeated exposure** (−0.033 s per exposure, 95% CI −0.058 to −0.007; robust to excluding multi-TOR trials). **PROVISIONAL / ASSOCIATIONAL**, not causal learning.
- TOR → validated lane change: no clear exposure association.

| Human-layer category | Items |
|---|---|
| Identified / measurable | event timing (`t_button`, TOR → lane change, handback); repeated-exposure association for validated metrics |
| Associational only | driving / ADAS experience; participant characteristics |
| Blocked by B17 | driver-attributed brake timing, brake rise, brake-first/steer-first, negative handover lag, driver control intensity, control-channel correction counts, owners' ToT |
| Not identified | EV / one-pedal / regen familiarity; expectation mismatch M as a causal vehicle-specific construct |

## 11. Phase R2C-lite: participant associations and carry-over

Full report: `docs/R2C_LITE_REPORT.md`; outputs: `results/R2C_lite/`.

- Participant median `t_button` and exposure slope vs years of driving, km in the past 12 months, driving frequency and ADAS-use frequency (n = 57): **no association survives Holm adjustment**. Secondary re-analysis; the dataset owners have already analysed driver characteristics.
- Carry-over (previous scenario cell) is identifiable as a main effect but **not detected** (joint Wald p 0.56 compact, 0.77 full). Adjusting for it changes the exposure slope by 3–4%.
- Caveat on R2B: restricted to exposures 2–9, the exposure slope stays negative (−0.026 s per exposure) but its cluster-robust CI includes 0 even without carry-over terms. The R2B association is **modest**, and its precision depends on including exposure 1.
- Multi-TOR exclusion changes no conclusion.

| Human-layer category | Items |
|---|---|
| Identified | event timing; repeated-exposure association for `t_button` (modest; not explained by carry-over) |
| Associational only | driving / ADAS experience relationships (null after correction); carry-over relationships (none detected) |
| Blocked by B17 | any driver-attributed control-channel result |
| Not identified | EV / one-pedal / regen familiarity; causal expectation mismatch M |

## 12. Phase R3A: vehicle, transition and hazard evidence baseline

Full report: `docs/R3A_VEHICLE_TRANSITION_HAZARD_REPORT.md`. Registry: `research/PARAMETER_PROVENANCE_REGISTRY.csv`. Identifiability: `research/identifiability/identifiability_matrix_R3A.csv`.

- `a_pre`: primarily a transition-policy variable; drag alone is 0.2–0.4 m/s² at 100 km/h (EPA road-load data), so larger values need engine braking, lift-off regen or an automation command.
- Braking spine: capability-bound (`u = 1`) necessary condition for braking-only recovery; not sufficient; exact only when no escape path exists.
- Recoverability must be manoeuvre-specific; the lateral / combined requirement is not identifiable from D003 (hazard geometry, gaps and steering authorship missing).
- Not identifiable: authority transfer, effective human input, regen/friction blending, escape-path availability, D003 vehicle and automation model.
- Novelty: no new physical, human or transition model. The most plausible contribution is a measurement / assurance framework for when fallback claims are supportable; its prior art has not yet been searched.
- No synthesis exists.
