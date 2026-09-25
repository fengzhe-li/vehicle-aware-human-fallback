# Research Decisions Log

## D001 — Problem origin
The project starts from automated-driving human fallback, not from an EV-vs-ICE comparison.

## D002 — Scientific object
Use **vehicle-response profile / architecture** as the main explanatory object. ICE/EV labels are contextual categories, not sufficient causal variables.

## D003 — First-phase human model
Fix the driver model and set driver–vehicle mismatch to zero in the first mechanism experiment.

## D004 — Driver familiarity
Retain ICE-like vs EV-like learned-control prior as a later interaction variable, not a Phase-1 confounder.

## D005 — High-performance acceleration
Do not test acceleration capability in a fixed-speed braking experiment. Use a separate risk-state-escalation scenario in which identical-duration acceleration commands produce different hazard-entry states.

## D006 — Primary simulator
Begin with a transparent longitudinal simulator. CARLA is conditional on surviving mechanism gates.

## D007 — Evidence discipline
All parameters are tagged OBSERVED / LITERATURE_CONSTRAINED / DERIVED / COUNTERFACTUAL.

## D008 — Claim boundary
No product-specific safety claims without product-specific observed parameters.

## D009 — Pre-audit snapshot (2026-09-22)
The exact pre-audit state is preserved at tag `pre-audit-2026-09-22` and branch `archive/pre-audit-2026-09-22` (commit `7f918fcc269ce734f6434f069a9c2c35b0269aac`, snapshot of `main@1ad1951` plus the then-untracked handoff dossier). Neither reference may be deleted, rewritten, squashed, rebased or force-moved.

## D010 — Research architecture V2
The project is structured as one mother question, four causal layers (A vehicle response, B human control reacquisition, C automation transition, D scenario/hazard state), a B↔A internal-model interface M, a closed loop, and a gated synthesis (`docs/RESEARCH_ARCHITECTURE_V2.md`). This replaces the H0 RQ1–RQ4 structure. The split of the charter's handover layer into B and C, and the promotion of hazard state to a layer, are restructurings, not restorations.

## D011 — Observation layer is mandatory
Empirical conclusions cannot pass into the causal layers until event semantics, channel semantics, observation and authority windows, censoring/competing events, outcome labels and plausibility filters are validated (`docs/OBSERVATION_LAYER.md`).

