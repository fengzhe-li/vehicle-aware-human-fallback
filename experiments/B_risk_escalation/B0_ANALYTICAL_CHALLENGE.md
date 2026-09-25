# Branch B0: Risk-State Escalation — Analytical Challenge and Preregistration

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** B0 is a modelling remark (decision: NARROW): the mediation result holds by construction under the deterministic Markov assumptions stated here. It is not an empirical finding about acceleration authority, driver behaviour, or risk compensation. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** Complete  
**Date:** 2026-09-21  
**Classification:** **B0-A: ANALYTICAL ONLY** (Simulation Experiment B1 Killed / Reclassified)  
**Parent Baseline:** Commit `aed0e30` (A1 claim audit passed, 19 tests green, `phase0-frozen` at `bc21fbc`)  
**Claim Level:** **TYPE 1 (Analytical)** per [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md)

---

## 1. Original Motivation

In the initial project charter ([`research/project_charter.md`](../../research/project_charter.md), Section 4.1 & Section 9, Gate B), a second experimental branch was proposed: **high acceleration capability / risk-state escalation**.

The motivating hypothesis was:
> *"A vehicle with greater propulsion acceleration authority may enter a high-speed, high-energy, low-recoverability state more quickly, potentially consuming human-fallback safety margin faster before or around a time-critical automated-driving takeover request (TOR)."*

In `docs/RESEARCH_ARCHITECTURE_V1.md`, Branch B was provisionally carried forward under the survival condition that it must be tested via a controlled *"same lower-risk initial state, same-duration acceleration command, then hazard"* protocol, rather than a trivial fixed-speed braking comparison.

The explicit purpose of this **B0 Analytical Challenge** is to subject this branch to the most aggressive scientific scrutiny before writing any B-specific simulation code. Specifically, the project rule demands:
- Do not protect the original idea.
- Actively attempt to **KILL** or **RECLASSIFY** the branch.
- Determine whether the proposed phenomenon contains a scientifically non-trivial mechanism beyond the deterministic truism: *"greater acceleration over the same duration produces higher subsequent speed, which increases stopping distance."*
- Prohibit using a numerical simulator merely to rediscover a closed-form certainty.

---

## 2. The Mother Question Context

The core mother question of this research programme is:
> *"Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?"*

Branch B must **not** be allowed to drift into a generic study of:
- "High-performance cars are dangerous", or
- "Electric vehicles are more hazardous than ICE vehicles".

The treatment variable is strictly **propulsion acceleration authority** ($a_{accel} \in \mathbb{R}^+$), a physical capability of the powertrain, not a commercial propulsion label (EV vs. ICE). Furthermore, the only scientifically legitimate connection to the mother question is through **human fallback recoverability** during an automated-to-human control transfer.

The precise research question investigated in B0 is therefore:
> *"How quickly does vehicle acceleration prior to takeover move the vehicle state across the human-fallback recoverability boundary, and does vehicle propulsion capability interact non-trivially with the post-takeover fallback dynamics?"*

---

## 3. Physical State & Causal Architecture

To avoid confounding, the physical timeline is partitioned into three distinct causal stages:

```
[ Stage 0: Pre-Takeover Acceleration ]
Initial State: x(0) = 0, v(0) = v0, Hazard at x_hazard = d0
Propulsion Command: a_accel(t) over duration t_accel
        |
        v
Kinematic State at TOR (t = t_accel):
x_tor = v0·t_accel + 0.5·a_accel·t_accel²
v_tor = v0 + a_accel·t_accel
        |
        v
[ Stage 1: Handover & Automation Withdrawal ] (t ∈ [t_accel, t_accel + t_reaction))
Automation Withdrawal Policy (W0 vs W1)
Longitudinal Response: a(t) = 0 (W0) or a(t) = -a_coast (W1)
Speed at human brake onset: v1 = v_tor - a_coast·t_reaction
        |
        v
[ Stage 2: Post-Takeover Human Fallback Braking ] (t ≥ t_accel + t_reaction)
Brake Hardware Response: t_delay, t_buildup ramp, a_max steady braking
Stopping Distance from TOR: D_stop(v_tor; θ_vehicle, θ_driver)
Total Stopping Location: X_stop = x_tor + D_stop(v_tor)
Fallback Safety Margin: Margin = d0 - X_stop
```

