# A0 — Analytical Baseline and Simulator Validation

**Status:** Reclassification of the original "Experiment A" (`experiments/A_brake_response/`). This document does not implement anything; it defines what A0 is *for* once implementation begins.

## Why the reclassification is accepted, not just applied

`analytical_sanity_check.md` (Phase 0.3) derived, and verified with `sympy`, that under the frozen open-loop driver and baseline handover policy (W0 — `control_ownership_timeline.md`), the R0-vs-R2 comparison's sign is a closed-form certainty:

```
D_stop = v0²/(2·a_max) + v0·(t1+t2+t3/2) - a_max·t3²/24
d(D_stop)/dt3 = v0/2 - a_max·t3/12 > 0   for any realistic t3
```

A simulator that reproduces "longer `t_buildup` → longer stopping distance" is reproducing algebra, not discovering physics. Presenting that reproduction as the project's central finding would misattribute a property of the chosen model to an empirical result about vehicles. The reclassification is **accepted without reservation** — there is no rigorous argument for treating R0-vs-R2 under W0 as a discovery-oriented experiment once its sign is already proven.

## Role of A0

A0 is **infrastructure**, not a research contribution. Its outputs validate that the eventual simulator is correct, not that vehicle-response architecture matters.

1. **Validate numerical integration against closed-form dynamics.** For the piecewise-linear R0/R2 profiles under W0, the simulator's numerically-integrated `stopping_margin`, `TTC_min`, and `impact_speed` must match the closed-form `D_stop` (and its derivatives, `TTC(t)`, `v(t)`) to within a stated numerical tolerance (see `docs/MINIMAL_SIMULATOR_SPEC.md`).
2. **Verify collision / stopping-margin calculations.** `metric_definitions.md`'s sign convention and collision-boundary behaviour (continues the counterfactual trajectory past `x_hazard`) must be checked against hand-computable cases.
3. **Verify `T_TOR_critical` calculation.** The closed-form `T_TOR_critical = D_stop/v0` (`metric_definitions.md`) must match whatever numerical root-finding procedure the simulator uses, for the same R0/R2 cases.
4. **Provide transparent sensitivity baselines.** Running R0 vs R2 across the scenario grid produces a fully-predicted sensitivity surface (the analytical formula predicts it exactly) — useful as a calibration reference for later experiments (A1 and beyond), not as a scientific result in itself.
5. **Confirm the simulator reproduces analytically known behaviour** before any experiment whose result is *not* analytically known (A1) is allowed to run on the same codebase.

## Claim boundary — enforced, not just stated

A0 **must not** be reported, in any future paper/thesis section, as:
> "We found that a slower vehicle-response build-up increases stopping distance and reduces safety margin."

That sentence describes a mathematical property of the model (`analytical_sanity_check.md`), proven before any code existed. A0's only legitimate reportable claim is of the form:
> "The simulator's numerical output matches the closed-form solution to within [tolerance] across [tested range], validating the integration and metric implementations used in later experiments."

## Scope

- **In scope:** R0, R2 (pure-friction profiles differing only in `t_buildup`), under baseline withdrawal policy W0 only.
- **Out of scope:** R1 (regen-onset, `v_rolloff` active) — its governing equation is nonlinear and state-dependent near standstill with no closed form derived (`analytical_sanity_check.md`), so it cannot serve as a *validation* target the way R0/R2 can. R1 belongs to the genuinely open research question, not the validation suite.
- **Out of scope:** any withdrawal policy other than W0 — those belong to A1 (see `docs/CAUSAL_MODEL.md`, `docs/RESEARCH_ARCHITECTURE_V1.md`).

## Relationship to prior Phase-0 documents

A0 inherits, unchanged: `control_ownership_timeline.md` (policy W0 baseline), `control_input_definition.md`, `vehicle_response_model.md`'s R0/R2 definitions, `metric_definitions.md`, `gate_A_preregistration.md`'s numerical-noise-floor comparator (repurposed here as a validation tolerance rather than a Gate A decision input — A0 has no "Gate," since it is not testing a hypothesis). `experiments/A_brake_response/` remains the physical location of these inherited documents; A0 is a role assigned to that existing work, not a rewrite of it.
