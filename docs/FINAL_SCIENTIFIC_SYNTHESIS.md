# Final Scientific Synthesis: State-Dependent Physical Recoverability in Automated-to-Human Handover

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** This synthesis is retained as the historical G0 record. Superseded: `P1-B: READY` and paper readiness are withdrawn (stage: EXPLORATORY). Novelty class N2 ("distinct closed-form integration") is withdrawn: `t1 + t2 + t3/2` is standard accident-reconstruction stopping-distance practice and `−a·t3²/24` follows directly from a linear ramp. The remaining novelty candidate (layer separation and coupling; recoverability framework) is not established. The analytical results are MODEL-VALID only (deterministic, open-loop, 1-D, saturated braking) and are one slice of the vehicle-response layer, not a completed layer or a system-level result. Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Document:** `docs/FINAL_SCIENTIFIC_SYNTHESIS.md`  
**Status:** Frozen Final Synthesis (Branch G0)  
**Date:** 2026-09-21  
**Project Baseline:** `phase0-frozen` (`bc21fbc`)  
**Active HEAD:** `040b13f` (Branch G0)  
**Test Suite:** 38 passed (`pytest -q` in ~1.4s)  
**Paper Readiness Decision:** ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN; stage EXPLORATORY]**

---

## 1. Final Research Question (Mother Question)

The project's central research inquiry, narrowed from early exploratory scoping, addresses:

> **State-Dependent Physical Recoverability During Automation-to-Human Fallback: How do current vehicle kinematic state, driver reaction latency, longitudinal vehicle response during the authority transition prior to effective human braking, brake-response dynamics, and braking capability interact to determine the minimum physically required takeover lead time ($T_{required}$) for collision-free stopping before a stationary hazard?**

### Explicit Exclusions:
- **NOT an EV-vs-ICE safety trial:** The project does not assert that electric vehicles are safer or more dangerous than internal-combustion vehicles. Longitudinal deceleration during reaction latency ($a_{pre} \in [0.0, 3.0]\text{ m/s}^2$) reflects powertrain deceleration dynamics (e.g., active regenerative or engine braking during reaction latency), not propulsion chemistry.
- **NOT a generic braking safety study:** The model is strictly focused on the **automation withdrawal and handover window** before a forward obstacle.
- **NOT a generic human-factors latency survey:** Human reaction time ($t_1 \in [0.7, 1.5]\text{ s}$) is treated as an exogenous kinematic delay parameter bounded by established takeover literature, not a newly modeled cognitive distribution.

---

## 2. Surviving Causal Model

The surviving causal DAG mapping state transitions during an emergency Takeover Request (TOR) at $t = 0$:

```
[ Kinematic State at TOR: (x_TOR, v_TOR) ] ──┐
                                             │
[ Driver Reaction Latency: t1 ] ─────────────┼──> [ Transition Trajectory: x1, v1 ] ──┐
                                             │                                        │
[ Pre-Effective Deceleration: a_pre ] ───────┘                                        │
                                                                                      ├──> [ Total Stopping Distance: D_stop ]
[ Brake Actuation Delay: t2 ] ────────────────────────────────────────────────────────┤                        │
                                                                                      │                        v
[ Brake Build-up Ramp: t3 ] ──────────────────────────────────────────────────────────┤             [ Minimum Required ]
                                                                                      │             [ Takeover Lead Time ]
[ Max Braking Deceleration: a_max ] ──────────────────────────────────────────────────┘             [ T_required = D_stop / v0 ]
```

### Analytical Closed-Form Formulation:
$$T_{required}(v_0, t_1, a_{pre}, t_2, t_3, a_{max}) = \frac{v_0}{2 a_{max}} + t_1 \left(1 - \frac{a_{pre}}{a_{max}}\right)\left(1 - \frac{a_{pre} t_1}{2 v_0}\right) + \left(t_2 + \frac{t_3}{2}\right)\left(1 - \frac{a_{pre} t_1}{v_0}\right) - \frac{a_{max} t_3^2}{24 v_0}$$
where $v_1 = v_0 - a_{pre} t_1 > 0$ is the vehicle speed at human brake initiation.

