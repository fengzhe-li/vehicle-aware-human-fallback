# R6B: Full Thesis Drafting Documentation

**Status:** Complete
**Date:** 2026-09-24
**Branch:** `audit/research-baseline-restructure`
**Master Document:** `thesis/draft/thesis.md` (28,801 words)
**Verification Suite:** `tests/test_r6b_thesis.py` (12/12 passed)

---

## 1. Executive Summary

Phase R6B completes the full drafting of the academic thesis in academic prose, converting the frozen R5A claim ledger (`research/R5A_CLAIM_LEDGER.csv`), the frozen R5B thesis blueprint (`docs/R5B_THESIS_BLUEPRINT.md`), and the frozen R6A figure set (`thesis/figures/`) into a comprehensive, fully articulated monograph.

### Core Drafting Invariants Maintained
- **Zero New Scientific Results:** No new computations, analyses, parameter sweeps, or synthetic risk scores were introduced.
- **Zero Claim Status Changes:** All 42 claims maintain their exact R5A ledger status (1 SUPPORTED, 19 SUPPORTED_WITH_QUALIFIER, 6 PROVISIONAL, 11 BLOCKED, 5 WITHDRAWN).
- **Zero Placeholder Text:** Every chapter is drafted in complete academic prose; no "this section will discuss" or placeholder bullet points exist.
- **Strict Grounding:** Every substantive statement is directly grounded in an R5A claim ID ($L01$–$L42$) or parameter provenance identifier (P01–P26).
- **Exact Abstract, Contribution, and Conclusion:** The abstract (298 words), contribution paragraph, and conclusion verbatim match the traced text in `docs/R5B_THESIS_BLUEPRINT.md`.
- **Epistemic Refusal of Unsupported Synthesis:** Braking-only recovery bounds and descriptive lateral sequences are reported with rigorous boundaries, explicitly refusing to construct an unverified combined "safety envelope" across unobservable control bridges.

---

## 2. Thesis Structure and Word Counts

The master thesis is assembled in `thesis/draft/thesis.md`, constructed from 17 modular chapter and front-matter documents in `thesis/draft/`:

