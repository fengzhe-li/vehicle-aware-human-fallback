# R3B: interval-bounded longitudinal braking recoverability slice

**Status:** Phase R3B, 2026-09-23.
- Model corrections: commit `028786b`.
- Analysis code: commit `da7230e`.
- Outputs: `results/R3B_braking_bounds/`.

**What this is:** a deterministic, braking-only, interval-bounded computation of `T_required^brake` for a stationary in-lane obstacle.

**What this is not:**
- a probability model
- a claim that human fallback succeeds
- a recoverability envelope or a "Human Fallback Safety Envelope"
- a statement about steering or combined recovery
- a statement about any production system

**Labels:** ROBUSTLY SATISFIED / PARAMETER-SENSITIVE / ROBUSTLY UNSATISFIED refer **only to this braking-only model**. They are never "safe / unsafe".

---

## 1. Model corrections (implemented before any result)

| Correction | Implementation | Verification |
|---|---|---|
| **Friction** | `effective_braking_deceleration = min(u · a_max · rolloff, μ·g)`, g = 9.81 m/s²; scenario `road_friction` is now applied; negative sign applied by the caller as before | non-binding at μ = 1.0 for a_max ≤ 9.81 (all legacy cases); μ = 0.5 caps at 4.905 m/s²; capability monotone in μ |
| **Authority timing** | `HandoverTimeline(t_authority, t_effective, t_first_input)` with 0 = t_TOR ≤ t_authority ≤ t_effective and first input ≤ t_effective (not ordered relative to authority). `PreControlProfile`: policy deceleration on [0, t_authority), vehicle-only deceleration on [t_authority, t_effective) | authority at TOR and delayed authority both representable; one deceleration source per interval |
| **Command path** | `driver.u_target` is applied to the vehicle model; `u_brake` is recorded in every state and in the result | u = 0.5 gives half the steady deceleration; u = 1 reproduces saturated braking |

**Legacy reproduction:**
- W0 and W1 simulations run through the new timeline path are **bit-identical** to the legacy path.
- The general closed form `stopping_distance_r3b_analytical` equals the legacy W0/W1 formulas to ≤ 3·10⁻¹⁴ m.
- All 167 pre-existing tests pass unchanged.
- The general closed form also handles standstill inside the pre-control phase or the ramp exactly.

**Deviation from the R3B-0 design note:** the note wrote `a = −u · a_lim` with `a_lim = min(a_max, μg)`. The R3B specification requires `min(requested, μg)` with requested = `u · a_max`, and that is what is implemented. The two orderings coincide for u = 1 (the only command used in this slice). They differ for partial commands on low friction: for example, at u = 0.5 and μg = 4.9, the note's ordering gives 2.45 m/s² and the implemented one 4.25 m/s².

**External draft:** an uncommitted draft of this phase appeared in the working tree during a pause in this session. It was not authored in this session.
- Its policy/authority semantics were inverted: the policy acted only *after* authority transfer, so every branch held speed before authority.
- Its friction ordering followed the R3B-0 design note (see above), not the R3B specification.

It was preserved in `git stash` ("EXTERNAL R3B infrastructure draft …") and not used.

---

## 2. Policy branches (counterfactual, not production policies)

| Branch | [0, t_authority) | [t_authority, t_effective) | Authority | Provenance |
|---|---|---|---|---|
| **P0 \| AUTH_AT_EFFECTIVE** | net 0 (speed held) | — | at effective braking (= legacy W0) | assumption branch |
| **P0 \| AUTH_UNCERTAIN** | net 0 | drag | f·t1, f ∈ [0, 1] | f: assumption (R157 §6.2.5.2 / §6.3.2 allow both extremes) |
| **P1** (passive release) | drag | drag | irrelevant (drag on both sides) | drag: EPA source; lift-off regen and engine braking excluded, so this is the powertrain-conservative passive case |
| **P2 \| AUTH_AT_EFFECTIVE** | a_sup ∈ [1.0, 3.0] m/s² | — | at effective braking | a_sup: assumption interval, kept below the R157 emergency-manoeuvre threshold 5.0 m/s² (§5.3.1.1) |
| **P2 \| AUTH_UNCERTAIN** | a_sup | drag | f·t1 | assumptions |

