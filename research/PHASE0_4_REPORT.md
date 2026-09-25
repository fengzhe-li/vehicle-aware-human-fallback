# Phase 0.4 Report — Scientific Contribution Freeze + Experiment Architecture

## Scope

This is the final Phase-0 design pass. Its purpose is not to gather more evidence but to freeze the research architecture so implementation can begin immediately afterward if the design survives. No new literature search was conducted; every claim below is either inherited from Phase 0.1-0.3 or derived analytically (verified with `sympy`) in this pass.

## Key Phase 0.3 consequence, restated

`analytical_sanity_check.md` proved, not merely observed, that under the fixed open-loop driver and baseline withdrawal policy (W0), the R0-vs-R2 comparison's sign is a closed-form certainty: `d(D_stop)/dt_buildup > 0` for any realistic parameter range. A simulator reproducing this is validating itself, not discovering physics. This report's central task was determining what the project's *actual* first contribution is, given that constraint — not searching for more evidence to prop up the original framing.

## Task 1 — Experiment A reclassified as A0

**Accepted without reservation.** See `experiments/A0_analytical_baseline/spec.md`. A0's role is validation (numerical integration vs. closed form, collision/stopping-margin/`T_TOR_critical` calculation correctness, sensitivity-surface calibration) — explicitly not a discovery claim. Its claim boundary is enforced in writing: A0 may never be reported as "we found slower build-up is worse," only as "the simulator matches the proven algebra to within tolerance."

## Task 2-4 — First non-trivial experiment identified and verified non-trivial

**A1: withdrawal policy (W0 vs W1) × vehicle-response architecture (`a_coast = 0` vs `a_coast > 0`)** — the minimum 2×2 design, with W2 explicitly excluded (it would need an unconstrained blending-shape parameter with no evidence behind it, the same objection already accepted against unconstrained shape parameters throughout this project).

**Non-triviality was tested, not assumed**, by extending the A0 closed form with a withdrawal-coast phase and taking the mixed second derivative (`docs/CAUSAL_MODEL.md`, verified with `sympy`):

```
∂²D_stop / ∂a_coast ∂t_buildup = -t_reaction / 2     (nonzero whenever t_reaction > 0 — always)
```

