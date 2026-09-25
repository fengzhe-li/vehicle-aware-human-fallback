# Response Episode Definition

**Status:** Design document only. Per the task instruction, the full dataset is **not** mass-processed here — this defines how an episode *would* be extracted, and verifies measurability using the small raw samples already pulled in `raw_dataset_forensics.md`, not a full run.

## Why this is needed

`t_delay`, `t_buildup`, and the replacement regen-response-speed differential (`control_ownership_timeline.md` / `vehicle_response_model.md`) are currently LITERATURE_ONLY or COUNTERFACTUAL_ONLY (`phase1A_identifiability_final.csv`) precisely because no braking episode has yet been located and measured in this project's own raw-data access. This document makes "locate and measure an episode" a well-defined procedure rather than a vague aspiration.

## Candidate source: D004 (OpenLKA EV Dataset)

Chosen over D005 (no brake channel at all — see `raw_dataset_forensics.md`) and D001 (gated access; and only its 38.3% 100Hz subset would even be usable). D004's real, confirmed schema provides everything needed: `brake_padel_status` (binary onset flag), `state_gas_pos` (continuous accelerator position), `state_regen_break_enable` (binary regen-active flag), `aEgo` (continuous realized acceleration, ~100Hz-class), `vEgo` (continuous speed).

## Episode definition

**Event trigger:** the first sample where `brake_padel_status` transitions `0 -> 1` (or, for a regen-only episode, `state_regen_break_enable` transitions `False -> True` while `brake_padel_status` remains 0 — this distinguishes a regen-triggered episode from a friction-brake episode, which is itself useful data given the reformulated mechanism in `control_ownership_timeline.md`).

**Baseline window:** the 1.0s of samples immediately preceding the trigger, used to confirm the vehicle was in a stable, non-braking state beforehand (`brake_padel_status = 0` throughout, `aEgo` within a small band around 0, consistent with steady-state cruise) — an episode whose baseline window is not stable (e.g., already mid-maneuver) is excluded (see quality filters below).

**Response onset:** the first sample **after** the trigger at which `aEgo` crosses a fixed deceleration threshold distinguishable from baseline noise (proposed: `aEgo < -0.3 m/s^2`, chosen as roughly 3x the baseline noise band typically seen in the sampled data — e.g. the `-0.585 to 0.446 m/s^2` range observed in ordinary non-braking driving in the mid-file sample pulled for `raw_dataset_forensics.md`). `t_delay := t(response_onset) - t(trigger)`.

**Peak/plateau definition:** the first local maximum of `|aEgo|` reached and sustained (does not immediately reverse) for at least 3 consecutive samples, to avoid triggering on a single noisy spike. `a_max_episode := |aEgo|` at this point.

**Build-up-time definition:** `t_buildup := t(peak/plateau) - t(response_onset)`.

**Low-speed roll-off definition:** for episodes where `vEgo` approaches near-zero before the episode ends, compare `|aEgo|` in the final 1.0s of the episode (as `vEgo -> 0`) against the episode's own peak `|aEgo|`. A roll-off is present if the ratio falls below some fraction (not yet fixed — this is exactly the numeric gap `v_rolloff` has in `phase1A_identifiability_final.csv`; this episode definition would let that fraction be **measured** rather than assumed, once enough near-standstill episodes are found).

**Quality filters / exclusion criteria:**
- Baseline window must be stable (as above) — excludes episodes starting mid-maneuver.
- `op_enable` must be consistently `False` throughout the human-control portion of the episode (per `control_ownership_timeline.md`'s `w_authority` distinction) — an episode where openpilot's own longitudinal control was active would be measuring automation behaviour (relevant to a different, AEB-architecture-style question, per L011's framing), not human post-takeover braking, and must not be silently mixed into the same pool.
- Episode must contain at least one `aEgo` sample beyond the response-onset threshold — otherwise there is no response to measure (this is not a failure of the definition, it is a valid negative result: "no braking event in this window," exactly as logged for the two windows already sampled in `raw_dataset_forensics.md`).
- Minimum episode length: propose 2.0s from trigger to end-of-episode (defined as `vEgo` reaching a local minimum or `aEgo` returning to near-zero), to ensure `t_buildup` and any roll-off behaviour have room to appear given the sampling rate (~100Hz-class, so 2.0s gives ~200 samples — more than sufficient resolution for values in the 0.05-2s range being estimated).

## What this does NOT do

It does not run this procedure across the dataset. It does not produce a number. It exists so that, when Phase 1 or a later pass does run this procedure, `t_delay`/`t_buildup`/roll-off measurement is not designed ad hoc under time pressure — the trigger, window, and threshold choices are written down and open to challenge *before* being applied, consistent with the same pre-registration discipline already used for Gate A (`gate_A_preregistration.md`).

## Measurability check (not full extraction)

Using the two real windows already pulled in `raw_dataset_forensics.md`: neither contained a `brake_padel_status` or `state_regen_break_enable` transition, so this definition could not be exercised end-to-end on real data in this pass. This is itself the correct, honest outcome of a measurability check on a small sample — it confirms the *fields* needed for this definition exist and are well-formed (continuous `aEgo`/`vEgo`, binary onset flags), but it does not yet confirm the definition produces sensible numbers on a real episode, because no real episode was found in the ~2,260 rows inspected. A wider scan (not performed here, per the task's instruction not to mass-process) would be the natural next step.
