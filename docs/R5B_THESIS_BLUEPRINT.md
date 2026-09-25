# R5B: thesis blueprint

**Status:** 2026-09-24. **Frozen** (R5B final revision, D034); claim boundary: the 42-claim ledger after the D033 amendment. Planning and drafting only.
- No new result.
- No change to any claim status.
- No synthesis.

**Claim boundary:** `research/R5A_CLAIM_LEDGER.csv` is authoritative. Claim IDs `Lxx` refer to it. Wording here never goes beyond a claim's `permitted_wording`. Where a sentence would need a claim that is not in the ledger, it is weakened or omitted, and the case is listed in §11.

**Literature rule:** only sources in `research/R3A_SOURCE_REGISTER.csv` (S01–S31), the prior-art notes in `research/ASSURANCE_FRAMEWORK_PRIOR_ART.md` and the dataset owners' paper (S17) may be cited. Sources read at abstract or summary level (for example S05, S09–S12, S15, S16) may be cited only for what their abstracts state. The navigation-only sources S29 and S30 are never cited. Any other citation needs a new, verified register entry before drafting.

**Test:** `tests/test_r5b_blueprint.py` checks claim-ID existence, sentence-level traceability, hedging of provisional claims, banned wording and the abstract length.

---

## 1. Thesis structure (frozen)

The requested 15 chapters are condensed into 14. This was reviewed at the freeze and kept, because both merges remove duplication rather than add symmetry:
- The research questions become §1.3 of the Introduction, because they are short and frame everything that follows.
- The interval method is merged into the model chapter (Ch. 7), because the method is only meaningful with the model.

The order follows the R5A result story: empirical evidence, then modelling, then the boundary between them.

| Ch. | Title | Purpose (source phases) | Claim IDs allowed | Figures / tables | Major caveats | Must NOT appear |
|---|---|---|---|---|---|---|
| 1 | Introduction | Problem; why time-critical takeovers need a necessary-condition view; RQs (§1.3); contributions (§1.4) (R5A) | RQ wording from R5A §1; contribution paragraph (§9 below) | F1 | Braking-only, necessary condition; D003 does not identify driver braking | success prediction; safety envelope; "first" |
| 2 | Background and related work | Takeover timing (S09, S10, S17); shared control (S11); transition models and time budgets (S12, S13, S19); regulatory benchmark and braking evidence (S01, S02, S31, S03, S04, S20); assurance context (prior-art notes) (R3A, R3B-0) | Descriptions of sources at their access level | — | Abstract-level sources only for what their abstracts say | claims from abstract-only sources beyond their abstracts; novelty claims |
| 3 | Evidence framework and research design | Evidence classes; phase sequence; claim-ledger discipline (R0 baseline, R4, R5A) | L04, L29, L30 (as design rationale) | T1 | — | any result |
| 4 | Dataset and event-semantics audit (D003) | D003 description; event semantics; control-channel authorship; mode flag; hazard reconstruction and distance at TOR; gap semantics (R1, R2A, R4 internal audit, R4V, R4V-D §6–7) | L05, L06, L07, L08, L12, L14, L17, L18, L42 | F2, F3; T2, T3, T11 | Manual_Start is documented design intent, not a verified longitudinal authority boundary. The hazard station and the distance at TOR are along-road quantities only in the 8 station-consistent cells (d0_n1 excluded). Gap zeros are unresolved | "driver braking"; "brake onset" as a human event; lane crossing as completion; "the hazard was 178 m away in all scenarios" |
| 5 | Human response analysis | `t_button`; exposure association; carry-over; covariates; TOR → lane crossing (R2B, R2C-lite) | L01, L02, L03 (permitted wording only), L14, L34 | F4; T4 | Associational; the exposures 2–9 CI includes 0; n = 57 for covariates | "reaction time"; "learning"; experience or ADAS effects |
| 6 | Vehicle and automation-transition evidence | Parameter provenance; friction relation; P0/P1/P2 as counterfactual branches; authority timing as assumption (R3A, R3B-0, R3B §2–3) | L04, L24, L25 (definitions only) | T5 | Generic passenger-car evidence, not the D003 vehicle; branches counterfactual | D003 vehicle parameters; "how R157 systems behave" |
| 7 | Braking-only recoverability model and interval method | Success condition; closed form (standard kinematics, generalised); interval propagation; monotonicity guard; stationary-point escalation; ε classification; simulator cross-check (R3B §1–5, gate review, D024–D026) | L19 (method part), L27 (method), L40 (as the reason no closed-form novelty is claimed) | T6 | Deterministic point-mass model; u = 1 capability bound | "novel closed-form solution"; safe/unsafe labels |
| 8 | Braking-only results | Classification; TTC, speed, friction and a_max effects; branch comparison; authority timing; t1 sensitivity; 4 s supplement; D003-like case (R3B §6–8, §13) | L19–L28 | F5, F6, F7, F8; T7 | t1, t3, authority timing and a_sup are assumptions; labels are within-model | takeover success/failure; "P2 is safer"; statements about D003 drivers' braking |
| 9 | Descriptive steering sequence | Detector definition and comparison; event sequence; indicator; torque; hazard distances at onset and crossing; gaps; exposure; onset timing relative to the R3B assumed braking-delay interval (R4V-D; R5A §10) | L09, L10, L11, L12, L13, L15, L16, L18, L35, L41 | F9; T8; appendix FA1 | Detector-dependent timing; steering authorship unverified; indicator undocumented; L41 compares a signal event with a model assumption | "steering reaction time"; "intention time"; gap acceptance; "steering follows braking"; "t1 is validated / too short" |
| 10 | Integration boundary | Identifiability map; why no human → braking link; why no combined model (R4, R4V, R4V-D §10, R5A) | L04, L29, L30; identifiability map (R5A §7); L41 only as an illustration that the two clocks are not bridged (the interval is an R3B assumption) | F10; T9 | Absent links are not evidence that the missing effects are small | combined score; recoverability envelope |
| 11 | Discussion | See §5 | as listed in §5 | back-references | — | new results |
| 12 | Limitations | See §6 | — | T10 | — | — |
| 13 | Future work | See §7 | — | — | — | generic filler |
| 14 | Conclusion | See §10 | as traced | — | — | new claims |
| App. | Appendices | Full claim ledger; detector sensitivity; participant slopes; supplement table; reproduction instructions | — | TA1–TA3, FA1–FA2 | — | — |

