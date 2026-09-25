# Post-A1 Claim and Estimand Audit

**Audit Date:** Phase 1A Post-Execution Review
**Document Purpose:** Formal record of causal estimand clarification, scientific boundary enforcement, unsupported-language corrections, and final claim calibration for Experiment A1.

---

## 1. Causal Estimand Clarification

### The Ambiguity in Initial Phrasing
Initial write-ups referred to the primary stopping-distance contrast as:
> *"Main Effect of Withdrawal Policy ($W0 \to W1$)"*

This phrasing created a potential attribution error by implying that an abstract software policy label (`W0` vs `W1`) possesses an independent physical mechanism that directly stops the vehicle.

### Mechanism Decomposition
The simulator's physical model (`src/vehicle/models.py` and `src/simulation/simulator.py`) operationalizes the system through three distinct physical layers:

1. **Control Policy / Ownership Semantics:**
   A supervisory decision logic governing control authority during the reaction-time interval $[0, t_{reaction})$:
   - $W0$: Automation retains longitudinal control, commanding constant cruise speed ($a(t) = 0$).
   - $W1$: Automation withdraws propulsion immediately upon TOR issuance ($t = 0$), leaving the vehicle in an uncommanded state.
2. **Withdrawal-Induced Longitudinal Response:**
   The actual physical deceleration ($a_{coast}$) delivered by the vehicle powertrain and chassis when uncommanded:
   - For a vehicle with regenerative overrun or strong engine braking: $a_{coast} \in [1.0, 4.0]\text{ m/s}^2$.
   - For a vehicle with neutral freewheel / minimal coast-down drag: $a_{coast} \approx 0.0\text{ m/s}^2$.
3. **Vehicle Brake-Buildup Transient:**
   The actuation latency ($t_{delay}$) and deceleration rise time ($t_{buildup}$) governing friction brake application *after* human pedal input begins at $t_{reaction}$.

### Empirical Proof of the Invariance Principle
In `tests/test_a1_experiment.py::test_policy_label_has_no_independent_physical_effect`, we simulated a vehicle with $a_{coast} = 0.0\text{ m/s}^2$ under both $W0$ and $W1$:
- State trajectories ($t, x, v, a$), stopping distance, stopping margin, and critical takeover time ($T_{TOR\_critical}$) were **bit-identical** across $W0$ and $W1$.
- Varying $a_{coast}$ under $W0$ produced zero physical change because automation actively commands cruise.

**Audited Estimand Definition:**
> The simulator does NOT identify an abstract policy label effect. It identifies **the causal effect of pre-human-braking longitudinal deceleration ($a_{coast}$) during the handover latency interval $[0, t_{reaction})$**, and its interaction with the post-takeover brake build-up transient ($t_{buildup}$).

---

## 2. Unsupported-Language Corrections

### Removal of "Fatal"
- **Correction:** Any mention of "fatal collision" was expunged from the report and documentation.
- **Scientific Grounding:** The simulator implements point-mass kinematic equations ($x, v, a$) with a rigid hazard distance marker. It contains **no biomechanical, injury, cabin intrusion, or fatality model**.
- **Approved Terminology:**
  - "collision"
  - "collision outcome"
  - "collision-to-safe-stop transition"
  - "stopping margin crossing"

---

## 3. Grid-Percentage Interpretation

### Correction of Simulation Grid Metrics
- **Initial phrasing:** "flips 16.35% of all tested scenarios from collisions into safe stops".
- **Audited phrasing:** "flips 170 of 1,040 matched conditions (16.35% of matched conditions in the pre-specified core simulation grid)".
- **Scientific Boundary Enforcement:**
  - The 16.35% figure is a descriptive property of the specific pre-registered simulation grid (which deliberately sampled densely in the marginal band).
  - It is **not** a real-world collision probability, accident reduction rate, or population prevalence.
  - It is not invariant to grid resolution or scenario weighting.

---

## 4. Sensitivity Model Clarification

### Wet Road Friction ($\mu = 0.7$)
- **Audited Description:** "Within the current low-friction sensitivity model".
- **Physical Details:** Maximum achievable deceleration was scaled to $a_{max} = \mu \cdot g = 5.95\text{ m/s}^2$, while reaction time ($1.0\text{ s}$), actuation delay ($0.10\text{ s}$), and coast deceleration ($2.0\text{ m/s}^2$) were held constant.
- **Scope Limitation:** This is an idealized steady-state friction sensitivity check. It does not model real-world dynamic wet-surface phenomena such as ABS pressure modulation, transient tire adhesion peaks, or hydroplaning.

---

## 5. Four-Part Separation of the Core Scientific Result

The experimental findings are explicitly separated into four distinct levels:

| Level | Finding | Magnitude | Evidence Level |
|---|---|---|---|
| **A. Structural Non-Additivity** | Analytical cross-derivative $\partial^2 D / \partial a_c \partial t_b = -t_1 / 2 \neq 0$ is numerically confirmed to machine precision ($< 10^{-14}\text{ m}$). | Mathematical proof | Analytical (Type 1) |
| **B. Interaction Magnitude** | The interaction contrast attenuates stopping distance by only a small amount across the entire domain. | $0.10 - 1.40\text{ m}$<br>($5 - 70\text{ ms}$ on $T_{TOR\_critical}$) | Counterfactual Simulation (Type 2) |
| **C. Dominant First-Order Effect** | Pre-human-braking coast deceleration ($a_{coast}$) substantially shortens stopping distance and required warning budget. | $5.67 - 11.87\text{ m}$<br>($0.28 - 0.59\text{ s}$ on $T_{TOR\_critical}$) | Empirically-Constrained Simulation (Type 3) |
| **D. Boundary Localization** | All recoverability flips concentrate in the marginal band ($\text{TOR} \in [1.8, 2.5]\text{ s}$ at $72\text{ km/h}$). Hopeless scenarios remain unrecoverable. | Localized to marginal band | Empirically-Constrained Simulation (Type 3) |

**Key Synthesis:**
The second-order interaction (B) is modest relative to the dominant first-order response (C) and an order of magnitude smaller than human reaction time variability (Comparator A: $16.0\text{ m}$).

---

## 6. Claim Ladder Placement

- **Withdrawal-Induced Deceleration ($a_{coast}$):** `docs/CLAIM_LADDER.md` **TYPE 3 (Empirically-Constrained Simulation)**. Grounded in OpenLKA fleet telemetry (D004) and SAE coast-down testing standards.
- **Brake Build-Up Transient Interaction ($t_{buildup}$):** `docs/CLAIM_LADDER.md` **TYPE 2 (Counterfactual Simulation)**. Input $t_{buildup}$ remains counterfactual. Numerical agreement with the analytical oracle validates simulator correctness, but does not upgrade parameter provenance.
- **Real-World Takeover Safety:** `docs/CLAIM_LADDER.md` **TYPE 4 (Empirical Real-World Claim) — NOT SUPPORTABLE**. No production vehicle or human participant was evaluated.

---

## 7. Final Gate Decision and Narrowed Claim

### Gate A1 Verdict: **A1: NARROW**

### Approved Narrowed Claim Statement:
> **"Within the current empirically constrained/counterfactual simulation model, the longitudinal vehicle response during the delay between automation handover and effective human braking can materially shift the critical fallback boundary in marginal scenarios (reducing required takeover lead time by $\approx 0.3 - 0.6\text{ s}$). Its interaction with post-takeover brake build-up latency is mathematically present but practically modest ($\le 0.07\text{ s}$) relative to this first-order response."**