## D012 — Status labels reset
All status, readiness and novelty labels are governed by `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. `P1-B: READY`, `H0-B`, "paper-ready", "first exact closed form", "RQ1 partially answered", "RQ2 answered/complete", and `T_stable` ≈ 22–23 s are withdrawn. The current stage is EXPLORATORY.

## D013 — Historical accuracy
The original project was one mother question plus mechanism layers. The four peer RQs and the quoted RQ4 "Original Charter Wording" were constructed in H0 (`c09f682`). W0/W1/W2 terminology first appears in Phase 0.4 (`bc21fbc`). Documents must not present later constructions as charter content.

## D014 — D003 findings are provisional
D003-derived quantities are provisional until the blockers in `research/data_matrix/D003_KNOWN_BLOCKERS.md` are resolved. Factorial cell differences are descriptive and condition-associated only. The dataset owners' prior analyses must be cited, and replication must be distinguished from reinterpretation and new analysis.

## D015 — Phase ordering after R0
Phase R1 (ingestion and observation-semantics repair) is proposed but not started. Until review: no pipeline repair, no model fitting, no new experiments, no controller-model competition, no Monte Carlo envelope, no synthesis, no CARLA, no lateral-dynamics model, no human-subject work, no EV vs ICE claims, no novelty-led manuscript drafting, no causal workload/density claims.

## D016 — Phase R1 ingestion rules (2026-09-22)
New D003 work uses `src/data/d003_ingest.py`. Its rules:
- **TOR selection:** a TOR is selected only as the unique value at TTC 7.0 ± 0.25 s, following the owners' documented protocol. Otherwise the TOR anchor is unresolved and TOR-anchored windows are undefined.
- **Handback:** the first `Manual_Stop` after `Manual_Start` ends the first manual episode.
- **Minimum TTC:** uses only samples in the documented formula's domain (distance > 0, speed > 0, TTC > 0).
- **Lane change:** lane-change-anchored windows require a lane change validated against `lane_id`.
- **Trailing row:** the export-channel footer is parsed, cross-checked and excluded from telemetry.
- **Unresolved meanings:** brake channel, `laneGap` component 1, adjacent-lane zeros and `Manual_Start` authority stay unresolved and are labelled as such.
- **Legacy code:** the legacy loader and pre-audit H1 scripts are not used for new results.

## D017 — Phase R2A: control-channel authorship rule and canonical pipeline (2026-09-22)
- D003 accelerator, brake and steering channels are not driver-only channels (blocker B17, all scenarios). No human first-input, driver-action or driver-command inference from them until authoritative semantics exist; historical versions are labelled INVALID / UNRESOLVED HUMAN-AUTHORSHIP SEMANTICS.
- `src/data/d003_ingest.py` is the single canonical D003 ingestion path. The legacy loader and H1 scripts are DEPRECATED / HISTORICAL ONLY and emit `DeprecationWarning`.
- The collision proxy is retired from active outputs; no replacement safety label until hazard geometry is identified.
- Populations are explicit and metric-specific; there is no universal clean denominator. The owners' 466-trial set is NOT RECONSTRUCTED.
- The owners' published window [TOR, lane change] and the handback-bounded manual-interval window are stored separately and never mixed.
- Workload/density cell comparisons are descriptive only (B11 extended to automation-transition behaviour).
- Repeated-exposure analysis is deferred until its dependent variables are semantically valid.

## D018 — Phase R2B: repeated-exposure analysis rules (2026-09-22)
- Exposure = chronological trial position (1–9) from recording start times. Models are fitted only if exposure is separable from scenario cell (it is: Cramér's V 0.05, VIF 1.008).
- Primary outcomes are limited to B17-safe event timing: `t_button` and TOR → validated lane change. Secondary outcomes are descriptive vehicle-state quantities.
- Model: participant fixed intercepts, scenario-cell indicators, linear exposure, participant-clustered SE. It is used instead of a mixed model because statsmodels is not a dependency.
- Results are reported as associations with repeated exposure, never as causal learning or vehicle-specific familiarity.
- The multi-TOR sensitivity analysis (excluding all multi-TOR trials) is pre-defined as material only if the slope sign or its CI-based conclusion changes.

## D019 — Phase R2C-lite: participant associations and carry-over rules (2026-09-23)
- Participant-level analysis uses four pre-specified self-report covariates (years of driving, km in the past 12 months, driving days per week, ADAS-use frequency) against participant median `t_button` and the R2B per-participant exposure slope; Holm adjustment within each family of 8 tests. No other questionnaire variable is tested.
- Participant-characteristic results are a secondary re-analysis: the dataset owners have already analysed driver characteristics against takeover timing.
- Carry-over is limited to the immediately preceding cell's main effect (compact: previous density + previous n-back; full: previous cell). Previous × current interactions are not identifiable (2–8 trials per pair) and are not fitted.
- Reference and carry-over models are fitted on the same exposure 2–9 trials. "Carry-over adjustment changes the exposure association" means a slope change > 25% or a changed CI-based conclusion versus that same-trial reference. This replaced an initial rule that confounded carry-over with the exposure 2–9 restriction; both are reported.
- A REML random-intercept model is fitted as a cross-check of the participant fixed-intercept model.

## D020 — Phase R3A: evidence baseline rules for layers A, C and D (2026-09-23)
- Every parameter proposed for synthesis must appear in `research/PARAMETER_PROVENANCE_REGISTRY.csv` with sources in `research/R3A_SOURCE_REGISTER.csv`; `src/provenance/registry.py` enforces source resolution, value ordering, code references, and that no NOT IDENTIFIABLE or LOW-confidence parameter is marked synthesis-ready.
- `a_pre` is treated as a transition-policy-selected quantity (A↔C interaction), not an EV/ICE property; `t3` as a human × vehicle quantity (A↔B).
- The braking closed form is classified as the capability-bound (`u = 1`) braking slice: a necessary, not sufficient, condition for braking-only recovery.
- TOR, driver acknowledgement (Manual_Start), authority transfer and effective input are four distinct events; none is equated with another. Immediate withdrawal (W1) stays a counterfactual bound.
- `T_available` is defined per manoeuvre and policy; TTC at TOR is only the observable proxy. Recoverability is manoeuvre-specific.
- Regulatory values obtained only through secondary quotation (UN R157, ISO 15622) are marked as such and graded no higher than MEDIUM until the primary text is read.
- `research/identifiability/identifiability_matrix_R3A.csv` supersedes the Phase-0 identifiability matrix for the quantities it lists; the Phase-0 file is kept as history.
- The questionnaire-ID join (R2C) is classified STRONGLY SUPPORTED BUT NOT EXPLICIT; R2C is not rerun.

## D021 — Phase R3B-0: source and specification hardening (2026-09-23)
- UN R157 claims are cited only from the official texts (S02: Rev.1, 01 series; S31: 00 series, OJ L 82) with clause numbers. Wikipedia and certification summaries are navigation aids only and may not be cited (enforced by the validator).
- Corrected wording: the MRM starts *earliest* 10 s after the transition demand without deactivation (§5.4.4.1); there is no fixed "transition period". 4.0 m/s² is an *aim* for the MRM deceleration demand (Rev.1 §5.5.2), not a hard limit.
- Standards are classified FULL TEXT VERIFIED / ABSTRACT OR PUBLIC SUMMARY ONLY / SECONDARY ONLY / NOT VERIFIED. A synthesis-ready parameter needs at least one full-text or dataset-verified source.
- Events are defined in `research/SYSTEM_EVENT_REGISTRY.csv`. Authority transfer is latent and may not use TOR or Manual_Start as a proxy; first human input may not use channel activity as a proxy.
- `T_available^m` = constant-velocity reference time from TOR to the manoeuvre boundary; all policy, human and vehicle dynamics enter `T_required^m`. Combined braking + steering is undefined.
- The three code simplifications (`u_target` not wired, friction unused, authority not separated from TOR / effective input) are documented with a correction design (order B, C, A, each gated by a golden test). None is implemented.
- The measurement/assurance framing is classified INCREMENTAL relative to confidence-argument, eliminative-argumentation, Assurance 2.0, model-credibility and AD safety-case frameworks. No novelty is claimed.
- An interval-only braking evaluation is conditionally defensible as a labelled capability bound, once policy branches, the assumption intervals for `t1` and `t3`, `a_max ≤ μg` and the scenario set are fixed.

## D022 — Phase R3B: interval-bounded braking slice (2026-09-23)
- Model corrections implemented before any result: braking deceleration `min(u·a_max·rolloff, μg)`; explicit `HandoverTimeline` (TOR, authority, first input, effective control); `PreControlProfile` with the policy acting before authority transfer and vehicle-only response after it; the driver command wired into the vehicle model. The legacy W0/W1 behaviour is reproduced bit-for-bit.
- The friction ordering follows the R3B specification, `min(u·a_max, μg)`, and deviates from the R3B-0 design note (`u·min(a_max, μg)`). The two are identical for u = 1.
- An external uncommitted draft found in the working tree (inverted policy/authority semantics; friction ordering as in the R3B-0 note) was preserved in git stash and not used.
- Policy branches P0 (hold), P1 (passive drag) and P2 (supported deceleration) are counterfactual. Authority is either at effective control or uncertain within [TOR, effective control]. P0/P2 with authority at TOR equal P1.
- Inputs are classed as source-supported (v0, TTC, μ relation, drag, t2, a_max) or explicit assumption intervals (t1 1.15–3.0 s, t3 0.3–1.2 s, authority fraction, a_sup 1–3 m/s², 2.0 m standstill margin). Blocked inputs are asserted absent.
- Bounds are exact over the parameter box (corner enumeration verified on an interior grid); no distributions. The labels ROBUSTLY SATISFIED / PARAMETER-SENSITIVE / ROBUSTLY UNSATISFIED apply only to the braking-only model and are never shortened to safe / unsafe.
- Physical sensitivity (elasticities, scenario axes) is reported separately from epistemic width (one-at-a-time swing). The dominance of t1 in the width is attributed to its assumption interval.

## D023 — R3B reconciliation of draft defects (2026-09-23)
- A (missed TTC 3 s / P2 / 60 km/h / μ 0.5 PARAMETER-SENSITIVE) and B (contradictory t1 = 4 s sentence) were report-wording defects in an uncommitted draft. They never entered a commit; results and code were correct. They were fixed before `fe34ffc`.
- C (friction ordering of the external draft called a defect) is retracted: the draft followed the R3B-0 design note. HEAD deliberately implements `min(u·a_max, μg)` per the R3B specification (identical for u = 1). This supersedes the corresponding wording in the `028786b` commit message; history is not rewritten.
- D (policy acting only after authority transfer) was a genuine defect of the external draft (`stash@{0}`) only. HEAD applies the policy before authority transfer; this is pinned by tests.
- Stale current-state descriptions of the pre-R3B semantics were corrected in the handover docstring, the event/state specification, the design note header, the R3B-0 report and the README layer table.
- Recommendation: narrative classification summaries should be generated from the machine-readable results, with a consistency test, instead of being written by hand.

## D024 — R3B gate engineering (2026-09-24)
- **Margin units:** `classify` receives time margins `T_available − T_required` in seconds; distance margins are derived outputs only. `EPSILON_S = 0.01` s, `MARGIN_UNITS = "s"`; no distance conversion is needed. A test guards against unit confusion.
- **Classification:** ROBUSTLY SATISFIED iff worst > +ε; ROBUSTLY UNSATISFIED iff best < −ε; otherwise PARAMETER-SENSITIVE. Separate `boundary_flag` if either bound is within ±ε. No committed label changes (closest |margin| 0.047 s).
- **Monotonicity guard (fail-closed):** exact analytic partial derivatives of the closed form, covering all regimes (standstill in either pre-control segment or in the ramp, friction saturation), verified against the oracle (≤ 1e-12) and finite differences. They are evaluated on a dense grid (n points per dimension, n^d ≤ 1e6), and every axis-parallel line must keep one derivative sign (|dT/dp| ≤ 1e-9 is sign-neutral). This detects interior reversals, not only endpoint differences. On failure, `bound()` raises `MonotonicityGuardError` stating that a true constrained-bound search is required. Resolution limit: reversals confined between adjacent nodes of every line are not resolved.
- **t1 = 4 s supplement:** an independent interior-grid cross-check is now enforced in `run()` and tested for all 30 cases. The guard fails closed for 60 km/h, μ 0.5, P2 (both branches): the gate-review statement that the supplement is monotone is withdrawn (erratum in `docs/R3B_GATE_REVIEW.md`). The committed values were confirmed by a global search. The next rerun needs a scientific decision on the supplement.
- **Legacy enum:** `WithdrawalPolicy` is pinned to `{W0, W1}` by test; no refactor needed.
- **R3A test:** the source-token assertion is replaced by behavioural and provenance tests (legacy reproduction at u = 1, deceleration scaling for u < 1, recorded command, `u_eff` blocked).
- **Study rerun test:** `test_deterministic_reproduction` carries the `r3b_study` marker and is deselected by default (`pytest.ini`) until an authorised rerun.
- **Commit hygiene:** commit `47347a0` (gate review) was staged with `git add -A` and unintentionally included the separately developed R3B reporting layer (`src/provenance/r3b_reporting.py`, `tests/test_r3b_reporting.py`, `docs/R3B_REPORTING_CONSISTENCY.md`) and its regenerated-block rewrite of `docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md` §6–8. Those files were authored in a separate task, not in the gate review. History is not rewritten. Explicit path staging is used from now on.

## D025 — R3B t1 = 4 s supplement: stationary-point t1 bound (Option A, 2026-09-24)
- Main-domain and supplement ranges are unchanged. The main path is unchanged: guard, then the corner method (`monotone_endpoint_bound`).
- **Supplement:** `bound_supplement` runs the same guard scan.
  - If it passes, the corner method is used.
  - If **only t1** reverses sign, every other bounded parameter is monotone along every guarded line, so the extremes lie at the corners of the other parameters. Along each such line, T_required is evaluated at both t1 endpoints and at every interior root of the exact `dT_required/dt1` (sign-change bracketing on a 2001-point scan, brentq with xtol 1e-12; scan nodes with |dT/dt1| ≤ 1e-9 are also candidates). The result is `stationary_point_t1_bound`.
  - **Fails closed if:** any other coordinate is non-monotone; a 201-point T scan of a line exceeds its candidate extremes; the root solver fails; or the 4-point interior grid falls outside the bounds.
- **Results:** 28 supplement cases use `monotone_endpoint_bound`; 60 km/h, μ 0.5, P2 (both branches) use `stationary_point_t1_bound` and reproduce the global-search values exactly. No saved result changes.
- `run()` evaluates the supplement after, and independently of, the main domain (`evaluate_supplement`, `attach_supplement`). A supplement case that cannot be bounded is recorded as NOT BOUNDED and cannot block or modify main-domain rows. The supplement classification now uses the supplement's own minimum and maximum. The bounding method is recorded per case in `t_required_bounds.csv`, `results.csv` and `summary.json` (effective at the next authorised rerun; saved outputs unchanged).

## D026 — R3B final freeze and authorised rerun (2026-09-24)
- The configuration was frozen unchanged from the gate-reviewed state (drift check: none). The parameter classes are recorded in report §13.1. The t1 = 4 s supplement is sensitivity-only.
- The first rerun attempt exposed a CSV-writer defect (branch-dependent guard columns). Partial outputs were restored, the defect fixed and tested (`a4f2cc4`), and the canonical rerun done on a clean tree.
- **Outcome:** no numerical change. 58 ROBUSTLY SATISFIED, 47 PARAMETER-SENSITIVE, 45 ROBUSTLY UNSATISFIED; 0 boundary flags. Supplement: 28 endpoint, 2 stationary-point t1 (60 km/h, μ 0.5, P2), values unchanged.
- **Verification:** reproduction test (`-m r3b_study`), full default suite and reporting consistency all pass.
- R3B is complete as a braking-only, necessary-condition slice with explicit assumptions. It is not a system-level recoverability result. Downstream synthesis is not started.

## D027 — Phase R4: synthesis-readiness audit (2026-09-24)
- The cross-layer alignment is limited to TOR (clock origin) and TTC at TOR = T_available^brake. Authority transfer, first input, effective braking, lane crossing and handback stay distinct. `t_button` is not t1; lane crossing is not effective longitudinal control; handback is not recovery completion.
- Link classes (`research/R4_CROSS_LAYER_LINKS.csv`): 4 identified, 2 partially identified, 2 assumption-dependent, 8 not identifiable.
- Synthesis levels: S1 (braking-only, deterministic) is defensible only as R3B already is. Composing it with R2 adds no identified input. S2 (with steering) and S3 (probabilistic) are blocked.
- Blockers by scientific importance: B17, B7, hazard geometry / gaps / adjacent-lane semantics, completion definition, D003 vehicle / automation model, population human timing, EV/ICE familiarity (permanently unidentifiable in D003), owners' 466 set.
- Recommended next step: stop and wait for dataset-owner clarification. Sending the questions is the user's decision. No synthesis started.

## D028 — R4 internal source-of-truth audit (2026-09-24)
- There is no external owner to contact (user). The internal search of the repository, all branches, the worktrees, the local disk and the full D003 archive found **no D003-generating artifacts** (no simulator, export, automation or vehicle configuration; the archive notebook is empty). The project's own records identify D003 as a published 4TU archive.
- From the archive's documentation and the owners' paper: Manual_Start is a button-triggered switch to manual mode that enables manual inputs (documented design intent; behaviour unverified); Manual_Stop is the switch back to automated mode; the lane change is to the left lane; the hazard is a construction zone; target-lane gap distances are logged. `VehicleUpdate-state` is constant (2.0) in all 513 trials and is not a mode flag. `steeringTorq` is undocumented.
- B7 is reclassified as documented design intent. B17 is split: pre-switch channels are not driver-effective by design; post-switch channels are driver-generated by design, pending verification. Vehicle and automation models are not identifiable from project artifacts.
- The recommendation changes to an internal verification of the documented design intent. No synthesis is started.

## D029 — R4V: D003 control-channel authorship validation (2026-09-24)
- **Tested:** whether post-Manual_Start signal behaviour is consistent with the documented design intent (MS enables manual inputs). The classification criteria (a1–a5, classes A–D) were stated in code before the run. The post-rule review was written after seeing the output and may only downgrade a verdict; this is enforced in code.
- **State flag:** constant 2.0; not authority evidence.
- **Brake and accelerator:** automation content straddles MS. The brake is active at MS in 54 % of trials and releases about 0.95 s later. The accelerator is active at MS in 86 % of d20_n0 trials. **Onset verdict: MIXED_OR_AMBIGUOUS.** Brake magnitude: **NOT_IDENTIFIABLE** (unit conflict, straddle, possible cap at 400).
- **Steering-wheel angle:** the rule verdict (A) was downgraded to **PLAUSIBLE_BUT_UNVERIFIED**. The channel is cell-locked while automation drives and changes at TOR in whole cells only; ICC is marginal. The left indicator (undocumented) is also PLAUSIBLE_BUT_UNVERIFIED. Steering torque: **NOT_IDENTIFIABLE**. No channel reaches class A.
- **Timeline:** MS → steering-angle change onset median 2.00 s; onset → lane crossing median 2.35 s. Lane crossing is not steering onset.
- **Geometry:** hazard distance usable per time point; hazard station only partially reconstructable; lateral geometry not logged; gap zero semantics unresolved.
- R3B t1/u are not substituted. R4 link classes are unchanged. No synthesis is started.

## D030 — R4V-D: D003 descriptive steering sequence (2026-09-24)
- **Primary steering-onset detector:** signed angle rise > 0.05 rad above its running minimum since MS, sustained 0.25 s. It is causal, uses a fixed MS + 15 s horizon, never uses lane crossing or Manual_Stop, and is robust to the post-MS scripted drift. It was compared with five alternatives; the median varies from 1.4 to 3.0 s across detectors, and none is cell-stereotyped.
- **Timings (492 eligible trials):** MS → onset median 2.10 s (IQR 1.30–3.13); onset → lane crossing 2.45 s (2.00–3.30). Weak participant structure (ICC ≤ 0.19). No exposure association (CIs include 0, with or without exposure 1).
- **Indicator:** never on between TOR and MS; it precedes steering onset in 63 % of trials. It stays PLAUSIBLE_BUT_UNVERIFIED and is not an intention time.
- **Torque:** almost a linear, opposite-sign function of the angle (r ≈ −0.99). NOT_IDENTIFIABLE as driver torque; excluded.
- **Hazard station** (`s_h = abscissa + dir · D`): reconstructed in 8 of 9 cells (435 trials; across-trial SD ≤ 1.7 m, residual p95 < 1 m). Not consistent in d0_n1 (dD/ds ≈ 0.78).
- **Gap zeros:** context-tagged (recording start, after far value, after lane crossing, handoff, after near value). Unresolved in general; true zero separation cannot be excluded for near-value zeros. Erratum to R4V: rare negatives and 0.24 % missing samples exist over full trials.
- **Descriptors:** hazard distance at onset and at lane crossing is VALIDATED (station-consistent trials). MS → onset, onset → lane crossing, indicator lead/lag and target-lane gaps are PROVISIONAL. A steering-duration proxy is BLOCKED (no completion event).
- **R3B:** 75 % of steering onsets fall after the t1 assumption window; the brake channel is co-active at 38 % of onsets. This is insufficient for a combined model. Nothing is substituted, and no synthesis is started.

## D031 — R5A: final research question, claim ledger and contribution structure (2026-09-24)
- **Research question frozen:** under which scenario, vehicle-capability and counterfactual transition conditions can a braking-only recovery satisfy a necessary stopping condition, and how far can D003 anchor the human timing it depends on? Four subordinate questions: measurement, human response, braking recoverability, integration boundary.
- **Canonical claim ledger:** `research/R5A_CLAIM_LEDGER.csv`, 40 claims: 1 SUPPORTED, 17 SUPPORTED_WITH_QUALIFIER, 6 PROVISIONAL, 11 BLOCKED, 5 WITHDRAWN. Each claim has permitted and forbidden wording, evidence, qualifier, scope and phase source.
- **Contributions:**
  - C1 D003 measurement/semantics audit: strong project contribution;
  - C2 human-response findings: supporting;
  - C3 evidence-graded vehicle/transition parameterisation: supporting;
  - C4 interval-bounded braking necessary-condition method: incremental/methodological;
  - C5 epistemic/assurance separation: incremental/methodological (prior-art check: INCREMENTAL).

  No novelty is claimed as established.
- **Also recorded:** the final identifiability map, the withdrawn/superseded list and the scope statements.
- Consolidation only: no new model, analysis, assumption or result, and no earlier output is changed. R5B (thesis structure / figure planning) is not started.

## D032 — R5B: thesis blueprint (2026-09-24)
- **Thesis structure:** 14 chapters (RQs folded into the Introduction; the interval method merged into the model chapter), ordered empirical evidence → modelling → integration boundary, as in the R5A result story.
- **Figure and table plan:** 10 main figures (F1–F10), 3 appendix figures, and 10 main + 3 appendix tables, all from stored outputs; no new computation. No probability or combined figure.
- **Drafted text:** results-chapter blueprint (R-1 … R-8), discussion (11 topics), limitations (groups A–H), future work (7 items, each tied to a limitation), a 298-word abstract, the contribution paragraph and the conclusion.
- **Traceability:** every abstract, contribution and conclusion sentence is traced to R5A claim IDs in machine-checked tables (`tests/test_r5b_blueprint.py`). Provisional claims must be hedged. BLOCKED/WITHDRAWN IDs never ground a claim alone. The contribution sentence for C5 cites the R5A contribution structure (R5A-C5), because the ledger has no positive claim for it.
- **Open items (need R5A reopened to use):**
  - T-1: steering-activity onset vs the t1 interval, stated as a finding;
  - hazard distance at TOR.

  Both are omitted.
- No new result; no claim status changed; no synthesis.

## D033 — R5A narrow amendment: L41 and L42 (2026-09-24)
- R5A was reopened only to add two claims that R5B left out as open items. No existing claim status or wording changed. Both claims were verified against stored R4V-D outputs; nothing was recomputed from the archive.
- **L41 (SUPPORTED_WITH_QUALIFIER):** measured from TOR, the steering-angle activity onset falls predominantly after the R3B assumed t1 interval (1.15–3.0 s):
  - primary detector: 75% after 3.0 s, none before 1.15 s (n = 491);
  - a majority for all six detectors (57–87%) and in every cell (51–98%);
  - it does not hold against the 4 s supplementary bound (47%).

  This is a descriptive comparison of a signal event with an assumption. It implies no braking timing and no causal link. L09 stays PROVISIONAL.
- **L42 (SUPPORTED_WITH_QUALIFIER):** hazard distance at TOR is the directly logged Distance_to_Construction, interpolated at TOR. It is not derived from speed or TTC. Median 178 m (IQR 175–196) in 435 station-consistent trials; d0_n1 excluded (logged value consistent, along-path meaning unverified). The R4V all-trial median (177.5 m) is superseded for claim purposes.
- **Ledger:** 42 claims: 1 SUPPORTED, 19 SUPPORTED_WITH_QUALIFIER, 6 PROVISIONAL, 11 BLOCKED, 5 WITHDRAWN.
- R5B open items T-1 and "hazard distance at TOR" are now resolvable, but the R5B revision is not started.

## D034 — R5B final revision and freeze (2026-09-24)
- **Stale items removed:** the R5B open items (T-1; hazard distance at TOR) are replaced by the ledger claims L41 and L42. Their permitted wording, required qualifier and forbidden wording are quoted verbatim, and a test enforces this.
- **Structure frozen unchanged:** 14 chapters. The chapter table now also records major caveats. A garbled T2 source reference was corrected (R4V-D §1).
- **L41 use:**
  - F9 moves to a TOR-anchored axis, with a hatched band labelled "R3B assumed braking-delay interval" (model assumption, not observed) and a dashed 4.0 s supplementary bound;
  - it also appears in FA1, the T8 final panel, R-7 (verbatim block), R-8 (illustration only), and one methodological discussion topic: it neither validates nor invalidates t1, does not show braking before steering, and illustrates why the two clocks cannot be merged without an identified control bridge;
  - it is never labelled a driver braking time.
- **L42 use:** table and text only. A new table T11 (hazard reconstruction and distance at TOR by cell) has d0_n1 explicitly marked "along-road interpretation excluded". R-1 carries a verbatim block. L42 is not used in the discussion or for any stopping-distance claim. The appendix figure FA3 is dropped as redundant with T11.
- **Frozen lists:** F1–F10, FA1–FA2; T1–T11, TA1–TA3. Supersedes the counts in D032 (10 main tables; 3 appendix figures).
- **Unchanged:** the abstract, contribution paragraph and conclusion. L41 needs its full qualifier to be stated safely; L42 is a descriptor, not a result.
- **New checks** (`tests/test_r5b_blueprint.py`):
  - no stale reopen text;
  - L41/L42 quoted verbatim;
  - every line citing L41 marks the interval as an assumption, and every line citing L42 carries its station-consistent / d0_n1 scope;
  - the F9 band label;
  - results claim lines exist in the ledger, and all-BLOCKED lines are marked as boundary statements;
  - the frozen figure/table lists.
- No new result, no claim-status change, no new analysis. Figure rendering and full drafting are not started.

## D035 — R6A: final thesis figure rendering and manifest freeze (2026-09-24)
- **Frozen figure set rendered:** all 12 figures planned in R5B §2 (F1–F10, FA1–FA2) rendered to `thesis/figures/` in both vector (`.pdf`) and preview (`.png`) formats from stored, validated outputs. Total: 24 figure files.
- **Rendering script & manifest:** `src/figures/r6a_thesis_figures.py` writes `thesis/figures/figure_manifest.json` recording figure metadata, generation command, git commit, outputs, and sha256 hashes of all source files.
- **Documentation generated from manifest:** `docs/R6A_FINAL_FIGURES.md` is generated directly from the canonical figure manifest and ledger to prevent caption drift. For every figure, it records figure ID, title, purpose, outputs, generation command, source phase, source files with hashes, claim IDs with statuses, qualification status, required qualifiers, forbidden interpretations, and canonical caption.
- **Byte determinism verified:** two independent renders produce 100% byte-identical PDF and PNG files (identical SHA256 hashes across all 24 image outputs). Matplotlib metadata and `pdf.fonttype=42` are locked. Figure outputs are not git-ignored.
- **Governance & qualification preserved:**
  - F4 includes L34 ("TOR → validated lane crossing shows no clear linear exposure association (not shown)") and qualifies the modest t_button slope as non-causal.
  - F9 and FA1 preserve L41 model-assumption distinction: the 1.15–3.0 s interval is strictly labelled and described as the "R3B assumed braking-delay interval", a model assumption, never as driver braking time; caption notes no braking timing is implied.
  - Boundary figures F3 and F10 explicitly treat BLOCKED claims as unidentifiability limits, never positive empirical findings.
  - L42 (hazard distance at TOR) remains strictly table/text only (T11 in Chapter 4; station-consistent cells, d0_n1 excluded) and is not rendered as a figure.
  - No WITHDRAWN claims appear in any figure.
- **Test suite:** `tests/test_r6a_figures.py` (11 tests covering figure completeness, manifest/documentation consistency, caption consistency, claim validity, blocked/withdrawn exclusion, L41/L42 preservation, F4/L34 requirement, byte determinism, gitignore status, and results immutability).
- Consolidation only: no new model, analysis or result; no earlier output is changed. R6B (thesis drafting) is not started.

## D036 — R6B: full thesis drafting (2026-09-24)
- **Full thesis drafted:** all 14 chapters, front matter, appendices, and references drafted in academic prose in `thesis/draft/` (28,801 words total in `thesis/draft/thesis.md`).
- **Claim grounding:** all 42 claims ($L01$–$L42$) from `research/R5A_CLAIM_LEDGER.csv` are mapped, cited, and grounded within permitted wording.
- **Frozen structures respected:** 14-chapter structure from R5B §1; figures F1–F10, FA1–FA2 placed; tables T1–T11, TA1–TA3 placed.
- **Traceability preserved:** abstract (298 words), contribution paragraph, and conclusion (K1–K8) match the traced text in `docs/R5B_THESIS_BLUEPRINT.md` verbatim.
- **Claim boundary invariants enforced:**
  - L41 verbatim comparison with the R3B assumed braking-delay interval (1.15–3.0 s) preserves the required qualifier: signal event vs model assumption, unverified steering authorship, 4 s exception, no driver braking timing implied.
  - L42 verbatim block preserves station-consistent scope (median 178 m; d0_n1 strictly excluded).
  - Four unidentifiable control bridges (human event to braking onset, authority timing, manoeuvre completion, lateral geometry) remain strictly uncomposed.
  - Refusal to synthesize unsupported composite recoverability envelopes or crash probabilities.
  - All banned overclaim phrases absent from prose.
- **Test suite:** `tests/test_r6b_thesis.py` (12 tests passing).
- Consolidation and drafting only: no new models, parameter sweeps, or analyses; no change to claim statuses.

## D037 — R6D: targeted final thesis corrections (2026-09-24)
- **Authoritative Issue List:** Resolved all P0 and P1 issues identified in the R6C audit report.
- **P0-1 (Table T11 Rebuilt):** Rebuilt Table T11 in `thesis/draft/ch04_dataset_audit.md` directly from `results/R4V_steering_sequence/hazard_reconstruction.csv` across all 9 cells (Road IDs 15, 37, 23, 24, 31; Stations 79.7 m, 788.9 m, etc.); cell `d0_n1` explicitly marked as excluded from along-road interpretation; Claim L42 scope preserved.
- **P0-2 (Table TA2 Rebuilt):** Rebuilt Table TA2 in `thesis/draft/appendices.md` directly from `results/R3B_braking_bounds/t_required_bounds.csv` and `results/R3B_braking_bounds/results.csv` across all 30 canonical scenario-branch rows to 4 decimal places; corrected TTC 5s classification inversions; zero stale draft values remain.
- **P0-3 (Figure Links & Portability):** Replaced all absolute `/Users/...` machine paths in markdown files with portable relative paths (`thesis/figures/...`); aligned all embed filenames with canonical manifest names (`F5_r3b_classification_matrix.png`, `F6_r3b_t_required_bounds.png`, `F7_r3b_sensitivity.png`, `F8_transition_branch_comparison.png`, `F9_steering_sequence_vs_assumed_interval.png`, `F10_identifiability_boundary.png`, `FA1_onset_detector_sensitivity.png`, `FA2_participant_exposure_slopes.png`); fixed mislabeled Figure F8 in Chapter 8.
- **P1-1 (Claim L14 Timing):** Corrected Chapter 4 lane-crossing timing to match canonical Claim L14 (TOR -> LC: median 6.40 s, IQR 5.45–7.70 s, n = 477; MS -> LC: median 4.80 s, IQR 3.75–5.94 s, n = 478); removed stale 6.25 s figure.
- **P1-2 (Friction Cap Exactness):** Replaced obsolete 4.9033 m/s² with canonical model value 4.905 m/s² ($\mu = 0.5, g = 9.81\text{ m/s}^2$).
- **P1-3 (Assurance Framework Citations):** Linked explicit citations `[A01]`–`[A07]` in Chapter 2 §2.5 for GSN, Eliminative Argumentation, Assurance 2.0, UL 4600, SOTIF, RESPONSE 3, and NASA-STD-7009A.
- **P1-4 (Bibliography Pruning):** Removed uncited orphan references S14, S16, S21, and S26 from `references.md`; zero filler citations added; 100% of references in bibliography are now actively cited.
- **Master Thesis Reassembly:** Reassembled `thesis/draft/thesis.md` from corrected modular files (28,719 words).
- **Test Suite:** Extended `tests/test_r6b_thesis.py` with 9 regression tests covering all R6D corrections (21/21 passed); full suite (455 passed, 1 deselected) clean.
- Strictly corrective: no new scientific results, no claim status changes, no figure modifications, and no analysis reruns.

## D038 — R7B: public release preparation and thesis embargo (2026-09-24)
- **License:** Added root MIT LICENSE file for project source code. Third-party data terms explicitly preserved without ownership claims.
- **Dependencies:** Created `requirements.txt` with sensible lower bounds for external dependencies (`numpy`, `scipy`, `pandas`, `matplotlib`, `sympy`, `pytest`).
- **README Rewrite:** Comprehensive technical documentation covering research question, repository contents, main findings (grounded in R5A ledger), non-claims, installation, testing, figure reproduction, data availability, licensing, and thesis manuscript notice.
- **Path Relativization:** Eliminated all 21 machine-specific `/Users/fengzhecharlieli/...` Markdown links across legacy audit files in `experiments/` and `docs/`.
- **.gitignore:** Added development, coverage, log, and swap file exclusions (`*.log`, `*.swp`, `*.swo`, `.coverage`, `htmlcov/`, `.ruff_cache/`).
- **Thesis Embargo Strategy:** Preserved complete thesis draft locally on `audit/research-baseline-restructure`. Prepared clean public release branch without exposing `thesis/draft/` in git history, protecting pre-defense institutional examination and anti-plagiarism invariants.