---

## 2. Figure plan (frozen: F1–F10, FA1–FA2)

"Existing" means an output already exists and can be used as is or restyled. "To draw" means a new rendering of existing data or of a documented diagram: no new computation beyond plotting stored values. Plan IDs are not final thesis numbers; figures are numbered by chapter at drafting.

| ID | Purpose | Data source | Axes / elements | Caption message | Placement | Claims |
|---|---|---|---|---|---|---|
| **F1** | Evidence / model architecture | R5A §2; R3B §2–3 | Four layers (human/D003, vehicle, transition, recoverability) as blocks; each input tagged with its evidence class (colour + text label); arrows only for links actually used in R3B | "Which inputs are observed, source-supported, assumed or model conditions, and where they enter the braking-only model." | Main, Ch. 1 or 3 | L04, L19 |
| **F2** | Event-semantic timeline | `results/R4V_steering_sequence/interval_summary.csv`; R2B | Horizontal time axis from TOR (s). Rows: TOR, Manual_Start, steering-activity onset, indicator, lane crossing, Manual_Stop. Median markers with IQR bars; semantic labels ("mode switch", "derived signal event, provisional", "validated crossing", "protocol handback") | "The observable takeover events are distinct; none of them is effective braking or manoeuvre completion." | Main, Ch. 4 | L08, L09, L13, L14 |
| **F3** | Brake/accelerator content across Manual_Start | `results/R4V_channel_authorship/trial_features.csv`, `cell_stereotypy.csv` | Per scenario cell: fraction with brake active at MS; brake release relative to MS (median, IQR); accelerator active at MS. Small multiples by cell, one shared axis | "Scripted automation content continues across the switch to manual mode, so driver brake onset and strength are not identifiable." | Main, Ch. 4 | L05, L06, L07 |
| **F4** | `t_button` vs exposure | Existing `results/R2B_repeated_exposure/figures/exposure_t_button_s.png` (restyle); `exposure_summary.csv` | x: exposure 1–9; y: `t_button` (s), median with IQR and participant-centred median; annotated model slope and CI | "A modest within-participant decrease of the mode-switch latency is associated with repeated exposure." | Main, Ch. 5 | L01 (L34 in caption) |
| **F5** | R3B classification matrix | `results/R3B_braking_bounds/results.csv` | Rows: TTC (2, 3, 5, 7, 10 s); columns: speed × μ; cells split into the 5 branches. Three labels drawn as text + pattern, not colour alone; t1 = 4 s changes marked with an outline | "Within the braking-only model, TTC at TOR separates robustly satisfied from robustly unsatisfied cases; the band between is assumption-dependent." | Main, Ch. 8 | L19, L20, L21, L22, L27, L28 |
| **F6** | T_required bounds vs TTC | Existing `results/R3B_braking_bounds/t_required_bounds.png`; `t_required_bounds.csv` | Per (speed, μ): bars for [min, max] T_required by branch; horizontal reference lines at TTC values | "Required-time intervals are 2.2–3.5 s wide; a case is parameter-sensitive when its TTC falls inside the interval." | Main, Ch. 8 | L19, L21, L22 |
| **F7** | Sensitivity | `results/R3B_braking_bounds/sensitivity.csv` | One-at-a-time swing share by parameter (t1, t3, t2, a_max, a_drag, a_sup, f_auth), grouped by μ; ranges across cases | "The t1 assumption drives most of the width; a_max matters only when friction does not bind." | Main, Ch. 8 | L23, L26 |
| **F8** | P0/P1/P2 comparison | `results/R3B_braking_bounds/policy_comparison.csv` | x: branch; y: midpoint ΔT_required relative to P0 with authority at effective control (s); points per (speed, μ); separate markers for authority at effective control vs uncertain | "Counterfactual support before authority shortens required time only while the automation keeps authority." | Main, Ch. 8 | L24, L25 |
| **F9** | Steering-sequence timeline with the R3B assumption band | `results/R4V_steering_sequence/event_table.csv` | x: time from TOR (s), so the band and the events share one clock. Rows: trials sorted by TOR → primary onset. Markers: Manual_Start, primary steering-activity onset, left-indicator onset, lane crossing; median lines. A shaded vertical band at 1.15–3.0 s labelled exactly "R3B assumed braking-delay interval", with the sub-label "model assumption, not observed". A dashed line at 4.0 s labelled "R3B supplementary upper bound (sensitivity only)". Title: "Descriptive signal events; steering authorship unverified" | "Measured from TOR, steering-angle activity onset falls predominantly after the R3B assumed braking-delay interval (75% after 3.0 s with the primary detector; a majority for every detector), but not predominantly after the 4 s supplementary bound. The band is a model assumption; the figure implies no braking timing." | Main, Ch. 9 | L09, L10, L11, L13, L27, L41 (assumed interval shown as assumption) |
| **F10** | Identifiability / synthesis boundary | R5A §7; `research/R4_CROSS_LAYER_LINKS.csv` | Nodes = quantities (TOR … automation model), grouped by layer; node label = identifiability class; edges = the links needed for a combined model, drawn solid (identified), dashed (assumption) or crossed (not identifiable) | "A combined braking-and-steering model would need links that the evidence does not identify." | Main, Ch. 10 | L04, L29, L30 |
| FA1 | Onset-detector sensitivity | `onset_detector_sensitivity.csv`; R5A §10 detector table | Median and IQR of MS → onset per detector; beside it, per detector, the share of TOR-anchored onsets after the R3B assumed braking-delay interval | "Onset time depends on the detector (median 1.4–3.0 s after Manual_Start); the 'predominantly after the assumed interval' comparison holds for every detector (57–87%)." | Appendix | L09, L41 (assumed interval) |
| FA2 | Participant exposure slopes | Existing `participant_slopes.png` | per-participant slope distribution | — | Appendix | L01 |

