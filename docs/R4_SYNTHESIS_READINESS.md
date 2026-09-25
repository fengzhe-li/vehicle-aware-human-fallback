# R4: system integration boundary / synthesis readiness

**Status:** Phase R4 audit, 2026-09-24.
- No synthesis, no combined score, no probabilities.
- No inferred D003 authority or braking variables.
- Repository evidence only.

**Machine-readable:**
- `research/R4_SYNTHESIS_READINESS_MATRIX.csv` (21 candidate variables)
- `research/R4_CROSS_LAYER_LINKS.csv` (18 links; 2 design-intent links added by the internal source-of-truth audit)

Both are checked by `tests/test_r4_readiness.py`.

---

## 1. Current evidence layers

**A. Human (R2A–R2C)**
- Validated event timing:
  - `t_button` = Manual_Start − TOR: median 1.65 s, IQR 1.25–2.00, n = 492
  - TOR → validated lane change: median 6.40 s, IQR 5.45–7.70, n = 477
  - handback timing: TOR → handback median 18.85 s
- Repeated exposure: `t_button` decreases by 0.033 s per exposure (95% CI −0.058, −0.007). This is robust to excluding multi-TOR trials and to carry-over adjustment (carry-over not detected), but modest: on exposures 2–9 the cluster-robust CI includes 0.
- Participant covariates: no association survives Holm correction (n = 57; secondary re-analysis). The questionnaire-id join is strongly supported but not explicit.
- **Blocked (B17):** first human input, effective braking onset, braking strength, steering onset and correction counts. The accelerator, brake and steering channels are not driver-only.
- **Unresolved:** Manual_Start authority semantics (B7).

**B. Vehicle (R3A–R3B)**

| Quantity | Status |
|---|---|
| drag | EPA distribution by speed (100 km/h: 0.22–0.40 m/s²) |
| t2 | 0.05–0.17 s, source-supported |
| t3 | human × vehicle; assumption interval 0.3–1.2 s |
| a_max | 6.43–9.1 m/s², source-supported |
| friction limit | a ≤ μg |
| command | u = 1 (model condition) |
| D003 vehicle and automation model | undocumented (V21, T14); D003 kinematics are achieved motion, not capability |

**C. Automation transition**
- TOR (observable, protocol-resolved).
- Authority transfer is latent and an explicit assumption. The rules come from R157 (§6.2.5 deactivation, §6.3 override); D003 timing is unknown.
- P0/P1/P2 are counterfactual branches: policy deceleration before authority, vehicle-only after.
- Source-supported bounds:
  - R157 continued operation during the transition demand (§5.4.3);
  - demand above 5.0 m/s² counts as an emergency manoeuvre (§5.3.1.1);
  - MRM earliest 10 s after the transition demand; MRM deceleration demand aim 4.0 m/s².
- The P2 level (1–3 m/s²) is an assumption.
- D003 automation behaviour at TOR is cell-specific and undocumented (B17).

**D. Scenario / hazard**

| Quantity | D003 status |
|---|---|
| speed at TOR | observable (median 25.0 m/s, 19.2–27.8) |
| TTC | observable within its domain (TOR at TTC ≈ 7 s) |
| hazard distance | partial (reference point undocumented) |
| friction | not reported |
| geometry, escape path, target-lane gaps | not identifiable (B10, B5, adjacent-lane zeros) |
| steering availability | real in practice (lane change in 499/513 trials) but not parameterisable |

**E. R3B braking-only model**
- Deterministic, open loop, 1-D; stationary in-lane obstacle; no escape path; u = 1.
- Frozen configuration: report §13.1.
- 150 scenarios: 58 ROBUSTLY SATISFIED, 47 PARAMETER-SENSITIVE, 45 ROBUSTLY UNSATISFIED; 0 in the ±0.01 s boundary band.
- Main domain uses the guarded endpoint method.
- The t1 = 4 s supplement is sensitivity-only. It has 28 endpoint cases and 2 cases (60 km/h, μ 0.5, P2) bounded with the stationary-point t1 method.

## 2. Synthesis-readiness matrix (summary)

