# Quantitative Claim Ledger: Source of Truth for Scientific Findings

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** The arithmetic in this ledger is retained (MODEL-VALID inside the deterministic open-loop 1-D model). Interpretive notes: effect-size ratios such as NUM-10 (≈3.7×, `a_pre` over [0, 3] m/s² vs `t2` over [0.05, 0.17] s) depend on the chosen parameter ranges and are not properties of real vehicles. No entry is empirical validation, and none supports a novelty claim. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Document:** `docs/QUANTITATIVE_CLAIM_LEDGER.md`  
**Status:** Frozen Source of Truth for Quantitative Results (Branch G0.2)  
**Date:** 2026-09-21  
**Repository Baseline:** `phase0-frozen` (`bc21fbc`)  
**Active HEAD:** Post-G0.1 (`3f146aa`)  
**Test Suite:** All unit tests verified via `pytest -q`

---

## 1. Executive Purpose & Usage Rules

This document establishes the **single source of truth** for all headline numerical values, parameter spans, sensitivity derivatives, and comparative claims across the repository and future manuscripts.

### Mandatory Rules for Manuscript Authors:
1. **No Untracked Numbers:** Every quantitative figure appearing in the manuscript text, tables, or figures must have a corresponding entry in this ledger.
2. **Strict Dimensionality:** Raw partial derivatives (units $\text{s} / (\text{m/s}^2)$) must **never** be compared directly against time intervals (units $\text{s}$). Comparisons between parameters must use either:
   - **Bounded Effect Sizes ($\Delta T$ in seconds):** The change in $T_{required}$ across the pre-specified admissible parameter interval.
   - **Dimensionless Normalized Sensitivities ($S_x$):** Elasticities $S_x \equiv \frac{x}{T_{required}} \frac{\partial T_{required}}{\partial x}$.
3. **No Unscoped Dominance Claims:** A1 demonstrated that the first-order pre-effective deceleration effect dominates the $a_{pre} \times t_3$ interaction ($\le 0.07\text{ s}$). Globally, initial velocity $v_0$ and maximum deceleration capability $a_{max}$ dominate model elasticity. Do not assert global parameter dominance without specifying the exact comparator and reference domain.

---

## 2. Headline Quantitative Claims Ledger

