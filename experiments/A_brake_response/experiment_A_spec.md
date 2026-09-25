# Experiment A Specification — Vehicle Braking-Response Mechanism

## Status
**Pre-registration draft / Phase 0.3. NOT YET READY TO IMPLEMENT — see `research/PHASE0_3_REPORT.md`.**
No result should be interpreted before parameter ranges and metric definitions are frozen.

**Phase 0.3 update (supersedes Phase 0.2 where they conflict):**
- `control_ownership_timeline.md` — **new**: defines `u_automation(t)`, `w_authority(t)`, and the chosen baseline handover policy (B: automation holds `v0` until `t_reaction`). Resolves the L3 category error in Phase 0.2's "accelerator release" framing.
- `control_input_definition.md` — revised: `u_human_accel(t) ≡ 0` (never engaged, per L3 framing); `Δt_transfer` retired; single brake-step command at `t_reaction`.
- `vehicle_response_model.md` — revised: `a_coast` retired (its role absorbed into a regen-flavored `t_delay`); **3** free parameters (`t_delay`, `t_buildup`, `v_rolloff`) + held-constant `a_max`; `t_buildup`'s numeric anchor downgraded to COUNTERFACTUAL after adversarial re-check; `v_rolloff` retained only as a COUNTERFACTUAL sensitivity axis (Task 9, Option B).
- `analytical_sanity_check.md` — **new**: closed-form derivation showing the R0-vs-R2 comparison's *sign* is analytically guaranteed, not an empirical finding; R1 (`v_rolloff`) is the only comparison whose sign is genuinely open.
- `metric_definitions.md` — adds `T_TOR_critical` as a secondary derived outcome, directly connected to the closed-form result above.
- `research/data_matrix/raw_dataset_forensics.md` — real byte-level inspection of D004/D005 (D001 gated, schema-level only), correcting several README-level claims (D005's sampling rate, D001's access method and mixed sampling rate).
- `research/parameter_provenance/phase1A_identifiability_final.csv` — per-parameter DIRECTLY_ESTIMABLE / DERIVABLE_WITH_ASSUMPTIONS / LITERATURE_ONLY / COUNTERFACTUAL_ONLY / NOT_IDENTIFIABLE status.
- `research/parameter_provenance/response_episode_definition.md` — **new**: how `t_delay`/`t_buildup`/roll-off would be measured from raw D004 data (not yet executed at scale).

## Research question

> Holding the driver, hazard, initial vehicle state and nominal maximum braking capability constant, can differences in the transient braking-response mapping materially change time-critical human-fallback outcomes?

## Why this experiment comes first

If vehicle braking-response architecture does not move the recovery boundary under controlled conditions, the central vehicle-aware branch should be killed or sharply narrowed before investing in CARLA or a large coupled framework.

## Controlled assumptions

Fixed across conditions:
- same virtual driver, **open-loop** (frozen in `control_input_definition.md`: the command trajectory is bit-for-bit identical across all profiles; the vehicle's resulting motion never feeds back into the command)
- automation holds authority and `v0` until `t_reaction` (baseline handover policy B, `control_ownership_timeline.md`); the driver's accelerator channel is never engaged (L3 out-of-loop framing)
- same attention
- same reaction time (`t_reaction = 1.0s`, a documented choice within the 0.7-1.5s literature range — see `phase1A_parameter_table.csv`)
- same decision rule
- same familiarity (`M_mismatch = 0`)
- same initial speed
- same hazard
- same TOR condition
- same road-friction condition within each matched comparison
- same nominal maximum deceleration for the primary mechanism-isolation run

Changed:
- **transient brake-response mapping**

## Candidate response profiles (revised in Phase 0.3 — see research/PHASE0_3_REPORT.md)

These are generic response architectures, not named production vehicles. The P1-P4 labels are **not preserved automatically**; each surviving profile is defined by its parameter values in `vehicle_response_model.md` / `phase1A_parameter_table.csv`, not by a prose description.

### R0 — Reference (formerly "P1 — Progressive friction-like")
`t_delay` and `t_buildup` at their (respectively literature-anchored and COUNTERFACTUAL — see below) friction-brake values, `v_rolloff` inactive. This is the baseline every other profile is compared against. Per `analytical_sanity_check.md`, R0's comparison against R2 is analytically, not empirically, one-directional — Experiment A's value for this pair is in the *magnitude*, not the *sign*.

### R1 — Regen-onset (formerly "P2 — Regen-heavy / early deceleration")
Reformulated in Phase 0.3 (`control_ownership_timeline.md`, `vehicle_response_model.md`): **no separate `a_coast` phase** (retired — see below). Instead, `t_delay` is set *shorter* than R0's (qualitative-direction-only, unquantified — faster electric-motor response vs hydraulic actuation) and `v_rolloff` is active (near-stop fade — mechanism confirmed, numeric shape COUNTERFACTUAL, retained per Task 9 Option B as a sensitivity-only axis). Per `analytical_sanity_check.md`, R1 is the **only** profile pair whose comparison against R0 is not already analytically guaranteed — it is where Experiment A's actual open scientific question lives.

### R2 — Delayed build-up (formerly "P4 — Delayed / slower build-up")
Identical to R0 except `t_buildup` is increased. Same eventual `a_max`. The cleanest, single-parameter-difference profile relative to the reference — and, per `analytical_sanity_check.md`, the pair whose *sign* is a closed-form certainty (`d(D_stop)/dt_buildup > 0` for any realistic value), making this comparison's scientific value purely about magnitude and boundary-crossing, not discovery of direction.

### RETIRED — "P3 — Blended nonlinear" (unchanged from Phase 0.2)
Deferred, not implemented in Phase 1A — no causal channel under the frozen open-loop driver. See Phase 0.2 rationale, still valid.

### RETIRED (Phase 0.3) — `a_coast` as a standalone accelerator-release-phase parameter
Under the chosen Phase 1A baseline handover policy (B — automation holds `v0` until `t_reaction`, `control_ownership_timeline.md`), there is no temporal window in which the vehicle is uncommanded before the brake step — the phase `a_coast` was meant to describe does not occur. Its causal role is absorbed into R1's `t_delay`, as described above.

The numerical shapes are constrained from Phase-0.2/0.3 empirical/literature evidence in `phase1A_parameter_table.csv`; `t_buildup` and `v_rolloff`'s numeric shape (and R1's `t_delay` reduction) remain COUNTERFACTUAL and must be labeled as such in any reported run per `gate_A_preregistration.md` Step 5.3.

