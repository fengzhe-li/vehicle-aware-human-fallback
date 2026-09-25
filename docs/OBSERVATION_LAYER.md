# Observation / Measurement Layer (non-causal, mandatory)

**Status:** Adopted 2026-09-22 (Phase R0). **Partly implemented for D003 ingestion in Phase R1** (`src/data/d003_ingest.py`, §4). Not yet applied to any analysis; the pre-audit H1 scripts do not use it.
**Context:** `docs/RESEARCH_ARCHITECTURE_V2.md` §7 (rule of passage).
**Dataset-specific blockers:** `research/data_matrix/D003_KNOWN_BLOCKERS.md`.

## 1. Purpose

The observation layer states how telemetry becomes evidence. It is not a causal layer and makes no claim about the vehicle, the human, the automation, or the hazard. It exists because most defects found in the 2026-09-22 audit were measurement defects, not modelling defects.

**Rule:** no empirical conclusion may pass into causal layers A–D, the B↔A interface, or the synthesis until every item below has been specified **and validated** for the dataset and quantity concerned. Unvalidated quantities may be reported only as descriptive, provisional, and dataset-specific.

## 2. Required components

Every empirical quantity must name each of the following.

| Component | What must be stated | Validation required before use |
|---|---|---|
| **Event semantics** | What each logged event means (e.g., TOR, mode-switch press, handback, lane change), on which clock, and with which logging delay. | Agreement with the official dataset documentation. Per-trial consistency checks (uniqueness, ordering, presence). |
| **Telemetry channel semantics** | Physical meaning, unit, and **source** of each channel (driver input vs actuator output vs automation command). | Official documentation, or explicit behavioural tests with the inference labelled as inference. |
| **Observation windows** | The start and end of the window in which the quantity is computed. | The window must not extend into a period where the process being measured is not active. |
| **Authority-window definitions** | Which agent (automation / human / shared) controls each channel in each interval. | Documented system behaviour, or tested against the data; otherwise marked UNRESOLVED. |
| **Censoring and competing events** | How the quantity is handled when the window ends before the event occurs, and which events end observation. | Censoring must be reported. Informative censoring (e.g., voluntary handback) must be treated as a competing event, not ignored. |
| **Outcome-label definitions** | Exact rule for any outcome label (collision, clearance, success), including its failure modes. | Checked against independent evidence in the same data (e.g., lane occupancy at the hazard station) and manually reviewed where labels disagree. |
| **Plausibility filters** | Physiological and physical bounds, e.g., human responses faster than about 0.3 s after a stimulus are not attributable to that stimulus without further evidence. | Filter counts reported per condition; never applied silently. |
| **Dataset-specific limitations** | Scenario design (fixed budgets, scripted routes), simulator type, and missing fields. | Stated wherever a result from that dataset is reported. |

## 3. Currently known violations (D003)

The current H1 outputs (`results/H1/`, `results/H1_sensitivity/`) were produced **before** this layer existed. Known violations:

- **Observation window:** the nominal `T_stable` detector and the brake-extrema/reapplication counts run over the full post-TOR record, which for most trials extends past `Time_Manual_Stop` (handback to automation).
- **Censoring:** handback was not treated as ending human observation, so "100% settled / 0% censored" is an artifact.
- **Channel semantics:** it is unresolved whether `[00].VehicleUpdate-brake` is driver pedal input or actuated brake force (possibly automation-commanded).
- **Authority window:** it is unresolved whether pedal input before `Time_Manual_Start` controls the vehicle.
- **Outcome labels:** the collision proxy disagrees with lane occupancy at the hazard station.
- **Event semantics:** multiple TOR values; lane-change timing needs per-trial validation.

Details and numbers: `research/data_matrix/D003_KNOWN_BLOCKERS.md`.

These outputs are retained unchanged as **pre-audit artifacts**. They are not current findings.

## 4. Phase R1 implementation for D003 (ingestion level only)

`src/data/d003_ingest.py` encodes the following. It computes no human-response, stabilisation or outcome metric.