### Eliminated Causal Pathways (Negative & Deferred Scoping):
1. **Pre-TOR Acceleration History (Branch B0):** Disproved as an independent causal factor. Once the current TOR state $(x_{TOR}, v_{TOR})$ and post-TOR parameters are fixed, pre-TOR acceleration history has no independent effect within the current longitudinal Markov model.
2. **Driver Internal-Model Mismatch (Branch C0):** Deferred. Under the current open-loop full-brake human-response model ($u = 1.0$), pedal mismatch $M$ has zero physical pathway to affect stopping distance; furthermore, existing naturalistic datasets lack vehicle familiarity labels, rendering $M$ non-identifiable.
3. **Staged Automation Withdrawal ($W2$):** Excluded during Phase 0 design to prevent uncontrolled parameter proliferation.
4. **Lateral Steering Avoidance:** Excluded; the model is strictly longitudinal.
5. **Closed-Loop Human Modulation:** Excluded; human brake demand is modeled as an open-loop step input.

---

## 3. Categorized Scientific Contributions

### A. Analytical Contributions (TYPE 1 — Kinematic Deductions)
1. **Closed-Form Handover Boundary:** Derived the exact algebraic solution for $T_{required}(v_0, \mathbf{\theta})$, proving that the physical boundary between collision and safe recovery is closed without numerical simulation error.
2. **Global Coordinate-Wise Monotonicity:** Mathematically proved that $\nabla T_{required}$ maintains invariant signs coordinate-wise across the entire admissible domain ($\partial T/\partial v_0 > 0$, $\partial T/\partial t_1 > 0$, $\partial T/\partial a_{pre} < 0$, $\partial T/\partial t_2 > 0$, $\partial T/\partial t_3 > 0$, $\partial T/\partial a_{max} < 0$).
3. **Absence of Interior Local Extrema:** Proved that because all partial derivatives are non-zero and signed, the continuous infimum and supremum occur strictly at the hyper-rectangular domain corners.
4. **State-Mediation Invariance (B0):** Analytically proved that once the current TOR state $(x_{TOR}, v_{TOR})$ and post-TOR parameters are fixed, pre-takeover longitudinal acceleration history has zero independent carry-over effect on stopping distance.
5. **Criterion Equivalence & Discretization Bound:** Reconciled Criterion 1 (physical collision margin $\ge 0$) and Criterion 2 (resolvable margin $\ge a_{max} dt^2$), proving analytical convergence as $dt \to 0$ and bounding numerical discretization shift to $< 0.85\ \mu\text{s}$.

### B. Numerical & Computational Contributions (TYPE 2 — Bounded Mappings)
1. **Analytical Oracle Verification:** Built and validated a forward Euler minimal longitudinal simulator verified against analytical oracles to machine precision ($< 10^{-12}\text{ m}$ in A0).
2. **Bounded Parameter Mapping:** Evaluated the exact state-dependent requirement spread across the literature-supported domain ($1.15 - 3.58\text{ s}$ core empirical range, spread $\Delta T_{core} = 2.44\text{ s}$; $1.07 - 4.98\text{ s}$ sensitivity range, spread $\Delta T_{ext} = 3.91\text{ s}$).
3. **Deterministic Elasticity Mapping:** Derived normalized sensitivities $S_x \equiv (x / T_{req}) \partial T_{req} / \partial x$ and quantified that speed ($S_{v_0} \approx +0.50$ to $+0.56$) and braking capability ($S_{a_{max}} \approx -0.46$ to $-0.49$) dominate, while brake build-up ramp is low-sensitivity ($S_{t_3} \approx +0.06$).
4. **Leave-One-Out Bottleneck Perturbation:** Verified that 5-fold counterfactual variation in brake build-up ramp ($t_3 \in [0.10, 0.50]\text{ s}$) shifts $T_{required}$ by $< 0.20\text{ s}$ ($< 4.5\%$).

### C. Evidence & Methodological Contributions (Methodological Governance)
1. **The Project Claim Ladder ([`docs/CLAIM_LADDER.md`](CLAIM_LADDER.md)):** Enforced strict epistemic separation between TYPE 1 (analytical deductions), TYPE 2 (counterfactual/sensitivity bounds), and TYPE 3 (empirical findings).
2. **Weakest-Link Boundary Claim Rule:** Enforced the principle that a numerical boundary evaluation cannot claim a higher scientific status than its least-supported parameter input.
3. **Identifiability-Based Gate Keeping:** Prevented wasteful simulation execution by formally killing Branch B1 (state-mediated) and deferring Branch C1 (unidentifiable without experimental human data).
4. **Global 5-Level Validation Audit:** Subjected five candidate public datasets (D001–D005) to forensic verification, establishing that external validation is currently feasible only at Level 2 (Parameter-Level Evidence).