### Variable Provenance and Classification

Applying the project's evidence classification framework ([`research/parameter_provenance/`](../../research/parameter_provenance/)):

| Variable | Physical Meaning | Units | Provenance Class | Role in B0 |
| :--- | :--- | :---: | :---: | :--- |
| $v_0$ | Initial cruising speed prior to acceleration | $\text{m/s}$ | `CORE_EMPIRICAL` | Controlled base state ($10 - 30\text{ m/s}$) |
| $a_{accel}$ | Propulsion acceleration authority / realized rate | $\text{m/s}^2$ | `EMPIRICAL_RANGE` / `COUNTERFACTUAL` | Candidate Treatment ($0.5 - 6.0\text{ m/s}^2$) |
| $t_{accel}$ | Duration of acceleration command prior to TOR | $\text{s}$ | `COUNTERFACTUAL_SENSITIVITY` | Controlled scenario input ($1.0 - 5.0\text{ s}$) |
| $d_0$ | Initial distance to stationary hazard at $t=0$ | $\text{m}$ | `COUNTERFACTUAL_SENSITIVITY` | Scenario boundary geometry |
| $(x_{tor}, v_{tor})$ | Kinematic state vector at TOR onset | $\text{m}, \text{m/s}$ | `DERIVED` | **Complete State Mediator** |
| $W$ | Withdrawal policy ($W0$ vs $W1$) | — | `CONTROLLED` | A1 Handover policy axis |
| $a_{coast}$ ($a_{pre}$) | Pre-human-braking longitudinal deceleration | $\text{m/s}^2$ | `EMPIRICAL_RANGE` | $1.0 - 4.0\text{ m/s}^2$ (W1) vs $0.0\text{ m/s}^2$ (W0) |
| $t_{reaction}$ | Driver perception-reaction latency ($t_1$) | $\text{s}$ | `CORE_EMPIRICAL` | $1.0\text{ s}$ fixed open-loop benchmark |
| $t_{delay}$ | Brake hydraulic/actuator dead time ($t_2$) | $\text{s}$ | `EMPIRICAL_RANGE` | $0.05 - 0.17\text{ s}$ (Paquette & Porter 2014) |
| $t_{buildup}$ | Brake pressure rise ramp time ($t_3$) | $\text{s}$ | `COUNTERFACTUAL_SENSITIVITY` | $0.10 - 0.50\text{ s}$ |
| $a_{max}$ | Maximum steady-state braking deceleration | $\text{m/s}^2$ | `LITERATURE_CONSTRAINED` | $8.0 - 9.0\text{ m/s}^2$ (dry asphalt) |
| $X_{stop}$ | Final resting position of vehicle | $\text{m}$ | `DERIVED` | Primary outcome |
| $t_{cross}$ | Time from $t=0$ to unrecoverable boundary | $\text{s}$ | `DERIVED` | Boundary outcome |

> **Terminology Note (`a_coast` vs `a_pre`):**  
> As established in A1, the variable named `a_coast` in the codebase represents the *magnitude of pre-human-braking longitudinal deceleration* during $[0, t_{reaction})$. In production vehicles with regenerative braking or high engine drag, positive values ($1 - 4\text{ m/s}^2$) represent active powertrain deceleration rather than neutral coasting. To avoid breaking regression tests or code reproducibility, the code identifier remains `a_coast`, while conceptually and documentarily it is referred to as pre-takeover deceleration $a_{pre}$ or $a_{withdrawal}$.

---

## 4. Analytical Derivations

