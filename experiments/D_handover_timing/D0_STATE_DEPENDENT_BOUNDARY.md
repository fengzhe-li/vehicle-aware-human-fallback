# Branch D0: State-Dependent Handover Boundary — Analytical Challenge

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** D0 is PARTIAL / MODEL-VALID: a closed-form longitudinal requirement inside a deterministic, open-loop, 1-D, saturated-braking, stationary-hazard model. It is one slice of the deterministic precursor `T_available >= T_required`, not a completed vehicle-response layer and not a system-level synthesis (NOT STARTED / GATED). Its `t1 + t2 + t3/2` structure and `−a·t3²/24` term are prior-art-compatible mechanics, not novel results. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** Complete
**Date:** 2026-09-21
**Classification:** **D0-B: ANALYTICAL CORE + BOUNDED NUMERICAL MAPPING**
**(Simulation Experiment D1 KILLED / NOT REQUIRED)**
**Parent Baseline:** Commit `4778f22` (C0 claim cleanup passed, 26 tests green, `phase0-frozen` at `bc21fbc`)
**Claim Level:** **TYPE 1 (Analytical Functional Form)** & **TYPE 2 (Numerical Boundary Conditional on Counterfactual $t_{buildup}$)** per [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md)

---

## 1. Motivation: Challenging the Fixed Takeover Lead-Time Paradigm

In automated driving human-factors literature and system design (e.g. ISO/TR 21959, standard driving-simulator studies L001, L002, L007), Takeover Request (TOR) lead time is predominantly evaluated or calibrated as a single, fixed time constant:
$$T_{TOR} \in \{2.5\text{ s}, 3.0\text{ s}, 4.0\text{ s}, 5.0\text{ s}\}$$

This practice implicitly assumes that a scalar lead-time threshold can demarcate "safe" from "unsafe" fallback transitions across diverse driving contexts.

The goal of this **D0 Analytical Challenge** is to subject this fixed-TOR paradigm to rigorous physical scrutiny within the validated project model:
> **Can a single scalar TOR lead time equal the minimum required fallback time across the admissible, literature-supported physical variation in vehicle speed, human reaction latency, pre-braking vehicle response, brake build-up, and road conditions?**

Rather than asserting that "more warning time is always safer" (a trivial truism), D0 mathematically derives the exact functional form of the **Minimum Required Fallback Time ($T_{required}$)** and evaluates the state-dependent requirement spread across the admissible domain within the current model.

---

## 2. Current Accepted Causal Model

Following the verified outcomes of A0, A1, B0, and C0:

1. **Pre-Takeover Kinematics (B0):** The vehicle state at the moment of TOR issuance ($t = 0$) is completely summarized by position $x(0) = 0$ and current velocity $v_0$. Pre-takeover acceleration history has zero independent carry-over effect in the current Markovian model.
2. **Pre-Human Longitudinal Response (A1):** During the driver's reaction latency $[0, t_1)$, where $t_1 = t_{reaction}$, the automation withdrawal policy and powertrain determine deceleration $a_{pre} \ge 0$ (coded as `a_coast`).
   - Under $W0$: $a_{pre} = 0.0$ (speed held constant).
   - Under $W1$: $a_{pre} \in [1.0, 4.0]\text{ m/s}^2$ (active powertrain deceleration, e.g. regenerative or engine braking).
   - Velocity at human brake onset: $v_1 = v_0 - a_{pre} t_1$.
   - Displacement during latency: $x_1 = v_0 t_1 - \frac{1}{2} a_{pre} t_1^2$.
3. **Human Driver Model (C0):** The human driver executes an open-loop emergency full-braking step demand ($u=1.0$) after latency $t_1$. Internal-model mismatch $M$ is excluded as unidentifiable from existing empirical data.
4. **Brake Hardware Transients (A0):** Deceleration builds up following dead time $t_2 = t_{delay}$ and linear ramp $t_3 = t_{buildup}$ to steady-state maximum deceleration $a_{max}$.
5. **Recoverability Condition:** Safe recovery before a stationary hazard at initial distance $d_0$ requires $D_{stop} \le d_0$. For a hazard encountered at initial distance $d_0 = v_0 \cdot T_{available}$, the required lead time is governed by the frozen Phase-0 criteria.