---

## 4. Negative and Narrowed Results

The project rigorously documents its negative, narrowed, and deferred findings:

1. **Branch A1 (Withdrawal Policy $\times$ Vehicle Architecture Interaction):**
   - *Finding:* A statistical interaction between withdrawal policy ($W$) and brake transient profile ($R$) exists mathematically but is numerically modest ($\le 0.07\text{ s}$).
   - *Dominant Mechanism:* Within A1, pre-human longitudinal deceleration ($a_{pre}$) is the dominant vehicle-response effect relative to the build-up interaction, shortening required stopping time by $0.30 - 0.58\text{ s}$ across the tested range (though global sensitivity in E0 shows initial speed $v_0$ and maximum deceleration $a_{max}$ remain the primary determinants overall).
2. **Branch B1 (Risk-State Escalation Dynamic Simulation — KILLED):**
   - *Finding:* The planned dynamic simulation was killed because B0 proved that pre-takeover acceleration is entirely mediated by current state $(x_{TOR}, v_{TOR})$ at the moment of TOR. Running dynamic simulation would have added zero scientific information.
3. **Branch C1 (Driver–Vehicle Internal-Model Mismatch — DEFERRED):**
   - *Finding:* C0 proved that under the modeled full-brake step response ($u = 1.0$), driver mismatch $M$ has no causal mechanism to affect deceleration. Existing naturalistic datasets lack vehicle familiarity labels, making empirical calibration unidentifiable.
4. **Branch D1 (State-Dependent Handover Forward Simulation — KILLED / NOT REQUIRED):**
   - *Finding:* Because the fallback boundary was completely solved in closed form in D0, forward simulation bisection would merely replicate exact algebraic values with floating-point discretization error.

---

## 5. Final Synthesis Claim Table

| Claim Statement | Result | Claim Type | Empirical Support | Allowed Wording | Prohibited Wording |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Analytical Form of $T_{required}$** | Exact closed-form equation derived and verified | **TYPE 1** | Kinematic derivation; validated against analytical oracles | "Mathematically deduced physical boundary", "closed-form recoverability relation" | "Empirically discovered formula", "statistical model" |
| **State-Dependence of Required Lead Time** | $T_{required}$ spans $1.15 - 3.58\text{ s}$ across core domain ($\Delta = 2.44\text{ s}$) | **TYPE 2** | Evaluated on empirical ranges of $v_0, t_1, a_{pre}, t_2$; conditional on nominal $t_3 = 0.30\text{ s}$ | "Modeled requirement spread across literature-bounded parameter extrema" | "Population crash probability distribution", "empirical quantile spread" |
| **Pre-Effective Deceleration Effect ($a_{pre}$)** | Reduces $T_{required}$ by $0.30 - 0.58\text{ s}$ across core domain ($8.8\text{ m}$ at nominal speed, up to $17\text{ m}$ at highway speed; nominal $\partial T/\partial a_{pre} = -0.155\text{ s/(m/s}^2)$) | **TYPE 2** | D004 EV telemetry bounds and coastdown literature ($1.0 - 3.0\text{ m/s}^2$); NUM-08, NUM-10 | "Pre-effective deceleration during reaction latency expands the physical stopping margin" | "EVs are universally safer than ICE vehicles during handover" |
| **Withdrawal $\times$ Architecture Interaction** | Cross-term interaction is small ($\le 0.07\text{ s}$) | **TYPE 2** | Factorial simulation sweep (A1) and analytical Hessian evaluation | "Interaction is non-zero but secondary to pre-human longitudinal deceleration" | "Brake build-up architecture determines handover success independently" |
| **Fixed-TOR Lead Time Interpretation** | State-invariant minimum unsupported; worst-case fixed bound feasible | **TYPE 1 & 2** | Monotonicity proof across domain $\Omega$ | "A single scalar cannot equal the state-dependent minimum; within the current deterministic longitudinal stationary-hazard model and specified bounded parameter domain, a worst-case fixed bound is sufficient for stopping across the modeled domain, but is overly conservative in easier states" | "Fixed TOR policies are mathematically impossible", "fixed TOR guarantees collision" |
| **Pre-Takeover Acceleration Authority (B0)** | Pre-TOR acceleration history has 0 independent effect | **TYPE 1** | Markovian kinematic proof | "Once the current TOR state (x_TOR, v_TOR) and post-TOR parameters are fixed, pre-TOR acceleration history has no independent effect within the current longitudinal Markov model" | "Acceleration authority escalates takeover risk independently of speed" |
| **Driver–Vehicle Internal Model Mismatch (C0)** | Mismatch $M$ unidentifiable and causally severed | **TYPE 1 & 2** | Formal sensitivity derivation & dataset forensic audit | "Mismatch is unidentifiable in existing open data and has zero causal pathway under the modeled full-brake step response" | "Drivers crash because they fail to adapt to EV regenerative braking" |
| **External Real-World Validation** | Parameter-level validation only (V1) | **TYPE 3 (Audit)** | Forensic audit of D001–D005 against 5-level hierarchy | "Parameter-grounded analytical model; full trajectory and outcome validation unobserved in public data" | "Real-world validated safety envelope", "proven on naturalistic fleet data" |
| **EV vs ICE Propulsion Comparison** | Architecture modeled via $a_{pre}$ and $t_3$, not propulsion type | **TYPE 1** | Model specification | "Longitudinal deceleration during latency and actuation transients" | "EV safety advantage", "ICE braking deficiency" |