P0 and P2 with authority at TOR are **identical to P1** by construction (tested) and are not repeated. No interval has two deceleration sources, so `a_pre` is not double-counted. After effective control, drag is neglected (conservative).

## 3. Parameter classes

| Parameter | Class | Interval | Provenance |
|---|---|---|---|
| v0 | source-supported (scenario-defined) | 60 / 100 / 130 km/h | R157 00-series limit; D003; R157 Rev.1 limit |
| TTC = T_available^brake | source-supported (scenario-defined) | 2 / 3 / 5 / 7 / 10 s | R157 Annex 3 TTC 2 s; D003 7 s; others grid fill |
| μ | source-supported relation (a ≤ μg), scenario values | 1.0 / 0.5 | R157 Annex 3 reference friction; 0.5 = reduced-friction assumption |
| a_drag | source-supported | EPA 5–95% at the scenario speed: 60 km/h 0.126–0.227; 100 km/h 0.218–0.400; 130 km/h 0.310–0.590 m/s² | S07 |
| t2 | source-supported | 0.05–0.17 s | S20 (prior-phase record); within the R13-H 0.6 s bound |
| a_max | source-supported | 6.43–9.1 m/s² | R13-H floor; Greibe measured |
| **t1** | **assumption interval for sensitivity analysis** | 1.15–3.0 s (supplementary upper bound 4.0 s) | lower = R157 Annex 3 attentive-driver benchmark (not a takeover measurement); upper = scenario choice. **Not** t_button, Manual_Start or the meta-analysis takeover time |
| **t3** | **assumption interval for sensitivity analysis** | 0.3–1.2 s | informed by the R157 benchmark 0.6 s and Greibe non-professional pedal build-up; not a takeover measurement |
| **f_auth** | assumption | 0–1 | not identified from D003 |
| **a_sup** (P2) | assumption | 1.0–3.0 m/s² | bounded by the R157 5.0 m/s² EM threshold only |
| standstill margin | assumption | 2.0 m | success definition |
| u_brake | model condition | 1 | defines this slice |

**Blocked (asserted absent from the computation):** human takeover braking strength; braking jerk; ISO 15622 ACC limits; takeover-time distribution; engine braking; regen roll-off; lift-off regen; D003 vehicle properties.

## 4. Success condition and margins (frozen before computation)

- **Success:** the vehicle reaches standstill at least **2.0 m** before the stationary obstacle.
- `T_available^brake` = TTC at TOR (constant-velocity reference).
- `T_required^brake` = (D_stop + 2.0 m) / v0.
- Margin = `T_available − T_required`, in seconds; the distance margin is v0 × that.

**Classification:**
- **ROBUSTLY SATISFIED:** worst-case (conservative) margin > 0.
- **ROBUSTLY UNSATISFIED:** best-case (optimistic) margin < 0.
- **PARAMETER-SENSITIVE:** otherwise (zero counts as the boundary).

## 5. Interval propagation and cross-check

- **Method:** exact minimum and maximum over **all corners** of the parameter box (32–128 corners per case). No distributions.
- **Why corners suffice:** `D_stop` is monotone in every parameter (signs tested), so the extremes lie on corners. This was **verified** against a 4-point-per-dimension interior grid in every case.
- **Optimistic (min T_required) corner:** t1, t2, t3 low; a_max, a_drag, a_sup high; for P0 authority early, for P2 authority late.
- **Conservative corner:** the opposite of each.
- **Cross-check:** closed form vs simulator (dt = 1 ms) at the optimistic, conservative and midpoint corners of all 30 (speed, μ, branch) cases. Maximum relative difference in `D_stop` is **2.2·10⁻⁴**, against a tolerance of 10⁻³ (the A0 criterion).

## 6. Results

The following blocks are generated from stored CSV results by
`python -m src.provenance.r3b_reporting --write`. This command does not run the study.
Labels apply only to this braking-only model.

`T_required^brake` bounds and midpoint in seconds:

