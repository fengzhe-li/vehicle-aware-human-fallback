# Braking slice: exact scope and correction design (R3B-0; no code)

**Status:** design note, 2026-09-23. **Implemented in R3B (commit `028786b`)**: friction cap `min(u·a_max·rolloff, μg)`, `HandoverTimeline` / `PreControlProfile`, and the wired command. All golden (legacy-reproduction) requirements are met. See `docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md` §1. The text below is kept as the design record.

**One deliberate deviation:** correction B below writes `a_lim = min(a_max, μg)` with the command applied afterwards (`u · a_lim`). The implementation follows the R3B specification, `min(u · a_max, μg)`. The two are identical for u = 1 (the only command used in the R3B slice) and differ only for partial commands on low friction (D022, D023).

---

## 1. Exact scope of the current longitudinal model

The closed form `T_required(v0, t1, a_pre, t2, t3, a_max)` and the simulator (`src/simulation/simulator.py`, `src/vehicle/models.py`) implement a model that is:

| Property | Statement |
|---|---|
| Deterministic | no randomness; every parameter is a point value |
| Open loop | no feedback from state to human command after onset |
| 1-D | longitudinal only; stationary hazard at `x_hazard = v0 · tor_lead_time` |
| Stopping-focused | success = stopping before the hazard station |
| Saturated braking | after `t_reaction + t2`, deceleration ramps over `t3` to `a_max` (optionally with roll-off) and stays there: the command is effectively `u = 1` |
| Necessary-condition analysis | if `T_available < T_required(u = 1)`, braking alone cannot succeed; the converse does not hold |
| Exact only under its own assumptions | the closed form matches the simulator (A0), which is verification, not validation |
| Not system-level recoverability | no human variability, no transition policy beyond W0/W1, no hazard geometry |
| Not valid for steering-dominant recovery | lane-change recovery (D003: 499/513 trials) is outside the model |

**Known implementation simplifications** (verified by reading the code in R3A and R3B-0):
1. **`u_target` does not reach the vehicle model.**
   - `HumanDriverConfig.u_target` exists and `get_human_command` returns it.
   - `calculate_acceleration(t, v, vehicle, withdrawal, t_reaction)` has no command argument and returns `-a_max · rolloff · s` after the delay.
   - A1 only checks `u_target` as a design invariant and plots it.
2. **`road_friction` does not constrain `a_max`.**
   - `ScenarioConfig.road_friction` (default 1.0) is passed around by `critical_tor.py` and checked in `a1_runner.py`.
   - It never enters the dynamics.
   - The default `a_max = 8.5` implies μ ≥ 0.87.
3. **Authority transfer is not separated from TOR.**
   - `src/handover/models.py` documents `T_authority = 0 (TOR)` and `T_effective = t_reaction`.
   - `get_control_authority` switches at `t_reaction`.
   - Authority transfer, first input and effective input are therefore one instant, and the pre-reaction interval is governed only by W0 (hold speed) or W1 (`a_coast`).

---

## 2. Correction A: wire the control input `u(t)` into the vehicle dynamics

| Item | Design |
|---|---|
| Current behaviour | Full braking is hard-coded; `u_target` is ignored. |
| Desired behaviour | Deceleration follows the commanded brake input through the response stages: `a(t) = −g_map(u_brake(t − t2)) · a_lim · s(t)`. The default `g_map(u) = u` is linear; a nonlinear map is an optional parameter. The build-up `s(t)` follows the change in command, not a single step. |
| API / state change | `calculate_acceleration` receives the current (delayed) brake command or a command-history accessor; `VehicleResponseConfig` gains an optional `brake_map`; `HumanDriverConfig.u_target` feeds the command generator. `MinimalSimulator` passes the command. |
| Test requirements | (i) golden test: `u_target = 1` reproduces every existing A0/A1/D0/E0 output bit-for-bit or to 1e-12; (ii) `u = 0.5` gives half the steady deceleration; (iii) `T_required` decreases monotonically in `u`; (iv) a closed-form check for a constant `u < 1`; (v) `u = 0` never stops. |
| Backward compatibility | The default must equal the current behaviour. Historical outputs must not be regenerated with the new code unless the golden test passes. |
| Scientific consequence | Partial braking becomes expressible. The capability-bound slice becomes the special case `u = 1`, and behavioural `u_eff` (crash median ≈ 0.58 g) can be explored as a scenario. The partial-command vehicle map (regen/friction blending) is still not identifiable, so only generic maps are allowed. |

## 3. Correction B: apply the friction constraint to achievable deceleration

| Item | Design |
|---|---|
| Current behaviour | `road_friction` is carried but unused; `a_max` is independent of μ. |
| Desired behaviour | `a_lim = min(a_max, μ · g)`, where `a_max` is the vehicle capability on a reference surface. The same cap will later bound the combined `√(a_x² + a_y²)`, but not in the braking slice. |
| API / state change | One pure function, `effective_deceleration_limit(vehicle, scenario)`, used everywhere `a_max` is used; `ScenarioConfig.road_friction` becomes meaningful. A registry rule already requires μ to carry unit, range and source before entering synthesis. |
| Test requirements | (i) with the default μ = 1.0, `a_lim = 8.5` (unchanged results); (ii) μ = 0.5 gives `a_lim = 4.905`; (iii) results are invariant for any μ ≥ `a_max / g`; (iv) the closed form uses `a_lim`; (v) the A1 design-invariant check still passes. |
| Backward compatibility | The default μ = 1.0 gives μg = 9.81 > 8.5, so every existing result is unchanged. Scenarios with `a_max > μg` change and must be labelled. |
| Scientific consequence | Wet and low-friction scenarios become physically consistent; `a_max` intervals from the registry (6.43–9.1 m/s²) can no longer exceed friction silently. |

## 4. Correction C: separate TOR from authority transfer

| Item | Design |
|---|---|
| Current behaviour | Authority, first input and effective control coincide at `t_reaction`; the documentation places authority at TOR; the pre-reaction interval is W0 or W1 only. |
| Desired behaviour | An explicit timeline `0 = t_TOR ≤ t_auth^lon ≤ t_eff^lon`, with the transition policy `π` acting on `[0, t_auth^lon)`: hold speed, decelerate within a stated bound, release propulsion, or MRM. The human brake command acts only after `t_eff^lon`. Lateral fields are reserved for later. |
| API / state change | A `HandoverTimeline` value (e.g. `t_auth_lon`, `t_eff_lon`, reserved `t_auth_lat`, `t_eff_lat`) and a `TransitionPolicy` value replacing the W0/W1 enum. W0 and W1 become two policy instances; `get_control_authority` uses `t_auth`. |
| Test requirements | (i) golden test: `t_auth = t_eff = t_reaction` with the W0/W1 policies reproduces current outputs; (ii) invariant `t_auth ≤ t_eff` is enforced; (iii) an R157-like policy (continued operation, speed reduction, demand ≤ 5 m/s² before any EM) is representable; (iv) authority can never precede TOR. |
| Backward compatibility | The W0/W1 names stay as aliases; historical A1 outputs stay reproducible. |
| Scientific consequence | `a_pre` becomes an explicit policy output on a defined interval, matching the R3A reinterpretation. R157-consistent transitions (continued operation until deactivation) can be expressed. `t_auth` stays an **input assumption**: it is not identified from D003. |

---

## 5. Order and gating
Implement B first (smallest, fully backward-compatible), then C, then A. Each needs its golden test before any result is regenerated. None of this is authorised in R3B-0.
