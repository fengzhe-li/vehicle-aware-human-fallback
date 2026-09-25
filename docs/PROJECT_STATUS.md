# Project Status: Vehicle-Aware Human Fallback

**Repository:** `vehicle-aware-human-fallback`
**Current milestone:** **R7B complete** (claims: 42-claim ledger `research/R5A_CLAIM_LEDGER.csv`, D033; frozen blueprint `docs/R5B_THESIS_BLUEPRINT.md`, D034; rendered figures: F1–F10, FA1–FA2 in `thesis/figures/`, manifest `thesis/figures/figure_manifest.json`, D035; full thesis drafted: 14 chapters in `thesis/draft/thesis.md`, 28,719 words, D036; targeted corrections complete: D037; public release preparation, MIT license, requirements.txt, path relativization, and thesis embargo complete: D038)
**Date:** 2026-09-24
**Pre-audit snapshot:** tag `pre-audit-2026-09-22`, commit `7f918fcc269ce734f6434f069a9c2c35b0269aac` (branch `archive/pre-audit-2026-09-22`)
**Source state of the audit:** `main@1ad19510edf567db1522772cdae2ae2f52afeff1`
**Frozen Phase 0 baseline:** `phase0-frozen` (`bc21fbce8b9b9518919fcaecd6a301785a1fee0d`)
**Test suite:** see the R2A commit (pre-existing tests unchanged except the replaced collision-proxy test)
**Current stage:** **EXPLORATORY.** A potentially thesis-capable / paper-shaped core exists **after repairs**. Not manuscript-ready. Not submission-ready.
**Paper readiness:** **WITHDRAWN.** The former `P1-B: READY` and `PAPER-READY, PROGRAMME-INCOMPLETE` (H0-B) labels no longer apply.

Authoritative documents:
- `docs/RESEARCH_ARCHITECTURE_V2.md`: mother question, causal layers A–D, B↔A interface, closed loop, gated synthesis
- `docs/OBSERVATION_LAYER.md`: mandatory measurement rules
- `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`: full status table, withdrawals, novelty, familiarity split
- `research/data_matrix/D003_KNOWN_BLOCKERS.md`: open D003 blockers and the dataset owners' prior analyses

This file previously (2026-09-21) reported `P1-B: READY` and `H0-B: CORE PHYSICAL SPINE COMPLETE`. That content is preserved in git history and at the pre-audit tag.

---

## 1. Branch ledger (corrected)

| Branch | Description | Previous decision | Corrected status | Decision |
|---|---|---|---|---|
| Phase 0 | Scoping and architecture | COMPLETE | COMPLETE as a historical baseline. Its architecture is superseded by V2 for structure, not for history. | KEEP |
| A0 | Simulator and analytical oracle | PASS | **MODEL-VALID** (numerical integration matches closed form) | KEEP |
| A1 | Withdrawal × vehicle response | NARROW / COMPLETE | **MODEL-VALID counterfactual.** W1 (immediate withdrawal) is not representative of regulated L3 transition behaviour. | NARROW |
| B0 | Risk-state escalation | ANALYTICAL ONLY | Modelling remark, true by construction under the Markov assumption | NARROW |
| B1 | Risk-state simulation | KILLED | Not executed | — |
| C0 | Internal-model mismatch | DEFER | Severance argument **WITHDRAWN**; RQ-M split into four sub-questions | RESTRUCTURE |
| C1 | Mismatch simulation | NOT AUTHORIZED | Not executed | DEFER |
| D0 | State-dependent boundary | D0-B | **PARTIAL / MODEL-VALID.** One longitudinal slice of the deterministic precursor. | KEEP (math), NARROW (claims) |
| D1 | Handover timing simulation | NOT REQUIRED | Not executed | — |
| E0 | Boundary robustness | E0-A, V1 | **MODEL-VALID** monotonicity within the stated domain; no empirical validation | KEEP (math), NARROW (validation language) |
| F0 / G0 / G0.1 / G0.2 | Synthesis, novelty, quantitative ledger | COMPLETE: P1-B | Novelty claims **WITHDRAWN/NARROWED**; P1-B withdrawn. Arithmetic in the quantitative ledger is retained. | RESTRUCTURE |
| H0 | Original scope reconciliation | COMPLETE: H0-B | Contains a later-constructed "original" RQ4 quote and a four-RQ structure not in the charter | RESTRUCTURE |
| Phase 2A | Public human-data audit | H2A / M0-C | `lane_gap` described as direct although unparsed and undocumented; owners' analyses not cited; M0-C over-broad | RESTRUCTURE |
| Phase 2B-1 … 2B-1.4 | D003 empirical recovery (H1) | H1-B | Timeline descriptives **PARTIAL** (pending semantics); `T_stable` **WITHDRAWN**; correction counts **INVALID AS COMPUTED**; collision proxy **WITHDRAWN**; factorial causal language **WITHDRAWN**; `T_pass` kept | RESTRUCTURE |
| Phase 2B-2 | Controller-model competition | "Current focus" | Not started | DEFER |
| System synthesis | Recoverability envelope | "RQ1 PARTIALLY ANSWERED" | **NOT STARTED / GATED** | DEFER |

