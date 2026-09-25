# Experiment A1 Results: Withdrawal-Induced Longitudinal Response × Brake-Response Architecture

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** A1 is a MODEL-VALID counterfactual parameter mapping (decision: NARROW). W0/W1 are Phase 0.4 abstractions, not original charter RQs. Immediate withdrawal (W1) is not representative of regulated L3 transition behaviour: UN Regulation No. 157 (ALKS) requires the system to keep operating during a transition demand and to be capable of a minimum-risk manoeuvre. The "dominant first-order effect" of pre-braking deceleration holds inside the model and depends on the chosen `a_coast`/`a_pre` range; it is not empirical evidence about real vehicles. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** Completed Experiment Report & Claim Audit.
**Gate A1 Decision:** **A1: NARROW**
**Claim Level:** **EMPIRICALLY-CONSTRAINED SIMULATION** (for pre-human-braking coast response $a_{coast}$) / **COUNTERFACTUAL SIMULATION** (for brake build-up transient $t_{buildup}$ and $v_{rolloff}$).

---

## 1. Research Question, Estimand Clarification, and Framing

### Research Question
> Does automation withdrawal policy interact with vehicle longitudinal response architecture strongly enough to materially alter the recoverability boundary of a time-critical human fallback?

### Distinguishing Analytical Prior from Simulation Findings
- **Analytical Prior (Phase 0.4):**
  Phase 0.4 established via symbolic derivation (`experiments/A_brake_response/analytical_sanity_check.md` and `docs/CAUSAL_MODEL.md`) that the mixed second derivative of stopping distance with respect to uncommanded coast deceleration $a_{coast}$ and brake build-up ramp time $t_{buildup}$ is:
  $$\frac{\partial^2 D_{stop}}{\partial a_{coast} \partial t_{buildup}} = -\frac{t_{reaction}}{2}$$
  Because this cross-partial is non-zero for any $t_{reaction} > 0$, structural mathematical non-additivity is a proven property of the governing kinematic equations. **A1 does not claim to "discover an interaction."**
- **New A1 Simulation Result:**
  A1 evaluates the quantitative magnitude of this interaction across the parameter domain permitted by Phase-0 evidence, maps how it shifts critical takeover lead times ($T_{TOR\_critical}$) and stopping margins, benchmarks effect sizes against pre-registered evidence-based comparators, and identifies whether it moves actual collision recoverability boundaries in realistic fallback scenarios.

### Causal Estimand Clarification: Policy Label vs Physical Response
A critical post-experiment audit establishes the exact causal path identified by the simulator:
1. **Control Policy / Ownership Semantics:** Determines the system authority rule during $[0, t_{reaction})$:
   - $W0$: Automation retains longitudinal control, holding steady cruise speed $v_0$ ($a(t) = 0.0\text{ m/s}^2$).
   - $W1$: Automation withdraws longitudinal propulsion immediately at TOR ($t = 0$), leaving the vehicle in an uncommanded state.
2. **Withdrawal-Induced Longitudinal Response:** In the uncommanded state under $W1$, the physical vehicle powertrain and road/aerodynamic drag produce deceleration $a(t) = -a_{coast}$.
3. **Vehicle Brake-Buildup Transient:** After human brake pedal onset at $t_{reaction}$, hydraulic/actuation delay $t_{delay}$ and linear ramp build-up $t_{buildup}$ govern deceleration toward $a_{max}$.

**The Policy-Label Invariance Principle:**
The semantic policy label (`W0` vs `W1`) is not an independent physical actuator. When uncommanded coast deceleration is set to zero ($a_{coast} = 0.0\text{ m/s}^2$), the physical acceleration trajectory under $W1$ is identical to $W0$ ($a(t) = 0.0$ for $t < t_{reaction}$). Controlled simulation tests confirm that under $a_{coast} = 0$, all stopping distances, safety margins, collision flags, and critical takeover times under $W1$ are **bit-identical** to $W0$.
Therefore, the simulator does not identify an abstract "policy effect"; it identifies **the physical effect of pre-human-braking longitudinal deceleration ($a_{coast}$) enabled by automation withdrawal**, and its downstream interaction with the post-takeover brake build-up transient ($t_{buildup}$).

