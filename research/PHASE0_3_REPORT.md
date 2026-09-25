# Phase 0.3 Report — Control-Ownership Definition + Raw Data Forensics

## Scope

Phase 0.3 does not implement the simulator, does not touch CARLA, and does not run Experiment A. It resolves the control-ownership ambiguity Phase 0.2 left open, and determines — by actually fetching and parsing real bytes, not README claims — how much of the vehicle-response model can be anchored from raw public data. All prior Phase 0.1/0.2 outputs were re-read before starting and are treated as background, corrected here where new evidence requires it.

## 1-2. Control ownership and handover policy — see `control_ownership_timeline.md`

Phase 0.2's "driver releases accelerator" framing was an L2/supervisory-ACC category error for an L3 out-of-loop project. Resolved with four signals (`u_automation`, `u_human_accel`, `u_human_brake`, `w_authority`) and a chosen baseline handover policy (**B**: automation holds `v0` until `t_reaction`, then authority flips cleanly to the human's brake step). Policies A (immediate withdrawal) and C (staged) are deferred as later sensitivity tests, not folded into Phase 1A automatically, per the task's explicit instruction. This gives a literal, formal instantiation of the project's own `T_authority`/`T_effective` distinction: `T_authority = 0` (nominal, at TOR), `T_effective = t_reaction` (when `w_authority` actually flips) — not just a slogan, a modeled gap.

**Real-world grounding, not just a modeling choice:** direct inspection of raw OpenLKA EV Dataset telemetry (Section 4 below) independently confirmed that production ADAS logging already separates "automation actively commanding" (`op_enable`, gating `act_ctrl_*`/`aTarget`) from "what the vehicle is actually doing" (`aEgo`, `vEgo`) — the same distinction `w_authority`/`u_automation` formalises, found in real data rather than asserted from first principles.

## 3. `a_coast` reassessment — REFORMULATE

Under the chosen baseline B, there is no temporal window in which the vehicle is uncommanded before the brake step (automation holds `v0` right up to `t_reaction`) — the phase `a_coast` was meant to describe **does not occur**. Verdict: **REFORMULATE**, not RETAIN or DROP outright. Its causal role (distinguishing regen-flavored from friction-only architectures) is absorbed into a regen-flavored variant of `t_delay` — electric motor torque response is physically faster than hydraulic friction actuation, a well-evidenced qualitative direction with no quantified magnitude found. See `vehicle_response_model.md` and `phase1A_parameter_table.csv`.

## 4. Raw OpenLKA data inspection — see `raw_dataset_forensics.md`

