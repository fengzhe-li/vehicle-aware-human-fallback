# R3B scientific / mathematical gate review

**Date:** 2026-09-24. **Reviewed state:** HEAD `c7a44bf` (`audit/research-baseline-restructure`). Review only: no engine change, no scenario rerun, no new t1/t3 ranges.

## Erratum (2026-09-24, gate engineering)

The finite-difference scan used for §1–2 (6–8 points per dimension) was too coarse. The exact analytic-derivative guard (`src/metrics/braking_derivatives.py`, about 1e6 grid points per case) finds that the **t1 ≤ 4 s supplement is not monotone** in two cases: 60 km/h, μ 0.5, both P2 branches. There dT_required/dt1 ranges from −0.030 to +0.73 (+0.96 for AUTH_UNCERTAIN), with 1,701 and 1,162 grid lines reversing sign. The statement "+0.010 (still monotone)" in §1 and the claim in §2 that the supplement lies inside the monotone domain are therefore **withdrawn**.

- **Main domain:** all 30 cases pass the guard (P2 minimum dT/dt1 = +0.040, unchanged).
- **Committed numbers for the two cases:** a global check (9-point grid plus 40 multi-start bounded optimisations for each of min and max) reproduces the corner values exactly (min 2.376852 s; max 5.188854 / 6.385743 s). All ten supplementary classifications are unchanged. The committed supplement values are therefore **correct but not guaranteed by the corner method**. The sign reversal occurs at high `a_sup`, where T_required is small, so it does not control the extremes.
- **Consequence:** with the guard, a rerun **fails closed** on the supplement for these two cases. How to handle the supplement (constrained/global bound search, dropping it, or reshaping it) is a scientific decision and has not been taken.
- **Resolution (D025, Option A):** these two cases are now bounded by the stationary-point t1 method (`stationary_point_t1_bound`), which reproduces the global-search values exactly. The supplement is evaluated separately from the main domain in `run()` and cannot block it.
- **Final (D026):** the gate conditions are met; the authorised rerun reproduced every committed bound and label (report §13).

## 0. Scope correction: which implementation was reviewed

Several premises of the gate request describe the **stashed external draft** (`stash@{0}`), not HEAD:

| Gate premise | Stashed draft | HEAD |
|---|---|---|
| hyperrectangle corners with `t_authority` clamped to `t1` | yes (`t_auth = min(max(0, t_authority), t_reaction)`) | **no**: authority is reparameterised as `t_authority = f · t1`, `f ∈ [0, 1]` (`r3b_braking_bounds.profile`) |
| `worst_margin >= 0 ⇒ ROBUSTLY_SATISFIED` | yes (`ClassificationStatus` docstring) | **no**: `classify` uses `worst > 0`; exactly zero is PARAMETER-SENSITIVE |
| P0 / P1 / P2 members of `WithdrawalPolicy` | yes | **no**: enum is `{W0, W1}` only; branches are `PreControlProfile` values |

The R3B scenario grid **has already been run and committed** at HEAD (`da7230e` code, `fe34ffc` outputs) under the previous R3B instruction. This review treats those outputs as **provisional** until the gate conditions below are met.

## 1. Constrained interval enumeration

**The draft's clamping method is incomplete.** Box corners plus clamping do not generate all vertices of `{0 ≤ t_a ≤ t_a,max, t1 ∈ [t1_lo, t1_hi], t_a ≤ t1}`. In the counterexample, (2, 2) is never generated. It is not scientifically defensible and must not be adopted.

**HEAD's reparameterisation.** With no independent upper bound on `t_authority`, the feasible set is `{0 ≤ t_a ≤ t1, t1 ∈ [t1_lo, t1_hi]}`. The map `(f, t1) ↦ (f·t1, t1)` sends the four box corners exactly to the four polytope vertices `(0, t1_lo), (0, t1_hi), (t1_lo, t1_lo), (t1_hi, t1_hi)`. If a separate absolute `t_authority` interval is ever introduced, as in the counterexample, this parameterisation cannot represent it. General constrained-vertex enumeration would then be required.

**But vertices are not the real issue.** `T_required` is nonlinear, so vertex arguments from linear programming do not apply. Corner evaluation gives the exact box minimum and maximum if `T_required` is **monotone along every coordinate for every fixing of the others** (coordinatewise monotone). The direction may differ between coordinates. Under that condition, the extremes of each one-dimensional section lie at endpoints, and by recursion the extremes over the box lie at corners.

**Analytic domain conditions** (`D` = stopping distance, `v_e` = speed at effective control, `a_e = min(u · a_max, μg)`, `d_b'(v) = v / a_e + t2 + t3/2`):

| Coordinate | Sign of ∂D | Condition |
|---|---|---|
| `t2` | ≥ 0 | always (`= v_e`) |
| `t3` | ≥ 0 | `v_e ≥ a_e · t3 / 6` (standstill inside the ramp: always) |
| `a_max`, `u` | ≤ 0 | always; friction saturation only flattens (derivative 0), it cannot reverse the sign |
| `a_drag`, `a_sup` (pre-control decelerations) | ≤ 0 | always |
| `f` (authority fraction) | sign of `a_after − a_before` | constant over the box: P0 always; P2 requires `a_sup,lo ≥ a_drag,hi` |
| `t1` at fixed `f` | `f·[v_ins − a_b(τ₂ + d_b'(v_e))] + (1 − f)·[v_e − a_a · d_b'(v_e)]` must not change sign | **the binding condition for P2**: it fails when automation support is strong relative to `a_e`, because delaying the takeover then *removes* the handover dead time `t2 + t3/2` |

