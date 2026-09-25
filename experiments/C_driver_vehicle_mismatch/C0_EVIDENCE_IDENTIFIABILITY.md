# Branch C0: Driver–Vehicle Internal-Model Mismatch — Evidence and Identifiability Challenge

> **AUDIT CORRECTION NOTICE (2026-09-22, Phase R0).** The internal-model mismatch M is generic (charter §4.2) and belongs at the human↔vehicle interface; EV/ICE familiarity is one instance. The "∂a_ego/∂M ≡ 0 under panic step braking" argument is withdrawn as evidence: it is true by construction once u ≡ 1 is assumed, and its premise is contradicted by D003's non-step braking (subject to unresolved brake-channel semantics). Corrected statement: direct vehicle-response familiarity (EV / one-pedal / regen) × takeover response is not identifiable from the verified public data checked; repeated-exposure learning is identifiable in D003 (trial order recoverable, Latin square balanced); driving and ADAS experience are associational only. "Not found in checked data" is not "does not exist". Current status: `docs/RESEARCH_STATUS_BASELINE_2026-09-22.md`. Architecture: `docs/RESEARCH_ARCHITECTURE_V2.md`. Pre-audit version: tag `pre-audit-2026-09-22`.

**Status:** Complete  
**Date:** 2026-09-21  
**Classification:** **C0-B: DEFER — HUMAN EXPERIMENTAL DATA REQUIRED** **[AUDIT 2026-09-22: RESTRUCTURE into four sub-questions; see notice]**  
**(Simulation Experiment C1 KILLED / NOT AUTHORIZED in Phase 1)**  
**Parent Baseline:** Commit `324e215` (B0 claim cleanup completed, 23 tests green, `phase0-frozen` at `bc21fbc`)  
**Claim Level:** **TYPE 1 (Analytical / Methodological Audit)** per [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md)

---

## 1. Original Mismatch Hypothesis

In the project charter ([`research/project_charter.md`](../../research/project_charter.md), Section 4.2 & Section 9, Gate C), Branch C was conceptualized around a driver cognitive/sensorimotor internal model:

> Let $\hat{f}_{driver}$ represent the driver's internal expectation of the control-input to vehicle-response mapping, and $f_{vehicle}$ the actual physical vehicle mapping.  
> Define a generic mismatch term:
> $$M = \mathcal{D}(\hat{f}_{driver}, f_{vehicle})$$
>
> The motivating intuition was:  
> *"A driver accustomed to one longitudinal response architecture (e.g., an ICE vehicle with light coast-down deceleration and progressive friction braking) taking over an automated vehicle with a radically different response architecture (e.g., an EV with aggressive one-pedal regenerative deceleration or nonlinear blended braking) may experience internal-model mismatch, leading to inappropriate initial braking inputs, delayed effective control, or unstable secondary corrections."*

In early Phase 0 scoping (`research/PHASE0_1_REPORT.md` and `docs/RESEARCH_ARCHITECTURE_V1.md`), Branch C was provisionally placed on `DEFER` status with $M = 0$ fixed across Phase 1, pending evidence.

This **C0 Evidence & Identifiability Challenge** subjects Branch C to rigorous scientific falsification. The burden of proof is on the branch: we do not assume the mechanism is identifiable, we do not protect the original idea, and we actively test whether mismatch has any legitimate empirical foundation or causal pathway in the project.

---

## 2. Current Human-Model Audit

We inspect the actual implemented human driver model in the repository ([`src/driver/models.py`](../../src/driver/models.py)):

```python
@dataclass(frozen=True)
class HumanDriverConfig:
    t_reaction: float = 1.0  # seconds from TOR to brake onset
    u_target: float = 1.0    # normalized brake demand [0, 1]
```

The control generation logic in `get_human_command(t)` is:
- For $t < t_{reaction}$: $u_{accel}(t) = 0.0, \quad u_{brake}(t) = 0.0$
- For $t \ge t_{reaction}$: $u_{accel}(t) = 0.0, \quad u_{brake}(t) = u_{target} = 1.0$