**Decisions at freeze:**
- **L41** enters **F9** (main) and **FA1** (appendix), always as a band labelled "R3B assumed braking-delay interval". It is never labelled a driver braking time, and never shown on the same axis as a braking-model output.
- **L42** (station-consistent cells; d0_n1 excluded) is **table and text only (T11, Ch. 4)**. It is one scenario descriptor per cell, and a figure would add nothing.
- The former hazard-station appendix figure (FA3) is dropped, because it is redundant with T11.

**Not planned** (redundant or unsupported):
- a probability or "safety" map;
- a combined longitudinal-lateral figure;
- covariate scatter plots (null results are better given in a table);
- any figure with both D003 timing and R3B required time on one axis.

**Visual rules:**
- labels never encoded by colour alone;
- one axis per chart;
- no safe/unsafe colouring (neutral three-level labels);
- model-assumption bands visually distinct from data (hatched), and labelled as assumptions.

---

## 3. Table plan (frozen: T1–T11, TA1–TA3)

Plan IDs are not final thesis numbers. **No table places R3B outputs and D003 timing in the same row, and no table computes a combined braking/steering quantity.**

| ID | Table | Purpose | Source | Claims | Placement |
|---|---|---|---|---|---|
| T1 | Evidence classes and claim statuses | Define the vocabulary used throughout | R5A §2–3 | — | Main, Ch. 3 |
| T2 | D003 event semantics | Each event: definition source, semantics used, what it is *not* | R4 internal audit; R4V-D §1 | L08, L13, L14 | Main, Ch. 4 |
| T3 | Channel authorship classes | Channel × (documentation, pre/post-MS behaviour, class) | R4V §7 | L05, L06, L07, L11, L12 | Main, Ch. 4 |
| T4 | Human-response results | `t_button` descriptives; exposure models (with/without cell controls; exposures 2–9; carry-over); covariate Spearman/Holm; TOR → lane crossing | R2B §3; R2C §1–2 | L01, L02, L34 | Main, Ch. 5 |
| T5 | Parameter / provenance | Every model parameter: interval, class, source ID, transferability note | R3B §3; `research/PARAMETER_PROVENANCE_REGISTRY.csv` | L04 | Main, Ch. 6 |
| T6 | R3B frozen configuration | Grid, intervals, branches, ε, standstill margin, supplement | R3B §13.1 | L19, L27 | Main, Ch. 7 |
| T7 | R3B classification summary | Counts by TTC, by speed and by μ; overall 58/47/45; supplement changes | R3B §6, §13.3 | L19, L20, L21, L22, L27 | Main, Ch. 8 |
| T8 | Steering-sequence descriptors | Interval summary (n, median, IQR, 5–95%, ICC, η²) with a descriptor-class column (validated / provisional / blocked). Gap rows give non-zero values only, with a visible column "zero semantics unresolved" and the share of zero-tagged samples. A final panel gives, per detector, the share of TOR-anchored onsets before, within and after the R3B assumed braking-delay interval (L41). | R4V-D §3, §7, §8; R5A §10 | L09, L10, L13, L15, L16, L18, L41 (assumed interval) | Main, Ch. 9 |
| T9 | Final identifiability matrix | 17 quantities × class × reason | R5A §7 | L04, L29, L30 | Main, Ch. 10 |
| T10 | Limitations / blocked variables | Blocked or assumed quantity → consequence → what would resolve it | §6 below | L03–L07, L11, L12, L29–L33 | Main, Ch. 12 |
| T11 | Hazard reconstruction and distance at TOR by scenario cell | Per cell: road ID, reconstructed station, across-trial SD, residual p95, dD/ds, station-consistent (yes/no), and logged Distance_to_Construction at TOR (median). d0_n1 is shown with its logged value but explicitly marked "along-road interpretation excluded (not station-consistent)" | `results/R4V_steering_sequence/hazard_reconstruction.csv`, `event_table.csv` | L17, L42 (station-consistent cells; d0_n1 excluded) | Main, Ch. 4 |
| TA1 | Full claim ledger | Auditability | `research/R5A_CLAIM_LEDGER.csv` | all | Appendix |
| TA2 | Full classification pivot and bounds | Reproducibility | R3B §6 generated blocks | L19 | Appendix |
| TA3 | Withdrawn / superseded claims | Auditability | R5A §6 | L36–L40 | Appendix |

---

## 4. Results chapter blueprint (narrative order)

These blueprints cover the results parts of Ch. 4, 5, 8, 9 and 10. Numbers are copied from the cited phases. A new number may not be introduced when drafting.

### R-1. What the dataset records, and what its signals mean (Ch. 4)

**Purpose.**
- Establish the events that are measurable: TOR, Manual_Start, lane crossing, Manual_Stop, hazard distance.
- Describe the scenario at TOR by the logged distance to the construction zone (L42, station-consistent cells only; d0_n1 excluded).
- Establish their documented meanings.
- Show that Manual_Start is documented as a switch to manual mode that enables manual inputs.
- Show that there is no logged mode or authority flag.

**Numbers:**
- 513 trials; 492 anchorable (TOR resolved and a single Manual_Start); 57 participants.
- `VehicleUpdate-state` is constant 2.0.
- Lane crossing validated in 478 of the 492.
- Hazard station reconstructed in 8 of 9 cells (across-trial SD ≤ 1.7 m).
- Distance_to_Construction at TOR (L42): median 178 m (IQR 175–196; 5–95% 151–197; n = 435 station-consistent trials); cell medians 158–197 m; d0_n1 excluded from the along-road interpretation.

**Permitted interpretation:** Manual_Start is a documented mode switch, and lateral signals are consistent with it.

**Caveat:** the switch is design intent, not a verified longitudinal authority boundary.

