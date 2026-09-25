# R3A: vehicle-response, automation-transition and hazard-state evidence baseline

**Status:** Phase R3A, 2026-09-23. Evidence preparation only. No synthesis, no probability, no Monte Carlo, no new simulator. The human layer is paused.
**Question answered:** which quantities can be parameterised from evidence, which must stay bounded, and which are not identifiable.

**Machine-readable outputs** (validated by `src/provenance/registry.py`, tested in `tests/test_r3a.py`):

| File | Content |
|---|---|
| `research/R3A_SOURCE_REGISTER.csv` | 30 sources, each with its access level (full text read / abstract / secondary quotation / dataset / repository / first principles) |
| `research/data_matrix/VEHICLE_RESPONSE_EVIDENCE_MATRIX.csv` | 21 rows |
| `research/data_matrix/TRANSITION_EVIDENCE_MATRIX.csv` | 16 rows |
| `research/data_matrix/HAZARD_STATE_MATRIX.csv` | 14 rows |
| `research/PARAMETER_PROVENANCE_REGISTRY.csv` | 23 parameters |
| `research/identifiability/identifiability_matrix_R3A.csv` | 17 quantities; supersedes the Phase-0 matrix for these quantities |
| `research/data_matrix/r3a_epa_coastdown_deceleration.csv` (+ provenance JSON) | Drag-only deceleration from US EPA road-load data (`src/experiments/r3a_coastdown_epa.py`) |

**R3B-0 correction notice (2026-09-23):** the official UN R157 texts have since been read (Rev.1 01 series and the 00 series in OJ L 82); see `docs/R3B0_SOURCE_AND_SPECIFICATION_HARDENING.md`. Three statements below are corrected there:
- "10 s transition period" is replaced by "MRM earliest 10 s after the start of the transition demand without deactivation" (§5.4.4.1)
- "MRM ≤ 4.0 m/s²" is an *aim* for the deceleration demand (Rev.1 §5.5.2)
- the deactivation criteria are now verified (§6.2.5, §6.3)

The `T_available` bookkeeping is also revised: `T_available^m` is the constant-velocity reference time to the manoeuvre boundary, and all policy effects go into `T_required^m` (`docs/SYSTEM_EVENT_STATE_SPECIFICATION.md` §3). Option E in §10 is now classified **INCREMENTAL** after the assurance prior-art search (`research/ASSURANCE_FRAMEWORK_PRIOR_ART.md`).

**Source-access caveat (as of R3A, superseded for R157):** the official UN R157 text could not be downloaded (HTTP 403 from every UNECE host). R157 provisions below are marked *secondary quotation*, and the driver-deactivation criteria remain **unverified**. ISO 15622 and ISO 23793-1 were not read in full.

---

## 0. R2C closure: questionnaire-ID join

**Classification: STRONGLY SUPPORTED BUT NOT EXPLICIT.**

Evidence for the join:
- The data dictionary defines `id` with the same text ("assigned id for each participant") under all four file groups: driver characteristics, scenario experience, simulator data and physiological signals.
- The README cohort (33 male / 24 female; mean age 38.51 ± 17.23) matches the questionnaire exactly: 24 female counting one lowercase entry; the population SD is 17.23.
- Two other `id`-keyed owner tables line up with the simulator filenames:
  - The eye-tracking `scenario_start2end_time.csv`, joined on `id`, reproduces every simulator recording start time (difference 0 s in 513/513 trials). A shifted id misses by a median of ~55,000 s.
  - The scenario-experience rows are listed per `id` in the same chronological order as the R2B exposure reconstruction for 57/57 participants.

Why it is not VERIFIED:
- No document states that the driver-characteristic file uses the same id space.
- That file has no per-trial field that could be cross-checked. The owners' paper and dataset portal say nothing on it.

The R2C limitation is kept, with this classification. R2C was **not rerun**, because the join's validity has not changed.

Side note: the dataset portal describes the order as a Latin-square design. R2B found 20 distinct sequences, i.e. counterbalanced but not a strict 9 × 9 Latin square. This does not affect R2B.

---

## 1–3. Vehicle-response layer

Full matrix: `VEHICLE_RESPONSE_EVIDENCE_MATRIX.csv`. Architectures are not forced into one number.