---

## 2. Experimental Design and Factorial Structure

A1 was executed using a three-stage progressive protocol:
1. **Stage A1.0 — Diagnostic Sanity Cases:** Hand-inspectable matched conditions ($N=4$) under a marginal scenario ($v_0 = 20.0\text{ m/s}$, $\text{TOR} = 2.5\text{ s}$, $x_{hazard} = 50.0\text{ m}$) verifying full-state trajectory kinematics, event transitions, and analytical directionality.
2. **Stage A1.1 — Empirically Admissible Core Sweep:** Full factorial sweep ($N = 2,080$ trajectory runs, $N = 80$ bisection $T_{TOR\_critical}$ searches, $N = 24$ interaction contrasts):
   - **Withdrawal Policy Mode:** $\{W0, W1\}$
   - **Uncommanded Coast Deceleration $a_{coast}$:** $\{0.0, 1.0, 2.0, 3.0, 4.0\}\text{ m/s}^2$
   - **Brake Build-up Time $t_{buildup}$:** $\{0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7\}\text{ s}$
   - **Takeover Warning Budget $\text{TOR\_lead\_time}$:** $13$ values spanning $[1.5, 4.0]\text{ s}$ (covering hopeless, marginal, and easy recoverability bands)
   - **Initial Cruise Speed $v_0$:** $\{20.0, 30.0\}\text{ m/s}$ ($72$ and $108\text{ km/h}$)
3. **Stage A1.2 — Sensitivity and Robustness Checks:** Benchmarking against low-speed regenerative torque roll-off ($v_{rolloff}$), human reaction time perturbation (Comparator A), numerical noise floor (Comparator B), and wet road friction ($\mu = 0.7$).

---

## 3. Parameter Provenance and Controlled Invariants

Every parameter used in A1 was audited against `research/parameter_provenance/phase1A_parameter_table.csv` and frozen in `experiments/A_brake_response/a1_parameter_manifest.csv`:

| Parameter | Role | Value / Range | Unit | Provenance | Classification |
|---|---|---|---|---|---|
| $t_{reaction}$ | Frozen human reaction time | $1.0$ (range $0.7 - 1.5$) | s | Literature bounds (expected vs surprise paradigms, L014) | `EMPIRICAL_RANGE` |
| $u_{accel}(t)$ | Driver throttle command | $0.0$ (identically) | — | L3 out-of-loop handover framing (`control_input_definition.md`) | `CONTROLLED` |
| $u_{brake}(t)$ | Driver brake command | Step to $1.0$ at $t_{reaction}$ | — | Fixed open-loop emergency step (`control_input_definition.md`) | `CONTROLLED` |
| $a_{max}$ | Peak braking deceleration | $8.5$ (range $8.0 - 9.0$) | m/s² | Dry asphalt emergency braking consensus | `EMPIRICAL_RANGE` |
| $t_{delay}$ | Brake actuation delay | $0.10$ (range $0.05 - 0.17$) | s | Paquette & Porter (2014) friction brake data | `EMPIRICAL_RANGE` |
| $a_{coast}$ | Uncommanded coast deceleration | $0.0$ (no-coast) vs $1.0 - 4.0$ (regen) | m/s² | OpenLKA EV Kinematic fleet D004 + SAE 2012-01-0616 | `EMPIRICAL_RANGE` |
| $t_{buildup}$ | Deceleration ramp time | $0.0$ (R0) vs $0.50$ (R2, sweep $0.1-0.7$) | s | arXiv:2112.09074 (downgraded to counterfactual in Phase 0.3) | `COUNTERFACTUAL_SENSITIVITY` |
| $v_0$ | Cruise speed | $20.0$ ($72\text{ km/h}$), $30.0$ ($108\text{ km/h}$) | m/s | Representative road speeds (`project_charter.md`) | `CONTROLLED` |
| $\text{TOR}$ | Warning lead time | $1.5 - 4.0$ | s | Spanning hopeless, marginal, and easy bands | `CONTROLLED` |
| $\mu$ | Road friction coefficient | $1.0$ (dry) / $0.7$ (wet) | — | `gate_A_preregistration.md` | `CONTROLLED` |
| $v_{threshold}$ | Roll-off threshold speed | $5.0$ | m/s | EV powertrain explainers + patent literature | `COUNTERFACTUAL_SENSITIVITY` |
| $floor$ | Residual roll-off fraction | $0.2$ | — | EV powertrain explainers + patent literature | `COUNTERFACTUAL_SENSITIVITY` |
| $dt$ | Numerical timestep | $0.001$ (sensitivity halving $0.0005$) | s | Validated in A0 (`docs/MINIMAL_SIMULATOR_SPEC.md`) | `CONTROLLED` |

