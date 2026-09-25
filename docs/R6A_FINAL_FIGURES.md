# R6A: final thesis figure set and manifest

**Status:** 2026-09-24. Rendered and frozen.
- **Figure set:** F1–F10 (main text) and FA1–FA2 (appendix) as frozen in R5B §2 (`docs/R5B_THESIS_BLUEPRINT.md`).
- **Rendering script:** `src/figures/r6a_thesis_figures.py`.
- **Manifest:** `thesis/figures/figure_manifest.json`.
- **Output directory:** `thesis/figures/` (formats: vector `.pdf` and preview `.png`).
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`.
- **Code commit at render:** `e6c215c90f42b0ce7603f11691f0cfb1748a2fb7`.
- **Byte determinism:** independent renders produce 100% byte-identical PDF and PNG SHA256 hashes.
- **Outputs tracked:** figures are not git-ignored.
- **Test suite:** `tests/test_r6a_figures.py`.

---

## 1. Frozen figure list summary

| ID | Title | Purpose | Placement | Source phase | Claims | Outputs |
|---|---|---|---|---|---|---|
| **F1** | Evidence / model architecture | Map inputs by layer and class to show which enter R3B and establish no D003 quantity enters it | Main (Ch. 1 / 3) | R5A §2; R3B §2–3 | L04, L19, L03 | PDF, PNG |
| **F2** | Event-semantic timeline | Display observable takeover events on a common clock to show distinct definitions and sequence | Main (Ch. 4) | R4V-D; R2B | L08, L09, L11, L13, L14 | PDF, PNG |
| **F3** | Brake/accelerator content across Manual_Start | Demonstrate automation content persists across switch, establishing unidentifiability | Main (Ch. 4) | R4V | L05, L06, L07 | PDF, PNG |
| **F4** | t_button vs exposure | Evaluate mode-switch latency association with exposure under participant fixed effects | Main (Ch. 5) | R2B | L01, L03, L34 | PDF, PNG |
| **F5** | R3B classification matrix | Classify main-domain cases across TTC, speed, friction, and counterfactual transition branches | Main (Ch. 8) | R3B (canonical outputs) | L19, L20, L21, L22, L24, L27, L28 | PDF, PNG |
| **F6** | T_required bounds vs TTC | Compute interval bounds on required braking time across branches, speed, and friction | Main (Ch. 8) | R3B (canonical outputs) | L19, L21, L22, L27 | PDF, PNG |
| **F7** | R3B parameter sensitivity | Evaluate one-at-a-time swing share of each R3B parameter on required braking time | Main (Ch. 8) | R3B (canonical outputs) | L23, L26 | PDF, PNG |
| **F8** | P0/P1/P2 comparison | Compare midpoint required braking time between transition branches and authority timing | Main (Ch. 8) | R3B (canonical outputs) | L24, L25 | PDF, PNG |
| **F9** | Steering-sequence timeline with the R3B assumption band | Evaluate descriptive lateral signal timing relative to assumed braking interval | Main (Ch. 9) | R4V-D; R3B t1 interval; R5A §10 (L41) | L09, L10, L11, L13, L27, L41 | PDF, PNG |
| **F10** | Identifiability / synthesis boundary | Map cross-layer quantities and links to explain why combined model is not identifiable | Main (Ch. 10) | R5A §7; R4 cross-layer links | L04, L29, L30 | PDF, PNG |
| **FA1** | Onset-detector sensitivity | Compare alternative steering onset detectors and robustness of interval comparison | Appendix | R4V-D; R5A §10 (L41) | L09, L11, L41 | PDF, PNG |
| **FA2** | Participant exposure slopes | Display distribution of individual OLS slopes of t_button against exposure | Appendix | R2B | L01 | PDF, PNG |

---

## 2. Per-figure specification and documentation

### F1: Evidence / model architecture (`F1_evidence_architecture`)

- **Purpose:** Group inputs by layer and evidence class to show which parameters enter the R3B model and establish that no D003 quantity enters it.
- **Outputs:** `thesis/figures/F1_evidence_architecture.pdf`, `thesis/figures/F1_evidence_architecture.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R5A §2; R3B §2–3
- **Sources:** `research/R5A_CLAIM_LEDGER.csv` (sha256 `75e250abc142…`); `docs/R5A_FINAL_CLAIM_LEDGER.md` (sha256 `5b0547e37294…`)
- **Claims:** L04 (BLOCKED), L19 (SUPPORTED_WITH_QUALIFIER), L03 (BLOCKED)
- **Qualification status:** qualified / supported
- **Required qualifiers:** no D003 human quantity enters the R3B model; t1 is an explicit assumption
- **Forbidden interpretations:** "t_button calibrates t1"; "the architecture is a validated system model"
- **Caption:** Evidence architecture of the thesis. Inputs are grouped by layer and tagged with their evidence class: observed, source-supported, explicit assumption, model condition, provisional or blocked. Arrows show only the inputs that enter the R3B braking-only model. No D003 human quantity enters it: the mode-switch latency t_button is not the model's effective-braking onset t1, which remains an explicit assumption interval.

