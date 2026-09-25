# R2C-lite: participant-level associations and carry-over sensitivity for `t_button`

**Status:** Phase R2C-lite, 2026-09-23. Associational and descriptive only; no causal claims. Participant-characteristic results are a **secondary re-analysis**, not novel evidence.
**Code:** `src/experiments/r2c_lite.py`. **Outputs:** `results/R2C_lite/` (machine-readable `summary.json`; provenance in `provenance.json`: code commit, archive sha256, R2B trial-table sha256, definitions, populations, decision rules, limitations).
**Inputs:** the accepted R2B trial table (`results/R2B_repeated_exposure/trial_table.csv`) and the public driver-characteristic answers (`2.2 driver_characteristic_answers.csv` in the D003 archive).
**Measurement rule:** only `t_button` = Manual_Start − TOR is used. Manual_Start is an event marker and authority transfer is UNRESOLVED (B7). No accelerator, brake or steering quantity is used (B17).

## 1. Participant-level associations

**Prior work.** The dataset owners have already analysed driver characteristics against takeover timing (Liang et al., *Applied Ergonomics* 129:104603, 2025; only the abstract was read). This section re-analyses those variables with our validated `t_button`. It is **not** novel evidence about participant characteristics.

**Design** (pre-specified; no variable search):
- Unit: participant, n = 57.
- Primary outcomes:
  - participant median `t_button`
  - R2B per-participant OLS exposure slope (identical to `results/R2B_repeated_exposure/participant_slopes.csv`)
- Secondary outcomes: participant mean `t_button`; a cell-adjusted slope (cell effects removed before fitting the slope).
- Covariates (four self-report items):

| Column | Construct | Meaning |
|---|---|---|
| `accu_years` | driving experience | years of driving |
| `accu_km` | annual mileage | km in the past 12 months; **not** accumulated km, despite the name |
| `driving_frequency` | driving frequency | days per week |
| `assist_frequency` | ADAS-use frequency | assistance use out of 10 drives |

  The data dictionary names two of these differently (`driving_years`, `auto_usage`).
- Statistics:
  - Spearman ρ with a 2000-resample bootstrap 95% CI
  - OLS slope per covariate SD with an HC3 95% CI
  - Holm adjustment within each family of 8 tests (2 outcomes × 4 covariates)
- Not tested: age, gender, self-rated skill, and the risk, trust and takeover-style scales.

**Results** (primary population, 492 trials; Spearman ρ [95% CI], raw p → Holm p):

| Covariate | Median `t_button` | Exposure slope |
|---|---|---|
| Years of driving | −0.10 [−0.36, 0.16], p 0.48 → 1.00 | 0.15 [−0.12, 0.41], p 0.28 → 1.00 |
| km past 12 months | −0.18 [−0.44, 0.09], p 0.18 → 1.00 | 0.13 [−0.13, 0.38], p 0.32 → 1.00 |
| Driving days/week | −0.11 [−0.36, 0.15], p 0.40 → 1.00 | 0.26 [−0.03, 0.48], p 0.055 → 0.38 |
| ADAS-use frequency | −0.28 [−0.49, −0.05], p 0.037 → 0.30 | −0.17 [−0.42, 0.10], p 0.22 → 1.00 |

- **No association survives Holm adjustment.**
- The largest estimate: participants reporting more ADAS use had shorter median `t_button` (ρ −0.28; about −0.08 s per SD, HC3 CI −0.16 to 0.005). At n = 57 with 8 tests this is not distinguishable from chance and is treated as a hypothesis only.
- The secondary outcomes give the same picture: no Holm-significant association.
- Years of driving is strongly correlated with age (Spearman ρ 0.85), so "experience" and age cannot be separated here.

## 2. Carry-over sensitivity

**Question.** Is the immediately preceding scenario cell associated with the current `t_button`, beyond exposure and the current cell? And does adjusting for it change the R2B exposure association?

**Construction:**
- The previous cell comes from the full chronological (RAW) order, so every trial at exposure ≥ 2 has a predecessor.
- Exposure-1 trials have none and are excluded from **all** carry-over models, including the reference.
- Population: 435 trials, 57 participants. Multi-TOR sensitivity population: 416 trials.

**Identifiability:**
- Each of the 9 previous-cell levels has 43–50 trials.
- The design is full rank. Exposure VIF is 0.97; the maximum previous-cell VIF is 1.74.
- **Main effects are identifiable.**
- All 72 previous × current pairs occur, but with only 2–8 trials each (median 6). **The interaction is not identifiable and was not fitted.**