<!-- R3B:bounds:START -->
| Speed (km/h) | μ | Branch | Min (s) | Mid (s) | Max (s) |
| --- | --- | --- | --- | --- | --- |
| 60 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 3.1678 | 4.372 | 5.5713 |
| 60 | 0.5 | P0\|AUTH_UNCERTAIN | 3.103 | 4.3239 | 5.5713 |
| 60 | 0.5 | P1 | 3.103 | 4.2647 | 5.4432 |
| 60 | 0.5 | P2\|AUTH_AT_EFFECTIVE | 2.3769 | 3.2522 | 4.6061 |
| 60 | 0.5 | P2\|AUTH_UNCERTAIN | 2.3769 | 3.6777 | 5.4432 |
| 60 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 2.3837 | 3.7423 | 5.1629 |
| 60 | 1.0 | P0\|AUTH_UNCERTAIN | 2.3432 | 3.7078 | 5.1629 |
| 60 | 1.0 | P1 | 2.3432 | 3.6621 | 5.0529 |
| 60 | 1.0 | P2\|AUTH_AT_EFFECTIVE | 1.8834 | 2.8953 | 4.3297 |
| 60 | 1.0 | P2\|AUTH_UNCERTAIN | 1.8834 | 3.206 | 5.0529 |
| 100 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 4.2529 | 5.4594 | 6.663 |
| 100 | 0.5 | P0\|AUTH_UNCERTAIN | 4.147 | 5.3828 | 6.663 |
| 100 | 0.5 | P1 | 4.147 | 5.295 | 6.4778 |
| 100 | 0.5 | P2\|AUTH_AT_EFFECTIVE | 3.497 | 4.4491 | 5.8392 |
| 100 | 0.5 | P2\|AUTH_UNCERTAIN | 3.497 | 4.828 | 6.4778 |
| 100 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 2.947 | 4.4141 | 5.9881 |
| 100 | 1.0 | P0\|AUTH_UNCERTAIN | 2.884 | 4.3615 | 5.9881 |
| 100 | 1.0 | P1 | 2.884 | 4.2973 | 5.8342 |
| 100 | 1.0 | P2\|AUTH_AT_EFFECTIVE | 2.4952 | 3.6921 | 5.3016 |
| 100 | 1.0 | P2\|AUTH_UNCERTAIN | 2.4952 | 3.9548 | 5.8342 |
| 130 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 5.0859 | 6.2933 | 7.4983 |
| 130 | 0.5 | P0\|AUTH_UNCERTAIN | 4.9344 | 6.1858 | 7.4983 |
| 130 | 0.5 | P1 | 4.9344 | 6.0661 | 7.2528 |
| 130 | 0.5 | P2\|AUTH_AT_EFFECTIVE | 4.3421 | 5.3208 | 6.7235 |
| 130 | 0.5 | P2\|AUTH_UNCERTAIN | 4.3421 | 5.6631 | 7.2528 |
| 130 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 3.3886 | 4.9356 | 6.6227 |
| 130 | 1.0 | P0\|AUTH_UNCERTAIN | 3.3002 | 4.8629 | 6.6227 |
| 130 | 1.0 | P1 | 3.3002 | 4.7776 | 6.4216 |
| 130 | 1.0 | P2\|AUTH_AT_EFFECTIVE | 2.9535 | 4.2569 | 5.987 |
| 130 | 1.0 | P2\|AUTH_UNCERTAIN | 2.9535 | 4.4895 | 6.4216 |
<!-- R3B:bounds:END -->

<!-- R3B:classifications:START -->
Scenario count: 150. PARAMETER-SENSITIVE: 47; ROBUSTLY SATISFIED: 58; ROBUSTLY UNSATISFIED: 45.