**L42 block** (station-consistent cells only; d0_n1 excluded):
- **Claim ID:** L42 (SUPPORTED_WITH_QUALIFIER; station-consistent cells only, d0_n1 excluded).
- **Permitted wording (verbatim):** "At the resolved TOR, the logged distance to the construction zone (Distance_to_Construction, linearly interpolated at the TOR time) is a median 178 m (IQR 175–196; 5–95% 151–197; n = 435 station-consistent trials); cell medians range from 158 to 197 m."
- **Required qualifier (verbatim):** "Directly logged, not derived from speed or TTC. Valid as an along-path distance only in the 8 station-consistent cells. d0_n1 is excluded: its logged value (135.7 m) is consistent across trials, but the channel's rate does not match the road abscissa there. The reference point on the construction zone is undocumented; the value is cell-dependent."
- **Location:** T11 (per cell) and Ch. 4 text. No figure.
- **Strongest forbidden interpretation:** "The hazard was 178 m away in all scenarios; TOR distance defines the escape space; TTC or stopping distance derived for D003 drivers from this value." Also forbidden: any real-driver stopping-distance claim from this value (station-consistent context).

**References:** F2, T2, T11. **Claims:** L08, L14, L17, L42 (station-consistent cells).

### R-2. Longitudinal control channels are not driver-only (Ch. 4)

**Purpose.**
- Show scripted, cell-locked brake activity between TOR and Manual_Start.
- Show brake and accelerator content that continues across the switch.
- Conclude that driver brake onset and braking strength are not identifiable.
- Present the criterion-based authorship classes.

**Numbers:**
- Brake onset between TOR and MS in 60% of trials; cell η² 0.76; participant ICC −0.11; stereotyped cells (for example d0_n0 at TOR + 1.200 s, IQR 0.000 s).
- Brake active at MS in 54% of trials (86–96% in the d10 cells); release a median 0.95 s after MS (IQR 0.80–1.10).
- Accelerator active at MS in 86% of d20_n0 trials.
- Brake value 400 reached in 0.6% of trials.

**Permitted interpretation:** these channels are MIXED_OR_AMBIGUOUS; brake magnitude is NOT_IDENTIFIABLE.

**Caveat:** this is a limit of D003's observability, not a statement about how drivers brake.

**References:** F3, T3. **Claims (boundary statements; permitted wording of BLOCKED claims):** L05, L06, L07, L12.

### R-3. Mode-switch latency and repeated exposure (Ch. 5)

**Purpose.**
- Report `t_button` as the TOR → mode-switch latency.
- Report the within-participant exposure association, and its robustness to cell controls, carry-over and multi-TOR exclusion.
- Report the precision caveat for exposures 2–9.
- Report the null TOR → lane-crossing association.

**Numbers:**
- `t_button` median 1.65 s (IQR 1.25–2.00), n = 492.
- Exposure slope −0.033 s per exposure (95% CI −0.058 to −0.007); −0.032 s without cell controls.
- Early vs late: −0.10 s; 63% of participants lower; Wilcoxon p = 0.006.
- Carry-over joint Wald p 0.56 / 0.77; slope change 3–4%.
- Exposures 2–9 reference CI −0.057 to 0.005.
- TOR → lane crossing +0.09 s per exposure (−0.13 to +0.31).

**Permitted interpretation:** a modest decrease associated with repeated exposure.

**Caveat:** associational; the per-exposure change is below the 0.05 s sampling interval; not a reaction time.

**References:** F4, T4, FA2. **Claims:** L01, L03, L34.

### R-4. Participant characteristics (Ch. 5)

**Purpose:**
- Report the pre-specified secondary re-analysis: 4 covariates × 2 outcomes, Holm-corrected.
- Report the null result.
- Note the confounding of experience with age.

**Numbers:**
- No Holm-significant association.
- Largest: ADAS-use vs median `t_button`, ρ −0.28, raw p 0.037, Holm p 0.30.
- Experience–age ρ 0.85.

**Permitted interpretation:** no association detected.

**Caveat:** n = 57; single self-report items; the owners analysed these variables already.

**References:** T4. **Claims:** L02.

### R-5. Braking-only classification across scenarios (Ch. 8)

**Purpose.**
- Present the 150-case classification and the exactness of the bounds.
- Present TTC as the dominant separator, and the speed and friction patterns.
- Explain a_max's conditional role.

**Numbers:**
- 58 ROBUSTLY SATISFIED / 47 PARAMETER-SENSITIVE / 45 ROBUSTLY UNSATISFIED.
- Simulator cross-check 2.2·10⁻⁴ relative; 0 boundary flags; closest |margin| 0.047 s.
- By TTC: at 2 s, 28 unsatisfied and 2 sensitive; at 3 s, 16 unsatisfied and 14 sensitive; at 5 s, 27 sensitive, 2 satisfied and 1 unsatisfied; at 7 s, 26 satisfied and 4 sensitive; at 10 s, all 30 satisfied.
- Speed, P0 with authority at effective control, dry road: midpoint 3.74 / 4.41 / 4.94 s; unsatisfied counts 11 / 15 / 19.
- μ 0.5: cap 4.905 m/s²; midpoint +0.36 to +1.36 s; unsatisfied 16 → 29.
- a_max elasticity on a dry road: −0.21 to −0.47; zero at μ 0.5.

**Permitted interpretation:** within the braking-only model and the stated intervals.

**Caveat:** a necessary condition; labels are not safe/unsafe.

**References:** F5, F6, T7. **Claims:** L19, L20, L21, L22, L23.

### R-6. Transition branches, authority timing and t1 (Ch. 8)

**Purpose.**
- Compare the counterfactual branches.
- Show that pre-control behaviour matters only while the automation holds authority.
- Show that t1 drives the interval width.
- Present the t1 = 4 s supplement and the D003-like case.

**Numbers:**
- Midpoint change relative to P0 with authority at effective control:
  - P1: −0.08 to −0.23 s;
  - P0 with uncertain authority: −0.03 to −0.11 s;
  - P2 with authority at effective control: −0.68 to −1.12 s;
  - P2 with uncertain authority: −0.45 to −0.69 s.
- 13 label changes.
- t1 one-at-a-time swing share 0.33–0.77; widths 2.2–3.5 s.
- Supplement: 10 labels change (9 at TTC 7 s, 1 at 5 s).
- D003-like case (100 km/h, TTC 7 s): ROBUSTLY SATISFIED in every branch; worst-case margin +1.01 s (dry) and +0.34 s (μ 0.5) for P0 with authority at effective control; at μ 0.5, 4 of 5 branches become PARAMETER-SENSITIVE with the 4 s bound.
- Two supplement cases use the stationary-point t1 bound.

