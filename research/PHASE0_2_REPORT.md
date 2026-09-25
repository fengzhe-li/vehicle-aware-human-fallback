# Phase 0.2 Report — Mechanism Definition + Parameter Anchoring

## Scope

Phase 0.2 does not implement the simulator, does not touch CARLA, and does not run Experiment A. It answers a narrower question: **can Experiment A now be parameterised with defensible empirical/literature constraints, and if pieces are still missing, exactly which pieces?** All Phase 0.1 outputs (`PHASE0_1_REPORT.md`, `gap_audit.md`, `parameter_evidence_table.csv`, `experiment_A_review.md`, `dataset_inventory.csv`, `identifiability_matrix.csv`) were re-read before starting this work and are treated as authoritative background, not re-litigated here except where new evidence changes a conclusion.

## 1. Refined novelty statement — and an active challenge to it

**Refined working hypothesis (as given):**
> Existing work studies takeover criticality, driver state, time budget and vehicle motion, and separate braking literature shows that control architectures alter longitudinal behaviour. The unresolved question is whether the transient mapping from the same human control sequence to different physically plausible vehicle responses materially shifts recovery safety during time-critical automated-driving takeover.

**Challenge to this formulation:**

1. **"The same human control sequence" is itself a strong idealisation that the project adopts, not a fact about the world.** Real drivers do not necessarily apply an identical command sequence across different vehicle architectures — L012 (Phase 0.1) shows adaptation to altered dynamics happens within seconds for small changes. So the "unresolved question," as stated, is really: *unresolved under the specific simplifying assumption of an identical open-loop human command* (which Phase 0.2 now freezes explicitly in `control_input_definition.md`). The more realistic question — does architecture change recovery safety when a driver's own command *also* adapts to the vehicle in front of them — is a different, harder question that neither the narrower hypothesis nor Experiment A's Phase 1A design answers. This must be stated as a scope limit, not glossed over.
2. **Part of the "unresolved question" is already partially informed, not fully open.** L004 (one-pedal vs two-pedal) already shows that accelerator-release-based deceleration changes throttle-to-brake transition timing and its variability, in a manual (non-TOR) emergency-braking paradigm. The genuinely unresolved part is narrower than the sentence implies: it is specifically the **TOR/handover framing**, the **isolation from `a_max`**, and the **recovery-safety outcome framing** (TTC/stopping-margin/impact-speed) that are missing from L004, not the base claim that architecture changes braking behaviour.
3. **Even a "materially shifts recovery safety" finding from this project would be a simulation result under COUNTERFACTUAL-labeled parameters in several places (see Workstream 4 below), not an empirical one.** The narrower hypothesis, if read as asking a claim about the *real world*, cannot be fully answered by a simulation-only project — at most, Experiment A can show that the mechanism is *physically plausible and non-trivial under literature-anchored ranges where they exist*. This is a real, still-useful result, but it is weaker than "materially shifts recovery safety" read literally, and the project's own reporting must not blur that distinction.

**Conclusion:** the refined hypothesis survives this challenge as the project's organising question, but only with the above three caveats made explicit in every future write-up that cites it. It should not be repeated as a flat sentence without the open-loop/COUNTERFACTUAL/simulation-only qualifications attached.

## 2. Control input — see `control_input_definition.md`

Open-loop, two-channel (`u_accel`, `u_brake`), step-command driver. Three timing parameters (`t_reaction = 1.0s` chosen; `Δt_transfer = 0.2s` COUNTERFACTUAL placeholder), one magnitude parameter (`u_target = 1.0`, full commanded brake demand). The command trajectory is frozen identical across all profiles — this is the resolution to Phase 0.1's single most important open gap (`experiment_A_review.md` Q2).

## 3. Minimum vehicle-response model — see `vehicle_response_model.md`

Reduced from the task's eight candidate parameters to **four free parameters** (`a_coast`, `t_delay`, `t_buildup`, `v_rolloff`) plus one held-constant parameter (`a_max`). "Brake gain / nonlinear gain" was dropped (no causal channel under a step command) and "speed dependence" was merged into `v_rolloff` (only the specific, evidenced form — near-stop regen fade — survives; a generic speed-dependence term would be an unconstrained free choice). Jerk was demoted from a free input to a monitored/derived plausibility check.