| TTC (s) | Speed (km/h) | μ | P0\|AUTH_AT_EFFECTIVE | P0\|AUTH_UNCERTAIN | P1 | P2\|AUTH_AT_EFFECTIVE | P2\|AUTH_UNCERTAIN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 60 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 2.0 | 60 | 1.0 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 2.0 | 100 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 2.0 | 100 | 1.0 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 2.0 | 130 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 2.0 | 130 | 1.0 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 3.0 | 60 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 3.0 | 60 | 1.0 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 3.0 | 100 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 3.0 | 100 | 1.0 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 3.0 | 130 | 0.5 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED |
| 3.0 | 130 | 1.0 | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 5.0 | 60 | 0.5 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| 5.0 | 60 | 1.0 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| 5.0 | 100 | 0.5 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 5.0 | 100 | 1.0 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 5.0 | 130 | 0.5 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 5.0 | 130 | 1.0 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE |
| 7.0 | 60 | 0.5 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 7.0 | 60 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 7.0 | 100 | 0.5 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 7.0 | 100 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 7.0 | 130 | 0.5 | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| 7.0 | 130 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 60 | 0.5 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 60 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 100 | 0.5 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 100 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 130 | 0.5 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |
| 10.0 | 130 | 1.0 | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED | ROBUSTLY SATISFIED |

Supplementary t1 changes: 10 (TTC 5.0 s: 1, TTC 7.0 s: 9).

| Scenario ID | Stored classification | Stored classification with t1 upper bound 4 s |
| --- | --- | --- |
| v60_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc5.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v100_mu0.5_P0\|AUTH_AT_EFFECTIVE_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v100_mu0.5_P0\|AUTH_UNCERTAIN_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v100_mu0.5_P1_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v100_mu0.5_P2\|AUTH_UNCERTAIN_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v130_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P0\|AUTH_AT_EFFECTIVE_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P0\|AUTH_UNCERTAIN_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P1_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P2\|AUTH_UNCERTAIN_ttc7.0 | ROBUSTLY SATISFIED | PARAMETER-SENSITIVE |
<!-- R3B:classifications:END -->

## 7. Physical sensitivity vs uncertainty width

Stored midpoint elasticities and one-at-a-time swing shares, grouped by parameter and friction.
These are descriptive ranges across the stored branch/speed cases, not new evaluations.

<!-- R3B:sensitivity:START -->
| Parameter | μ | Elasticity range | OAT swing share range (fraction) |
| --- | --- | --- | --- |
| a_drag | 0.5 | -0.03704 to 0.00000 | 0.00000 to 0.06045 |
| a_drag | 1.0 | -0.03274 to 0.00000 | 0.00000 to 0.03129 |
| a_max | 0.5 | 0.00000 to 0.00000 | 0.00000 to 0.00000 |
| a_max | 1.0 | -0.47214 to -0.21283 | 0.08898 to 0.25533 |
| a_sup | 0.5 | -0.31194 to -0.09016 | 0.16686 to 0.47380 |
| a_sup | 1.0 | -0.26957 to -0.08146 | 0.10338 to 0.33578 |
| f_auth | 0.5 | -0.13766 to 0.01836 | 0.04321 to 0.31502 |
| f_auth | 1.0 | -0.11960 to 0.01624 | 0.02834 to 0.23699 |
| t1 | 0.5 | 0.19395 to 0.47461 | 0.33401 to 0.76973 |
| t1 | 1.0 | 0.30721 to 0.55448 | 0.37441 to 0.66599 |
| t2 | 0.5 | 0.01748 to 0.02586 | 0.03228 to 0.05053 |
| t2 | 1.0 | 0.02229 to 0.02966 | 0.03153 to 0.04342 |
| t3 | 0.5 | 0.05858 to 0.08440 | 0.11589 to 0.18620 |
| t3 | 1.0 | 0.07394 to 0.09437 | 0.11212 to 0.15315 |
<!-- R3B:sensitivity:END -->

Interpretation remains manually authored: the t1 assumption interval is a major contributor
to uncertainty width. These intervals are assumptions, not measured takeover distributions.

## 8. Effect of the transition-policy branches

<!-- R3B:policy:START -->
Classification changes relative to P0|AUTH_AT_EFFECTIVE: 13 scenario/branch comparisons.

