# Phase 1A Vehicle-Response Model

**Status:** Pre-registration draft. Consumes `u_human_brake(t)`, `w_authority(t)` from `control_input_definition.md` / `control_ownership_timeline.md`; outputs `a(t)` for the kinematic integrator in `experiment_A_spec.md`.

**Phase 0.3 correction (read before the rest of this document):** the Phase 0.2 version of this model included `a_coast`, a deceleration active during an "accelerator-release phase" before brake onset. `control_ownership_timeline.md` establishes that under Phase 1A's chosen baseline (policy B), that phase does not exist — automation holds `v0` until `t_reaction`, and the human command goes directly to a brake step with no accelerator involvement. `a_coast`, as originally formulated, is **retired**, not merely re-anchored (see `phase1A_identifiability_final.csv`, Task 3 verdict: REFORMULATE). Its causal role — distinguishing regen-flavored from friction-only architectures — is absorbed into `t_delay` below, via a physically distinct and better-motivated mechanism.

## Method: reduce, don't enumerate

The task lists eight candidate parameters: coast/regen deceleration after accelerator release, brake actuation delay, deceleration build-up time, brake gain/nonlinear gain, maximum deceleration, speed dependence, low-speed regen fade/cutoff, jerk. Each is tested below against one question: **does it have an independent, non-redundant causal channel to the outcomes, under the open-loop step-command driver frozen in `control_input_definition.md`?** If not, it is dropped or merged.

### Kept as free parameters (revised, Phase 0.3)

**1. `t_delay`** — time from brake-command onset (`u_human_brake` step) to the first meaningful deceleration build-up. Now carries a **second role** beyond Phase 0.2's: it is also where the regen-vs-friction architecture distinction lives, since regen-blended brakes can plausibly deliver initial deceleration faster than a purely hydraulic friction system (electric motor torque response is physically faster than hydraulic actuation — a well-established general fact, though its *size* is unquantified, see `phase1A_identifiability_final.csv`). A regen-flavored profile therefore uses a **shorter** `t_delay` than a friction-only profile; this is the reformulated replacement for `a_coast`'s causal role. **Retained**, evidence status per parameter below.

**2. `t_buildup`** — time from `t_delay` to reach `a_max`. Still the single parameter the R0 (reference) vs R2 (delayed build-up) distinction reduces to, and still the primary architecture-shape axis. **Retained as a model parameter**, but its Phase 0.2 numeric anchor was **downgraded to COUNTERFACTUAL_ONLY** after adversarial re-checking in Phase 0.3 — see `phase1A_identifiability_final.csv`, Task 7. The parameter's role in the model is unaffected; only its numeric anchoring is.