**Models:** participant fixed intercepts + current cell + linear exposure, with participant-clustered CR1 SE, as in R2B. A REML random-intercept model with the same fixed effects is fitted as a cross-check.

| Model (exposures 2–9) | Exposure slope (s/exposure) | FE CR1 95% CI | RI 95% CI | Carry-over joint Wald p |
|---|---|---|---|---|
| M0 reference | −0.026 | −0.057, 0.005 | −0.051, −0.0004 | — |
| M1 + previous density + previous n-back (4 df) | −0.027 | −0.057, 0.004 | −0.052, −0.001 | 0.56 |
| M2 + previous cell (8 df) | −0.026 | −0.056, 0.003 | −0.052, −0.001 | 0.77 |

**Findings:**
- **No carry-over association detected.** No individual previous-cell term has a CI excluding 0 (`carryover_coefficients.csv`).
- Adjusting for carry-over changes the exposure slope by only 3–4%. **The R2B exposure association is not explained by short-term carry-over.**
- Caveat: with exposures 2–9 only, the cluster-robust CI of the *reference* model already includes 0, before any carry-over term is added. The point estimate (−0.026) is close to R2B's −0.033, but this subset loses one exposure level and 57 trials. The random-intercept model's model-based CI still excludes 0.
- So the R2B association is **modest**: its precision under cluster-robust inference depends on including exposure 1. This is a precision / subset effect, not a carry-over effect.

**Decision-rule revision (recorded in `summary.json`).** The first run used the rule "exposure CI below 0 in every carry-over model". That rule confounds carry-over adjustment with the exposure 2–9 restriction, since the reference model already fails it. It was replaced by a same-trial comparison: an exposure-slope change greater than 25% versus the reference, or a changed CI-based conclusion. Both sets of CIs are reported.

## 3. Multi-TOR robustness

Every `t_button` analysis was repeated after excluding all multi-TOR trials (R2B sensitivity population):
- Participant-level: 472 trials, 57 participants. Still no Holm-significant association; ADAS-use vs median ρ −0.25 (raw p 0.059).
- Carry-over: 416 trials. Joint Wald p 0.53 (M1) and 0.74 (M2); exposure slope −0.028 to −0.029, with the same CI-based conclusions.

**No conclusion changes** (`multitor_sensitivity_materially_changes_conclusion: false`).

## 4. New vs secondary

| Result | Status |
|---|---|
| `t_button` vs driving experience, mileage, frequency, ADAS use | **Secondary re-analysis** of variables the owners already analysed; null after multiplicity correction |
| Per-participant exposure slope vs characteristics | Not found in the owners' text read; descriptive and null |
| Carry-over sensitivity of the exposure association | Robustness check of R2B; not found in the owners' text read |

## 5. Human-layer status after R2C-lite

| Category | Items |
|---|---|
| **IDENTIFIED** | Event timing (`t_button`, TOR → validated lane change, handback timing). Repeated-exposure association for `t_button`: modest; not explained by carry-over; its cluster-robust precision depends on including exposure 1 |
| **ASSOCIATIONAL ONLY** | Driving / ADAS experience relationships (none survives multiplicity correction); carry-over relationships (none detected) |
| **BLOCKED BY B17** | Any driver-attributed control-channel result: brake timing, brake rise, brake-first vs steer-first, negative handover lag, driver control intensity, control-channel correction counts, the owners' ToT |
| **NOT IDENTIFIED** | EV / one-pedal / regen familiarity; causal expectation mismatch M |

## 6. Limitations

- Covariates are single self-report items; n = 57 gives low power for participant-level correlations.
- The questionnaire `id` is joined to the trial filename `id_N`. The dictionary describes it as the assigned participant id, but an identical id space is not explicitly stated. **R3A closure check:** classified STRONGLY SUPPORTED BUT NOT EXPLICIT (same `id` definition in every dictionary section; cohort statistics match the README; other `id`-keyed owner tables align exactly with simulator filenames). R2C was not rerun.
- Previous cell is a bundle (B11): density, n-back, road, speed, hazard state and automation-transition behaviour. It is not a workload factor.
- Participant 28's trial after the ~50.7 h break keeps its nominal predecessor.
- The owners' 466-trial analysis set is not reconstructed (B12).