| Status | Variables |
|---|---|
| Observable in D003 and usable (as descriptors or boundaries) | TOR time, `t_button`, speed, TTC, handback, repeated exposure, covariates |
| Observable but only partly (semantics / geometry missing) | hazard distance, lane-change timing, a_pre kinematics |
| Source-supported generic intervals (not D003-specific) | t2, a_max, drag, friction relation |
| Explicit assumptions (R3B only) | t1, t3, authority transfer (= effective control in the model), P2 support, μ = 0.5, u = 1 |
| Not usable anywhere yet | first human input, manoeuvre completion, steering escape-path availability |

**No variable is both D003-observable and usable as a human-response input to the R3B model.** The only D003 human timing (`t_button`) is a different event from t1.

## 3. Event-semantic alignment

**Valid aliases (same event under both clocks):**
- R2 TOR = R3 clock origin (t = 0)
- Manual_Start = `E_driver_acknowledgement`
- validated lane crossing = `E_lane_change`
- first Manual_Stop after Manual_Start = `E_handback`
- D003 TTC at TOR = `T_available^brake` (constant-velocity reference)

**Invalid aliases:**
- `t_button` → t1
- Manual_Start → authority transfer
- first channel activity → first human input
- lane change → effective longitudinal control
- Manual_Stop / handback → recovery completion or stabilisation

**Must remain distinct:** TOR, acknowledgement, authority transfer, first human input, effective braking, lane crossing, handback, and the hazard boundary.

**Verdict:** R2 and R3 share only the TOR origin and the TTC / T_available definition. Any trial-level alignment beyond that would need authority transfer or effective braking, which are latent in D003. It would leak model assumptions into observed data and is therefore not allowed.

## 4. Cross-layer identifiability

| Class | Links |
|---|---|
| **IDENTIFIED** | repeated exposure → `t_button` (associational); covariates → `t_button` (null after Holm); speed × μ × a_max → T_required^brake (within model); D003 TTC at TOR → T_available^brake (definitional) |
| **PARTIALLY IDENTIFIED** | vehicle type → a_pre (drag component only); lane crossing → steering recovery time (crossing timing observed; onset, authorship and required offset not) |
| **ASSUMPTION-DEPENDENT** | TOR → authority transfer; TTC → braking-only recoverability |
| **NOT IDENTIFIABLE** | `t_button` → t1; first input → effective control; first channel activity → first input; P2 support → D003 automation; familiarity → braking strength; TTC → full takeover recoverability; Manual_Stop → recovery completion; lane change → effective longitudinal control |

Two quantities being times does not create a link.

## 5. What "system synthesis" could mean

| Level | Required inputs | Available now | Blocked | Claims possible | Still prohibited |
|---|---|---|---|---|---|
| **S1** deterministic braking-only necessary-condition composition | TTC, speed, μ, a_pre policy, t1, t2, t3, a_max, authority timing, u | all, **as R3B assumptions or sources** | empirical t1, u, authority timing for takeovers | "under stated assumptions, braking alone can / cannot meet the condition" | anything about observed takeovers or steering |
| **S2** multi-channel envelope (braking + steering / lane change) | S1 inputs plus hazard geometry, target-lane gaps, lateral dynamics, steering onset and authority, completion definition | lane-crossing timing only | geometry (B10), gaps (B5), steering authorship (B17), completion definition | manoeuvre-specific recoverability | — (not reachable yet) |
| **S3** probabilistic human–vehicle–automation model | S2 inputs plus distributions of human timing and command strength, automation behaviour, scenario frequencies | none identified | B17, B7, D003 automation model, population-level human distributions | probability statements | all probability claims today |

**S1 is already what R3B is.** Composing it with R2 adds no identified input (§4). S2 and S3 are not reachable with current evidence.

## 6. R3B feed-forward boundary

**May contribute:**
- braking-only T_required^brake intervals and labels within the validity envelope;
- the parameter-sensitivity structure;
- policy-branch deltas as counterfactuals;
- method and provenance metadata (bound method, guard results, ε, frozen configuration).

**May not contribute as if observed:**
- a driver reaction-time distribution;
- D003 braking onset or braking strength;
- authority timing;
- steering recovery;
- takeover success rates or probabilities;
- real D003 automation behaviour.

## 7. R2 (human-layer) feed-forward boundary

**May contribute:**
- validated event timings (`t_button`, TOR → lane crossing, handback) as descriptors;
- the within-participant repeated-exposure association;
- the null covariate associations;
- multi-TOR and carry-over robustness.