### F2: Event-semantic timeline (`F2_event_semantic_timeline`)

- **Purpose:** Display D003 observable takeover events on a common clock to show their distinct operational definitions and sequence.
- **Outputs:** `thesis/figures/F2_event_semantic_timeline.pdf`, `thesis/figures/F2_event_semantic_timeline.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R4V-D (event table); R2B
- **Sources:** `results/R4V_steering_sequence/event_table.csv` (sha256 `0887b68c78b5…`)
- **Claims:** L08 (SUPPORTED_WITH_QUALIFIER), L09 (PROVISIONAL), L11 (PROVISIONAL), L13 (PROVISIONAL), L14 (SUPPORTED)
- **Qualification status:** contains PROVISIONAL claims: provisional labels shown
- **Required qualifiers:** steering-activity and indicator onsets are provisional; steering authorship unverified; indicator channel undocumented
- **Forbidden interpretations:** "Manual_Start is effective control"; "lane crossing is manoeuvre completion"; "Manual_Stop is recovery completion"
- **Caption:** D003 takeover events on a common clock (time from TOR, s): median (marker) and interquartile range (bar) across anchorable trials, with the number of trials per event. Manual_Start is the documented switch to manual mode. Steering-activity onset and left-indicator onset are derived signal events: provisional, with steering authorship unverified and the indicator channel undocumented. Lane crossing is the validated crossing event; Manual_Stop is the protocol handback. None of these events is effective braking or manoeuvre completion.

### F3: Brake/accelerator content across Manual_Start (`F3_longitudinal_channels_across_manual_start`)

- **Purpose:** Demonstrate that scripted automation content continues across Manual_Start, rendering driver brake onset and strength unidentifiable.
- **Outputs:** `thesis/figures/F3_longitudinal_channels_across_manual_start.pdf`, `thesis/figures/F3_longitudinal_channels_across_manual_start.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R4V
- **Sources:** `results/R4V_channel_authorship/trial_features.csv` (sha256 `0190ac9e72f8…`)
- **Claims:** L05 (BLOCKED), L06 (BLOCKED), L07 (BLOCKED)
- **Qualification status:** boundary figure (permitted wording of BLOCKED claims)
- **Required qualifiers:** channel content, not driver input; driver brake onset and strength not identifiable
- **Forbidden interpretations:** "drivers braked at Manual_Start"; "driver braking strength"
- **Caption:** Brake and accelerator channel content around Manual_Start (MS), by scenario cell (dX_nY: traffic density X, n-back level Y). (a) Share of trials with the brake channel active at MS. (b) Brake release after MS in trials braking at MS: median and interquartile range (s). (c) Share of trials with the accelerator channel active at MS. Scripted automation content continues across the switch to manual mode, so driver brake onset and braking strength are not identifiable from these channels.

### F4: t_button vs exposure (`F4_t_button_vs_exposure`)