---

## 6. Applicable Model Domain and Operational Boundaries

The model and findings apply strictly within the following specified physical domain:

1. **Longitudinal-Only Recovery:** Vehicle motion is restricted to a straight, one-dimensional path ($x, v, a$). Lateral steering avoidance, lane changes, and yaw dynamics are not modeled.
2. **Stationary Forward Hazard:** Obstacle is stationary ($v_{hazard} = 0$). Moving lead vehicles, cut-ins, and decelerating traffic targets are excluded.
3. **Deterministic Initial State:** Vehicle state at TOR is deterministically specified by $(x_0 = 0, v_0)$. Probabilistic sensor noise and perceptual uncertainty are not modeled.
4. **Modeled Full-Brake Step Human Response:** In the current open-loop model, the driver applies an immediate step command to full braking authority ($u = 1.0$) following latency $t_1$. Closed-loop pedal modulation, feedback corrections, and gradual pedal application are excluded.
5. **Constant Road Friction / Capability:** Maximum deceleration $a_{max}$ is held constant during steady-state braking. ABS pressure cycling, tire slip curves, load transfer, and road patchiness are not modeled.
6. **No Thermal or Component Memory:** Brake fade, rotor temperature, and fluid compressibility changes are excluded.
7. **Current-State Markov Formulation:** The vehicle state at $t = 0$ fully encapsulates physical history. Prior acceleration or jerk trajectories have no independent carry-over.

---

## 7. Project Validation Status

The final project validation status across the global 5-level hierarchy is:

```
[ LEVEL 1: Mathematical Verification ]        ==>  ESTABLISHED
[ LEVEL 2: Parameter Plausibility / Evidence ] ==>  EVIDENCE-BOUNDED / PARTIAL
[ LEVEL 3: Trajectory Validation ]             ==>  NOT ESTABLISHED
[ LEVEL 4: Outcome / Boundary Validation ]     ==>  NOT ESTABLISHED
[ LEVEL 5: Population / Generalisation ]       ==>  NOT ESTABLISHED
```

- **Level 1 (Mathematical Verification): ESTABLISHED.** Closed-form equations, partial derivative signs, and analytical oracle matches are verified to machine precision in automated unit tests.
- **Level 2 (Parameter-Level Evidence): EVIDENCE-BOUNDED / PARTIAL.** $v_0$ is operational domain; $t_1$ is anchored in large human-factors literature ($0.7 - 1.5\text{ s}$); $a_{pre}$ is bounded by EV telemetry ($0.0 - 3.0\text{ m/s}^2$); $t_2$ is bounded by brake lag tests ($0.05 - 0.17\text{ s}$); $a_{max}$ is literature-constrained. However, build-up ramp $t_3$ remains counterfactual ($0.30\text{ s}$ nominal, $[0.10, 0.50]\text{ s}$ sensitivity).
- **Level 3 (Trajectory Validation): NOT ESTABLISHED.** No public dataset provides synchronized, continuous high-frequency pedal input and brake pressure traces during automated handover across varied vehicle architectures.
- **Level 4 (Outcome / Boundary Validation): NOT ESTABLISHED.** No public dataset pairs an L3 TOR alert with a known obstacle distance $d_0$, multi-vehicle response architectures, and crash/stopping outcomes.
- **Level 5 (Population / Generalisation Validity): NOT ESTABLISHED.** Representative fleet crash probabilities have not been measured.