### Design-Matrix Invariant Verification
A programmatic invariant check (`src/experiments/a1_runner.py::assert_design_matrix_invariants`) was executed across all matched conditions. It verified that changing treatment (withdrawal policy, $a_{coast}$, or $t_{buildup}$) caused zero alteration of non-treatment variables ($v_0$, $x_{hazard}$, $t_{reaction}$, $a_{max}$, $t_{delay}$, $dt$). Sampled brake command arrays $u_{brake}(t)$ were verified to be bit-identical across all treatment conditions.

---

## 4. Primary Outcomes and Interaction Definition

Primary recoverability metrics were computed per `experiments/A_brake_response/metric_definitions.md`:
1. **$T_{TOR\_critical}$ (s):** Smallest warning lead time achieving $\text{stopping\_margin} \ge 0.0\text{ m}$.
2. **$\text{stopping\_margin}$ (m):** $x_{hazard} - x_{stop\_full}$ under continued counterfactual integration.
3. **$\text{collision}$ (bool):** Derived strictly as $(\text{stopping\_margin} < 0)$.
4. **$\text{impact\_speed}$ (m/s):** Speed at $x_{hazard}$ crossing if collision, else `NaN`.
5. **$\text{TTC\_min}$ (s):** Minimum TTC over $[t_{reaction}, t_{stop\_or\_collision}]$, $0.0$ on collision.

### 2×2 Interaction Contrast Definition
For any outcome $Y$, the empirical interaction contrast between withdrawal-induced coasting ($\{W0, W1\}$ under coast deceleration $a_{coast}$) and vehicle build-up transient ($\{R0, R2\}$, where $t_{buildup}(R0) = 0.0\text{ s}$ and $t_{buildup}(R2) = t_b$) is:
$$I_Y = [Y(W1, R2) - Y(W0, R2)] - [Y(W1, R0) - Y(W0, R0)]$$

For stopping distance $D_{stop}$, the theoretical analytical interaction is:
$$I_D = -\frac{1}{2} a_{coast} \cdot t_{reaction} \cdot t_b$$
and for critical takeover time $T_{TOR\_critical}$:
$$I_{T_{crit}} = \frac{I_D}{v_0} = -\frac{a_{coast} \cdot t_{reaction} \cdot t_b}{2 v_0}$$

---

## 5. Empirical Results

### 5.1 Stage A1.0 Diagnostic Sanity Cases
Evaluated at $v_0 = 20.0\text{ m/s}$, $\text{TOR} = 2.5\text{ s}$ ($x_{hazard} = 50.0\text{ m}$), $t_{reaction} = 1.0\text{ s}$, $a_{max} = 8.5\text{ m/s}^2$:

| Condition ID | Policy | Vehicle Profile | $a_{coast}$ (m/s²) | $t_{buildup}$ (s) | $D_{stop}$ (m) | Stopping Margin (m) | Collision | Impact Speed (km/h) | $TTC_{min}$ (s) |
|---|---|---|---|---|---|---|---|---|---|
| **W0_R0** | W0 | Reference Friction | $0.0$ | $0.0$ | $45.53$ | $+4.47$ | **False** | NaN | $1.03$ |
| **W0_R2** | W0 | Delayed Build-up | $0.0$ | $0.50$ | $50.45$ | $-0.45$ | **True** | $9.97$ | $0.00$ |
| **W1_R0** | W1 | Regen Coast | $2.0$ | $0.0$ | $39.86$ | $+10.14$ | **False** | NaN | $1.54$ |
| **W1_R2** | W1 | Delayed + Regen | $2.0$ | $0.50$ | $44.28$ | $+5.72$ | **False** | NaN | $1.16$ |

**Diagnostic Takeaway:**
At $\text{TOR} = 2.5\text{ s}$, introducing delayed build-up ($R2$) under baseline policy $W0$ shifts the outcome into a **collision** ($\text{margin} = -0.45\text{ m}$, impact speed $10.0\text{ km/h}$). Under withdrawal policy $W1$ with active coasting ($a_{coast} = 2.0\text{ m/s}^2$), pre-braking kinetic energy dissipation ($v_1 = 18.0\text{ m/s}$, $x_1 = 19.0\text{ m}$) recovers safety margin, keeping both $R0$ ($\text{margin} = +10.14\text{ m}$) and $R2$ ($\text{margin} = +5.72\text{ m}$) safe from collision.

### 5.2 Stage A1.1 Core Interaction Contrasts
The table below reports the empirical interaction contrast on stopping distance ($I_D$) and critical TOR ($I_{T_{crit}}$) across the admissible grid ($v_0 = 20.0\text{ m/s}$):

| $a_{coast}$ (m/s²) | $t_{buildup}$ (s) | Simulated $I_D$ (m) | Analytical $I_D$ (m) | Discretization Error (m) | Simulated $I_{T_{crit}}$ (s) | Analytical $I_{T_{crit}}$ (s) | Discretization Error (s) |
|---|---|---|---|---|---|---|---|
| $1.0$ | $0.20$ | $-0.100$ | $-0.100$ | $< 10^{-14}$ | $-0.0050$ | $-0.0050$ | $2.8 \times 10^{-5}$ |
| $1.0$ | $0.50$ | $-0.250$ | $-0.250$ | $< 10^{-14}$ | $-0.0125$ | $-0.0125$ | $3.1 \times 10^{-5}$ |
| $1.0$ | $0.70$ | $-0.350$ | $-0.350$ | $< 10^{-14}$ | $-0.0175$ | $-0.0175$ | $2.4 \times 10^{-5}$ |
| $2.0$ | $0.20$ | $-0.200$ | $-0.200$ | $< 10^{-14}$ | $-0.0100$ | $-0.0100$ | $4.9 \times 10^{-5}$ |
| **$2.0$ (nominal)** | **$0.50$ (nominal)** | **$-0.500$** | **$-0.500$** | **$< 10^{-14}$** | **$-0.0251$** | **$-0.0250$** | **$5.5 \times 10^{-5}$** |
| $2.0$ | $0.70$ | $-0.700$ | $-0.700$ | $< 10^{-14}$ | $-0.0350$ | $-0.0350$ | $4.8 \times 10^{-5}$ |
| $3.0$ | $0.20$ | $-0.300$ | $-0.300$ | $< 10^{-14}$ | $-0.0151$ | $-0.0150$ | $7.0 \times 10^{-5}$ |
| $3.0$ | $0.50$ | $-0.750$ | $-0.750$ | $< 10^{-14}$ | $-0.0376$ | $-0.0375$ | $8.0 \times 10^{-5}$ |
| $3.0$ | $0.70$ | $-1.050$ | $-1.050$ | $< 10^{-14}$ | $-0.0526$ | $-0.0525$ | $7.1 \times 10^{-5}$ |
| $4.0$ | $0.20$ | $-0.400$ | $-0.400$ | $< 10^{-14}$ | $-0.0201$ | $-0.0200$ | $9.9 \times 10^{-5}$ |
| $4.0$ | $0.50$ | $-1.000$ | $-1.000$ | $< 10^{-14}$ | $-0.0501$ | $-0.0500$ | $1.0 \times 10^{-4}$ |
| $4.0$ | $0.70$ | $-1.400$ | $-1.400$ | $< 10^{-14}$ | $-0.0701$ | $-0.0700$ | $9.5 \times 10^{-5}$ |