**Permitted interpretation:** counterfactual comparisons; sensitivity to assumptions.

**Caveat:** P2 is not a production policy, and the D003-like case says nothing about D003 drivers' braking.

**References:** F7, F8, T6, TA2. **Claims:** L24, L25, L26, L27, L28.

### R-7. Descriptive lateral sequence after the switch (Ch. 9)

**Purpose.**
- Define the causal primary detector and compare it with alternatives.
- Report the sequence Manual_Start → steering-activity onset → lane crossing, and the indicator order.
- Report the torque audit, hazard distances at the two events, target-lane gaps (non-zero only) and the exposure null.

**Numbers:**
- MS → onset median 2.10 s (IQR 1.30–3.13; n = 491); detector medians 1.4–3.0 s.
- Onset → crossing 2.45 s (IQR 2.00–3.30; n = 477); onset before crossing in 98.3% of trials.
- MS → indicator 2.03 s; indicator before onset in 63% of trials.
- Torque–angle r ≈ −0.99.
- Hazard distance at onset: median 90 m (IQR 69–109, n = 434). At crossing: 43 m (IQR 26–58, n = 421).
- Next-lane lead vehicle at onset: median 33 m (non-zero values).
- Exposure: CIs include 0.

**Permitted interpretation:** a provisional description of signal events; authorship plausible but unverified.

**Caveat:**
- the timing depends on the detector;
- the indicator channel is undocumented;
- gap zeros are unresolved.

**References:** F9, T8, FA1. **Claims:** L09, L10, L11, L12, L13, L15, L16, L18, L35, L41 (assumed interval).

**L41 block** (cross-layer descriptive comparison with an assumed interval):
- **Claim ID:** L41 (SUPPORTED_WITH_QUALIFIER; comparison with an assumed interval). L09 stays PROVISIONAL for exact onset times.
- **Permitted wording (verbatim):** "Measured from TOR, the descriptive steering-angle activity onset in D003 falls predominantly after the upper end of the braking-delay interval assumed in R3B (1.15–3.0 s): 75% of onsets with the primary detector (n = 491; median 3.85 s, IQR 3.00–4.88), none before 1.15 s, and a majority for every onset detector compared (57–87%) and in every scenario cell (51–98%)."
- **Required qualifier (verbatim):** "Cross-layer descriptive comparison of a signal event with a modelling assumption. R3B t1 is an assumption, not an observed braking delay. Steering authorship is unverified (L11) and the exact fraction depends on the detector (L09). It does not hold against the 4 s supplementary bound (47% after 4.0 s). No braking timing is implied."
- **Location:** F9 (hatched band "R3B assumed braking-delay interval"; dashed 4.0 s line), T8 final panel, FA1. Discussed in Ch. 11 (§5, methodological topic) and referenced in Ch. 10.
- **Strongest forbidden interpretation (verbatim):** "Drivers steer after they brake; steering follows effective braking; drivers take longer than t1 to steer, so the t1 interval is validated / too short; longitudinal and lateral recovery are causally linked or sequential." The comparison is with an assumed interval.

### R-8. Integration boundary (Ch. 10)

**Purpose.**
- Present the identifiability map.
- Show that the links needed for a combined model are missing: human event → effective braking, braking magnitude, completion, lateral geometry.
- State why no combined model is built.

**Numbers:** class counts from the R5A §7 map (6 identified, 2 partially identified, 2 assumption-dependent, 7 not identifiable).

**Permitted interpretation:** absence of identified links.

**Caveat:** absent links are not evidence that the missing effects are small.

**Illustration:** the L41 comparison (R-7) shows that the lateral signal clock and the braking model's assumed clock are different quantities. It is referenced here as an illustration that no control bridge is identified, not as a link; the interval is an assumption.

**References:** F10, T9. **Claims:** L04, L29, L30; L41 (illustration only, assumed interval).

---

## 5. Discussion structure

L41 (a comparison with the R3B assumed interval) is used only for the methodological topic below and as an illustration in the integration topic. L42 is used only in Ch. 4 as a D003 scenario descriptor (station-consistent cells; d0_n1 excluded). It is not used in the discussion, and never to derive stopping distances or any real-driver claim.

| Topic | Core point | Evidence | Allowed wording | Overclaim to avoid |
|---|---|---|---|---|
| TTC as dominant separator | Within the model, TTC at TOR largely determines the label | L20; F5 | "In the braking-only model, TTC at the request separates robustly satisfied from robustly unsatisfied cases." | "A 7 s budget is sufficient for safe takeover." |
| Speed | Required time rises with speed | L21 | "Required braking time rises with initial speed in the model." | "High-speed takeovers are unsafe." |
| Friction-limited braking | μ = 0.5 caps deceleration and raises required time | L22 | "Under reduced (assumed) friction, …" | "Wet roads make takeovers fail." |
| a_max under μ limitation | When μg < a_max, the capability term never binds | L23; the friction relation (S27) | "Braking capability matters only where friction does not bind." | "Better brakes make takeover safe." |
| Conditional effect of automation support | Support before authority reduces required time only while the automation keeps authority | L24, L25; F8 | "Counterfactually, …" | "Systems should brake during transitions"; "P2 is safer" |
| t1 sensitivity | The assumed effective-braking onset dominates uncertainty width; the 4 s supplement shifts 10 labels | L26, L27 | "The classification is most sensitive to the assumed effective-braking onset." | "Human reaction time determines takeover safety." |
| Repeated exposure | A modest, associational decrease in mode-switch latency; lane crossing unchanged; steering timing unchanged (provisional) | L01, L34, L35 | "associated with repeated exposure" | "drivers learned"; "practice makes takeovers faster" |
| Why D003 braking channels do not identify driver braking | Scripted automation braking before and across the switch; no authority flag; unit conflict | L05, L06, L07 | "not identifiable from D003" | "D003 drivers braked late / weakly" |
| What the steering sequence adds | Descriptive lateral timing and hazard distances at signal events; the indicator mostly leads | L09, L10, L13, L15, L16 | "provisional", "signal event", "authorship unverified" | "steering reaction time", "intention time", "gap acceptance" |
| Steering-activity timing vs the assumed t1 interval (methodological) | Measured from TOR, descriptive lateral activity timing is often later than the upper edge of the R3B assumed braking-delay interval. This neither validates nor invalidates t1, which is an assumption. It does not show that drivers brake before they steer. It illustrates why the lateral signal clock and the longitudinal model clock cannot be merged without an identified control bridge | L41, L04, L11; F9 | "Measured from TOR, steering-angle activity onset falls predominantly after the R3B assumed braking-delay interval; this compares a signal event with a model assumption and implies no braking timing." | "t1 is validated / too short"; "drivers brake before they steer"; "steering follows effective braking" |
| Why braking and steering cannot be combined | No identified human → braking link; no completion event; no lateral geometry; steering provisional | L04, L29, L30; L41 as an illustration against the assumed interval; F10 | "not identifiable from this evidence" | combined score; "full recoverability" |
| Epistemic value of refusing unsupported synthesis | Fail-closed composition prevents treating HMI events as effective control and assumptions as findings | L03, L04, L30; T1; prior-art note (INCREMENTAL) | "a methodological discipline" | "a new assurance framework" |

