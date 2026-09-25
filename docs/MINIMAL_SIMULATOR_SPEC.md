# Minimal Simulator Specification

**Status:** Specification only. No code in this document or produced alongside it. Defines the smallest simulator needed for A0 (validation) and A1 (first non-trivial experiment), per `docs/RESEARCH_ARCHITECTURE_V1.md`.

## State variables

`t`, `x_ego`, `v_ego`, `a_ego`. `x_hazard` (equivalently, `gap = x_hazard - x_ego`) is a fixed scalar per scenario, not a state variable that evolves (this project's scenarios are single-fixed-hazard, per `project_charter.md`'s longitudinal-only scope). `TTC(t) = gap(t) / v_ego(t)` for `v_ego(t) > 0`, undefined otherwise (`metric_definitions.md`).

## Inputs

- `TOR_lead_time` (determines `x_hazard = v0 · TOR_lead_time`)
- `t_reaction` (fixed per `control_input_definition.md`)
- **withdrawal policy** ∈ {W0, W1} (`control_ownership_timeline.md`, `docs/CAUSAL_MODEL.md`)
- `u_human_brake(t)` (frozen step function, `control_input_definition.md` — identical across every compared condition; the simulator must not expose any way to make this profile-dependent)
- vehicle-response parameters: `t_delay`, `t_buildup`, `a_max` (held constant), `v_rolloff` (`v_threshold`, `floor`), `a_coast` (active only under W1, per `docs/CAUSAL_MODEL.md`)

## Outputs

`collision` (derived), `TTC_min`, `stopping_margin`, `impact_speed`, `T_TOR_critical` (per-scenario, requires the search/closed-form procedure in `metric_definitions.md`, run as a wrapper around the core trajectory simulator, not as a state variable of it).

## Integration method

**Piecewise-constant-acceleration-within-a-step, matching the formula already given in `experiment_A_spec.md`'s "Minimal longitudinal model":**

```
v[k+1] = max(0, v[k] + a[k]·dt)
x[k+1] = x[k] + v[k]·dt + 0.5·a[k]·dt²
```

This is exact for genuinely constant `a` within a step (which is what makes the A0 comparison against the closed form meaningful — the closed form itself assumes piecewise-constant/linear-ramp `a(t)`, so the numerical scheme's only error source is the *ramp* being approximated as a staircase of constant steps, not an additional modeling error). `a[k]` is computed once per step from `vehicle_response_model.md`'s functional form, evaluated at `(t[k], v[k])` — the roll-off term `rolloff(v)` makes this an explicit (not implicit) scheme, which is acceptable given the small `dt` required below and is simpler to validate than an implicit solver.

## `dt` requirements

The smallest evidenced timescale in the whole parameter set is `t_delay`'s literature-anchored range floor, **0.05s** (Paquette & Porter). `raw_dataset_forensics.md` already demonstrated, empirically, what happens when sampling is too coarse relative to the phenomenon (D005's 10Hz/100ms sampling cannot resolve a 50-170ms transient) — the simulator must not repeat that mistake internally. **Default `dt = 0.001s` (1ms)**, giving ≥50 samples across even the shortest evidenced `t_delay` value. This is a starting point, not a final choice — Task 10's `dt`-convergence test (test 6) is exactly how this gets confirmed rather than assumed.

## Event handling

Three classes of event, handled differently:

1. **A-priori-known phase transitions** (`t_reaction`, `t_reaction+t_delay`, `t_reaction+t_delay+t_buildup`): these are scenario-parameter-determined, not state-dependent, so the simulator should step to these exact times (adjusting the last `dt` of each phase if needed) rather than discovering them numerically — this avoids the phase-boundary numerical error that a naive fixed-grid stepper would otherwise introduce.
2. **State-dependent threshold crossing** (`v_ego` crossing `v_threshold` for `v_rolloff`): genuinely state-dependent, cannot be scheduled in advance. Detect via bracketing (the threshold falls between `v[k]` and `v[k+1]`) and use linear interpolation within the step to estimate the crossing time, rather than accepting the coarse-grid value.
3. **Outcome-defining events** (`x_ego` reaching `x_hazard` — collision; `v_ego` reaching 0 — full stop): same bracketing-and-interpolation treatment as (2). This directly affects `impact_speed` precision (`metric_definitions.md` requires this to be the *actual* crossing-point speed, not a coarse-grid approximation) and `stopping_margin`'s continued-integration convention (the interpolated full-stop point, not a `dt`-quantized one).

## Collision detection

`collision := stopping_margin < 0` (derived, per `metric_definitions.md` — never computed independently of `stopping_margin`, to avoid the internal-inconsistency failure mode already flagged there). The underlying trajectory-crossing check (for `impact_speed`, which *does* need the real, wall-respecting crossing) uses event class 3 above.

## Stopping condition

Simulation for a given trajectory ends at the earlier of: (a) `v_ego` reaching 0 (full stop — event class 3, interpolated), or (b) a pre-registered maximum simulation time (a safety bound against an infinite loop if a degenerate parameter combination is ever supplied — not expected to bind under any of the profiles in `phase1A_parameter_table.csv`, but must exist). For `stopping_margin`'s counterfactual continued-integration convention (`metric_definitions.md`), the simulator continues past `x_hazard` if a collision would occur, stopping only at condition (a) or (b) — the wall-respecting collision check is a separate, non-terminating observation on the same trajectory, not a different simulation run.

## Numerical tolerances

**A0 validation tolerance:** at `dt = 0.001s`, simulated `stopping_margin`/`TTC_min`/`impact_speed`/`T_TOR_critical` for R0/R2 under W0 must match the closed-form values (`analytical_sanity_check.md`, `metric_definitions.md`) to within a **relative error of 0.1%** (chosen as a round, conservative bound given the piecewise-constant scheme's expected `O(dt)`-to-`O(dt²)` local truncation error at this `dt`; the exact achieved order is what Task 10's convergence test measures, not assumed here). A0 fails its own validation role if this tolerance is not met — that failure would be a simulator bug, not a research finding, and must block any A1 run until fixed.

**A1 numerical-noise floor:** unchanged from `gate_A_preregistration.md` Comparator B (`dt`-halving) — an A1 effect smaller than the resulting change is not material, regardless of which withdrawal-policy/architecture cell produced it.

## Analytical unit tests using A0

Specified in full in `tests/TEST_PLAN.md` (Task 10) — this section only states the principle: **every A0 configuration is, by construction, a unit test**, because its correct output is known in closed form before the simulator runs. No A1 result may be trusted until every A0 test in `tests/TEST_PLAN.md` passes.