### Key Operational Characteristics:
1. **Strictly Open-Loop:** The human driver applies a pure step command at $t = t_{reaction}$.
2. **Fixed Command Amplitude:** $u_{brake}$ steps immediately to $1.0$ (emergency full-pedal application).
3. **Zero Sensory Feedback:** The driver does not perceive vehicle acceleration, headway, looming, jerk, or obstacle closure.
4. **Zero State Modulation:** There is no modulation, releasing, or pumping of the pedal.
5. **Enforced Isolation Invariant (Test 8):** In [`tests/test_simulator.py`](../../tests/test_simulator.py), Test 8 programmatically enforces that `sample_human_brake_command` is bit-identical across all compared vehicle-response profiles to guarantee that observed differences in stopping performance arise solely from vehicle hardware, not human variability.

---

## 3. Causal-Path Analysis

We ask the fundamental structural question:
> **Under the current model, can an internal model $\hat{f}_{driver}$ or mismatch $M$ affect any control input, kinematic state, or outcome?**

**Answer: STRICTLY ZERO CAUSAL PATHWAY.**

In the current simulator DAG:
$$\text{Scenario } (v_0, d_0) \longrightarrow \text{TOR} \longrightarrow \text{Withdrawal } (W0/W1) \longrightarrow \text{Driver } (t_1, u=1) \longrightarrow \text{Vehicle } (t_2, t_3, a_{max}) \longrightarrow \text{Outcome}$$

The human driver block has exactly two scalar inputs: $(t_{reaction}, u_{target})$.
- There is no variable $M$ in `HumanDriverConfig`.
- There is no driver expectation state $\hat{f}_{driver}$.
- There is no term in `calculate_acceleration()` or `MinimalSimulator` that reads or is modified by human expectation.

Under the current architecture, any mismatch variable $M$ is causally orphaned:
$$\frac{\partial u_{human}}{\partial M} \equiv 0, \quad \frac{\partial D_{stop}}{\partial M} \equiv 0, \quad \frac{\partial \text{Margin}}{\partial M} \equiv 0$$

To simulate mismatch, one would have to alter the human model itself.

---

## 4. What Would Be Required for Mismatch to Matter?

To give mismatch a causal pathway, the human model would need to be fundamentally redesigned from an open-loop step into a closed-loop behavioral controller.

Candidate mechanisms through which an internal-model error could physically alter trajectory include:

1. **Altered Initial Brake Amplitude ($u_0 \ne 1.0$):**  
   If a driver expects vehicle deceleration $\hat{a}_{pre}$ (e.g. regenerative braking) upon releasing the throttle, they may apply insufficient initial brake pedal force:
   $$u_{brake}(t_{reaction}) = 1.0 - \beta \cdot M$$
2. **Delayed Brake Onset ($\Delta t_{reaction} > 0$):**  
   Sensory surprise or cognitive dissonance when vehicle response deviates from expectation could induce hesitation or pedal-search latency:
   $$t_{reaction} = t_{reaction, 0} + \Delta t_{hesitation}(M)$$
3. **Closed-Loop Feedback Regulation:**  
   The driver observes realized deceleration $a(t)$ or visual looming $\tau^{-1}(t)$, detects an error $\epsilon(t) = a_{target}(t) - a(t)$, and dynamically modulates the pedal:
   $$\dot{u}_{brake}(t) = K_p \epsilon(t - \tau_{sensory}) + K_d \dot{\epsilon}(t - \tau_{sensory})$$
4. **Secondary Corrections / Pumping ($N_{correction} > 0$):**  
   If initial deceleration is unexpectedly high (over-braking), the driver releases the pedal before reapplying.
5. **Repeated-Trial Adaptation:**  
   The internal model updates over repeated encounters according to an error-correcting learning rule:
   $$\hat{f}_{k+1} = \hat{f}_k + \alpha (f_{vehicle} - \hat{f}_k)$$