- **Purpose:** Evaluate within-participant mode-switch latency association with repeated exposure under participant fixed effects.
- **Outputs:** `thesis/figures/F4_t_button_vs_exposure.pdf`, `thesis/figures/F4_t_button_vs_exposure.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R2B
- **Sources:** `results/R2B_repeated_exposure/exposure_summary.csv` (sha256 `b11b6e97a0ce…`); `results/R2B_repeated_exposure/exposure_models.csv` (sha256 `c2c21145b440…`)
- **Claims:** L01 (SUPPORTED_WITH_QUALIFIER), L03 (BLOCKED), L34 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** associational; t_button is a mode-switch latency, not a reaction time
- **Forbidden interpretations:** "drivers learned"; "reaction time decreases"
- **Caption:** Mode-switch latency t_button (TOR → Manual_Start, s) by exposure (chronological trial position 1–9 within participant). (a) Median and interquartile range across trials at each exposure. (b) Participant-centred median (trial value minus that participant's median). The participant fixed-effects model with scenario-cell controls gives −0.033 s per exposure (95% CI −0.058 to −0.007). The association is not a causal learning effect, and t_button is a mode-switch latency, not a reaction time. TOR → validated lane crossing shows no clear linear exposure association (not shown).

### F5: R3B classification matrix (`F5_r3b_classification_matrix`)

- **Purpose:** Classify main-domain cases under necessary stopping conditions across TTC, speed, friction, and counterfactual transition branches.
- **Outputs:** `thesis/figures/F5_r3b_classification_matrix.pdf`, `thesis/figures/F5_r3b_classification_matrix.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R3B (canonical outputs, code a4f2cc4)
- **Sources:** `results/R3B_braking_bounds/results.csv` (sha256 `9762d076eb7c…`)
- **Claims:** L19 (SUPPORTED_WITH_QUALIFIER), L20 (SUPPORTED_WITH_QUALIFIER), L21 (SUPPORTED_WITH_QUALIFIER), L22 (SUPPORTED_WITH_QUALIFIER), L24 (SUPPORTED_WITH_QUALIFIER), L27 (SUPPORTED_WITH_QUALIFIER), L28 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** within the braking-only model; branches are counterfactual model branches; t1 = 4 s outline is sensitivity only
- **Forbidden interpretations:** "safe / unsafe"; "takeover succeeds / fails"; "observed D003 automation modes"
- **Caption:** Braking-only classification of the 150 main-domain cases of the R3B model, by TTC at TOR, initial speed, road friction μ and counterfactual transition branch. ROBUSTLY SATISFIED: worst-case time margin > +0.01 s. ROBUSTLY UNSATISFIED: best-case margin < −0.01 s. PARAMETER-SENSITIVE: otherwise. No case lies within ±0.01 s of the boundary. Outlined cells change from ROBUSTLY SATISFIED to PARAMETER-SENSITIVE when the assumed t1 upper bound is raised to 4 s (sensitivity only). Labels are within-model necessary-condition results, not safety statements. The branches are counterfactual model branches, not observed D003 automation modes.

### F6: T_required bounds vs TTC (`F6_r3b_t_required_bounds`)

- **Purpose:** Compute interval bounds on required braking time T_required^brake across branches, speed, and friction compared to scenario TTC.
- **Outputs:** `thesis/figures/F6_r3b_t_required_bounds.pdf`, `thesis/figures/F6_r3b_t_required_bounds.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R3B (canonical outputs)
- **Sources:** `results/R3B_braking_bounds/t_required_bounds.csv` (sha256 `a98bff86fc74…`)
- **Claims:** L19 (SUPPORTED_WITH_QUALIFIER), L21 (SUPPORTED_WITH_QUALIFIER), L22 (SUPPORTED_WITH_QUALIFIER), L27 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** within-model bounds, not confidence intervals; t1 = 4 s extension is sensitivity only
- **Forbidden interpretations:** "required time is a measured driver quantity"; "safe TTC"
- **Caption:** Bounds on the required braking time T_required^brake (s) in the R3B model, per counterfactual branch, initial speed and road friction μ, computed with the guarded corner method (stationary-point t1 bound where required). Solid bars: main-domain interval. Hatched extension: upper bound with the assumed t1 upper end raised to 4 s (sensitivity only). Dotted lines: the TTC values of the scenario grid; a case is parameter-sensitive when its TTC lies within the interval. The bounds are interval bounds under stated assumptions, not confidence intervals.

### F7: R3B parameter sensitivity (`F7_r3b_sensitivity`)

- **Purpose:** Evaluate one-at-a-time swing share of each R3B parameter on required braking time interval width.
- **Outputs:** `thesis/figures/F7_r3b_sensitivity.pdf`, `thesis/figures/F7_r3b_sensitivity.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R3B (canonical outputs)
- **Sources:** `results/R3B_braking_bounds/sensitivity.csv` (sha256 `56b011387dc7…`)
- **Claims:** L23 (SUPPORTED_WITH_QUALIFIER), L26 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** t1, t3, a_sup and f_auth are assumptions; one-at-a-time shares, within-model
- **Forbidden interpretations:** "human reaction time determines takeover safety"; "better brakes make takeover safe"
- **Caption:** One-at-a-time swing share of each R3B parameter in the T_required^brake interval: the range across speed and branch cases, shown separately for μ = 1.0 and μ = 0.5. The t1 assumption interval is the main contributor. a_max contributes nothing where friction binds (μ = 0.5). t1, t3, a_sup and f_auth are explicit assumptions; t2, a_max and a_drag are source-supported.

