# Causal Model — Phase 0.4

**Status:** Design document. Fixes the causal structure and variable roles for the research programme going forward, and determines (Task 2) the minimum withdrawal-policy comparison and (Task 4) whether it is genuinely non-trivial, before any simulator code exists.

## Task 2 — Minimum withdrawal-policy comparison

Three candidate policies were given: **W0** (automation maintains longitudinal control until first effective human brake input — this is exactly the baseline already frozen as `control_ownership_timeline.md` policy B, and is A0's setting), **W1** (automation withdraws longitudinal propulsion/control immediately at TOR), **W2** (staged/overlap withdrawal).

**Chosen: W0 vs W1 only. W2 is excluded from the first non-trivial experiment.**

Justification: W2 requires a withdrawal-blending-shape free parameter (how the transition from automation to zero-command is shaped over time) with no evidence behind it anywhere in this project's searches — the same objection already raised and accepted against an unconstrained "brake gain" curve (`vehicle_response_model.md`, Phase 0.2) and against W2 itself in `control_ownership_timeline.md` (Phase 0.3, "Others may become later sensitivity tests"). Adding it now would violate this phase's own instruction to prefer a smaller defensible programme over a speculative one. W0 vs W1 is a clean, binary, already-partially-specified contrast: W0 is already fully defined (A0's baseline); W1 only requires specifying automation's command during `[0, t1)` as an immediate drop to zero/neutral, reopening exactly the "uncommanded coast" mechanism `control_ownership_timeline.md` already described (as the *deferred* case) and `vehicle_response_model.md` retired (as *not applicable to W0*). No new unconstrained parameter is introduced — `a_coast` (retired under W0) is un-retired under W1, in exactly its Phase 0.2 form, now correctly scoped.

## Task 3 — Causal structure

```
scenario state (v0, TTC0/hazard distance, road friction)
        |
        v
TOR issuance (t=0, T_authority — nominal)
        |
        v
automation withdrawal policy (W0 or W1)  ---->  vehicle longitudinal state evolution during [0, t_reaction)
        |                                              |
        |                                              v
        |                                       v(t_reaction)  [= v0 under W0; architecture- and
        |                                       (state handed to the human-control phase)  W1-duration-
        |                                                                                    dependent under W1]
        v
human reaction time (t_reaction, fixed) -> human effective brake input (u_human_brake step, identical
        |                                    command trajectory across all compared conditions)
        v
vehicle transient response (t_delay, t_buildup, v_rolloff, a_max — vehicle_response_model.md)
        |
        v
recovery outcome (collision, TTC_min, stopping_margin, impact_speed, T_TOR_critical)
```

### Variable roles

| variable | role | notes |
|---|---|---|
| `v0`, `TTC0`/hazard distance, road friction | **CONTROLLED** | Fixed within any single matched comparison; varied only across the pre-registered scenario grid (`gate_A_preregistration.md`-style grid, extended for A1). |
| TOR issuance time (`t=0`), `t_reaction` | **CONTROLLED** | Fixed per `control_input_definition.md`; identical across every compared condition. |
| `u_human_brake(t)` (the human command trajectory) | **CONTROLLED** (by design, not a variable under study) | Frozen identical across all conditions per `control_input_definition.md`'s explicit invariant — this must remain true when withdrawal policy is added as a new axis, or the isolation the whole research programme depends on breaks. |
| **withdrawal policy (W0 vs W1)** | **TREATMENT (axis 1)** | The first of the two manipulated variables in A1. |
| **vehicle-response profile (architecture parameters: `t_delay`, `t_buildup`, `a_coast`, `v_rolloff`)** | **TREATMENT (axis 2) in A0; TREATMENT / EFFECT MODIFIER (jointly with withdrawal policy) in A1** | See discussion below — its causal role is not fixed across experiments. |
| `v(t)` for `t ∈ [0, t_reaction)` | **MEDIATOR** | Sits on the causal path from (withdrawal policy × vehicle response) to the recovery outcome. This is the variable through which the Task 4 interaction is transmitted — see the closed form below. |
| `a_max` (held constant across profiles) | **NUISANCE / SENSITIVITY** | Not itself a treatment in A0 or A1's primary comparison; varied only as a later robustness/sensitivity check, per its existing role in `vehicle_response_model.md`. |
| `collision`, `TTC_min`, `stopping_margin`, `impact_speed`, `T_TOR_critical` | **OUTCOME** | Unchanged definitions (`metric_definitions.md`), computed identically regardless of which treatment axes are active. |

### Is vehicle response a treatment, an effect modifier, or both?

**Both, depending on the experiment — and this is not a loose statement; Task 4's derivation makes it precise.**

- **In A0** (withdrawal policy fixed at W0), vehicle-response architecture (specifically `t_buildup`) is a **direct treatment**: its effect on `D_stop` is additive/separable and analytically known (`analytical_sanity_check.md`).
- **In A1** (withdrawal policy varies), vehicle-response architecture (specifically `a_coast`, active only under W1) acts as an **effect modifier** of the withdrawal-policy treatment: the derivation below shows the *size* of withdrawal policy's effect on the outcome depends on which vehicle-response profile is paired with it, and vice versa — this is precisely what "effect modifier" means, and precisely what distinguishes A1 from a second copy of A0 with a relabeled axis.

## Task 4 — Is the withdrawal-policy × vehicle-response interaction non-trivial?

**Method: extend the A0 closed form with a withdrawal-coast phase, then test for separability directly — not by argument, by taking the mixed partial derivative.** Verified symbolically with `sympy` before being written here.

Let `a_coast ≥ 0` be the (architecture-dependent) deceleration active during `[0, t1)` under W1 (`a_coast = 0` recovers W0 exactly — checked explicitly below). Then:

```
v1 = v0 - a_coast·t1                         (speed at t_reaction, no longer architecture-independent under W1)
x1 = v0·t1 - a_coast·t1²/2                   (displacement during the withdrawal-coast phase)
D_stop(W1) = x1 + v1²/(2·a_max) + v1·(t2+t3/2) - a_max·t3²/24
```

Expanding (sympy):

```
D_stop(W1) = v0²/(2a_max) + t1·v0 + t2·v0 + t3·v0/2 - a_max·t3²/24
             - a_coast·t1·v0/a_max - a_coast·t1·t2 - a_coast·t1·t3/2 - a_coast·t1²/2 + a_coast²·t1²/(2a_max)
```

**Sanity check (must recover A0's result):** setting `a_coast = 0` gives exactly `D_stop(W1) = v0²/(2a_max) + v0·(t1+t2+t3/2) - a_max·t3²/24` — identical to `analytical_sanity_check.md`'s `D_stop`. Confirmed by `sympy.simplify`.

**Separability test:** if withdrawal policy and vehicle response contributed independently, `∂²D_stop(W1) / ∂a_coast ∂t3` would be zero (no cross term). It is not:

```
∂²D_stop(W1) / ∂a_coast∂t3 = -t1/2     (nonzero whenever t1 > 0, i.e. always)
∂²D_stop(W1) / ∂t1∂t3      = -a_coast/2  (nonzero whenever a_coast > 0, i.e. whenever the profile has any withdrawal-coast response at all)
```

**This is the rigorous answer to Task 4: the interaction is genuinely non-trivial, not reducible to a constant additive delay term.** Two concrete, physically interpretable consequences:
1. The size of the architecture effect (`t_buildup`'s contribution) is *scaled by reaction time* under W1 in a way it is not under W0 — a longer `t_reaction` amplifies how much the withdrawal-coast/architecture interaction matters, because the cross-partial is proportional to `t1`.
2. The interaction **vanishes exactly** when `a_coast = 0` (a pure-freewheel/no-coast architecture under W1 reduces to the same separable structure as W0) — so the non-triviality is conditional on comparing at least one profile with genuine coast/regen behaviour against one without, under W1. A comparison using only pure-friction profiles (`a_coast = 0` for all of them) would find no interaction, correctly, because none exists for that profile pair — this is not a design flaw, it is the model correctly reporting a null result where one is expected.

**This directly determines A1's minimum design**: a 2×2 comparison — {W0, W1} × {a friction profile with `a_coast=0`, a regen profile with `a_coast>0`} — is the smallest design that can exercise the nonzero cross term. A 2×3 (adding W2) or a design using only `a_coast=0` profiles would either add an unjustified free parameter or fail to exercise the interaction at all.

**Which outcomes does this reach?** `stopping_margin` and `impact_speed` inherit the interaction directly (both are functions of `D_stop`/`v1` under the R0/R2-style closed form, extended above). `TTC_min` inherits it because `TTC(t) = (x_hazard - x(t))/v(t)` and both `x(t)` and `v(t)` during `[0,t1)` are now architecture-dependent under W1. `T_TOR_critical = D_stop(W1)/v0` inherits it directly from the closed form above — so the minimum-safe-handover-time boundary itself shifts *jointly* with withdrawal policy and architecture, not just with either alone. None of the four primary outcomes are exempt.

## Summary

The withdrawal-policy × vehicle-response interaction is accepted as the project's first genuinely non-trivial experiment (A1) on the strength of a verified, nonzero mixed second derivative — not on the grounds that it "sounds closer to the project motivation." Per the task's explicit instruction, if this test had come back separable (cross-partial = 0), it would have been reported as trivial and not preserved.