**The Evidentiary Challenge:**  
Each of these mechanisms introduces unconstrained free parameters:
- What is $\beta$? What is $\Delta t_{hesitation}$?
- What is human sensory transport delay $\tau_{sensory}$ (visual vs vestibular)?
- What is neuromuscular gain $K_p$?
- What is the perceptual Just Noticeable Difference (JND) threshold for longitudinal acceleration?
- What is adaptation rate $\alpha$?

Unless these parameters are anchored in empirical data, any simulation of "mismatch" is merely an arbitrary tuning exercise.

---

## 5. Evidence Review

We exhaustively audited the project's evidence base ([`research/literature_matrix/literature_matrix.csv`](../../research/literature_matrix/literature_matrix.csv)):

| Source ID | Citation | Study Domain | Methodology | Key Finding | Transferability to Takeover Braking Mismatch |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **L012** | *Sensorimotor adaptation when steering with altered vehicle dynamics* (2018), Transp. Res. Part F | Lateral Steering | Driving simulator; steering-gain manipulation | Rapid adaptation to subtle steering changes; slow adaptation and after-effects for large/reversed gains. | **INDIRECT / ANALOGY ONLY.** Investigated lateral steering gain, not longitudinal braking. Did not involve automated takeover or emergency stopping. |
| **L004** | *One-pedal or two-pedal: Does regenerative braking improve driving safety?* (2024), Sci. Direct | Longitudinal Pedal Use | Driving simulator; manual car-following | One-pedal mode exhibited longer throttle-to-brake transition and higher timing variability in high-urgency lead-vehicle braking. | **BEHAVIORAL COMPARISON, NOT MISMATCH.** Compared driving under 1-pedal vs 2-pedal modes. Did not test a driver trained in one mode suddenly taking over the other in an unexpected TOR. |
| **L005** | *Driving experience and takeover* (Chen et al. 2021), Transp. Res. Part F | Takeover Human Factors | Driving simulator; 48 drivers | Driving experience (years of licensure) influenced takeover stability under secondary tasks. | **NO VEHICLE FAMILIARITY.** Manipulated novice vs experienced general drivers, not familiarity with specific vehicle deceleration dynamics. |
| **L003** | *Critical braking takeover* (Roche et al. 2020), AAP | Takeover Braking | Driving simulator; 42 drivers | In critical takeovers, drivers frequently applied excessive braking or sudden lane changes. | **NO VEHICLE DYNAMICS VARIATION.** Vehicle response architecture was identical across all participants. Captures human panic/urgency, not internal-model mismatch. |
| **L010** | *Takeover modeling review* (McDonald et al. 2019), Human Factors | Computational Modeling | Comprehensive literature review | Evaluates cognitive and control-theoretic takeover models; confirms manual braking models are applied to takeovers. | **CONFIRMS GAP.** Confirms that vehicle longitudinal-response architecture (regen, blending, delay) is completely neglected in existing takeover driver models. |

**Evidence Synthesis:**  
In the entire scientific literature cataloged by the project (L001–L014), **not a single study** provides empirical measurements or calibrated control laws for human driver internal-model mismatch during longitudinal takeover braking.

---

## 6. Dataset Identifiability Audit

We audited all five primary datasets in [`research/data_matrix/dataset_inventory.csv`](../../research/data_matrix/dataset_inventory.csv):

