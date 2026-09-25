# Branch E0: Boundary Evidence Closure, Robustness, and External-Validation Feasibility

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** The monotonicity and sensitivity results are MODEL-VALID within the stated domain. Statements that no Level 3/4 dataset "exists" should be read as "none found in the datasets checked". Later Phase 2 documents claimed partial Level-3 validation via D003; that claim is withdrawn (D003 samples a non-critical 7 s budget regime with an unparameterised simulator vehicle). Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** Complete (as a MODEL-VALID analysis; **[AUDIT 2026-09-22: not empirical validation]**)  
**Date:** 2026-09-21  
**Robustness Classification:** **E0-A: ROBUST ANALYTICAL / EVIDENCE-BOUNDED RESULT**  
**Validation Feasibility Decision:** **V1: PARAMETER-LEVEL VALIDATION FEASIBLE (OUTCOME VALIDATION NON-IDENTIFIABLE ON PUBLIC DATA)**  
**Parent Baseline:** Commit `387f964` (D0 claim/classification cleanup passed, 31 tests green, `phase0-frozen` at `bc21fbc`)  
**Claim Level:** **TYPE 1 (Analytical Monotonicity & Extrema Proof)** and **TYPE 2 (Bounded Numerical Sensitivity Mapping conditional on $t_{buildup}$)** per [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md)

---

## Executive Summary

Branch E0 provides formal **evidence closure, deterministic robustness verification, and external-validation feasibility assessment** for the state-dependent handover boundary derived in Branch D0.

In accordance with strict project scientific constraints:
1. **No Probabilities or Monte Carlo:** We do not construct subjective probability distributions, Bayesian belief networks, or Monte Carlo collision frequencies. The analysis is strictly deterministic kinematic interval analysis and sensitivity theory.
2. **Identification of the Claim Bottleneck:** The brake-response build-up ramp ($t_3 = t_{buildup} = 0.30\text{ s}$) is isolated as the sole `COUNTERFACTUAL_SENSITIVITY / TYPE 2` parameter. By the project claim ladder principle, the numerical boundary is formally bounded at **TYPE 2**. Crucially, we distinguish between a **claim-level bottleneck** and a **robustness bottleneck**: while $t_{buildup}$ limits the empirical claim level to TYPE 2, its normalized elasticity is small ($S_{t_3} \approx 0.06$), meaning it does *not* undermine boundary robustness.
3. **Deterministic Robustness Proof:** We analytically prove that $\nabla T_{required}$ is coordinate-wise strictly signed across the entire admissible hyper-rectangular domain $\Omega$. Consequently, no interior local extrema, saddle points, or sparse-grid artifacts exist: the true continuous infimum ($1.15\text{ s}$) and supremum ($3.58\text{ s}$ core; $4.98\text{ s}$ extension) occur strictly at the hyper-rectangle corners.
4. **Normalized Sensitivities (Elasticities):** We derive exact analytical formulas for $S_x = (x / T_{req}) \partial T_{req} / \partial x$. At nominal reference operating points, speed ($S_{v_0} \approx +0.49$ to $+0.56$) and maximum braking capability ($S_{a_{max}} \approx -0.46$ to $-0.49$) dominate; human reaction latency is secondary ($S_{t_1} \approx +0.34$ to $+0.41$); pre-deceleration is tertiary ($S_{a_{pre}} \approx -0.10$); while brake build-up is quaternary ($S_{t_3} \approx +0.06$). While partial derivative signs are globally invariant, elasticity magnitude rankings permute across the domain (28 distinct permutations over the grid).
5. **Fixed-TOR Policy Distinction:**
   - **State-Invariant Minimum:** NOT SUPPORTED. Because $T_{required}$ varies across the admissible domain ($\Delta T_{core} = 2.44\text{ s}$), no single scalar lead time can equal the minimum required fallback time across heterogeneous driving states.
   - **Worst-Case Fixed Bound:** FEASIBLE IN A BOUNDED DOMAIN. A fixed lead time chosen at or above the worst-case requirement ($T_{fixed} \ge 3.58\text{ s}$ core; $4.98\text{ s}$ extension) can guarantee collision-free stopping across the bounded domain, but is unnecessarily conservative in easier states.
