# D003 (TU Delft takeover dataset): known blockers and prior analyses

**Status:** Documented 2026-09-22 (Phase R0); updated in Phase R1 (ingestion and measurement-semantics repair) and Phase R2A (pipeline consolidation; new dataset-wide blocker B17). Each blocker carries an explicit R1 status. No blocker is resolved by documentation alone.

**Dataset:** "Driver takeover responses in conditionally automated driving", TU Delft / 4TU.ResearchData, DOI 10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB.
- Local archive (gitignored): `data/external/d003/tu_delft_takeover.zip`, 450,332,391 bytes, sha256 `6e85e5365d0ae5e356559d20cf0b95cf81d60f9bd3ba5a52ec36021f664ca212`.
- 4TU version number not yet confirmed.

**Evidence basis:** R0 numbers came from read-only probes outside the repository. R1 numbers are reproduced by repository code (`src/data/d003_ingest.py`, `src/experiments/r1_ingestion_validation.py`) and pinned by `tests/test_d003_ingest.py`.

---

## 1. Blockers

Status vocabulary (Phase R1): **RESOLVED**, **PARTIALLY RESOLVED**, **STILL OPEN**, **BENIGN**. A semantic question is marked resolved only with official documentation or reproducible evidence.

**R1 implementation:** strict ingestion in `src/data/d003_ingest.py`; tests in `tests/test_d003_ingest.py`; validation outputs in `results/R1_ingestion_validation/` (produced by `src/experiments/r1_ingestion_validation.py`). Counts below are reproduced by that code and pinned by integration tests.

| Blocker | R0 status | R1 status | R2A status |
|---|---|---|---|
| B1 Multiple TOR values | OPEN | PARTIALLY RESOLVED | PARTIALLY RESOLVED |
| B2 Missing-TOR trials | OPEN | RESOLVED (handling); owner match STILL OPEN (see B12) | RESOLVED (handling) |
| B3 NaN-timestamp final row | BENIGN (R0 wording was wrong) | BENIGN, re-characterised | BENIGN |
| B4 `lane_gap` parsing | OPEN | RESOLVED (technically parsed) | RESOLVED |
| B5 `lane_gap` semantics | INFERRED | STILL OPEN | STILL OPEN |
| B6 Brake-channel semantics | UNRESOLVED | STILL OPEN | STILL OPEN; subsumed by B17 for authorship |
| B7 `Time_Manual_Start` authority | UNRESOLVED | STILL OPEN | STILL OPEN |
| B8 Lane numbering | OPEN | PARTIALLY RESOLVED | PARTIALLY RESOLVED |
| B9 Event clocks | PARTLY CONFIRMED | PARTIALLY RESOLVED | PARTIALLY RESOLVED |
| B10 Collision proxy | OPEN (invalid) | STILL OPEN (not relabelled in R1) | Proxy RETIRED from active outputs (historical only); safety outcome STILL OPEN |
| B11 Factorial aliasing | OPEN (design limitation) | STILL OPEN (design limitation; not addressable by ingestion) | STILL OPEN; extended to automation-transition behaviour |
| B12 Owner prior analyses | Citation corrected in R0 | PARTIALLY RESOLVED: definitions/counts compared; set reconciliation STILL OPEN | PARTIALLY RESOLVED; set NOT RECONSTRUCTIBLE |
| B13 TTC outside its defined domain (new) | — | PARTIALLY RESOLVED | PARTIALLY RESOLVED |
| B14 Multiple `Time_Manual_Stop` values (new) | — | PARTIALLY RESOLVED | PARTIALLY RESOLVED |
| B15 Legacy loader and pre-audit H1 scripts (new) | — | STILL OPEN | PARTIALLY RESOLVED (deprecated; historical only) |
| B16 Header variants (new, formalised) | — | RESOLVED | RESOLVED |
| B17 Control-channel authorship / automation actuation at TOR (new) | — | — | STILL OPEN / DATASET-WIDE |

