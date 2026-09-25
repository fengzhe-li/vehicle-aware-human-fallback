# Claim Ladder

**Status:** Design document. Fixes, once, what kind of claim each planned deliverable can support, so future write-ups do not drift upward in confidence without new evidence to justify it.

## The four types

**TYPE 1 — Analytical.** A statement provable from the model's own equations, true by construction, requiring no simulation and no data.
> Example: "A delayed response necessarily increases stopping distance under the specified model" — `analytical_sanity_check.md`'s `d(D_stop)/dt3 > 0` result. "The withdrawal-policy × vehicle-response interaction does not reduce to an additive delay term" — `docs/CAUSAL_MODEL.md`'s nonzero cross-partial result.

**TYPE 2 — Counterfactual simulation.** A statement about how the *model* behaves across a parameter sweep, using COUNTERFACTUAL (unanchored, labeled-as-such) parameter values, run through the simulator rather than closed-form algebra because a closed form does not exist (e.g., anything involving `v_rolloff`).
> Example: "Within a defined COUNTERFACTUAL parameter sweep, response architecture shifts `T_TOR_critical` by X seconds under withdrawal policy W1 but not W0."

**TYPE 3 — Empirically constrained simulation.** The same simulation, but with parameters restricted to their literature/data-anchored ranges (`CORE_EMPIRICAL` or `EMPIRICAL_RANGE` per `phase1A_parameter_table.csv`'s Task 7 policy below), reporting whether an effect survives inside those bounds.
> Example: "Within literature-constrained `t_delay` and `a_coast` ranges, a robust (magnitude exceeding both Gate-A comparators) shift in `T_TOR_critical` persists across the marginal scenario band."

**TYPE 4 — Empirical real-world claim.** A statement about actual production vehicles, actual drivers, or actual crash outcomes.
> Example: "Production vehicle architecture A produces worse real-world takeover safety than architecture B."

## What this project can support

| type | can this project support it? | basis |
|---|---|---|
| TYPE 1 | **YES, already delivered.** | `analytical_sanity_check.md`, `docs/CAUSAL_MODEL.md`. No further evidence-gathering required — these are proofs, not findings pending confirmation. |
| TYPE 2 | **YES, once the minimal simulator exists** (`docs/MINIMAL_SIMULATOR_SPEC.md`). | Requires only that the simulator is validated against A0 (Type 1) first — no additional data collection needed, since COUNTERFACTUAL parameters are explicitly not claiming real-world grounding. |
| TYPE 3 | **CONDITIONAL — depends entirely on which parameters carry `CORE_EMPIRICAL`/`EMPIRICAL_RANGE` status** (Task 7 below). Currently: `t_delay` (friction baseline) and `a_max` have real, if imperfect, anchors; `t_buildup`, `v_rolloff`, and `a_coast`'s magnitude do not (`phase1A_identifiability_final.csv`). A TYPE 3 claim restricted to the anchored subset of parameters is supportable now; a TYPE 3 claim that requires `t_buildup` or `v_rolloff` to be literature-constrained is **not** supportable until Phase 0.3's Recommended Next Action (re-reading arXiv:2112.09074 properly, executing `response_episode_definition.md` at scale) succeeds. |
| TYPE 4 | **NOT SUPPORTABLE, and must not be implied.** | This project has never obtained direct, production-vehicle, real-world takeover-outcome data (no dataset in `dataset_inventory.csv` is a controlled TOR experiment varying real vehicle-response architecture), and the charter's own claim boundaries (`docs/DECISIONS.md` D008, `project_charter.md` Section 8) already forbid product-specific claims without product-specific evidence. Nothing in Phase 0.1-0.4 changes this. |

## Enforcement rule

**Every future report, figure, or abstract sentence produced by this project must be labeled with its claim type**, either explicitly (a "Type N" tag) or unambiguously by its phrasing (COUNTERFACTUAL sweep vs literature-constrained vs a bare model-derived inequality). A sentence that reads like TYPE 4 but is backed only by TYPE 2/3 evidence is a claim-boundary violation regardless of the author's intent, and should be caught the same way `experiment_A_review.md` and `analytical_sanity_check.md` were used in Phase 0.1/0.3 — by checking the sentence against this ladder before it ships, not after.

## Relationship to existing claim-boundary documents

This does not replace `project_charter.md` Section 8 (what the project must not aim to prove) or `experiments/A_brake_response/experiment_A_spec.md`'s "Claim boundary" section — it generalizes them into a reusable four-level scale that applies to A0, A1, and every later branch (B, C, D, E in `docs/RESEARCH_ARCHITECTURE_V1.md`), not just the original Experiment A.