6. **Project Validation Status:** Aligned strictly with the frozen global validation hierarchy:
   - **Level 1 (Mathematical Verification):** ESTABLISHED.
   - **Level 2 (Parameter Plausibility / Evidence):** EVIDENCE-BOUNDED / PARTIAL ($v_0, t_1, a_{pre}, t_2, a_{max}$ grounded; $t_3$ counterfactual).
   - **Level 3 (Trajectory Validation):** NOT ESTABLISHED.
   - **Level 4 (Outcome / Recoverability Validation):** NOT ESTABLISHED.
   - **Level 5 (Population Validity):** NOT ESTABLISHED.
   - Overall validation feasibility: **V1: PARAMETER-LEVEL VALIDATION ONLY**.

---

## 1. Parameter Closure and Evidence Audit

The parameters governing the closed-form state-dependent fallback boundary:
$$T_{required}(v_0, t_1, a_{pre}, t_2, t_3, a_{max}) = \frac{v_0}{2 a_{max}} + t_1 \left(1 - \frac{a_{pre}}{a_{max}}\right)\left(1 - \frac{a_{pre} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right) - \frac{a_{max} t_3^2}{24 v_0}$$
are audited in [`experiments/E_boundary_validation/e0_parameter_closure.csv`](../../experiments/E_boundary_validation/e0_parameter_closure.csv):

| Parameter Name | Symbol | Unit | Core Range | Provenance Class | Claim Level | Claim Bottleneck? | Evidence Source |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Initial Cruising Speed** | $v_0$ | $\text{m/s}$ | $[10.0, 30.0]$ | `CORE_EMPIRICAL` | TYPE 3 | NO | Operational design domain ($36 - 108\text{ km/h}$) |
| **Human Reaction Latency** | $t_1$ | $\text{s}$ | $[0.7, 1.5]$ | `CORE_EMPIRICAL` | TYPE 3 | NO | Takeover literature (L001, L014; D002, D003 parameter ranges) |
| **Pre-Human Deceleration** | $a_{pre}$ | $\text{m/s}^2$ | $[0.0, 3.0]$ | `EMPIRICAL_RANGE` | TYPE 3 | NO | D004 EV telemetry & SAE coast-down literature ($a_{coast}$) |
| **Brake Actuation Delay** | $t_2$ | $\text{s}$ | $[0.05, 0.17]$ | `EMPIRICAL_RANGE` | TYPE 3 | NO | Paquette & Porter (2014) brake lag measurements |
| **Brake Build-up Ramp** | $t_3$ | $\text{s}$ | $0.30$ (ext: $[0.1, 0.5]$) | `COUNTERFACTUAL_SENSITIVITY` | **TYPE 2** | **YES** | Unanchored: D001 gated/10Hz, D004 unpopulated, D005 no brake |
| **Maximum Deceleration** | $a_{max}$ | $\text{m/s}^2$ | $[8.0, 9.0]$ (wet: $4.9$) | `LITERATURE_CONSTRAINED` | TYPE 3 | NO | Vehicle dynamics emergency braking literature; dry vs wet scaling |
| **Initial Curvature** | $K_0$ | $\text{1/m}$ | $0.0$ | `KINEMATIC_INVARIANT` | TYPE 1 | NO | B0 State-Mediation Invariance proof |
| **Resolvable Margin** | $\Delta x_{robust}$ | $\text{m}$ | $8.5 \times 10^{-6}$ | `DISCRETIZATION_ARTIFACT` | TYPE 1 | NO | A0 numerical grid limit ($a_{max} dt^2 \to 0$) |

### Claim-Level Bottleneck vs Robustness Bottleneck:
- **Claim-Level Bottleneck:** Per [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md), an empirical finding (TYPE 3) requires all load-bearing parameter inputs to be empirically grounded. Because brake-response build-up ramp $t_3 = t_{buildup}$ carries `COUNTERFACTUAL_SENSITIVITY / TYPE 2` status, any numerical evaluation of $T_{required}$ is structurally bottlenecked at **TYPE 2**. The analytical functional form remains a mathematical deduction (**TYPE 1**).
- **Robustness Non-Bottleneck:** Although $t_3$ acts as a claim bottleneck, it is *not* a robustness bottleneck. Its normalized sensitivity is low ($S_{t_3} \approx 0.06$), and full 5-fold variation across $[0.10, 0.50]\text{ s}$ shifts required lead time by $< 0.20\text{ s}$ ($< 4.5\%$). The physical finding of a $2.44\text{ s}$ state-dependent requirement spread is insensitive to this uncertainty.

---

## 2. Deterministic Robustness Analysis

### 2.1 Normalized Sensitivities (Elasticities)
The dimensionless elasticity $S_x$ quantifies the percentage change in $T_{required}$ per $1\%$ change in parameter $x$:
$$S_x \equiv \frac{x}{T_{required}} \frac{\partial T_{required}}{\partial x}$$

Evaluated at nominal reference points ($v_0 = 20\text{ m/s}, t_1 = 1.0\text{ s}, t_2 = 0.10\text{ s}, t_3 = 0.30\text{ s}, a_{max} = 8.5\text{ m/s}^2$):

| Parameter ($x$) | Partial Derivative Expression ($\partial T / \partial x$) | Nominal $W0$ ($a_{pre} = 0$) | Nominal $W1$ ($a_{pre} = 1.5$) | Elasticity $S_x$ ($W0$) | Elasticity $S_x$ ($W1$) | Nominal Rank ($W1$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **$v_0$ (Speed)** | $\frac{1}{2 a_{max}} + \frac{a_{pre} t_1^2 (1 - a_{pre}/a_{max})}{2 v_0^2} + \frac{a_{pre} t_1 (t_2 + t_3/2)}{v_0^2} + \frac{a_{max} t_3^2}{24 v_0^2}$ | $+0.0589\text{ s/(m/s)}$ | $+0.0614\text{ s/(m/s)}$ | **$+0.4858$** | **$+0.5584$** | **1** |
| **$a_{max}$ (Braking Cap.)** | $- \frac{v_1^2}{2 a_{max}^2 v_0} - \frac{t_3^2}{24 v_0}$ | $-0.1386\text{ s/(m/s}^2\text{)}$ | $-0.1186\text{ s/(m/s}^2\text{)}$ | **$-0.4858$** | **$-0.4585$** | **2** |
| **$t_1$ (Reaction)** | $\left(1 - \frac{a_{pre}}{a_{max}}\right)\frac{v_1}{v_0} - \frac{a_{pre}}{v_0}\left(t_2 + \frac{t_3}{2}\right)$ | $+1.0000\text{ s/s}$ | $+0.7430\text{ s/s}$ | **$+0.4124$** | **$+0.3379$** | **3** |
| **$a_{pre}$ (Pre-decel)**| $- \frac{t_1}{a_{max}}\frac{v_1}{v_0} - \frac{t_1}{v_0}\left(\frac{t_1}{2} + t_2 + \frac{t_3}{2}\right)$ | $-0.1551\text{ s/(m/s}^2\text{)}$ | $-0.1463\text{ s/(m/s}^2\text{)}$ | $0.0000$ | **$-0.0998$** | **4** |
| **$t_3$ (Build-up)** | $\frac{1}{2}\frac{v_1}{v_0} - \frac{a_{max} t_3}{12 v_0}$ | $+0.4894\text{ s/s}$ | $+0.4519\text{ s/s}$ | **$+0.0605$** | **$+0.0617$** | **5** |
| **$t_2$ (Delay)** | $\frac{v_1}{v_0}$ | $+1.0000\text{ s/s}$ | $+0.9250\text{ s/s}$ | **$+0.0412$** | **$+0.0421$** | **6** |

*(where $v_1 = v_0 - a_{pre} t_1$ is vehicle velocity at human brake onset).*

### Audit of Factor Ranking Invariance:
- **Sign Invariance vs Ranking Permutations:** While the algebraic *signs* of all six partial derivatives are 100% invariant across the entire domain, the *ordering of elasticity magnitudes* is **not globally invariant**.
- Across the admissible domain grid, there are **28 distinct permutations** of factor ranking. For example, at low speeds ($v_0 = 10\text{ m/s}$) with long reaction times ($t_1 = 1.5\text{ s}$), driver reaction latency ($t_1$) has the highest elasticity ($|S_{t_1}| > |S_{v_0}|$), whereas at high highway speeds ($v_0 = 30\text{ m/s}$), initial velocity ($v_0$) and maximum deceleration ($a_{max}$) dominate.
- Therefore, the hierarchy in the table above must be understood as a **representative nominal sensitivity ordering** at the specified reference states, not a globally invariant importance ranking.

---

### 2.2 Proof of Global Coordinate-Wise Monotonicity

To establish whether interior local extrema, saddle points, or non-linear bifurcations exist within the admissible domain, we inspect the partial derivative bounds across the entire sensitivity hyper-rectangle $\Omega = [10, 30]\text{ m/s} \times [0.7, 1.5]\text{ s} \times [0.0, 3.0]\text{ m/s}^2 \times [0.05, 0.17]\text{ s} \times [0.10, 0.50]\text{ s} \times [4.9, 9.0]\text{ m/s}^2$:

1. **$\partial T / \partial v_0 > 0$ strictly everywhere:** All four additive terms are strictly positive for $v_0 \ge 10\text{ m/s}$ and $a_{pre} \le 3.0\text{ m/s}^2 < a_{max}$. Numerical bounds: $\partial T / \partial v_0 \in [+0.0556, +0.1238]\text{ s/(m/s)}$.
2. **$\partial T / \partial t_1 > 0$ strictly everywhere:** Minimum occurs at $v_0 = 10\text{ m/s}, a_{pre} = 3.0\text{ m/s}^2, t_1 = 1.5\text{ s}$, yielding $\partial T / \partial t_1 \ge +0.1081 > 0$.
3. **$\partial T / \partial a_{pre} < 0$ strictly everywhere:** Both terms are strictly negative. Bounds: $\partial T / \partial a_{pre} \in [-0.4403, -0.0856]\text{ s/(m/s}^2\text{)}$.
4. **$\partial T / \partial t_2 > 0$ strictly everywhere:** Equal to $v_1 / v_0 \in [0.5690, 1.0000] > 0$.
5. **$\partial T / \partial t_3 > 0$ strictly everywhere:** Minimum occurs at $v_0 = 10\text{ m/s}, t_3 = 0.50\text{ s}, a_{max} = 9.0\text{ m/s}^2$, where $\frac{a_{max} t_3}{12 v_0} = 0.0375$, far below $\frac{1}{2} \frac{v_1}{v_0} \ge 0.2845$. Bounds: $\partial T / \partial t_3 \in [+0.2546, +0.4979] > 0$.
6. **$\partial T / \partial a_{max} < 0$ strictly everywhere:** Both terms are strictly negative. Bounds: $\partial T / \partial a_{max} \in [-0.6033, -0.0239]\text{ s/(m/s}^2\text{)}$.

### Mathematical Implication (Absence of Interior Extrema):
Because the gradient $\nabla T_{required}$ is non-zero and maintains strictly invariant sign in each coordinate throughout the hyper-rectangle $\Omega$:
$$\forall \mathbf{x} \in \operatorname{int}(\Omega), \quad \nabla T_{required}(\mathbf{x}) \ne \mathbf{0}$$
**There are no local extrema, saddle points, or internal valleys in the interior.**  
The global supremum and infimum are mathematically guaranteed to lie at the vertices (corners) of $\Omega$.

---

### 2.3 Verification Against Sparse-Grid Artifacts

Having proven global coordinate-wise monotonicity, the true continuous analytical extrema are:
- **Global Infimum ($T_{min}$):**
  $$(v_0^{min}, t_1^{min}, a_{pre}^{max}, t_2^{min}, t_3^{min}, a_{max}^{max})$$
- **Global Supremum ($T_{max}$):**
  $$(v_0^{max}, t_1^{max}, a_{pre}^{min}, t_2^{max}, t_3^{max}, a_{max}^{min})$$

Evaluating these analytical corner coordinates:
- **Core Domain Corners:**
  - $T_{min} = T(10.0, 0.7, 3.0, 0.05, 0.30, 8.5) = \mathbf{1.1484\text{ s}}$
  - $T_{max} = T(30.0, 1.5, 0.0, 0.17, 0.30, 8.5) = \mathbf{3.5836\text{ s}}$
  - Continuous Span: $\Delta T_{core} = \mathbf{2.4352\text{ s}}$
- **Sensitivity Extension Corners:**
  - $T_{min} = T(10.0, 0.7, 3.0, 0.05, 0.10, 8.5) = \mathbf{1.0723\text{ s}}$
  - $T_{max} = T(30.0, 1.5, 0.0, 0.17, 0.50, 4.9) = \mathbf{4.9795\text{ s}}$
  - Extended Span: $\Delta T_{ext} = \mathbf{3.9073\text{ s}}$

**Conclusion:** The discrete 54-point grid in D0 included the box corners and therefore captured the true continuous extrema to machine precision. There are **zero sparse-grid artifacts**.

---

### 2.4 Leave-One-Out Bottleneck Perturbation

To evaluate the operational impact of the unresolved bottleneck parameter $t_3 = t_{buildup}$, we perform a leave-one-out perturbation across its full counterfactual range $[0.10, 0.50]\text{ s}$ ($\pm 67\%$ variation):
- Under baseline $W0$: $T_{required}$ shifts from $2.326\text{ s}$ to $2.522\text{ s}$ ($\Delta = +0.196\text{ s}$, or $\pm 4.0\%$).
- Under active policy $W1$ ($a_{pre} = 1.5\text{ m/s}^2$): $T_{required}$ shifts from $2.108\text{ s}$ to $2.288\text{ s}$ ($\Delta = +0.181\text{ s}$, or $\pm 4.1\%$).

**Physical Implication:** Even under a five-fold variation in brake build-up speed ($100\text{ ms}$ high-performance response vs $500\text{ ms}$ sluggish build-up), the required lead time shifts by less than $0.20\text{ s}$. The $2.44\text{ s}$ state-dependent spread across driving contexts is completely preserved regardless of $t_{buildup}$ assumptions.

---

### 2.5 Discretization Robustness (Criterion 1 vs Criterion 2)

As derived in D0, the shift between Criterion 1 ($\text{margin} \ge 0$) and Criterion 2 ($\text{margin} \ge \Delta x_{robust} = a_{max} dt^2$) is:
$$\Delta T_{discrete} = \frac{a_{max} dt^2}{v_0}$$
At nominal $dt = 0.001\text{ s}$, $a_{max} = 8.5\text{ m/s}^2$, and lowest speed $v_0 = 10\text{ m/s}$:
$$\Delta T_{discrete} = \frac{8.5 \times 10^{-6}\text{ m}}{10\text{ m/s}} = 8.5 \times 10^{-7}\text{ s} \quad (0.85\ \mu\text{s})$$
At highway speed ($30\text{ m/s}$), the shift is $0.28\ \mu\text{s}$.  
This confirms that Criterion 1 and Criterion 2 are mathematically and practically indistinguishable.

---

## 3. External Dataset Forensic Audit (D001–D005)

### 3.1 Frozen Project Validation Hierarchy
The project adheres to a single frozen 5-level validation hierarchy:

1. **LEVEL 1: Mathematical Verification** — Closed-form derivations, sign invariance, analytical oracle equivalence.  
   **Status: ESTABLISHED.**
2. **LEVEL 2: Parameter Plausibility / Evidence** — Empirical and literature bounds on individual kinematic parameters.  
   **Status: EVIDENCE-BOUNDED / PARTIAL** ($v_0, t_1, a_{pre}, t_2, a_{max}$ bounded; $t_3$ remains counterfactual).
3. **LEVEL 3: Trajectory Validation** — Continuous empirical kinematic time-series $x(t), v(t), a(t)$ during emergency fallback across vehicle architectures.  
   **Status: NOT ESTABLISHED.**
4. **LEVEL 4: Outcome / Recoverability-Boundary Validation** — Empirical verification of crash vs stop boundary under controlled obstacle distance $d_0$ and TOR lead times.  
   **Status: NOT ESTABLISHED.**
5. **LEVEL 5: Population / Generalisation Validity** — Representative fleet-wide distributions and crash probability reductions in real traffic.  
   **Status: NOT ESTABLISHED.**

---

### 3.2 Dataset Forensic Audit:

| Dataset ID | Dataset Name | Domain / Context | Sampling Rate Scope | Key Channels | Braking Channel Status | Dataset Validation Role | Forensic Audit Findings & Scope |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| **D001** | **ADAS-TO** | Naturalistic ADAS disengagements | Mixed: 61.7% at 10Hz (`qlog`), 38.3% at 100Hz (`rlog`) | Radar distance, `aEgo`, `vEgo`, `carControl` | **BINARY ONLY** (`brakePressed`, `gasPressed`). No continuous pedal position or force. | `SANITY_CHECK_ONLY` | Sampling split documented in arXiv paper text. Gated Hugging Face access (manual approval required). 10Hz majority cannot resolve hydraulic lag ($t_2$); binary pedal prevents ramp fitting; no controlled obstacle distance $d_0$. Usable solely for aggregate deceleration/TTC distribution sanity checks. |
| **D002** | **TD2D** | L2 driving-simulator takeovers (distracted) | Variable CSV | Driver reaction times, secondary task logs | Single vehicle model; no powertrain variation | `PARAMETER_VALIDATION` | Publicly hosted on Zenodo (Nature Scientific Data 2025). 50 drivers, 500 takeover cases. L2 context (driver in-the-loop); braking architecture not manipulated. Validates human reaction latency $t_1$ bounds ($0.7 - 1.5\text{ s}$). |
| **D003** | **TU Delft Takeover** | L3 conditionally automated takeovers | Fixed-base sim logs | Reaction times, steering, pedal onset | Single vehicle model; fixed brake physics | `PARAMETER_VALIDATION` | Published via TU Delft 4TU.ResearchData. 57 participants, 9 scenarios. Conditionally automated L3 paradigm; vehicle physics invariant. Validates $t_1$ distribution under non-driving secondary tasks. |
| **D004** | **OpenLKA EV Kinematic** | Naturalistic EV driving logs | Measured ~100Hz-class (~128Hz average over 1,812 rows in 1 session) | `state_gas_pos`, `state_regen_break_enable`, `aEgo`, `vEgo` | `brake_padel_status` binary; brake commands zero in sampled windows (`op_enable=False`) | `PARAMETER_VALIDATION` | Committed directly in GitHub repo. 197.5h claimed (`METADATA_UNCERTAIN` across full fleet; only 1 session inspected). Confirmed continuous `state_gas_pos`. Validates EV coastdown/regen bounds ($a_{pre} \in [1.0, 3.0]\text{ m/s}^2$); sampled windows contain zero hard-braking events. |
| **D005** | **OpenLKA Acceleration** | EV longitudinal acceleration | **Measured ~10Hz ($\Delta t \approx 0.10\text{ s}$)**, contradicting 100Hz claim | `v, a, t, padel` (accelerator only) | **NO BRAKE CHANNEL** anywhere in schema | `NOT_USABLE` | Committed directly in GitHub repo. 12 EV models claimed (`METADATA_UNCERTAIN`). Measured at ~10Hz across 6+ segments in sampled Hyundai Ioniq 5 segments file. Schema has no brake channel; disqualified for braking, fallback, or handover timing. |

### Summary of Dataset Audit Findings:
- **No Level 3 (Trajectory) or Level 4 (Outcome) Dataset Exists:** None of the public datasets record automated vehicle handovers against a stationary obstacle with ground-truth stopping distance $d_0$ and varied vehicle deceleration profiles.
- **Level 2 (Parameter) Evidence is Partially Established:** Human reaction latency $t_1$ is bounded by D002/D003 ($0.7 - 1.5\text{ s}$); pre-deceleration $a_{pre}$ is bounded by D004 ($1.0 - 3.0\text{ m/s}^2$); brake actuation delay $t_2$ is bounded by Paquette & Porter (2014); dry-road maximum deceleration $a_{max}$ is literature-constrained. Build-up ramp $t_3$ remains counterfactual.

---

## 4. External Validation Feasibility Classification

We classify external validation feasibility into five standardized tiers:

- **V0: Unfeasible / Non-Identifiable:** Key variables unobservable in principle.
- **V1: Parameter-Level Validation Feasible:** Individual component parameters can be bounded by public empirical datasets, but end-to-end trajectory and collision outcome validation require new empirical experiments.
- **V2: Trajectory-Level Validation Feasible:** Continuous kinematics observable across architectures, but hazard-relative stopping outcomes unobserved.
- **V3: Outcome-Level Validation Feasible in Simulation Only:** High-fidelity simulation test bench (e.g. CARLA HIL) required.
- **V4: Full Empirical Outcome Validation Feasible on Existing Public Data:** All variables, trajectories, and outcomes present in existing open datasets.

### Formal Gate Decision: **V1: PARAMETER-LEVEL VALIDATION FEASIBLE**
**(Outcome Validation Non-Identifiable with Existing Public Data)**

### Requirements for a Future Level 3 / Level 4 Validation Experiment:
To advance beyond V1 to Level 3/4 validation, an empirical study must implement:
1. **Coupled Test Protocol:** Automated handover issued at variable time budgets ($T_{available} \in [1.0, 4.0]\text{ s}$) before a soft crashable stationary target.
2. **Manipulated Powertrain Architecture:** Controlled variation of automation withdrawal policy ($W0$: neutral coasting vs $W1$: active powertrain deceleration $1.0 - 3.0\text{ m/s}^2$).
3. **Synchronized High-Frequency CAN Logging ($\ge 100\text{ Hz}$):** Continuous pedal force/stroke, brake line pressure transducer, wheel speeds, IMU acceleration ($aEgo$), and millimeter-wave radar obstacle distance.

---

## 5. Robustness Classification Decision

### Formal Decision: **E0-A: ROBUST ANALYTICAL / EVIDENCE-BOUNDED RESULT**

### Justification:
1. **Mathematical Exactness (Type 1):** The state-dependent required-time boundary $T_{required}$ is closed in finite algebraic form with zero unresolved dynamic approximations.
2. **Strict Global Monotonicity:** Partial derivatives maintain invariant signs across the entire admissible domain. The absence of interior local extrema guarantees that the boundary spread is bounded strictly by the domain corners.
3. **Robustness to Claim Bottleneck:** The only counterfactual parameter ($t_{buildup}$, elasticity $\approx 0.06$) shifts required time by $< 0.20\text{ s}$ across its entire 5-fold sensitivity span, leaving the $2.44\text{ s}$ state-dependent spread structurally unaltered.
4. **Honest Boundary Claiming (Type 2):** In strict adherence to [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md), the numerical boundary is classified as **TYPE 2**, transparently acknowledging the brake build-up ramp evidence gap while proving that the physical finding is robust.
5. **Fixed-TOR Scoping:** The finding is precisely scoped: while a state-invariant *minimum* lead time is physically unsupported, a *worst-case fixed bound* is feasible within a bounded model domain at the cost of over-conservatism in lower-speed/active-regen states.

---

## 6. Programmatic Verification

The analytical proofs, elasticities, monotonicity checks, and extrema matches are verified in [`tests/test_e0_robustness.py`](../../tests/test_e0_robustness.py):
- `test_parameter_closure_table_integrity`: Confirms CSV integrity and single bottleneck identification.
- `test_normalized_sensitivities_elasticities`: Verifies analytical elasticities and representative nominal factor ranking.
- `test_elasticity_ranking_permutations_across_domain`: Confirms that while partial derivative signs are globally invariant, elasticity rankings permute across the domain (28 distinct permutations).
- `test_global_monotonicity_across_admissible_domain`: Proves coordinate-wise derivative signs across domain.
- `test_analytical_extrema_match_domain_corners`: Verifies corner extrema match discrete grid values.
- `test_bottleneck_leave_one_out_sensitivity`: Confirms $t_3$ perturbation impact is $< 0.20\text{ s}$.
- `test_discretization_shift_bound`: Confirms numerical margin shift $< 1\ \mu\text{s}$.

All unit tests pass without error.