### B1. Multiple TOR values: PARTIALLY RESOLVED
- 26 trials have 2–3 distinct TOR values: 25 in `density_20_nback_1`, 1 in `density_20_nback_2`.
- **Handling (R1):** every distinct value and the TTC at each value are kept (`tor_raw_values`, `tor_ttc_at_values`). No TOR is taken silently. A value is selected only by the owners' documented protocol: "a takeover request is triggered seven seconds before the ego vehicle would collide" (arXiv 2507.22252). The rule is: select the **unique** value with TTC within 7.0 ± 0.25 s; otherwise the anchor is **unresolved** and TOR-anchored windows are not defined.
- **Result:** 20 trials `MULTI_RESOLVED_BY_PROTOCOL_TTC` (first value at TTC 7.00–7.11 s, second at 5.93–6.00 s); **6 trials `MULTI_UNRESOLVED`**:
  - `density_20_nback_1_id_13` and `_id_35` have a third value that is also at TTC ≈ 7.05–7.09 s;
  - `density_20_nback_1_id_27`, `_id_37`, `_id_42`, `_id_50` have two values both at TTC ≈ 7.0–7.17 s.
- **Still open:** the source of the extra TOR values (a second scripted trigger is an unconfirmed inference). The 6 unresolved trials cannot be anchored without an undocumented assumption.
- **R2B sensitivity:** excluding all 20 protocol-resolved multi-TOR trials leaves the `t_button` exposure result unchanged (slope −0.033 → −0.036 s per exposure; both 95% CIs below 0).

### B2. Missing-TOR trials: RESOLVED (handling)
- 15 files use header variant `NO_TOR_44` (TOR column absent). They are labelled `MISSING_TOR_COLUMN` and excluded from every TOR-anchored quantity.
- Whether these are the owners' 16 "control before TOR / forgot button" exclusions is an inference (see B12).

### B3. NaN-timestamp final row: BENIGN, re-characterised (R0 wording corrected)
- **Correction:** R0 described these 42 rows as empty ("trailing empty row"; "the row carries no data"). That was wrong. The rows are **not empty**.
- Each of the 42 final rows has an empty `time` cell followed by exactly 2 × k values, where k is the number of export-channel columns in that file's header (18 values for k = 9 in 39 files; 16 values for k = 8 in 3 files). The rows are left-shifted: the values occupy the first vehicle columns.
- The last k values equal the export channels' values (TOR, manual start/stop, TTC, lane change, distances). In all 42 rows, each event value equals the latest value of that event channel in the file body. The first k values have **undocumented meaning** and are kept raw (`footer["unknown_block"]`).
- **Handling (R1):** the row is parsed as an export-channel footer, excluded from telemetry, cross-checked (`FOOTER_EVENTS_CONSISTENT`, INFO) and would raise `FOOTER_EVENT_MISMATCH` (ERROR) if inconsistent. Any empty timestamp before the final row, or a footer of unexpected shape, fails loudly.
- It is benign because it duplicates, and agrees with, information already in the body. The legacy loader drops it silently, which happens to be harmless.
- Row counts: 1,190–3,760 (median 1,585). The 1,953-rows assumption is not used anywhere in R1 code.

### B4. `lane_gap` parsing: RESOLVED (technically parsed)
- Header field `"[00].VehicleUpdate-roadInfo-laneGap.0,time"`; each cell is the quoted pair `"<value>,<relative time>"`.
- **Handling (R1):** `lane_gap_raw` (original cell), `lane_gap_component1` (value) and `lane_gap_reltime` (second component) are parsed separately. The token `null` (exactly one per trial, in the first row) is counted and set to NaN. Any cell that is not a pair fails.
- Second component vs `t_rel`: max absolute difference 9.5e-8 s over all 513 trials (tolerance 1e-4 s; exceeding it is an ERROR).
- The legacy loader still yields an all-NaN `lane_gap` (see B15).

### B5. `lane_gap` semantics: STILL OPEN
- The data dictionary gives no definition or unit. Component 1 is **not** renamed to a lane-centre offset.
- Reproducible behavioural evidence (R1): at 1,136 same-road lane transitions, |Δ component 1| lies within 3.0–4.0 m in 1,123 cases (13 outside, in 7 trials; surfaced as `LANE_GAP_JUMP_OUT_OF_RANGE`, INFO). This is consistent with, but does not establish, a signed lateral offset from the current lane centre on ~3.5 m lanes.