---

## 3. Derivation of the State-Dependent Required Fallback Time ($T_{required}$)

From the validated closed-form stopping distance under pre-braking deceleration $a_{pre}$:
$$D_{stop} = x_1 + \frac{v_1^2}{2 a_{max}} + v_1 \left( t_2 + \frac{t_3}{2} \right) - \frac{a_{max} t_3^2}{24}$$

Expanding $v_1 = v_0 - a_{pre} t_1$ and $x_1 = v_0 t_1 - \frac{1}{2} a_{pre} t_1^2$:
$$D_{stop} = \frac{v_0^2}{2 a_{max}} + v_0 \left[ t_1 + t_2 + \frac{t_3}{2} - \frac{a_{pre} t_1}{a_{max}} \right] + K_0$$
where $K_0$ is the distance offset:
$$K_0 = - a_{pre} t_1 \left( \frac{t_1}{2} + t_2 + \frac{t_3}{2} \right) + \frac{(a_{pre} t_1)^2}{2 a_{max}} - \frac{a_{max} t_3^2}{24}$$

Dividing by $v_0$ yields the exact closed-form expression for **$T_{required}$**:

$$\mathbf{T_{required}(v_0, t_1, a_{pre}, t_2, t_3, a_{max}) = \frac{v_0}{2 a_{max}} + t_1 + t_2 + \frac{t_3}{2} - \frac{a_{pre} t_1}{a_{max}} + \frac{K_0}{v_0}}$$

Under baseline policy $W0$ ($a_{pre} = 0$), this simplifies to:
$$T_{required}(W0) = \frac{v_0}{2 a_{max}} + t_1 + t_2 + \frac{t_3}{2} - \frac{a_{max} t_3^2}{24 v_0}$$

### 3.1 Reconciling the Two Frozen Phase-0 $T_{TOR}$ Criteria

Earlier Phase-0 architecture ([`experiments/A_brake_response/metric_definitions.md`](../../experiments/A_brake_response/metric_definitions.md)) froze two transparent criteria for $T_{TOR\_critical}$:
1. **Criterion 1 (Collision-Free Boundary):** Smallest $T_{TOR}$ such that $\text{stopping\_margin} \ge 0$.
   In closed form, this is exactly:
   $$T_{required, 1} = \frac{D_{stop}}{v_0}$$
2. **Criterion 2 (Resolvable-Margin Boundary):** Smallest $T_{TOR}$ such that $\text{stopping\_margin} \ge \Delta x_{robust} = a_{max} \cdot dt^2$ (a threshold tied to the numerical discretization near full stop).
   In closed form, this is:
   $$T_{required, 2} = \frac{D_{stop} + a_{max} \cdot dt^2}{v_0} = T_{required, 1} + \frac{a_{max} \cdot dt^2}{v_0}$$

**Analytical Equivalence & Separation:**
- In the continuous analytical limit ($dt \to 0$), Criterion 2 converges identically to Criterion 1 ($\lim_{dt \to 0} T_{required, 2} = T_{required, 1}$).
- In discrete simulation with nominal $dt = 0.001\text{ s}$ and $a_{max} = 8.5\text{ m/s}^2$, $\Delta x_{robust} = 8.5 \times 10^{-6}\text{ m}$, shifting $T_{required}$ by $< 5 \times 10^{-7}\text{ s}$ ($< 1\ \mu\text{s}$).
- Criterion 1 represents the exact physical collision boundary, while Criterion 2 confirms its numerical robustness against discretization artifacts. In this analytical treatment, Criterion 1 is reported as the physical boundary.

---

## 4. Analytical Sensitivity & Partial Derivatives

We compute the exact partial derivatives of $T_{required}$ with respect to all constituent system variables:

### 4.1 Velocity Dependence ($\partial T / \partial v_0$)
$$\frac{\partial T_{required}}{\partial v_0} = \frac{1}{2 a_{max}} - \frac{K_0}{v_0^2}$$
- Because $K_0 < 0$ across all admissible vehicle parameters, $- K_0 / v_0^2 > 0$.
- Thus, **$\frac{\partial T_{required}}{\partial v_0} > 0$ strictly everywhere**.
- **Physical Rate:** At dry asphalt braking ($a_{max} = 8.5\text{ m/s}^2$), the marginal cost of speed is $\approx \frac{1}{17} \approx 0.059\text{ s}$ of required warning time per $1\text{ m/s}$ increase in cruising speed ($\approx 0.16\text{ s}$ per $10\text{ km/h}$).