| Dataset ID | Dataset Name | Prior Vehicle Exposure? | Vehicle Familiarity Field? | Continuous Pedal Signal? | Takeover Context? | Identifiability Classification | Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **D001** | ADAS-TO | NO | NO | NO (Binary flags only) | YES | **NOT_USEFUL_FOR_MISMATCH** | Pedal signals are binary (`gasPressed`, `brakePressed`). No driver exposure history or familiarity is recorded. |
| **D002** | TD2D | NO | NO | YES (CSV traces) | YES (L2) | **HUMAN_RESPONSE_ONLY** | Focus is secondary-task distraction. Single simulator vehicle model used for all subjects; vehicle dynamics never manipulated. |
| **D003** | TU Delft Takeover | NO | NO | YES (Kinematics) | YES (L3) | **HUMAN_RESPONSE_ONLY** | Records driver risk attitude questionnaires, but zero EV/ICE familiarity. Single vehicle model across all 9 scenarios. |
| **D004** | OpenLKA EV Kinematics | NO | NO | YES (Gas pedal continuous, brake binary) | NO | **NOT_USEFUL_FOR_MISMATCH** | Continuous driving logs without takeover events. In inspected windows, openpilot was disengaged (`op_enable=False`). |
| **D005** | OpenLKA Acceleration | NO | NO | YES (`padel` continuous, **no brake**) | NO | **NOT_USEFUL_FOR_MISMATCH** | Accelerator-only dataset. Contains no brake channel, no regen channel, and no takeover context. |

**Identifiability Conclusion:**  
Every single dataset in the inventory is classified as **`NOT_USEFUL_FOR_MISMATCH`** or **`HUMAN_RESPONSE_ONLY`**.  
There is **zero empirical data** in the project repository capable of identifying or constraining a driver internal-model mismatch parameter $M$.

---

## 7. Distinguishing Three Distinct Scientific Claims

To maintain scientific integrity, we strictly decouple three propositions that are frequently conflated:

1. **Claim A: Drivers can adapt to altered vehicle control mappings.**  
   - *Status:* **ESTABLISHED IN MOTOR CONTROL LITERATURE** (e.g. L012 for steering gains, general psychology).  
   - *Meaning:* Humans exhibit sensorimotor plasticity; given repeated practice, control gains converge to new system dynamics.
2. **Claim B: Prior vehicle familiarity can influence subsequent control behavior.**  
   - *Status:* **QUALITATIVELY PLAUSIBLE / OBSERVED IN SPECIALIZED TASKS.**  
   - *Meaning:* Transfer of training can produce negative after-effects (e.g. reaching for a clutch in an automatic, or pedal transition latency differences in L004).
3. **Claim C: An ICE-trained driver taking over an EV-like vehicle during an automated driving emergency suffers a quantifiable mismatch safety penalty.**  
   - *Status:* **COMPLETELY UNPROVEN AND UNIDENTIFIED.**  
   - *Meaning:* That this specific transfer of training manifests as a measurable stopping distance or TTC penalty during an emergency takeover.

> [!IMPORTANT]
> **Claim A does NOT prove Claim B, and Claim B does NOT prove Claim C.**  
> Demonstrating that drivers adapt steering gain over 50 simulator trials (L012) does not prove that an ICE driver in a critical 3-second takeover will under-brake in an EV. Conflating these claims is a severe methodological error.

---

## 8. Critique and Rejection of the Conceptual 2×2 Design

The original conceptual design contemplated a 2×2 factorial experiment:
$$\text{Driver Prior } \{\text{ICE-like vs EV-like}\} \times \text{Vehicle Architecture } \{\text{ICE-like vs EV-like}\}$$

We formally **REJECT** this design for five decisive reasons:

1. **Commercial Propulsion Labels Mask Control Variables:**  
   "ICE-like" and "EV-like" are marketing terms, not physical or control-theoretic definitions. An EV with pure freewheeling coasting (e.g. Porsche Taycan) has an "ICE-like" deceleration response. An ICE vehicle in low gear has an "EV-like" engine-braking response.
2. **Undefined Operational Units:**  
   What are the units of a driver's prior? Expected deceleration ($\text{m/s}^2$)? Expected pedal gain ($\text{m/s}^2 / \text{mm}$)? Expected pedal force ($\text{N}$)? None of these have operational definitions in the literature.
3. **Unmeasurable Prior State:**  
   No validated psychometric or physiological instrument exists to measure a driver's latent internal model prior to a sudden takeover.