### B6. Brake-channel semantics: STILL OPEN (authorship question subsumed by B17)
- **R2A:** the question of *who* produces the brake channel is now part of the dataset-wide blocker B17, which also covers the accelerator and steering channels. B6 remains for the brake channel's physical meaning and unit.
- Dictionary: `car_brake`, "brake force, N". Owners' paper: "braking pedal positions".
- R1 records observable facts per trial in `trial_qa.csv`: the start-of-run transient, samples above 15 units before TOR (excluding the first 1 s), samples above 15 units after handback, first brake candidate after TOR, and the Spearman correlation between brake and longitudinal acceleration within [TOR, handback).
- First-input candidates within 0.3 s of TOR: 78 of 492 anchored trials (flag `FIRST_INPUT_CANDIDATE_UNDER_0P3S`). Candidates are never promoted to validated human input (`first_validated_human_input` is always empty, with the reason recorded).
- Whether the channel is driver pedal force, pedal position, actuated braking, or a mixed or simulator-derived signal is **not** decided.

### B7. Authority semantics of `Time_Manual_Start`: STILL OPEN
- Encoded as `manual_start_authority_semantics = UNRESOLVED`. Two windows are provided without choosing between them: [TOR, handback) and [Manual_Start, handback).

### B8. Lane numbering: PARTIALLY RESOLVED
- R1 records every `lane_id` change with the road IDs on both sides. Changes across a `road_id` boundary are labelled renumbering (`same_road = False`), not lane changes.
- Validated lane-change transitions: 2→3 (283), 6→5 (213), 7→6 (2); the clock-exception trial matches a 2→3 transition. No code in R1 assumes 2→3.
- **Still open:** left/right meaning is not inferred from numeric IDs. The dictionary's "changed to the left lane" describes the event, not the ID ordering. Stabilisation candidate C in the legacy H1 script still hard-codes lane 3 (see B15).

### B9. Event clocks: PARTIALLY RESOLVED
**Confirmed and now enforced by automated checks (R1):**
- `time` is Unix epoch seconds; `t_rel = time − time[0]`.
- `laneGap` component 2 equals `t_rel` in all 513 trials (max error 9.5e-8 s).
- For each distinct TOR, `Manual_Start`, `Manual_Stop` and lane-change value, the lag between the value and the first row carrying it lies in [0, 0.2] s. The only exception in the archive is one lane-change value (below).
- Sampling interval ≤ 0.05 s in every trial.

**Requires per-trial validation (implemented; exceptions surfaced, not accepted):**
- Lane-change timing is validated against a same-road `lane_id` transition within 0.15 s: 498 `VALIDATED`, 14 `ABSENT_COLUMN`, 1 `CLOCK_EXCEPTION` (`density_10_nback_1_id_8`: channel appears 0.95 s before its stated value, and the lane transition is 0.949 s before the stated value).
- Lane-change-anchored metrics (e.g., the owner window TOR → lane change) are computed only for `VALIDATED` lane changes.
- TOR selection in multi-TOR trials: see B1.

### B10. Collision proxy: RETIRED from active outputs (R2A); safety outcome STILL OPEN
- **R2A:** the proxy is removed from all active outputs and claims. Historical labels are preserved in `research/data_matrix/d003_trial_qa.csv`, marked HISTORICAL ONLY / WITHDRAWN in `results/HISTORICAL_OUTPUTS_MANIFEST.md`. The pre-audit test that asserted the labels was replaced by `test_historical_collision_proxy_is_withdrawn_and_contradicted_by_lane_evidence`. Among TOR-anchored trials, 11 reach the hazard station in their TOR lane on the same road, and only 3 of those carry a historical label. The 3 labelled trials that are not in-lane passages are the lane-change clock exception, one adjacent-lane crossing, and one trial without a TOR anchor. No replacement safety label was created: hazard geometry is not identified. `T_pass` is kept only as a longitudinal hazard-station crossing (vehicle-state event), not as clearance or collision.
- Not relabelled in R1. The withdrawn proxy is still asserted by `tests/test_h1_sensitivity_and_audit.py::test_derived_collision_proxies_old_clear_audit_and_tpass`. That test is not changed or weakened in R1; it encodes pre-audit labels and uses the id-8 lane-change value, which R1 now flags as a clock exception.
- Observation from R1: all 14 `NO_LANE_CHANGE_44` trials (no lane-change channel) are in density-20 cells. Relabelling needs obstacle geometry, which the data do not contain.

