# R5A: final research question, claim ledger and contribution structure

**Status:** 2026-09-24. Consolidation only.
- No new model, analysis, assumption or result.
- No earlier result file is changed.
- Every number is quoted from an earlier phase's canonical outputs or report.

**Canonical claim ledger:** `research/R5A_CLAIM_LEDGER.csv`, 42 claims (40 at freeze; L41–L42 added by the amendment in §10) with the fields `claim_id`, `status`, `permitted_wording`, `forbidden_stronger_wording`, `evidence_basis`, `required_qualifier`, `scope` and `phase_source`. The CSV governs where it and this document differ.
**Test:** `tests/test_r5a_claim_ledger.py`.

---

## 1. Final research question

### A. Primary research question

> In time-critical automated-driving takeovers before a stationary in-lane hazard, under which combinations of scenario constraints (speed, time-to-collision at the takeover request, road friction), vehicle braking capability and counterfactual automation-transition behaviour can a braking-only recovery satisfy a necessary stopping condition? And how far can the human-response evidence in a public driving-simulator takeover dataset (D003) anchor the human timing on which that condition depends?

### B. Subordinate questions

- **SQ1, measurement.** Which takeover events and control quantities in D003 are identified by its documented semantics and signal behaviour, and which are blocked?
- **SQ2, human response.** What does D003 show about:
  - the mode-switch latency (`t_button`) and its association with repeated exposure and participant characteristics;
  - the descriptive lateral sequence that follows the switch to manual mode?
- **SQ3, braking recoverability.** Within an interval-bounded, braking-only model, which scenarios robustly satisfy, robustly fail, or depend on the assumed parameters for the necessary stopping condition? The model uses source-supported vehicle parameters, explicit human-timing assumptions and counterfactual transition branches. Which assumptions drive the answer?
- **SQ4, integration boundary.** Which links between the empirical human layer and the braking model are identified? Why can braking and steering not be combined into a full recoverability model from this evidence?

### C. Why this wording matches the evidence boundary

- **"Necessary stopping condition", "braking-only":** R3B gives exact bounds for a condition that a successful braking recovery must meet. It is not a sufficient condition, a success predictor or a safety assessment.
- **"Counterfactual automation-transition behaviour":** P0, P1 and P2 are modelling branches. They do not describe D003's automation or any production system.
- **"How far … can anchor the human timing":** this is left open as a question, because the answer is largely negative:
  - `t_button` is a mode-switch latency, not t1;
  - driver brake onset and braking strength are not identifiable;
  - steering timing is descriptive, and its authorship is plausible but unverified.
- **What the question avoids:** it does not ask what drivers' braking delay or strength is, and it does not ask for full longitudinal + lateral recoverability. D003 cannot answer either.

---

## 2. Final evidence layers

**Classes:**

| Class | Meaning |
|---|---|
| OBSERVED | measured in D003 with validated semantics |
| SOURCE_SUPPORTED | taken from an external or documented source |
| EXPLICIT_ASSUMPTION | stated interval or value without empirical anchor |
| MODEL_CONDITION | defines the model or method; exact within-model results carry this class, because they are conditional on the model, not observations |
| PROVISIONAL_DESCRIPTOR | derived signal quantity with unverified semantics |
| BLOCKED | not identifiable |

### A. Human / D003 empirical layer