At $v_0 = 30.0\text{ m/s}$ ($108\text{ km/h}$), the stopping distance interaction $I_D$ is identical (since $I_D = -0.5 a_{coast} t_1 t_b$ is velocity-invariant), while the critical TOR interaction scales as $I_D / v_0$:
- Nominal ($a_{coast}=2.0, t_b=0.5$): $I_D = -0.500\text{ m}$, $I_{T_{crit}} = -0.0167\text{ s}$ ($-16.7\text{ ms}$).
- Extreme ($a_{coast}=4.0, t_b=0.7$): $I_D = -1.400\text{ m}$, $I_{T_{crit}} = -0.0467\text{ s}$ ($-46.7\text{ ms}$).

### 5.3 Critical Takeover Boundary ($T_{TOR\_critical}$) Analysis
The baseline critical takeover times under $W0$ are:
- $W0 \mid R0$ ($t_b = 0.0\text{ s}$): $T_{TOR\_critical} = 2.276\text{ s}$
- $W0 \mid R2$ ($t_b = 0.5\text{ s}$): $T_{TOR\_critical} = 2.522\text{ s}$ ($\Delta T_{crit} = +0.246\text{ s}$)

Under $W1$ with nominal coast deceleration ($a_{coast} = 2.0\text{ m/s}^2$):
- $W1 \mid R0$ ($t_b = 0.0\text{ s}$): $T_{TOR\_critical} = 1.993\text{ s}$ ($\Delta T_{crit} = -0.283\text{ s}$ relative to $W0 \mid R0$)
- $W1 \mid R2$ ($t_b = 0.5\text{ s}$): $T_{TOR\_critical} = 2.214\text{ s}$ ($\Delta T_{crit} = -0.308\text{ s}$ relative to $W0 \mid R2$)

Across the full sweep, withdrawal with coasting ($W1$) reduces the minimum required warning budget by:
$$\Delta T_{TOR\_critical} \in [-0.147\text{ s}, -0.594\text{ s}]$$
depending on $a_{coast} \in [1.0, 4.0]\text{ m/s}^2$.

---

## 6. Collision-Boundary Behaviour and Grid-Percentage Claim

Across the $1,040$ matched condition pairs in the core sweep ($v_0$, $\text{TOR}$, $t_{buildup}$, $a_{coast}$):
- **Collision-to-Safe-Stop Transitions:** **170 of 1,040 matched conditions (16.35% of matched conditions in the pre-specified core simulation grid)** flip classification from **Collision under W0** to **Safe under W1**.
- **Reverse Transitions (Safe under W0 → Collision under W1):** **0 (0.0%)**. As guaranteed by non-negative coast deceleration ($a_{coast} \ge 0$), immediate withdrawal strictly improves or maintains stopping distance.
- **Interpretation of Grid Percentage:** This 16.35% figure is strictly a descriptive property of the pre-specified core simulation grid (which deliberately concentrated sampling in the marginal band). It must **not** be interpreted as a real-world driving probability, collision risk, or population crash prevalence, and it is not invariant to grid density or scenario weighting.
- **Location of Effect Concentration:** Boundary flips are concentrated entirely in the **marginal recoverability band**:
  - For $v_0 = 20.0\text{ m/s}$: $\text{TOR} \in [1.8\text{ s}, 2.5\text{ s}]$ ($x_{hazard} \in [36\text{ m}, 50\text{ m}]$).
  - For $v_0 = 30.0\text{ m/s}$: $\text{TOR} \in [2.2\text{ s}, 3.0\text{ s}]$ ($x_{hazard} \in [66\text{ m}, 90\text{ m}]$).
