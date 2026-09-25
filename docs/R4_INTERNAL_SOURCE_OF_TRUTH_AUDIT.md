# R4 internal source-of-truth audit for the blocked D003 semantics

**Status:** 2026-09-24. Audit only: no synthesis, no new analysis of the trial data beyond reading raw source fields.
**Trigger:** the user stated that D003 is part of the project and there is no external owner to contact. This audit replaces the "wait for owner clarification" recommendation in `docs/R4_SYNTHESIS_READINESS.md` §9.

## 0. Scope of the internal search and what it found

**Searched:**
- the full repository (tracked files, all five branches, full history);
- both parallel worktrees (the unmerged D003 ingestion-QA branch at `9bef347` and the ingestion-hardening branch, identical to `main` at `1ad1951`);
- `~/Documents`, `~/Downloads` and `~/Desktop`, by file name and by content (`Time_Manual_Start`, `VehicleUpdate-brake`, `Distance_to_Construction`);
- every file inside the D003 archive, including the shipped notebook.

**Found:** no D003-generating artifact of any kind. There is no simulator scenario or project file, export-channel configuration, automation or vehicle-model configuration, experiment protocol, or recording script.
- The branches hold only this project's loaders and QA scripts. The unmerged QA branch (`9bef347`) itself flags `AUTHORITY_SEMANTICS_UNVERIFIED`.
- The archive's notebook `.ipynb_checkpoints/rename_files-checkpoint.ipynb` is empty (72 bytes, no cells).
- The archive also contains an Office lock file (`~$gap_1_nback_0_n_1_gaze.xlsx`). It was not read beyond its name, because it holds only editor metadata.

**The project's own records identify D003 as an external published archive.** `experiments/H_human_internal_model/H0_PUBLIC_DATA_AUDIT.md` §D003 records it as 4TU.ResearchData DOI 10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB (450,332,391 bytes, open public), with authors Liang, Calvert and van Lint (S17, S18). The archive was imported as data, not generated in this repository.

**Consequence:** the internal sources of truth are (i) the archive's own documentation (README, data dictionary, file naming, raw headers) and (ii) the dataset owners' paper already in the source register (S17). If the experiment was run inside the user's team, its original simulator and export files are the true source of truth, and **they are not present in any location searched.**

## 1. Findings per item

| # | Item | Source (exact) | Recovered meaning | Confidence | Class if unresolved |
|---|---|---|---|---|---|
| 1a | Brake channel | data dictionary, simulator section: `car_brake` "brake force", unit N; raw `[00].VehicleUpdate-brake` | named as brake force in N. The owners' paper speaks of pedal positions; units conflict unresolved | medium (name/unit only) | **B**: name documented; driver vs automation authorship only by design intent (1f) |
| 1b | Accelerator channel | dictionary: `car_accelerator` "gas position [0:1]"; raw `[00].VehicleUpdate-accelerator` | normalised gas position | medium | **B** (as 1a) |
| 1c | Steering | dictionary: `car_steering_wheel_angle` (rad), `car_steering_wheel_speed` (rad/s); raw also has `[00].VehicleUpdate-steeringTorq`, **not in the dictionary** (range about −2 to +2.8 in sampled trials) | angle and speed documented; torque present but undocumented (driver torque vs force feedback unknown) | angle: medium; torque: none | angle **B**; torque semantics **C** |
| 1d | Manual_Start | dictionary: `Time_Manual_Start` "the time stamp when the participant pressed the switch button and switched to manual mode"; S17: drivers "press the mode switch button to enable manual inputs" | **documented design intent:** a button-triggered switch to manual mode that enables manual inputs | medium-high (two independent owner statements) | verified behaviour: **B** |
| 1e | Manual_Stop | dictionary: `Time_Manual_Stop` "…pressed the switch button and switched to automated mode"; S17: drivers hand control back after the lane change | switch back to automated mode (handback); protocol-driven | medium-high | — (multiple values in 12 trials still unexplained: **B**) |
| 1f | Authority / mode flags | raw channels: `[00].VehicleUpdate-state` is **2.0 in every sample of all 513 trials** (never changes); `[00].VehicleUpdate-lights` is an undocumented bit field | **no mode or authority flag exists in the data.** Authority is documented only through Manual_Start (1d) | high (for "no flag") | per-channel authority timing: **B** (design intent only) |
| 1g | Lane change | dictionary: `Time_Lane_Change` "the time when the car changed to the **left** lane during takeover"; raw `[78 (Time/Time_Lane_Change)]` | lane crossing to the **left** lane; the escape direction is documented. Steering onset is not documented | medium-high | steering onset **B** (via 1c under 1d) |
| 1h | Hazard | dictionary: `Distance_to_Construction` "distance to collosion" [sic], m; `Time_TTC` = distance_to_collision / car_speed_x | the hazard is a **construction zone**; a longitudinal distance to it is logged | medium-high | hazard station **A** (car position + distance); lateral extent / occupied lane **C** |
| 1i | Adjacent-lane traffic | dictionary: `Distance_to_Following_Vehicle`, `Distance_to_Leading_Vehicle_Next_Lane`, `Distance_to_Following_Vehicle_Next_Lane` (m) | gap distances to vehicles in the left (target) lane are logged | medium | zero / sentinel semantics **B** |
| 1j | Road / lane geometry | dictionary `road_info`: roadId, roadAbscissa, roadGap, roadAngle, laneId, laneGap (names only) | names only; lane width and laneGap semantics not documented | low | lane width **C**; laneGap **B** |
| 1k | Vehicle model | none in archive or project | — | — | **C** |
| 1l | Automation model / withdrawal behaviour | none in archive or project; S17 does not describe automation behaviour at TOR | — | — | **C** (behaviour at TOR only observable as the B17 pattern) |
| 1m | Participant ID mapping | dictionary: `id` "assigned id for each participant" in every section; `scenario_info` = `'density_' + i + '_nback_' + j + '_id_' + n`, n = [1:57]; the rename notebook is empty; the lock-file name shows an earlier `gap_*_nback_*_n_*` naming | filename id n and questionnaire id share one documented definition; the renaming mapping itself is undocumented | unchanged: **strongly supported but not explicit** | **B** |