**May not contribute:**
- causal learning claims;
- a braking-strength distribution;
- effective-control or first-input timing;
- EV/ICE familiarity effects;
- authority-transfer timing;
- `t_button` as a substitute for t1.

## 8. Remaining blockers, by scientific importance

| # | Blocker | Prevents | Resolvable from D003? | Owner clarification could resolve? | Literature | Permanent? |
|---|---|---|---|---|---|---|
| 1 | **B17 control-channel authorship** | observed t1, u_eff, first input, steering onset; empirical anchoring of S1 and any S2/S3 | no (tested in R2A) | **yes**: questions A1–A6 | assumptions only | no, pending owners |
| 2 | **Authority semantics (B7)** | authority timing; alignment of the D003 clock with the model timeline | no | **yes**: questions B1–B3 | R157 gives rules, not D003 timing | no |
| 3 | **Hazard geometry, gaps, adjacent-lane semantics (B10, B5)** | T_required^steer; S2 | no | **yes**: questions D1–D4, E1 | cannot identify D003 geometry | no |
| 4 | **Recovery completion definition** (T_stable withdrawn) | S2/S3 outcome definition | partly (handback censors observation) | partly (protocol intent) | definitions only | no, conceptual work |
| 5 | **D003 vehicle / automation model (V21, T14)** | calibrating a_pre, t2, t3, a_max and P-branches to D003 | no | **yes**: questions F1–F4, A6 | generic intervals only (already used) | no |
| 6 | **Population human timing / braking strength for takeovers** | S3 | only after #1 | no (analysis, not semantics) | external data would be a different population / assumption | no |
| 7 | **EV / one-pedal / regen familiarity (M)** | vehicle-specific human effects | no (single simulator vehicle) | no | not from D003 | **yes, for D003** |
| 8 | **Owners' 466-trial set (B12)** | exact comparability with published results | no | yes | — | no (low importance for synthesis) |

## 9. Recommended next phase

> **Superseded (2026-09-24):** the user stated that there is no external dataset owner to contact. The recommendation below is replaced by `docs/R4_INTERNAL_SOURCE_OF_TRUTH_AUDIT.md` §4 (internal verification of the documented Manual_Start design intent). The blocker list in §8 is revised in that audit's §3. The two new design-intent links are recorded in `research/R4_CROSS_LAYER_LINKS.csv`.


**Recommendation: stop and wait for owner clarification** (send `research/D003_DATASET_OWNER_QUESTIONS.md` / the email draft). No R4A–C work is started in the meantime.

**Why this, rather than R4A, R4B or R4C:**
- **R4C** (assumption-bounded deterministic synthesis) would repackage R3B. S1 composition adds no identified input, because every human-to-model link is not identifiable or assumption-dependent.
- **R4B** (steering model) cannot be parameterised to D003 without geometry, gaps and steering authorship (blockers 1 and 3). A generic lateral model would be another assumption layer.
- **R4A** (event harmonisation) is largely done by this audit and the R3B-0 event registry. Encoding it further gains little until the owners say what Manual_Start and the control channels mean. The link table would then change: `t_button` → authority and first input → effective control could move out of NOT IDENTIFIABLE.
- The three highest-ranked blockers are all answerable only by the dataset owners. Their answers decide whether S1 can be empirically anchored and whether S2 is feasible on D003 at all.

Sending the questions is the user's decision; no contact details are invented.

## 10. Verdicts

1. **Readiness matrix:** see §2 and the CSV.
2. **Links:** 4 identified, 2 partially identified, 2 assumption-dependent, 8 not identifiable.
3. **Event alignment:** only TOR and TTC / T_available align across R2 and R3; all authority, input and braking events remain distinct and latent.
4. **R3B feed-forward:** bounded braking-only intervals, labels, sensitivities, counterfactual policy deltas and provenance. Never observed human quantities.
5. **R2 feed-forward:** event-timing descriptors and associational findings. Never t1, braking strength, authority timing or causal claims.
6. **Strongest blockers:** B17, B7, hazard geometry and escape paths.
7. **Deterministic synthesis today:** only S1, which R3B already is. Composing it with R2 is not scientifically defensible, because no human-to-model link is identified.
8. **Steering before synthesis:** required for any claim about D003-type recovery (lane change in 499/513 trials). Not required for the braking-only necessary condition.
9. **B17 / owner clarification:** remains gating for everything beyond S1.
10. **Next phase:** stop and wait for owner clarification.