## 4. Numerical evidence anchoring — results

Full detail and source-by-source evaluation in `research/parameter_provenance/phase1A_parameter_table.csv`. Summary of what changed since Phase 0.1:

| parameter | Phase 0.1 status | Phase 0.2 status |
|---|---|---|
| `t_delay` (friction brake onset) | unresolved (COUNTERFACTUAL) | **RESOLVED**: 0.05-0.17s, Paquette & Porter (2014), 4 instrumented light passenger vehicles. MEDIUM confidence (trade-journal, not academic peer review). |
| `t_buildup` | unresolved (COUNTERFACTUAL) | **PARTIALLY RESOLVED**: 1.75-2.0s upper-bound anchor from a driving-simulator pedestrian-collision-warning study (arXiv:2112.09074) — explicitly flagged as human-inclusive, not pure vehicle-hardware, so usable only as a plausibility ceiling. |
| `a_coast` (regen) | unresolved (L006 paywalled) | **PARTIALLY RESOLVED**: 1-4 m/s² (0.1-0.3g), from OpenLKA EV Dataset's (D004) own README documentation. L006's SAE full text and its ResearchGate mirror both remained inaccessible (SAE Mobilus paywall; ResearchGate returned HTTP 403) despite a second retrieval attempt — flagged MEDIUM confidence, dataset-maintainer documentation, not yet cross-checked against raw files. |
| `v_rolloff` (low-speed regen fade) | qualitative only | **STILL qualitative only.** Mechanism strongly corroborated by multiple independent engineering sources (regen torque is inherently speed-dependent; production EV control logic deliberately phases out regen near standstill in favour of creep torque) but no numeric threshold speed or fade curve was found anywhere. This is now explicitly the weakest-anchored of the four retained parameters. |
| jerk (emergency, human-driven) | unresolved | **STILL unresolved** — and a specific numeric claim (5.3 m/s³ jerk / 3.6 m/s² deceleration at the 90th percentile) that surfaced during this pass's search **could not be traced to a verifiable source** and was explicitly excluded rather than used. A genuine, traceable anchor was found for *non-emergency* naturalistic jerk (2.6 m/s³, 99th percentile, Feng et al. 2017) — usable only as a plausibility floor, not an emergency ceiling. |
| `a_max` | ~8-9 m/s², LOW-MEDIUM confidence | unchanged; still the best-anchored held-constant parameter. |