Real files were fetched and parsed, not assumed from documentation:
- **D005 (Acceleration Dataset)**: full 20MB `HYUNDAI_IONIQ_5_segments.json` downloaded and parsed. **Measured sampling rate ≈10Hz, directly contradicting the README's "100Hz" claim.** Confirmed schema has **no brake field at all** — this dataset is accelerator-only and cannot inform any braking/regen parameter (correcting an implicit assumption carried since Phase 0.1/0.2).
- **D004 (EV Dataset)**: two real byte-range chunks (~2,260 rows) of an actual 88.6MB session file downloaded and parsed. Confirmed 90-column schema, confirmed genuinely continuous `state_gas_pos`, and confirmed — the key finding — that `act_ctrl_*`/`aTarget`/`brake`/`brake_padel_status`/`state_regen_break_enable` were constant/inactive throughout both windows, traced to `op_enable=False` for the whole sampled span (automation not engaged). **No braking or regen event was captured** — a genuine, reported negative result, not evidence the fields don't work.
- **D001 (ADAS-TO)**: raw per-clip files were **not reachable** in this pass (gated Hugging Face access, confirmed via the HF page — a correction to Phase 0.1's "direct download" claim). Schema-level detail was obtained from the underlying paper instead, surfacing a previously unknown **mixed 10Hz/100Hz sampling split (61.7%/38.3%)** that materially affects `t_delay`'s resolvability from this source, and a **clip-count discrepancy** between the paper and the live HF listing that was not resolved.

`dataset_inventory.csv` was updated with all of the above as corrections, not silent overwrites.

## 5. Parameter estimability — see `phase1A_identifiability_final.csv`

- `a_coast` (original formulation): **NOT_IDENTIFIABLE under the chosen baseline** — retired, not a data gap.
- Regen-response-speed differential (replacement): **COUNTERFACTUAL_ONLY** — direction known, magnitude not found anywhere searched.
- `t_delay` (friction baseline): **LITERATURE_ONLY**, with a described but unexecuted **DERIVABLE_WITH_ASSUMPTIONS** path via D004 raw data.
- `t_buildup`: **downgraded to COUNTERFACTUAL_ONLY** — see Task 7 finding below.
- `v_rolloff`: **COUNTERFACTUAL_ONLY** — mechanism LITERATURE_ONLY (qualitative), numeric shape unfound despite a real raw-data search attempt.
- `a_max`: **LITERATURE_ONLY** — not derived from any raw file accessed (no peak-deceleration episode captured).

## 6. Episode extraction design — see `response_episode_definition.md`

A concrete, executable trigger/window/threshold/exclusion definition was written for extracting `t_delay`/`t_buildup`/roll-off episodes from D004's raw continuous signals (D005 has no brake channel; D001 is gated). Exercised against the two real windows already pulled — correctly identified that neither contains an episode, which is itself the honest output of a measurability check on a small sample. Full-dataset extraction was deliberately **not** performed, per the task's explicit instruction not to mass-process.

## 7. `t_buildup` challenge — DOWNGRADED

Adversarial re-check could not confirm the Phase 0.2 anchor (1.75-2.0s from arXiv:2112.09074) actually measures "time to reach maximum deceleration." An independent search found that pedestrian-collision-warning systems conventionally trigger at **TTC < 2 seconds** — meaning the "2s" figure is at serious risk of being a **warning-trigger threshold**, an entirely different physical quantity, not a build-up-time measurement. The source PDF could not be re-parsed with enough fidelity to rule this out. Per the task's explicit instruction, **this number is not allowed into Phase 1A** as a literature anchor until the ambiguity is resolved by actually reading the paper's methods section directly (not a search-engine summary of it) — see Recommended next action.

## 8. Regen `1-4 m/s²` challenge

Traceable to D004's own README documentation (dataset-maintainer level, not independently peer-reviewed), not to L006 (SAE full text remained paywall-blocked; ResearchGate mirror returned HTTP 403 on a second attempt). The specific speed, drive/regen mode, and transient-vs-sustained character of this range are **not** documented anywhere found. Raw-file verification was attempted in this pass (Section 4) but did not capture a regen event to check against. **Status: not frozen as a numeric Phase 1A input** — retained only as a MEDIUM-confidence working range with these caveats stated explicitly wherever cited, consistent with its existing `phase1A_identifiability_final.csv` entry.

## 9. `v_rolloff` status — Option B

**Retained only as an explicit COUNTERFACTUAL sensitivity axis.** Dropping it (Option A) would remove the one part of Experiment A whose result is not already analytically known (see Section 11) — gutting the experiment's remaining value. Empirical support (Option C) was genuinely attempted (Section 4) and not obtained. It must never be allowed to drive the primary literature-anchored Gate A claim (`gate_A_preregistration.md` Step 5.3, `vehicle_response_model.md`).

## 10. `T_TOR_critical` — see `metric_definitions.md`

**Well-defined**, and does not require inventing a safety threshold — it uses the `stopping_margin = 0` boundary the project already has. Monotonicity of `stopping_margin` in TOR lead time guarantees uniqueness. A closed form was derived for R0/R2: `T_TOR_critical = D_stop/v0`, directly inheriting the analytically-guaranteed R0-vs-R2 ordering from Section 11. Added as a secondary derived outcome.

## 11. Analytical triviality check — see `analytical_sanity_check.md`

A full closed-form derivation (verified with `sympy`, not hand algebra alone) for the piecewise-linear R0/R2 case gives:

```
D_stop = v0²/(2·a_max) + v0·(t1 + t2 + t3/2) - a_max·t3²/24
```

**The R0-vs-R2 sign is a mathematical certainty**: `d(D_stop)/dt3 = v0/2 - a_max·t3/12 > 0` for any realistic parameter range, meaning R2 (larger `t_buildup`) is *guaranteed* to produce a longer stopping distance than R0, before any simulation runs. This is not a discovery Experiment A can make — it is already true of the model's own algebra. What simulation (eventually) adds: the *magnitude* under literature-anchored parameters (currently blocked, per Section 7), whether that magnitude crosses a realistic collision boundary in a specific scenario, and — the one genuinely open question — the **entire R1 comparison**, since `v_rolloff` makes the governing equation nonlinear and state-dependent near standstill, with no closed form derived and no sign guaranteed a priori.

## Decisions

**A. Control-ownership model: RESOLVED**
Four signals defined, one baseline policy chosen and justified, reconciled explicitly with the project's own `T_authority`/`T_effective` vocabulary, and independently corroborated by real telemetry structure found in raw data.

**B. Raw-data verification: CONDITIONAL PASS**
Real byte-level access and parsing was achieved for D004 and D005 (not README-level trust), producing genuine, load-bearing corrections (D005's sampling rate, D005's total lack of a brake channel, D004's automation-authority gating of command fields). D001 was not reachable at the byte level (gated). None of the three target parameters (`t_delay`, `t_buildup`, `v_rolloff`) were numerically resolved from raw data in this pass — the verification *method* passed; the target *parameters* remain unresolved.

**C. `a_coast` status: REFORMULATE**
Retired as originally formulated (not applicable under the chosen baseline); its causal role reassigned to a regen-flavored `t_delay` variant.

**D. `t_delay` status: PARTIAL**
Friction baseline has a real (MEDIUM-confidence, trade-journal-sourced) literature anchor; the regen variant introduced by the reformulation has direction only, no magnitude.

**E. `t_buildup` status: UNRESOLVED**
Downgraded from Phase 0.2's PARTIAL after this pass's adversarial re-check found the prior anchor is likely mischaracterized (plausibly a TTC warning-trigger threshold, not a build-up-time measurement).

**F. `v_rolloff` status: COUNTERFACTUAL ONLY**
Mechanism well-supported qualitatively; no numeric shape found despite a genuine raw-data search attempt. Retained per Option B.

**G. Can `T_TOR_critical` be defined defensibly? YES**
Well-defined, closed-form for R0/R2, does not require an invented safety threshold.

**H. Does Experiment A add more than a trivial stopping-distance identity? CONDITIONAL**
For R0-vs-R2, the *sign* is a trivial consequence of the chosen model (Section 11) — not by itself a reason to kill that comparison, but any report of it must be framed as a magnitude/boundary question, never a direction discovery. For R1, the comparison is genuinely open (nonlinear, state-dependent, no closed form). Experiment A's real non-trivial content lives in R1 and in locating the scenario-grid boundary where R0-vs-R2's known-sign gap actually flips a real outcome — not in whether an effect exists at all.

**I. Experiment A implementation status: NEEDS MORE EVIDENCE**
Not READY: `t_buildup` was actively downgraded (not just still-pending) this pass, and `v_rolloff`/the regen `t_delay` differential remain COUNTERFACTUAL_ONLY with no numeric path found despite genuine attempts. Not KILL: the mechanism remains physically plausible, the control-ownership ambiguity that blocked Phase 0.2 is now resolved, a real (if partial) numeric anchor exists for `t_delay`, and the analytical work in Section 11 clarifies exactly where the remaining scientific value is concentrated (R1, and R0-vs-R2's magnitude/boundary question) rather than casting doubt on the mechanism itself.

**J. Recommended next action**
1. Resolve `t_buildup` properly: obtain and directly read arXiv:2112.09074's actual methods/results section (not a search-engine summary) to determine definitively what the 1.75-2.0s figure measures, or locate an independent source specifically for vehicle mechanical build-up time.
2. Execute `response_episode_definition.md`'s procedure across a wider (but still bounded — not full-dataset) sample of D004 sessions, specifically searching for `brake_padel_status` and `state_regen_break_enable` transitions, to attempt direct measurement of `t_delay`, `t_buildup`, and `v_rolloff`'s numeric shape from real episodes rather than continuing to rely on external literature.
3. If gated access to ADAS-TO can be obtained, restrict any `t_delay`-relevant use to its 100Hz (rlog) subset only, per the newly-discovered mixed sampling rate.
4. Only once `t_buildup` is either resolved or explicitly, permanently accepted as COUNTERFACTUAL-only, and `v_rolloff` has at least a qualitative-to-quantitative estimate or a firm decision to run it as pure sensitivity, proceed to a first Gate A run under the frozen `gate_A_preregistration.md` procedure — still no simulator or CARLA code before that point.