---

## 6. Limitations

| Group | Limitation | Consequence | Claims |
|---|---|---|---|
| **A. Dataset observability** | No mode/authority flag (state constant 2.0) | Authority timing cannot be observed | L07 |
| | Multi-TOR (6 unresolved), missing TOR column (15), multiple Manual_Stop values (12) | Anchorable set 492 of 513; first-episode rule for handback | L14 |
| | Scenario cells bundle density, n-back, road, speed and automation behaviour | Condition effects are descriptive only | L36 |
| **B. Control authorship** | Brake and accelerator carry automation content across Manual_Start | Driver brake onset and **braking strength not identified** | L05, L06 |
| | **Steering authorship unverified** (angle channel cell-locked before TOR) | Steering timing is provisional | L11 |
| | Steering torque undocumented, and near-linear in the angle | Not usable | L12 |
| | Indicator undocumented | Order information only | L13 |
| **C. Vehicle / simulator identification** | No D003 vehicle or automation model | R3B uses generic external parameters; nothing is calibrated to D003 | L28 |
| **D. Human timing** | **t1 is an explicit assumption interval** (1.15–3.0 s; 4.0 s supplement) | It dominates the uncertainty width | L04, L26, L27 |
| | `t_button` is not a reaction time and not t1 | No empirical human anchor for R3B | L03, L04 |
| | **No probabilistic human model** | Bounds, not distributions or probabilities | L19, L29 |
| **E. Steering / geometry** | **No manoeuvre-completion metric** | No duration or recovery time | L10, L29 |
| | **Lane width and full lateral geometry not logged**; hazard reference point undocumented; station inconsistent in d0_n1 | No escape-path or clearance analysis; the distance at TOR is a scenario descriptor only | L15, L16, L17, L42 |
| | Gap zero semantics unresolved | Gap descriptors are non-zero values only | L18 |
| **F. Braking-model assumptions** | **t3 assumption** (0.3–1.2 s) | Part of the width | L26 |
| | **u = 1 model condition** (capability bound) | Not observed braking behaviour | L06, L19 |
| | **P2 is counterfactual**; a_sup 1–3 m/s² assumed | Branch effects are counterfactual | L24 |
| | **Authority-timing assumption** (at effective control, or f·t1) | Branch effects depend on it | L25 |
| | Stationary in-lane hazard; point mass; no jerk; drag neglected after effective control; μ 0.5 assumed | Scope of the necessary condition | L19, L22 |
| **G. Generalisability** | One simulator, one vehicle, 57 participants, TTC ≈ 7 s at TOR in D003 | Human findings are not population estimates; the non-critical regime only | L01, L02, L28 |
| | EV / one-pedal familiarity not represented | No familiarity claim | L33 |
| **H. Scope of recoverability** | Braking-only necessary condition | **No production safety claim**; no full recoverability; no combined model | L29, L30, L31 |

---

## 7. Future work

Each item follows from a limitation above.

| Priority | Item | Resolves | Needed before |
|---|---|---|---|
| 1 | **Explicit authority-state logging** in simulator studies (per-channel authority flags at TOR, switch and handback) | A, B (L07) | any human → braking link |
| 2 | **Driver-only brake and steering channels** (pedal and hand-wheel sensors separate from automation actuation) | B (L05, L06, L11) | identifying effective braking onset and strength, and steering authorship |
| 3 | **Simulator vehicle- and automation-model export** (parameters and controller configuration shipped with the data) | C | calibrating R3B to a studied vehicle |
| 4 | **Lane geometry and gap semantics** (lane width, hazard extent, a documented zero/sentinel convention) | E (L15–L18) | any lateral recovery analysis |
| 5 | **A manoeuvre-completion definition** agreed before analysis (for example a lateral-position and heading criterion) | E (L10) | steering duration or recovery time |
| 6 | **Validated longitudinal-lateral combined recovery analysis**, only after items 1–5 | H (L30) | — |
| 7 | **A probabilistic human model** only after observability improves (items 1–2), replacing the t1/t3 assumption intervals with measured distributions | D (L26) | any probability statement |

---

## 8. Abstract

### 8.1 Sentence traceability

Types:
- **context:** background; no claim.
- **claim:** must cite IDs.
- **limit:** states a boundary using permitted wording.

