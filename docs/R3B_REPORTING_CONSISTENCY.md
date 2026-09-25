# R3B reporting consistency contract

This layer reads committed outputs only. It does not import the experiment, calculate
bounds, classify margins, change assumptions, or establish a scientific gate outcome.

From the repository root:

```
python -m src.provenance.r3b_reporting
python -m src.provenance.r3b_reporting --write
pytest tests/test_r3b_reporting.py
```

The default command checks; `--write` updates only marked Markdown blocks. Missing,
duplicate or reversed markers fail closed. Review generated documentation changes
alongside any independently approved result updates. Result CSV/JSON files are never
written by this command. Exact block comparisons detect missing cases, wrong labels,
counts and transition lists; this is not a general natural-language fact checker.

## Sources and ownership

All sources are under `results/R3B_braking_bounds/`:

- `results.csv`: canonical scenario classifications and stored supplementary
  `classification_if_t1_high_4s`. Counts, full TTC/friction/branch matrix, t1 transition
  list and policy classification transitions derive exclusively from these labels.
  No classification formula is duplicated. Labels retain the existing hyphen spelling.
- `scenario_table.csv`: coverage check against canonical scenario IDs.
- `summary.json`: total and classification counts checked against `results.csv`.
- `policy_comparison.csv`: complete branch coverage and TTC change lists checked
  against matched reference labels in `results.csv`; stored numerical deltas are
  presented without recomputing scientific quantities.
- `t_required_bounds.csv`: stored min/mid/max values presented in the bounds table.
- `sensitivity.csv`: descriptive min/max of stored elasticities and OAT swing shares,
  grouped by parameter and friction. No derivatives or scenario evaluations run.

## Duplication inventory and remaining manual material

| Location | Risk found | Treatment |
|---|---|---|
| R3B report §6 bounds | Rounded branch/friction values copied by hand | Generated explicit stored values |
| R3B report §6 counts and TTC patterns | Exceptions omitted by compressed prose (historical defect A) | Generated complete matrix and counts |
| R3B report §6 D003-like summary | Subset classifications and margins repeated in prose | Removed numeric repetition; cases remain in complete matrix and CSV |
| R3B report §6 supplementary t1 | Count/list contradiction (historical defect B) | Generated count, TTC breakdown and every changed scenario |
| R3B report §7 | Rounded elasticity/share and friction/speed comparisons | Generated stored sensitivity ranges; bounds table contains scenario comparisons |
| R3B report §8 | Policy effect ranges and speed/TTC lists manually copied | Generated stored deltas and all label transitions relative to the existing P0 reference |
| PROJECT_STATUS R3B paragraph | Repeated counts and rounded cross-check | Counts generated; numeric cross-check duplication removed |
| R3B report §5 | Rounded cross-check maximum, corner/case counts and method claims | Still manually authored; underlying cross-check CSV covered by existing scientific tests |
| R3B report §1, §12 and D022/D023 | Legacy test count, historical corrections, semantic/method claims and the missed-case example | Historical/manual record retained; not parsed as current result summaries |
| README, architecture, R3B-0/design/specification documents | Qualitative status, scope and model descriptions | Manual; not computed result summaries |

Interpretations, provenance, definitions, assumptions, validity limits and readiness
remain manually authored. Adding new numeric prose outside the marked blocks requires
review and is not automatically detected. The historical recommendation in D023 is
preserved as a decision-log record; this document records its implementation.

## Test scope

Mutation tests cover a missing TTC 3 / 60 km/h / μ 0.5 PARAMETER-SENSITIVE row,
wrong classification, wrong scenario count, omitted policy/t1 transitions, stale
bounds/sensitivity, JSON count drift, CSV policy-list drift, malformed markers,
duplicate IDs, order independence, deterministic generation and read-only results.

The existing `tests/test_r3b_bounds.py::test_deterministic_reproduction` invokes the
entire final R3B study. Under the engineering-only instruction prohibiting that study,
run the full remaining suite with that single test deselected; do not claim it passed.