**3. `v_rolloff` (roll-off speed threshold and floor fraction)** — below a low-speed threshold, achievable deceleration is scaled toward a floor value, representing regenerative-torque fade near standstill. Still the only feature that is non-monotonic relative to a simple time-shifted ramp (needed to avoid the triviality risk identified in Phase 0.1's Q5 and confirmed analytically in `analytical_sanity_check.md`, where R0-vs-R2's sign is shown to be a foregone conclusion but R1's is not). **Retained, but per Task 9's decision, only as an explicit COUNTERFACTUAL sensitivity axis — see "v_rolloff status" below.** It must not be allowed to drive the primary, literature-anchored Gate A claim.

**`a_coast` is REMOVED from the free-parameter list** (see correction above).

### Held constant across all profiles in the primary mechanism-isolation run

**5. `a_max`** — maximum achievable deceleration. Per `experiment_A_spec.md`'s own design and the charter's Gate A framing, this is deliberately equalised across profiles so that any outcome difference is attributable to transient shape, not to braking capacity. It remains a parameter of the model (needed to compute the ramp target) but is not a free/varying dimension of the primary comparison.

### Dropped or merged

**"Brake gain / nonlinear gain" (command-magnitude nonlinearity) — DROPPED as an independent parameter.** Under the frozen open-loop step command (`control_input_definition.md`), `u_brake(t)` only ever takes two values (0 and `u_target = 1.0`). A gain curve's shape *between* those two values (linear vs S-curve vs threshold-then-ramp with respect to *command magnitude*) has no causal channel to the outcome, because the command never dwells at an intermediate value — this is the same logic Phase 0.1's Experiment A review (Q7) used to flag that P3's mid-range nonlinearity cannot show up under an open-loop driver. A real "blended nonlinear" architecture instead shows up as a **shape** feature of the deceleration-vs-*time* curve (e.g., a fast initial regen-dominated rise followed by a slower friction-blend transition, producing an inflection). That is not an independent parameter — it is a special case of `t_buildup` (a two-phase ramp instead of a single linear ramp) and is treated that way below, not reinstated as a fifth free parameter.

**"Speed dependence" (generic) — MERGED into `v_rolloff`.** A generic, unconstrained "deceleration capability depends on speed" term would need its own unconstrained function shape and would violate the "do not include a parameter just because it is physically possible" instruction. The only *specific*, evidenced form of speed-dependence found (Workstream 4) is low-speed regen fade near standstill — that is `v_rolloff`. No other speed-dependence mechanism has evidence behind it for Phase 1A, so no generic term is added.

**"Jerk" — DEMOTED from input parameter to monitored/derived output.** Jerk `j(t) = da/dt` is fully determined once `t_delay`, `t_buildup`, and the ramp shape are fixed — it is not a free input. It is retained only as a **plausibility check**: after choosing `t_delay`/`t_buildup` for a profile, the implied peak jerk should be checked against the literature ranges gathered in Phase 0.2 (comfort range ~1-2.5 m/s³; naturalistic non-emergency ceiling ~2.6 m/s³, Feng et al. 2017). An implausibly high implied jerk (e.g., from an unrealistically instantaneous ramp) should trigger revisiting `t_buildup`, not be reported as a project finding.

## Resulting minimum parameter set (revised, Phase 0.3)

**Three** free parameters (`t_delay`, `t_buildup`, `v_rolloff`) — down from Phase 0.2's four, since `a_coast` was retired rather than merely re-anchored — one held-constant parameter (`a_max`), and one derived/monitored quantity (jerk). Of the three free parameters, only `t_delay` carries a real (if architecture-generic) numeric anchor; `t_buildup` was downgraded and `v_rolloff` remains COUNTERFACTUAL-only (both `phase1A_identifiability_final.csv`). This is a further, evidence-driven reduction from Phase 0.2's already-reduced eight-item candidate list — see `research/parameter_provenance/phase1A_parameter_table.csv`.

## Functional form

For `t >= t_reaction` (relative to the reference TOR/hazard onset):

```
s = clip((t - t_reaction - t_delay) / t_buildup, 0, 1)
a(t) = -a_max * rolloff(v(t)) * s        # linear ramp from t_delay onset to a_max over t_buildup
                                          # (a(t) = 0 for t < t_reaction + t_delay, since w_authority
                                          #  is automation and u_human_brake has not yet stepped or
                                          #  has not yet produced a response - no separate coast phase)

rolloff(v) = 1                                  if v >= v_threshold   (pure-friction profiles: always 1)
rolloff(v) = floor + (1-floor) * v / v_threshold  if v < v_threshold   (regen-flavored profiles only)
```

`floor` (residual deceleration fraction as v -> 0) and `v_threshold` (speed below which roll-off begins) are the two sub-parameters of `v_rolloff`; both remain COUNTERFACTUAL after a second, more targeted search attempt in Phase 0.3 (mechanism confirmed by multiple independent sources, no numeric shape found — see `raw_dataset_forensics.md` for why raw-data extraction did not resolve this either: no regen event was captured in the sampled windows).

**Linear ramp, not a smoothstep or exponential, by design**: unchanged from Phase 0.2 — see rationale there. Linear remains the minimal, parameter-free interpolation between the two endpoints.

**Regen-flavored `t_delay`, per the Phase 0.3 reformulation**: a regen-flavored profile (R1) uses a *shorter* `t_delay` value than the friction-only baseline (R0), representing faster electric-motor torque response relative to hydraulic friction-brake actuation. This is currently a **qualitative direction only** (see `phase1A_identifiability_final.csv`) — no source quantifies the size of the difference, so R1's `t_delay` value, like `v_rolloff`, must be treated as COUNTERFACTUAL until a comparative source or a raw-data episode (per `response_episode_definition.md`) is found.

## v_rolloff status (Task 9 decision)

Per the task's three options (A: drop from formal Phase 1A, B: retain only as COUNTERFACTUAL sensitivity analysis, C: obtain empirical numeric support): **Option B.** `v_rolloff` is retained in the model (it is the only feature giving R1 a non-trivial, non-analytically-guaranteed comparison — see `analytical_sanity_check.md`), but it must be run only as an explicit, visibly-labeled COUNTERFACTUAL sensitivity axis, never as an input to the primary literature-anchored Gate A claim (`gate_A_preregistration.md` Step 5.3 already requires this; this section makes the requirement specific to `v_rolloff` by name). Option A (dropping it) was rejected because it would remove the one part of Experiment A whose result is not already known from the closed-form derivation, gutting the experiment's remaining scientific value. Option C (obtaining empirical support) remains the goal but was not achieved in this pass despite a genuine raw-data search attempt.

## What this model explicitly does not represent

- Lateral dynamics (out of scope, per charter Section 10).
- A closed-loop driver response to felt deceleration (out of scope for Phase 1A, per `control_input_definition.md`).
- A precise OEM regen/friction blending map (would require proprietary data; explicitly disallowed by the charter's claim boundaries).
- Any interaction between `t_buildup` shape and driver-perceived urgency (would require the closed-loop model above).
- A pre-brake accelerator-release phase (retired in Phase 0.3 — see correction at the top of this document and `control_ownership_timeline.md`).