<!-- TRACE:abstract:START -->
| # | Type | Claims | Sentence |
|---|---|---|---|
| A1 | context | — | When conditionally automated driving reaches its limits, the driver may have to regain control before a hazard is reached. |
| A2 | claim | L19, L04 | This thesis asks when a braking-only recovery can satisfy a necessary stopping condition across speed, time-to-collision at the takeover request, road friction, braking capability and automation-transition behaviour, and how far public takeover data can anchor the human timing it depends on. |
| A3 | claim | L08, L05 | Human-response evidence comes from a public driving-simulator dataset (57 participants, 492 trials) whose event and control-channel semantics were audited first. |
| A4 | claim | L01, L02, L03 | The latency from takeover request to manual-mode switch (median 1.65 s) decreased modestly with repeated exposure within participants, and no recorded driver characteristic was associated with it after multiplicity correction. |
| A5 | limit | L05, L06, L07 | However, the brake and accelerator channels carry scripted automation content across the switch, so driver brake onset and braking strength are not identifiable. |
| A6 | claim | L04, L24, L25 | Vehicle parameters were therefore taken from documented sources, effective-braking onset and brake build-up were treated as explicit assumption intervals, and pre-authority automation behaviour as counterfactual hold, passive-drag and supported-deceleration branches. |
| A7 | claim | L19 | Exact interval bounds on the required braking time classify 58 of 150 scenario–branch cases as robustly satisfying the braking-only condition, 45 as robustly failing it and 47 as assumption-dependent. |
| A8 | claim | L20, L22, L23, L26 | Within this model, time-to-collision at the request dominates the classification, reduced friction removes the influence of braking capability, and the assumed effective-braking onset drives most uncertainty. |
| A9 | claim | L09, L10, L11 | A provisional, detector-checked description of the lateral sequence places steering-angle activity a median 2.10 s after the switch and lane crossing 2.45 s later; steering authorship is unverified. |
| A10 | limit | L04, L29, L30 | Because no link from observed human events to effective braking is identified, and no completion event or lateral geometry is logged, braking and steering cannot be combined into a validated recoverability model. |
| A11 | claim | L04, L19, L30 | The contribution is an evidence-graded, fail-closed analysis separating what a takeover dataset observes from what a braking-recoverability model must assume. |
<!-- TRACE:abstract:END -->

### 8.2 Assembled abstract

<!-- ABSTRACT:START -->
When conditionally automated driving reaches its limits, the driver may have to regain control before a hazard is reached. This thesis asks when a braking-only recovery can satisfy a necessary stopping condition across speed, time-to-collision at the takeover request, road friction, braking capability and automation-transition behaviour, and how far public takeover data can anchor the human timing it depends on. Human-response evidence comes from a public driving-simulator dataset (57 participants, 492 trials) whose event and control-channel semantics were audited first. The latency from takeover request to manual-mode switch (median 1.65 s) decreased modestly with repeated exposure within participants, and no recorded driver characteristic was associated with it after multiplicity correction. However, the brake and accelerator channels carry scripted automation content across the switch, so driver brake onset and braking strength are not identifiable. Vehicle parameters were therefore taken from documented sources, effective-braking onset and brake build-up were treated as explicit assumption intervals, and pre-authority automation behaviour as counterfactual hold, passive-drag and supported-deceleration branches. Exact interval bounds on the required braking time classify 58 of 150 scenario–branch cases as robustly satisfying the braking-only condition, 45 as robustly failing it and 47 as assumption-dependent. Within this model, time-to-collision at the request dominates the classification, reduced friction removes the influence of braking capability, and the assumed effective-braking onset drives most uncertainty. A provisional, detector-checked description of the lateral sequence places steering-angle activity a median 2.10 s after the switch and lane crossing 2.45 s later; steering authorship is unverified. Because no link from observed human events to effective braking is identified, and no completion event or lateral geometry is logged, braking and steering cannot be combined into a validated recoverability model. The contribution is an evidence-graded, fail-closed analysis separating what a takeover dataset observes from what a braking-recoverability model must assume.
<!-- ABSTRACT:END -->

---

## 9. Introduction contribution paragraph

<!-- TRACE:contribution:START -->
| # | Type | Claims | Sentence |
|---|---|---|---|
| P1 | context | — | This thesis makes five contributions. |
| P2 | claim | L05, L06, L07, L09, L11 | First, it audits the event and control-channel semantics of a public simulator takeover dataset, shows that its longitudinal control channels carry automation content across the switch to manual mode so that driver brake onset and braking strength are not identifiable, and derives a sensitivity-checked, provisional description of the steering sequence whose authorship remains unverified. |
| P3 | claim | L01, L02, L34 | Second, it reports the human-response findings that survive this audit: a modest within-participant decrease of the manual-mode switch latency associated with repeated exposure, not explained by short-term carry-over, no association with recorded driver characteristics after multiplicity correction, and no exposure association for the time to lane crossing. |
| P4 | claim | L04, L24, L25, L26 | Third, it assembles a provenance-graded parameter set for a braking-only takeover model that separates source-supported vehicle parameters from explicit assumptions about effective-braking onset, brake build-up, authority timing and automation support. |
| P5 | claim | L19, L27 | Fourth, it computes exact interval bounds on the required braking time, using corner enumeration protected by an analytic monotonicity guard and a fail-closed stationary-point escalation where monotonicity fails, and classifies scenarios with an explicit boundary tolerance. |
| P6 | claim | R5A-C5; L04, L29, L30 | Fifth, it applies an explicit separation of observed, source-supported, assumed, provisional and blocked quantities and declines to compose links that the evidence does not identify, which is offered as a methodological discipline rather than as a new assurance framework. |
<!-- TRACE:contribution:END -->

**Assembled:**

<!-- CONTRIBUTION:START -->
This thesis makes five contributions. First, it audits the event and control-channel semantics of a public simulator takeover dataset, shows that its longitudinal control channels carry automation content across the switch to manual mode so that driver brake onset and braking strength are not identifiable, and derives a sensitivity-checked, provisional description of the steering sequence whose authorship remains unverified. Second, it reports the human-response findings that survive this audit: a modest within-participant decrease of the manual-mode switch latency associated with repeated exposure, not explained by short-term carry-over, no association with recorded driver characteristics after multiplicity correction, and no exposure association for the time to lane crossing. Third, it assembles a provenance-graded parameter set for a braking-only takeover model that separates source-supported vehicle parameters from explicit assumptions about effective-braking onset, brake build-up, authority timing and automation support. Fourth, it computes exact interval bounds on the required braking time, using corner enumeration protected by an analytic monotonicity guard and a fail-closed stationary-point escalation where monotonicity fails, and classifies scenarios with an explicit boundary tolerance. Fifth, it applies an explicit separation of observed, source-supported, assumed, provisional and blocked quantities and declines to compose links that the evidence does not identify, which is offered as a methodological discipline rather than as a new assurance framework.
<!-- CONTRIBUTION:END -->