This is a rigorous proof that withdrawal policy and vehicle-response architecture do **not** contribute additively — a genuine interaction exists, not reducible to a constant delay term, and it vanishes exactly (recovering A0's separable case) when `a_coast = 0`. This is the strongest possible answer to Task 4: not "this seems more interesting," but a nonzero cross-partial derivative computed from the model itself.

## Task 5 — `T_TOR_critical` formally frozen

See `metric_definitions.md`'s "Formal freeze" section. Two mathematically transparent criteria (collision-free boundary; a resolution-tied "robust boundary" criterion, not an invented safety number), a closed-form-first / bisection-fallback search procedure, monotonicity **proven** (not assumed) for the current linear-in-`TOR_lead_time` model, and explicit, non-arbitrary handling of both edge cases (no solution within range; every tested TOR safe).

## Task 6 — Claim ladder defined

See `docs/CLAIM_LADDER.md`. TYPE 1 (analytical) is already delivered. TYPE 2 (counterfactual simulation) will be available once A0 passes. TYPE 3 (empirically constrained) is currently supportable only for the subset of parameters carrying `EMPIRICAL_RANGE` status (Task 7) — notably not yet for `t_buildup` or `v_rolloff`. TYPE 4 (real-world production claims) remains explicitly out of reach and must not be implied by any future write-up.

## Task 7 — Parameter evidence policy frozen

See updated `research/parameter_provenance/phase1A_parameter_table.csv`. Every parameter now carries one of `CORE_EMPIRICAL` / `EMPIRICAL_RANGE` / `COUNTERFACTUAL_SENSITIVITY` / `VALIDATION_ONLY` / `EXCLUDE`. Notably: `a_coast` (both the regen-active and no-coast baseline values, revived specifically for A1) qualify as `EMPIRICAL_RANGE` — a real, if imperfect, dataset-documented anchor — while `t_buildup` and `v_rolloff` remain `COUNTERFACTUAL_SENSITIVITY`. This means **A1's actual treatment parameter (`a_coast`) is better anchored than A0's (`t_buildup`)** — a genuinely encouraging finding for A1's near-term viability that fell out of the evidence-policy exercise rather than being assumed going in.

## Task 8 — `v_rolloff` status decided

**Retained, `COUNTERFACTUAL_SENSITIVITY` only** (not dropped). Justification, per the task's explicit warning not to let it become the main mechanism merely because it was the only mathematically open parameter: it no longer has to carry that weight, because A1 (Task 2-4) is now the project's primary non-trivial mechanism, independently and more rigorously justified (a proven nonzero cross-partial, not "the one thing simulation didn't already answer"). `v_rolloff` remains available as a secondary sensitivity axis within A0/A1's R1-style extension, never as a conclusion-driver.

## Task 9-10 — Minimal simulator and test plan specified

See `docs/MINIMAL_SIMULATOR_SPEC.md` and `tests/TEST_PLAN.md`. State (`t, x_ego, v_ego, a_ego, gap, TTC`), inputs (TOR lead time, `t_reaction`, withdrawal policy, frozen human brake command, vehicle-response parameters), outputs (the four primary outcomes plus `T_TOR_critical`), integration method (piecewise-constant-acceleration, matching the existing minimal-model formula), `dt` requirements (1ms default, justified against the shortest evidenced timescale and against D005's own cautionary example of under-sampling), event handling (a-priori phase transitions vs. state-dependent crossings, both interpolated for sub-`dt` precision), and eight concrete pre-implementation tests, each with a numeric pass/fail criterion — including a programmatic check (test 8) that treatment changes never accidentally perturb the frozen human command, discharging a promise `control_input_definition.md` made but had not yet operationalised.

## Task 11 — Research architecture frozen

See `docs/RESEARCH_ARCHITECTURE_V1.md`. A0 (must-pass infrastructure) → A1 (first real contribution, ready to specify) → B (risk-state escalation, independently viable, reinforced by Phase 0.3's dataset forensics) → C (driver-vehicle mismatch, deferred, needs new data) → D (broader handover-policy work, explicitly not yet justified, contingent on A1's result) → E (coupled safety envelope, premature, contingent on everything above). No later branch is assumed to survive because an earlier one did.

## Decisions

**A. Original Experiment A status: ANALYTICAL BASELINE**
Reclassified as A0 per Task 1, accepted without reservation.

**B. First non-trivial experiment:**
**A1 — Withdrawal Policy × Vehicle-Response Architecture (W0 vs W1 × `a_coast`)**

**C. Is withdrawal-policy × vehicle-response interaction scientifically meaningful? YES**
Proven via a nonzero mixed second derivative of the extended closed form (`docs/CAUSAL_MODEL.md`), not assumed or asserted by proximity to the project's motivating narrative.

**D. `T_TOR_critical` status: FROZEN**
Two transparent criteria, proven monotonicity (for the current model), closed-form-first search procedure, explicit edge-case handling — see `metric_definitions.md`.

**E. Parameter evidence policy: FROZEN**
Every Phase-1 parameter (A0 and A1) classified; see `phase1A_parameter_table.csv`.

**F. Minimal simulator specification: READY**
State, inputs, outputs, integration method, `dt` requirements, event handling, and numerical tolerances all specified in `docs/MINIMAL_SIMULATOR_SPEC.md`.

**G. Research architecture: FROZEN**
`docs/RESEARCH_ARCHITECTURE_V1.md` — six branches (A0, A1, B, C, D, E), each with an independent status and survival condition.

**H. Implementation decision: CONDITIONAL GO**
Condition: A0 (`tests/TEST_PLAN.md` tests 1-7) must pass, and the frozen-command check (test 8) must pass across every A0 and A1 condition pair, before any A1 result is implemented or trusted. A1 results must be reported per `docs/CLAIM_LADDER.md` TYPE 2 (counterfactual sweep) until `a_coast`'s dataset-documented range is verified at the raw-file level (still outstanding per `raw_dataset_forensics.md`) or until it is otherwise upgraded — do not report a TYPE 3 claim prematurely.

**I. Exact next implementation task**
Implement the minimal longitudinal simulator exactly as specified in `docs/MINIMAL_SIMULATOR_SPEC.md`, then immediately run `tests/TEST_PLAN.md` items 1-8 against it — nothing else. Do not write A1-specific scenario-grid or comparator code until every A0 test (1-7) and the frozen-command check (8) pass. Only after that gate is cleared does A1 implementation begin, using the `a_coast` `EMPIRICAL_RANGE` values from `phase1A_parameter_table.csv` and the 2×2 design frozen in `docs/CAUSAL_MODEL.md`.
