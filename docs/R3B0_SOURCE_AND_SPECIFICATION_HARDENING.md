# R3B-0: source and specification hardening

**Status:** Phase R3B-0, 2026-09-23. No synthesis, no Monte Carlo, no `P(safe fallback | …)`, no lateral model, no code change to the simulator, no novelty claim.

**Outputs:**
- this report
- `docs/SYSTEM_EVENT_STATE_SPECIFICATION.md`
- `docs/BRAKING_MODEL_CORRECTION_DESIGN.md`
- `research/ASSURANCE_FRAMEWORK_PRIOR_ART.md`
- `research/SYSTEM_EVENT_REGISTRY.csv`
- updated `research/R3A_SOURCE_REGISTER.csv`, the evidence matrices and `research/PARAMETER_PROVENANCE_REGISTRY.csv`

Validation: `src/provenance/registry.py`; tests in `tests/test_r3b0.py`.

---

## 1. Official R157 text

Two official texts were obtained and read:

| Source | Document | Access | sha256 |
|---|---|---|---|
| **S02** | UN R157 **Revision 1, 01 series** (entry into force 4 Jan 2023), E/ECE/TRANS/505/Rev.3/Add.156/Rev.1, 102 pp. | UNECE PDF via a browser session (scripted access is blocked); text extracted with pdf.js | `552b5792…1de537c` |
| **S31** | UN R157 **original 00 series** [2021/389], OJ L 82, 9.3.2021, p. 75 (authentic text ECE/TRANS/WP.29/2020/81) | Publications Office PDF | `9def8327…7de53327`* |

\*Full hashes are in the source register.

### Claims now verified from the primary text

| Claim | Location | Result |
|---|---|---|
| Transition demand = procedure to transfer the DDT to the driver | §2.2 (both) | VERIFIED |
| Transition phase = duration of the transition demand | §2.3 (both) | VERIFIED |
| System continues to operate during the transition; may reduce speed; no standstill unless required | §5.4.3 (both, identical) | VERIFIED |
| Escalation at the latest 4 s after the start of the transition demand | §5.4.3.2 (both) | VERIFIED (new) |
| Transition demand ends only at deactivation or MRM start | §5.4.4 | VERIFIED (new) |
| MRM "earliest 10 s after the start of the transition demand" if the driver does not deactivate | §5.4.4.1 (both) | VERIFIED |
| Immediate MRM on severe ALKS or vehicle failure | §5.4.4.1.1 | VERIFIED |
| MRM deceleration: "with an aim of achieving a deceleration demand not greater than 4.0 m/s²"; higher briefly or on severe failure | Rev.1 §5.5.2; 00 series §5.5.1 | VERIFIED as an **aim for the demand** |
| MRM to standstill in a target stop area, with MRM lane change if capable (Rev.1); in lane (00) | Rev.1 §5.5.1; 00 series §5.5.1–5.5.2 | VERIFIED |
| Maximum speed 130 km/h, and above 60 km/h only if MRM lane change is possible | Rev.1 §5.2.3.1 (00 series: 60 km/h) | VERIFIED, with its condition |
| Imminent collision risk: not avoidable with a braking demand below 5 m/s² | §2.6 | VERIFIED (new) |
| A system deceleration demand above 5.0 m/s² is an emergency manoeuvre | §5.3.1.1 | VERIFIED (new) |
| Deactivation during a transition demand: steering override or brake/accelerator override while holding the steering control, or holding the steering control with attentiveness confirmed | §6.2.5.1–6.2.5.2 | VERIFIED (was UNVERIFIED) |
| Braking overrides longitudinal control only if it yields higher deceleration than the system; accelerator *may* override; steering override needs force and duration thresholds | §6.3.1–6.3.3 | VERIFIED (new) |
| Benchmark driver: 0.4 s risk evaluation + 0.75 s to deceleration; 0.6 s to 0.774 g at road friction 1.0 (0.85 g after full wrap) | Rev.1 Annex 3 §3.3 Table 1; 00 series Annex 4 App. 3 §3.3 Table 1 | VERIFIED; the 00 series states the model assumes avoidance by braking only in a low-speed scenario |

### Claims corrected or downgraded

| Previous wording | Correction |
|---|---|
| "10 s transition period" | **Oversimplified.** There is no fixed transition period. §5.4.4.1 sets an **earliest MRM start** of 10 s without driver deactivation, and the transition phase lasts until deactivation or MRM start. It is not a takeover-time requirement. Registry `P17` renamed to `T_MRM_min`. |
| "MRM ≤ 4.0 m/s²" | **An aim for the deceleration demand**, not a hard limit on achieved deceleration; exceptions for very short durations and severe failure. |
| "Exact deactivation criteria unverified" | Now verified (§6.2.5, §6.3). Authority transfer in R157 is **per channel, conditional and threshold-based**. |
| "130 km/h (01 series)" | Correct, but only for systems capable of an MRM lane change (§5.2.3.1). |
| Wikipedia and ATIC as corroboration | Reclassified **NAVIGATION ONLY**; cited nowhere as evidence (enforced by test). |
| Olleja et al. as the source of the Annex parameters | The parameters are now cited from S02/S31. Olleja et al. is kept only for its finding that the benchmark models are not validated against real near-crashes. |

---

## 2. Standards access status