| Scenario ID | Reference classification | Branch classification |
| --- | --- | --- |
| v60_mu1.0_P2\|AUTH_AT_EFFECTIVE_ttc2.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v60_mu1.0_P2\|AUTH_UNCERTAIN_ttc2.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v60_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc3.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v60_mu0.5_P2\|AUTH_UNCERTAIN_ttc3.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P2\|AUTH_AT_EFFECTIVE_ttc3.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu1.0_P2\|AUTH_UNCERTAIN_ttc3.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v60_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc5.0 | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED |
| v60_mu1.0_P2\|AUTH_AT_EFFECTIVE_ttc5.0 | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED |
| v130_mu0.5_P0\|AUTH_UNCERTAIN_ttc5.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu0.5_P1_ttc5.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc5.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu0.5_P2\|AUTH_UNCERTAIN_ttc5.0 | ROBUSTLY UNSATISFIED | PARAMETER-SENSITIVE |
| v130_mu0.5_P2\|AUTH_AT_EFFECTIVE_ttc7.0 | PARAMETER-SENSITIVE | ROBUSTLY SATISFIED |

Stored policy deltas relative to the reference (seconds):

| Speed (km/h) | μ | Branch | Mid delta | Min delta | Max delta |
| --- | --- | --- | --- | --- | --- |
| 100 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 100 | 0.5 | P0\|AUTH_UNCERTAIN | -0.0766 | -0.1059 | 0.0 |
| 100 | 0.5 | P1 | -0.1644 | -0.1059 | -0.1852 |
| 100 | 0.5 | P2\|AUTH_AT_EFFECTIVE | -1.0103 | -0.7559 | -0.8238 |
| 100 | 0.5 | P2\|AUTH_UNCERTAIN | -0.6314 | -0.7559 | -0.1852 |
| 100 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 100 | 1.0 | P0\|AUTH_UNCERTAIN | -0.0526 | -0.063 | 0.0 |
| 100 | 1.0 | P1 | -0.1168 | -0.063 | -0.154 |
| 100 | 1.0 | P2\|AUTH_AT_EFFECTIVE | -0.722 | -0.4518 | -0.6865 |
| 100 | 1.0 | P2\|AUTH_UNCERTAIN | -0.4593 | -0.4518 | -0.154 |
| 130 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 130 | 0.5 | P0\|AUTH_UNCERTAIN | -0.1075 | -0.1515 | 0.0 |
| 130 | 0.5 | P1 | -0.2271 | -0.1515 | -0.2455 |
| 130 | 0.5 | P2\|AUTH_AT_EFFECTIVE | -0.9724 | -0.7438 | -0.7748 |
| 130 | 0.5 | P2\|AUTH_UNCERTAIN | -0.6302 | -0.7438 | -0.2455 |
| 130 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 130 | 1.0 | P0\|AUTH_UNCERTAIN | -0.0727 | -0.0884 | 0.0 |
| 130 | 1.0 | P1 | -0.158 | -0.0884 | -0.2011 |
| 130 | 1.0 | P2\|AUTH_AT_EFFECTIVE | -0.6787 | -0.4351 | -0.6358 |
| 130 | 1.0 | P2\|AUTH_UNCERTAIN | -0.4461 | -0.4351 | -0.2011 |
| 60 | 0.5 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 60 | 0.5 | P0\|AUTH_UNCERTAIN | -0.0482 | -0.0649 | 0.0 |
| 60 | 0.5 | P1 | -0.1073 | -0.0649 | -0.1281 |
| 60 | 0.5 | P2\|AUTH_AT_EFFECTIVE | -1.1198 | -0.791 | -0.9652 |
| 60 | 0.5 | P2\|AUTH_UNCERTAIN | -0.6944 | -0.791 | -0.1281 |
| 60 | 1.0 | P0\|AUTH_AT_EFFECTIVE | 0.0 | 0.0 | 0.0 |
| 60 | 1.0 | P0\|AUTH_UNCERTAIN | -0.0345 | -0.0405 | 0.0 |
| 60 | 1.0 | P1 | -0.0801 | -0.0405 | -0.1099 |
| 60 | 1.0 | P2\|AUTH_AT_EFFECTIVE | -0.847 | -0.5003 | -0.8332 |
| 60 | 1.0 | P2\|AUTH_UNCERTAIN | -0.5363 | -0.5003 | -0.1099 |
<!-- R3B:policy:END -->

These are counterfactual comparisons, not statements that any policy is safer.

## 9. Validity envelope (carried in `summary.json` and `provenance.json`)

