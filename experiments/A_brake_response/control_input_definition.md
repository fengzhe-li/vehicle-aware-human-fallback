# Phase 1A Control Input Definition

**Status:** Pre-registration draft. Defines the human command signal only — the vehicle-response mapping is defined separately in `vehicle_response_model.md`. The automation/human authority split is defined separately in `control_ownership_timeline.md`, whose baseline policy (B) this document now assumes throughout.

**Phase 0.3 correction (read this before the rest of the document):** the original version of this document modeled the human's first action as "accelerator release," implicitly assuming the driver's foot was on the accelerator before TOR. `control_ownership_timeline.md` establishes this is an L2/supervisory-ACC framing, not L3 out-of-loop — under L3, the driver is not operating the accelerator pre-TOR, so there is nothing to release. This document is revised accordingly: `u_human_accel(t) = 0` for all `t` in Phase 1A's baseline (the driver never engages the accelerator at all), and the human's first and only action is the brake-pedal step. `Δt_transfer` (the old "throttle-to-brake transition time") is **retired**, not merely re-anchored — it described a transition between two pedals that, under this corrected framing, the driver never occupies in the first place.

## Why this needs its own document

`experiment_A_spec.md` says "same decision rule" and "same correction rule" but never specifies the actual command signal. `experiment_A_review.md` (Phase 0.1, Q2) flagged this as the single most important open control gap: if the driver command is closed-loop (reacts to felt vehicle response), differences between profiles would be partly driven by the driver model, not the vehicle-response mechanism alone. Phase 0.1 recommended resolving this before implementation. This document resolves it.

## Decision: open-loop, two-channel, step-command driver

Phase 1A uses an **open-loop** driver: the command signal `u(t) = (u_accel(t), u_brake(t))` is a fixed function of time only (relative to TOR/hazard onset), identical **bit-for-bit** across all vehicle-response profiles. The vehicle's actual resulting motion never feeds back into `u(t)`. This is a deliberate simplification, not an oversight — it is the only way to guarantee that any outcome difference between profiles is attributable to `vehicle_response()` and not to profile-dependent driver behaviour. A closed-loop/correction-capable driver is explicitly deferred to a later phase (this is also why `t_stabilise` and `N_correction` are dropped from Phase 1A outcomes — see `metric_definitions.md`).

## Two separate channels (not one vague "brake input")

Per the task instruction, accelerator and friction-brake pedal must be distinguished explicitly, because it is exactly the accelerator-release phase (before any brake pedal action) that produces a real, evidenced behavioural difference (L004; and see `vehicle_response_model.md`'s `a_coast` parameter).

- `u_accel(t)` — normalized accelerator command, `[0, 1]`.
- `u_brake(t)` — normalized friction-brake pedal command, `[0, 1]`.

These are **human command inputs**, not vehicle outputs. They are the analogue of ADAS-TO's `carState.gas`/`carState.brake` fields *if* those were continuous (Workstream 5 finding: in ADAS-TO's actual release they are not — see `PHASE0_2_REPORT.md`). The vehicle-response model consumes `u_accel(t)` and `u_brake(t)` and outputs `a(t)`; it does not see anything else.

## Minimum command sequence (revised, Phase 0.3)

Two timing/magnitude parameters — smaller than the Phase 0.2 version, because retiring the accelerator-release phase removes `Δt_transfer` entirely (see correction above):

| symbol | meaning | Phase-1A value | evidence |
|---|---|---|---|
| `t_reaction` | time from TOR/hazard reference to driver's first physical action (brake pedal command begins directly — no accelerator involved) | **1.0 s** (fixed, chosen — see below) | Bounded by literature between ~0.7 s (expected/planned reaction-time literature) and ~1.5 s (surprise reaction-time literature); L014 shows naturalistic onset is urgency-dependent, not fixed, which is exactly the limitation already logged in `parameter_evidence_table.csv`. 1.0 s is a documented **choice** within the literature range, not itself a literature point-value — an out-of-the-loop TOR context is neither a fully "expected" nor a fully "surprise" reaction, so the midpoint is used as a defensible starting value. |
| `u_human_accel(t)` | accelerator command | **identically 0 for all `t`** (retired as an active channel — see correction above) | Consistent with L3 out-of-loop framing per `control_ownership_timeline.md`. Retained as a named channel (per the task's instruction to distinguish the two channels explicitly) purely so its non-engagement is a stated modeling decision, not a silent omission. |
| `u_human_brake: 0 -> u_target` | brake pedal command | **step to `u_target = 1.0` (full/near-maximum commanded brake demand) at `t_reaction`** | Consistent with the general finding that genuine emergency braking is typically a near-maximal, decisive pedal application rather than a graded one (implicit in the AEB/emergency-braking literature reviewed in Phase 0.1, e.g. L003's finding that takeover braking is often *stronger* than required, not weaker). |

## Why step commands, not smooth human-side ramps

A tempting alternative is to give the human command itself a smooth ramp (e.g., brake pedal rising over some seconds). This is deliberately rejected for Phase 1A:

1. **It would need its own unanchored shape parameter** (how fast does the human ramp the pedal?), duplicating a parameter that is much better evidenced on the *vehicle* side (`t_buildup` in `vehicle_response_model.md`, anchored to real brake-timing literature).
2. **It reintroduces the exact confound Q2 flagged in Phase 0.1**: if the human-side ramp shape is itself allowed to vary or be profile-specific, the isolation between "what the human commands" and "how the vehicle responds" breaks down.
3. Putting all transient shape into `vehicle_response()` and keeping `u(t)` as the simplest physically-interpretable step function is the **minimal** design that still lets Experiment A ask its actual question: does the *vehicle's* mapping from command to motion matter, holding the *command* fixed?

## Explicit invariant

> `u_human_accel(t) ≡ 0` and `u_human_brake(t)` (the single step at `t_reaction`) are identical functions of `t` for every vehicle-response profile compared in Experiment A. Only `vehicle_response(u_human_brake(t), v(t), w_authority(t), θ_profile)` differs between profiles — see `control_ownership_timeline.md` for how `w_authority(t)` and `u_automation(t)` fit around this human command.

This invariant must be checked programmatically (e.g., a unit test asserting bit-identical `u(t)` arrays across profile runs) once implementation begins — not just asserted in text.
