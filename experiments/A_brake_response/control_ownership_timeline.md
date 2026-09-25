# Control-Ownership Timeline

**Status:** Pre-registration draft. Resolves the gap Phase 0.2 left open: `control_input_definition.md` froze a two-channel human command but never specified who is actually driving the vehicle *before* that command exists.

## The problem, stated precisely

`control_input_definition.md` modeled the pre-brake phase as "driver releases accelerator." In genuine L3 automated driving, out-of-loop before TOR, the human's foot is not necessarily on the accelerator at all — there is nothing to release. Modeling `a_coast` as triggered by an "accelerator release" event silently imports an L2/supervisory-ACC framing (foot resting on/near the pedal, actively modulating it) into a project whose stated object is L3 out-of-loop handover. This is a category error, and Phase 0.3 exists specifically to fix it before it gets encoded into a simulator.

## Real-world grounding, not just a modeling choice

Direct inspection of the raw OpenLKA EV Dataset (`Hyundai_IONIQ_5/bdda168c0c35fad7/2024-06-05--16-17-00/data.csv`, fetched and parsed in this pass — see `raw_dataset_forensics.md`) independently confirms that this authority distinction is not an academic abstraction: the underlying openpilot-derived telemetry schema itself separates **state** fields (`aEgo`, `vEgo`, `state_gas_pos` — always populated, describe what the vehicle is actually doing) from **automation-command** fields (`act_ctrl_gas`, `act_ctrl_brake`, `act_ctrl_accel`, `aTarget` — observed to sit at a constant inactive value of 0 throughout both sampled windows of this session, coincident with `op_enable = False`, `op_long_enable = False` for the entire sampled span). In other words: real production ADAS logging already distinguishes "is automation actively commanding longitudinal motion" from "what is the vehicle physically doing," via an explicit enable/authority flag. That is exactly the structure Task 1 asks the model to formalise.

## Four signals

- **`u_automation(t)`** — the automation's own longitudinal command (acceleration/deceleration it is asking for), defined only while automation holds authority.
- **`u_human_accel(t)`**, **`u_human_brake(t)`** — the human's own two-channel command, as defined in `control_input_definition.md`, defined only while the human holds authority (and, per that document, frozen open-loop from the moment it becomes active).
- **`w_authority(t) ∈ {automation, human}`** — which of the two actually determines `a(t)` at time `t`. Exactly one is active at any instant in the Phase 1A model (no blended/shared-authority state — that is a real phenomenon in some staged-withdrawal designs, but Phase 1A's baseline, chosen below, does not need it).

## Reconciling with the project's own T_authority / T_effective / T_stable vocabulary

`project_charter.md` Section 4.3 already distinguishes nominal authority transfer (`T_authority`) from first effective human control (`T_effective`). This document's `w_authority(t)` is the *model's* control-owning variable — it is not automatically the same timeline as `T_authority`. Under the baseline policy chosen below:

- `T_authority = 0` (TOR issuance) — the *nominal* handback, matching common real-ADS convention that a TOR event formally ends the system's design domain the instant it is issued.
- `w_authority(t) = automation` for `0 ≤ t < t_reaction` — automation continues to be the thing *actually* producing `a(t)` during this interval, even though nominal authority has already passed.
- `T_effective = t_reaction` — the first instant `w_authority(t)` flips to `human`, coincident with `control_input_definition.md`'s human brake-command onset.

This is a direct, literal instantiation of the project's own founding distinction ("authority transfer != capability recovery") inside the Phase 1A model, not just a slogan in the README — nominal authority (`T_authority`) and actual control-producing ownership (`w_authority`) are formally different timestamps, and the gap between them is exactly `t_reaction`.

## Distinguishing the candidate mechanisms (per the task's list)

- **Automation propulsion-command withdrawal**: `u_automation(t)` stepping to some lower/zero/negative value. This is a **policy choice about what automation does**, not a vehicle-hardware property.
- **Zero-drive-torque response**: what the vehicle's powertrain does when *no one* (neither automation nor human) is issuing a net propulsion or braking command. This is a **vehicle-architecture property** (ICE: engine braking via compression/gearing, or near-neutral freewheel depending on gear/clutch state; EV: either freewheel or a default light regen, depending on the specific vehicle's control logic).
- **Coast / overrun deceleration**: the *outcome* — whatever deceleration results from the zero-drive-torque condition, regardless of which architecture produced it.
- **Regenerative deceleration under a specific control architecture**: a *human-commanded or automation-commanded* deceleration delivered via the electric motor rather than friction brakes — this is different again from zero-drive-torque coast; it requires an active (nonzero) request, just routed through a different actuator.
- **Staged automation withdrawal**: a *handover-policy* variant where `w_authority(t)` is not a clean binary step but a blended/ramped transition.

These five are not interchangeable, and Phase 0.2's `a_coast` blurred at least three of them together (see Section 3 below).

## Baseline handover policy for Phase 1A (Task 2)

Three candidates were given: (A) immediate withdrawal at TOR, (B) automation maintains previous command until human brake onset, (C) staged/overlap withdrawal.

**Chosen baseline: B.**

```
t < 0:                  w_authority = automation; u_automation(t) holds v0 (steady-state cruise)
t = 0:                  TOR issued (T_authority, nominal)
0 <= t < t_reaction:    w_authority = automation; u_automation(t) CONTINUES holding v0
t = t_reaction:         w_authority flips to human (T_effective); u_human_brake step begins (control_input_definition.md)
t > t_reaction:         w_authority = human; vehicle_response_model.md governs a(t)
```

**Justification:** this is the only one of the three baseline candidates under which `[0, t_reaction)` is **identical across every compared vehicle-response profile by construction** — the vehicle's motion in that interval is entirely determined by automation holding a constant speed, which does not depend on the profile being tested. Policy A (immediate withdrawal) would make the vehicle's own architecture-dependent coast/withdrawal response active *during* the reaction-time interval, which is scientifically interesting (and connects to the charter's own "automation withdrawal policy" variable) but **confounds two mechanisms at once** — architecture and withdrawal-timing — inside what is supposed to be Experiment A's single isolated mechanism. Policy C (staged) adds a free blending-shape parameter with no evidence behind it (the same objection `vehicle_response_model.md` already raised against unconstrained shape parameters). B is the minimal, cleanest baseline; A and C are logged as **later sensitivity tests**, not part of the Phase 1A baseline, per the task's explicit instruction not to put all three in automatically.

## What this means for the pre-brake interval

Under baseline B, there is **no temporal window** in which the vehicle is in a zero-drive-torque / uncommanded state before the human's brake command — automation is actively holding `v0` right up to `t_reaction`. This directly motivates Task 3's reassessment of `a_coast`, below: the "accelerator-release coast phase" Phase 0.2 imagined **does not exist** under the chosen Phase 1A baseline.