### 4.1 State at Takeover
Under constant propulsion acceleration $a_{accel}$ over duration $t_{accel}$:
$$v_{tor} = v_0 + a_{accel} t_{accel}$$
$$x_{accel} = v_0 t_{accel} + \frac{1}{2} a_{accel} t_{accel}^2$$

### 4.2 Post-Takeover Stopping Distance ($D_{stop}$)
From the validated A0/A1 analytical formulation ([`docs/CAUSAL_MODEL.md`](../../docs/CAUSAL_MODEL.md)), the stopping distance from TOR onset is:
$$D_{stop}(v_{tor}) = \frac{v_{tor}^2}{2 a_{max}} + K_1 v_{tor} + K_0$$
where:
$$K_1 = t_1 + t_2 + \frac{t_3}{2} - \frac{a_{coast} t_1}{a_{max}}$$
$$K_0 = - \frac{1}{2} a_{coast} t_1^2 - a_{coast} t_1 \left( t_2 + \frac{t_3}{2} \right) + \frac{(a_{coast} t_1)^2}{2 a_{max}} - \frac{a_{max} t_3^2}{24}$$

Notice that $K_1$ (effective latency, seconds) and $K_0$ (distance offset, meters) are strictly functions of post-takeover braking and human parameters ($t_1, t_2, t_3, a_{max}, a_{coast}$) and are **completely independent of $a_{accel}$ and $t_{accel}$**.

### 4.3 Total Stopping Distance ($X_{stop}$) and Margin
The total vehicle stopping coordinate relative to initial position $x(0) = 0$ is:
$$X_{stop}(a_{accel}) = x_{accel} + D_{stop}(v_{tor})$$
$$X_{stop}(a_{accel}) = \left( v_0 t_{accel} + \frac{1}{2} a_{accel} t_{accel}^2 \right) + \left[ \frac{(v_0 + a_{accel} t_{accel})^2}{2 a_{max}} + K_1 (v_0 + a_{accel} t_{accel}) + K_0 \right]$$

Expanding in powers of $a_{accel}$:
$$X_{stop}(a_{accel}) = X_{stop}(0) + a_{accel} t_{accel} \left[ \frac{1}{2} t_{accel} + \frac{v_0}{a_{max}} + K_1 \right] + a_{accel}^2 \frac{t_{accel}^2}{2 a_{max}}$$
where $X_{stop}(0) = v_0 t_{accel} + D_{stop}(v_0)$ is the stopping position under zero acceleration (pure cruise).

Against a stationary obstacle at initial distance $d_0$, the stopping margin is:
$$\text{Margin}(a_{accel}) = d_0 - X_{stop}(a_{accel})$$

### 4.4 Rate of Margin Consumption & Performance–Recovery Coupling
Differentiating $X_{stop}$ with respect to acceleration duration $t$ while accelerating at rate $a_{accel}$:
$$\frac{d X_{stop}}{d t} = v(t) + a_{accel} \left[ \frac{v(t)}{a_{max}} + K_1 \right] + \frac{a_{accel}^2 t}{a_{max}}$$

Defining the dimensionless **propulsion-to-braking capability ratio**:
$$\eta \equiv \frac{a_{accel}}{a_{max}}$$

The second-order rate of margin consumption is:
$$\frac{d^2 X_{stop}}{d t^2} = a_{accel} \left( 1 + \frac{a_{accel}}{a_{max}} \right) = a_{accel} (1 + \eta)$$