| File | Chapter / Section Title | Word Count | Character Count | Figures Placed | Tables Placed | Key Grounding Claims |
|---|---|---|---|---|---|---|
| `front_matter.md` | Front Matter (Title, Abstract, Abbreviations, Contributions) | 767 | 5,611 | — | — | L01–L09, L11, L19, L24, L26, L30, L34 |
| `ch01_introduction.md` | Chapter 1: Introduction & Research Questions | 1,646 | 12,679 | F1 | — | L04, L05, L06, L07, L19, L24, L27, L29, L30 |
| `ch02_background.md` | Chapter 2: Background and Related Work | 2,096 | 15,711 | — | — | S01–S31, A01–A07 (Prior Art) |
| `ch03_framework.md` | Chapter 3: Evidence Framework and Research Design | 1,015 | 7,661 | — | T1 | L04, L29, L30 |
| `ch04_dataset_audit.md` | Chapter 4: Dataset and Event-Semantics Audit (D003) | 2,231 | 15,441 | F2, F3 | T2, T3, T11 | L05, L06, L07, L08, L12, L14, L17, L18, L42 |
| `ch05_human_response.md` | Chapter 5: Human Response Analysis | 1,287 | 9,380 | F4 | T4 | L01, L02, L03, L14, L34 |
| `ch06_vehicle_automation.md` | Chapter 6: Vehicle and Automation Evidence | 2,185 | 15,541 | — | T5 | L04, L24, L25 |
| `ch07_braking_model.md` | Chapter 7: Braking-Only Recoverability Model & Interval Method | 1,977 | 14,040 | — | T6 | L19, L27, L40 |
| `ch08_braking_results.md` | Chapter 8: Braking-Only Results | 2,230 | 15,938 | F5, F6, F7, F8 | T7 | L19–L28 |
| `ch09_steering_sequence.md` | Chapter 9: Descriptive Steering Sequence | 2,009 | 14,215 | F9 | T8 | L09, L10, L11, L12, L13, L15, L16, L18, L35, L41 |
| `ch10_integration_boundary.md` | Chapter 10: Integration Boundary | 1,640 | 11,947 | F10 | T9 | L04, L29, L30, L41 |
| `ch11_discussion.md` | Chapter 11: Discussion (12 Topics) | 1,615 | 12,025 | — | — | L01, L03–L07, L09–L11, L13, L15, L16, L19–L28, L30, L34, L35, L41 |
| `ch12_limitations.md` | Chapter 12: Limitations (Groups A–H) | 1,314 | 9,288 | — | T10 | L01–L07, L10–L19, L22, L24–L31, L33, L36, L37, L42 |
| `ch13_future_work.md` | Chapter 13: Future Work (Priorities 1–7) | 770 | 6,234 | — | — | L05–L07, L10, L11, L15–L18, L26, L28, L30 |
| `ch14_conclusion.md` | Chapter 14: Conclusion & Answers to RQs | 1,162 | 8,241 | — | — | K1–K8, L01, L02, L04–L11, L14–L28, L29, L30, L31, L34, L35, L40 |
| `appendices.md` | Appendices (Ledger, Bounds Pivot, Withdrawn, Reproduction) | 3,779 | 24,383 | FA1, FA2 | TA1, TA2, TA3 | L01–L42 |
| `references.md` | References (Comprehensive Bibliography) | 1,062 | 7,923 | — | — | S01–S31 (excl. S29/S30), A01–A07 |
| **Total Master Thesis** | `thesis/draft/thesis.md` | **28,801** | **206,197** | **12 (100%)** | **14 (100%)** | **42 / 42 (100%)** |

---

## 3. Claim Traceability Matrix

Every claim in `research/R5A_CLAIM_LEDGER.csv` ($L01$ to $L42$) is mapped to its primary discussion chapter and supporting evidence:

| Claim ID | Status | Host Chapter(s) | Section(s) | Key Grounding Statement / Role in Thesis |
|---|---|---|---|---|
| **L01** | SUPPORTED_WITH_QUALIFIER | Ch. 5, Ch. 11, App. A | §5.2, §11.7, Table TA1 | Mode-switch latency $t_{button}$ decreases modestly with repeated exposure ($-0.033\text{ s/exposure}$). |
| **L02** | SUPPORTED_WITH_QUALIFIER | Ch. 5, App. A | §5.3, Table TA1 | No participant characteristic (driving experience, ADAS use) survived Holm correction. |
| **L03** | BLOCKED | Ch. 4, Ch. 5, Ch. 10 | §4.2, §5.1, §10.2 | $t_{button}$ is an electronic HMI event; blocked as reaction time or time to effective control. |
| **L04** | BLOCKED | Ch. 6, Ch. 7, Ch. 10 | §6.1, §7.2, §10.2 | $t_{button}$ cannot anchor $t_1$; $t_1$ remains an explicit assumption interval ($[1.15, 3.00]\text{ s}$). |
| **L05** | BLOCKED | Ch. 4, Ch. 10, Ch. 11 | §4.3, §10.2, §11.8 | Driver brake onset is unidentifiable; scripted automation braking straddles mode switch. |
| **L06** | BLOCKED | Ch. 4, Ch. 10, Ch. 11 | §4.3, §10.2, §11.8 | Driver braking strength is unidentifiable; unit conflicts and automation saturation. |
| **L07** | BLOCKED | Ch. 4, Ch. 6, Ch. 10 | §4.2, §6.1, §10.2 | Longitudinal authority does not transfer at MS; `state = 2.0` identically constant. |
| **L08** | SUPPORTED_WITH_QUALIFIER | Ch. 4, Ch. 10, App. A | §4.2, §10.1, Table TA1 | Manual_Start is documented design intent enabling manual inputs; lateral signals consistent. |
| **L09** | PROVISIONAL | Ch. 9, Ch. 11, App. A | §9.1, §11.9, Table TA1 | Steering onset occurs median $2.10\text{ s}$ after MS (primary); detector-dependent ($1.4\text{--}3.0\text{ s}$). |
| **L10** | PROVISIONAL | Ch. 9, Ch. 10, App. A | §9.3, §10.2, Table TA1 | Lane crossing follows steering onset by median $2.45\text{ s}$; not manoeuvre completion. |
| **L11** | PROVISIONAL | Ch. 9, Ch. 10, Ch. 11 | §9.2, §10.1, §11.9 | Steering authorship is plausible but unverified (PLAUSIBLE_BUT_UNVERIFIED). |
| **L12** | BLOCKED | Ch. 9, Ch. 10, App. A | §9.2, §10.1, Table TA1 | Steering torque channel is collinear with angle ($r \approx -0.99$); blocked as driver effort. |
| **L13** | PROVISIONAL | Ch. 9, Ch. 11, App. A | §9.3, §11.9, Table TA1 | Turn indicator activates median $2.03\text{ s}$ after MS; precedes steering in 63% of trials. |
| **L14** | SUPPORTED | Ch. 4, Ch. 9, App. A | §4.2, §9.3, Table TA1 | TOR to validated lane crossing median $6.40\text{ s}$; validated physical lane line crossing. |
| **L15** | SUPPORTED_WITH_QUALIFIER | Ch. 9, Ch. 10, App. A | §9.4, §10.2, Table TA1 | Distance to construction at steering onset median $90\text{ m}$; reference point undocumented. |
| **L16** | SUPPORTED_WITH_QUALIFIER | Ch. 9, Ch. 10, App. A | §9.4, §10.2, Table TA1 | Distance to construction at lane crossing median $43\text{ m}$; lateral clearance unrecorded. |
| **L17** | SUPPORTED_WITH_QUALIFIER | Ch. 4, Ch. 10, App. A | §4.5, §10.1, Table TA1 | Hazard station reconstructed along road in 8 of 9 cells (across-trial SD $\le 1.7\text{ m}$). |
| **L18** | PROVISIONAL | Ch. 9, Ch. 10, App. A | §9.4, §10.1, Table TA1 | Next-lane lead vehicle gap median $33\text{ m}$; zero semantics unresolved (sentinels). |
| **L19** | SUPPORTED_WITH_QUALIFIER | Ch. 7, Ch. 8, Ch. 14 | §7.1, §8.1, §14.1 | 150-case braking classification: 58 satisfied, 47 sensitive, 45 unsatisfied. |
| **L20** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.2, §11.1, §14.1 | TTC at TOR dominates classification within the model. |
| **L21** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.2, §11.2, §14.1 | Required braking time rises with initial cruising speed (midpoint $3.74\text{ to }4.94\text{ s}$). |
| **L22** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.2, §11.3, §14.1 | Low friction ($\mu = 0.5$) caps deceleration at $4.905\text{ m/s}^2$ and raises required time. |
| **L23** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.3, §11.4, §14.1 | Braking capability $a_{max}$ matters only where friction does not bind ($\eta = 0$ at $\mu = 0.5$). |
| **L24** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.4, §11.5, §14.1 | Supported braking (P2) reduces midpoint required time by $0.68\text{--}1.12\text{ s}$. |
| **L25** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.4, §11.5, §14.1 | Pre-control behaviour matters only while automation keeps authority. |
| **L26** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 11, Ch. 14 | §8.5, §11.6, §14.1 | $t_1$ assumption interval drives 33%–77% of required-time uncertainty width ($2.2\text{--}3.5\text{ s}$). |
| **L27** | SUPPORTED_WITH_QUALIFIER | Ch. 7, Ch. 8, Ch. 14 | §7.4, §8.6, §14.1 | Supplementary $t_1 = 4.0\text{ s}$ upper bound shifts 10 cases to parameter-sensitive. |
| **L28** | SUPPORTED_WITH_QUALIFIER | Ch. 8, Ch. 14, App. A | §8.6, §14.1, Table TA1 | D003-like case ($100\text{ km/h}$, TTC 7 s) is robustly satisfied in all model branches. |
| **L29** | BLOCKED | Ch. 10, Ch. 12, Ch. 14 | §10.4, §12.2, §14.2 | Full takeover recoverability / safety envelope is blocked. |
| **L30** | BLOCKED | Ch. 10, Ch. 11, Ch. 14 | §10.4, §11.11, §14.2 | Combined longitudinal-lateral recoverability synthesis is blocked. |
| **L31** | BLOCKED | Ch. 10, Ch. 12, Ch. 14 | §10.4, §12.2, §14.2 | Production automated driving system safety rating is blocked. |
| **L32** | BLOCKED | Ch. 5, Ch. 11, App. A | §5.2, §11.7, Table TA1 | Causal learning / practice causes faster takeover is blocked. |
| **L33** | BLOCKED | Ch. 12, App. A | §12.1, Table TA1 | EV / one-pedal driving familiarity effect is blocked. |
| **L34** | SUPPORTED_WITH_QUALIFIER | Ch. 5, Ch. 9, App. A | §5.2, §9.5, Table TA1 | TOR to validated lane crossing shows zero linear association with exposure ($+0.09\text{ s}$). |
| **L35** | PROVISIONAL | Ch. 9, Ch. 11, App. A | §9.5, §11.7, Table TA1 | Steering timing (onset and execution) shows zero linear association with exposure. |
| **L36** | WITHDRAWN | Ch. 4, Ch. 12, App. C | §4.1, §12.1, Table TA3 | Condition (density / n-back) causal factorial claims withdrawn (aliased cells). |
| **L37** | WITHDRAWN | Ch. 4, Ch. 10, App. C | §4.2, §10.2, Table TA3 | $T_{stable}$ as human stabilisation withdrawn (81% post-handback under automation). |
| **L38** | WITHDRAWN | Ch. 4, Ch. 12, App. C | §4.3, §12.1, Table TA3 | Control-channel correction counts withdrawn (mixed channels, post-handback). |
| **L39** | WITHDRAWN | Ch. 4, Ch. 12, App. C | §4.5, §12.1, Table TA3 | Derived collision proxy (1.17%) withdrawn (unvalidated lateral geometry). |
| **L40** | WITHDRAWN | Ch. 7, Ch. 14, App. C | §7.2, §14.2, Table TA3 | Closed-form kinematic novelty withdrawn (standard Newtonian kinematics). |
| **L41** | SUPPORTED_WITH_QUALIFIER | Ch. 9, Ch. 10, Ch. 11 | §9.6, §10.3, §11.10 | Steering onset predominantly after assumed $t_1$ window (75.4% > 3.0 s; descriptive comparison). |
| **L42** | SUPPORTED_WITH_QUALIFIER | Ch. 4, App. A | §4.5, Table TA1 | Distance at TOR median 178 m in 435 station-consistent trials; d0_n1 strictly excluded. |