- In the **hopeless band** ($\text{TOR} \le 1.5\text{ s}$), both $W0$ and $W1$ result in collisions (e.g., at $\text{TOR} = 1.5\text{ s}$, impact speeds remain $> 14\text{ m/s}$).
- In the **easy band** ($\text{TOR} \ge 3.0\text{ s}$ at $72\text{ km/h}$), both $W0$ and $W1$ are collision-free with large safety margins ($> 15\text{ m}$).

---

## 7. Reassessment of the Core Scientific Result

The A1 experimental evidence separates into four distinct components:

### A. Structural Result (Non-Zero Interaction)
The analytical non-additivity between pre-human-braking deceleration and brake build-up latency is real and non-zero:
$$\frac{\partial^2 D_{stop}}{\partial a_{coast} \partial t_{buildup}} = -\frac{t_{reaction}}{2} \neq 0$$
The numerical simulator reproduces this interaction to within $10^{-14}\text{ m}$, confirming that the two mechanisms do not separate purely additively.

### B. Interaction Magnitude (Modest Effect)
The quantitative magnitude of this interaction across the entire evidenced parameter domain ($a_{coast} \in [1.0, 4.0]\text{ m/s}^2$, $t_{buildup} \in [0.1, 0.7]\text{ s}$) contributes only:
$$|I_D| \in [0.10\text{ m}, 1.40\text{ m}] \quad \text{and} \quad |I_{T_{crit}}| \le 0.070\text{ s} \ (70\text{ ms})$$
- **Comparison to Comparator B (Noise Floor: $0.005\text{ m}$):** $20\times - 280\times$ larger (robustly resolved).
- **Comparison to Comparator A (Human Reaction Time: $16.0\text{ m}$ / $0.8\text{ s}$):** $0.6\% - 8.8\%$ of Comparator A (an order of magnitude smaller).

### C. Dominant First-Order Effect (Pre-Braking Deceleration)
The first-order longitudinal response during the pre-human-braking delay ($[0, t_{reaction})$) shifts stopping distance and critical takeover budget far more substantially:
$$\Delta D_{stop} \in [5.67\text{ m}, 11.87\text{ m}] \quad \text{and} \quad \Delta T_{TOR\_critical} \in [0.28\text{ s}, 0.59\text{ s}]$$
This first-order response is $35\% - 74\%$ of Comparator A and drives virtually all observed recoverability changes.

### D. Boundary Localization
All collision-to-safe-stop transitions concentrate in the marginal band ($\Delta \text{TOR} \approx 0.3 - 0.6\text{ s}$). The interaction term alone ($I_{T_{crit}} \le 70\text{ ms}$) is capable of altering recoverability only within a narrow, knife-edge warning window.

**Scientific Synthesis:**
Result B (the cross-derivative interaction) is modest relative to Result C (the first-order withdrawal deceleration). The interaction acts as a minor moderating effect (slightly attenuating the penalty of slow friction-brake build-up because the vehicle enters braking at lower initial speed), but is not the primary driver of takeover recoverability.

---

## 8. Sensitivity Analysis (Stage A1.2)

1. **Low-Speed Regenerative Roll-off ($v_{rolloff}$):**
   Activating roll-off ($v_{threshold} = 5.0\text{ m/s}, floor = 0.2$) extends total stopping distance by $0.725\text{ m}$ in both $W0$ and $W1$. Because roll-off activates only below $5\text{ m/s}$ near standstill, its net impact on the withdrawal interaction contrast is numerically zero ($\Delta I = -1.4 \times 10^{-14}\text{ m} \approx 0$).