---

## 2. What is established (within stated scope)

1. **Closed-form longitudinal requirement (MODEL-VALID).** Inside a deterministic, open-loop, 1-D model with a stationary in-lane hazard and a step emergency brake command:
   $$T_{required} = \frac{v_0}{2 a_{max}} + t_1 \left(1 - \frac{a_{pre}}{a_{max}}\right)\left(1 - \frac{a_{pre} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right) - \frac{a_{max} t_3^2}{24 v_0}$$
   This is standard kinematics. The `t1 + t2 + t3/2` structure and the `−a·t3²/24` term are prior-art-compatible mechanics, not novel results.
2. **Model-internal sensitivities** (A1, D0, E0; `docs/QUANTITATIVE_CLAIM_LEDGER.md`). The arithmetic is retained. Effect-size ratios depend on the chosen parameter ranges.
3. **Numerical verification** of the simulator against the closed form (A0).

Nothing in this list is empirical validation of real vehicles, drivers, or transitions.

## 3. What is not established

- A complete vehicle-response layer: the `u -> a` mapping for partial, regenerative, one-pedal, and blended braking is untested.
- Human control reacquisition beyond provisional event timing (D003 channel, authority, and window semantics unresolved).
- Human stabilisation time (the former `T_stable` is withdrawn).
- Any causal effect of workload or traffic density.
- Any transition-layer result beyond the W0/W1 abstraction; TOR budget never varied.
- Hazard-state layer.
- Any system-level recoverability synthesis.
- Novelty.

## 4. Next phase

Phase R4 (system integration boundary / synthesis readiness; audit only) is recorded in `docs/R4_SYNTHESIS_READINESS.md`, with `research/R4_SYNTHESIS_READINESS_MATRIX.csv` and `research/R4_CROSS_LAYER_LINKS.csv`. Verdict: only S1 (braking-only necessary condition, which R3B already is) is defensible. No human-to-model link is identified (`t_button` ≠ t1). S2/S3 are blocked mainly by B17, B7 and hazard geometry, all answerable only by the dataset owners. Recommended next step: stop and wait for owner clarification. **Superseded:** there is no external owner; `docs/R4_INTERNAL_SOURCE_OF_TRUTH_AUDIT.md` finds no D003-generating artifacts in the project, reclassifies B7 as documented design intent (Manual_Start = switch to manual mode enabling manual inputs) and splits B17 (post-switch channels driver-generated by design, pending verification). Recommended next: internal verification of that design intent.

Phase R4V (control-channel authorship validation) is recorded in `docs/R4V_CHANNEL_AUTHORSHIP_VALIDATION.md`, with outputs in `results/R4V_channel_authorship/` (D029).
- Brake and accelerator: automation content straddles Manual_Start, so onset is MIXED_OR_AMBIGUOUS; brake magnitude is NOT_IDENTIFIABLE.
- Steering-wheel angle and left indicator: PLAUSIBLE_BUT_UNVERIFIED.
- Steering torque and the state flag (constant 2.0): NOT_IDENTIFIABLE.
- R3B t1/u are not substituted, and R4 link classes are unchanged.
- A descriptive, class-B steering-onset timeline is possible; steering recoverability is still blocked by geometry and gap semantics.

Phase R4V-D (descriptive steering sequence) is recorded in `docs/R4V_STEERING_SEQUENCE.md`, with outputs in `results/R4V_steering_sequence/` (D030).
- Causal steering-onset detector, compared with alternatives: MS → onset median 2.10 s; onset → lane crossing 2.45 s. No exposure association.
- Hazard station reconstructed in 8 of 9 cells.
- Gap zeros context-tagged but unresolved; torque not identifiable.
- Steering-duration proxy blocked. A combined braking + steering model is not defensible.

Phase R5A (consolidation; no new results) is recorded in `docs/R5A_FINAL_CLAIM_LEDGER.md`, with the canonical ledger in `research/R5A_CLAIM_LEDGER.csv` (D031).
- Frozen: the final research question, 40 claims at freeze, 42 after the D033 amendment that added L41 and L42 (1 SUPPORTED, 19 SUPPORTED_WITH_QUALIFIER, 6 PROVISIONAL, 11 BLOCKED, 5 WITHDRAWN), five contributions, the result story, the withdrawn/superseded list, the identifiability map and the scope statements.
- Thesis drafting must use the permitted wording in the ledger.

Phase R5B (planning and drafting; no new results) is recorded in `docs/R5B_THESIS_BLUEPRINT.md` (D032) and **frozen** after the final revision (D034).
- 14-chapter structure; figures F1–F10 plus FA1–FA2; tables T1–T11 plus TA1–TA3, all planned from stored outputs.
- L41 is used in F9 (labelled band "R3B assumed braking-delay interval"), T8, FA1, R-7, R-8 and one methodological discussion topic.
- L42 is used in T11 and R-1 only (station-consistent cells; d0_n1 excluded).
- No open items remain.
- Results and discussion blueprints; limitations A–H; future work tied to the limitations.
- Traced abstract (298 words), contribution paragraph and conclusion.
- Traceability is machine-checked against the R5A ledger.

Phase R6A (figure rendering from stored outputs; no new results) is recorded in `docs/R6A_FINAL_FIGURES.md`, with canonical figures in `thesis/figures/` and manifest in `thesis/figures/figure_manifest.json` (D035).
- All 12 figures planned in R5B §2 (F1–F10, FA1–FA2) rendered in vector (`.pdf`) and preview (`.png`) formats from stored, validated outputs (24 image files total).
- Rendering script: `src/figures/r6a_thesis_figures.py`.
- Byte-level determinism confirmed: independent renders produce 100% byte-identical PDF and PNG files (SHA256 verified).
- Single source of truth: `docs/R6A_FINAL_FIGURES.md` is generated directly from the canonical manifest to prevent caption drift.
- All qualifications and boundary conditions enforced: F4 includes L34; F9/FA1 strictly label the R3B assumed braking-delay interval as a model assumption (no driver braking implied); F3/F10 treat blocked claims as limits; L42 is table/text only.
- Test suite: `tests/test_r6a_figures.py` (11 tests passing).

Phase R6B (full thesis drafting; no new results) is recorded in `docs/R6B_THESIS_DRAFTING.md`, with the master thesis in `thesis/draft/thesis.md` and component drafts in `thesis/draft/` (D036).
- All 14 chapters, front matter, appendices, and references drafted in academic prose (28,801 words total).
- All 42 claims ($L01$–$L42$) mapped, cited, and grounded within permitted wording.
- Frozen 14-chapter structure, 12 figures (F1–F10, FA1–FA2), and 14 tables (T1–T11, TA1–TA3) placed.
- Traced abstract (298 words), contribution paragraph, and conclusion (K1–K8) match the frozen blueprint verbatim.
- Invariants strictly preserved: L41 verbatim comparison with the assumed $t_1$ window; L42 station-consistent scope; 4 unidentifiable control bridges kept uncomposed; no combined recoverability synthesis.
Phase R6D (targeted final thesis corrections; no new results) is recorded in `docs/DECISIONS.md` (D037).
- Resolved all P0 and P1 issues from the R6C thesis audit.
- Table T11 rebuilt directly from `results/R4V_steering_sequence/hazard_reconstruction.csv` across all 9 cells (cell `d0_n1` explicitly marked as excluded).
- Table TA2 rebuilt directly from `results/R3B_braking_bounds/t_required_bounds.csv` and `results.csv` across all 30 canonical rows to 4 decimal places.
- Hardcoded `/Users/...` machine paths eliminated in favor of portable relative paths; canonical image filenames aligned with `thesis/figures/figure_manifest.json`; mislabeled Figure F8 caption corrected.
- Chapter 4 lane-crossing timing aligned with canonical Claim L14 (TOR -> LC: median 6.40 s, IQR 5.45–7.70 s, n = 477; MS -> LC: median 4.80 s, IQR 3.75–5.94 s, n = 478).
- Friction deceleration cap aligned with canonical 4.905 m/s² ($\mu = 0.5, g = 9.81\text{ m/s}^2$).
- Assurance citations `[A01]`–`[A07]` linked in Chapter 2 §2.5; uncited orphan references S14, S16, S21, S26 removed from `references.md` (100% citation rate).
- Master thesis reassembled in `thesis/draft/thesis.md` (28,719 words).
- Verification suite: `tests/test_r6b_thesis.py` expanded to 21 tests (all passing); full test suite (455 passed, 1 deselected) clean.

Phase R7B (public release preparation and thesis embargo; no new results) is recorded in `docs/DECISIONS.md` (D038).
- Added root `LICENSE` (MIT) for project source code; third-party data terms preserved.
- Added `requirements.txt` with external dependencies (`numpy`, `scipy`, `pandas`, `matplotlib`, `sympy`, `pytest`).
- Rewrote `README.md` to document research questions, D003 audit, R3B braking slices, non-claims, installation, test suite, deterministic figure generation, and data availability.
- Relativized all 21 machine-specific `/Users/fengzhecharlieli/...` Markdown links across legacy audit files.
- Added development and test artifact exclusions to `.gitignore` (`*.log`, `*.swp`, `*.swo`, `.coverage`, `htmlcov/`, `.ruff_cache/`).
- Enforced thesis embargo strategy: full thesis draft preserved locally; clean public release branch prepared with `thesis/draft/` absent from its entire git history.


Phase R3B (the three model corrections implemented with legacy reproduction; deterministic interval bounds for the braking-only slice over the frozen scenarios; labels valid only for the braking-only model) has been carried out on the same branch and **awaits review**: `docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md`. The width is dominated by the t1 assumption interval. No probability, no envelope, no steering. Not ready for a true synthesis phase. R3C has not started. **Gate review (2026-09-24, `docs/R3B_GATE_REVIEW.md`):** corner bounds are conditionally valid (coordinatewise-monotone domain; thin for P2); committed R3B outputs are provisional until the listed engine/test changes are made. **Gate engineering (2026-09-24, D024):** analytic-derivative monotonicity guard (fail-closed), epsilon = 0.01 s time-margin classification with boundary flag, legacy-enum guard and behavioural R3A tests are implemented; the guard passes the main domain but fails closed on the t1 = 4 s supplement (60 km/h, mu 0.5, P2), so a rerun needs a scientific decision on that supplement first. **Resolved (D025, Option A):** those two supplement cases now use an exact stationary-point t1 bound; the supplement is evaluated separately from the main domain. **Final (D026):** configuration frozen unchanged; authorised canonical rerun on code `a4f2cc4` (clean); no numerical change; reproduction test and reporting consistency pass. R3B is complete as a braking-only slice; system synthesis is not started and remains gated (t1/t3 and authority timing are assumptions; steering not modelled).

<!-- R3B:counts:START -->
Scenario count: 150. PARAMETER-SENSITIVE: 47; ROBUSTLY SATISFIED: 58; ROBUSTLY UNSATISFIED: 45.
<!-- R3B:counts:END -->

Phase R3B-0 (official UN R157 text verified clause by clause, with three R157 statements corrected; ISO access status made explicit; assurance prior-art search: the measurement/assurance framing is INCREMENTAL; formal event/state specification; manoeuvre-specific `T_available`/`T_required`; braking-slice scope and a no-code correction design; interval-readiness classification) has been carried out on the same branch and **awaits review**: `docs/R3B0_SOURCE_AND_SPECIFICATION_HARDENING.md`. An interval-only braking evaluation is conditionally defensible but not yet ready.

Phase R3A (evidence baseline for the vehicle-response, automation-transition and hazard-state layers; parameter provenance registry; R3A identifiability matrix; no synthesis) has been carried out on the same branch and **awaits review**: `docs/R3A_VEHICLE_TRANSITION_HAZARD_REPORT.md`. Key findings: `a_pre` is primarily a transition-policy variable; the braking spine is the capability-bound (`u = 1`) necessary-condition slice; recoverability must be manoeuvre-specific; authority transfer, escape-path availability and blending are not identifiable.

Phase R2C-lite (participant-level associations of `t_button` with driving / ADAS experience, a secondary re-analysis; carry-over sensitivity of the R2B exposure association; multi-TOR robustness) has been carried out on the same branch and **awaits review**: `docs/R2C_LITE_REPORT.md`. No participant association survives multiplicity correction; no carry-over association is detected. No eye-tracking, owner-dependent or system-synthesis work has started.

Phase R2B (repeated-exposure / within-participant adaptation on B17-safe quantities; owner-metric reconciliation; owner question set and email draft, not sent) has been carried out on the same branch and **awaits review**: `docs/R2B_REPEATED_EXPOSURE_REPORT.md`.

Phase R2A (pipeline consolidation; event-timing and vehicle-state descriptives; control-channel authorship blocker B17) has been carried out on branch `audit/research-baseline-restructure` and **awaits review**. The canonical D003 path is `src/data/d003_ingest.py` (`research/data_matrix/D003_PIPELINE_REGISTRY.md`). Human first-input metrics from control channels are UNRESOLVED (B17).

Phase R1 (D003 ingestion and measurement-semantics repair) was carried out before R2A. It added strict ingestion (`src/data/d003_ingest.py`), ingestion tests, and validation outputs (`results/R1_ingestion_validation/`). No scientific result, causal claim or status label outside D003 ingestion changed. Blocker statuses: `research/data_matrix/D003_KNOWN_BLOCKERS.md`. R2 has not started. See `docs/DECISIONS.md` D015–D016.
