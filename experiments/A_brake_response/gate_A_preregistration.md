# Gate A Pre-registration

**Status:** Written before any simulation result exists. Per the task instruction, if a scientifically justified absolute threshold cannot yet be set, this document defines the **decision procedure**, not an invented number.

## Why no absolute numeric threshold is set

An absolute threshold (e.g., "a 2-metre stopping-margin difference is material") would have to be justified by either a safety-consequence argument (how much margin difference changes real injury/fatality risk) or a statistical argument (how much exceeds measurement noise for a comparable real system) — this project has neither in hand yet, and inventing one to make Gate A runnable would violate the evidence-discipline rules already governing this project (`docs/DECISIONS.md` D007). Instead, Gate A uses **relative comparators** built entirely from evidence already gathered in `parameter_evidence_table.csv` and `phase1A_parameter_table.csv`.

## The decision procedure

### Step 1 — Compute profile effect sizes
For each retained outcome (`TTC_min`, `stopping_margin`, `impact_speed`; `collision` is derived) and each pair of profiles surviving Workstream 9 (see `PHASE0_2_REPORT.md`), compute the outcome difference at every point of the pre-registered scenario-tightness grid (Step 2).

### Step 2 — Pre-register the scenario-tightness grid before any run
A small grid of `(v0, TTC0, TOR)` combinations must be fixed *before* results are seen, spanning three qualitative bands:
- **easy**: large TTC margin relative to reaction time + full stopping time at `a_max` — outcome should be "no collision" for all profiles.
- **marginal**: TTC margin comparable to the total time budget under the baseline profile — this is the band where `experiment_A_review.md` (Q6) predicted transient-shape effects are most likely to be decisive.
- **hopeless**: TTC margin below what even instantaneous maximum braking could recover — outcome should be "collision" for all profiles.

The grid must include multiple points in the marginal band, not just one, and the bands must be defined by the physics (closed-form constant-`a_max` stopping distance vs. available distance) before any profile-specific simulation is run, so the bands cannot be chosen to flatter a desired result.

### Step 3 — Two comparators, not one invented number

**Comparator A — reaction-time-perturbation-equivalent effect.** Recompute each outcome with `t_reaction` shifted by the literature-derived bound already used to justify the Phase 1A choice (`control_input_definition.md`: 0.7 s "expected" vs 1.5 s "surprise", i.e. an 0.8 s perturbation). This uses real literature bounds, not an invented statistical quantity. A profile effect **smaller** than this reaction-time-equivalent effect, at a given grid point, should not be reported as "the vehicle-response mechanism matters more than known human-factors variability" at that point.

**Comparator B — numerical noise floor.** Halve the integration timestep `dt` and recompute. A profile effect smaller than the resulting change (a pure discretization artifact, not a physical effect) must not be reported as material anywhere.

### Step 4 — Classification rule
At each marginal-band grid point, for each outcome:
- **Meaningful**: profile effect exceeds both Comparator A and Comparator B.
- **Negligible**: profile effect is smaller than Comparator B (indistinguishable from numerical noise) — this is a clean kill signal for that grid point.
- **Ambiguous**: between Comparator B and Comparator A — real but smaller than known human-factors variability; log but do not claim as a headline result.

### Step 5 — Robustness checks that must survive before any KEEP claim
1. **Timestep-halving invariance** (Comparator B, above) — must pass everywhere a "meaningful" classification is claimed.
2. **Direction consistency** — the ranking between any two profiles (e.g., slower-build-up profile worse than baseline) must not flip sign across marginal-band grid points without a stated physical explanation. An unexplained sign flip invalidates a broad claim even if individual points show "meaningful" effects.
3. **Literature-anchored, not COUNTERFACTUAL-only** — if a "meaningful" effect requires pushing `phase1A_parameter_table.csv` parameters outside their literature-anchored ranges into COUNTERFACTUAL-only territory to appear at all, it must be reported as a COUNTERFACTUAL-parameter-region finding, not a literature-anchored Gate A result (this directly operationalises Phase 0.1's falsification criterion, `experiment_A_review.md` Q9).

### Step 6 — What parameter-region dependence invalidates a broad claim
A result is **parameter-region-dependent** (and must not be reported as a broad "vehicle-response architecture matters" claim) if either:
- "Meaningful" classifications occur at **fewer than half** of the pre-registered marginal-band grid points, with none in the easy/hopeless bands (expected, per Step 2, but must be stated as a scope limitation: "matters in marginal-recoverability scenarios," not "matters generally"), or
- "Meaningful" classifications require COUNTERFACTUAL-only parameter values (Step 5.3).

Either condition, on its own, downgrades the claim from "the mechanism materially shifts recovery safety" to "the mechanism could plausibly matter under specific, currently-unverified conditions" — this is not automatically a kill, but it must be stated as the honest scope of the finding.

## What would constitute a KILL of the vehicle-response branch (Gate A fail)
Per `experiment_A_review.md` Q9: if, across the full pre-registered grid (all three bands) and using literature-anchored parameter values only, no outcome for any surviving profile pair is classified "meaningful" anywhere — i.e., every grid point is "negligible" or "ambiguous" — the branch fails Gate A and should be killed or narrowed further per the charter's own Gate A wording.

## What this pre-registration deliberately does not do
It does not predict the result. It does not set a percentage or metre threshold pulled from intuition. It commits, in writing, before any simulation code exists, to a procedure that treats "smaller than known human-factors variability" and "smaller than numerical noise" as the two honest bars a claimed effect must clear — using only evidence already logged elsewhere in this repository.