### 4.2 Human Reaction Latency ($\partial T / \partial t_1$)
$$\frac{\partial T_{required}}{\partial t_1} = 1 - \frac{a_{pre}}{a_{max}} - \frac{a_{pre}}{v_0} \left( t_1 + t_2 + \frac{t_3}{2} - \frac{a_{pre} t_1}{a_{max}} \right)$$
- Under $W0$ ($a_{pre} = 0$): **$\frac{\partial T_{required}}{\partial t_1} \equiv 1.0$ identically**. Every millisecond of driver reaction delay requires exactly one millisecond of additional TOR lead time.
- Under $W1$ ($a_{pre} > 0$): $\frac{\partial T_{required}}{\partial t_1} < 1.0$, proving that active pre-braking deceleration softens the safety penalty of human reaction latency.

### 4.3 Pre-Human Longitudinal Response ($\partial T / \partial a_{pre}$)
$$\frac{\partial T_{required}}{\partial a_{pre}} = - \frac{t_1}{a_{max}} - \frac{t_1}{v_0} \left( \frac{t_1}{2} + t_2 + \frac{t_3}{2} - \frac{a_{pre} t_1}{a_{max}} \right) < 0$$
- Strictly negative: pre-braking deceleration unequivocally reduces the required warning budget.
- For typical parameters ($v_0 = 20\text{ m/s}, t_1 = 1.0\text{ s}, a_{max} = 8.5\text{ m/s}^2$), each $1.0\text{ m/s}^2$ of pre-braking deceleration saves $\approx 0.15 - 0.20\text{ s}$ of required warning time.

### 4.4 Brake Actuation Delay ($\partial T / \partial t_2$)
$$\frac{\partial T_{required}}{\partial t_2} = 1 - \frac{a_{pre} t_1}{v_0} > 0$$
- Shifting brake actuation delay by $\Delta t_2$ adds almost exactly $\Delta t_2$ to required TOR time.

### 4.5 Deceleration Build-Up Ramp ($\partial T / \partial t_3$)
$$\frac{\partial T_{required}}{\partial t_3} = \frac{1}{2} - \frac{a_{pre} t_1}{2 v_0} - \frac{a_{max} t_3}{12 v_0} > 0$$
- Increases required warning time at a slope of approximately $0.45 - 0.50\text{ s/s}$.

### 4.6 Maximum Braking Capability ($\partial T / \partial a_{max}$)
$$\frac{\partial T_{required}}{\partial a_{max}} = - \frac{v_0}{2 a_{max}^2} + \frac{a_{pre} t_1}{a_{max}^2} - \frac{(a_{pre} t_1)^2}{2 a_{max}^2 v_0} - \frac{t_3^2}{24 v_0} < 0$$
- Strictly negative: lower tire-road friction or reduced braking capability sharply escalates required fallback time, scaling quadratically with $1 / a_{max}^2$.

---

## 5. Dominance Hierarchy of Handover Factors

From the closed form and partial derivatives, we establish the quantitative dominance hierarchy:

| Rank | Parameter / Factor | Admissible Variation ($\Delta$) | Impact on Required Time ($\Delta T_{required}$) | Provenance Status |
| :---: | :--- | :---: | :---: | :---: |
| **1** | **Road Friction / $a_{max}$** | $4.9 - 8.5\text{ m/s}^2$ (wet vs dry) | **$+0.80\text{ s}$ to $+1.45\text{ s}$** | `COUNTERFACTUAL_SENSITIVITY` (simplified friction-limited sensitivity) |
| **2** | **Initial Cruising Speed ($v_0$)** | $10 - 30\text{ m/s}$ ($36 - 108\text{ km/h}$) | **$+1.18\text{ s}$ to $+1.25\text{ s}$** | `CORE_EMPIRICAL` |
| **3** | **Human Reaction Time ($t_1$)** | $0.7 - 1.5\text{ s}$ (expected vs surprise) | **$+0.60\text{ s}$ to $+0.80\text{ s}$** | `CORE_EMPIRICAL` / `LITERATURE_CONSTRAINED` |
| **4** | **Pre-Human Deceleration ($a_{pre}$)** | $0.0 - 3.0\text{ m/s}^2$ ($W0$ vs $W1$ powertrain/regen) | **$-0.30\text{ s}$ to $-0.58\text{ s}$** | `EMPIRICAL_RANGE` |
| **5** | **Brake Build-up Ramp ($t_3$)** | $0.10 - 0.50\text{ s}$ (fast vs slow ramp) | **$+0.15\text{ s}$ to $+0.19\text{ s}$** | `COUNTERFACTUAL_SENSITIVITY` |
| **6** | **Brake Actuation Delay ($t_2$)** | $0.05 - 0.17\text{ s}$ (actuation lag) | **$+0.10\text{ s}$ to $+0.12\text{ s}$** | `EMPIRICAL_RANGE` |
| **7** | **$a_{pre} \times t_3$ Interaction** | Full core grid | **$\le 0.07\text{ s}$** | Analytical cross-term |

---

## 6. Parameter Provenance & Admissible Domains

We partition all parameters into their established provenance classes:

| Parameter | Symbol | Units | Admissible Domain | Provenance Class | Evidence Source |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Initial Velocity** | $v_0$ | $\text{m/s}$ | $[10.0, 30.0]$ | `CORE_EMPIRICAL` | Standard operational speeds ($36 - 108\text{ km/h}$) |
| **Reaction Latency** | $t_1$ | $\text{s}$ | $[0.7, 1.5]$ | `CORE_EMPIRICAL` | Human factors literature (L001, L014; nominal midpoint $1.0\text{ s}$) |
| **Pre-Braking Decel** | $a_{pre}$ | $\text{m/s}^2$ | $[0.0, 3.0]$ | `EMPIRICAL_RANGE` | D004 EV telemetry & SAE coast-down literature ($a_{coast}$) |
| **Brake Delay** | $t_2$ | $\text{s}$ | $[0.05, 0.17]$ | `EMPIRICAL_RANGE` | Paquette & Porter (2014) light vehicle brake lag |
| **Brake Build-up** | $t_3$ | $\text{s}$ | $[0.10, 0.50]$ | `COUNTERFACTUAL_SENSITIVITY` | Counterfactual ramp range (nominal baseline $0.30\text{ s}$) |
| **Max Deceleration** | $a_{max}$ | $\text{m/s}^2$ | $[8.0, 9.0]$ (dry baseline $8.5$) | `LITERATURE_CONSTRAINED` | Emergency passenger car braking literature |
| **Friction Sensitivity** | $a_{max, wet}$ | $\text{m/s}^2$ | $4.9$ ($\mu = 0.50$) | `SENSITIVITY_ONLY` | Simplified friction-limited braking sensitivity $a_{max} = \mu \cdot g$ |

---

## 7. Claim-Level Audit & Domain Partitioning