---

## 10. Conclusion

<!-- TRACE:conclusion:START -->
| # | Type | Claims | Sentence |
|---|---|---|---|
| K1 | claim | L19, L04 | This thesis examined when a braking-only recovery can satisfy a necessary stopping condition after a time-critical takeover request, and how far a public simulator takeover dataset can anchor the human timing on which that condition depends. |
| K2 | claim | L20, L21, L22, L23 | Within the braking-only model, time-to-collision at the request separates robustly satisfied from robustly unsatisfied cases, higher speed and reduced friction raise the required time, and braking capability matters only where friction does not bind. |
| K3 | claim | L24, L25, L26 | Counterfactual automation support before authority transfer shortens the required time only while the automation retains authority, and the assumed onset of effective braking accounts for most of the remaining uncertainty. |
| K4 | claim | L28, L27 | At the dataset-like operating point of 100 km/h and a time-to-collision of 7 s, the condition is robustly satisfied in every branch of the model, but at reduced friction this depends on the assumed upper bound of the effective-braking onset. |
| K5 | claim | L01, L14, L15, L16 | The dataset identifies the timing of the manual-mode switch and of lane crossing and the distance to the hazard, and it shows a modest association of the switch latency with repeated exposure. |
| K6 | limit | L05, L06, L09, L11 | It does not identify when or how strongly drivers brake, and its steering sequence remains a provisional description whose authorship is unverified. |
| K7 | limit | L29, L30, L31 | Consequently, no takeover-success prediction, production-system assessment or combined braking-and-steering recoverability model is established. |
| K8 | claim | L19, L29, L30 | The result remains useful because it states which scenario conditions leave braking alone insufficient or dependent on assumptions, and which observations, namely explicit authority-state logging, driver-only control channels and lane geometry, would be needed before a combined model could be defended. |
<!-- TRACE:conclusion:END -->

**Assembled:**

<!-- CONCLUSION:START -->
This thesis examined when a braking-only recovery can satisfy a necessary stopping condition after a time-critical takeover request, and how far a public simulator takeover dataset can anchor the human timing on which that condition depends. Within the braking-only model, time-to-collision at the request separates robustly satisfied from robustly unsatisfied cases, higher speed and reduced friction raise the required time, and braking capability matters only where friction does not bind. Counterfactual automation support before authority transfer shortens the required time only while the automation retains authority, and the assumed onset of effective braking accounts for most of the remaining uncertainty. At the dataset-like operating point of 100 km/h and a time-to-collision of 7 s, the condition is robustly satisfied in every branch of the model, but at reduced friction this depends on the assumed upper bound of the effective-braking onset. The dataset identifies the timing of the manual-mode switch and of lane crossing and the distance to the hazard, and it shows a modest association of the switch latency with repeated exposure. It does not identify when or how strongly drivers brake, and its steering sequence remains a provisional description whose authorship is unverified. Consequently, no takeover-success prediction, production-system assessment or combined braking-and-steering recoverability model is established. The result remains useful because it states which scenario conditions leave braking alone insufficient or dependent on assumptions, and which observations, namely explicit authority-state logging, driver-only control channels and lane geometry, would be needed before a combined model could be defended.
<!-- CONCLUSION:END -->

---

## 11. Claim-traceability check (against the 42-claim ledger)

| Text | Sentences | Traced | Notes |
|---|---|---|---|
| Abstract | 11 | 10 traced + 1 context | A9: "provisional, detector-checked … authorship unverified" (L09, L11 are PROVISIONAL). A8: "within this model" kept. Unchanged at freeze (see §12). |
| Contribution paragraph | 6 | 5 traced + 1 context | P6 has no positive ledger claim: it rests on the R5A contribution structure (C5), and the blocked claims L04, L29 and L30 it demonstrates. It is worded as a "methodological discipline", not a framework (prior-art check: INCREMENTAL). No "first" / "novel". Unchanged at freeze. |
| Conclusion | 8 | 8 traced | K4: "dataset-like operating point … of the model" (L28 qualifier). K5: hazard distance stated without "at steering onset", because that event is provisional. Unchanged at freeze. |
| Results blueprint | R-1 … R-8 | all subsections list claim IDs | L42 in R-1 (verbatim block; station-consistent cells); L41 in R-7 (verbatim block) and R-8 (illustration only; assumed interval). R-2 is marked as boundary statements (permitted wording of BLOCKED claims). |
| Discussion | 12 topics | all topics list claim IDs | L41 only in the methodological topic and as an illustration in the integration topic (assumed interval); L42 not used (a station-consistent scenario descriptor, Ch. 4 only) |

**Open items:** none. The two items previously listed here were resolved by the R5A amendment (D033) and are used as L41 (comparison with an assumed interval) and L42 (station-consistent cells).

---

## 12. Readiness and freeze

**R5B is frozen** (D034):
- the 14-chapter structure;
- figures F1–F10 and FA1–FA2;
- tables T1–T11 and TA1–TA3;
- the results blueprint R-1 … R-8;
- the discussion (12 topics);
- limitations A–H and future work;
- the abstract, contribution paragraph and conclusion.

It introduces no new scientific result and changes no claim status.

**Abstract, contribution paragraph and conclusion: unchanged at freeze.**
- **L41** would need its full qualifier (an assumed interval, detector range, the 4 s exception, no braking timing) to be stated safely. In a 300-word abstract or a one-line conclusion, that would either overload the sentence or invite a reading as braking timing.
- **L42** is a scenario descriptor for the station-consistent cells, not a result.
- The conclusion's K8 already states the missing control bridge.

**Next steps (not started):**
- **(A) Figure rendering** of F1–F10 and FA1–FA2, from stored outputs only.
- **(B) Full thesis drafting** under the ledger and this blueprint.

Changing a frozen element requires an explicit R5B reopening, and changing a claim requires an explicit R5A reopening.