**Prohibited Description:** The project must **never** be described as "real-world validated" or "empirically proven on fleet data."  
**Permitted Description:** "Analytically verified and evidence-bounded kinematic framework."

---

## 8. Final Novelty Position

### Literature State of the Art (Already Known):
1. **Takeover Timing Matters:** TOR lead time is known to strongly influence takeover success (Deng et al., 2024; Liang et al., 2026; McDonald et al., 2019).
2. **Human Reaction Latency Varies:** Driver response time varies widely under distraction, urgency, and cognitive load (Markkula et al., 2016; Roche et al., 2020).
3. **Vehicle Deceleration Physics Matters:** Stopping distance scales quadratically with speed and depends on brake delays (Paquette & Porter, 2014; IIHS, 2023).

### Distinct Project Contribution:
The project's specific scientific contribution is:
> **The closed-form analytical integration of pre-effective-human-braking longitudinal vehicle deceleration ($a_{pre}$) and deceleration-response transients ($t_2, t_3$) into the takeover lead-time requirement equation ($T_{required}$), proving that the required lead time is a multi-dimensional state-dependent surface rather than a scalar constant.**

### Novelty and Quantitative Audit Closure:
The comprehensive external literature and citation integrity audit (Branch G0.1, [`docs/FINAL_NOVELTY_RECHECK.md`](FINAL_NOVELTY_RECHECK.md)) and quantitative claim audit (Branch G0.2, [`docs/QUANTITATIVE_CLAIM_LEDGER.md`](QUANTITATIVE_CLAIM_LEDGER.md)) established:
1. **[AUDIT 2026-09-22: N2 withdrawn: the closed form is prior-art-compatible mechanics]** Novelty is classified as ~~**N2 (Distinct Closed-Form Integration)**~~ with **N1 (Rigorous Extension of Known Concepts)** problem framing, specifically distinguished from Papadimitriou et al. (2024) and Eclipse SUMO / TransAID (2018–2026).
2. All headline figures adhere strictly to the Quantitative Claim Ledger (`docs/QUANTITATIVE_CLAIM_LEDGER.md`), eliminating ungrounded claims of global dominance and correcting marginal sensitivities.

---

## 9. Citation-Integrity Audit