4. **Violation of Charter Claim Boundaries:**  
   [`research/project_charter.md`](../../research/project_charter.md) Section 8 explicitly forbids proving that "EVs are more or less safe than ICE vehicles." Framing the experiment as "ICE driver in EV" directly violates this founding boundary.
5. **Manufactured Novelty:**  
   Running a simulation where an artificial parameter $M$ is defined to degrade braking performance simply guarantees that mismatch causes crashes by construction.

---

## 9. Model-Complexity Cost & The "Degrees-of-Freedom Trap"

To implement Branch C, we evaluate the required model-class expansion:

| Model Component | Current Validated Model (Phase 1) | Required Branch C Model | New Parameters Required | Provenance Class |
| :--- | :--- | :--- | :---: | :---: |
| **Driver Control Policy** | Open-loop step ($u=1.0$) | Closed-loop neuromuscular feedback | $\Delta u_0, K_p, K_d$ | **UNIDENTIFIABLE** |
| **Perceptual Transport** | Fixed latency ($t_{reaction} = 1.0\text{ s}$) | Vestibular/visual delay + JND threshold | $\tau_{sensory}, a_{threshold}$ | `LITERATURE_CONSTRAINED` |
| **Internal Model State** | None | Latent expectation $\hat{a}_{pre}$ | $\hat{a}_{pre}, \sigma_{prior}$ | **UNIDENTIFIABLE** |
| **Correction Logic** | None | Dynamic pedal re-modulation / deadband | $\delta_{deadband}, t_{hold}$ | **UNIDENTIFIABLE** |
| **Adaptation Rule** | None | State estimator / learning rate | $\alpha_{learn}$ | **UNIDENTIFIABLE** |

**Evaluation:**  
Moving to Branch C would require introducing **at least 6 to 8 new free parameters**, of which at least 5 are completely unidentifiable from existing empirical data.  
This creates a classic **"Degrees-of-Freedom Trap"**: with 5 unconstrained parameters, the simulator can be tuned to produce *any desired safety outcome* (mismatch helps, mismatch hurts, mismatch is neutral). Such a simulation produces zero scientific evidence.

---

## 10. Claim Ladder Classification

Under [`docs/CLAIM_LADDER.md`](../../docs/CLAIM_LADDER.md):

- **TYPE 1 (Analytical):** Not applicable; human sensorimotor mismatch is an empirical psychological phenomenon, not a mathematical identity.
- **TYPE 2 (Counterfactual Simulation):** Possible only by defining an arbitrary mathematical penalty function $u(t; M)$. However, because $M$ is unconstrained, such simulations provide no actionable safety insight.
- **TYPE 3 (Empirically-Constrained Simulation):** **COMPLETELY UNSUPPORTABLE.** No literature-anchored numerical ranges exist for mismatch magnitude or feedback gain during emergency takeovers.
- **TYPE 4 (Real-World Empirical):** **COMPLETELY UNSUPPORTABLE.**

---

## 11. Branch Decision & Classification

### Formal Gate Decision: **C0-B: DEFER — HUMAN EXPERIMENTAL DATA REQUIRED**
**(Branch C1 Simulation is KILLED / NOT AUTHORIZED in Phase 1)**

### Explicit Classification Options Reviewed:
- **C0-A: KILL / REMOVE ENTIRELY FROM CURRENT PROJECT [PARTIALLY ADOPTED]**  
  The premature 2×2 "ICE vs EV" simulation design is permanently killed and excised from the active simulation pipeline.
- **C0-B: DEFER — HUMAN EXPERIMENTAL DATA REQUIRED [FORMALLY ADOPTED]**  
  The theoretical hypothesis that driver internal models influence takeover control remains scientifically plausible, but cannot be identified from existing datasets. It is formally deferred until dedicated human-in-the-loop experimental data can be gathered.
- **C0-C: NARROW COUNTERFACTUAL SENSITIVITY [REJECTED]**  
  Rejected because defining an arbitrary scalar penalty $M$ would add ungrounded complexity without scientific value, violating the project charter's commitment to defensibility.