| Claim ID | Metric / Quantity | Numerical Value / Range | Units | Governing Equation or Code Anchor | Reference Point or Domain | Claim Type | Evidence Status | Approved Manuscript Wording | Known Caveat / Guardrail |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :--- | :--- | :--- |
| **NUM-01** | A0 Simulator Truncation Error | $< 10^{-12}$ ($< 10^{-14}$ residual) | m | `tests/test_analytical_oracle.py::test_forward_euler_convergence` | Forward Euler ($dt = 0.001\text{ s}$) vs. kinematic oracle | **TYPE 1** | Analytically Verified | *"The forward numerical simulator matches the analytical kinematic oracle to double precision ($< 10^{-12}\text{ m}$)."* | Validated on minimal deterministic model; not a physical vehicle telemetry claim. |
| **NUM-02** | A1 First-Order Pre-Braking Effect | $0.15 - 0.59$ (nominal $0.30 - 0.58$) | s | `experiments/A_brake_response/A1_RESULTS.md`, `results/A1/a1_core_sweep.csv` | $v_0 \in \{20, 30\}\text{ m/s}, a_{coast} \in [1.0, 4.0]\text{ m/s}^2$ | **TYPE 2** | Empirically-Constrained Simulation | *"Pre-effective deceleration shifts critical takeover time by $0.30 - 0.58\text{ s}$ ($6 - 17\text{ m}$ at highway cruise speeds)."* | Derived under step-demand open-loop braking ($u=1.0$). |
| **NUM-03** | A1 Interaction Contrast ($W \times R$) | $|I_D| \in [0.10, 1.40]$<br>$\|I_{T_{crit}}\| \le 0.070$ (nominal $-0.025$) | m<br>s | $I_D = -\frac{1}{2} a_{coast} t_1 t_b$<br>$I_{T_{crit}} = -\frac{a_{coast} t_1 t_b}{2 v_0}$ | Core sweep grid ($a_{coast} \le 4.0\text{ m/s}^2, t_b \le 0.7\text{ s}$) | **TYPE 1** (form)<br>**TYPE 2** (grid) | Analytically Exact (simulated $< 10^{-14}\text{ m}$) | *"The analytical non-additivity between withdrawal policy and response ramp contributes a modest shift of $\|I_{T_{crit}}\| \le 0.07\text{ s}$ ($70\text{ ms}$)."* | Modest magnitude ($\le 9\%$ of human reaction latency); secondary to first-order effects. |
| **NUM-04** | D0 Core Domain $T_{required}$ Span | $1.15$ to $3.58$ ($\Delta T_{core} = 2.44$) | s | `tests/test_d0_analytical_boundary.py::test_domain_spread_matches_reported_values` | $v_0 \in [10, 30]\text{ m/s}, t_1 \in [0.7, 1.5]\text{ s}, a_{pre} \in [0, 3]\text{ m/s}^2, t_2 \in [0.05, 0.17]\text{ s}, t_3 = 0.30\text{ s}, a_{max} \in [6.0, 9.0]\text{ m/s}^2$ | **TYPE 2** | Bounded Parameter Mapping | *"Across the core literature-grounded parameter domain, minimum required takeover lead time spans $1.15\text{ s}$ to $3.58\text{ s}$."* | Held at nominal $t_3 = 0.30\text{ s}$ due to public CAN dataset telemetry limits (`TYPE 2`). |
| **NUM-05** | D0 Extended Sensitivity Span | $1.07$ to $4.98$ ($\Delta T_{ext} = 3.91$) | s | `tests/test_d0_analytical_boundary.py::test_domain_spread_matches_reported_values` | Extended domain: $v_0 \in [10, 35]\text{ m/s}, a_{max} \in [3.5, 9.0]\text{ m/s}^2$ (wet asphalt) | **TYPE 2** | Sensitivity Mapping | *"Under adverse environmental conditions (wet surface, reduced friction), required lead time extends up to $4.98\text{ s}$."* | Represents worst-case friction boundary; not a typical dry asphalt requirement. |
| **NUM-06** | E0 Normalized Elasticity Hierarchy | $S_{v_0} \approx +0.58$<br>$S_{a_{max}} \approx -0.45$<br>$S_{t_1} \approx +0.31$<br>$S_{a_{pre}} \approx -0.13$<br>$S_{t_3} \approx +0.06$<br>$S_{t_2} \approx +0.04$ | — | $S_x = \frac{x}{T} \frac{\partial T}{\partial x}$; `tests/test_e0_robustness.py::test_elasticity_hierarchy` | Representative active state: $(20.0, 1.0, 2.0, 0.10, 0.30, 8.5)$ | **TYPE 1** (form)<br>**TYPE 2** (eval) | Mathematically Exact at Point | *"Speed ($S_{v_0} \approx +0.58$) and braking capability ($S_{a_{max}} \approx -0.45$) exert the largest normalized elasticities, while actuator delay and build-up ramp are low-sensitivity ($S \le 0.06$)."* | Ranking can permute at domain extremes (20+ permutations observed), but speed and $a_{max}$ dominate globally. |
| **NUM-07** | E0 Build-Up Ramp ($t_3$) Robustness | $\Delta T < 0.20$ ($< 4.5\%$ relative shift) | s | `tests/test_e0_robustness.py::test_bottleneck_leave_one_out_sensitivity` | 5-fold variation in $t_3 \in [0.10, 0.50]\text{ s}$ across domain | **TYPE 2** | Bounded Perturbation | *"A 5-fold variation in deceleration build-up ramp ($t_3 \in [0.10, 0.50]\text{ s}$) shifts $T_{required}$ by $< 0.20\text{ s}$, confirming that the uncalibrated $t_3$ parameter does not destabilize the boundary."* | Limits impact of CAN telemetry absence for emergency hydraulic rise times. |
| **NUM-08** | Nominal Partial Derivative $\partial T / \partial a_{pre}$ | $-0.155$ (exact: $-0.155147$) | $\frac{\text{s}}{\text{m/s}^2}$ | $\frac{\partial T}{\partial a_{pre}} = -\frac{t_1}{v_0}\left[\frac{v_1}{a_{max}} + \frac{t_1}{2} + t_2 + \frac{t_3}{2}\right]$; `tests/test_e0_robustness.py::test_apre_sensitivity_and_bounded_effects` | Nominal state: $(20.0, 1.0, 0.0, 0.10, 0.30, 8.5)$ | **TYPE 1** | Analytically Exact | *"At nominal cruising speed ($20\text{ m/s}$), pre-effective deceleration reduces required takeover lead time at an initial marginal rate of $-0.155\text{ s}$ per $\text{m/s}^2$."* | **Permanently replaces and corrects the erroneous $\sim 0.83\text{ s/(m/s}^2)$ figure.** |
| **NUM-09** | Domain Bounds on $\partial T / \partial a_{pre}$ | $[-0.422, -0.083]$ | $\frac{\text{s}}{\text{m/s}^2}$ | `tests/test_e0_robustness.py::test_apre_sensitivity_and_bounded_effects` | Entire admissible domain $\Omega$ | **TYPE 1** | Analytically Exact | *"Across the full admissible domain, the marginal sensitivity $\partial T / \partial a_{pre}$ ranges strictly between $-0.422$ and $-0.083\text{ s}$ per $\text{m/s}^2$."* | Most negative at low speed ($10\text{ m/s}$) with long latency ($1.5\text{ s}$); least negative at high speed ($35\text{ m/s}$) with short latency ($0.7\text{ s}$). |
| **NUM-10** | Bounded Effect: $a_{pre}$ vs. Actuator Delay $t_2$ | $\Delta T(a_{pre}) \approx -0.44\text{ s}$ vs.<br>$\Delta T(t_2) = +0.12\text{ s}$<br>(Ratio $\approx 3.7\times$) | s | `tests/test_e0_robustness.py::test_apre_sensitivity_and_bounded_effects` | Full parameter spans: $a_{pre} \in [0, 3]\text{ m/s}^2$ vs. $t_2 \in [0.05, 0.17]\text{ s}$ at nominal $v_0=20\text{ m/s}$ | **TYPE 2** | Bounded Parameter Comparison | *"Across their plausible parameter spans, varying pre-effective deceleration ($0$ to $3\text{ m/s}^2$) yields a lead-time reduction ($\sim 0.44\text{ s}$) that is approximately 3 to 4 times larger than the full span of brake response delay ($0.12\text{ s}$)."* | Dimensionally valid comparison between bounded effects in seconds; not an order-of-magnitude difference. |
| **NUM-11** | Discretization Shift Upper Bound | $0.85\ \mu\text{s}$ ($8.5 \times 10^{-7}\text{ s}$) | s | $\Delta T_{shift} = \frac{a_{max} dt^2}{v_{0,min}}$; `tests/test_e0_robustness.py::test_discretization_shift_bound` | Worst-case: $a_{max}=8.5\text{ m/s}^2, dt=0.001\text{ s}, v_0=10\text{ m/s}$ | **TYPE 1** | Analytically Exact | *"The difference between zero-margin and discrete resolvable margin accounts for $< 1\ \mu\text{s}$ of lead time."* | Proves analytical criterion equivalence. |