| ID | Author(s) & Year | Title | Publication Venue / Identifier | Supported Project Claim | Risk of Overstatement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **L001** | Deng et al. (2024) | Takeover time budget in conditionally automated driving: A systematic review | *Transportation Research Part F*, 103, 102–120. DOI: [10.1016/j.trf.2024.04.015](https://doi.org/10.1016/j.trf.2024.04.015) | Motivates scenario-dependent TOR lead times over single fixed scalar constants. | Do not cite as endorsing our specific algebraic formula. |
| **L002** | Liang, Calvert & van Lint (2025/2026) | Systematic review of takeover time budgets in automated driving | *IJHCI* (PubMed ID: 42283150) | Confirms human reaction time variability under secondary tasks. | Focuses on driver workload, not vehicle powertrain dynamics. |
| **L003** | Roche, Thüring & Trukenbrod (2020) | Critical braking takeover in conditionally automated driving | *Accident Analysis & Prevention*, 144, 105658. DOI: [10.1016/j.aap.2020.105658](https://doi.org/10.1016/j.aap.2020.105658) | Confirms drivers frequently apply maximum emergency braking in critical handover. | Open-loop step assumption is a simplification of observed behavioral variance. |
| **L004** | ScienceDirect (2024) | One-pedal or two-pedal: Does the regenerative braking system improve driving safety? | *Accident Analysis & Prevention*, 208, 107774. DOI: [10.1016/j.aap.2024.107774](https://doi.org/10.1016/j.aap.2024.107774) | Demonstrates regenerative braking alters transition timing and deceleration profile. | Tests manual driving; does not test automated TOR transitions. |
| **L006** | Vigil, Kaayal & Szepelak (2023) | Quantifying Deceleration of Various Electric Vehicles Utilizing Regenerative Braking | *SAE Technical Paper 2023-01-0623*. DOI: [10.4271/2023-01-0623](https://doi.org/10.4271/2023-01-0623) | Bounds production EV regenerative deceleration rates ($0.1 - 0.3g$). | Paywalled; exact numerical profiles require full-text extraction. |
| **L010** | McDonald et al. (2019) | Toward more realistic human fallback models: A review of takeover models | *Human Factors*, 61(4), 582–606. DOI: [10.1177/0018720819829572](https://doi.org/10.1177/0018720819829572) | Identifies that existing takeover models neglect vehicle deceleration transients. | Confirms gap; does not provide numerical vehicle parameters. |
| **L011** | IIHS (2023) | Characteristics of automatic emergency braking responses in passenger vehicles | *Accident Analysis & Prevention*, 191, 107197. DOI: [10.1016/j.aap.2023.107197](https://doi.org/10.1016/j.aap.2023.107197) | Shows distinct vehicle models exhibit measurably different braking onset delays. | Evaluates autonomous AEB, not human takeover braking. |
| **L014** | Markkula et al. (2016) | A farewell to brake reaction times? Kinematics-dependent brake response | *Accident Analysis & Prevention*, 95, 209–226. DOI: [10.1016/j.aap.2016.07.007](https://doi.org/10.1016/j.aap.2016.07.007) | Challenges fixed reaction-time constant; supports looming/urgency dependence. | Motivates future state-dependent $t_1(v_0, d_0)$ extensions. |
| **L015** | Papadimitriou et al. (2024) | A method to assess the safety implications of authority transitions in automated driving | *Traffic Safety Research*, 6, e000048. DOI: [10.55329/fkix6369](https://doi.org/10.55329/fkix6369) | **Primary Prior Art:** Proposes Safe Time Budget (STB) and Time to Control (TC = TOT + t_action) incorporating physical braking time into authority transitions. | Evaluated via empirical microscopic simulation; lacks closed-form transient decomposition. |
| **L016** | Eclipse SUMO / TransAID (2018–2026) | SUMO Takeover Device (`device.toc`) / TransAID Deliverables D3.1/D3.2 | Open-Source Traffic Simulator / EU H2020 | **Secondary Prior Art:** Establishes speed-dependent TOR triggering based on MRM stopping distance: $d = t_{lead} v + v^2 / (2 a_{MRM})$. | Point-mass constant acceleration; omits powertrain latency dynamics and actuator transients. |
| **P&P** | Paquette & Porter (2014) | Brake Timing Measurements and the Effect of Brake Lag on Deceleration Rates | *Accident Reconstruction Journal*, 24(2), 19–21. | Empirical anchor for brake actuation delay $t_2 \in [0.05, 0.17]\text{ s}$. | Trade journal study on 4 passenger cars; not academic peer review. |
| **D001** | OpenLKA (2024) | ADAS-TO: A Dataset for Takeover Analysis in Naturalistic Driving | arXiv:2404.12051 / Hugging Face | Naturalistic takeover clips; confirms binary pedal logging. | Gated HF access; 10Hz majority; unsuitable for transient fitting. |
| **D002** | Nature Data (2025) | TD2D: Takeover Distracted Driving Dataset | *Scientific Data*, 12, 181. DOI: [10.1038/s41597-025-04781-8](https://doi.org/10.1038/s41597-025-04781-8) | Grounds human reaction time distributions ($0.7 - 1.5\text{ s}$). | L2 monitoring context, single simulator vehicle model. |
| **D003** | TU Delft (2024) | Conditionally automated driving takeover dataset | 4TU.ResearchData. DOI: [10.4271/2023-01-0623](https://doi.org/10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB) | Grounds L3 takeover reaction times under secondary tasks. | Single fixed simulator dynamics; no powertrain variation. |
| **D004** | OpenLKA (2024) | OpenLKA EV Kinematic Dataset | GitHub: OpenLKA/EV_Dataset | Continuous EV speed/accelerator CAN data; bounds $a_{pre}$. | Sampled sessions lacked hard braking events; full scale unverified. |
| **D005** | OpenLKA (2024) | OpenLKA Acceleration Dataset | GitHub: OpenLKA/Acceleration_Dataset | EV acceleration dynamics. | **Disqualified:** ~10Hz measured sampling, zero brake channels. |

---

## 10. Computational Reproducibility

### Repository Reproduction Blueprint:
- **Baseline Git Tag:** `phase0-frozen` (`bc21fbce8b9b9518919fcaecd6a301785a1fee0d`)
- **Key Milestones:**
  - `e038dab` — Validated A0 simulator and analytical oracles.
  - `58c3665` — Completed A1 factorial simulation sweep.
  - `aed0e30` — A1 claim and estimand audit.
  - `324e215` — B0 analytical mediation challenge.
  - `4778f22` — C0 identifiability and human model audit.
  - `76f539e` — D0 analytical boundary derivation.
  - `9321851` — E0 robustness verification and parameter closure.
  - `3cd7673` — E0 validation hierarchy cleanup.
  - `3f146aa` — G0.1 prior-work audit and novelty reclassification.
  - Current — G0.2 quantitative claim integrity audit ([`docs/QUANTITATIVE_CLAIM_LEDGER.md`](QUANTITATIVE_CLAIM_LEDGER.md)).

### Execution Commands:
1. **Run Full Test Suite (39 tests):**
   ```bash
   pytest -q
   ```
2. **Re-run A1 Simulation Sweeps:**
   ```bash
   python3 -m src.cli run-experiment --config experiments/A_brake_response/experiment_A_spec.md
   ```
3. **Verify D0/E0 Analytical Boundaries:**
   Analytical results require zero dynamic simulation loops and execute in $< 0.1\text{ s}$ via closed-form unit tests in `tests/test_d0_analytical_boundary.py` and `tests/test_e0_robustness.py`.

---

## 11. Paper Readiness Decision

### Final Classification: ~~`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`~~ **[AUDIT 2026-09-22: WITHDRAWN]**

Following the comprehensive Branch G0.1 External Novelty Audit ([`docs/FINAL_NOVELTY_RECHECK.md`](FINAL_NOVELTY_RECHECK.md)) and Branch G0.2 Quantitative Claim Audit ([`docs/QUANTITATIVE_CLAIM_LEDGER.md`](QUANTITATIVE_CLAIM_LEDGER.md)), the project is confirmed as **`P1-B: READY, NOVELTY CLAIM MUST BE NARROW`**.

### Epistemic Bounds & Honest Novelty Framing:
1. **Brake-Response Build-Up Calibration Gap:** Brake build-up ramp $t_3 = t_{buildup}$ is held at nominal $0.30\text{ s}$ (`COUNTERFACTUAL_SENSITIVITY / TYPE 2`) because sampled public CAN datasets contain no emergency braking episodes. The numerical boundary must remain TYPE 2 until calibrated against physical brake-pressure telemetry.
2. **External Validation Feasibility Limitation:** The project achieves **V1 (Parameter-Level Validation Only)**. Direct Level 3 (continuous trajectory) and Level 4 (crash vs stop outcome) validation are non-identifiable on existing public datasets.
3. **Novelty Scoping Requirement (Prior Art Boundaries):** The general concept of incorporating maneuver execution time into takeover safety evaluation was established by Papadimitriou et al. (2024) ($TC = TOT + t_{action}$; $STB = sTTC$), while speed-dependent dynamic TOR triggering using stopping distance is established engineering precedent (Eclipse SUMO / TransAID, 2018–2026). Furthermore, setting $a_{pre}=0, t_2=0, t_3=0$ reduces our boundary to the familiar reaction-distance plus constant-deceleration structure matching the SUMO MRM triggering special case ($T_{required} = t_1 + v_0 / (2 a_{max})$). Novelty must therefore be claimed strictly and narrowly on the **closed-form decomposition of pre-effective-human-braking longitudinal vehicle deceleration ($a_{pre}$) and deceleration-response transients ($t_2, t_3$) within the physical recoverability boundary**.

### Transition Recommendation:
The repository is **ready to proceed to manuscript drafting and synthesis** once explicitly authorized, under the strict condition that all paper sections respect the Claim Table constraints, adhere to the figures in [`docs/QUANTITATIVE_CLAIM_LEDGER.md`](QUANTITATIVE_CLAIM_LEDGER.md), avoid ungrounded broad novelty or priority claims ("first", "unique"), cite Papadimitriou et al. (2024) and Eclipse SUMO / TransAID as foundational baselines, and transparently disclose the Level 2 / V1 evidence boundaries.