## Minimal longitudinal model

For integration step `dt`:

`v[t+1] = max(0, v[t] + a[t] * dt)`

`x[t+1] = x[t] + v[t] * dt + 0.5 * a[t] * dt^2`

`a[t] = vehicle_response(driver_command[t], v[t], profile_parameters)`

The baseline model should remain simple enough that every transformation can be inspected.

## Primary outcomes (Phase 0.2: scope frozen — see metric_definitions.md)

1. `collision` — derived: `stopping_margin < 0`.
2. `TTC_min`
3. `stopping_margin` — rigorous continuous definition in `metric_definitions.md`; not clipped at the hazard for this one measurement.
4. `impact_speed` — `NaN` when no collision, never 0.

`t_stabilise` and `N_correction` are **dropped from Phase 1A's scope**, not merely "inactive." Both require a closed-loop/correction-capable driver controller, which the frozen open-loop design (`control_input_definition.md`) structurally does not have — reporting them would misrepresent a structural non-result as a finding. See `metric_definitions.md` for the full rationale; they remain valid outcomes once a correction-capable driver model exists.

**Secondary derived outcome (added Phase 0.3):** `T_TOR_critical` — the minimum TOR lead time at which `stopping_margin = 0` for a given profile/scenario. See `metric_definitions.md` for its closed-form derivation and its direct link to the mother question (does vehicle response move the minimum safe handover-time boundary).

## Preliminary scenario axes

These are placeholders to be checked against the literature matrix before freezing:
- initial speed: multiple representative road speeds
- TTC / obstacle distance: low to high criticality
- TOR budget: multiple levels
- road friction: dry baseline first, wet sensitivity later

Do not use a huge Cartesian grid before a one-at-a-time diagnostic verifies that the simulator behaves physically.

## Gate A decision

**Decision procedure frozen in `gate_A_preregistration.md` (Phase 0.2)** — no absolute numeric threshold is invented; effect sizes are judged against two evidence-derived comparators (a reaction-time-equivalent perturbation and a numerical-noise floor) across a pre-registered scenario-tightness grid. Summary:

**KEEP the branch** only if realistic (literature-anchored, not COUNTERFACTUAL-only) response-profile changes produce effects classified "meaningful" (exceeding both comparators) at a non-trivial share of marginal-band grid points, with consistent direction and timestep-invariance.

**KILL / NARROW the branch** if apparent effects:
- are smaller than the numerical noise floor (Comparator B) anywhere claimed as material,
- occur only under COUNTERFACTUAL-only parameter values,
- disappear when maximum deceleration is controlled,
- or require the RETIRED "P3 blended nonlinear" mechanism, which has no causal channel under the frozen open-loop driver.

The practical-effect comparators were frozen in `gate_A_preregistration.md` before any simulation result exists, per the task instruction not to select thresholds after seeing results.

**Phase 0.3 addition:** `analytical_sanity_check.md` shows the R0-vs-R2 sign is already known before any run. Any future Gate A report on the R0-vs-R2 pair must be framed as a magnitude/boundary-crossing finding, not a discovery of direction — reporting it as "we found slower build-up is worse" would misrepresent a tautology of the chosen model as an empirical result.

## Claim boundary

Experiment A can support a statement of the form:

> Within empirically constrained response profiles, transient vehicle braking dynamics can/cannot materially shift simulated human-fallback recovery margins under controlled conditions.

It cannot, by itself, support:

> EVs are safer / less safe than ICE vehicles.

or

> A named production vehicle has an unsafe takeover response.