### F8: P0/P1/P2 comparison (`F8_transition_branch_comparison`)

- **Purpose:** Compare midpoint required braking time between counterfactual transition branches and authority timing assumptions.
- **Outputs:** `thesis/figures/F8_transition_branch_comparison.pdf`, `thesis/figures/F8_transition_branch_comparison.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R3B (canonical outputs)
- **Sources:** `results/R3B_braking_bounds/policy_comparison.csv` (sha256 `3a1ea7d97a61…`)
- **Claims:** L24 (SUPPORTED_WITH_QUALIFIER), L25 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** counterfactual model branches; a_sup and authority timing are assumptions
- **Forbidden interpretations:** "P2 is safer"; "production systems behave like P2"; "observed D003 automation"
- **Caption:** Midpoint change in T_required^brake (s) relative to P0 with authority at effective control, for each counterfactual transition branch, by initial speed and road friction μ. Before authority transfer, P0 holds speed, P1 applies passive drag and P2 applies an assumed supported deceleration of 1–3 m/s². 'Uncertain' authority places the transfer at f·t1 with f ∈ [0, 1]. These are counterfactual model branches, not observed D003 automation or production policies.

### F9: Steering-sequence timeline with the R3B assumption band (`F9_steering_sequence_vs_assumed_interval`)

- **Purpose:** Evaluate descriptive steering onset and lateral sequence timing relative to the R3B assumed braking-delay interval.
- **Outputs:** `thesis/figures/F9_steering_sequence_vs_assumed_interval.pdf`, `thesis/figures/F9_steering_sequence_vs_assumed_interval.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R4V-D; R3B t1 interval; R5A §10 (L41)
- **Sources:** `results/R4V_steering_sequence/event_table.csv` (sha256 `0887b68c78b5…`)
- **Claims:** L09 (PROVISIONAL), L10 (PROVISIONAL), L11 (PROVISIONAL), L13 (PROVISIONAL), L27 (SUPPORTED_WITH_QUALIFIER), L41 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** contains PROVISIONAL claims: provisional labels shown
- **Required qualifiers:** R3B assumed braking-delay interval is a model assumption, not observed; steering and indicator events are provisional; steering authorship unverified; no braking timing implied
- **Forbidden interpretations:** "driver braking time"; "measured reaction time"; "observed braking delay"; "steering follows effective braking"; "t1 is validated / too short"
- **Caption:** Descriptive takeover signal events per trial on a common clock from TOR (s). Trials are sorted by steering-angle activity onset (primary detector; trials with an onset). Markers show Manual_Start, steering-angle activity onset, left-indicator onset and validated lane crossing. The hatched band is the R3B assumed braking-delay interval (1.15–3.0 s), a model assumption and not an observed quantity. The dashed line is the R3B supplementary upper bound (4.0 s; sensitivity only). Measured from TOR, the steering-angle activity onset falls predominantly after the upper end of the assumed interval: 75% of onsets with the primary detector, and a majority for every onset detector compared. It does not fall predominantly after the 4 s supplementary bound. Steering and indicator events are provisional descriptive signals, and steering authorship is unverified; no braking timing is implied.

### F10: Identifiability / synthesis boundary (`F10_identifiability_boundary`)