**Physical Interpretation:**  
When accelerating towards a hazard:
1. The vehicle advances kinematically at acceleration $a_{accel}$ ($\frac{1}{2} a_{accel} t^2$), consuming distance margin directly.
2. The vehicle accumulates kinetic energy at rate $v \cdot a_{accel}$, requiring additional braking distance to dissipate ($\frac{a_{accel}^2 t^2}{2 a_{max}} = \frac{1}{2} \eta a_{accel} t^2$).
3. The effective rate of risk escalation is amplified by the factor $(1 + \eta)$.  
   - In ordinary passenger vehicles under moderate ACC ($\eta \approx 1.5 / 8.5 \approx 0.18$), distance consumption is dominated by physical travel ($85\%$).
   - In high-performance vehicles at full acceleration ($\eta \approx 6.0 / 8.5 \approx 0.71$), the stopping-distance penalty adds an additional $71\%$ to the rate of margin consumption, nearly doubling the rate of risk escalation.

### 4.5 Time to Enter the Unrecoverable Region ($t_{cross}$)
Let $M_0 = d_0 - D_{stop}(v_0) > 0$ be the initial recoverability margin at $t=0$.  
The boundary of safe human fallback is crossed at the exact time $t_{cross}$ when the required stopping distance equals $d_0$:
$$X_{stop}(t_{cross}) = d_0 \iff X_{stop}(t_{cross}) - D_{stop}(v_0) = M_0$$

Substituting the kinematic trajectories:
$$\frac{a_{accel}}{2} \left( 1 + \frac{a_{accel}}{a_{max}} \right) t_{cross}^2 + \left[ v_0 + a_{accel} \left( \frac{v_0}{a_{max}} + K_1 \right) \right] t_{cross} - M_0 = 0$$

This is a standard quadratic equation $A t_{cross}^2 + B t_{cross} - M_0 = 0$ with coefficients:
$$A = \frac{a_{accel}}{2} (1 + \eta) > 0$$
$$B = v_0 + a_{accel} \left( \frac{v_0}{a_{max}} + K_1 \right) > 0$$

Because $A > 0, B > 0$, and $M_0 > 0$, Descartes' rule of signs guarantees **exactly one unique positive real root**:
$$t_{cross} = \frac{-B + \sqrt{B^2 + 4 A M_0}}{2 A} = \frac{2 M_0}{B + \sqrt{B^2 + 4 A M_0}}$$

In the limit $a_{accel} \to 0$ (steady cruise):
$$t_{cross}(0) = \frac{M_0}{v_0}$$

---

## 5. What is Mathematically Trivial

We now rigorously answer Section 2 & 6 of the prompt:

1. **Monotonicity with Speed:**
   $$\frac{\partial v_{tor}}{\partial a_{accel}} = t_{accel} > 0$$
   $$\frac{\partial D_{stop}}{\partial v_{tor}} = \frac{v_1}{a_{max}} + t_1 + t_2 + \frac{t_3}{2} > 0$$
   $$\frac{\partial D_{stop}}{\partial a_{accel}} = t_{accel} \frac{\partial D_{stop}}{\partial v_{tor}} > 0$$
   Higher acceleration over a fixed duration produces higher terminal speed, which strictly produces longer stopping distance.

2. **Monotonicity with Margin and Critical TOR:**
   $$\frac{\partial \text{Margin}}{\partial a_{accel}} = - t_{accel} \left[ \frac{1}{2} t_{accel} + \frac{v_{tor}}{a_{max}} + K_1 \right] < 0$$
   $$\frac{\partial T_{TOR\_critical}}{\partial a_{accel}} = t_{accel} \frac{\partial}{\partial v_{tor}} \left( \frac{D_{stop}(v_{tor})}{v_{tor}} \right) = t_{accel} \left[ \frac{1}{2 a_{max}} - \frac{K_0}{v_{tor}^2} \right] > 0$$
   Higher acceleration strictly consumes margin faster and requires strictly more warning lead time.

3. **Monotonicity with Time-to-Boundary:**
   $$\frac{\partial t_{cross}}{\partial a_{accel}} < 0 \quad \text{strictly everywhere}$$
   Higher acceleration strictly shortens the time window available before entering the unrecoverable state.