| Component | R1 encoding | Semantic status |
|---|---|---|
| Event semantics | Every distinct value of TOR, `Manual_Start`, `Manual_Stop` and lane change is kept. TOR is selected only by the owners' documented protocol (unique value at TTC 7.0 ± 0.25 s), otherwise it is unresolved. `Manual_Stop`: the first value after `Manual_Start` ends the first manual episode; later values are kept and flagged. | Protocol-justified for TOR; the meaning of extra TOR and `Manual_Stop` values is unresolved |
| Event clocks | Automated checks: `laneGap` component 2 vs `t_rel` (ERROR above 1e-4 s); value-to-first-row lag in [0, 0.2] s for each event value (WARNING otherwise); lane change validated per trial against a same-road `lane_id` transition within 0.15 s | Confirmed for TOR / `Manual_Start` / `Manual_Stop`; lane change validated per trial (1 exception) |
| Channel semantics | `laneGap` component 1 kept under a neutral name; brake channel reported as facts only; adjacent-lane zeros classified `zero_semantics_unresolved`; undocumented columns carry `_undocumented` names | Unresolved (laneGap component 1, brake, zeros) |
| Observation windows | [TOR, first manual-episode end) and [`Manual_Start`, first manual-episode end), both provided. The TOR-based window is undefined when the TOR anchor is unresolved. | Windows are defined; which one is the human-control window is unresolved |
| Authority windows | `manual_start_authority_semantics = UNRESOLVED` | Unresolved |
| First human input | Brake and steering *candidates* only. `first_validated_human_input` is always empty, with the reason recorded. | Not validatable with current semantics |
| Censoring / competing events | Handback (`Manual_Stop`) is represented as the end of the first manual episode; no time-to-event metric is defined in R1 | Rule defined in §2; not yet used |
| Outcome labels | None defined in R1; the pre-audit collision proxy remains withdrawn | — |
| Plausibility filters | First-input candidates under 0.3 s after TOR are flagged (78 of 492 anchored trials) | Flag only; no exclusion rule adopted |
| Dataset limitations | Header variant, export footer and lane-numbering context are recorded per trial | — |

Integration tests (`tests/test_d003_ingest.py`) pin the archive-level counts, so any change in ingestion behaviour is caught.

## 5. Phase R2A additions

**Interpretation rule (blocker B17, all scenarios).** The D003 accelerator, brake and steering channels are **not driver-only channels**. They may contain automation actuation, simulator/controller activity, driver activity, or a mixture. Until authoritative semantics are available:
- any inference of human first input from these channels is UNRESOLVED;
- outputs based on them are described only as channel activity (e.g., "brake-channel activity", "steering-channel activity", "accelerator-channel activity", "pre/post-TOR channel transition");
- they are never described as driver action, driver command or human input.

Activity within 0.3 s of TOR is treated as evidence that channel authorship is unresolved, not as an outlier-filtering problem.

**Populations and windows** (`src/data/d003_populations.py`):

| Population | n | Rule |
|---|---|---|
| RAW | 513 | every simulator file |
| TOR_PRESENT | 498 | TOR column present |
| TOR_ANCHORED | 492 | TOR anchor resolved |
| OWNER_WINDOW_ELIGIBLE | 478 | TOR_ANCHORED, lane change validated, TOR < lane change |
| LANE_CHANGE_ANCHORED | 477 | OWNER_WINDOW_ELIGIBLE and lane change < handback |
| MANUAL_WINDOW_ELIGIBLE | 492 | TOR_ANCHORED, single Manual_Start, handback defined, TOR and Manual_Start before handback |
| OWNER_ANALYSIS_SET | UNKNOWN / NOT RECONSTRUCTED | owners' 466; not public |

There is no universal "clean" denominator. Every output states which population it uses.

| Window | Definition | Handback-bounded |
|---|---|---|
| POST_TOR_MANUAL | [TOR, handback) | yes |
| POST_BUTTON_MANUAL | [Manual_Start, handback); Manual_Start is a button/event marker, authority UNRESOLVED | yes |
| MANUAL_TOR_TO_LANE_CHANGE | [TOR, lane change], requires lane change < handback | yes |
| OWNER_TOR_TO_LANE_CHANGE | [TOR, lane change] as published by the owners | **no**, stored separately and never mixed with the manual-interval window |

`window_bounds` raises `ObservationWindowError` if a manual-interval window would extend past handback. Handback is a protocol-driven competing event, not independent censoring; no survival model is fitted in R2A.