- stationary longitudinal hazard fully blocking the ego lane
- no usable escape path: braking-only analysis
- deterministic point-mass longitudinal approximation
- full braking command after effective human control (a capability bound, not observed human braking)
- zero acceleration during the actuation delay, and drag neglected after effective control (conservative)
- drag held at its v0 value during pre-control (slightly optimistic, ≤ 0.6 m/s² over ≤ 3 s)
- authority timing, t1 and t3 are assumptions
- no lateral dynamics and no human steering strategy
- no probabilistic driver model; interval bounds are not confidence intervals
- no D003 vehicle calibration
- no claim about production automated-driving systems

## 10. Remaining blockers / readiness

- **Not ready for a true synthesis phase.** The inputs that decide most classifications are assumptions: t1 (effective braking onset after a TOR), authority timing and the P2 support level. The braking command u = 1 is a capability condition, not observed behaviour.
- **Also missing:** steering and combined recovery (geometry, gaps and steering authorship absent), and behavioural braking strength (blocked).
- **What would change this:** an empirical anchor for effective braking onset and braking strength in takeovers, from a dataset with driver-attributed control channels. That is not D003 (B17).

## 11. Recommended R3C scope (not started)

1. **Evidence acquisition for t1 and u_eff:** identify public takeover datasets with driver-attributed pedal channels, and audit their semantics under the observation-layer rules before using any value.
2. **Sensitivity presentation:** report the TTC at which each branch becomes ROBUSTLY SATISFIED as a function of the assumed t1 upper bound. This is deterministic and needs no new evidence.
3. **Lateral evidence plan:** only a data and geometry survey for `T_required^steer`; no lateral model.
4. Keep the recoverability envelope and any probabilistic synthesis gated.

---

## 12. Reconciliation of draft defects (post-review, 2026-09-23)

Verified against current code (HEAD), `results/R3B_braking_bounds/results.csv` and git history. No historical commit was rewritten.

| Item | Type | Origin | Status at HEAD |
|---|---|---|---|
| **A.** TTC 3 s, P2, 60 km/h, μ 0.5 is PARAMETER-SENSITIVE (both P2 branches) but was omitted from the narrative | **wording / report defect only**; code and `results.csv` were always correct | uncommitted report draft; the wrong row never appears in any commit (`git log -S` finds nothing); the report was first committed in `fe34ffc` already corrected | corrected; every row of the §6 TTC pattern table was re-checked against the full classification pivot |
| **B.** Self-contradictory sentence on the t1 = 4.0 s sensitivity ("all at TTC 7 s … plus one at 5 s") | **wording / report defect only**; `classification_if_t1_high_4s` was always correct (9 changes at 7 s, 1 at 5 s) | uncommitted report draft; never committed | corrected in `fe34ffc` |
| **C.** Friction ordering of the external draft (`u · min(a_max, μg)`) described as a defect | **retracted characterisation**, not a defect. The draft followed the R3B-0 design note; HEAD implements the R3B specification `min(u · a_max, μg)`. The two are identical for u = 1, the only command used in this slice | the wrong characterisation first appears in the **commit message of `028786b`** ("friction applied before the command") | superseded by this report (§1) and by D022/D023 |
| **D.** External draft: policy acted only *after* authority transfer; all branches held speed before authority | **genuine code defect in the external draft only**; confirmed in `stash@{0}` (`if t < t_authority: return 0.0`) | external uncommitted draft; never committed | not present at HEAD: `calculate_acceleration` applies `a_before_authority` before `t_authority` and `a_after_authority` after it; `test_authority_is_separate_from_tor_and_effective_control` and `test_policy_branches_collapse_consistently` pin this |

**Superseded commit-message wording (`028786b`):**
1. "friction applied before the command" as a defect of the external draft: retracted (item C).
2. "Implements docs/BRAKING_MODEL_CORRECTION_DESIGN.md corrections A–C": correct except for the deliberate friction-ordering deviation, now recorded in the design note header, §1 of this report, D022 and D023.