Per the project claim ladder ([`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md)), the **analytical functional form** of $T_{required}$ is a mathematically proven kinematic deduction (**TYPE 1**).

However, any **numerical boundary evaluation** is bounded by its least-supported parameter input. Because the brake-response build-up ramp $t_3 = t_{buildup} = 0.30\text{ s}$ carries `COUNTERFACTUAL_SENSITIVITY` provenance (TYPE 2), all numerical boundary evaluations conditional on this value inherit **TYPE 2** status. No numerical boundary in this model can claim TYPE 3 (empirical finding) until brake build-up ramp timing is empirically grounded.

We partition numerical evaluations across two domains:

### Boundary 1: Core Domain Numerical Mapping (TYPE 2)
Evaluated across core empirical and literature ranges ($v_0, t_1, a_{pre}, t_2$), conditional on nominal dry-road deceleration ($a_{max} = 8.5\text{ m/s}^2$) and nominal build-up ($t_3 = 0.30\text{ s}$):
- $v_0 \in [10.0, 30.0]\text{ m/s}$
- $t_1 \in [0.7, 1.5]\text{ s}$
- $a_{pre} \in [0.0, 3.0]\text{ m/s}^2$
- $t_2 \in [0.05, 0.17]\text{ s}$

**Numerical Results across Core Domain (54 grid points):**
- **$T_{required, min}$:** **$1.15\text{ s}$** (low speed $10\text{ m/s}$, alert driver $0.7\text{ s}$, strong pre-decel $3.0\text{ m/s}^2$, fast brake delay $0.05\text{ s}$)
- **$T_{required, max}$:** **$3.58\text{ s}$** (highway speed $30\text{ m/s}$, surprise reaction $1.5\text{ s}$, zero pre-decel $W0$, slow brake delay $0.17\text{ s}$)
- **Mean $T_{required}$:** $2.25\text{ s}$
- **Core Modeled Span ($\Delta T_{core}$):** **$2.44\text{ s}$**
  *(Note: This span represents the deterministic range across the specified parameter extrema in the model; it is not a population distribution or probability quantile.)*

### Boundary 2: Sensitivity Extension Mapping (TYPE 2)
Extending the domain to assess sensitivity under counterfactual build-up ($t_3 \in [0.10, 0.50]\text{ s}$) and simplified friction-limited sensitivity ($a_{max} = 4.9\text{ m/s}^2$):
- **$T_{required, min}$:** **$1.07\text{ s}$**
- **$T_{required, max}$:** **$4.98\text{ s}$**
- **Extended Modeled Span ($\Delta T_{ext}$):** **$3.91\text{ s}$**
  *(Deterministic range over the full sensitivity grid; not a population distribution.)*

---

## 8. Fixed-TOR Adequacy Analysis: State-Invariant Minimum vs Worst-Case Fixed Bound

The $2.44\text{ s}$ core modeled span (and $3.91\text{ s}$ sensitivity span) demonstrates the exact physical relationship between fixed-time policies and state-dependent requirements:

```
[ T_required Spectrum ]
1.0s ------------ 2.0s ------------ 3.0s ------------ 4.0s ------------ 5.0s
|<- Minimum Core    |                 |                 |                  |
   (1.15s)          |                 |                 |                  |
                    |                 |                 |                  |
                    v                 |                 v                  v
             Fixed TOR = 2.5s         |          Fixed TOR = 4.0s    Max Sensitivity
                    |                 |                 |               (4.98s)
                    |                 v                 |
                    |          Max Core (3.58s)         |
                    |                                   |
[ UNDER-PROTECTIVE ZONE ]                [ OVER-CONSERVATIVE ZONE ]
Fixed 2.5s falls short in highway,       Fixed 4.0s exceeds requirement
surprise, or low-friction states         in low-speed, high-regen, alert states
(Modeled requirement up to 3.58s - 4.98s)(Modeled requirement only 1.15s)
```

### Key Conceptual Distinction:
1. **State-Invariant Minimum: NOT SUPPORTED.**
   Because $T_{required}$ is fundamentally state-dependent, no single scalar lead time can simultaneously equal the minimum required fallback lead time across heterogeneous operational states.
2. **Worst-Case Fixed Bound: FEASIBLE IN BOUNDED DOMAIN.**
   A fixed TOR policy is not mathematically impossible. A system can guarantee collision-free stopping across a bounded parameter domain by fixing $T_{fixed} \ge \max_{\Omega} T_{required}$ (e.g. $T_{fixed} = 3.6\text{ s}$ for the core domain, or $5.0\text{ s}$ under wet friction). However, this worst-case fixed bound incurs an over-conservatism penalty in easier driving states:
   - In highway scenarios ($v_0 = 30\text{ m/s}$) with a surprised driver ($t_1 = 1.5\text{ s}$) under $W0$, a moderate fixed TOR of $2.5\text{ s}$ falls short by **$1.08\text{ s}$** of warning time ($32.4\text{ m}$ of modeled stopping distance).
   - Conversely, setting a conservative fixed TOR of $3.6\text{ s}$ demands handover **$2.45\text{ s}$ earlier than required** in urban, high-regen, alert driver states ($T_{required} = 1.15\text{ s}$), unnecessarily consuming available headway.

---

## 9. State-Aware Fallback Boundary Formulation

We replace the fixed-time concept with a **State-Aware Fallback Boundary**:

$$\mathcal{R}_{safe} = \left\{ (v_0, T_{avail}, \mathbf{\theta}) \;\middle|\; T_{avail} \ge T_{required}(v_0, \mathbf{\theta}) \right\}$$
$$\mathcal{R}_{unsafe} = \left\{ (v_0, T_{avail}, \mathbf{\theta}) \;\middle|\; T_{avail} < T_{required}(v_0, \mathbf{\theta}) \right\}$$

where $\mathbf{\theta} = (t_1, a_{pre}, t_2, t_3, a_{max})$ represents the vehicle-driver parameter vector.

### Distinction from Finished Envelope:
This formulation represents a **modeled physical recoverability boundary**, not a finished "Human Fallback Safety Envelope." It maps deterministic recoverability under frozen open-loop assumptions; it does not assign subjective probabilities, nor does it model closed-loop driver steering avoidance.

---

## 10. Relationship to Prior Branches

1. **Relation to A1 (Withdrawal-Induced Deceleration):**
   D0 directly incorporates the A1 finding: $a_{pre}$ (the pre-human deceleration) reduces $T_{required}$ by up to $0.58\text{ s}$, proving that powertrain handover architecture directly expands the physical recoverability region.
2. **Relation to B0 (Risk-State Escalation):**
   Following B0's State-Mediation Invariance finding, D0 takes the current kinematic velocity $v_0$ at TOR onset as the state input. Historical acceleration authority prior to TOR is excluded because its physical effect is 100% mediated by $v_0$.
3. **Relation to C0 (Driver Internal Model):**
   Following C0's identifiability challenge, driver internal-model mismatch $M$ is excluded. Human response is held at the empirical benchmark ($t_1 \in [0.7, 1.5]\text{ s}, u=1.0$), ensuring the boundary remains mathematically defensible.

---

## 11. Limitations

1. **Simplified Friction Model:** Road friction is modeled strictly via steady-state deceleration scaling $a_{max} = \mu \cdot g$. ABS pressure cycling, tire slip transients, and load transfer are not modeled.
2. **Open-Loop Panic-Braking Assumption:** The human response is an open-loop step to $u=1.0$. Steering avoidance or gradual pedal modulation is not represented.
3. **Deterministic Bounds:** Outcomes reflect deterministic parameter ranges; they do not represent population crash probabilities.

---

## 12. Classification and Gate Decision

### Formal Decision: **D0-B: ANALYTICAL CORE + BOUNDED NUMERICAL MAPPING**
**(Simulation Experiment D1 is KILLED / NOT REQUIRED)**

### Justification:
1. **Analytical Sufficiency (D0-A):** The required-time boundary $T_{required}(v_0, \mathbf{\theta})$ is completely solved in closed form. A forward numerical simulation (D1) would simply execute bisection root-finding using the simulator to rediscover the exact same algebraic numbers down to floating-point precision, adding zero scientific information.
2. **Bounded Evaluation (D0-B):** The discrete evaluation over the 54 core grid points and 216 sensitivity points completely quantifies the boundary spread ($1.15 - 3.58\text{ s}$ core; $1.07 - 4.98\text{ s}$ extension) without running any dynamic simulator loops.
3. **Rejection of D1 (D0-C):** There is no unresolved non-separable dynamic that requires numerical experimentation. D1 is killed.


---

## 13. Minimal Next Task (Non-Simulation Tabulation)

Because the boundary is analytical, no numerical simulation code will be written. If desired in a future consolidation pass, the 54-point core lookup table can be formatted into an exportable reference artifact for the project's final synthesis.

---

## 14. Programmatic Verification

The derivations in this document are verified in [`tests/test_d0_analytical_boundary.py`](../../tests/test_d0_analytical_boundary.py):
- `test_t_required_matches_oracle`: Verifies closed-form formula matches validated analytical oracles to machine precision.
- `test_derivative_signs`: Verifies all partial derivative signs.
- `test_w0_reaction_time_derivative_is_unity`: Confirms $\partial T / \partial t_1 \equiv 1.0$ under $W0$.
- `test_spread_across_domains`: Programmatically confirms the $2.44\text{ s}$ core spread and $3.91\text{ s}$ extension spread.
- `test_recoverability_region_consistency`: Confirms $T_{avail} \ge T_{required} \iff \text{Margin} \ge 0$.
