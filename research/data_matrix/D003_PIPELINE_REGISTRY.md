# D003 pipeline registry (Phase R2A)

## Canonical ingestion path

**`src/data/d003_ingest.py`** (strict ingestion, Phase R1) is the single canonical entry point for D003. Every active analysis must use it, together with `src/data/d003_populations.py` (populations and enforced observation windows). `tests/test_r2a.py` checks that active scripts do not import the legacy loader.

**Interpretation rule (blocker B17):** the accelerator, brake and steering channels are not driver-only channels. No active code may infer human input, driver action or driver command from them.

## Components

| Component | Classification | Notes |
|---|---|---|
| `src/data/d003_ingest.py` | ACTIVE (canonical) | Strict ingestion; R1 |
| `src/data/d003_populations.py` | ACTIVE | Populations and windows; R2A |
| `src/metrics/control_activity.py` | ACTIVE (neutral) | Channel-activity detectors; authorship-neutral API. Hysteresis-reversal algorithm MIGRATED from `h1_sensitivity_analysis.count_steering_reversals` |
| `src/experiments/r1_ingestion_validation.py` | ACTIVE (R1 validation) | Uses canonical ingestion. Its owner window is the owners' published, non-handback-bounded window; in `density_0_nback_2_id_29` that window includes post-handback data. R2A stores this window and the handback-bounded one separately |
| `src/experiments/r2a_event_vehicle_descriptives.py` | ACTIVE | Event timing, vehicle-state quantities and neutral channel observations; R2A |
| `src/data/d003_loader.py` → `D003Dataset` | DEPRECATED; STILL REQUIRED (historical reproduction) | Emits `DeprecationWarning`. All-NaN `lane_gap`, silent footer drop, pandas coercion |
| `src/data/d003_loader.py` → `parse_trial_filename`, `TrialMeta`, `RAW_TO_CANONICAL_COLUMNS` | STILL REQUIRED | Shared filename parsing and legacy canonical names, reused by the canonical ingestion |
| `src/experiments/h1_recovery_analysis.py` | HISTORICAL ONLY | Emits `DeprecationWarning`. Silently takes the first TOR, uses full-record windows, hard-codes lane 3, contains the collision proxy, and treats control channels as human input. Reproduces the historical outputs byte-for-byte |
| `src/experiments/h1_sensitivity_analysis.py` | HISTORICAL ONLY | Same as above (`T_stable`, correction counts, factorial contrasts) |
| `research/data_matrix/d003_trial_qa.csv`, `results/H1/`, `results/H1_sensitivity/` | HISTORICAL ONLY | Listed with status and hash in `results/HISTORICAL_OUTPUTS_MANIFEST.md` |
| `tests/test_h1_analysis.py`, `tests/test_h1_sensitivity_and_audit.py` (legacy-function tests) | STILL REQUIRED (historical) | Test the historical functions. The collision-proxy test was replaced in R2A |
| `tests/test_d003_loader.py` | STILL REQUIRED | Tests the shared filename/mapping utilities |
| Unmerged D003 ingestion-QA branch (`9bef347`) | HISTORICAL ONLY (unmerged) | Superseded by R1 strict ingestion. Would wrongly fail the 42 export-footer trials |

## Migration notes

The historical H1 quantities were **not** migrated. Migrating them would change the scientific quantity itself: first-input times, brake/steer ordering, `T_stable` and correction counts all depend on control-channel authorship or on windows that extend past handback. R2A reconstructs only quantities whose meaning does not depend on channel authorship (see `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md` §9).