**Stale current-state wording corrected in this reconciliation:**
- the `src/handover/models.py` module docstring (said T_authority = 0 at TOR)
- `docs/SYSTEM_EVENT_STATE_SPECIFICATION.md` (header "nothing implemented", §5, braking deceleration ordering)
- `docs/BRAKING_MODEL_CORRECTION_DESIGN.md` header (deviation note)
- `docs/R3B0_SOURCE_AND_SPECIFICATION_HARDENING.md` §7–8 (pointer to R3B)
- the `README.md` layer-status rows A, C and D (still read "saturated emergency braking only" and "NOT STARTED beyond the narrow W0/W1 abstraction")

**Reporting consistency implemented:** Sections 6–8 are generated from stored CSV outputs; see [reporting contract](R3B_REPORTING_CONSISTENCY.md). Historical reconciliation above remains manually authored.

---

## 13. Final frozen configuration and authorised rerun (2026-09-24)

**Status: R3B complete** as an interval-bounded longitudinal braking recoverability slice. It is not a system-level recoverability result.

### 13.1 Frozen configuration (unchanged from the gate-reviewed configuration; drift check against the saved intervals: none)

| Item | Frozen value | Class |
|---|---|---|
| v0 | 60 / 100 / 130 km/h | source-supported (R157 00-series limit; D003; R157 Rev.1 limit) |
| TTC = T_available^brake | 2, 3, 5, 7, 10 s | 2 s (R157 Annex 3) and 7 s (D003): source-anchored; 3, 5, 10 s: explicit assumption (grid fill) |
| μ | 1.0 / 0.5 | 1.0: source-supported (R157 Annex 3 reference); 0.5: explicit assumption; relation a ≤ μg: source-supported |
| t1 | 1.15–3.0 s | explicit assumption (sensitivity interval) |
| t2 | 0.05–0.17 s | source-supported |
| t3 | 0.3–1.2 s | explicit assumption |
| a_max | 6.43–9.1 m/s² | source-supported |
| drag | EPA 5–95% at the scenario speed | source-supported |
| P0 / P1 / P2 | hold speed / passive drag / supported deceleration before authority; drag after authority | model condition (counterfactual branches) |
| P2 supported deceleration | 1.0–3.0 m/s² (below the R157 5.0 m/s² EM threshold) | explicit assumption |
| Authority timing | at effective control, or f·t1 with f ∈ [0, 1] | explicit assumption |
| Braking command u | 1 after effective control | model condition |
| Standstill margin | 2.0 m | explicit assumption (success definition) |
| Classification tolerance ε | 0.01 s (time margin) | model condition (numerical tolerance) |
| Main scenario set | 3 speeds × 5 TTC × 2 μ × 5 branches = 150 | — |
| t1 = 4 s supplement | same box with the t1 upper bound 4.0 s; per-case bounds and classification | **sensitivity-only** |

### 13.2 Methods and rerun
- **Main domain:** all 30 (speed, μ, branch) cases use `monotone_endpoint_bound`; the guard passes everywhere (P2 minimum dT/dt1 = +0.040).
- **Supplement:** 28 cases use `monotone_endpoint_bound`. 60 km/h, μ 0.5, P2 | AUTH_AT_EFFECTIVE and P2 | AUTH_UNCERTAIN use `stationary_point_t1_bound`. Fail-closed behaviour remains active.
- **First attempt failed:** a CSV writer defect for branch-dependent guard columns. Partial outputs were restored and the defect fixed in `a4f2cc4`. The canonical rerun used code `a4f2cc4` with a clean tree (`provenance.json`).
- **Numerical change vs the pre-gate outputs:** none. All pre-existing columns of `results.csv` are byte-identical. New fields: `boundary_flag` and `t1_high_4s_bound_method` (results); `bound_method`, `t1_high_4s_bound_method` and `t_required_min_if_t1_high_4s` (bounds); `monotonicity_guard.csv`; and the ε-based classification rule and `bound_methods` in `summary.json`.
- **Verification:**
  - `pytest -m r3b_study` (deterministic reproduction) passes;
  - the full default suite passes;
  - `python -m src.provenance.r3b_reporting --write` changed no generated block, and the consistency check passes.