---

## 3. Discontinued / Corrected Figures

The following figures appeared in earlier drafts or notes and are **permanently retired**:

1. **`0.83 s / (m/s²)` (RETIRED):**
   - *Origin:* Typographical error or misinterpretation of either a single row in an A1 simulation grid (`0.835` margin) or the minimum magnitude boundary derivative ($|\partial T / \partial a_{pre}| \approx 0.083$ at $v_0 = 35\text{ m/s}$).
   - *Correction:* Replaced by the exact nominal derivative $\left.\frac{\partial T}{\partial a_{pre}}\right|_{nom} = -0.155\text{ s / (m/s}^2)$ and the global domain range $[-0.422, -0.083]\text{ s / (m/s}^2)$.
2. **"Order-of-Magnitude Dominance of $a_{pre}$ over Actuator Tuning" (RETIRED):**
   - *Origin:* Dimensionally invalid comparison of raw derivative (units $\text{s} / (\text{m/s}^2)$) against actuator time span (units $\text{s}$).
   - *Correction:* Replaced by valid bounded effect sizes: $\Delta T(a_{pre}) \approx -0.44\text{ s}$ across $[0, 3.0]\text{ m/s}^2$ compared to $\Delta T(t_2) = +0.12\text{ s}$ across $[0.05, 0.17]\text{ s}$ (a factor of $\sim 3.7\times$, not an order of magnitude).
3. **"Global Dominance of $a_{pre}$ over the Model" (RETIRED):**
   - *Origin:* Overgeneralizing the A1 result (where $a_{pre}$ first-order effect dominated the $a_{pre} \times t_3$ interaction) to the global 6-parameter boundary.
   - *Correction:* Replaced by the exact normalized elasticity hierarchy showing that speed ($S_{v_0} \approx +0.58$) and braking capability ($S_{a_{max}} \approx -0.45$) dominate globally, while $a_{pre}$ ($S_{a_{pre}} \approx -0.13$) is secondary, and actuator transients are low ($S \le 0.06$).