---

## 4. Figure and Table Placement Register

All 12 figures and 14 tables frozen in R5B are placed in their designated chapters:

### Figure Register
- **Figure F1:** Chapter 1 (§1.4) — Causal Layer Architecture and Evidence Classifications.
- **Figure F2:** Chapter 4 (§4.2) — Event-Semantic Timeline in D003.
- **Figure F3:** Chapter 4 (§4.3) — Longitudinal Channel Automation Straddle.
- **Figure F4:** Chapter 5 (§5.2) — Mode-Switch Latency $t_{button}$ vs Repeated Exposure.
- **Figure F5:** Chapter 8 (§8.1) — R3B 150-Case Classification Matrix.
- **Figure F6:** Chapter 8 (§8.2) — Required Braking Time Bounds vs Scenario TTC Budgets.
- **Figure F7:** Chapter 8 (§8.5) — Parameter Sensitivity Swing Share Tornado.
- **Figure F8:** Chapter 8 (§8.4) — Counterfactual Transition Policy Comparison and Authority Timing.
- **Figure F9:** Chapter 9 (§9.6) — Descriptive Steering Timeline with R3B Assumed $t_1$ Band.
- **Figure F10:** Chapter 10 (§10.1) — Final Cross-Layer Identifiability Map.
- **Figure FA1:** Appendix D (§D.1) — Onset Detector Sensitivity and $t_1$ Interval Share.
- **Figure FA2:** Appendix D (§D.2) — Participant Exposure Regression Slopes.

