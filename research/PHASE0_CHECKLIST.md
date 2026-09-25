# Phase 0 Checklist

## Deliverables started
- [x] Project charter v1.0
- [x] Initial literature matrix
- [x] Initial dataset inventory
- [x] Initial variable dictionary
- [x] Initial identifiability matrix
- [x] Experiment A pre-registration draft

## Phase 0.1 — completed (see research/PHASE0_1_REPORT.md)
- [x] Expand literature search systematically by mechanism (L007-L014 added; see literature_matrix.csv):
  - [x] TOR/time-budget design
  - [x] critical takeover recovery quality
  - [x] regenerative / one-pedal / blended braking behaviour
  - [x] driver vehicle-control adaptation / internal models
  - [x] vehicle-response dynamics in human-in-the-loop takeover
  - [x] acceleration authority / risk-state escalation
- [x] Check licenses and actual downloadable fields for every candidate dataset (verified by direct fetch; see dataset_inventory.csv — one dataset, D004, remains ACCESS_UNCERTAIN on exact license)
- [x] Inspect ADAS-TO field schema and vehicle metadata in detail (brake/accel confirmed BINARY, not continuous — see dataset_inventory.csv)
- [~] Inspect OpenLKA EV and Acceleration dataset sample files — repo-level fields confirmed via fetch; file-level (continuous-vs-binary, per-trace driver ID) inspection still outstanding, see PHASE0_1_REPORT.md Recommended next action #2
- [ ] Define quantitative `stopping_margin` (still open — no numeric operational definition frozen)
- [~] Freeze a provisional definition of `t_stabilise` — empirical anchor found (L009: ~8-10s driving-metric stabilisation); operational threshold definition itself still needs to be written
- [ ] Freeze a provisional definition of `N_correction` (still open — L008 identified as candidate source for a threshold convention)
- [~] Build an empirical parameter table for candidate P1–P4 profiles — see parameter_provenance/parameter_evidence_table.csv; a_max and TOR/reaction-time ranges are reasonably anchored, build-up time / emergency jerk / regen magnitude remain COUNTERFACTUAL/unverified
- [x] Run a novelty/gap audit before writing a novelty claim — see literature_matrix/gap_audit.md; verdict MODERATE GAP
- [ ] Only then implement the minimal longitudinal simulator (not started — blocked on items above per PHASE0_1_REPORT.md Decision H)
