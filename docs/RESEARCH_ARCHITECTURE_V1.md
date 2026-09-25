# Research Architecture V1

> **AUDIT NOTICE (2026-09-22, Phase R0):** Superseded for current structure by `docs/RESEARCH_ARCHITECTURE_V2.md`. Kept unchanged below as the historical Phase 0 architecture. Current status of every branch: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Note that V1's branch E ("coupled Human Fallback Safety Envelope — PREMATURE") is still the correct status: the synthesis is NOT STARTED / GATED.

**Status:** Frozen at the end of Phase 0. This document is the single reference for how the branches relate, their current status, and what would kill each one — later phases update the *status* column, not this document's structure, unless a branch itself needs re-architecting.

## Principle

Each branch below has an independent survival condition. A branch does not inherit justification from the branches before it, and later branches are not assumed necessary just because earlier ones survived — per this phase's explicit instruction, "do not force later branches to survive."

## A0 — Analytical Baseline / Simulator Validation

**What it is:** the original "Experiment A" (`experiments/A_brake_response/`), reclassified (`experiments/A0_analytical_baseline/spec.md`). R0 vs R2 under withdrawal policy W0.

**Role:** infrastructure, not a research contribution. Validates the simulator against closed-form dynamics (`analytical_sanity_check.md`, `tests/TEST_PLAN.md` tests 1-7) before any A1 result is trusted.

**Status: MUST PASS before anything downstream is implemented.** Not a Gate in the hypothesis-testing sense — there is no "KEEP/KILL" decision for A0, only "does the code match the proven algebra." If it does not, that is a simulator bug, and everything downstream is blocked until fixed.

## A1 — First genuinely research-relevant experiment

**What it is:** withdrawal policy (W0 vs W1) × vehicle-response architecture (`a_coast = 0` vs `a_coast > 0`), per `docs/CAUSAL_MODEL.md`. The minimum 2×2 design that exercises the proven nonzero interaction term (`∂²D_stop/∂a_coast∂t3 = -t1/2`).

**Role:** the project's actual first research contribution. Tests whether the safety consequence of an automation-to-human withdrawal policy depends on vehicle transient-response architecture — directly answering the mother question's "handover conditions × vehicle dynamics" clause for the first time with a result that is not already known before running it.

**Status: READY TO SPECIFY, NOT YET READY TO IMPLEMENT.** Blocked on the same implementation sequence as A0 (A0 must pass first, since A1 shares its codebase and metric definitions) plus `docs/MINIMAL_SIMULATOR_SPEC.md`/`tests/TEST_PLAN.md` items 8 (frozen human command) being in place before any A1 comparison is trustworthy.

**Kill/narrow condition:** if, once implemented, the measured interaction effect (per `gate_A_preregistration.md`-style comparators, extended to the withdrawal-policy axis) is smaller than the numerical noise floor or the reaction-time-equivalent comparator across the full pre-registered scenario grid — i.e., the proven-nonzero *algebraic* interaction turns out to be numerically negligible in *magnitude* under literature-anchored `a_coast` ranges — A1 should be narrowed to a COUNTERFACTUAL-only sensitivity finding (`docs/CLAIM_LADDER.md` TYPE 2), not reported as a TYPE 3 empirically-constrained result.

## B — Risk-state escalation

**What it is:** unchanged from the original charter (Section 4, Gate B) and Phase 0.1's decision (NARROW) — acceleration-authority effects on time-to-hazardous-kinetic-state, using D005 (OpenLKA Acceleration Dataset) as the parameter source.

**Status: UNCHANGED, still NARROW.** Phase 0.3's raw-data forensics *reinforced* this branch's data foundation (D005 fully verified as a real, accessible, accelerator-only dataset well-suited to exactly this branch — see `raw_dataset_forensics.md`) while simultaneously confirming it has **zero relevance to A0/A1** (no brake channel at all). This is good news for B specifically: its dedicated dataset is real and independently usable, uncontaminated by A0/A1's unresolved braking parameters.

**Survival condition:** unchanged from `project_charter.md` Gate B — must be tested via the "same lower-risk initial state, same-duration acceleration command, then hazard" design (not a fixed-speed braking comparison), independently of whether A1 survives.

## C — Driver-vehicle internal-model mismatch

**What it is:** unchanged from the charter and Phase 0.1's decision (DEFER). `M_mismatch = 0` remains fixed through A0 and A1.

**Status: UNCHANGED, still DEFER.** Nothing in Phase 0.2-0.4 required revisiting this. L012 (Phase 0.1) remains the best available anchor for how mismatch effects should eventually be parameterised, whenever this branch reopens.

**Survival condition:** unchanged — Gate C (`project_charter.md`), and no dataset in `dataset_inventory.csv` currently records driver EV/ICE familiarity, so this branch cannot proceed empirically without new data collection, not just more analysis of existing sources.

## D — Broader handover-policy analysis, if still justified

**What it is:** **conditional, not committed.** If A1 (the minimum W0-vs-W1 comparison) finds a material interaction, this branch would extend the design — e.g., adding W2 (staged/overlap withdrawal, deferred from `docs/CAUSAL_MODEL.md`'s Task 2 for exactly this reason), or testing whether `t_reaction` itself depends on `TOR_lead_time` (flagged as a monotonicity-breaking possibility in `metric_definitions.md`'s `T_TOR_critical` freeze).

**Status: NOT YET JUSTIFIED — explicitly deferred pending A1's result, not assumed.** Per this phase's instruction to prefer a smaller defensible programme, D does not get written up further until A1 either (a) finds a material effect worth generalising, or (b) fails to, in which case D should likely not be pursued at all rather than being retried with a bigger design.

## E — Possible coupled Human Fallback Safety Envelope

**What it is:** unchanged from the charter (Section 4.4) and Phase 0.1's decision (PREMATURE).

**Status: UNCHANGED, still PREMATURE.** Depends on A1 (and, contingently, B, C, D) surviving their own gates first. Nothing in Phase 0.2-0.4 changes this sequencing — if anything, A0's reclassification and A1's more precisely-scoped design make it clearer than before how much would still need to survive before E is justified.

## Summary table

| branch | status | depends on | kill/narrow condition |
|---|---|---|---|
| A0 | must pass (infrastructure) | — | simulator fails to match closed form |
| A1 | ready to specify, not yet to implement | A0 passing | interaction magnitude negligible under literature-anchored ranges |
| B | NARROW (unchanged) | — (independent dataset) | fails charter's existing Gate B design |
| C | DEFER (unchanged) | new driver-familiarity data | no data source exists yet |
| D | not yet justified | A1's result | A1 finds no material effect |
| E | PREMATURE (unchanged) | A1, B, C, D | any of A1/B/C/D fails its own gate |