### Table Register
- **Table T1:** Chapter 3 (§3.2) — Evidence Classification Taxonomy.
- **Table T2:** Chapter 4 (§4.2) — D003 Event Semantics and Observability.
- **Table T3:** Chapter 4 (§4.3) — Control-Channel Authorship Classification.
- **Table T4:** Chapter 5 (§5.2) — Human Response Exposure and Covariate Regression Results.
- **Table T5:** Chapter 6 (§6.1) — Parameter Provenance Registry.
- **Table T6:** Chapter 7 (§7.5) — R3B Model Frozen Configuration.
- **Table T7:** Chapter 8 (§8.1) — R3B Classification Summary Matrix.
- **Table T8:** Chapter 9 (§9.3, §9.6) — Descriptive Steering-Sequence Metrics & Detector Sensitivity.
- **Table T9:** Chapter 10 (§10.1) — Final Cross-Layer Identifiability Matrix.
- **Table T10:** Chapter 12 (§12.1) — Analytical Limitations and Blocked Variables Catalogue.
- **Table T11:** Chapter 4 (§4.5) — Hazard Station Reconstruction & Distance at TOR by Cell.
- **Table TA1:** Appendix A — Complete 42-Claim Ledger.
- **Table TA2:** Appendix B — Full 30-Configuration Classification Pivot and Interval Bounds.
- **Table TA3:** Appendix C — Register of Withdrawn and Superseded Claims.

---

## 5. Verification and Quality Audits

### 5.1 Automated Test Suite Verification
The verification test suite `tests/test_r6b_thesis.py` checks all formal requirements:
- Component file existence (17 files): **PASS**
- Master thesis existence and word count (> 20,000 words): **PASS** (28,801 words)
- Abstract exactness and word count (250–300 words): **PASS** (298 words)
- Contribution paragraph exactness: **PASS**
- Conclusion exactness (verbatim K1–K8): **PASS**
- All 12 figures placed: **PASS**
- All 14 tables placed: **PASS**
- All 42 claims referenced: **PASS**
- Navigation-only sources S29/S30 absent: **PASS**
- Verbatim Claim L41 block and qualifier: **PASS**
- Verbatim Claim L42 block and qualifier: **PASS**
- Banned overclaim phrases absent: **PASS**

### 5.2 Literature Provenance Verification
Every citation in the thesis references only:
- Primary and secondary literature in `research/R3A_SOURCE_REGISTER.csv` (S01–S31, strictly excluding navigation-only S29 and S30).
- The dataset owners' primary paper (S17: Liang, Calvert & van Lint 2025).
- Formal prior-art safety assurance frameworks (A01–A07: GSN, Goodenough & Kelly, Bloomfield Assurance 2.0, UL 4600, ISO 21448 SOTIF, RESPONSE 3 CoP, ISO 23793-1, NASA-STD-7009A).

### 5.3 Readiness
Phase R6B is complete and verified. The master thesis `thesis/draft/thesis.md` and all modular chapter drafts are ready for final academic review.
