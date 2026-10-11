# Vehicle-Aware Human Fallback: Braking-Only Recoverability and Evidence-Boundary Analysis

**Repository:** `vehicle-aware-human-fallback`
**Author:** Fengzhe Li
**License:** MIT (Source Code)
**Python Version:** Python >= 3.10 (tested on Python 3.14.5)

---

## Research Question

> Under what combinations of vehicle dynamics, human driver capability, handover policy, and scenario criticality does human fallback remain an effective and physically recoverable safety mechanism during time-critical automated-driving takeovers?

In Level 3 (conditionally automated) driving, when an automated driving system reaches its operational design domain (ODD) limit or detects an unmanageable hazard, it issues a Takeover Request (TOR) to transition control authority to the human driver. Conventional safety engineering often evaluates takeover safety primarily through *takeover lead time* (e.g., Time-to-Collision at TOR). This project investigates whether fallback recoverability is governed by joint physical interactions among:
1. **Vehicle braking capability and road friction** ($\mu$, $a_{\max}$, actuator delay, hydraulic pressure rise);
2. **Human response latency and action sequencing** ($t_{\text{button}}$, brake onset, steering onset);
3. **Control authority transition policies** (timing of automation authority withdrawal vs. effective human input); and
4. **Initial kinematic state and scenario criticality** ($v_0$, TTC, road stationing).

---

## What This Repository Contains

This repository contains the complete open-source scientific codebase, verification test suite, derived analytical datasets, claim ledger, and deterministic figure-generation pipelines for the project:

- **D003 Evidence and Observability Audit:** A complete signal-processing and control-channel audit of the TU Delft conditionally automated driving takeover simulator dataset (D003; Happee et al.), analyzing 513 trials across 57 participants.
- **Human Response Timing Analysis:** Empirical distributions of driver mode-switch button response times ($t_{\text{button}}$), repeated-exposure practice slopes, and carry-over sensitivity models across consecutive TOR exposures.
- **Vehicle and Automation Parameter Evidence:** Road-load deceleration models calibrated from official EPA certification test data, paired with physical braking limits (Coulomb friction caps $\mu g$, hydraulic actuation delay $t_2$, deceleration rise time $t_3$).
- **Deterministic Interval-Bounded Braking Model (Phase R3B):** An analytical, open-loop kinematic model calculating required stopping time $T_{\text{req}}$ and margin $\Delta T = \text{TTC} - T_{\text{req}}$ across parameter intervals, with closed-form coordinatewise-monotonicity guards.
- **P0/P1/P2 Counterfactual Transition Branches:** Three distinct handover authority policies modeling automation deceleration withdrawal relative to human control reacquisition.
- **Steering Sequence Descriptive Analysis (Phase R4V):** Empirical timing of lateral steering-angle activity onset relative to TOR, lane-marker crossing times, indicator activation, and along-road hazard station reconstruction.
- **Identifiability Boundary Analysis:** Formal classification of what can and cannot be mathematically identified or causally linked using public simulator telemetry alone.
- **Comprehensive Claim Ledger:** 42 formally audited, frozen claims ([`research/R5A_CLAIM_LEDGER.csv`](research/R5A_CLAIM_LEDGER.csv)) with explicit epistemic labels: 33 `EMPIRICAL_DESCRIPTIVE`, 2 `ANALYTICAL_CLOSED_FORM`, 3 `COUNTERFACTUAL_INTERVAL`, 4 `UNIDENTIFIABLE_OR_BLOCKED`.
- **Deterministic Thesis Figures:** Reproduction pipeline rendering 12 publication figures ([F1–F10, FA1–FA2](thesis/figures/)) with bit-identical PDF and PNG hash verification.

![Figure F1: Evidence and Model Architecture](thesis/figures/F1_evidence_architecture.png)
*Figure F1: Four-layer research framework separating vehicle response, human control reacquisition, transition policy, and scenario criticality, supported by an empirical observation layer and constrained by identifiability gates.*

---

## Main Findings (Grounded in Frozen Claim Ledger)

All findings reported below are strictly bounded by the frozen R5A Claim Ledger ([`research/R5A_CLAIM_LEDGER.csv`](research/R5A_CLAIM_LEDGER.csv)):

1. **Driver Mode-Switch Button Timing ($t_{\text{button}}$):**
   Across 492 anchorable D003 trials, mode-switch button actuation exhibits a median of **1.65 s** (IQR: 1.25–2.00 s; 5th–95th percentile: 0.95–2.90 s; Claim L03 notes button press is intent signaling, not hazard response time). Within participants, $t_{\text{button}}$ decreased modestly with repeated exposure (**$-0.033\text{ s}$ per exposure**, 95% CI $-0.058$ to $-0.007$; about $-0.26\text{ s}$ across 8 exposures; **associational only**; **Claim L01**).
