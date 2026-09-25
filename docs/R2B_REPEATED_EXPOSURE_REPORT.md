# R2B: repeated-exposure / within-participant adaptation in the D003 simulated takeover task

**Status:** Phase R2B, 2026-09-22. Associational and descriptive only. This is **not** causal learning, and **not** vehicle-specific (EV/ICE, one-pedal, regen) familiarity.
**Code:** `src/experiments/r2b_repeated_exposure.py`. **Outputs:** `results/R2B_repeated_exposure/` (machine-readable `summary.json`; provenance in `provenance.json`: code commit, archive sha256, populations, definitions, windows, exclusions, limitations).
**Measurement rule:** only quantities that do not depend on control-channel authorship are used (blocker B17).

## 1. Exposure order

- Reconstructed from recording start times. All 57 participants have exactly 9 trials covering all 9 scenario cells, with no ties and no overlapping recordings, so order is **reconstructable**.
- 20 distinct order sequences (a counterbalanced design, not a strict 9-row Latin square). Each cell appears 4–8 times at each exposure position.
- Cell × exposure: Cramér's V = 0.05; variance inflation of exposure given participant and cell = 1.008. Exposure is **separable from scenario cell** at the level of linear adjustment.
- Irregularity: participant 28 had a ~50.7 h break before exposure 5 (every other gap ≤ ~9 min at the 95th percentile). It is flagged and kept.
- Limitations: carry-over from the specific preceding scenario cannot be separated from exposure, and practice drives (if any) are not in the public data.

## 2. Populations

| Outcome | Population | n | Exclusions |
|---|---|---|---|
| `t_button` = Manual_Start − TOR | TOR_ANCHORED | 492 trials / 57 participants | 15 no TOR column; 6 multi-TOR unresolved |
| TOR → validated lane change | LANE_CHANGE_ANCHORED (window MANUAL_TOR_TO_LANE_CHANGE) | 477 / 57 | 21 no TOR anchor; 13 no lane-change channel; 1 lane-change clock exception; 1 lane change after handback |
| Minimum TTC; vehicle max accel/decel (secondary) | OWNER_WINDOW_ELIGIBLE (owners' published window) | 478 / 57 | as above, except the post-handback lane change is included |

## 3. Results

Model: least squares with participant fixed intercepts, scenario-cell indicators and a linear exposure term, with participant-clustered (CR1) standard errors. Fitted only because exposure is separable from cell.

**`t_button` (primary).**
- Median 1.70 s at exposure 1, 1.55 s at exposure 9.
- Model slope −0.033 s per exposure (95% CI −0.058 to −0.007). Without cell controls: −0.032 s.
- Early (exposures 1–3) vs late (7–9), within participant: median difference −0.10 s; 63% of participants lower late (Wilcoxon p = 0.006).
- Per-participant slopes: median −0.010 s per exposure; 65% negative.
- **Interpretation:** a small decrease in button-press latency is **associated with repeated exposure** (≈ −0.26 s across 8 exposures). The per-exposure change is below the 0.05 s sampling interval, so individual-trial resolution is limited.

**TOR → validated lane change (primary).**
- Model slope +0.09 s per exposure (95% CI −0.13 to +0.31).
- Early vs late median difference −0.07 s (p = 0.71); per-participant slopes 51% negative.
- **No clear linear exposure association.**

**Secondary (descriptive; no model).** Early vs late median differences:
- minimum TTC: +0.11 s (p = 0.21)
- vehicle maximum deceleration: +0.88 m/s² (p = 0.51)
- vehicle maximum acceleration: +0.03 m/s² (p = 0.63)

Deceleration and acceleration are vehicle kinematics, not driver braking intensity (B17).

**Multi-TOR sensitivity (`t_button`).** The pre-defined criterion was: a change in the sign of the slope, or in its CI-based conclusion.

| Analysis | n | Median (IQR) | Slope (95% CI) |
|---|---|---|---|
| Protocol-resolved TOR | 492 | 1.65 (1.25–2.00) s | −0.033 (−0.058, −0.007) |
| Excluding all multi-TOR trials | 472 | 1.65 (1.25–2.00) s | −0.036 (−0.062, −0.010) |

The conclusion does not change materially.

## 4. Handback (competing event / observation boundary)

Handback = first `Time_Manual_Stop` after `Manual_Start` (switch back to automated mode). It is protocol-driven (participants were instructed to hand back after the lane change) and is **not** a stabilisation measure.

- TOR → handback: median 18.85 s (IQR 15.25–24.05; range 4.6–133.7), n = 492. This is also the available manual-control observation time after TOR.
- Manual_Start → handback: median 16.95 s (IQR 13.55–22.40).
- Lane change → handback (lane change before handback): median 11.80 s (IQR 9.00–15.05).
- Lane change relative to handback:
  - 477 before
  - 1 at or after (`density_0_nback_2_id_29`)
  - 13 no lane-change channel
  - 1 lane-change clock exception
  - 21 no TOR anchor
- 12 trials have several `Manual_Stop` values (B14).

## 5. What is new, replicated, descriptive

- **Replication (definition-compatible only):** `t_button`, minimum TTC, and vehicle maximum acceleration/deceleration are owner metrics. No numerical owner values were available to compare (`research/data_matrix/D003_OWNER_METRIC_RECONCILIATION.md`).
- **New (descriptive, associational):** the within-participant exposure-order analysis of `t_button` and TOR → lane change on a validated population, and the handback / observation-window descriptives.
- **Not new, not causal:** nothing here identifies learning mechanisms, workload or density effects, or vehicle-specific familiarity.

## 6. Human-layer status after R2B

| Category | Items |
|---|---|
| **A. Identified / measurable** | Event timing: `t_button`, TOR → validated lane change, handback timing. Repeated-exposure association for `t_button` (small decrease); no clear association for TOR → lane change |
| **B. Associational only** | Driving and ADAS experience (self-report, n = 57; not analysed in R2B); any participant-characteristic relationships |
| **C. Blocked by B17** | Driver-attributed brake timing; brake rise; brake-first vs steer-first; negative handover lag; driver control intensity (braking or steering); human correction counts from control channels; the owners' takeover time (ToT) |
| **D. Not identified** | EV / one-pedal / regen familiarity effects; expectation mismatch M as a causal vehicle-specific construct |