2. **Road Friction Perturbation ($\mu = 0.7$ Wet Asphalt Sensitivity Model):**
   Within the current low-friction sensitivity model, maximum braking capability $a_{max}$ is scaled from $8.5\text{ m/s}^2$ to $5.95\text{ m/s}^2$ ($a_{max} = \mu \cdot g$), while $t_{delay}$, $t_{reaction}$, and $a_{coast}$ remain fixed. Stopping distance increases by $8.2 - 10.1\text{ m}$, and the withdrawal effect increases from $6.17\text{ m}$ to $8.09\text{ m}$ (a $+1.92\text{ m}$ shift), demonstrating that reduced friction amplifies the value of early coast deceleration. *Limitation:* This check models steady-state friction reduction only; it does not model real-world wet-surface complexities such as tire slip transients, hydroplaning, or ABS cycling.
3. **Timestep Discretization ($dt = 0.0005\text{ s}$ vs $0.001\text{ s}$):**
   Halving $dt$ shifts simulated stopping distance by $0.005\text{ m}$ (Comparator B), confirming that numerical noise is negligible relative to all physical effects.

---

## 9. Limitations and Claim Boundaries

1. **Claim Level (`docs/CLAIM_LADDER.md`):**
   - **Pre-Human-Braking Coast Response ($a_{coast}$):** Supported at **TYPE 3 (Empirically-Constrained Simulation)**, because its numerical range ($1.0 - 4.0\text{ m/s}^2$) is grounded in fleet data (D004) and coast-down literature (SAE).
   - **Build-up Transient Interaction ($t_{buildup}$):** Supported at **TYPE 2 (Counterfactual Simulation)**, because $t_{buildup}$ remains classified as `COUNTERFACTUAL_SENSITIVITY`. Numerical agreement with the analytical oracle does not elevate counterfactual inputs to empirical claims.
2. **Explicit Non-Claims:**
   - A1 does **not** prove that electric vehicles are safer than internal combustion engine vehicles.
   - A1 does **not** imply that automation should always withdraw immediately. Immediate uncommanded deceleration under $W1$ during driver surprise could create rear-end collision hazards from trailing traffic (a multi-vehicle traffic trade-off explicitly outside this single-vehicle longitudinal scope).
   - A1 does **not** model driver closed-loop modulation or driver startle responses.

---

## 10. Gate A1 Research Decision

### Verdict: **A1: NARROW**

### Justification:
1. **The interaction mechanism is physically real and numerically verified:**
   $\partial^2 D_{stop} / (\partial a_{coast} \partial t_{buildup}) = -t_{reaction} / 2$ was verified to machine precision across all conditions, easily exceeding Comparator B (numerical noise floor) by up to $280\times$.
2. **However, practical recoverability is dominated by the first-order withdrawal deceleration, not the interaction:**
   - The primary withdrawal response shifts stopping margin by $5.7 - 11.9\text{ m}$ and critical TOR by $0.28 - 0.59\text{ s}$, flipping $16.35\%$ of matched conditions in the core simulation grid from collision into safe stop.
   - The interaction effect ($0.10 - 1.40\text{ m}$, $5 - 70\text{ ms}$) is an order of magnitude smaller than human reaction-time variability ($16.0\text{ m}$) and alters collision recoverability only within a narrow $70\text{ ms}$ warning window.

### Final Narrowed Claim:
> **"Within the current empirically constrained/counterfactual simulation model, the longitudinal vehicle response during the delay between automation handover and effective human braking can materially shift the critical fallback boundary in marginal scenarios (by $\approx 0.3 - 0.6\text{ s}$ of warning budget). Its interaction with post-takeover brake build-up is mathematically present but practically modest ($\le 0.07\text{ s}$) relative to this first-order response."**