### B11. Factorial aliasing: STILL OPEN (design limitation; extended in R2A)
- **R2A:** each density × n-back cell is aliased with road segment, entry speed, hazard geometry and state, lane configuration, time and order within the run, **and automation-transition behaviour around TOR** (see B17). Cell comparisons are descriptive only. Workload or density effects are not identifiable.
- Unchanged: each cell is a distinct road segment with its own speed and distance at TOR. R1 records `road_id_at_tor` and `lane_id_at_tor` per trial. Ingestion cannot remove the aliasing.

### B12. Dataset-owner prior analyses: PARTIALLY RESOLVED
- Citation deficiency corrected in R0.
- **R1:** the owners' metric definitions and windows were implemented and compared (§3); per-trial accounting is in `results/R1_ingestion_validation/owner_reconciliation.csv`.
- **Set reconciliation: STILL OPEN (stop condition reported, not worked around).** The owners report 513 → 466 (−16 control before TOR / forgot button; −31 incomplete questionnaires or hardware). Their per-trial list is not published. The evidence:
  - 15 trials lack a TOR column (inferred candidate for the 16).
  - 31 trials lack an eye-tracking gaze file (inferred candidate for part of the 31), of which 3 overlap with the no-TOR trials.
  - The public questionnaire file has no missing values, so "incomplete questionnaires" cannot be identified.

  The 466-trial set cannot be reconstructed without undocumented assumptions, so it has not been forced.
- The owners' numerical results were not available in the sources read; no numerical comparison was made.

### B13. TTC outside its defined domain (new): PARTIALLY RESOLVED
- Dictionary: `Time_TTC` = distance_to_collision / car_speed_x. Away from very low speeds, the channel agrees with distance/speed to a median of 0.007 s (sampled trials).
- In 22 trials the vehicle stops (speed ≤ 0) inside [TOR, lane change]. There the channel takes extreme values (down to −2.4 × 10⁸ s), including negative values next to small positive speeds, because the export channel is sampled out of step with the vehicle speed channel.
- **Handling (R1):** minimum TTC uses only samples in the formula's domain (distance > 0, speed > 0, TTC > 0). Excluded samples are counted (`n_ttc_samples_excluded`), and stopped-vehicle trials are flagged (`vehicle_stopped_in_window`).
- **Still open:** how the owners handled these samples is not stated.

### B14. Multiple `Time_Manual_Stop` values (new): PARTIALLY RESOLVED
- 12 trials have 2–3 distinct `Manual_Stop` values, all after the lane change, while `Manual_Start` has one value in every trial.
- **Handling (R1):** all values are kept. The first value after `Manual_Start` is used as the end of the first manual episode (dictionary: the switch to automated mode). Trials are flagged `HANDBACK_MULTI_...`. The meaning of the later values is unresolved.

### B15. Legacy loader and pre-audit H1 scripts (new): PARTIALLY RESOLVED (R2A)
- **R2A:** `D003Dataset`, `run_full_h1_analysis` and `run_sensitivity_audit` now emit `DeprecationWarning` and are classified DEPRECATED / HISTORICAL ONLY in `research/data_matrix/D003_PIPELINE_REGISTRY.md`. They still reproduce the historical outputs byte-for-byte (checked by `tests/test_r2a.py`). No active analysis imports the legacy loader.
- `src/data/d003_loader.py`, `src/experiments/h1_recovery_analysis.py` and `h1_sensitivity_analysis.py` still:
  - silently take the first TOR
  - produce an all-NaN `lane_gap`
  - search windows past `Time_Manual_Stop`
  - hard-code lane 3 (candidate C)
- R1 added explicit legacy notices to their docstrings but did **not** change their behaviour: their outputs are pre-audit artifacts, and existing tests depend on them. They must not be rerun for new results, and they are to be migrated or retired in R2.