- **Purpose:** Map cross-layer quantities and links to explain why a combined braking-and-steering recoverability model is not identifiable.
- **Outputs:** `thesis/figures/F10_identifiability_boundary.pdf`, `thesis/figures/F10_identifiability_boundary.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R5A §7; R4 cross-layer links; R5A ledger
- **Sources:** `docs/R5A_FINAL_CLAIM_LEDGER.md` (sha256 `5b0547e37294…`); `research/R4_CROSS_LAYER_LINKS.csv` (sha256 `9c48d586ee55…`)
- **Claims:** L04 (BLOCKED), L29 (BLOCKED), L30 (BLOCKED)
- **Qualification status:** boundary figure (permitted wording of BLOCKED claims)
- **Required qualifiers:** absent links are not evidence that missing effects are small
- **Forbidden interpretations:** "combined recoverability model"; "recoverability score"
- **Caption:** Identifiability of the quantities and links that a combined braking-and-steering recoverability model would need. Node borders and fills give each quantity's identifiability class (R5A); edge styles give each cross-layer link's class (R4). The links from observed D003 events to effective braking, and from lane crossing or handback to manoeuvre completion, are not identifiable, so no combined model is built. Absent links are not evidence that the missing effects are small.

### FA1: Onset-detector sensitivity (`FA1_onset_detector_sensitivity`)

- **Purpose:** Compare alternative steering onset detector definitions and evaluate robustness of the assumed-interval comparison.
- **Outputs:** `thesis/figures/FA1_onset_detector_sensitivity.pdf`, `thesis/figures/FA1_onset_detector_sensitivity.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R4V-D; R5A §10 (L41)
- **Sources:** `results/R4V_steering_sequence/onset_detector_sensitivity.csv` (sha256 `c695c2e02d16…`); `results/R4V_steering_sequence/event_table.csv` (sha256 `0887b68c78b5…`)
- **Claims:** L09 (PROVISIONAL), L11 (PROVISIONAL), L41 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** contains PROVISIONAL claims: provisional labels shown
- **Required qualifiers:** provisional descriptive signal; steering authorship unverified; R3B assumed braking-delay interval is a model assumption
- **Forbidden interpretations:** "steering reaction time"; "driver braking time"
- **Caption:** Steering-activity onset by detector. (a) Manual_Start → onset (s): median and interquartile range for each of the six detectors compared. (b) Share of onsets, measured from TOR, before, within and after the R3B assumed braking-delay interval (1.15–3.0 s), a model assumption. Onset timing depends on the detector (medians 1.4–3.0 s after Manual_Start). A majority of onsets falls after the assumed interval for every detector (57–87%). Provisional descriptive signal; steering authorship unverified.

### FA2: Participant exposure slopes (`FA2_participant_exposure_slopes`)

- **Purpose:** Show the distribution of individual ordinary-least-squares slopes of t_button against exposure.
- **Outputs:** `thesis/figures/FA2_participant_exposure_slopes.pdf`, `thesis/figures/FA2_participant_exposure_slopes.png`
- **Generation command:** `python -m src.figures.r6a_thesis_figures thesis/figures`
- **Source phase:** R2B
- **Sources:** `results/R2B_repeated_exposure/participant_slopes.csv` (sha256 `c0aac6d23746…`)
- **Claims:** L01 (SUPPORTED_WITH_QUALIFIER)
- **Qualification status:** qualified / supported
- **Required qualifiers:** descriptive per-participant slopes; associational
- **Forbidden interpretations:** "individual learning rates"
- **Caption:** Per-participant ordinary-least-squares slopes of t_button against exposure (s per exposure), one point per participant. Descriptive; the pooled association is reported in F4 and is not a causal learning effect.

---

## 3. Governance and invariants

- **Single source of truth:** All figure specifications, sources, claims, qualifiers, forbidden interpretations, and captions are defined in `src/figures/r6a_thesis_figures.py:FIGURES` and recorded in `thesis/figures/figure_manifest.json`.
- **Caption drift prevention:** Tested by `tests/test_r6a_figures.py`. Captions in this document and the manifest must match exactly.
- **Claim boundary preservation:** Boundary figures (F3, F10) explicitly treat BLOCKED claims (L04, L05, L06, L07, L29, L30) as unidentifiability limits, never positive empirical findings.
- **Model assumption distinction (L41):** In F9 and FA1, the 1.15–3.0 s interval is strictly qualified as the "R3B assumed braking-delay interval", a model assumption, never as measured driver braking time.
- **Hazard distance scope (L42):** L42 is table/text only (T11 in Chapter 4; station-consistent cells, d0_n1 excluded) and is not rendered as a standalone figure.
- **Exposure association vs learning (F4/L34):** F4 includes L34 noting no linear exposure association for lane crossing; the modest t_button slope is strictly associational and not causal learning.