| Phenomenon | Evidence (source) | Range | Status |
|---|---|---|---|
| Coast / drag deceleration `a_drag` | US EPA road-load coefficients, 1,537 configurations (S07; derived) | 100 km/h: median 0.31, 5–95% 0.22–0.40 m/s²; speed-dependent (130 km/h: 0.46) | DISTRIBUTION |
| ICE engine braking on release | no verified numeric source | ≥ drag; upper value not established | CONTEXT-DEPENDENT |
| EV lift-off (accelerator-release) regen | on-road, 4 EVs (S08); dataset documentation (S26); R13-H stop-lamp bands 0.7 / 1.3 m/s² (S01) | ≈ 1–4 m/s², depending on mode | CONTEXT-DEPENDENT |
| Regen-only maximum | S26, S23 | ≈ 1–4 m/s² (0.1–0.3 g) | BOUNDED |
| One-pedal deceleration | S08; timing effects in a simulator study (S22) | up to ≈ 3 m/s²; torque peak 200–300 ms after lift-off | CONTEXT-DEPENDENT |
| Friction-brake delay `t2` | 4 instrumented vehicles (S20); R13-H (S01); Greibe (S04) | hydraulic hard braking 0.05–0.17 s; regulatory ≤ 0.6 s to prescribed performance | BOUNDED |
| Build-up `t3` | pedal-force logging (S04); R157 reference model (S03) | time to 10 kg pedal force: professionals 0.05 s, non-professionals 0.83 s (0.63–1.26); CCDM 0.6 s | CONTEXT-DEPENDENT (human × vehicle) |
| Jerk | derived; ACC standard (S14); naturalistic driving (S21); CCDM (S03) | 2.5 (comfort) … 12.65 (regulatory reference) m/s³ | CONTEXT-DEPENDENT |
| `a_max`, dry, ABS | Greibe (S04); R13-H floor (S01); CCDM (S03) | professionals 8.4 (up to ≈ 9.1 over 100–70 km/h); non-professionals 7.4; approval floor 6.43; CCDM 7.6 m/s² | BOUNDED |
| `a_max`, wet | S04 | professionals 7.9; non-professionals 7.0 m/s² | CONTEXT-DEPENDENT |
| Friction limit | first principles | a ≤ μg | FIXED (law) |
| Human-achieved emergency deceleration | EDR crashes (S05); S04; S06 | crash median 0.58 g ≈ 5.7 m/s²; non-professionals used ≈ half the pedal force of professionals | CONTEXT-DEPENDENT |
| Brake assist | R13-H definitions (S01) | manufacturer-declared thresholds | NOT IDENTIFIABLE |
| Brake-by-wire response | R13-H upper bound only | ≤ 0.6 s; no verified peer-reviewed number | BOUNDED |
| Regen / friction blending | R13-H category B definition | proprietary | NOT IDENTIFIABLE |
| D003 simulator vehicle | owners do not document it | — | NOT IDENTIFIABLE |

**Main points:**
1. **Drag is small.** Drag-only deceleration is 0.2–0.4 m/s² at motorway speed. Any `a_pre` above ≈ 0.5 m/s² must come from engine braking, lift-off regen or an automation command. A1 used `a_coast = 2.0 m/s²` (about 6× the drag median), so A1's W1 condition models a release **with** regen / engine braking, not coasting.
2. **Capability ≠ achieved deceleration.** Trained drivers reach about 8.4 m/s² on dry ABS braking. Ordinary drivers average less, build up pedal force far more slowly, and in real crashes average about 5.7 m/s².
3. **`t3` is not a vehicle constant.** In measured emergency stops, build-up is dominated by how fast and hard the human presses the pedal. A vehicle-only `t3` cannot be separated with the sources checked.

---

## 4. `a_pre` reinterpretation

`a_pre` is **not** an EV-vs-ICE property. It is the net deceleration between TOR and effective human braking:

`a_pre = a_drag(v) + g·sinθ + [a_powertrain_release  if propulsion is released] + [a_auto  if automation commands it]`

Which terms are active is decided first by the **transition state** and only then by the vehicle:

| Source of pre-effective deceleration | Present when | Layer |
|---|---|---|
| Continued automation control / cruise maintenance (`a_pre ≈ 0`) | automation keeps control after TOR (R157 requires continued operation during the transition) | **Transition** |
| Automation deceleration during the transition (e.g., headway enlargement) | policy (SUMO/TransAID preparatory phase), bounded by the ACC envelope ≈ 3.5 m/s² | **Transition** (vehicle only executes) |
| Transition support / active braking assistance / MRM | policy; MRM aim ≤ 4.0 m/s² (R157) | **Transition** |
| Drag / rolling resistance | always | Vehicle |
| Engine braking | automation releases propulsion, ICE in gear | **Interaction** (transition decides release; vehicle decides magnitude) |
| Lift-off regenerative deceleration | automation releases propulsion, EV | **Interaction** |
| One-pedal deceleration | a human modulates the accelerator in one-pedal mode | Interaction (vehicle × human); rare in L3, where the driver is out of the loop |