**Verdict on Triviality:**  
Every single one of these directional relationships is a direct, closed-form mathematical certainty of Newtonian mechanics. Setting up a numerical simulator to run forward Euler integration over a grid of $a_{accel}$ values to report that "greater acceleration authority reduces time-to-collision and increases stopping distance" would be an empty exercise in simulating trivial algebra.

---

## 6. Rigorous Test for Non-Separable Mechanisms

In Experiment A1, the branch survived because the analytical derivation revealed a **structural, non-zero interaction term** that was not an additive constant:
$$\frac{\partial^2 D_{stop}}{\partial a_{coast} \partial t_{buildup}} = - \frac{t_1}{2} \ne 0$$

We subject Branch B to the exact same standard. We test all mixed second derivatives between acceleration authority $a_{accel}$ and post-takeover parameters $Z \in \{ t_{buildup}, a_{coast}, a_{max}, t_{reaction}, t_{delay} \}$:

### 6.1 Mixed Partial with Brake Build-up ($t_3$)
$$\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial t_3} = \frac{t_{accel}}{2}$$
Is this a new physical interaction?  
Examine the origin of this term:
$$\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial t_3} = \frac{\partial}{\partial t_3} \left( \frac{\partial D_{stop}}{\partial v_{tor}} \frac{\partial v_{tor}}{\partial a_{accel}} \right) = t_{accel} \frac{\partial}{\partial v_{tor}} \left( \frac{\partial D_{stop}}{\partial t_3} \right) = t_{accel} \frac{\partial^2 D_{stop}}{\partial v_0 \partial t_3}$$
Since $\frac{\partial^2 D_{stop}}{\partial v_0 \partial t_3} = \frac{1}{2}$, the cross-partial with $a_{accel}$ is simply the cross-partial with initial velocity multiplied by $t_{accel}$. It reflects nothing more than: *"at higher speeds, a given brake build-up latency consumes more distance."*

### 6.2 Mixed Partial with Pre-Braking Deceleration ($a_{coast}$)
$$\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial a_{coast}} = - \frac{t_1 t_{accel}}{a_{max}} = t_{accel} \frac{\partial^2 D_{stop}}{\partial v_0 \partial a_{coast}}$$

### 6.3 Mixed Partial with Maximum Braking ($a_{max}$)
$$\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial a_{max}} = - \frac{t_{accel} (v_{tor} - a_{coast} t_1)}{a_{max}^2} = t_{accel} \frac{\partial^2 D_{stop}}{\partial v_0 \partial a_{max}}$$

### 6.4 State-Mediation Invariance within the Current Model
For **every** parameter $Z$ in the post-takeover system:
$$\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial Z} \equiv t_{accel} \frac{\partial^2 D_{stop}}{\partial v_0 \partial Z}$$

**Physical Scope and Model-Specific Finding:**  
Within the current deterministic Markovian longitudinal model, once the state $(x_{tor}, v_{tor})$ and the post-TOR parameters are fixed, pre-TOR acceleration history has **zero independent effect** on the post-TOR trajectory.

This is **not** a universal theorem about real physical vehicles. It holds strictly under the following explicit model assumptions:
1. **Kinematic Markov Property:** The vehicle longitudinal state is fully described by $(x, v)$; higher-order states (such as powertrain drive-by-wire lag or suspension pitch dynamics) are not modeled.
2. **No Thermal or Brake State Memory:** There is no brake pad temperature rise, friction coefficient fade, or fluid pressure lag carry-over from prior driving.
3. **No Powertrain State Carry-Over:** Inverter slew, motor flux decay, or engine/turbo spool states are assumed to terminate cleanly at TOR.
4. **No Tire Slip Memory:** Tire relaxation length, carcass compliance, and tire surface thermal dynamics are neglected.
5. **No Driver Neuromuscular or Cognitive Adaptation:** The human driver model is open-loop and identical across conditions; driver startle, arousal, or pedal expectation conditioned on prior acceleration magnitude is not modeled.
6. **Stationary Post-TOR Control Law:** The post-TOR deceleration schedule depends solely on current state and fixed vehicle/driver parameters.