- **C0-D: EMPIRICALLY-CONSTRAINED C1 JUSTIFIED [REJECTED]**  
  Rejected; zero empirical identification exists.

---

## 12. Proposed Protocol Targets for Future Human Experimental Data

To reopen Branch C in a future research phase, a dedicated human-in-the-loop empirical study would be required. The following are proposed protocol targets (methodological design choices for future empirical work, not existing literature-derived thresholds):

1. **Documented Substantial Prior Exposure (Proposed Calibration Target):**  
   - Participants with documented, substantial operational history (e.g. a proposed protocol target of several thousand kilometers or regular primary use) exclusively operating either:
     - Pure friction-dominant / 2-pedal vehicles (verified low coast deceleration), or
     - Strong one-pedal / high-regen vehicles (verified high coast deceleration).
2. **Transfer-of-Training Protocol:**  
   - High-fidelity driving simulator or closed test-track instrumented vehicle.
   - Drivers are placed in conditionally automated driving (L3) under controlled secondary tasks.
   - Critical takeover is triggered on an unannounced transfer trial under the alternative vehicle response architecture.
   - Subsequent repeated takeovers are recorded to measure trial-by-trial sensorimotor adaptation curves.
3. **High-Frequency Continuous Telemetry:**  
   - Telemetry sampled at sufficiently high frequency (e.g. a proposed engineering target of $\ge 100\text{ Hz}$) to adequately resolve sub-100ms pedal transit and pressure build-up transients.
   - Continuous accelerator and brake pedal displacement, velocity, and force.
   - Driver foot transfer time (gas release to brake touch).
   - First effective brake stroke amplitude ($u_{initial}$).
   - Secondary brake adjustments (re-applications, oscillations).
4. **Target Estimands:**  
   - Directly estimate the first-stroke pedal deficit: $\Delta u = u_{adapted} - u_{transfer}$.
   - Directly estimate any transfer-induced hesitation latency: $\Delta t_{hesitation}$.

Until such an experiment is executed and analyzed, Branch C cannot proceed empirically.

---

## 13. Relationship to Validated Results (A0 / A1)

Branch A1 established that in time-critical emergency takeovers, the safety boundary is dominated by:
1. The **first-order longitudinal vehicle response** ($a_{coast}$) during the driver's reaction latency $[0, t_{reaction})$, saving $5.7 - 11.9\text{ m}$ of stopping distance.
2. The **hardware brake build-up ramp** ($t_{buildup}$).

The current Phase-1 driver model deliberately represents the emergency response as a full-brake step command ($u_{brake} = 1.0$) after the frozen reaction delay. This is a modeling assumption used to isolate vehicle-side recoverability boundaries, not an empirical claim that all or most human drivers behave this way in real-world emergencies. While studies such as Roche et al. (L003) observe that drivers in critical takeovers frequently brake strongly, naturalistic and simulator driving exhibits substantial behavioral variance (hesitation, partial braking, steering avoidance). Preserving this modeling assumption cleanly separates the physical vehicle recovery envelope from unconstrained human behavioral variance.

Therefore:
- In the marginal critical boundary identified by A1, the open-loop step model ($u=1.0$) is a defensible, robust benchmark for vehicle hardware capability.
- Driver internal-model mismatch is not identifiable within the current model and does not alter the physical vehicle recovery boundary established in A1.

---

## 14. Programmatic Verification

The findings of this audit are verified programmatically in [`tests/test_c0_identifiability.py`](../../tests/test_c0_identifiability.py):
- `test_current_human_model_has_no_mismatch_pathway`: Verifies `HumanDriverConfig` exposes only `t_reaction` and `u_target`, with zero internal-model state.
- `test_command_trajectory_invariant_across_vehicle_profiles`: Confirms the human command is strictly bit-identical across diverse vehicle profiles.
- `test_dataset_inventory_lacks_driver_familiarity`: Verifies programmatically that zero datasets in `dataset_inventory.csv` contain driver EV/ICE familiarity fields.