### 13.3 Interpretation (within the braking-only model; manually authored, checked against the canonical outputs)
- **TTC** dominates the labels:
  - TTC 2 s: 28 ROBUSTLY UNSATISFIED, 2 PARAMETER-SENSITIVE
  - TTC 3 s: 16 unsatisfied, 14 sensitive
  - TTC 5 s: mostly PARAMETER-SENSITIVE (27; 2 satisfied, 1 unsatisfied)
  - TTC 7 s: 26 ROBUSTLY SATISFIED, 4 sensitive
  - TTC 10 s: all 30 ROBUSTLY SATISFIED
- **Speed:** the midpoint T_required rises with v0 (P0 at authority-at-effective, dry: 3.74 / 4.41 / 4.94 s; μ 0.5: 4.37 / 5.46 / 6.29 s). ROBUSTLY UNSATISFIED counts rise from 11 (60 km/h) to 15 (100) and 19 (130).
- **Friction:** μ 0.5 binds braking at 4.905 m/s² and removes all sensitivity to a_max. It raises the midpoint T_required by 0.36–1.36 s depending on branch and speed (smallest for P2 at 60 km/h, largest for P0 at 130 km/h). Unsatisfied counts rise from 16 (μ 1.0) to 29 (μ 0.5).
- **Policy branches** (counterfactual; midpoint change relative to P0 with authority at effective control):
  - P1: −0.08 to −0.23 s
  - P0 with uncertain authority: −0.03 to −0.11 s
  - P2 with authority at effective control: −0.68 to −1.12 s
  - P2 with uncertain authority: −0.45 to −0.69 s

  The pre-control behaviour matters only while the automation keeps authority. No policy is described as safer.
- **Parameter sensitivity:** the T_required interval width is 2.2–3.5 s, driven mainly by the t1 assumption interval (see §7). A scenario is PARAMETER-SENSITIVE exactly when its TTC lies inside that interval.
- **D003-like case** (100 km/h, TTC 7 s): ROBUSTLY SATISFIED in every branch. The worst-case margin is +1.01 s (dry) and +0.34 s (μ 0.5) for P0 with authority at effective control. This says nothing about D003 drivers' actual braking.
- **t1 = 4 s supplement** (sensitivity-only): 10 scenarios move from ROBUSTLY SATISFIED to PARAMETER-SENSITIVE (9 at TTC 7 s, 1 at 5 s). The TTC 7 s conclusion at higher speed or reduced friction therefore depends on the assumed t1 upper bound.
- **Non-monotone supplement cases:** the two P2 cases at 60 km/h, μ 0.5 changed **methodologically only**. Their bounds (2.3769–5.1889 s and 2.3769–6.3857 s) are identical to the earlier corner values and to the global search. Within them, a later takeover can *reduce* required time under strong automation support: this is model physics, not an artefact.
- **Boundary band:** no scenario has a margin within ±0.01 s (closest 0.047 s); `boundary_flag` is false everywhere.

### 13.4 Claim boundaries

| Category | Content |
|---|---|
| **A. Exact within-model findings** | For the stated boxes, T_required^brake bounds are exact (guarded corner method; stationary-point t1 method for the two escalated supplement cases), cross-checked against the simulator to 2.2e-4 relative. The labels follow from these bounds and ε |
| **B. Sensitivity findings** | Width driven mainly by t1; a_max matters only on dry roads; the policy effect depends on authority timing; the t1 = 4 s supplement changes 10 labels |
| **C. Source-supported inputs** | t2, a_max, drag, μ = 1.0 reference and the friction relation, v0 anchors, TTC 2 s and 7 s anchors |
| **D. Explicit modelling assumptions** | t1, t3, authority timing, P2 support level, standstill margin, μ = 0.5, TTC grid fill, u = 1, counterfactual branches, stationary in-lane obstacle, no escape path |
| **E. Not identifiable** (from D003 or the public sources checked) | driver effective-braking onset and braking strength in takeovers (B17); authority-transfer timing; D003 vehicle and automation behaviour; hazard geometry and escape paths; engine braking and regen roll-off; regen/friction blending |

**Not supported:** any statement about full takeover recoverability, steering or combined recovery, driver-performance prediction, production systems, or probabilities. The slice gives a braking-only necessary condition under the model.