If any of these assumptions change (for example, introducing brake thermal models, tire dynamics, or arousal-dependent reaction time), pre-TOR acceleration history could have non-zero physical or behavioral carry-over effects. Within the scope of the present model, however, any variation in fallback recoverability produced by $a_{accel}$ is **100% mediated by terminal speed $v_{tor}$ and position $x_{tor}$**.

---

## 7. Parameter Evidence Audit

Before considering any numerical experiment, we audit the available empirical evidence for acceleration parameters in the project repository:

| Parameter | Candidate Value / Range | Evidence Source | Provenance Class | Transferability to Takeover Fallback | Notes & Limitations |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Normal ACC Acceleration** | $0.5 - 1.5\text{ m/s}^2$ | ISO 15622 / ISO 22179 | `LITERATURE_CONSTRAINED` | HIGH | Standard operational design domain for automated speed control. Governed by passenger comfort ceilings ($\le 2.0\text{ m/s}^2$, jerk $\le 2.0\text{ m/s}^3$). |
| **Naturalistic EV Acceleration** | $0.3 - 0.7\text{ m/s}^2$ (mean) | D005 (OpenLKA Acceleration Dataset) | `EMPIRICAL_RANGE` | MEDIUM | Confirmed in Phase 0.3 forensics (`raw_dataset_forensics.md`) on `HYUNDAI_IONIQ_5_segments.json`. Consecutive segment timestamps measure $\Delta t \approx 0.10\text{ s}$ ($\approx 10\text{ Hz}$), contradicting the README's claim of 100 Hz CAN bus data. Underlying bus rate across other vehicle models or raw CAN logs remains `METADATA_UNCERTAIN`. Schema contains `v`, `a`, `t`, `padel` (normalized accelerator position, misspelled in schema). Contains **no brake channel**, **no regen field**, **no planner commands**, and **no takeover events**. |
| **Intersection Traffic Conflict Acceleration** | $1.5 - 3.5\text{ m/s}^2$ | L013 (ScienceDirect 2025) | `EMPIRICAL_RANGE` (traffic level) | LOW | Real-world study of EV vs ICE acceleration at signalized intersections in China. Shows higher EV conflict rates, but in manual driving cross-traffic, **not automated takeover**. |
| **Advertised WOT Acceleration** | $4.0 - 8.5\text{ m/s}^2$ | OEM 0–100 km/h Specifications | `OBSERVED` (track spec) | **COUNTERFACTUAL in ADS** | Wide-open-throttle launch capability (e.g. Tesla Model 3 Performance 0-100 in 3.1s $\approx 0.9g$). Such WOT/high-performance acceleration is not supported as a representative pre-TOR ADS operating condition by the current evidence base. |
| **Pre-Takeover ADS Acceleration** | None observed | D001 (ADAS-TO), D004 | **GAP (Unobserved)** | — | Neither ADAS-TO nor D004 contains instances of an automated vehicle aggressively accelerating immediately prior to a critical safety handover. |

### Summary of Parameter Realism vs Event Realism
- While vehicles possess physical capability to accelerate at $4 - 8\text{ m/s}^2$, automated longitudinal speed regulation in literature and standards (e.g. ISO 15622) is bounded by passenger comfort limits ($\le 2.0\text{ m/s}^2$). Such high-performance acceleration is not supported as a representative pre-TOR ADS operating condition by the current evidence base.
- Simulating an automated vehicle accelerating at $6\text{ m/s}^2$ prior to handover is a $100\%$ synthetic `COUNTERFACTUAL` scenario.
- As established in [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md), **parameter plausibility does not equal event-frequency realism**. We cannot present high-acceleration takeover scenarios as empirical safety findings.

---

## 8. Identifiability Analysis