### B16. Header variants (new, formalised): RESOLVED
- Exactly three header variants occur: `FULL_45` (484), `NO_TOR_44` (15), `NO_LANE_CHANGE_44` (14). Each trial's variant is recorded, and any other header raises `D003SchemaError`. Columns are matched by exact name; no silent remapping.

### B17. Control-channel authorship / automation actuation at TOR (new, R2A): STILL OPEN / DATASET-WIDE
- **Observation:** the accelerator, brake and steering channels show structured changes at or immediately after TOR (within 0.3 s), before a plausible human reaction. Counts per scenario cell (MANUAL_WINDOW_ELIGIBLE, n = 492; `results/R2A_event_vehicle_descriptives/channel_transition_pattern_by_cell.csv`):

  | Cell (density / n-back) | n | Accelerator channel drops to ~0 within 0.3 s | Brake channel > 5 within 0.3 s | Steering channel moving before TOR |
  |---|---|---|---|---|
  | 0 / 0 | 56 | 0 | 0 | 0 |
  | 0 / 1 | 57 | 57 | 1 | 57 |
  | 0 / 2 | 54 | 53 | 0 | 0 |
  | 10 / 0 | 53 | 53 | 53 | 53 |
  | 10 / 1 | 57 | 0 | 0 | 0 |
  | 10 / 2 | 57 | 57 | 0 | 0 |
  | 20 / 0 | 50 | 0 | 0 | 50 |
  | 20 / 1 | 51 | 51 | 24 | 50 |
  | 20 / 2 | 57 | 50 | 29 | 28 |

- **Consequences:**
  - The pattern is scenario-cell-specific. These channels therefore cannot currently be assumed to represent driver commands, in any cell.
  - Automation-transition behaviour around TOR appears to differ by experimental cell. The pattern is **consistent with** different automation-transition behaviours (e.g., accelerator actuation released at TOR in some cells and held in others). It is **not** shown to be a W0/W1 implementation, and the controller semantics are undocumented.
  - It explains why the earliest brake/steering channel activity falls within 0.3 s of TOR in all 53 trials of density 10 / 0-back and in 21 of 57 trials of density 20 / 2-back.
- **Interpretation rule (adopted R2A, all scenarios):** accelerator, brake and steering channels are not driver-only channels. They may contain automation actuation, simulator/controller activity, driver activity, or a mixture. Any inference of human first input from them is UNRESOLVED.
- **Withdrawn as human-response metrics** (historical versions labelled INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS):
  - `T_first` from these channels
  - first brake input and first steering input
  - brake-first vs steer-first
  - negative handover lag
  - brake-rise latency
  - maximum braking or steering attributed to the driver
- **Unaffected** (event or vehicle-state meaning):
  - `t_button`
  - TOR → validated lane change
  - minimum TTC in the approach domain
  - vehicle longitudinal acceleration and deceleration, as kinematics only
  - hazard-station crossing
- **Mechanism:** not confirmed. Questions A1–A6 in `research/D003_DATASET_OWNER_QUESTIONS.md`.

### R2A note on the R1 owner window
The R1 owner-metric window [TOR, lane change] follows the owners' published definition and is not bounded by handback. In `density_0_nback_2_id_29` the lane change (39.95 s) occurs after the first `Manual_Stop` (36.35 s), so that window includes post-handback data. R2A stores the owners' window (`OWNER_TOR_TO_LANE_CHANGE`, n = 478) and the handback-bounded manual-interval window (`MANUAL_TOR_TO_LANE_CHANGE`, n = 477) separately. R1 outputs are unchanged.

---

## 2. Prior analyses of D003 by the dataset owners

