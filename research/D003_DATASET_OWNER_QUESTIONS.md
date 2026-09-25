# Questions for the D003 dataset owners: full technical version (NOT SENT)

> **2026-09-24:** per the user, there is no external owner to contact. These questions now serve as an internal verification checklist; items resolved or reclassified from the archive's own documentation are listed in `docs/R4_INTERNAL_SOURCE_OF_TRUTH_AUDIT.md`.

**Status:** refined in Phase R2B (2026-09-22). Not sent. No response is assumed; all affected semantics stay UNRESOLVED until authoritative answers exist. A short email-ready version is in `research/D003_DATASET_OWNER_EMAIL_DRAFT.md`.

**Dataset:** "Driver takeover responses in conditionally automated driving", TU Delft / 4TU.ResearchData, DOI 10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB. Authors: Kexin Liang, Simeon C. Calvert, J. W. C. van Lint. Related paper: arXiv 2507.22252.

Blocker references point to `research/data_matrix/D003_KNOWN_BLOCKERS.md`.

## A. Control-channel authorship (highest priority; B17, B6)

Observation behind these questions: within 0.3 s of the TOR, before a plausible human reaction, the accelerator channel drops to ~0 in 6 of 9 scenario cells and not in the other 3; the brake channel rises in some cells; and the steering channel is already moving before the TOR in some cells.

- **A1.** What exactly does `VehicleUpdate-brake` record, and in what unit? The data dictionary says "brake force, N"; the paper refers to "braking pedal positions".
- **A2.** Is it the driver's pedal (sensor), a commanded input, a physical actuator state, or a simulator output?
- **A3.** Does the automation (or the simulator's controller) write to the same brake channel while it is in control or at the TOR?
- **A4.** Same questions for `VehicleUpdate-steeringWheelAngle`: driver hand-wheel sensor, automation-commanded wheel angle, or both?
- **A5.** Same questions for `VehicleUpdate-accelerator`.
- **A6.** Why do these channel patterns at the TOR differ between the density × n-back scenarios? Does the automation use different transition or withdrawal logic in different scenarios?

## B. Authority and handover semantics (B7, B14)

- **B1.** What does `Time_Manual_Start` mean exactly? Does pressing the button change longitudinal and lateral authority immediately, or can pedal and steering inputs affect the vehicle before the press? (Braking appears to affect the vehicle before the press.)
- **B2.** What does `Time_Manual_Stop` mean exactly, and what do the additional `Manual_Stop` values in 12 trials represent?
- **B3.** What happens to automation authority at the TOR itself (continued control, partial release, full release)?

## C. Multi-TOR trials (B1)

- **C1.** Why do 26 trials (25 in density 20 / 1-back) contain 2–3 distinct `Time_Takeover_Request` values, typically at TTC ≈ 7 s and ≈ 6 s?
- **C2.** Which value is the protocol-valid TOR presented to the participant? In 6 trials more than one value is near TTC 7 s.
- **C3.** Are the repeated values logging artefacts, reminders, or genuinely repeated requests (audible/visual)?

## D. `laneGap` (B4, B5)

- **D1.** What is the exact definition of `roadInfo-laneGap.0`?
- **D2.** First component: meaning and unit. It behaves like a signed lateral offset from the current lane centre, but that is our inference.
- **D3.** Second component: it equals time since the first logged row. Is that correct and intended?
- **D4.** Which lane is the reference, and what is the sign convention (left/right positive)?

## E. Adjacent-lane channels (channels 82–84)

- **E1.** Does 0 mean no vehicle in range, a measured zero distance, missing data, or a sentinel value?

## F. Vehicle and automation model

- **F1.** What vehicle type and longitudinal model does the simulator use?
- **F2.** What braking model (pedal-to-deceleration mapping, delay, build-up)? Is it the same in all scenarios?
- **F3.** How does the automation behave before and after the TOR (speed holding, releasing, braking, steering)?
- **F4.** Are emergency braking, friction braking, or regenerative/engine-drag deceleration represented separately, or not at all?

## G. Retained questions (file structure, analysis set, metric definitions)

- **G1.** In 42 files the final row has an empty `time` and two blocks of values; the second block matches the export channels. What does the first block mean?
- **G2.** Could you share the list of the 466 analysed takeovers, or reproducible exclusion criteria (the 16 "control before TOR / forgot button" and 31 "questionnaire / hardware" cases)?
- **G3.** How were takeover time, minimum TTC, maximum steering wheel angle, maximum acceleration and maximum deceleration computed (thresholds, axis and sign conventions, and handling of samples where the vehicle is stationary or TTC is negative)? Are descriptive values published anywhere?
- **G4.** Were there practice or familiarisation drives before the nine recorded scenarios?