Standstill during pre-control makes `D` constant in the later parameters. That is weakly monotone, and `D` stays continuous across regimes.

**Numerical verification on the R3B domain** (8 points per dimension, all 30 cases, every partial derivative):
- all partial derivatives keep a constant sign;
- no non-monotone grid line;
- analytic preconditions hold: `t3` condition minimum 5.85 m/s; P2 `f` condition `a_sup − a_drag` ≥ 0.41 m/s².

| Case | Minimum dT_required / dt1 in P2 |
|---|---|
| committed intervals (`a_sup` ≤ 3.0, t1 ≤ 3.0) | +0.040 |
| supplementary t1 ≤ 4.0 s | +0.010 (still monotone; dense check passes) |
| `a_sup` upper bound ≥ 3.5 m/s² (60 km/h, μ 0.5, t1 ≤ 4) | **−0.08 to −0.23: not monotone; corner bounds invalid** |

**Verdict: B. Conditionally valid under stated domain assumptions.** HEAD's corner evaluation gives exact bounds only inside the coordinatewise-monotone domain above. It is not mathematically complete for general inputs (not A). It is not currently incomplete for the committed domain (not C). It becomes C if intervals are widened, notably P2 support ≥ 3.5 m/s², or if an independent `t_authority` interval is added. "Corner exhaustive" should not be used without this qualification.

## 2. Could the current R3B bounds be wrong?

**No committed bound is numerically wrong.** All committed cases, including the t1 ≤ 4 s supplement, lie inside the verified monotone domain. The existing 4-point interior check never found an interior extremum. The results are correct **because the chosen intervals happen to lie in the monotone domain**, and for P2 the margin is thin (+0.010 at t1 ≤ 4 s).

**Code gap:** the supplementary t1 = 4 s bounds (`b_alt` in `run`) are computed without enforcing `dense_check_ok`. It passes today, but nothing guards it.

## 3. Zero-margin classification

HEAD already treats exact zero as PARAMETER-SENSITIVE. **Adopted design: B.**
- ROBUSTLY SATISFIED if `worst_margin > ε`
- ROBUSTLY UNSATISFIED if `best_margin < −ε`
- PARAMETER-SENSITIVE otherwise
- plus a separate `boundary_flag = |worst| ≤ ε or |best| ≤ ε`

**Why:**
- "Robustly" means robust over the stated parameter box (epistemic intervals). It does not mean a physical safety margin.
- The physical margin is already inside the success definition (2.0 m standstill margin).
- A bound at zero is the boundary of the deterministic necessary condition. It cannot be distinguished within numerical tolerance, so it is not robust.

**Tolerance:** ε = **0.01 s**. The closed form is exact to about 1e-12 s. Model verification (closed form vs simulator) allows 1e-3 relative in `D_stop`, i.e. ≤ 0.0075 s for T_required ≤ 7.5 s, so ε exceeds the verification tolerance. At 130 km/h, ε corresponds to 0.36 m.

**Effect on committed results:** none. The smallest |margin| is 0.047 s, so no label or flag changes.

## 4. Authority-transfer semantics

The R3B longitudinal model has **no shared control**. At `t_authority`, three things happen together, **by assumption (exclusive handover)**:
- the automation's longitudinal command ends (C);
- a driver longitudinal command becomes able to act (A);
- the driver becomes the only, hence dominant, longitudinal controller (B).

**Definition adopted:** `t_authority` is the instant at which the automation's longitudinal command ceases and any driver longitudinal command becomes the one applied (exclusive, non-shared handover). This matches R157 deactivation (§6.2.5). R157's braking override while the system is active (§6.3.2) is a shared-control interval that R3B represents only by its end point, i.e. the branch with authority at effective control. Authority timing is an input assumption and is never inferred from D003.

| Question | Answer |
|---|---|
| First human input before `t_authority`? | **Physically possible**, under ignored-input semantics: e.g. holding the wheel or a pedal input below the override threshold. Allowed; first input is unordered relative to authority |
| `t_authority` before first human input? | **Physically possible**: deactivation by holding the steering control with attentiveness confirmed (R157 §6.2.5.2(b)) before any pedal input; P1 release. Allowed |
| Effective control before `t_authority`? | **Impossible by definition** in R3B (exclusive authority). Possible under shared control, which is out of scope |
| Effective control before first input? | **Impossible by definition** (effective input is a human input) |

**Invariant decision:** keep `0 ≤ t_authority ≤ t_effective` and `0 ≤ t_first_input ≤ t_effective`, with first input unordered relative to authority. This is what `HandoverTimeline` enforces. No change.

## 5. Policy / authority interaction

