# Analytical Sanity Check

**Status:** Pure derivation. No simulation was run. Algebra verified symbolically with `sympy` (not by hand alone) before being written up here.

## Setup

Using the frozen baseline (`control_ownership_timeline.md` policy B, `control_input_definition.md`): `v(t) = v0` for `t < t1` (`t1 = t_reaction`), held by automation. At `t1`, the brake command begins. For the **R0/R2 profiles** (pure friction, no `v_rolloff`), `vehicle_response_model.md`'s piecewise-linear deceleration applies:

- Phase 0/1 (`0 ≤ t < t1 + t2`, where `t2 = t_delay`): `a = 0`, `v = v0`.
- Phase 2 (`t1+t2 ≤ t < t1+t2+t3`, where `t3 = t_buildup`): `a(τ) = -a_max·τ/t3` for `τ = t-(t1+t2) ∈ [0, t3]` (linear ramp).
- Phase 3 (`t ≥ t1+t2+t3`, until `v=0`): `a = -a_max` (constant).

## Closed-form stopping distance

Integrating each phase (verified with `sympy`, not just by hand):

```
D_stop = v0²/(2·a_max) + v0·(t1 + t2 + t3/2) - a_max·t3²/24
```

The first two terms are the familiar textbook "reaction-distance + braking-distance" identity. The **entire vehicle-response contribution reduces to two terms**: `v0·t3/2` (extra distance from the ramp taking time to reach full deceleration) minus `a_max·t3²/24` (a small correction from the ramp's average deceleration during build-up already being nonzero). For any realistic `t3` (well under `6·v0/a_max` — tens of seconds — for any plausible `v0`, `a_max`), this difference is **strictly positive and strictly increasing in `t3`**:

```
d(D_stop)/dt3 = v0/2 - a_max·t3/12   >   0   for realistic t3
d(D_stop)/dt1 = v0                     (exact, no approximation)
```

## Q: Which Phase-1A effects are already analytically guaranteed?

**The sign of the R0-vs-R2 comparison is a mathematical certainty, not an empirical finding.** R0 and R2 (`vehicle_response_model.md`, post-reformulation) differ by exactly one parameter, `t_buildup`. Since `d(D_stop)/dt3 > 0` for the entire realistic parameter range, **R2 (larger `t3`) will always produce a longer stopping distance than R0, for every scenario, before any simulation is run.** Running Experiment A cannot discover *whether* R2 is worse than R0 — that is guaranteed by the model's own algebra the moment `t_buildup` is chosen as the sole varying parameter between two profiles.

## Q: What would simulation add, then?

Three things, none of which the closed form above settles on its own:

1. **The magnitude** of `D_stop(R2) - D_stop(R0)` under literature-anchored (not invented) parameter values — currently blocked, since `t_buildup` itself was downgraded to COUNTERFACTUAL_ONLY in this pass (`phase1A_identifiability_final.csv`, Task 7 finding). The formula is ready; a trustworthy `t3` value is not.
2. **Whether that magnitude crosses a collision/no-collision boundary** in a *specific* scenario — this depends on how close the scenario's available stopping distance is to `D_stop(R0)` in the first place, which is exactly the "marginal band" already defined in `gate_A_preregistration.md`. The sign is free; the *boundary-crossing* is not, and is scenario-grid-dependent, not analytically obvious from the formula alone.
3. **The entire R1 comparison** (regen-onset, `v_rolloff` active). `v_rolloff` makes `a` depend on `v` as well as elapsed time near standstill, turning the phase-3 equation into a genuinely nonlinear ODE with no simple closed form derived here. Its effect is also *structurally* different from R0-vs-R2: it is concentrated specifically in the near-full-stop region of the trajectory, so unlike R0-vs-R2 (whose sign holds everywhere), R1's effect on `TTC_min`/`stopping_margin`/`impact_speed` is genuinely conditional on whether the scenario's hazard boundary happens to fall inside that near-stop region. **This is the one part of Experiment A whose sign is not already known before running it.**

## Q: Is the scientific value in the sign of the effect, or in quantifying the boundary shift?

For **R0-vs-R2**: unambiguously the latter. A future report that frames an R0-vs-R2 result as "we found that slower build-up is worse" would be reporting a tautology of the chosen model, not a discovery. The honest framing is "we quantified how much worse, under which literature-anchored parameter magnitudes, and whether that magnitude is large enough to move a realistic collision boundary" — which is exactly the framing `gate_A_preregistration.md` already committed to (comparators, not a bare sign check).

For **R1**: both the sign and the magnitude are open questions relative to this derivation, because the roll-off mechanism is nonlinear and state-dependent in a way the R0/R2 comparison is not.

## Q: Would interaction with TTC/TOR make the experiment non-trivial?

Yes — and this derivation shows precisely *how*. The guaranteed-sign part (`d(D_stop)/dt3 > 0`) says nothing about *when it matters*. Whether a given `(v0, TTC0, TOR)` combination sits close enough to the R0 stopping boundary for the algebraically-guaranteed R2 penalty to flip a `collision` outcome is a property of the **scenario grid**, not of the vehicle-response model alone — this is exactly why `gate_A_preregistration.md` pre-registers a three-band (easy/marginal/hopeless) grid rather than a single scenario. The non-trivial scientific content of Experiment A (for R0-vs-R2) lives entirely in *where the marginal band is* and *how wide the R0-vs-R2 gap is relative to it* — not in whether R2 is worse.

## Illustrative-only order-of-magnitude check (not a prediction)

Using only `t_delay`'s literature-anchored range width (0.05-0.17s, Paquette & Porter — the one number in this project's `t_delay`/`t_buildup` pair that survived adversarial re-check) as a stand-in scale, **purely to check whether the comparator logic in `gate_A_preregistration.md` is even the right order of magnitude**, not as a claim about `t_buildup`: at `v0 = 20 m/s`, a `t3` difference of `0.12s` (the width of the `t_delay` range, used only as an illustrative scale) produces `d(D_stop)/dt3 · Δt3 ≈ (v0/2)·0.12 ≈ 1.2m`, versus Gate A's Comparator A (reaction-time-equivalent effect) of `v0·Δt_reaction ≈ 20·0.8 = 16m`. At this illustrative scale, a vehicle-response-shape difference of a few tenths of a second is **an order of magnitude smaller** than known human-reaction-time variability. This does not predict Experiment A's actual result (the real `t_buildup` difference between profiles is unknown — see Task 7), but it does confirm that Gate A's comparator-based decision procedure (rather than an absolute threshold) is calibrated to the right scale: a genuinely material vehicle-response effect needs to be substantially larger than a few tenths of a second in `t_buildup` difference to compete with reaction-time variability, which is a useful, checkable expectation for whoever eventually anchors `t_buildup`.