2. **Inability to Identify Driver Braking in D003:**
   Longitudinal brake pedal telemetry in D003 is dominated by automated deceleration commands that straddle the mode switch (`Manual_Start`) and persist for up to $0.80\text{ s}$ into manual control (Claims L05, L06). Because the vehicle control state remains static (`state = 2.0`, Claim L07), independent human driver braking onset and pedal force cannot be identified from D003 telemetry (Claim L08).

   ![Figure F3: Longitudinal Control Channels Across Manual Start](thesis/figures/F3_longitudinal_channels_across_manual_start.png)
   *Figure F3: Empirical telemetry traces across Manual_Start in D003, showing scripted automated deceleration commands persisting into the manual driving phase (Claims L05, L06).*

3. **Deterministic Braking Recoverability (R3B Interval Slices):**
   Across the **150 canonical scenario–friction–policy evaluation cases** (25 speed/TTC scenarios $\times$ 2 friction levels $\times$ 3 transition policies):
   - **58 cases** are **ROBUSTLY SATISFIED** ($\min \Delta T \ge 0.01\text{ s}$ across the full parameter interval);
   - **47 cases** are **PARAMETER-SENSITIVE** ($\min \Delta T < 0 < \max \Delta T$, where recoverability depends strictly on where actual human/vehicle parameters fall within the assumed bounds);
   - **45 cases** are **ROBUSTLY UNSATISFIED** ($\max \Delta T \le -0.01\text{ s}$ across the full parameter interval; Claims L19, L20).

   ![Figure F5: R3B Classification Matrix](thesis/figures/F5_r3b_classification_matrix.png)
   *Figure F5: Braking-only recoverability classification across 150 scenario cases: 58 robustly satisfied, 47 parameter-sensitive, and 45 robustly unsatisfied (Claim L19). S/P/U labels and grayscale intensity distinguish the three within-model classifications; these are necessary-condition results, not safety labels.*

   ![Figure F6: Required Braking Time Bounds](thesis/figures/F6_r3b_t_required_bounds.png)
   *Figure F6: Deterministic interval bounds on required stopping time $T_{\text{req}}$ versus available TTC, showing parameter sensitivity dominated by assumed human braking latency $t_1$ (Claims L20, L24).*

4. **TTC is the Dominant Longitudinal Separator:**
   Within the deterministic braking model, initial TTC is the primary determinant of recoverability. High-TTC scenarios ($\ge 5.0\text{ s}$) are robustly satisfied at moderate highway speeds, whereas short-TTC emergency scenarios ($\le 2.5\text{ s}$) cannot be recovered by braking alone on low-friction surfaces ($\mu = 0.5$) under any policy (Claims L20, L25).
5. **Friction and Delay Sensitivity:**
   Pavement friction coefficient $\mu$ caps achievable deceleration at $\mu g$, acting as a hard physical constraint regardless of chassis braking hardware capability $a_{\max}$ (Claims L22, L23). The width of the required braking time interval $[T_{\text{req},\min}, T_{\text{req},\max}]$ is heavily dominated by the assumed human braking latency window $t_1 \in [1.15, 3.00]\text{ s}$ (Claims L24, L26).
6. **Steering Activity Timing vs. Assumed Braking Window:**
   In D003, empirical steering-angle activity onset occurs at a median of **3.85 s** post-TOR (IQR: 3.00–4.88 s; Claim L09). Measured from TOR, descriptive steering-angle activity onset in D003 **falls predominantly after the upper end of the R3B assumed braking-delay interval** ($[1.15, 3.00]\text{ s}$): $75.4\%$ of onsets fall after $3.00\text{ s}$ with the primary detector ($n = 491$), none before $1.15\text{ s}$, and a majority for every detector compared ($57$–$87\%$) and in every scenario cell ($51$–$98\%$; Claim L41).
   *Required qualifiers (Claim L41):* This observation is a cross-layer descriptive comparison between an empirical lateral signal event and an exogenous longitudinal modelling assumption. R3B $t_1$ is a model assumption, not an observed braking delay; steering authorship is unverified (Claim L11); the exact fraction depends on the detector definition (Claim L09); and the majority relationship does not hold against the $4.0\text{ s}$ supplementary bound ($47\%$ after $4.0\text{ s}$). No driver braking timing is implied.

   ![Figure F9: Steering Sequence vs. Assumed Braking Interval](thesis/figures/F9_steering_sequence_vs_assumed_interval.png)
   *Figure F9: Empirical steering-angle activity onsets falling predominantly after the upper boundary of the assumed braking-delay window $[1.15, 3.00]\text{ s}$ (Claim L41; descriptive cross-layer comparison; no driver braking implied).*

7. **Combined Recoverability is Unidentifiable:**
   Because lateral hazard clearance margins, obstacle dimensions, and lane widths are missing from simulator logs, and independent driver braking is unobservable, joint longitudinal/lateral recoverability cannot be empirically validated without ungrounded synthetic assumptions (Claims L27, L29, L30).

---

## What the Project Does NOT Claim

To maintain strict scientific and assurance integrity, this project explicitly disclaims the following:

- **NO System-Level Safety Prediction:** The project does not predict real-world collision probabilities or claim that any vehicle or automation system is "safe" or "unsafe" (Claim L31).
- **NO Empirical Driver Braking Model:** No human braking reaction time distribution or brake pedal transfer function was fitted to D003, because driver braking inputs are confounded by automation script commands (Claims L05, L06).
- **NO Validated Combined (Braking + Steering) Envelope:** The project does not claim to have proven combined evasive trajectory recoverability. Longitudinal braking slices and descriptive lateral steering sequences are evaluated as separate, uncomposed evidence layers (Claim L30).
- **P0/P1/P2 are Counterfactual Model Branches:** The transition policies analyzed in Phase R3B are deterministic mathematical models representing hypothetical authority timing, not validated production controller software (Claims L24, L25).
- **R3B is a Necessary-Condition Analysis:** The deterministic braking model proves *necessary conditions* for stopping without collision; satisfying $T_{\text{req}} \le \text{TTC}$ does not guarantee safe operational recovery in complex traffic (Claims L19, L29).

![Figure F10: Identifiability Boundary](thesis/figures/F10_identifiability_boundary.png)
*Figure F10: Identifiability boundary distinguishing identifiable analytical and descriptive quantities from blocked composite recoverability claims across simulator and physical domains.*

---

## Extension: VLA-Informed Handover Feasibility Analysis (`extensions/vla_handover_feasibility/`)

Building upon the frozen baseline framework above, this repository includes a physically grounded research extension under [`extensions/vla_handover_feasibility/`](extensions/vla_handover_feasibility/) that evaluates how genuine driving Vision-Language-Action (VLA) trajectory predictions interact with vehicle-dynamics constraints (`C1`–`C10`) and the Phase R3B braking-only human fallback recoverability framework (`P0`, `P1`, `P2`).

**Core Extension Research Question:**
> *Under what conditions do VLA-generated driving trajectories violate specified vehicle-dynamics constraints, and how does the available braking-only human fallback margin change under explicitly defined takeover-request timing assumptions?*

### Strict Epistemic Separation

The extension enforces a strict four-way epistemic boundary across all code, artifacts (`EXT-VLA-C01` through `EXT-VLA-C06`), and visualizations:
1. **Genuine Driving VLA Trajectory Predictions (`EMPIRICAL_MODEL_OUTPUT`):** Real neural network forward passes of **AutoVLA** (`Zewei-Zhou/AutoVLA` $\to$ `AutoVLA_PDMS_89.ckpt`, built on `Qwen/Qwen2.5-VL-3B-Instruct` with `2,048` physical `<action_k>` tokens, mapped with an exact `825 / 825` `strict=True` state-dict bijection to `transformers 5.x`) on 7 real multi-view driving scenes (`3 cameras × 4 history frames = 12 RGB images` per scene + ego kinematic state) extracted from the public `OpenDriveLab/OpenScene` (`navsim_logs/mini` + `sensor_blobs/mini`) nuPlan driving logs. AutoVLA outputs `10` discrete `<action_k>` tokens per scene decoded via `agent_vocab.pkl` into a `5.0 s`, `10-step` (`Δt = 0.5 s`) SE(2) trajectory `[x, y, heading]` in the ego-vehicle frame. **AutoVLA does not output a takeover request (TOR) signal (`predicts_human_takeover_request = False`).**
2. **Independent Physical & Kinematic Feasibility Verification (`ANALYTICAL_CLOSED_FORM`):** Each predicted trajectory is audited against 10 explicit vehicle-dynamics checks (`C1`–`C10`, using central finite differences at interior steps and forward/backward differences at boundaries) under nominal (`μ = 1.0`) and wet (`μ = 0.5`) road friction assumptions, plus 4 clearly labelled **synthetic stress fixtures** (`SYNTHETIC_FIXTURE_ONLY`, never mixed with real VLA outputs).
3. **Counterfactual R3B Human Takeover Analysis (`COUNTERFACTUAL_INTERVAL`):** Using the unchanged Phase R3B interval braking solver ([`src/experiments/r3b_braking_bounds.py`](src/experiments/r3b_braking_bounds.py) and [`src/handover/models.py`](src/handover/models.py)), the extension compares braking-only recoverability across policies `P0`, `P1`, and `P2` at two counterfactual request horizons:
   - **Immediate TOR at $\tau_{\text{req}} = 0.0\text{ s}$:** Grounded in the **observed** ego speed $v_0$ and initial obstacle distance $d_0$.
   - **Delayed TOR at $\tau_{\text{req}} \in \{0.5, 1.0, 1.5, 2.0, 2.5, 3.0\}\text{ s}$:** Evaluated at the **hypothetical** future ego speed and obstacle gap implied if the vehicle were to follow the AutoVLA trajectory up to $\tau_{\text{req}}$ before requesting human intervention. Both distance-based margins ($\Delta d_{\text{stop}} = d_{\text{obs}} - d_{\text{stop}}$ in metres) and time-based margins ($\Delta T = \text{TTC} - T_{\text{req}}$ in seconds) are reported.