Priority sources attempted per the task instruction: SAE full text (blocked — paywall), ResearchGate mirror (blocked — HTTP 403), IIHS/NHTSA/official data (used via L011 and FMVSS 121, the latter explicitly excluded as incompatible — see below), OpenLKA sample files (README-level documentation retrieved; raw file-level inspection still outstanding, consistent with Phase 0.1's `ACCESS_UNCERTAIN` flag on D004).

**Incompatible-conditions discipline applied:** FMVSS 121's air-brake pressure-rise timing (0.35-0.6s) was found and explicitly **excluded** from constraining `t_delay`, because it governs heavy-vehicle pneumatic brake actuation, a physically different technology from passenger-vehicle hydraulic/electric brakes. It is logged in `phase1A_parameter_table.csv` only to document why it was excluded, not merged with the friction `t_delay` figure.

## 5. ADAS-TO audit (corrected)

Re-fetching the actual field schema (via the underlying openpilot/`cereal` `car.capnp` convention that ADAS-TO's release is built on, cross-checked against ADAS-TO's own README) resolves this workstream precisely:

| file | field(s) | type | meaning |
|---|---|---|---|
| `carState.csv` | `gasPressed`, `brakePressed` | **Boolean** | Human pedal-press detection only ("user pedal only" per the underlying schema comment). |
| `carControl.csv` | `actuators.accel` | **Continuous, m/s²** | *Commanded* acceleration from the controller/planner — not a direct human-force signal. |
| `carOutput.csv` | `actuatorsOutput.accel`, `.brake`, `.gas` | **Continuous** (accel in m/s²; brake/gas 0.0-1.0) | "Matches what is sent to the car" — the realized/delivered control output after any safety limiting. |
| `longitudinalPlan.csv` | `aTarget` | **Continuous, m/s²** | Planner's target acceleration — a planning-level signal, not a human or raw-vehicle one. |
| `carState.csv` | `aEgo` | **Continuous** ("best estimate of acceleration") | The vehicle's actual realized acceleration, regardless of who is driving. |

**What ADAS-TO can and cannot identify, stated exactly:**

- **Cannot** identify a continuous human pedal-force-to-deceleration mapping, because the only human-side signal recorded is the binary `gasPressed`/`brakePressed` flag — there is no continuous pedal position or force field in the release. This confirms and sharpens the Phase 0.1 finding.
- **Can** identify the continuous *realized* vehicle acceleration trace (`aEgo`) around a binary brake-press onset event. This means ADAS-TO can supply an empirical, event-triggered "deceleration begins here (binary flag) → resulting acceleration trace (continuous `aEgo`)" distribution across 327 drivers and 163 vehicle models — a genuinely useful, previously under-recognised source for **cross-checking the plausibility of `t_delay`/`t_buildup` shapes** (though it conflates driver pedal dynamics with vehicle mechanical response, same caveat as the arXiv 2112.09074 anchor above), even though it cannot supply a clean input→output mapping isolated from the driver.
- **Can** identify continuous automation-commanded and automation-delivered acceleration (`actuators.accel`, `actuatorsOutput.*`, `aTarget`) during automated/ADAS-controlled segments — this is architecture-relevant in the same sense as L011's AEB characterisation (a controller's braking behaviour, not a human's), and could in principle support a future cross-model AEB-style architecture comparison, but this is explicitly **not** a human-driven-takeover signal.
- **Cannot**, from the README/schema alone, be confirmed to carry driver EV/ICE familiarity, consistent with the Phase 0.1 identifiability finding on driver-vehicle mismatch.

This upgrades ADAS-TO's practical role from Phase 0.1's blanket "USABLE_PARAMETER_SOURCE" to something more precise: usable for realized-acceleration-shape plausibility checks (via `aEgo` around binary brake onset), not usable for fitting a continuous human-command-to-response mapping. `dataset_inventory.csv`'s existing status label (`USABLE_PARAMETER_SOURCE`) remains correct but this precision should be carried into any future use.

## 6/7. Retained outcomes and stopping-margin definition

See `metric_definitions.md` in full. Phase 1A retains `collision` (derived), `TTC_min`, `stopping_margin`, `impact_speed`. `t_stabilise` and `N_correction` are dropped from this experiment's scope — not redefined — because they require a closed-loop/correction-capable driver that the frozen open-loop design structurally does not have; reporting them would misrepresent a structural non-result as a finding.

`stopping_margin` is defined as `x_hazard - x_stop_full`, where `x_stop_full` is computed by continuing the vehicle's actual (non-constant) deceleration trajectory mathematically past `x_hazard` if necessary, treating the hazard as a spatial reference marker for this one measurement rather than a rigid wall. This keeps it continuous and sign-informative across the collision boundary (positive = safety buffer, negative = counterfactual excess distance needed, correlating with but not duplicating `impact_speed`, which is measured at the real, wall-respecting crossing point in a different domain — velocity, not distance).

## 8. Gate A pre-registration

See `gate_A_preregistration.md` in full. No absolute numeric threshold was invented. The decision procedure instead uses two evidence-derived comparators — a reaction-time-perturbation-equivalent effect (using the already-documented 0.7-1.5s literature range) and a numerical noise floor (timestep-halving) — applied across a pre-registered, three-band (easy/marginal/hopeless) scenario grid, with explicit rules for what counts as parameter-region-dependent (and therefore not a broad claim).

## 9. Profile survival decision

The original P1-P4 labels are **not** preserved automatically, per the task instruction. Renamed and re-evaluated against the reduced 4-parameter model:

- **R0 (reference, formerly P1)** — KEPT. Baseline: `a_coast≈0`, literature-anchored `t_delay`/`t_buildup`, no roll-off.
- **R1 (regen-onset, formerly P2)** — KEPT. The single profile that carries the non-monotonic near-stop roll-off feature needed to avoid a trivial time-shift result; has the best (though still MEDIUM-confidence) numeric anchor for `a_coast`.
- **R2 (delayed build-up, formerly P4)** — KEPT. Cleanest possible comparison: differs from R0 by exactly one parameter (`t_buildup`).
- **"P3, blended nonlinear" — RETIRED for Phase 1A.** Under the frozen open-loop step-command driver, a command-magnitude gain nonlinearity has no causal channel to any outcome (the command never dwells between 0 and `u_target`). A real blended architecture's actual distinguishing feature — a two-phase build-up shape — collapses into a variant of R2's `t_buildup`, not an independent mechanism. Keeping a "P3" label under these conditions would risk exactly what the task warned against: a profile that is a visually different curve without a genuine, evidenced causal mechanism reachable by the current design. It is deferred, not deleted, pending a closed-loop/correction-capable driver model in a later phase.

## Decisions

**A. Can Experiment A now be parameterised defensibly? CONDITIONAL**
Two of the four free parameters (`t_delay`, and `a_max` held-constant) now have real, traceable numeric anchors. `t_buildup` and `a_coast` have partial anchors (usable with explicit caveats about what they actually measure). `v_rolloff`'s numeric shape remains entirely COUNTERFACTUAL. A first run is defensible **only** if every COUNTERFACTUAL value is visibly labeled as such in any output, per `gate_A_preregistration.md` Step 5.3 — an unlabeled, fully-literature-anchored run is not yet possible.

**B. Is a proprietary OEM brake map required? NO**
Nothing in this pass required or attempted proprietary OEM data. The reduced 4-parameter model with generic, literature/dataset-documentation-anchored (or explicitly COUNTERFACTUAL) values is sufficient to instantiate R0/R1/R2, consistent with the charter's standing claim boundary.

**C. Minimum vehicle-response parameter set**
`a_coast`, `t_delay`, `t_buildup`, `v_rolloff` (free); `a_max` (held constant); jerk (monitored/derived only). See `vehicle_response_model.md`.

**D. Retained Phase-1A outcomes**
`collision` (derived), `TTC_min`, `stopping_margin`, `impact_speed`. `t_stabilise` and `N_correction` dropped from this experiment's scope.

**E. Gate-A decision rule status: PARTIALLY FROZEN**
The procedure (comparators, grid structure, robustness checks, parameter-region-dependence rule) is fully frozen in `gate_A_preregistration.md`. What remains open is not the *rule* but the *inputs* to it — specifically the exact scenario-tightness grid values, which depend on finalising `a_max`/`t_reaction` (already chosen) and cannot be fully instantiated as concrete numbers until implementation begins. The decision *logic* is frozen; the grid's literal numeric coordinates are not yet written down.

**F. Experiment A status: NEEDS MORE EVIDENCE**
Not READY TO IMPLEMENT: `v_rolloff`'s numeric shape and `Δt_transfer` remain COUNTERFACTUAL with no credible path to resolution found in this pass, and `t_buildup`/`a_coast` carry caveats that must be explicitly surfaced in any run. Not a KILL: the mechanism remains physically plausible, the parameter set is now genuinely minimal and identifiable, and three (not four) profiles are well-motivated. A first run is defensible only as an explicitly-labeled mixed literature-anchored/COUNTERFACTUAL prototype, consistent with Phase 0.1's original recommendation, now sharpened to identify exactly which two parameters (`v_rolloff` shape, `Δt_transfer`) still block a fully literature-anchored claim.

**G. Recommended next action**
1. Attempt direct file-level inspection of OpenLKA D004/D005 sample data (not just README) to upgrade `a_coast`'s confidence from MEDIUM to HIGH and potentially locate a numeric `v_rolloff` threshold in the raw regen-level field.
2. If `v_rolloff`'s numeric shape still cannot be resolved, proceed to a first Gate A run using R0 and R2 only (both fully literature-anchored except `t_buildup`'s human-inclusive caveat), holding R1 back until `v_rolloff` is resolved or explicitly and visibly run as COUNTERFACTUAL.
3. Only then implement the minimal longitudinal simulator (`project_charter.md` Section 10) under the frozen `control_input_definition.md` / `vehicle_response_model.md` / `metric_definitions.md` / `gate_A_preregistration.md` specification — still no CARLA, still no simulation code before this sequence completes.
