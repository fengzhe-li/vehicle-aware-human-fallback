# Phase 0.1 Report — Systematic Evidence Audit + Gap Mapping

## Scope and method

This report covers Workstreams A-F requested for Phase 0.1: literature matrix expansion, a novelty/gap audit, a dataset audit (with direct verification of dataset pages, not abstract-level assumption), an identifiability audit, a parameter-provenance table, and an adversarial review of `experiment_A_spec.md`. No simulator code was written and no CARLA work was done, per the standing project constraints.

The literature search used ~15 distinct web/academic queries across the six required themes (A1-A6). This is a **bounded plausibility check**, not a systematic database review (no Scopus/Web of Science protocol, no citation chaining, no non-English literature). That limitation is carried into every conclusion below rather than hidden.

Five existing datasets were re-verified by fetching their actual pages (not just trusting the prior abstract-level inventory): `ADAS-TO`, `OpenLKA EV Dataset`, `OpenLKA Acceleration Dataset`, `TD2D`, and the `TU Delft takeover dataset`. All five are confirmed real and accessible; several important field-level caveats were found (see dataset audit summary below).

## Summary of findings by workstream

### A — Literature matrix
Nine new entries (L007-L014) were added to the six already present (L001-L006). Key new findings:
- A direct empirical anchor for post-takeover **stabilisation time** (~8-10 s driving-metric recovery; L009) — resolves one of the two outstanding metric-definition items in `PHASE0_CHECKLIST.md`.
- Strong **real-world (non-takeover) evidence** that distinct control architectures produce measurably different deceleration/jerk signatures, independent of propulsion label (L011, IIHS AEB study) — directly supports Decision D002 ("architecture, not label").
- A naturalistic-driving finding that directly **challenges the fixed-reaction-time simplifying assumption** (L014) — logged as a named Phase-1 limitation, not a reason to abandon the simplification for a first mechanism-isolation test.
- Real evidence that EV acceleration authority already shifts **traffic-conflict-level** risk indicators (L013) — motivating but not equivalent to the project's specific human-fallback-margin framing.

### B — Gap / novelty audit
See `research/literature_matrix/gap_audit.md` in full. Verdict: **MODERATE GAP**. The physical premise (architectures differ measurably; architecture changes emergency-braking timing in at least one paradigm — L004, L011) is well established and must not be claimed as novel. What was not found in this bounded search is a study that manipulates transient vehicle longitudinal-response architecture as an independent variable **inside a controlled ADS TOR/handover paradigm**, isolated from maximum deceleration, feeding into TTC/stopping-margin/impact-speed outcomes. The closest broad framework (McDonald et al. 2019, L010) treats vehicle response as part of the fixed plant, not as the object of study.

### C — Dataset audit
See updated `research/data_matrix/dataset_inventory.csv`. All five datasets exist and are (or plausibly are) accessible. Important corrections to the prior inventory:
- **ADAS-TO's brake/accelerator fields are binary press flags, not continuous pedal position/force.** This blocks fitting a continuous transient B_map shape from that dataset alone; it remains usable for continuous-acceleration-trace parameter bounding and cross-model sanity checks (`USABLE_PARAMETER_SOURCE`), not as a `USABLE_CORE` source.
- **TD2D** is confirmed publicly downloadable (Zenodo, CSV/MP4) but is an L2, distraction-focused paradigm with no vehicle-response manipulation — `USABLE_VALIDATION`, not core.
- **TU Delft dataset** confirmed: 9 scenarios manipulate traffic density x cognitive workload only; vehicle response is not varied across conditions — `USABLE_VALIDATION`, not usable for the vehicle-response mechanism branch itself.
- **OpenLKA EV Dataset**: exact license terms and continuous-vs-binary status of the brake/pedal fields were not resolved from the repository page alone — `ACCESS_UNCERTAIN`, flagged for direct file inspection before use.
- **OpenLKA Acceleration Dataset**: confirmed MIT-licensed, directly downloadable, with jerk as an explicit field — good parameter source for Phase 1B (`USABLE_PARAMETER_SOURCE`).

No dataset in the inventory is a controlled experiment that varies vehicle longitudinal-response architecture inside a TOR paradigm — this is expected, since that is exactly the gap the project's own simulation work is meant to fill, not evidence against feasibility.

