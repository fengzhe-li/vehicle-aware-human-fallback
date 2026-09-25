# Test Plan — Pre-Implementation Freeze

**Status:** Specification only, written before any simulator code exists, per the task instruction. Every test below must be implementable directly against `docs/MINIMAL_SIMULATOR_SPEC.md` and the closed forms in `analytical_sanity_check.md` / `docs/CAUSAL_MODEL.md` / `metric_definitions.md`. No test in this document may be satisfied by inspection or reasoning alone — each has a numeric pass/fail criterion.

## 1. Zero-delay constant-deceleration case matches closed form

Set `t_delay = 0`, `t_buildup = 0` (instantaneous full braking at `t_reaction`). Closed form reduces to the textbook identity `D_stop = v0²/(2·a_max) + v0·t1`. **Pass:** simulated `stopping_margin` matches this to within the tolerance in `docs/MINIMAL_SIMULATOR_SPEC.md` (0.1% relative, `dt=0.001s`). This is the simplest possible case and the first test that must pass before any other.

## 2. Positive delay increases stopping distance by the expected amount

Set `t_buildup = 0`, `t_delay = τ > 0`. Closed form reduces to `D_stop = v0²/(2·a_max) + v0·(t1+τ)` — a pure added-distance term of `v0·τ`. **Pass:** simulated `stopping_margin` for `t_delay=τ` minus simulated `stopping_margin` for `t_delay=0` equals `v0·τ` to within tolerance, for at least two distinct `τ` values spanning the `t_delay (friction baseline)` evidenced range (0.05s and 0.17s).

## 3. Linear build-up matches the analytical solution

Full `analytical_sanity_check.md` case: `t_delay = τ2 > 0`, `t_buildup = τ3 > 0`. **Pass:** simulated `D_stop` matches `v0²/(2·a_max) + v0·(t1+τ2+τ3/2) - a_max·τ3²/24` to within tolerance, for at least three `(τ2, τ3)` combinations, including one using the literature-anchored `t_delay` value and one using `t_buildup` well outside any previously-considered range (to catch errors that only appear far from the values used to develop the code).

## 4. Collision boundary behaves monotonically with obstacle distance

For a fixed profile and withdrawal policy, sweep `TOR_lead_time` (equivalently `x_hazard`) over a range spanning clearly-safe to clearly-unsafe. **Pass:** `stopping_margin(TOR_lead_time)` is monotonically non-decreasing across the swept range (per the linearity proof in `metric_definitions.md`'s `T_TOR_critical` freeze — this test exists specifically to catch an implementation bug that would violate a property already proven true of the model). A single non-monotonic step anywhere in the sweep is a fail, not a data point.

## 5. `T_TOR_critical` solver reproduces the analytical test case

For an R0/R2/W0 configuration (closed form available), run the simulator's numerical `T_TOR_critical` search procedure (bisection, per `metric_definitions.md`) and compare against the closed-form `T_TOR_critical = D_stop/v0`. **Pass:** agreement to within the same 0.1% relative tolerance, **and** the bisection search must converge within a pre-specified maximum iteration count (fail if it does not converge — a non-converging bisection on a proven-monotonic function indicates an implementation bug in the search, not a property of the underlying scenario).

## 6. `dt` convergence test

Run test 3's configuration at `dt ∈ {0.01, 0.005, 0.001, 0.0005}s`. **Pass:** the error between simulated and closed-form `D_stop` decreases as `dt` decreases, and the empirically observed convergence order (fit `log(error)` vs `log(dt)`) is reported, not assumed — this is what actually determines whether `docs/MINIMAL_SIMULATOR_SPEC.md`'s `dt=0.001s` default is adequate, superseding that document's provisional choice if the measured order says otherwise. This test also **is** `gate_A_preregistration.md`'s Comparator B in executable form — its output feeds directly into every later Gate A decision, not just A0 validation.

## 7. Identical profile produces identical output

Run the same profile, same scenario, same withdrawal policy twice, through two independently-constructed simulator invocations (not the same cached object). **Pass:** bit-identical (or floating-point-identical within machine epsilon) output. This catches hidden state leakage between runs — e.g., a `v_rolloff` or `a_coast` parameter accidentally persisting from a previous call — before it can silently corrupt an A1 comparison.

## 8. Treatment changes do not accidentally alter the frozen human command

For every pair of conditions compared in A0 (R0 vs R2) and A1 (W0 vs W1, `a_coast=0` vs `a_coast>0`), assert programmatically that `u_human_brake(t)` (the array of sampled command values, not just its symbolic definition) is **bit-identical** across the pair. **Pass:** exact equality check, not "close enough." This is the executable form of `control_input_definition.md`'s explicit invariant — per that document, this check "must be checked programmatically... not just asserted in text," and this is where that promise is discharged. A failure here invalidates any downstream A0/A1 result regardless of what the outcome metrics show, because it means the isolation the whole research programme depends on was silently broken.

## What this test plan does not cover

It does not test R1 (`v_rolloff` active, no closed form) against an analytical target, because none exists — R1's tests (once written, in a later phase) will necessarily be structural/property-based (e.g., "roll-off strictly reduces available deceleration relative to the same profile with `v_rolloff` disabled," a directional property, not a numeric target) rather than closed-form-matching tests like 1-6 above. This is a deliberate scope boundary, not an oversight: R1 is exactly the part of the model Phase 0.3/0.4 established has no closed form, so it cannot be validated the way A0's fully-analytical cases can.