Can the effect of acceleration authority on takeover safety be identified empirically from existing data?
- **Public Datasets:** As established in [`research/data_matrix/dataset_inventory.csv`](../../research/data_matrix/dataset_inventory.csv), D005 has no brake channel, D004 had openpilot disengaged during sampled runs, and D001 (ADAS-TO) contains naturalistic disengagements without controlled pre-takeover acceleration sweeps.
- **Confounding:** In naturalistic data, drivers or automation accelerate when the forward roadway is clear (high initial headway). High acceleration is negatively correlated with immediate hazard proximity.
- Therefore, any simulated experiment evaluating high acceleration authority immediately preceding a critical takeover is an unanchored counterfactual sweep, entirely unidentifiable from real-world telemetry.

---

## 9. Relationship to Experiment A1

Branch A1 evaluated:
$$\text{Handover Response Policy } (W0 \text{ vs } W1) \times \text{Brake Transient Architecture } (a_{coast}, t_{buildup})$$
A1 established the **recovery boundary**: given entry speed $v_{tor}$, what is the critical warning budget $T_{TOR\_critical}$ and stopping distance required for safe fallback?

Branch B operates strictly **upstream** of A1:
$$\text{Pre-takeover acceleration } (a_{accel}, t_{accel}) \implies \text{Entry State } (x_{tor}, v_{tor})$$
Because the interface between the pre-takeover phase and the post-takeover phase is completely captured by the two scalar state variables $(x_{tor}, v_{tor})$, Branch B does not alter or interact with A1's recovery physics. It merely shifts the entry coordinate along A1's existing, validated response surface.

---

## 10. Claim Ladder Classification

Applying [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md):

- **Analytical Formulation of $t_{cross}$ and Margin Consumption:** **TYPE 1 (Analytical).**  
  True by construction from Newtonian kinematics. Requires no simulation and no data fitting.
- **Hypothetical B1 Simulation Experiment:** **TYPE 2 (Counterfactual Simulation).**  
  Sweeping $a_{accel} \in [0.5, 6.0]\text{ m/s}^2$ across arbitrary scenario geometries produces only model-behavior demonstrations under unanchored counterfactual assumptions.
- **Empirical Claims (TYPE 3 / TYPE 4):** **NOT SUPPORTABLE.**  
  No empirical dataset supports the occurrence of high-acceleration handovers in production ADS.

---

## 11. Branch Decision & Classification

### Formal Gate Decision: **B0-A: ANALYTICAL ONLY**
**(Branch B1 Numerical Simulation is KILLED / RECLASSIFIED)**

### Explicit Classification Options Reviewed:
- **B0-A: ANALYTICAL ONLY [ACCEPTED]**  
  The proposed risk-state escalation effect is fundamentally a closed-form consequence of Newtonian kinematics and stopping physics. All governing quantities ($v_{tor}, x_{accel}, X_{stop}, \text{Margin}, t_{cross}, \frac{d X_{stop}}{dt}$) have exact, closed-form analytical solutions. The interaction with post-takeover variables is $100\%$ mediated by terminal speed. Numerical simulation adds zero physical or scientific knowledge.
- **B0-B: NARROW SIMULATION QUESTION [REJECTED]**  
  No bounded interaction, threshold discontinuity, or non-integrable state-dependent effect was identified that cannot be solved in closed form.
- **B0-C: FULL B1 JUSTIFIED [REJECTED]**  
  There is no non-trivial, identifiable mechanism supported by empirical takeover data that requires forward numerical simulation.

---

## 12. Justification for Killing B1 Numerical Simulation

1. **Numerical Simulation Adds Zero Information:**  
   The minimal longitudinal simulator integrates $\dot{v} = a$ and $\dot{x} = v + \frac{1}{2} a \cdot dt$. For constant or piecewise-constant acceleration, the simulator's numerical output is identical to the quadratic closed-form equations derived in Section 4 to within $10^{-6}\text{ m}$ (numerical floating-point noise). Running a simulator to generate numerical curves of a solved quadratic equation is unscientific.