**Conclusion:** `a_pre` is **primarily a transition-policy variable**. It takes a vehicle-dependent magnitude only in the propulsion-release branch.
- The code already reflects this: `calculate_acceleration` selects `a_pre` through the withdrawal-policy branch (W0 → 0; W1 → `a_coast`).
- The EV/ICE contrast exists only where the transition policy releases propulsion.
- For a regulated L3 system that keeps operating until the driver acts, the powertrain's lift-off behaviour is masked by the automation's own command.

---

## 5. Saturated braking (`u = 1`)

**What the code does:** the vehicle model hard-codes full braking after `t_reaction + t2`, ramping over `t3`. `HumanDriverConfig.u_target` exists but is never passed to the vehicle model, and `road_friction` is carried but never caps `a_max`.

- **When `u = 1` is physically reasonable:**
  - the driver brakes maximally (trained drivers; brake assist activated; ABS cycling)
  - the question is physical feasibility, i.e. the best case the vehicle allows
  - `a_max` is set consistently with μ (a_max ≤ μg)
- **When it is unrealistic as behaviour:**
  - ordinary drivers under-apply the brake (≈ half the pedal force; 0.83 s to reach 10 kg)
  - crash-sample braking averages about 5.7 m/s²
  - drivers choose to steer (D003: lane change in 499/513 trials)
  - non-critical takeovers invite comfort braking (D003's 7 s budget)
- **Phenomena that disappear under `u = 1`:**
  - the partial-command mapping `u → a` and its nonlinearity
  - regen / friction blending at moderate demand
  - one-pedal modulation
  - brake-assist effects (the command is already maximal)
  - human modulation and corrections
  - jerk as a choice
  - expected-vs-actual response mismatch M (there is nothing to mismatch at full command)
- **Parameters that still matter:** `v0`, distance / TTC, `a_pre` (via the transition policy), `t1`, `t2`, `t3` (human × vehicle), and `a_max` (μ-limited).
- **Questions that cannot be answered under `u = 1`:**
  - effects of regen or one-pedal calibration on realistic takeover braking
  - any M / familiarity question
  - comfort-vs-safety trade-offs
  - behaviourally realistic success rates
  - steering or combined recovery

**Scope of the spine:** the current closed form is the **capability-bound (best-case) longitudinal feasibility slice**. It is deterministic and open loop, assumes a stationary in-lane hazard, straight braking and full command, uses authority at TOR in the code, and does not couple friction.
- It gives a **necessary condition** for braking-only recovery: if `T_available < T_required^brake(u = 1)`, braking alone cannot succeed whatever the driver does.
- It is **not sufficient**: realistic `u < 1` raises the requirement.
- The same structure is the regulator's own reference model: the R157 CCDM uses a reaction time, then a linear ramp to 7.6 m/s² over 0.6 s (S03).

---

## 6. Automation-transition layer

Full matrix: `TRANSITION_EVIDENCE_MATRIX.csv`. Four distinct events are separated. **None may be equated with another.**

| Event | Meaning | D003 |
|---|---|---|
| `t_TOR` | request issued | observed (7 s TTC; B1 multi-TOR) |
| `t_ack` | driver acknowledgement / mode switch (Manual_Start) | observed as an event marker; authority UNRESOLVED (B7) |
| `t_auth` (per channel) | human input takes priority | **not identifiable** |
| `t_eff` | first effective human input | **not identifiable** (B17) |

Evidence:
- **UN R157** (secondary quotation):
  - a 10 s transition period before an MRM may start (an immediate MRM is allowed only on severe failure)
  - the system continues to operate during the transition
  - MRM in lane, aiming at ≤ 4.0 m/s²
  - "system override" is defined as a driver input with priority while the system is active; the exact deactivation criteria are unverified
  - 130 km/h under the 01 series
- **TransAID / SUMO ToC:**
  - after a TOR the vehicle enters a preparatory phase with headway enlargement and lane changes disabled, and automation continues for a lead time
  - a failed transition triggers an MRM at a constant `mrmDecel` (default 1.5 m/s²)
  - post-takeover awareness recovers linearly (defaults 0.5, 0.1 /s); these are software defaults, not empirical values
- **Takeover-time evidence:** mean 2.72 s (SD 1.45) across 129 studies; it depends strongly on the time budget (r = 0.73). Takeover time is therefore not independent of the TOR design.
- **Taxonomy:** D003 is a mandatory, automation-initiated transition with the driver in control afterwards, followed by a protocol handback (Lu et al. 2016). Shared control (Abbink et al. 2018) has no transition parameters available.
- **D003 automation behaviour at TOR:** channel changes are cell-specific (B17), and the owners do not describe them. Not identifiable.

**Status:** TOR timing is identifiable. Continued support is partially identifiable, as a policy variable. MRM and the automation envelope are externally parameterised (regulatory bounds). Authority transfer and effective control are **not identifiable**. Immediate withdrawal (W1) is a **counterfactual bound**, not a representative regulated policy.

---

## 7. `T_available`

| Definition | Physically meaningful | Observable | Model-derived | Scenario-dependent |
|---|---|---|---|---|
| TOR → hazard (TTC at TOR) | partly: ignores manoeuvre limits | **yes** (D003: 7 s) | no | yes |
| TOR → critical boundary for manoeuvre *m* (last point to brake / to steer) | **yes** | no | yes | yes (v0, d0, μ, geometry, gaps) |
| Automation-supported residual time | yes (the policy can change the state handed over) | no | yes | policy-dependent |
| Authority transfer → critical boundary | **yes**: the time the human actually has | no (`t_auth` unidentified) | yes | yes |
| Manoeuvre-specific available time | yes | no | yes | yes |

**Recommendation:** no universal `T_available`. Define

`T_available^m(policy) = t_crit^m(hazard state, transition policy) − t_TOR`

as the model quantity, measured from TOR so that `T_required^m` includes `t1…t3` without double counting. Keep TTC at TOR as the **observable proxy**. Report `t_crit^m − t_auth` only once authority transfer is identified.

For the braking slice with a stationary in-lane hazard at constant approach speed, the TOR → critical-boundary form reduces to the current "required TTC at TOR" comparison. For steering it does not.

---

## 8. Hazard / scenario layer

Full matrix: `HAZARD_STATE_MATRIX.csv`.

- **State:** `v0`; distance `d0`; closing speed / obstacle motion; hazard geometry (width, lateral position, lane); target-lane occupancy and gaps. TTC = `d0 / closing speed` is derived.
- **Environment:** μ; grade (2% ≈ 0.2 m/s², comparable to drag and small relative to `a_max`); lane width and layout.
- **Manoeuvre constraints:**
  - adjacent-lane availability
  - required lateral offset `y_req`
  - friction circle `√(a_x² + a_y²) ≤ μg`
  - gap acceptance
- **Derived:** escape-path availability; urgency = `T_available^m − T_required^m`.

**TTC alone is not the hazard state.** The same TTC can arise from different `(v0, d0)` pairs with different braking requirements, and TTC says nothing about whether an escape path exists.

In D003:
- `v0` is identifiable, and so is TTC within its domain (B13).
- Obstacle motion is only inferred as stationary, from the dictionary's TTC formula.
- Hazard geometry and escape paths are **not identifiable** (B10, B5).
- μ is not reported by the simulator.

---

## 9. Manoeuvre dependence

D003 drivers evade by lane change, but the spine is braking-only. **Recoverability must be manoeuvre-specific:** `T_required^brake`, `T_required^steer`, `T_required^combined`.

**Point-mass illustration only** (not a lateral model; ignores yaw build-up, steering reaction and whether the lane is free). At 100 km/h with a_x = a_y = 8 m/s²:
- braking to a stop needs 48.2 m (3.5 s)
- a 3.5 m lateral offset at constant lateral acceleration needs 26.0 m (0.94 s); a 2.5 m offset needs 22.0 m
- the crossover speed `2·a_x·√(2y/a_y)` is 45–54 km/h

This is consistent with the literature: braking is appropriate at low speed, steering at higher speed when the lane is clear (S16 and related work). At a 7 s TTC (194 m), both manoeuvres are far from critical, as already recorded.

- **What can be said for braking:**
  - necessary conditions under the capability bound
  - model sensitivities to `v0`, `a_max`, `a_pre` and `t1`
  - the exact requirement when **no escape path exists** (adjacent lane blocked)
- **What does not generalise to steering:**
  - `t2`/`t3` of the brake system
  - the stopping-distance form
  - the role of `a_pre`: slowing helps both manoeuvres, but in different ways
  - the absence of any geometry or gap dependence
- **Evidence required for a lateral / combined envelope:**
  - hazard width and position
  - lane width
  - target-lane gap state (laneGap semantics, B5)
  - driver-attributed steering channels (B17)
  - a lateral vehicle model with documented parameters
  - validated human steering onset and profile distributions
  - μ shared between braking and steering

**Net effect on the braking-only spine:** it is **optimistic in behaviour** (`u = 1`) but **conservative in manoeuvre**, because it ignores the shorter steering requirement when an escape path exists. It is exact only for the blocked-escape case with full braking.

---

## 10. Novelty recheck

| Candidate | Assessment |
|---|---|
| A. New physical model | **No.** Standard kinematics. The same reaction + delay + linear-ramp structure is in accident-reconstruction practice and in the R157 reference driver model (S03). |
| B. New human model | **No.** Driver-attributed control is blocked (B17); event timing is associational. |
| C. New transition model | **No.** R157 transition / MRM rules, the SUMO/TransAID ToC model and Papadimitriou et al.'s safe-time-budget vs time-to-control framework exist. |
| D. New coupling / recoverability framework | **Uncommon combination, not yet executed.** Separating the policy-selected `a_pre`, manoeuvre-specific requirements and the four transition events is not found in the sources checked, but nothing is computed yet. |
| E. Measurement / assurance framework for when fallback claims are supportable | **Most plausible contribution.** It combines observation-layer rules, control-channel authorship checks (B17), a parameter provenance registry with identifiability gating, and explicit classification of what a model slice can and cannot support. **Prior art on assurance frameworks (e.g., safety-case and SOTIF literature) was not searched in R3A and must be checked before any claim.** |

Standard components: all physics, R157 / ACC bounds, and the takeover-time literature. Genuinely new coupling: none demonstrated yet.

---

## 11–12. Parameter provenance and identifiability

`PARAMETER_PROVENANCE_REGISTRY.csv` holds 23 parameters, each with source, year, population, scenario, value, confidence, assumptions, status, transferability, code usage and synthesis entry. The validator enforces the following:
- every source id resolves
- values are ordered low ≤ central ≤ high
- code references exist
- no NOT IDENTIFIABLE or LOW-confidence parameter is marked ready for synthesis

`identifiability_matrix_R3A.csv`:

| Layer | Quantities |
|---|---|
| **Identifiable** | TOR timing, `v0`, TTC (within domain) |
| **Partially identifiable** | `a_pre`, `t3`, continued automation support, distance |
| **Bounded** | `t2`, `a_max`, jerk, withdrawal |
| **Externally parameterised** | regen / one-pedal, MRM, μ |
| **Not identifiable** | blending, authority transfer, escape-path availability |

---

## 13. Scope kept

No `P(safe fallback | …)`, no Monte Carlo, no combination of uncertain parameters, no simulator changes. The code findings are **documented, not fixed**:
- `u_target` is not wired to the vehicle model
- `road_friction` is not used
- `T_authority` is assumed to equal TOR

---

## 15–16. Ready for later synthesis vs blockers

**Ready (`synthesis_entry = YES`):** `v0`, `a_drag` (distribution), `t2` (bounded), `a_max` dry (bounded), `T_TOR`.

**Conditional:** `t1`, `t3`, `a_pre_auto` bounds, `a_coast`, lift-off regen, `a_max` wet, μ, R157 transition period, MRM deceleration, ACC envelope, `t_button`.

**Blocking synthesis:**
1. authority transfer and effective human input (B7, B17)
2. behavioural braking command `u_eff` in takeovers
3. hazard geometry and escape-path state (B10, B5)
4. no lateral / combined requirement
5. D003 vehicle and automation model undocumented
6. R157 full text not retrieved
7. code simplifications (`u` not wired; friction not coupled; authority = TOR)
8. assurance-framework prior art not yet checked

---

## 17. Recommended R3B scope (not started)

1. **Formal specification (no code):** state vector, the four transition events, and manoeuvre-specific `T_available^m` / `T_required^m`, with the policy branch for `a_pre` explicit.
2. **Braking-slice correction plan:** document how friction coupling (`a_max ≤ μg`) and a wired `u` would enter, as a design note, before any code change.
3. **Deterministic bounds evaluation of the braking slice** over registry bounds (interval / corner analysis only; no probabilities), clearly labelled as the capability bound.
4. **Source completion:** obtain the official R157 text (and ISO 15622 / ISO 23793-1 if available), for example by manual download, to replace the secondary quotations.
5. **Lateral evidence plan:** identify datasets with documented hazard geometry and validated steering authorship. Evidence gathering only, no lateral model.
6. **Assurance-framework prior-art search** before any novelty statement about option E.