## 2. What this changes

1. **B7 (Manual_Start authority)** moves from "unresolved" to **documented design intent, behaviour unverified**. Manual_Start is the switch to manual mode that enables manual inputs.
   - This is consistent with the R2A observation that some brake and accelerator channel activity occurs within 0.3 s of TOR, before a plausible human reaction, and differs by cell. By design that activity cannot be driver-effective, because manual inputs are not yet enabled.
   - Under this intent, `t_button` estimates TOR → longitudinal and lateral authority transfer (definition A of the gate review).
2. **B17 (channel authorship) splits in two:**
   - **Before Manual_Start:** automation or ignored input; not driver-effective by design.
   - **After Manual_Start, in manual mode:** driver-generated by design.

   Post-switch braking onset, braking strength (in the documented unit) and steering activity are therefore **potentially recoverable internally (class B)**, but only after a verification analysis that the post-switch channels carry no automation signature. Until then no human-braking claim is made.
3. **Hazard station and target-lane gaps** are **recoverable internally** from logged channels (class A and B). Lateral geometry and lane width are not.
4. **Vehicle and automation models** remain **not identifiable** from project artifacts (class C).
5. **Participant-ID join:** unchanged.

## 3. Revised R4 blocker list (internal artifacts only)

| # | Blocker | New status | Internally resolvable? |
|---|---|---|---|
| 1 | Post-Manual_Start channel authorship (was B17) | design intent documented (manual mode enables manual inputs); **verification pending** | **yes (class B)**: verification analysis |
| 2 | Pre-Manual_Start channel meaning (automation behaviour at TOR) | not driver-effective by design; controller semantics undocumented | **no (C)** for automation logic; the pattern is observable |
| 3 | Manual_Start as authority transfer (was B7) | documented design intent; per-channel effect unverified | partly **(B)**: consistency checks |
| 4 | Hazard geometry / escape path | hazard station and target-lane gaps recoverable; lateral extent, lane width, laneGap and zero semantics not | **A/B** for longitudinal and gap; **C** for lateral geometry |
| 5 | Brake unit conflict (force N vs pedal position) | unresolved | **no (C)** for units; onset timing unaffected |
| 6 | Vehicle / automation model | absent | **no (C)** |
| 7 | Recovery-completion definition | conceptual; handback documented as a protocol switch | definitional work, not data |
| 8 | EV / one-pedal familiarity (M) | single simulator vehicle | permanently **C** for D003 |
| 9 | Participant-ID join | strongly supported, not explicit | **B** (no mapping file) |

## 4. Revised recommendation (replaces R4 §9)

**Next phase: internal verification of the documented Manual_Start design intent.** This is not synthesis. It would:
- (a) test whether brake, accelerator and steering channels after Manual_Start are free of the cell-specific automation signatures seen at TOR;
- (b) test whether vehicle deceleration responds to the brake channel only after Manual_Start;
- (c) derive the hazard station and target-lane gap histories from the logged channels, with their zero semantics flagged.

If (a) and (b) pass, driver-attributed post-switch braking onset, braking strength (in the documented unit) and steering activity would become measurable. That would give R3B's t1 and u, and a future steering analysis, an empirical anchor. If they fail, B17 remains a permanent blocker for D003. The vehicle and automation models stay not identifiable either way, unless the original simulator and export files are located.