### D — Identifiability audit
See updated `research/identifiability/identifiability_matrix.csv`. **No WEC-style fatal blocker was found.** Every quantity essential to the mother question is either directly observable in at least one source, or admits a defensible parameterised/COUNTERFACTUAL treatment that does not require proprietary OEM data. The weakest-identified links are:
- Emergency-range jerk magnitude for human-driven (not AEB-controlled) braking — no usable numeric anchor found in this pass.
- Numeric regenerative-deceleration magnitudes (L006's exact figures are paywalled; not retrieved) and deceleration build-up time — currently COUNTERFACTUAL placeholders in `experiment_A_spec.md`.
These block a *literature-anchored numeric* Gate A run today, but do not block the mechanism-isolation logic of the experiment, which can proceed as an explicitly-labeled COUNTERFACTUAL prototype first (see Workstream F).

### E — Parameter provenance
See new `research/parameter_provenance/parameter_evidence_table.csv`. Of the parameters most critical to Experiment A, `a_max_emergency` and the TOR/reaction-time ranges are reasonably well constrained (MEDIUM-HIGH confidence); `deceleration_buildup_time`, `jerk_emergency_range`, and `regen_deceleration_range` are explicitly marked **not safe to use numerically in Phase 1** pending full-text/file-level verification. This is the single most important actionable finding of Workstream E: the project currently has a well-motivated *qualitative* mechanism but an under-anchored *quantitative* one for exactly the profile-shape parameters Experiment A most needs.

### F — Experiment A challenge
See new `experiments/A_brake_response/experiment_A_review.md` in full. Two findings materially affect implementation readiness:
1. The driver model's loop structure (open-loop vs closed-loop) is **not specified** in the current spec, and this choice determines whether the experiment cleanly isolates the vehicle-response mechanism or confounds it with driver-feedback effects.
2. There is a real risk that, if all four profiles differ only in a simple monotonic ramp-to-a_max, the result collapses to a trivial "effective delay" restatement rather than genuine evidence of an architecture-specific mechanism — mitigated by ensuring at least one profile (P2, via near-stop regen roll-off) introduces a non-monotonic feature.

## Decisions

**A. Research question: KEEP**
The mother question is appropriately conditional ("under what combinations... does fallback remain recoverable") and is not falsified by this audit. It should remain the long-run organizing question; near-term empirical work should proceed only on the narrower branches below, consistent with the charter's own gated design.

**B. Vehicle-response branch: NARROW**
The qualitative mechanism is supported (L004, L011) and is physically plausible (see experiment_A_review Q4-Q7). Narrow the near-term scope to: longitudinal-only, braking-dominant hazard scenarios; an explicitly open-loop Phase-1A driver model; a pre-registered scenario-tightness grid; and a first run explicitly labeled COUNTERFACTUAL/internal-validity-only, kept separate from any later literature-anchored numeric claim.

**C. Driver-internal-model branch: DEFER**
Consistent with the existing charter decision (D003/D004). L012 strengthens the case that this branch has real mechanism potential later (adaptation is magnitude-dependent, with after-effects for large changes) but no dataset in the inventory records driver EV/ICE familiarity, so a direct ICE-vs-EV prior claim remains untestable with current data. Continue to defer to Phase 2.

**D. Risk-state-escalation branch: NARROW**
The charter's existing scoping (same lower-risk initial state, same-duration acceleration command, then hazard) already avoids the main trap (comparing vehicles that start braking from the same speed). L013 provides real motivating evidence but at the traffic-conflict level, not the human-fallback-margin level the project targets — narrow the outcome measurement to explicit margin-consumption-rate metrics (not general conflict-frequency framing) and do not cite L013 as direct support beyond motivation.

**E. Unified Human Fallback Safety Envelope: PREMATURE**
Depends on branches B-D surviving their individual gates first, exactly as the charter's own Section 4.4 / Gate D already specify. Nothing in this audit changes that sequencing.

**F. Data feasibility: CONDITIONAL PASS**
No dataset directly supplies a controlled, vehicle-response-architecture-varied TOR experiment (expected — that's the simulation's job), but sufficient qualitative and partial-quantitative evidence exists to parameterise a first COUNTERFACTUAL-labeled Experiment A prototype. Full numeric confidence for `deceleration_buildup_time`, `jerk_emergency_range`, and `regen_deceleration_range` requires further retrieval work (L006 full text; D004/D005 file-level inspection) before a literature-anchored (non-counterfactual) Gate A run can be reported.

**G. Identifiability: CONDITIONAL PASS**
No fatal blocker to the mother question was found. Conditional because several Experiment-A-critical shape parameters are currently unanchored and must either be resolved or explicitly and visibly treated as COUNTERFACTUAL in any reported result.

**H. Recommended next action**
Do not implement the full numeric P1-P4 simulator yet. In order:
1. Resolve the open-loop/closed-loop driver-model decision and pre-register the scenario-tightness grid and practical-effect thresholds (per `experiment_A_review.md` Q2, Q10, Q11).
2. Attempt to retrieve L006's full text and inspect D004/D005 at the file level to anchor build-up-time, emergency-jerk, and regen-magnitude numbers; where this fails, proceed with an explicitly COUNTERFACTUAL-labeled first prototype run kept separate from any literature-anchored claim.
3. Freeze the `t_stabilise` operational definition using L009's ~8-10 s anchor as a plausibility check, and freeze an `N_correction` threshold definition (informed by L008's metrics review).
4. Only then implement the minimal longitudinal simulator described in `project_charter.md` Section 10, under the narrowed, pre-registered Experiment A protocol.
