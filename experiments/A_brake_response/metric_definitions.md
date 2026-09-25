# Phase 1A Metric Definitions

**Status:** Pre-registration draft.

## Retained vs dropped outcomes

`experiment_A_spec.md` lists six candidate outcomes: `collision`, `TTC_min`, `stopping_margin`, `impact_speed`, `t_stabilise`, `N_correction`. Phase 1A retains only the first four.

**`t_stabilise` and `N_correction` are dropped from Phase 1A**, not redefined. Both require a driver who can take a *second* action in response to how the vehicle is behaving (a correction-capable, closed-loop controller). `control_input_definition.md` freezes Phase 1A's driver as strictly open-loop (a fixed, one-shot command sequence). Under that design there is no mechanism by which `t_stabilise` or `N_correction` could take on more than one trivial value (the driver never corrects, so there is nothing to "stabilise" toward after the single command, and the correction count is definitionally zero). Reporting these as if measured would misrepresent a structural non-result as a finding. They remain valid future outcomes once a closed-loop/correction-capable driver model exists (already anticipated in `PHASE0_CHECKLIST.md`) — this is a **scope decision for Phase 1A**, not a retraction of the metrics from the project's vocabulary.

Retained: `collision`, `TTC_min`, `stopping_margin`, `impact_speed`.

## Simulation convention

The kinematic model integrates `x_ego(t)`, `v_ego(t)` from the TOR/hazard reference. `x_hazard` is a **fixed reference distance**, not a rigid wall that halts integration — see the stopping-margin rationale below for why this matters. `v(t)` is clipped at 0 (vehicle cannot reverse under this model).

## `collision`

**Definition:** `collision := (stopping_margin < 0)`.

Collision is **derived from** `stopping_margin`, not computed independently. This is a deliberate choice: an independently-computed collision flag and an independently-computed stopping-margin value could in principle disagree at floating-point/discretization boundaries, which would be an internal inconsistency bug, not a real edge case. Making `collision` a pure function of `stopping_margin`'s sign removes that failure mode by construction.

## `TTC_min`

**Definition:** `TTC_min = min over t in [t_reaction, t_stop_or_collision] of TTC(t)`, where `TTC(t) = (x_hazard - x_ego(t)) / v_ego(t)` for `v_ego(t) > 0`.

- `t_stop_or_collision` is the earlier of (a) the time `v_ego(t)` first reaches 0, or (b) the time `x_ego(t)` first reaches `x_hazard` (whichever the trajectory hits first under real, wall-respecting integration — see note below).
- `TTC(t)` is undefined (excluded from the min, not treated as 0 or +infinity in a way that would bias the minimum) whenever `v_ego(t) = 0`, since a stationary vehicle with no closing motion has no meaningful TTC.
- If collision occurs, `TTC_min -> 0` at the collision instant by construction (`x_ego = x_hazard` at that instant), so `TTC_min` and `collision` will be consistent by construction, not by coincidence.

## `impact_speed`

**Definition:** `impact_speed = v_ego(t)` evaluated at the instant `x_ego(t)` first reaches `x_hazard`, **if and only if** `collision = True`. If `collision = False`, `impact_speed` is `NaN`/undefined — **never 0**. Silently defaulting non-collisions to `impact_speed = 0` would make a "no collision" case indistinguishable from a "zero-speed collision" case in downstream analysis; the two are not the same event and must not be conflated. This must be enforced in whatever data structure holds simulation results (explicit null/NaN, not a numeric default).

## `stopping_margin` (rigorous definition, per Task 7)

**Definition:**

```
x_stop_full = ego position at the instant v_ego(t) first reaches 0,
              computed by continuing the vehicle's deceleration trajectory
              mathematically PAST x_hazard if necessary (x_hazard is treated
              as a reference marker in space, not a wall that halts integration,
              for the purpose of this one quantity).

stopping_margin = x_hazard - x_stop_full
```

**Sign convention:** `stopping_margin > 0` means the vehicle would come to a full stop that many metres *short* of the hazard (a safety buffer). `stopping_margin < 0` means the vehicle's own deceleration trajectory would only reach `v = 0` that many metres *past* the hazard reference point — i.e., a collision, with the magnitude serving as a severity-correlated (not severity-defining) indicator of how much additional stopping distance was required.

