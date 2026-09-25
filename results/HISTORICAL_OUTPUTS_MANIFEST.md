# Historical D003 outputs manifest

These pre-audit outputs are kept for audit history only. **None is a current finding.** They are reproducible byte-for-byte with the legacy pipeline (`run_full_h1_analysis`, `run_sensitivity_audit`), which is HISTORICAL ONLY and emits a `DeprecationWarning`. Machine-readable version: `results/historical_outputs_manifest.json` (checked by `tests/test_r2a.py`).

| File | Status | Reason | sha256 |
|---|---|---|---|
| `results/H1/event_times.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | T_first/T_effective from control channels (B17); T_stable columns WITHDRAWN | `5d7e74246033fb00…` |
| `results/H1/action_sequence.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | brake-first / steer-first ordering from control channels (B17) | `b4abdcc2459efa35…` |
| `results/H1/initial_control_metrics.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | brake/steering rise and peaks attributed to the driver (B17) | `d5dd9d3127a1cd2e…` |
| `results/H1/correction_metrics.csv` | WITHDRAWN | full-record windows past handback; channel authorship (B17) | `ba678a79acc9d61a…` |
| `results/H1/stabilization_candidates.csv` | WITHDRAWN | T_stable: ~81% of values after handback | `99507ce6361f519f…` |
| `results/H1/participant_summary.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | aggregates of the above | `bd01efe2800d5371…` |
| `results/H1/scenario_summary.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | aggregates of the above; cells aliased (B11) | `ec22cef533bbdf00…` |
| `results/H1_sensitivity/tfirst_threshold_sensitivity.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | T_first from control channels (B17) | `da5cea37bb286617…` |
| `results/H1_sensitivity/teffective_definition_sensitivity.csv` | INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS | anchored to control-channel onsets (B17) | `75aebf1171edd585…` |
| `results/H1_sensitivity/tstable_definition_sensitivity.csv` | WITHDRAWN | T_stable window past handback | `908b6e209faeefda…` |
| `results/H1_sensitivity/correction_metric_sensitivity.csv` | WITHDRAWN | full-record windows; channel authorship (B17) | `e5b18408313b3e74…` |
| `results/H1_sensitivity/scenario_repeated_measures.csv` | WITHDRAWN | causal workload/density contrasts; cells aliased incl. automation-transition behaviour (B11) | `a0505542c84fa3e2…` |
| `research/data_matrix/d003_trial_qa.csv` | HISTORICAL ONLY | collision_outcome / COLLISION_FAILURE labels WITHDRAWN (B10); legacy QA | `0cd8af19c6349224…` |

Full hashes are in the JSON file. Current D003 outputs: `results/R1_ingestion_validation/` and `results/R2A_event_vehicle_descriptives/`.