| Standard | Claim | Status |
|---|---|---|
| UN R157 (S02, S31) | all R157 claims above | **FULL TEXT VERIFIED** |
| UN R13-H (S01) | Type-0 6.43 m/s²; response time ≤ 0.6 s; regen stop-lamp 0.7 / 1.3 m/s² | **FULL TEXT VERIFIED** (revision of the copy not identified) |
| ISO 15622:2018 (S14) | ACC deceleration ≈ 3.5 m/s², jerk ≈ 2.5 m/s³ | **SECONDARY ONLY**: the public preview (12 pp.) has no numeric limits; registry `P19` now barred from synthesis |
| ISO 23793-1:2024 (S15) | MRM framework; type 1 straight stop, type 2 in-lane stop; light-duty L3–5 | **ABSTRACT / PUBLIC SUMMARY ONLY** (preview clause 1); no numeric claim retained |
| ISO 26262, ISO 21448, UL 4600, ISO/TS 5083 | prior-art context only | **ABSTRACT / PUBLIC SUMMARY ONLY**; not used quantitatively |

---

## 3. Assurance prior art

See `research/ASSURANCE_FRAMEWORK_PRIOR_ART.md`. General frameworks for evidence sufficiency, confidence, model credibility (including input pedigree), AD safety cases and controllability evidence already exist.

**Our measurement/assurance framing is INCREMENTAL** at best: an application of confidence and credibility ideas to fallback claims on public takeover data. No novelty is claimed.

---

## 4–6. Event / state specification and manoeuvre-specific times

See `docs/SYSTEM_EVENT_STATE_SPECIFICATION.md`.
- 11 events (the 9 required plus `E_driver_acknowledgement` and `E_first_channel_activity`, so that Manual_Start and channel activity have a home without being aliased).
- A minimal state vector by layer.
- `T_available^m` is the constant-velocity reference time from `E_TOR` to the manoeuvre boundary (observable; equals TTC at TOR for a stationary obstacle). All policy, human and vehicle dynamics go into `T_required^m`.
- Braking and steering are defined; steering is defined only when an escape path exists. Combined is **undefined**.

## 7–8. Braking slice and corrections

*(Superseded for the code state: the three simplifications below were corrected in R3B, commit `028786b`; see `docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md` §1.)*

See `docs/BRAKING_MODEL_CORRECTION_DESIGN.md`. It covers the exact scope and the three simplifications (`u_target` not wired; friction unused; authority, first input and effective input collapsed at `t_reaction`, with documentation placing authority at TOR). The correction designs A (command wiring), B (friction cap) and C (TOR ≠ authority) are not implemented.

---

## 9. Interval-only synthesis readiness

Column `interval_readiness` in the registry; the rules are enforced by the validator.

| Class | Parameters |
|---|---|
| READY AS FIXED / DIRECTLY SUPPORTED | `v0` (scenario input), `T_TOR` (scenario input / D003 protocol) |
| READY AS BOUNDED INTERVAL | `a_drag` 0.22–0.40 m/s² (100 km/h); `t2` 0.05–0.17 s; `a_max` dry 6.43–9.1 m/s² |
| CONDITIONAL / SCENARIO-SPECIFIC | `t1` (declared assumption only; not identified for takeovers); `t3` (human × vehicle); `a_pre_auto` (policy); `a_coast`; lift-off regen; `a_max` wet; μ; `T_MRM_min`; `a_MRM`; `t_button` |
| BLOCKED | `u_eff` (not wired; evidence from other contexts); jerk (derived only); ISO ACC envelope (secondary only); takeover time (abstract only; a different quantity); `a_y_max` (lateral, out of scope) |
| NOT IDENTIFIABLE | engine braking; regen roll-off; `T_authority` |

**Is an interval-only braking evaluation defensible?** **Conditionally, not yet.** It is scientifically defensible only as a labelled **capability-bound** computation for specified scenarios, with:
- `v0` and `d0` fixed
- `t2`, `a_max` and `a_drag` as evidence intervals
- `a_pre` taken from an explicit policy branch
- `t1` and `t3` as **declared assumption intervals**, not identified takeover values
- `a_max` restricted to ≤ μg (by input restriction or correction B)

It would **not** be evidence about human fallback success. The prerequisites are listed in §11.

---

## 10. Source-quality audit

The register now records, for every source:
- primary / secondary / navigation-only
- publication type
- access level and verification status
- the exact claim supported
- whether it is used quantitatively
- its transferability limitation
- a document hash where a file was read

Problems found:
- Parameters resting only on abstract, secondary or prior-phase sources: `P15` (roll-off), `P19` (ISO ACC envelope), `P21` (takeover time). All are `synthesis_entry = NO` (enforced).
- Abstract-only quantitative sources: S05 (crash deceleration 0.58 g), S09 (takeover-time meta-analysis). Neither supports a synthesis-ready parameter.
- Prior-phase sources not re-read here: S19–S26. S20 (brake lag) supports `t2`, but `t2` also rests on full-text S01/S04.
- No synthesis-ready parameter depends on Wikipedia, a certification page or marketing material.

---

## 11. Remaining blockers before R3B proper
1. Decide and document the **policy branches** for `a_pre` (hold / decelerate within §5.4.3 / release) per scenario.
2. Declare and justify **assumption intervals for `t1` and `t3`**, labelled as assumptions (not identified from D003).
3. Enforce **`a_max ≤ μg`**: either correction B (with its golden test) or an input restriction.
4. Keep authority transfer as an **input assumption** (`t_auth = t_eff = t1` in the braking slice), stated explicitly, until correction C exists.
5. Define the **scenario set** (`v0`, `d0`, μ) and the success margin before any computation.
6. Optional, for completeness: full texts of ISO 15622 / ISO 23793-1 / UL 4600 / ISO 21448, and a re-check of prior-phase sources S19–S26.
7. Steering / combined recovery remain outside scope (no geometry, gaps or steering authorship).