**Why the hazard is not treated as a rigid wall for this specific computation:** if integration stopped dead at `x_hazard` (as it must for computing `impact_speed`, which is a physically real quantity at a physically real point), `stopping_margin` would become undefined for every collision case, collapsing to a binary flag and failing the task's requirement that it "remain interpretable as a continuous recovery-margin metric" across the collision boundary. Continuing the *counterfactual* deceleration trajectory past `x_hazard` for this one measurement is a modeling convention, stated explicitly here so it is never mistaken for a claim about actual post-impact vehicle dynamics (which this project does not model — see `vehicle_response_model.md`, "what this model explicitly does not represent").

**Why this does not double-count `impact_speed`:** the two metrics are evaluated at **different points on the trajectory** and in **different physical domains**. `impact_speed` is a velocity, evaluated at the real, wall-respecting crossing of `x_hazard`. `stopping_margin` is a distance, evaluated at the counterfactual full-stop point under continued integration. Under an idealised *constant*-deceleration assumption the two are related (`v_impact^2 = 2 * a_max * |stopping_margin|` near the boundary), but Phase 1A's `a(t)` is explicitly **not** constant (that is the entire point of `vehicle_response_model.md`) — so under the actual transient profiles, the two metrics carry genuinely independent information about the same trajectory (one about how far short/past, one about how fast at the actual crossing point), and both should be reported.

## `T_TOR_critical` (added Phase 0.3, Task 10)

**Is it mathematically and conceptually well-defined? YES**, and it does not require inventing a safety threshold, because it is anchored to a threshold the project already has for free: the `collision`/no-`collision` boundary itself (`stopping_margin = 0`), not an arbitrary buffer distance.

**Definition:** for a fixed vehicle-response profile and scenario (`v0`, road friction, driver parameters held at their Phase-1A values), `T_TOR_critical` is the TOR lead time at which `stopping_margin(TOR_lead_time) = 0` — the boundary value separating collision from no-collision as TOR lead time varies, all else held fixed.

**Well-definedness argument:** `stopping_margin` is monotonically increasing in TOR lead time for fixed `v0` and profile (more warning time strictly increases available stopping distance, all else equal, under the frozen open-loop model — there is no mechanism in `vehicle_response_model.md`/`control_input_definition.md` by which more TOR lead time could ever *reduce* available stopping distance). A strictly monotonic function has at most one root, so `T_TOR_critical` is unique when it exists (it may not exist — e.g. if the scenario is "hopeless" at every TOR lead time up to some practical maximum — that non-existence is itself a valid, reportable outcome, not a definitional failure).

**Closed-form derivation (R0/R2, pure-friction profiles only — see `analytical_sanity_check.md`):** using `D_stop = v0²/(2·a_max) + v0·(t1+t2+t3/2) - a_max·t3²/24` and `x_hazard = v0 · TOR_lead_time` (the hazard distance implied by a given TOR lead time at constant pre-brake speed `v0`), setting `stopping_margin = x_hazard - D_stop = 0` and solving:

```
T_TOR_critical = D_stop / v0 = v0/(2·a_max) + (t1 + t2 + t3/2) - a_max·t3² / (24·v0)
```

**This directly connects Experiment A to the mother question.** Since `D_stop` differs between R0 and R2 exactly as derived in `analytical_sanity_check.md`, and dividing by `v0 > 0` preserves inequalities, **`T_TOR_critical(R2) > T_TOR_critical(R0)` is analytically guaranteed** by the same logic that guarantees `D_stop(R2) > D_stop(R0)` — vehicle response architecture provably shifts the minimum safe handover-time boundary for any parameter values where `t_buildup` differs, before any simulation is run. As with `D_stop`, the *sign* of this shift is not a simulation finding; the *magnitude* (how many extra seconds of TOR lead time R2 requires relative to R0, under literature-anchored parameters) is. For R1 (`v_rolloff` active), no closed form was derived (see `analytical_sanity_check.md`), so `T_TOR_critical(R1)` remains a genuine simulation/numerical question, not an algebraic one.

**Recommended status:** add `T_TOR_critical` as a **secondary, derived** Phase-1A outcome (computed from the same trajectory data as the four primary outcomes, not requiring new simulation machinery) — it is the natural quantity for connecting a Gate A result back to a handover-policy recommendation, and costs nothing extra to compute once `stopping_margin` is implemented.

### Formal freeze (Phase 0.4, Task 5)