4. **Evidence Gaps & Methodological Boundaries (`INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE`):** Stationary baseline scenes (`scene_07`, $v_0 = 0.0019\text{ m/s} \le 0.05\text{ m/s}$), obstacle-free open-road scenes without an assumed counterfactual obstacle (`scene_01`, `scene_06`, `scene_07`), and steps departing the 1D longitudinal corridor ($|y| > 1.75\text{ m}$ or $|\psi| > 0.35\text{ rad}$) are explicitly gated out of longitudinal collision-recovery scoring.

### Audited 7-Scene Empirical & Counterfactual Summary

All 7 scenes are verified end-to-end by [`provenance_audit.py`](extensions/vla_handover_feasibility/provenance_audit.py) across `scenes_manifest.json`, SHA-256 digests of the 84 camera JPEGs (`camera_images_sha256.json`), cached AutoVLA action tokens (`artifacts/predictions/scene_*_fast.json`), `agent_vocab.pkl` decoding, `evaluation_summary.json`, and the interactive HTML/PDF report (`0` provenance mismatches):

| Scene ID | nuPlan Token | $v_0$ ($\text{m/s}$) | $a_{x,0}$ ($\text{m/s}^2$) | Prompt $\|a_0\|$ ($\text{m/s}^2$) | Command (Source / Leakage Flag) | ADE ($\text{m}$) | FDE ($\text{m}$) | Nominal ($\mu=1.0$) | Wet ($\mu=0.5$) | R3B Counterfactual Summary ($P_1$, Nominal $\mu=1.0$) |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `scene_01_high_speed_open_road` | `5143e810d84656d0` | `13.58` | `-0.15` | `0.19` | `keep forward` (Clean) | `0.36` | `0.76` | `SATISFIED` | `SATISFIED` | `INSUFFICIENT_EVIDENCE` (Observed); Counterfactual $d_0=45\text{ m}$ schedule badged separately |
| `scene_02_stationary_lead_obstacle` | `3cacb287d398542f` | `6.95` | `+1.30` | `1.35` | `turn left` (**Leakage Flag**) | `2.42`* | `3.47`* | `SATISFIED` | **`VIOLATED` (`C7`)** | `ROBUSTLY_SATISFIED` ($\tau_{\text{req}}\le 2.0\text{ s}$) $\to$ departs 1D corridor ($\tau_{\text{req}}\ge 2.5\text{ s}$) |
| `scene_03_close_urban_lead_following` | `7a524614561c54ef` | `13.05` | `+0.09` | `0.10` | `keep forward` (Clean) | `1.03` | `2.27` | `SATISFIED` | `SATISFIED` | `PARAMETER_SENSITIVE` ($\tau_{\text{req}}\le 1.5\text{ s}$) $\to$ `ROBUSTLY_UNSATISFIED` ($\tau_{\text{req}}\ge 2.0\text{ s}$) |
| `scene_04_fast_arterial_lead_vehicle` | `c48640204ad758c4` | `6.21` | `-0.07` | `0.07` | `keep forward` (Clean) | `0.54` | `2.09` | `SATISFIED` | `SATISFIED` | `ROBUSTLY_SATISFIED` across $\tau_{\text{req}} \in [0.0, 3.0]\text{ s}$ |
| `scene_05_active_braking_deceleration` | `b49c80be2d0d5bb9` | `4.31` | `-1.55` | `1.56` | `keep forward` (Clean) | `6.25` | `12.90` | **`VIOLATED` (`C10`)** | **`VIOLATED` (`C10`)** | `ROBUSTLY_SATISFIED` ($\tau_{\text{req}}=0\text{ s}$, margin `[+6.60, +13.71] m`) $\to$ `PARAMETER_SENSITIVE` ($\tau_{\text{req}}=2.0\text{ s}$, `[-4.40, +5.46] m`) |
| `scene_06_intersection_turn_maneuver` | `c9d4d04945e85ef8` | `8.78` | `-0.40` | `1.41` | `turn left` (**Leakage Flag**) | `0.66`* | `1.88`* | `SATISFIED` | `SATISFIED` | `INSUFFICIENT_EVIDENCE` (Turn scenario without corridor obstacle) |
| `scene_07_stationary_ego_baseline` | `e9138a74627452c2` | `0.00` | `-0.02` | `0.02` | `keep forward` (Clean) | `3.93` | `10.10` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` (Stationary baseline $v_0 \le 0.05\text{ m/s}$) |

*\*Note on `scene_02` and `scene_06` ADE/FDE (`EXT-VLA-C06`):* See the explicit methodological disclosure below regarding driving-command conditioning and future-displacement leakage.

### Key Extension Findings & Methodological Disclosures

1. **Active-Braking Longitudinal State Mismatch (`EXT-VLA-C02`, `scene_05`):**
   In `scene_05_active_braking_deceleration`, the ego vehicle is actively braking at $a_{x,0} = -1.5525\text{ m/s}^2$ ($v_0 = 4.3103\text{ m/s}$). Because the upstream official AutoVLA NAVSIM prompt template (`autovla/vla-scripts/navsim_eval.py`) formats acceleration as the unsigned scalar norm $\sqrt{a_x^2 + a_y^2} = 1.56\text{ m/s}^2$, the model receives no sign indicating deceleration versus acceleration. While Step 1 ($t = 0.5\text{ s}$) decelerates mildly at $-0.8841\text{ m/s}^2$ from visual cues, Step 2 ($+0.7917\text{ m/s}^2$) and Step 3 ($+1.5442\text{ m/s}^2$) reverse into strong positive acceleration (`ADE = 6.2543 m`, `FDE = 12.8998 m`), triggering `C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY` ($|\hat{a}_{x,\text{early}} - a_{x,0}| = |+1.5442 - (-1.5525)| = 3.0967\text{ m/s}^2 > 2.50\text{ m/s}^2$). Under counterfactual R3B policy $P_1$ on dry pavement ($\mu = 1.0$), immediate takeover at $\tau_{\text{req}} = 0.0\text{ s}$ is `ROBUSTLY_SATISFIED` ($\Delta d_{\text{stop}} \in [+6.60, +13.71]\text{ m}$), whereas delaying takeover to $\tau_{\text{req}} = 2.0\text{ s}$ along the hypothetical accelerating VLA trajectory degrades recoverability to `PARAMETER_SENSITIVE` ($\Delta d_{\text{stop}} \in [-4.40, +5.46]\text{ m}$) and `ROBUSTLY_UNSATISFIED` by $\tau_{\text{req}} = 3.0\text{ s}$ (`[-11.83, -1.78] m`).
2. **Single-Scene Controlled Signed-Acceleration Ablation (`EXT-VLA-C05`, `scene_05`):**
   To test whether unsigned acceleration formatting contributes directly to the `scene_05` violation, we executed a single-variable controlled experiment holding the checkpoint, 12 camera images, greedy decoding (`do_sample=False`), velocity ($4.31\text{ m/s}$), and command (`keep forward`) strictly identical while replacing only `"1.56 m/s^2"` with signed `"-1.55 m/s^2"` ([`ablation_scene_05_signed_accel.json`](extensions/vla_handover_feasibility/artifacts/ablation_scene_05_signed_accel.json)):
   - Over the initial `0.0–2.0 s` braking phase (Steps 1–4), AutoVLA sustains continuous deceleration ($a_{\text{lon}} = -0.8841, -0.9854, -1.0846\text{ m/s}^2$) and brakes to a standstill at $x = 6.93\text{ m}$ (matching ground-truth stopping distance $x_{\text{GT}}(2.5\text{ s}) = 6.92\text{ m}$), reducing `0–2.0 s` braking-phase ADE by **88.1%** (`1.2131 m` $\to$ `0.1448 m`) and full `5.0 s` ADE by **61.3%** (`6.2543 m` $\to$ `2.4210 m`, `FDE = 8.7228 m`).
   - **Explicit Scientific Limitation:** Because `AutoVLA_PDMS_89.ckpt` was trained exclusively on non-negative acceleration norms ($\|a\| \ge 0$), passing `"-1.55 m/s^2"` is a **single-scene, out-of-distribution (OOD) diagnostic intervention**, not a validated model fix. At Step 9 ($t = 4.5\text{ s}$), after coming to rest (`<action_0>` at Step 8), the OOD prompt emits a `5.8 cm` backward jitter token (`<action_126>`, $\Delta x = -0.058\text{ m}$). Fixing active-braking handover safety in driving VLAs requires **retaining signed longitudinal/lateral acceleration components (`a_lon, a_lat`) during VLA training** alongside an independent physical verifier (`Phase C`).
3. **Wet-Surface Lateral Acceleration Violation (`EXT-VLA-C03`, `scene_02`):**
   In `scene_02_stationary_lead_obstacle`, AutoVLA predicts an evasive left-turn trajectory reaching peak lateral acceleration $|a_{\text{lat}}| = 2.2721\text{ m/s}^2$, which is `SATISFIED` under nominal dry limits ($4.00\text{ m/s}^2$) but violates the conservative wet-surface lateral stability threshold `C7_LATERAL_ACCELERATION_LIMIT` on wet pavement ($\mu = 0.5$, threshold $2.00\text{ m/s}^2$).
4. **Methodological Disclosure — Driving-Command Conditioning & Future-Displacement Leakage Risk (`EXT-VLA-C06`):**
   AutoVLA requires a discrete high-level driving command (`turn left`, `turn right`, `keep forward`) in its input prompt. In the upstream NAVSIM/OpenScene evaluation convention, this command is derived from the recorded ground-truth route/trajectory rather than an independent pre-trip navigation system. Specifically:
   - In **`scene_02_stationary_lead_obstacle`** (`3cacb287d398542f`), the ego vehicle approaches a stationary in-lane obstacle (`55.49 m` ahead) while the recorded human ground-truth trajectory executes a left turn / lane departure ($y_{\text{GT}}(3.0\text{ s}) = +4.5128\text{ m}$, $y_{\text{GT}}(5.0\text{ s}) = +16.6678\text{ m}$). When an unknown raw approach command is resolved to `"turn left"` from future ground-truth lateral displacement $y_{\text{GT}} > 2.0\text{ m}$ (matching the recorded OpenScene driving command bit `[1, 0, 0, 0]`), the VLA prompt is conditioned on the future lateral maneuver direction.
   - In **`scene_06_intersection_turn_maneuver`** (`c9d4d04945e85ef8`), the `"turn left"` prompt command similarly corresponds to a trajectory with $y_{\text{GT}}(3.0\text{ s}) = +4.0889\text{ m}$.
   - **Scientific Consequence:** While the remaining five scenes (`scene_01`, `scene_03`, `scene_04`, `scene_05`, `scene_07`) use `"keep forward"` commands with $|y_{\text{GT}}(3.0\text{ s})| < 0.10\text{ m}$, the open-loop `ADE`/`FDE` metrics on **`scene_02` (`2.42 m` / `3.47 m`)** and **`scene_06` (`0.66 m` / `1.88 m`)** are **command-conditioned evaluations** and must **not** be interpreted as strictly leakage-free, unconditioned maneuver-selection predictions. All original recorded inference inputs and cached prediction artifacts (`artifacts/predictions/scene_*_fast.json`) are preserved unmodified, and `provenance_audit.py` explicitly flags both scenes (`future_displacement_command_leakage_flag = True`).

### Interactive English Research Dashboard Screenshots

The extension includes a deterministic HTML/PDF report generator ([`report_generator.py`](extensions/vla_handover_feasibility/report_generator.py)) and automated headless Chromium visual QA inspector ([`browser_qa.py`](extensions/vla_handover_feasibility/browser_qa.py)):

![Screenshot 01: Executive Findings, Methodological Leakage Disclosure, and Overview](extensions/vla_handover_feasibility/artifacts/report/screenshots/01_executive_findings_and_overview.png)
*Screenshot 01: Executive Research Summary (`EXT-VLA-C01`–`EXT-VLA-C06`), driving-command leakage disclosure banner, interactive control bar, and Scene 01 overview.*

![Screenshot 02: Scene 05 Active-Braking Violation and Controlled Signed-Acceleration Ablation](extensions/vla_handover_feasibility/artifacts/report/screenshots/02_scene_05_braking_violation_and_ablation.png)
*Screenshot 02: Scene 05 `C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY` violation (`+1.5442 m/s^2` vs `-1.5525 m/s^2`) and single-variable signed-acceleration prompt ablation (`-1.55 m/s^2`) with OOD causal boundary notices.*

![Screenshot 03: Scene 03 Urban Lead-Following R3B Counterfactual Handover Analysis](extensions/vla_handover_feasibility/artifacts/report/screenshots/03_scene_03_urban_lead_r3b_handover.png)
*Screenshot 03: Scene 03 R3B braking-only stopping distance (`[m]`) and time (`[s]`) margins across takeover request times $\tau_{\text{req}} \in [0.0, 3.0]\text{ s}$ and policies `P0`, `P1`, and `P2`.*

![Screenshot 04: Scene 01 Counterfactual Obstacle Provenance Badge Verification](extensions/vla_handover_feasibility/artifacts/report/screenshots/04_scene_01_counterfactual_d0_provenance.png)
*Screenshot 04: Scene 01 counterfactual $d_0 = 45.00\text{ m}$ schedule explicitly badged as `Observed Ego (t0) + Assumed Obstacle (d0)` at $\tau_{\text{req}} = 0.0\text{ s}$ and `Hypothetical VLA + Assumed Obstacle (d0)` at $\tau_{\text{req}} > 0$.*

---

## Repository Structure

```text
├── docs/                     # Architectural baselines, decision records (D001-D038), audit logs
│   ├── DECISIONS.md          # Chronological record of all project decisions
│   ├── PROJECT_STATUS.md     # Phase ledger and milestone tracking
│   └── RESEARCH_ARCHITECTURE_V2.md # Four-layer closed-loop research framework
├── experiments/              # Legacy audit and analytical challenge documents (Phases A-H)
├── extensions/               # Research extensions preserving the frozen core baseline
│   └── vla_handover_feasibility/   # Audited AutoVLA trajectory & R3B handover feasibility pipeline
│       ├── artifacts/        # Evaluation summaries, claim register, ablation JSON, cached predictions, HTML/PDF report & PNG screenshots
│       ├── data/             # Scene manifest, SHA-256 camera digest, AutoVLA action codebook (agent_vocab.pkl)
│       ├── tests/            # 16 unit, synthetic-fixture, R3B-adapter, and provenance tests
│       ├── action_tokenizer.py     # Action token regex parser & SE(2) trajectory rollout decoder
│       ├── browser_qa.py           # Headless Chromium visual QA & screenshot generator
│       ├── cloud_gpu_runner.py     # Optional cloud GPU execution wrapper
│       ├── experiment_runner.py    # End-to-end evaluation & R3B counterfactual pipeline
│       ├── extract_navsim_scenes.py # On-demand OpenScene camera frame extractor & SHA-256 verifier
│       ├── provenance_audit.py     # 11-point cryptographic & numerical provenance auditor
│       ├── r3b_adapter.py          # Adapter into unchanged src/vehicle and src/handover modules
│       ├── report_generator.py     # License-compliant English HTML/PDF dashboard generator
│       ├── schemas.py              # Strongly typed dataclasses for scenes, trajectories, and R3B slices
│       ├── trajectory_verifier.py  # Independent C1-C10 physical feasibility verifier & synthetic fixtures
│       └── vla_inference.py        # Sequential batch_size=1 AutoVLA inference runner
├── research/                 # Foundational research registries, charters, and claim ledgers
│   ├── R5A_CLAIM_LEDGER.csv  # Authoritative 42-claim ledger (L01-L42, untouched)
│   ├── R3A_SOURCE_REGISTER.csv # External literature and standards evidence base
│   └── data_matrix/          # D003 field audits, EPA coastdown parameter derivations
├── results/                  # Committed analytical outputs, summary tables, and figures
│   ├── R1_ingestion_validation/   # D003 ingestion QA and owner reconciliation
│   ├── R2A_event_vehicle_descriptives/ # Channel activity diagnostics & populations
│   ├── R2B_repeated_exposure/     # Exposure slope models & participant trends
│   ├── R2C_lite/                  # Carry-over sensitivity models
│   ├── R3B_braking_bounds/        # Deterministic interval braking bounds & CSVs
│   ├── R4V_channel_authorship/    # Control channel authorship validation
│   └── R4V_steering_sequence/     # Steering sequence descriptives & hazard reconstruction
├── src/                      # Core project source code (Python package, untouched)
│   ├── data/                 # Strict D003 loader, population filters, QA pipelines
│   ├── driver/               # Parameterized driver response models
│   ├── experiments/          # Canonical experiment runners (R1, R2A, R2B, R2C, R3A, R3B, R4V)
│   ├── figures/              # R6A thesis figure rendering pipeline
│   ├── handover/             # Handover timeline models and policy definitions
│   ├── metrics/              # Control activity detectors, analytical derivatives, margins
│   ├── provenance/           # Structured metadata registries and report generators
│   └── vehicle/              # Physical vehicle models, road load, braking kinematics
├── tests/                    # Core automated pytest suite
├── thesis/
│   └── figures/              # 12 canonical frozen publication figures (PNG and PDF)
│       └── figure_manifest.json # Cryptographic SHA256 hashes of all figure outputs
├── .gitignore                # Production artifact exclusions and third-party dataset protections
├── LICENSE                   # MIT License
├── pytest.ini                # Pytest configuration
├── README.md                 # Project overview and reproduction guide
└── requirements.txt          # Python package dependencies
```

---

## Installation

### Prerequisites
- Python 3.10 or higher (tested on Python 3.14.5)
- Standard virtual environment (`venv`)

### Setup Instructions
```bash
# 1. Clone the repository
git clone https://github.com/fengzhe-li/vehicle-aware-human-fallback.git
cd vehicle-aware-human-fallback

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running Tests & Offline Reproducibility