| Branch | Before `t_authority` | At `t_authority` | Driver braking acts | `a_pre` belongs to |
|---|---|---|---|---|
| P0 | automation controls longitudinal motion and holds speed (propulsion continues; net 0) | automation command ends; vehicle coasts on drag | from `t_eff` (+ `t2`, ramp `t3`) | policy (0) on `[0, t_a)`, vehicle response (drag) on `[t_a, t_eff)`: an interaction |
| P1 | propulsion released at TOR; vehicle coasts on drag | no longitudinal change (lateral may stay automated; out of scope) | from `t_eff` | vehicle response |
| P2 | automation applies net `a_sup` (includes drag) | automation command ends; drag only | from `t_eff` | policy on `[0, t_a)`, vehicle response on `[t_a, t_eff)` |

**No double counting:**
- Each instant of `[0, t_eff)` has exactly one deceleration source.
- `t1 = t_eff` is the only human timing entering braking.
- `t_authority` only splits `[0, t_eff)`.
- After `t_eff`, only the braking stages act (drag is neglected there).
- P0/P2 with authority at TOR reduce exactly to P1. This is tested.

## 6. Legacy WithdrawalPolicy cleanup

At HEAD the enum is `{W0, W1}`, and the P-branches are **not** enum members. The risks the audit named do not exist at HEAD:
- enum used with an implicit `a_pre = 0`;
- legacy W0/W1 logic leaking into R3B paths. The simulator requires `timeline` and `pre_control` together, and `calculate_acceleration` raises if `pre_control` has no `t_authority`.

**Timing: C (architectural hygiene), already satisfied.** Recommended guard: a test asserting the enum members are exactly `{W0, W1}`, so the draft pattern cannot be re-introduced.

## 7. R3A brittle test replacement

HEAD replaced `"u_target" not in src` with `"u_brake" in src`. That is still a source-token assertion. Recommended replacement (behavioural and provenance invariants, most already implemented in `tests/test_r3b_model_corrections.py` and `tests/test_r3b_bounds.py`):
- u = 1 reproduces the legacy saturated case bit-for-bit (`test_legacy_nominal_case_reproduced_by_corrected_model`);
- u < 1 scales the steady deceleration as `min(u·a_max, μg)` (`test_command_propagates_to_vehicle_response`);
- the command is recorded per state and in the result (`commands`, `u_brake`);
- human braking strength stays blocked: registry `u_eff` has synthesis entry NO, and `r3b.BLOCKED_INPUTS` includes `u_eff` (`test_no_blocked_parameter_enters_computation`);
- the R3A test keeps only the registry/status checks. The historical freeze condition stays documented in the R3A report, not asserted on source tokens.

## 8. Reporting consistency

**Confirmed:** prose classifications should be generated from `results.csv` / `policy_comparison.csv`. Required checks:
1. the TTC pattern table is rebuilt from `results.csv` and compared with the report fragment;
2. the t1-sensitivity list equals the rows where `classification != classification_if_t1_high_4s`;
3. policy-change lists and counts equal `policy_comparison.csv`;
4. the classification counts in the report equal `summary.json`;
5. a test fails on any divergence.

This is a reporting-integrity requirement, not a model change.

## 9. Gate verdict

| # | Item | Verdict |
|---|---|---|
| 1 | Constrained enumeration | **B: conditionally valid** inside the coordinatewise-monotone domain (§1). The draft's clamping method is incomplete and not used |
| 2 | Current bounds wrong? | **No committed bound is wrong**; correctness depends on the intervals lying in the monotone domain (thin for P2) |
| 3 | Required engine/test changes | (a) **enforce the monotonicity precondition in code**: sign-constant partials on a grid per case, abort on violation; (b) enforce `dense_check_ok` for the t1 supplement; (c) ε = 0.01 s classification with boundary flag; (d) generated narrative with consistency test; (e) enum guard test; (f) R3A token test replaced by the behavioural checks; (g) constrained-vertex enumeration only if an absolute `t_authority` interval is ever used |
| 4 | Zero margin | **Design B**, ε = 0.01 s, separate boundary flag |
| 5 | `t_authority` | exclusive handover instant: automation longitudinal command ends and driver command becomes the one applied (A = B = C by assumption; shared control out of scope) |
| 6 | Timeline invariants | keep `t_authority ≤ t_effective`, `t_first ≤ t_effective`, first input unordered relative to authority |
| 7 | P0/P1/P2 | policy before `t_authority`, vehicle-only after; one deceleration source per instant; no double counting |
| 8 | Enum cleanup | not needed at HEAD (enum is W0/W1); add guard test |
| 9 | R3A test | replace token assertion with the behavioural and provenance invariants above |
| 10 | Reporting | generate narrative from machine-readable results, with consistency tests |
| 11 | Cleared to proceed? | **Not yet.** Proceed to final t1/t3 intervals, a re-frozen scenario set and interval-bounded evaluation only after changes 3(a)–(f) are implemented and tested. Any widening of the P2 support or t1 intervals must pass the monotonicity precondition, or the engine must switch to a global bound search. The committed `fe34ffc` outputs remain provisional until then. Their labels are expected to be unchanged |