**Independent variable being varied:** `TOR_lead_time` alone, holding `v0`, road friction, `t_reaction`, withdrawal policy, and vehicle-response profile fixed at their scenario-grid values. `x_hazard := v0 · TOR_lead_time` is the implied hazard distance.

**Fixed scenario state:** everything else in `docs/CAUSAL_MODEL.md`'s CONTROLLED row, plus the specific withdrawal policy and vehicle-response profile under test (`T_TOR_critical` is computed *per* (policy, profile, scenario) combination, not as a single global number).

**Safety criterion — two mathematically transparent criteria, not one invented regulatory threshold, per the task instruction:**
- **Criterion 1 (collision-free boundary):** smallest `TOR_lead_time` such that `stopping_margin ≥ 0` (equivalently, `collision = False`). The loosest, most literal criterion — "did not physically make contact."
- **Criterion 2 (resolvable-margin boundary):** smallest `TOR_lead_time` such that `stopping_margin ≥ dt · v(t_stop)` — i.e. a margin at least as large as one simulation timestep's worth of travel at the vehicle's own speed near the stopping point. This is **not** an invented safety-engineering number; it is tied to the simulator's own numerical resolution (the same `dt`-halving comparator already used in `gate_A_preregistration.md` Comparator B), so Criterion 2 answers "is the boundary crossing robust to the simulator's own discretization, or a knife-edge artifact of it?" — a question about numerical trustworthiness, not a claim about real-world safety margins. Report both criteria; do not collapse them into one number.

**Numerical search procedure:** for R0/R2/W0 (closed form exists), solve directly via the formula above — no search needed. For any profile/policy combination without a closed form (R1 with `v_rolloff` active; any A1 withdrawal-coast case where `a_coast > 0` interacts with `v_rolloff`), use bisection over `TOR_lead_time` within a bounded, pre-registered search range `[TOR_min, TOR_max]`, relying on the monotonicity property below to guarantee bisection converges to the unique root.

**Monotonicity — proven for the current model, not assumed:** in the current model, `D_stop` (and its `docs/CAUSAL_MODEL.md`-extended W1 form) does **not** depend on `TOR_lead_time` at all — `TOR_lead_time` enters the problem *only* through `x_hazard = v0 · TOR_lead_time`. Therefore `stopping_margin(TOR_lead_time) = v0·TOR_lead_time - D_stop` is **exactly linear** in `TOR_lead_time` with slope `v0 > 0`, which proves strict monotonicity rigorously rather than assuming it. **This proof is conditional on the current model** — if a later phase makes `t_reaction` or driver behaviour depend on how much warning was given (a real, literature-supported phenomenon — L001/L002 show TOR budget affects behaviour), monotonicity would need to be re-derived, not inherited.

**If no safe solution exists within the tested range:** because `stopping_margin` is linear and unbounded above in `TOR_lead_time` in the current model, a mathematical solution always exists as `TOR_lead_time → ∞` — so "no solution" in practice means `T_TOR_critical` exceeds the pre-registered, practically-meaningful upper search bound (e.g. tens of seconds, not a real TOR design range), not a true non-existence. Report this explicitly as `"T_TOR_critical > TOR_max (search bound), not a hopeless scenario in the mathematical sense"` — do not report an extrapolated number, and do not conflate this with a genuinely unrecoverable scenario (which would require `a_max`, `t_reaction`, or the profile parameters themselves to change, not just more warning). A future nonlinear model (e.g. one where reaction time degrades with excessive warning-induced complacency) could produce genuine non-existence — flag this as a modeling-assumption dependency, not a current limitation.

**If every tested TOR is safe:** report `T_TOR_critical ≤ TOR_min` (the lower bound of the tested/searched range) and state `TOR_min` explicitly — never report this as "zero risk," since it only means the scenario is safe at the tightest warning time actually tested, not at zero warning.

## Summary table

| metric | domain | defined when | edge-case handling |
|---|---|---|---|
| `collision` | boolean | always | derived: `stopping_margin < 0` |
| `TTC_min` | seconds | always (may be `+inf`-excluded if `v=0` throughout) | undefined instants excluded from min, not zero-filled |
| `stopping_margin` | metres, signed | always | continues counterfactual integration past `x_hazard`; not clipped at the wall |
| `impact_speed` | m/s | only if `collision = True` | `NaN` (never 0) when no collision |