### 1. VLA Handover Feasibility Extension Suite & Provenance Audit

The VLA extension is 100% reproducible offline from a fresh Git clone without requiring raw camera JPEGs or the AutoVLA checkpoint:

```bash
# Run the 16 extension unit, synthetic-fixture, R3B-adapter, and provenance tests
pytest extensions/vla_handover_feasibility/tests -v

# Re-run the physical verifier and R3B counterfactual pipeline from cached AutoVLA predictions
python3 -m extensions.vla_handover_feasibility.experiment_runner --skip-inference

# Re-generate the English HTML/PDF dashboard and run the strict provenance auditor
python3 -m extensions.vla_handover_feasibility.report_generator
python3 -m extensions.vla_handover_feasibility.provenance_audit
```

**Expected Extension Test Output:**
```text
================= 16 passed in ~3.0s =================
```

### 2. Core Baseline Test Suite

```bash
# Run the original baseline test suite
pytest tests/
```

**Recorded Baseline Test Output (430 passed, 4 known pre-existing release/environment failures, 1 skipped, 1 deselected):**
- `430 passed, 1 skipped, 1 deselected` across all mathematical, kinematic, D003 ingestion, R3B monotonicity (`27/27 passed`), and scientific-invariance (`test_scientific_results_unchanged`) tests.
- The **4 known pre-existing baseline failures** (documented in [`extensions/vla_handover_feasibility/artifacts/baseline_pytest_output.txt`](extensions/vla_handover_feasibility/artifacts/baseline_pytest_output.txt)) are left untouched to preserve the frozen baseline:
  1. `tests/test_r2a.py::test_r2a_provenance`, `tests/test_r2b.py::test_r2b_provenance`, and `tests/test_r2c_lite.py::test_r2c_provenance`: Fail with `git diff` exit code `128` (`fatal: bad object 9d1c41d01a5a141f07020610c58879b76b214d11`) because the initial public release squashed pre-release draft history referenced in frozen `results/R2*/provenance.json`.
  2. `tests/test_r6a_figures.py::test_deterministic_rendering`: Fails on `FA2_participant_exposure_slopes.pdf` byte-level SHA-256 comparison due to Matplotlib / Python `3.14` PDF stream metadata differences against the frozen PDF generated during release (`test_scientific_results_unchanged` passes).