| Item | Class | State |
|---|---|---|
| `t_button` (TOR → Manual_Start) | OBSERVED | median 1.65 s, IQR 1.25–2.00, n = 492 (R2B) |
| Repeated exposure vs `t_button` | OBSERVED (association) | −0.033 s per exposure (95% CI −0.058 to −0.007); not explained by carry-over; precision depends on including exposure 1 (R2B, R2C) |
| Repeated exposure vs TOR → lane crossing | OBSERVED (association) | no clear association (+0.09 s per exposure, CI −0.13 to +0.31) (R2B) |
| Participant covariates vs `t_button` | OBSERVED (null association) | nothing survives Holm correction; n = 57 (R2C) |
| Manual_Start semantics | SOURCE_SUPPORTED | switch to manual mode, enabling manual inputs (dictionary and owners' paper). Behaviour consistent for lateral channels, not a clean longitudinal boundary (R4 audit, R4V) |
| Mode / authority flag | BLOCKED | `VehicleUpdate-state` is constant 2.0 (R4V) |
| Brake onset / magnitude | BLOCKED | onset MIXED_OR_AMBIGUOUS; magnitude NOT_IDENTIFIABLE (R4V) |
| Accelerator | BLOCKED | MIXED_OR_AMBIGUOUS (R4V) |
| Steering onset sequence | PROVISIONAL_DESCRIPTOR | MS → onset median 2.10 s; onset → crossing 2.45 s; detector-dependent (R4V-D) |
| Steering torque | BLOCKED | NOT_IDENTIFIABLE as driver torque (R4V, R4V-D) |
| Indicator timing | PROVISIONAL_DESCRIPTOR | MS → indicator median 2.03 s; precedes steering onset in 63% of trials (R4V-D) |
| Lane crossing | OBSERVED | TOR → crossing median 6.40 s (n = 477); MS → crossing 4.80 s (R2B, R4V-D) |
| Hazard distance at onset / crossing | OBSERVED | medians 90 m / 43 m in station-consistent cells; the reference point is undocumented (R4V-D) |
| Target-lane gaps | PROVISIONAL_DESCRIPTOR | non-zero values only; zero semantics unresolved (R4V-D) |

### B. Vehicle / physical layer

| Item | Class | State (R3A, R3B) |
|---|---|---|
| Aerodynamic and rolling drag | SOURCE_SUPPORTED | EPA coast-down 5–95% at scenario speed |
| t2 (actuation delay) | SOURCE_SUPPORTED | 0.05–0.17 s |
| t3 (build-up) | EXPLICIT_ASSUMPTION | 0.3–1.2 s |
| a_max | SOURCE_SUPPORTED | 6.43–9.1 m/s² (regulatory floor; measured passenger cars); not the D003 vehicle |
| Friction limit | SOURCE_SUPPORTED relation; μ values mixed | a ≤ μg with μ 1.0 as the R157 reference; μ 0.5 is an EXPLICIT_ASSUMPTION |
| Braking command | MODEL_CONDITION | u = 1 after effective control (capability bound) |

### C. Automation-transition layer

| Item | Class | State |
|---|---|---|
| P0 / P1 / P2 | MODEL_CONDITION | counterfactual branches: hold / passive drag / supported deceleration before authority |
| Authority timing | EXPLICIT_ASSUMPTION | at effective control, or f·t1 with f ∈ [0, 1] |
| Supported deceleration a_sup | EXPLICIT_ASSUMPTION | 1.0–3.0 m/s², below the R157 5.0 m/s² threshold |
| D003 automation behaviour | OBSERVED as a pattern; logic BLOCKED | scripted braking and throttle around TOR, carrying past MS (R2A, R4V); no automation model |
| Counterfactual vs observed | — | every transition branch is counterfactual; nothing in R3B reproduces D003's automation |

### D. Recoverability layer

| Item | Class | State (R3B) |
|---|---|---|
| Interval bounds on T_required^brake | MODEL_CONDITION (exact within-model result) | guarded corner method; cross-checked against the simulator to 2.2·10⁻⁴ relative |
| Classifications | MODEL_CONDITION (exact within-model result) | 58 ROBUSTLY SATISFIED / 47 PARAMETER-SENSITIVE / 45 ROBUSTLY UNSATISFIED; ε = 0.01 s; 0 boundary flags; closest \|margin\| 0.047 s |
| Monotonicity guard | MODEL_CONDITION (method) | exact analytic derivatives on a dense grid; passes in the whole main domain |
| Stationary-point escalation | MODEL_CONDITION (method) | used for the 2 P2 supplement cases at 60 km/h, μ 0.5; fails closed |
| t1 = 4 s supplement | EXPLICIT_ASSUMPTION (sensitivity only) | 10 labels move from ROBUSTLY SATISFIED to PARAMETER-SENSITIVE |

---

## 3. Final claim ledger (summary)

The full fields are in `research/R5A_CLAIM_LEDGER.csv`.

| Status | Count | Claims |
|---|---|---|
| SUPPORTED | 1 | L14 lane-crossing timing |
| SUPPORTED_WITH_QUALIFIER | 19 | L01 exposure vs `t_button`; L02 covariate nulls; L08 Manual_Start as manual-mode switch; L15–L17 hazard distance and station; L19–L28 R3B results (classifications, TTC, speed, friction, a_max, P0/P1/P2, authority timing, t1 sensitivity, t1 = 4 s supplement, D003-like case); L34 lane crossing vs exposure; L41 steering onset relative to the R3B t1 window (amendment); L42 hazard distance at TOR (amendment) |
| PROVISIONAL | 6 | L09 steering onset; L10 onset → crossing; L11 steering authorship; L13 indicator; L18 target-lane gaps; L35 steering timing vs exposure |
| BLOCKED | 11 | L03 `t_button` as reaction time; L04 `t_button` as t1; L05 brake onset; L06 braking strength; L07 Manual_Start as longitudinal authority transfer; L12 steering torque; L29 full recoverability; L30 combined braking + steering; L31 production safety; L32 causal learning; L33 EV/one-pedal familiarity |
| WITHDRAWN | 5 | L36 condition causal effects; L37 T_stable; L38 correction counts; L39 collision proxy; L40 closed-form novelty |

These counts are checked against the CSV by `tests/test_r5a_claim_ledger.py`.

### 3.2 Key permitted and forbidden wordings

| Claim | Permitted | Forbidden |
|---|---|---|
| `t_button` | "latency from TOR to the mode-switch button press" | "reaction time", "takeover time", "time to effective control" |
| Exposure | "a modest decrease associated with repeated exposure" | "drivers learned", "practice causes" |
| Steering onset | "steering-angle activity onset (provisional, authorship unverified)" | "steering reaction time", "drivers start steering at …" |
| Indicator | "left-indicator signal onset (undocumented channel)" | "intention time", "decision time" |
| Lane crossing | "validated lane crossing" | "completion", "recovery", "safe state" |
| R3B labels | "ROBUSTLY SATISFIED / PARAMETER-SENSITIVE / ROBUSTLY UNSATISFIED within the braking-only model" | "safe / unsafe", "takeover succeeds / fails" |
| P2 | "counterfactual supported-deceleration branch" | "safer policy", "how R157 systems behave" |
| D003-like case | "in the model, ROBUSTLY SATISFIED in every branch" | "D003 drivers could have stopped" |

---

## 4. Contribution structure

### C1. Measurement and data-semantics audit of a public takeover dataset

**Novelty strength:** strong project contribution.

**Wording:** "A semantic audit of the D003 takeover dataset that separates TOR, the manual-mode switch, control-channel activity, lane crossing and handback. It shows that longitudinal control channels carry scripted automation content across the switch to manual mode, so driver brake onset and braking strength are not identifiable. It establishes a causal, sensitivity-checked descriptive steering sequence, with authorship classified as plausible but unverified."

**Evidence:**
- R1 ingestion validation
- R2A (B17)
- R4 internal source-of-truth audit
- R4V (criterion-based authorship classes, straddle analysis)
- R4V-D (detector comparison, hazard-station reconstruction, gap zero contexts)

**Overclaims to avoid:**
- "D003 is invalid"
- "the owners' analyses are wrong"
- "steering is driver-generated"
- "first audit of D003"

### C2. Defensible human-response findings

**Novelty strength:** supporting contribution.

**Wording:** "`t_button` decreases modestly with repeated exposure within participants. This is not explained by short-term carry-over. No participant covariate is associated with it after multiplicity correction. TOR → lane crossing shows no exposure association."

**Evidence:** R2B, R2C-lite.

**Overclaims to avoid:**
- learning mechanisms
- reaction time
- effects of experience or ADAS use

The covariate analysis is a secondary re-analysis of variables the dataset owners already studied.

### C3. Evidence-graded vehicle and transition parameterisation

**Novelty strength:** supporting contribution.

**Wording:** "A provenance-tracked parameter set for a braking-only takeover model:
- source-supported: drag, t2, a_max, the friction relation;
- explicit assumptions: t1, t3, authority timing, supported deceleration;
- model condition: the braking command;
- counterfactual P0/P1/P2 transition branches, with authority timing as an explicit, varied assumption."

**Evidence:** R3A registry (P01–P26), R3B-0, R3B §3 and §13.1.

**Overclaims to avoid:**
- calibrated vehicle model
- D003 vehicle parameters
- description of production transition behaviour

### C4. Interval-bounded braking-only necessary-condition method

**Novelty strength:** incremental / methodological contribution.

**Wording:** "Exact interval bounds on the required braking time for 150 scenario/branch cases:
- corner enumeration protected by an analytic monotonicity guard;
- fail-closed stationary-point escalation where monotonicity fails;
- margin classification that is aware of the ε boundary.

The results show that TTC dominates, friction removes the a_max effect, and the t1 assumption drives most of the uncertainty width."

**Evidence:** R3B, the gate review and gate engineering, the reproduction test, and the simulator cross-check.

**Overclaims to avoid:**
- "novel closed-form solution" (the kinematics are standard)
- "validated recoverability model"
- "safety envelope"
- probabilities

### C5. Epistemic / assurance discipline for fallback analysis

**Novelty strength:** incremental / methodological contribution. The prior-art check classifies it as INCREMENTAL, and no novelty is claimed.

**Wording:** "An explicit separation of observed, source-supported, assumed, provisional and blocked quantities across the human, vehicle, transition and recoverability layers. It uses fail-closed refusal to compose links that are not identified, demonstrated here by refusing `t_button` → t1 and a combined braking + steering synthesis."

**Evidence:** R4 matrix and links, R4V/R4V-D classifications, this ledger, and `research/ASSURANCE_FRAMEWORK_PRIOR_ART.md`.

**Overclaims to avoid:**
- a new assurance framework
- compliance with ISO 26262, ISO 21448 or UL 4600

---

## 5. Recommended result story

Figure and table references either point to existing outputs or are marked "(R5B)" for figures to be planned in R5B. No figure is produced here.

| # | Section | Key result | Exact claim | Strongest caveat | Figure / table |
|---|---|---|---|---|---|
| 1 | What D003 directly reveals | Event timing: TOR, Manual_Start, lane crossing, handback; the hazard distance; a descriptive lateral sequence | L14, L08, L09, L10, L13, L15–L17 | Lateral descriptors are provisional; the reference point on the hazard is undocumented | Event-sequence timeline per trial (R5B); `results/R4V_steering_sequence/interval_summary.csv` |
| 2 | What D003 fails to identify | Driver brake onset and strength; longitudinal authority; driver torque; the automation model; completion | L05–L07, L12; identifiability map §7 | These are limits of D003, not claims about drivers | Brake straddle around Manual_Start by cell (R5B); `results/R4V_channel_authorship/cell_stereotypy.csv` |
| 3 | Defensible human-response findings | `t_button` 1.65 s; a modest exposure decrease; covariate nulls | L01, L02, L34 | Associational; limited precision; n = 57 | `results/R2B_repeated_exposure/`; `results/R2C_lite/` tables |
| 4 | External vehicle and physical evidence | Drag, t2, a_max, friction relation | C3 parameter table | Generic passenger-car evidence, not the D003 vehicle | `research/PARAMETER_PROVENANCE_REGISTRY.csv`; R3B §13.1 table |
| 5 | What R3B establishes | 58 / 47 / 45 classification; TTC dominance; friction and a_max; branch deltas; t1-driven width; the 4 s supplement | L19–L28 | Braking-only necessary condition; t1, t3 and authority are assumptions | `results/R3B_braking_bounds/t_required_bounds.png`; classification pivot (R3B §6); sensitivity table (R3B §7) |
| 6 | What the steering sequence adds | MS → onset 2.10 s; onset → crossing 2.45 s; indicator order; hazard distances 90 m / 43 m; no exposure association | L09–L10, L13, L15–L16, L35 | Detector-dependent; authorship unverified | Detector-sensitivity table; onset distributions by cell (R5B) |
| 7 | Why the analyses cannot be combined | No identified human → braking link; the brake channel is mixed; no completion event; no lateral geometry | L04, L29, L30; R4 links | Absence of a link, not evidence that one is small | R4 cross-layer link table (`research/R4_CROSS_LAYER_LINKS.csv`) |
| 8 | Conclusion that remains | TTC at TOR, friction and the assumed effective-braking onset govern whether braking alone *can* satisfy the necessary condition. D003 cannot calibrate the human side; its lateral sequence shows that drivers in D003 predominantly resolved the takeover by steering, starting mostly after the braking model's assumed t1 window | L19–L26 with L09 and L41 | Descriptive lateral timing; braking-only model; no safety claim | Juxtaposition figure: TOR → steering-onset distribution vs the t1 assumption interval, clearly labelled as not combined (R5B) |

The claim in row 8 about steering "predominantly" resolving the takeover rests on lane crossing in 478 of 492 trials and on TOR → steering onset: median 3.85 s, with 75% of onsets after the 3.0 s upper t1 bound (R4V-D §10). It describes what happened in D003. It does not say that steering was required or sufficient.

---

## 6. Withdrawn or superseded claims

| Item | Originally | Why withdrawn | Replaced by |
|---|---|---|---|
| `T_stable` as human stabilisation | ≈ 22–23 s, "100% settled", "0% censored" | 81% of values fall after Manual_Stop, under automation; the detector fires on automation smoothness | No stabilisation metric; handback treated as a competing, protocol-driven event (baseline §3) |
| Control-channel correction counts | median 3 brake extrema, 2 reapplications, 13 steering reversals | Full-record windows include automation after handback; channel authorship (B17) | Nothing adopted; blocked pending authorship (R4V confirms mixed channels) |
| Derived collision proxy | 6 trials (1.17%) | Hazard geometry unvalidated (B10) | Retired; hazard distance descriptors only (R4V-D) |
| W0/W1 withdrawal simplification | Immediate withdrawal (W1) vs speed hold (W0) as the transition comparison | W1 conflicts with regulated L3 behaviour (R157); W0/W1 were not charter questions | Counterfactual P0/P1/P2 branches with explicit authority timing (R3B) |
| Factorial causal effects | "workload delays button press +0.40 s", "density triples brake force" | Cells aliased with road, speed, distance and automation behaviour; brake channel not driver-only | Descriptive condition-associated differences only |
| D003 brake channel as driver braking | first brake input, brake-first vs steer-first, brake rise, driver maximum braking | R2A found cell-scripted activity before any plausible reaction; R4V found automation braking straddling Manual_Start | Brake onset MIXED_OR_AMBIGUOUS, magnitude NOT_IDENTIFIABLE (R4V) |
| D003 timing as t1 | Candidate empirical anchor for the model's human latency | Mode switch ≠ effective braking; brake onset unidentifiable | t1 kept as an explicit assumption interval (R3B); the link is NOT IDENTIFIABLE (R4) |
| Stabilisation / settlement as completed recovery | Settlement after the lateral manoeuvre treated as recovery | See `T_stable`; Manual_Stop is protocol handback; lane crossing is only a crossing | No completion event; the steering-duration proxy is BLOCKED (R4V-D) |
| Closed-form boundary as system recoverability / novelty | "first exact closed form", "physical boundary between collision and safe recovery", `P1-B: READY` | Standard kinematics; one braking slice only | R3B as a braking-only necessary condition, labels not safe/unsafe; novelty claims withdrawn (baseline §4) |
| C0 "mismatch has no causal pathway" | Severance argument under u ≡ 1 | True by construction; step-braking premise contradicted | Familiarity split into sub-questions; EV/one-pedal familiarity BLOCKED |
| Gate-review monotonicity statement for the t1 = 4 s supplement | "monotone everywhere" | The exact guard found reversals in 2 P2 cases | Erratum; stationary-point t1 bound (D025) |
| R4 recommendation to wait for owner clarification | Stop and wait for the dataset owners | There is no external owner to contact | Internal source-of-truth audit (D028), then R4V |
| R4V steering-angle rule verdict | DRIVER_AUTHORSHIP_SUPPORTED (rule output) | Cell-locked automation content in the same channel; marginal ICC | PLAUSIBLE_BUT_UNVERIFIED (downgrade-only review, D029) |
| R4V gap description | "no negatives and no missing values" | True only for the analysed windows | Erratum in R4V §6; full-trial facts in R4V-D §7 |

---

## 7. Final cross-layer identifiability map

| Quantity | Class | Reason |
|---|---|---|
| TOR | IDENTIFIED | Logged event; protocol-resolved in 492 trials (15 without a TOR column; 6 multi-TOR unresolved) |
| Manual_Start | IDENTIFIED | Logged timestamp; documented as the switch to manual mode |
| `t_button` | IDENTIFIED | Difference of two identified events |
| First human input | NOT_IDENTIFIABLE | Brake and accelerator channels are mixed; steering authorship is unverified |
| Brake onset (driver) | NOT_IDENTIFIABLE | Automation braking straddles Manual_Start; clean onsets lack participant structure |
| Braking magnitude | NOT_IDENTIFIABLE | Unit conflict, straddle, possible cap |
| Steering onset | PARTIALLY_IDENTIFIED | The signal event is measurable with a causal detector, but is detector-dependent and its authorship is unverified |
| Lane crossing | IDENTIFIED | Validated against same-road lane transitions (478 of 492) |
| Authority transfer | ASSUMPTION_DEPENDENT | Lateral behaviour is consistent with Manual_Start; longitudinal content persists after it; R3B treats it as an explicit assumption |
| Effective longitudinal control | ASSUMPTION_DEPENDENT | Not observable in D003; enters R3B only as the t1 assumption interval |
| Effective lateral control | NOT_IDENTIFIABLE | Lateral motion under manual mode is observed (onset, then crossing), but when driver steering becomes effective is not identified |
| Manual_Stop | IDENTIFIED | Logged event (first-episode rule; 12 trials have several values) |
| Manoeuvre completion | NOT_IDENTIFIABLE | No documented completion event; lane crossing and handback are not completion |
| Hazard distance | IDENTIFIED (8 of 9 cells) | Logged documented distance; −dD/dt matches speed; station reconstructed. d0_n1 is trial-relative only; the reference point is undocumented |
| Target-lane gaps | PARTIALLY_IDENTIFIED | Non-zero values usable; zero semantics unresolved; the target-lane mapping is inferred |
| Vehicle model (D003) | NOT_IDENTIFIABLE | No simulator vehicle parameters; R3B uses external generic evidence |
| Automation model (D003) | NOT_IDENTIFIABLE | The behaviour pattern is observable; the logic and its configuration are absent |

---

## 8. Final scope statement

### A. What this project establishes

This project establishes, within a deterministic braking-only model, exact interval bounds on the time required to stop before a stationary in-lane hazard after a takeover request. The bounds cover 150 combinations of speed, time-to-collision, road friction and counterfactual automation-transition behaviour. Vehicle parameters are taken from documented sources, and the human-timing, authority and support parameters are explicit assumption intervals. The resulting classification shows which scenarios robustly satisfy, robustly fail or depend on these assumptions for this necessary condition. It identifies the time-to-collision at the request, road friction and the assumed onset of effective braking as the dominant factors.

On the empirical side, it establishes which events in a public simulator takeover dataset are measurable:
- the latency of the switch to manual mode, which decreases modestly with repeated exposure and is not associated with the recorded participant characteristics;
- the lane-crossing time;
- the distance to the hazard;
- a descriptive, sensitivity-checked lateral sequence after the switch.

It also establishes which quantities that dataset cannot identify.

### B. What this project does not establish

This project does not establish:
- whether human fallback succeeds or is safe in any scenario;
- a takeover-success predictor, a recoverability envelope or any probability;
- the time at which drivers begin effective braking, or how strongly they brake: the D003 longitudinal channels carry automation content across the switch to manual mode, and these quantities remain explicit assumptions;
- steering behaviour as driver-authored behaviour: steering timing is descriptive, and its authorship is plausible but unverified;
- a manoeuvre-completion time, lateral clearance or escape-path geometry;
- a combined longitudinal-lateral recoverability model, which the evidence does not support;
- anything about the D003 simulator vehicle, the automation logic or production automated-driving systems;
- causal effects of learning, workload, traffic density or vehicle familiarity (EV, one-pedal).

---

## 9. Readiness

R5A introduces no new scientific result. It freezes the research question, the claim ledger, the contribution structure and the identifiability map for thesis drafting. The next step is R5B (thesis structure and figure planning), which is not started.

---

## 10. Amendment (2026-09-24): L41 and L42

R5A was reopened narrowly to add two candidate claims that R5B had left out. No existing claim status or wording was changed. The only other edits are the claim count, the §3 summary row and the §5 row-8 reference, which now cites L41. Both claims were checked against stored outputs only; nothing was recomputed from the archive.

### L41: steering onset relative to the R3B assumed t1 window

**Status:** SUPPORTED_WITH_QUALIFIER.

**Evidence.** In `results/R4V_steering_sequence/`, TOR → primary steering-activity onset is the sum of TOR → MS and MS → onset. The identity holds for every row (n = 491; 1 missing).

| Detector | After 3.0 s | Before 1.15 s |
|---|---|---|
| Primary | 75.4% | 0% |
| Rise 0.02 rad | 56.9% | 0.2% |
| Rise 0.10 rad | 87.4% | 0% |
| Signed change from MS value | 77.5% | 0% |
| \|change\| from MS value | 72.6% | 0% |
| Wheel-speed detector | 71.9% | 0% |

- Primary detector: median 3.85 s (IQR 3.00–4.88).
- By scenario cell, 51–98% of onsets fall after 3.0 s.
- Against the 4.0 s supplementary bound, only 46.8% fall after it.

**Why SUPPORTED_WITH_QUALIFIER and not PROVISIONAL:**
- The claim is ordinal ("predominantly after the interval") and concerns a signal event. It holds for every detector compared and in every cell, which removes the detector dependence that keeps L09 PROVISIONAL for exact timings.
- Authorship remains unverified (L11). It is carried as a qualifier and does not affect a statement about signal timing.
- L09 itself stays PROVISIONAL.

**Qualifiers:**
- It compares a signal event with a modelling assumption.
- It implies no braking timing and no causal or sequential link between longitudinal and lateral recovery.
- It does not hold against the 4 s bound.

### L42: hazard distance at TOR

**Status:** SUPPORTED_WITH_QUALIFIER.

**Derivation.** `hazard_distance_at_tor_m` in the R4V-D event table is the **directly logged** channel `Distance_to_Construction` (channel 85; data dictionary: "distance to collosion" [sic], m), linearly interpolated at the resolved TOR time (20 Hz samples). It is **not** derived from speed or TTC, and not reconstructed.

**Validity scope:**
- It is interpreted as an along-path distance only in the 435 trials of the 8 station-consistent cells, where −dD/dt matches speed and the station reconstructs (L17).
- In those trials: median 178.0 m (IQR 175.2–195.9; 5–95% 150.6–196.9); cell medians 157.9–196.6 m.
- **d0_n1 is excluded** (57 trials). Its logged value is very consistent across trials (median 135.7 m, SD 0.2 m), but the channel's rate does not match the road abscissa there (dD/ds ≈ 0.78), so its meaning as an along-path distance is unverified.

**Qualifiers:**
- The reference point on the construction zone is undocumented.
- The value is cell-dependent.
- No TTC or stopping-distance quantity is derived from it here.

**Earlier figure.** The R4V value (median 177.5 m over all 492 trials) included d0_n1 and is superseded for claim purposes by L42.