2. **Absence of Independent Mechanism:**  
   As proven in Section 6, $\frac{\partial^2 D_{stop}}{\partial a_{accel} \partial Z} \equiv t_{accel} \frac{\partial^2 D_{stop}}{\partial v_0 \partial Z}$. Acceleration authority possesses no unique physical coupling to human reaction time, brake hydraulics, or automation withdrawal. It acts solely as an upstream velocity booster.

3. **Adherence to Research Charter Principles:**  
   [`docs/RESEARCH_ARCHITECTURE_V1.md`](../../docs/RESEARCH_ARCHITECTURE_V1.md) explicitly mandates:
   > *"Each branch has an independent survival condition... Later branches are not assumed necessary just because earlier ones survived — per this phase's explicit instruction, 'do not force later branches to survive.'"*  
   Killing B1 when it fails the non-triviality test protects the research programme from generating low-value, repetitive simulation papers.

---

## 13. Retention as a Supporting Analytical Result

While an independent numerical simulation experiment (B1) is rejected, the analytical derivations developed in B0 are **retained as a core analytical component (TYPE 1)** of the overall vehicle-aware human fallback framework:

1. **The Performance–Recovery Ratio ($\eta = a_{accel} / a_{max}$):**  
   Provides a rigorous, dimensionless metric quantifying how propulsion authority amplifies the rate of distance-margin consumption by $(1 + \eta)$.
2. **Closed-Form Time-to-Boundary ($t_{cross}$):**  
   Provides an exact analytical formula for the available time budget before an accelerating vehicle crosses into the unrecoverable fallback region:
   $$t_{cross} = \frac{2 M_0}{B + \sqrt{B^2 + 4 A M_0}}$$
   where $A = \frac{1}{2} a_{accel} (1 + \frac{a_{accel}}{a_{max}})$ and $B = v_0 + a_{accel} (\frac{v_0}{a_{max}} + K_1)$.
3. **Scoped Implication for Takeover Modeling:**  
   Within the current evidence-supported ADS acceleration regime and within the current model, acceleration authority does not introduce an independent post-TOR physical mechanism beyond the $(x_{tor}, v_{tor})$ state it creates. We do not make the categorical claim that A1 universally dominates real-world takeover risk, nor do we infer real-world event frequencies from parameter ranges.

---

## 14. Recommended Next Project Step

With Branch B successfully resolved as **B0-A (Analytical Only)**, the research programme should avoid manufacturing artificial acceleration simulations and proceed to evaluate the remaining planned architectural branches:

1. **Branch C (Driver–Vehicle Internal-Model Mismatch):**  
   Subject to an evidence and identifiability challenge (C0).
2. **Branch D (Handover Policy Extension / Timing):**  
   Investigating whether handover timing budgets interact with driver reaction latencies or warning lead-time sensitivity, building directly on the verified A1 fallback boundary. (Staged withdrawal policy $W2$ remains excluded per Phase 0 due to unconstrained authority/response shape parameters).

---

## 15. Programmatic Verification

The analytical derivations in this document are verified by automated tests in [`tests/test_b0_analytical.py`](../../tests/test_b0_analytical.py):
- `test_t_cross_matches_numerical_root`: Confirms closed-form $t_{cross}$ matches high-precision numerical root-finding ($|t_{closed} - t_{num}| < 10^{-12}\text{ s}$).
- `test_state_mediation_invariance`: Confirms prior acceleration history has zero independent effect on post-TOR stopping physics when entry state is held constant.
- `test_mixed_partial_derivative_is_chain_rule_multiple`: Confirms mixed partial derivatives wrt post-TOR variables are identical to velocity partials scaled by $t_{accel}$.
- `test_risk_escalation_monotonicity`: Confirms $t_{cross}$ decreases strictly monotonically with acceleration authority.