---

## Deterministic Figure Reproduction

All 12 thesis publication figures ([F1–F10, FA1–FA2](thesis/figures/)) can be deterministically rendered from stored analytical outputs:

```bash
# Render all figures into thesis/figures/
python3 -m src.figures.r6a_thesis_figures thesis/figures
```

Figure rendering is byte-deterministic on the reference build environment: outputs match the cryptographic hashes recorded in [`thesis/figures/figure_manifest.json`](thesis/figures/figure_manifest.json).

---

## External Data Availability & Licensing Compliance

Raw third-party datasets and multi-gigabyte model weights are **not redistributed** in this Git repository to respect third-party dataset licenses and repository size limits:

1. **TU Delft Conditionally Automated Takeover Dataset (D003):**
   - **Authors:** R. Happee et al. | **Repository:** 4TU.ResearchData | **DOI:** [`10.4121/uuid:e853b4e6-cba0-4e13-ac4b-506716ddd0fb`](https://doi.org/10.4121/uuid:e853b4e6-cba0-4e13-ac4b-506716ddd0fb) | **License:** CC BY 4.0
   - **Placement:** Download `tu_delft_takeover.zip` and place in `data/external/d003/`.
2. **EPA Test Car Certification Database:**
   - **Source:** US EPA (`24-testcar-2025-05.xlsx`) | **License:** Public Domain (US Government Work)
   - **Placement:** Place in `data/external/epa/`.
3. **OpenScene / NAVSIM Mini Sensor Blobs & AutoVLA Checkpoint (VLA Extension Live Inference Only):**
   - **Camera Images (`84 JPEGs`):** Derived from Motional nuPlan (`CC BY-NC-SA 4.0`) via `OpenDriveLab/OpenScene`. Raw `.jpg` files (`data/scenes/*/images/*.jpg`) are excluded from Git via `.gitignore` and replaced by cryptographic SHA-256 digests in [`extensions/vla_handover_feasibility/data/camera_images_sha256.json`](extensions/vla_handover_feasibility/data/camera_images_sha256.json). To materialize and verify the 84 camera frames on demand for live AutoVLA inference, run:
     ```bash
     python3 -m extensions.vla_handover_feasibility.extract_navsim_scenes
     ```
   - **AutoVLA Pretrained Checkpoint (`AutoVLA_PDMS_89.ckpt`):** Hosted on Hugging Face under [`Zewei-Zhou/AutoVLA`](https://huggingface.co/Zewei-Zhou/AutoVLA) (`ucla-mobility/AutoVLA`, MIT/Apache-2.0 compatible) and downloaded on demand when running live inference without `--skip-inference`.

---

## Reproducibility Scope

- **Committed Derived Results:** All derived CSV summaries, parameter tables, and statistical models in `results/`, as well as the cached AutoVLA action-token predictions (`extensions/vla_handover_feasibility/artifacts/predictions/*.json`), kinematic scene manifest (`scenes_manifest.json`), and SHA-256 camera manifest (`camera_images_sha256.json`), are committed directly to the repository. The verification test suites, thesis figure renderer (`r6a_thesis_figures.py`), and VLA evaluation/provenance pipeline execute offline immediately after cloning.
- **Raw Ingestion & Live Inference Pipelines:** If external source archives are downloaded as documented above, both the D003 ingestion pipeline (`src/data/d003_ingest.py`) and live AutoVLA inference (`extensions.vla_handover_feasibility.experiment_runner`) can be re-executed from scratch.
- **Provenance note:** Result records retain the historical development commit (`code_commit`) from which an analysis was produced. These identifiers refer to pre-release development history and are intentionally not part of the curated public-release Git history. For R2A, R2B and R2C, equivalence of the run-relevant dependencies is verified in this release by content hash. Details: [docs/PROVENANCE.md](docs/PROVENANCE.md).

---

## Licensing

- **Project Source Code & Architecture:** Licensed under the [MIT License](LICENSE).
- **Third-Party Data & Pretrained Weights:** External datasets (TU Delft D003, EPA test car data, Motional nuPlan / OpenScene) and external model weights (`ucla-mobility/AutoVLA`, `Zewei-Zhou/AutoVLA`, `Qwen/Qwen2.5-VL-3B-Instruct`) remain subject to their respective upstream licenses. No restricted raw camera imagery is redistributed in this repository.
- **Analytical Outputs:** Derived summary tables and metrics in `results/` and `extensions/vla_handover_feasibility/artifacts/` are provided for academic reproducibility under CC BY 4.0.

---

## Thesis Manuscript Notice

The full doctoral/master's thesis manuscript draft is **intentionally held from public release** pending institutional examination, defense, and degree award. This repository provides the complete open-source software, analytical data, and verification infrastructure supporting the dissertation.