| Publication | What it reports on D003 | Verification level |
|---|---|---|
| K. Liang, S. C. Calvert, J. W. C. van Lint, "Multidimensional Assessment of Takeover Performance in Conditionally Automated Driving", arXiv 2507.22252 (2025) | 57 drivers, 9 scenarios, **466 takeovers**, after excluding 16 (control before TOR / forgot button) and 31 (incomplete questionnaires, hardware). Metrics: button time (`t_button`), road-reorientation time (`t_road`), takeover time (first conscious operational response), minimum TTC, maximum steering angle, maximum acceleration, maximum deceleration, all from TOR to lane change. Protocol: TOR 7 s before collision on a 100 km/h two-lane motorway; take over, change lanes, hand control back to automation. | Read (HTML version) |
| K. Liang, S. C. Calvert, S. Nordhoff, M. Li, J. van Lint, "Predicting drivers' takeover time for safe and comfortable vehicle control transitions: The role of spare capacity and driver characteristics", *Applied Ergonomics* 129:104603 (2025) | Takeover-time prediction from perceived spare capacity and 13 driver characteristics. | Abstract/search record only; use of D003 is very likely but not confirmed from full text |
| K. Liang, S. C. Calvert, J. W. C. van Lint, "Adaptive Time Budgets for Safe and Comfortable Vehicle Control Transition in Conditionally Automated Driving", arXiv 2511.05744 (2025) | Adaptive time-budget framework with predicted takeover time and a preferred buffer. | Abstract only; dataset not named in abstract |
| K. Liang, S. C. Calvert, J. W. C. van Lint, systematic review of takeover time, time budget and takeover outcomes, *Human Factors* (2026) | Review, not a D003 analysis. Already cited in the repository as L002. | Search record |

### Relation of current H1 analyses to prior work

| H1 quantity | Classification |
|---|---|
| `ΔT_manual_start` (`Manual_Start − TOR`) | **Replication** of `t_button` |
| `T_first_ctrl − TOR` | **Replication** of takeover time (definitions differ; subject to B6/B7) |
| Peak brake / steering in early window | **Replication**-adjacent (owners report max deceleration and max steering to lane change) |
| Minimum TTC, lane-change time | **Replication** |
| Brake-first vs steer-first ordering | **Reinterpretation** (subject to B6) |
| "Negative handover lag" (input before button) | **Reinterpretation** (subject to B6/B7) |
| `T_effective` (causally constrained response) | **Reinterpretation** |
| `T_stable` (nominal) | New but **invalid** (window includes automation) |
| Full-record brake extrema / reapplications | New but **invalid as computed** (window includes automation) |
| Acute-window (TOR + 8 s) steering reversals | **New**; window lies within manual control in 99% of trials but begins before the button press; pending B6/B7 |
| `T_pass` (hazard-station crossing) | **New**, geometric only |
| Collision proxy | New but **invalid** (B10) |
| Trial-order / exposure effects | **Not yet analysed**; identifiable (B11) |

The H1 documents did not cite the owners' analyses and used 498 TOR trials against the owners' 466 without reconciliation. Previously published takeover metrics must not be presented as novel.

## 3. R1 owner-metric check (validation, not novelty)

Implemented in `src/experiments/r1_ingestion_validation.py`; output `results/R1_ingestion_validation/owner_metric_replication.csv` and `summary.md`.

| Owner metric | Owner window | R1 definition | Definition status |
|---|---|---|---|
| `t_button` | TOR → mode-switch press | `Manual_Start − TOR` (resolved TOR only) | matches the owners' description |
| Minimum TTC | TOR → lane change | min `Time_TTC` over [TOR, validated lane change], formula domain only (B13) | owners' handling of stopped vehicles not stated |
| Maximum steering wheel angle | TOR → lane change | max abs(angle), and max abs(angle − pre-TOR baseline) | owners' variant not stated |
| Maximum acceleration | TOR → lane change | max `accel.001` | axis and sign convention not stated by owners |
| Maximum deceleration | TOR → lane change | −min `accel.001` | axis and sign convention not stated by owners |

- **Counts:** the metrics are computed for 478 trials. The other 35 have no owner window: 21 have no resolved TOR anchor (15 missing, 6 multi-unresolved) and 14 have no lane-change channel. This compares with the owners' 466 analysed takeovers; the sets are not reconciled (B12).
- `t_button`, where computed: median 1.65 s (IQR 1.25–2.00 s). This is a validation descriptive, not a finding.
- No numerical comparison with the owners was possible: their reported values were not available in the sources read.
