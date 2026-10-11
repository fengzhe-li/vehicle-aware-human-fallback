# VLA-Informed Handover Feasibility Analysis (`extensions/vla_handover_feasibility`)

**Author:** Fengzhe Li  
**Repository:** [`fengzhe-li/vehicle-aware-human-fallback`](https://github.com/fengzhe-li/vehicle-aware-human-fallback)  
**License:** MIT (Source Code)

---

## 1. Research Objective & Scope

This extension investigates the interaction between genuine Vision-Language-Action (VLA) driving trajectory predictions, vehicle-dynamics feasibility bounds, and the existing R3B braking-only human fallback recoverability framework:

> **Central Research Question:**
> *Under what conditions do VLA-generated driving trajectories violate specified vehicle-dynamics constraints, and how does the available braking-only human fallback margin change under explicitly defined takeover-request timing assumptions?*

### Strict Scientific & Evidence Boundaries

This module is an **extension** of the `vehicle-aware-human-fallback` research repository. All original repository files, the 42-claim ledger ([`research/R5A_CLAIM_LEDGER.csv`](../../research/R5A_CLAIM_LEDGER.csv)), original thesis figures, counterfactual policy definitions ([`src/handover/models.py`](../../src/handover/models.py), [`src/experiments/r3b_braking_bounds.py`](../../src/experiments/r3b_braking_bounds.py)), and established evidence boundaries remain **completely unmodified**.

The pipeline strictly distinguishes between four analytical layers:

1. **Genuine VLA Trajectory Predictions (Phase B):** Real neural network forward passes from `AutoVLA` (`Zewei-Zhou/AutoVLA` $\to$ `AutoVLA_PDMS_89.ckpt`, built on `Qwen/Qwen2.5-VL-3B-Instruct` with 2,048 physical `<action_k>` tokens) on real 12-image multi-view camera history (`CAM_F0`, `CAM_L0`, `CAM_R0`) and ego kinematics from the nuPlan / OpenScene / NAVSIM mini dataset. **AutoVLA does not predict a human takeover request (`predicts_human_takeover_request = False`).**
2. **Independent Physical Trajectory Feasibility Verification (Phase C):** Step-wise kinematic and dynamic verification of the VLA-predicted 10-step trajectory ($\Delta t = 0.5\text{ s}$, horizon $T = 5.0\text{ s}$) against explicit continuity, speed, longitudinal acceleration/braking, lateral acceleration, yaw-rate, road-friction ($\mu g$), and initial-state acceleration continuity (`C1`–`C10`) bounds. Passing these checks (`CONSTRAINTS_SATISFIED`) does **not** establish collision avoidance, human takeover success, or production safety.
3. **Counterfactual R3B Braking-Only Human Fallback Analysis (Phase D & E):** Connects eligible trajectory states at explicitly assumed takeover request times $\tau_{\text{req}} \in \{0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0\}\text{ s}$ to the frozen R3B braking-only stopping distance ($[m]$) and time ($[s]$) bounds (`t1` $\in [1.15, 3.0]\text{ s}$, `t2` $\in [0.05, 0.17]\text{ s}$, `t3` $\in [0.3, 1.2]\text{ s}$, $a_{\max} \in [6.43, 9.10]\text{ m/s}^2$) across policy branches `P0` (`P0|AUTH_AT_EFFECTIVE`, constant-speed pre-control), `P1` (passive coastdown drag $a_{\text{drag}}$), and `P2` (`P2|AUTH_AT_EFFECTIVE`, supported pre-control deceleration $a_{\text{sup}} \in [1.0, 3.0]\text{ m/s}^2$) and road friction $\mu \in \{1.0, 0.5\}$. **Any state at $\tau_{\text{req}} > 0$ is a hypothetical VLA planning state, not observed vehicle motion.**
4. **Explicit Insufficient-Evidence / Non-Applicability Boundaries:** Obstacle distance and TTC are **never** inferred from a single camera image. When a scene has no observed 3D in-lane obstacle annotation and no counterfactual obstacle distance is explicitly specified, or when ego speed is stationary ($v \le 0.05\text{ m/s}$), or when a turning trajectory departs the 1D longitudinal corridor ($|y| > 1.75\text{ m}$ or $|\psi| > 0.35\text{ rad}$), the pipeline returns `INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE`.

---

## 2. Phase A & B — Candidate Driving VLA Audit & Sequential Execution Summary

| Candidate Model | Checkpoint Availability & License | Architecture & Inputs | Output Representation | Local Execution Status on Apple M5 (16 GB) |
| :--- | :--- | :--- | :--- | :--- |
| **OpenDriveVLA** ([`DriveVLA/OpenDriveVLA`](https://github.com/DriveVLA/OpenDriveVLA)) | **Gated (`HTTP 401 Unauthorized`)** on Hugging Face (`OpenDriveVLA/OpenDriveVLA-0.5B`, `3B`, `7B`); Apache-2.0 code license | Qwen2.5-0.5B/3B/7B + custom UniAD 3D perception queries (`track_query`, `map_query`, `bev_embed`) | Textual waypoint coordinates `[x, y]` over 6 steps (3.0 s at 0.5 s) | **BLOCKED:** (1) Gated HF weights return 401 without manual approval; (2) Requires compiling `mmcv-full==1.7.2` with `MMCV_WITH_OPS=1` (NVIDIA CUDA C++ Deformable Attention kernels), `mmdet3d==1.0.0rc6`, `deepspeed`, and pre-extracted UniAD 3D `.pth` queries incompatible with macOS Apple Silicon. |
| **AutoVLA** ([`ucla-mobility/AutoVLA`](https://github.com/ucla-mobility/AutoVLA)) | **Publicly accessible (`gated: False`)** on Hugging Face (`Zewei-Zhou/AutoVLA` $\to$ `AutoVLA_PDMS_89.ckpt`, 16.29 GB); MIT/Apache-2.0 compatible | `Qwen/Qwen2.5-VL-3B-Instruct` extended with 2,048 physical action tokens (`vocab_size = 153,713`). Inputs: 3 cameras (`CAM_F0`, `CAM_L0`, `CAM_R0`) $\times$ 4 frames at 2 Hz + scalar ego speed $v$, scalar unsigned accel norm $\|a\|$, and driving command | `<think>...</think>` Chain-of-Thought wrapper + 10 discrete `<action_k>` tokens decoded via `agent_vocab.pkl` `(2048, 6, 4, 2)` into 10 SE(2) ego poses `(x_m, y_m, heading_rad)` over 5.0 s ($\Delta t = 0.5\text{ s}$) | **RUNNABLE & VERIFIED:** All 825 tensors converted to `bfloat16` `safetensors` (8.14 GB) with `strict=True` key bijection and executed genuinely on Apple M5 (`batch_size=1` sequential execution). |

### Critical Technical Discovery (`transformers 5.x` State-Dict Bijection)

`AutoVLA_PDMS_89.ckpt` was saved under `transformers==4.49.0` with PyTorch Lightning prefix `autovla.vlm.*`, where vision weights are named `autovla.vlm.visual.*` and LLM weights are named `autovla.vlm.model.layers.*`. Under `transformers>=5.0` (`5.19.0`), `Qwen2_5_VLForConditionalGeneration` nests language-model weights under `model.language_model.layers.*` and vision weights under `model.visual.*`. Calling AutoVLA's original `load_state_dict(..., strict=False)` under `transformers 5.x` would silently drop the trained LLM and vision weights. Mapping:
- `autovla.vlm.visual.*` $\to$ `model.visual.*`
- `autovla.vlm.model.*` $\to$ `model.language_model.*`
- `autovla.vlm.lm_head.weight` $\to$ `lm_head.weight`

yields an exact **825 / 825 tensor key and shape bijection (`strict=True`)**.

### Verified 7-Scene Genuine AutoVLA Prediction Summary

All 7 scenes were extracted from the OpenScene / NAVSIM mini dataset (`mini/2021.06.09.14.58.55_veh-35_01894_02311.pkl` and `mini/2021.10.11.07.12.18_veh-50_00211_00304.pkl`) and evaluated sequentially with `batch_size=1`:

| Scene ID (`frame_token`) | Observed $v_0$ ($\text{m/s}$) | Observed $a_{x,0}$ ($\text{m/s}^2$) | Prompt $\|a_0\|$ ($\text{m/s}^2$) | Prompt Command (`y_GT(3.0s)`) | Device / Latency (ms) | Decoded Action Tokens (`<action_k>`) | ADE / FDE vs GT ($\text{m}$) | Phase C Nominal / Wet ($\mu=0.5$) Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scene_01_high_speed_open_road` (`5143e810d84656d0`) | `13.5806` | `-0.1456` | `0.19` | `keep forward` (`-0.04 m`) | `mps` / `162,954.9` | `[21, 127, 266, 896, 1007, 1256, 1007, 896, 11, 11]` | `0.3562` / `0.7638` | `SATISFIED` / `SATISFIED` |
| `scene_02_stationary_lead_obstacle` (`3cacb287d398542f`) | `6.9470` | `+1.3035` | `1.35` | `turn left`* (`+4.51 m`) | `cpu` / `355,750.0` | `[418, 728, 418, 728, 1506, 724, 841, 722, 684, 1429]` | `2.4187`* / `3.4684`* | `SATISFIED` / **`VIOLATED`** (`C7_LAT_ACCEL`) |
| `scene_03_close_urban_lead_following` (`7a524614561c54ef`) | `13.0503` | `+0.0945` | `0.10` | `keep forward` (`+0.01 m`) | `mps` / `42,275.1` | `[11, 11, 709, 128, 11, 709, 128, 1151, 177, 207]` | `1.0267` / `2.2656` | `SATISFIED` / `SATISFIED` |
| `scene_04_fast_arterial_lead_vehicle` (`c48640204ad758c4`) | `6.2117` | `-0.0713` | `0.07` | `keep forward` (`+0.04 m`) | `mps` / `60,673.0` | `[147, 88, 72, 913, 113, 145, 456, 185, 129, 30]` | `0.5361` / `2.0858` | `SATISFIED` / `SATISFIED` |
| `scene_05_active_braking_deceleration` (`b49c80be2d0d5bb9`) | `4.3103` | `-1.5525` | `1.56` | `keep forward` (`+0.08 m`) | `mps` / `37,860.6` | `[30, 189, 66, 145, 626, 147, 88, 1497, 1172, 42]` | `6.2543` / `12.8998` | **`VIOLATED`** (`C10_ACCEL_CONSISTENCY`) / **`VIOLATED`** |
| `scene_06_intersection_turn_maneuver` (`c9d4d04945e85ef8`) | `8.7828` | `-0.4007` | `1.41` | `turn left`* (`+4.09 m`) | `mps` / `69,041.2` | `[773, 1466, 1898, 115, 1898, 39, 115, 1108, 672, 646]` | `0.6595`* / `1.8800`* | `SATISFIED` / `SATISFIED` |
| `scene_07_stationary_ego_baseline` (`e9138a74627452c2`) | `0.0019` | `-0.0165` | `0.02` | `keep forward` (`-0.00 m`) | `mps` / `59,416.7` | `[28, 41, 70, 102, 12, 22, 3, 1629, 501, 367]` | `3.9304` / `10.1016` | **`INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE`** |

*\*Note on `scene_02` and `scene_06` (`EXT-VLA-C06`): The `"turn left"` command reflects future ground-truth lateral displacement ($y_{\text{GT}}(3.0\text{ s}) > 4.0\text{ m}$); see Section 3 for the future-information leakage boundary.*

---

## 3. Data Provenance Audit & Methodological Leakage Boundaries ([`provenance_audit.py`](./provenance_audit.py))

### Programmatic 11-Point Provenance Gate

[`provenance_audit.py`](./provenance_audit.py) is enforced inside [`experiment_runner.py`](./experiment_runner.py) and [`report_generator.py`](./report_generator.py), raising `ProvenanceMismatchError` on any discrepancy across:
1. Dataset log & `frame_token` identity
2. [`data/scenes_manifest.json`](./data/scenes_manifest.json) SHA-256 integrity (`8b8d77f168cda99ac724d995cae123dfaaf265849e2a4c31871eb8dfd7a963fc`)
3. Multi-view camera observation alignment (`12` camera frames per scene verified against [`data/camera_images_sha256.json`](./data/camera_images_sha256.json) and against live JPEGs whenever present on disk)
4. Ego-state kinematics ($v_x, v_y, v_0, a_x, a_y, \|a_0\|$, prompt substring alignment, and driving-command leakage audit)
5. Checkpoint & [`data/agent_vocab.pkl`](./data/agent_vocab.pkl) SHA-256 identity (`631c082f684160e98e965b73942a21b9d9fdca02d0d4e5525008f3d237e9e4c5`)
6. Exact regex extraction of `<action_k>` tokens from raw `output_text`
7. Exact SE(2) cumulative rollout reconstruction (`max_diff == 0.0` against `agent_vocab.pkl`)
8. Ground-truth 10-step horizon alignment ($\Delta t = 0.5\text{ s}$)
9. Independent ADE and FDE Euclidean recomputation (`atol = 1e-6 m`)
10. Prediction JSON SHA-256 identity ([`artifacts/predictions/scene_01..07_fast.json`](./artifacts/predictions))
11. Cross-check between [`artifacts/evaluation_summary.json`](./artifacts/evaluation_summary.json) and embedded data in [`artifacts/report/index.html`](./artifacts/report/index.html)

*(Historical note: Early pre-extraction candidate exploration logs printed unextracted candidate speeds such as `14.37 m/s` and `0.00 m/s`; all committed on-disk artifacts come from a single canonical extraction where `scene_01` has $v_0 = 13.5806\text{ m/s}$, $\text{FDE} = 0.7638\text{ m}$ and `scene_02` has $v_0 = 6.9470\text{ m/s}$, $\text{FDE} = 3.4684\text{ m}$.)*

### Methodological Limitation: Driving-Command Conditioning & Future-Displacement Leakage (`EXT-VLA-C06`)

A critical methodological boundary applies to driving-command conditioning in trajectory-prediction evaluation:

1. **`scene_02_stationary_lead_obstacle` (`frame_token = 3cacb287d398542f`):**
   - At $t_0 = 0.0\text{ s}$, the ego vehicle approaches a stationary in-lane vehicle at $d_0 = 55.486\text{ m}$, and over $t \in [0.5, 5.0]\text{ s}$ the logged human driver executes a left turn / lane departure ($y_{\text{GT}}(3.0\text{ s}) = +4.5128\text{ m}$, $y_{\text{GT}}(5.0\text{ s}) = +16.6678\text{ m}$).
   - When an unknown raw approach command is resolved into `"turn left"` from future ground-truth lateral displacement—or when conditioning on NAVSIM/OpenScene's `driving_command` (`[1, 0, 0, 0]`, `"turn left"`), which is itself constructed in upstream dataset preprocessing from future ego displacement—this introduces **future-information leakage** regarding the driver's subsequent lateral maneuver.
   - To preserve strict provenance integrity, the recorded inference input (`driving_command = "turn left"`) is not silently altered; instead, `provenance_audit.py` explicitly sets `future_displacement_command_leakage_flag = True` on `scene_02`, and its `ADE = 2.4187 m` / `FDE = 3.4684 m` are bounded as **command-conditioned** rather than leakage-free blind predictions.
2. **Other Scenes with Similar Command-Conditioning Limitations:**
   - **`scene_06_intersection_turn_maneuver` (`frame_token = c9d4d04945e85ef8`):** Also uses `driving_command = "turn left"` (`[1, 0, 0, 0]`), corresponding to future lateral displacement $y_{\text{GT}}(3.0\text{ s}) = +4.0889\text{ m}$ and $y_{\text{GT}}(5.0\text{ s}) = +8.3498\text{ m}$. Flagged with `future_displacement_command_leakage_flag = True` (`ADE = 0.6595 m`, `FDE = 1.8800 m` are command-conditioned, not leakage-free).
   - **All 7 scenes (`scene_01`–`scene_07`) at the benchmark protocol level:** Because NAVSIM/OpenScene `driving_command` labels (`keep forward` in `scene_01, 03, 04, 05, 07`; `turn left` in `scene_02, 06`) are derived from logged route/trajectory progression rather than an independent pre-trip navigation log, open-loop ADE/FDE values across the extension evaluate **command-conditioned trajectory generation**, not unconditioned intent prediction.

---

## 4. Scene 05 Active-Braking Finding & Controlled Signed-Acceleration Ablation

### Verified Step-Wise Kinematics in `scene_05_active_braking_deceleration`

- **Observed Initial State ($t_0 = 0.0\text{ s}$):** $v_0 = 4.3103\text{ m/s}$, $a_x(0) = -1.5525\text{ m/s}^2$, $a_y(0) = +0.1831\text{ m/s}^2$, Euclidean norm $\|a(0)\| = 1.5633\text{ m/s}^2$.
- **Baseline Unsigned Prompt (`"the ego acceleration is 1.56 m/s^2"`):**
  - **Step 1 ($t = 0.5\text{ s}$, `<action_30>`):** Implied speed drops from $4.3103\text{ m/s}$ to $3.8685\text{ m/s}$, giving $a_{\text{lon},1} = -0.8841\text{ m/s}^2$ (mild initial braking inferred from visual cues).
  - **Step 2 ($t = 1.0\text{ s}$, `<action_189>`):** Implied speed reverses upward to $4.2644\text{ m/s}$, giving $a_{\text{lon},2} = +0.7917\text{ m/s}^2$.
  - **Step 3 ($t = 1.5\text{ s}$, `<action_66>`):** Implied speed surges to $5.0365\text{ m/s}$, reaching peak positive longitudinal acceleration $a_{\text{lon},3} = +1.5442\text{ m/s}^2$.
  - **Phase C Violation (`C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY`):** Over the initial $1.5\text{ s}$ window, $|a_{\text{lon},3} - a_x(0)| = |+1.5442 - (-1.5525)| = 3.0967\text{ m/s}^2 > 2.50\text{ m/s}^2$. Over the $5.0\text{ s}$ horizon, the baseline trajectory reaches $x_{10} = 28.534\text{ m}$ (`ADE = 6.2543 m`, `FDE = 12.8998 m`).

### Single-Variable Controlled Prompt Ablation ([`artifacts/ablation_scene_05_signed_accel.json`](./artifacts/ablation_scene_05_signed_accel.json))

Holding all 12 camera images, $v_0 = 4.31\text{ m/s}$, driving command `'keep forward'`, model weights, and deterministic greedy decoding identical, replacing `"1.56 m/s^2"` with signed longitudinal acceleration `"-1.55 m/s^2"` yields:

| Metric | Baseline Unsigned Prompt (`1.56 m/s^2`) | Controlled Signed Ablation (`-1.55 m/s^2`) | Delta / Effect |
| :--- | :--- | :--- | :--- |
| **Generated `<action_k>` Tokens** | `[30, 189, 66, 145, 626, 147, 88, 1497, 1172, 42]` | `[30, 71, 187, 12, 16, 1, 28, 0, 126, 0]` | Token sequence shifts at Step 2 (`71` vs `189`) |
| **Step 1 / Step 2 / Step 3 $a_{\text{lon}}$ ($\text{m/s}^2$)** | `-0.8841` / `+0.7917` / **`+1.5442`** | `-0.8841` / **`-0.9854`** / **`-1.0846`** | Eliminates acceleration sign reversal; sustains braking |
| **Braking Phase ADE ($0.0\text{--}2.0\text{ s}$)** | `1.2131 m` | **`0.1448 m`** | **`-88.1%` error during active braking** |
| **Full 5.0 s Horizon ADE / FDE** | `6.2543 m` / `12.8998 m` | **`2.4210 m`** / **`8.7228 m`** | **`-61.3%` ADE / `-32.4%` FDE** |
| **Final Longitudinal Position $x_{10}$ ($t = 5.0\text{ s}$)** | `28.5340 m` | `6.9255 m` (brakes to standstill by $t = 3.5\text{ s}$) | Matches stopping phase (`x_GT(2.5s) = 6.92 m`) |

### Bounded Causal Conclusion & Single-Scene OOD Limitations

1. **Observed Input-Representation Limitation vs. Single-Factor Causal Law:** AutoVLA's prompt design (`np.linalg.norm(acceleration)`) discards the sign of longitudinal acceleration (`-1.5525 m/s^2` $\to$ `1.56 m/s^2`). Because Step 1 (`t = 0.5 s`) still decelerates at `-0.8841 m/s^2` under the unsigned prompt from visual context before reversing at Steps 2–3, unsigned acceleration encoding is a **strong contributing factor** rather than a single-cause deterministic law.
2. **Single-Scene Out-of-Distribution (OOD) Diagnostic Limitation:** AutoVLA was trained exclusively on non-negative acceleration norms ($\|a\| \ge 0$). Passing `"-1.55 m/s^2"` is a **post-hoc, single-scene out-of-distribution prompt intervention**, not a validated model improvement. At Step 9 (`t = 4.5 s`), after coming to rest (`<action_0>` at Step 8), the OOD prompt emits a `5.8 cm` backward jitter token (`<action_126>`, `dx = -0.058 m`) before returning to `<action_0>` at Step 10, while the human driver releases the brake after $t = 2.5\text{ s}$ and accelerates to $15.65\text{ m}$. Retraining with signed `(a_lon, a_lat)` inputs plus an independent physical verifier (`Phase C`) is required.

---

## 5. RQ1 — Controlled Driving-Command Sensitivity (`EXT-VLA-C07`, [`command_sensitivity.py`](./command_sensitivity.py))

To quantify how strongly AutoVLA depends on the supplied high-level driving command in the two scenes subject to the `EXT-VLA-C06` command-leakage boundary (`scene_02_stationary_lead_obstacle` and `scene_06_intersection_turn_maneuver`), [`command_sensitivity.py`](./command_sensitivity.py) executes a controlled single-variable prompt intervention replacing `"turn left"` with `"keep forward"` while holding all 12 camera frames, initial speed/acceleration, model weights, `agent_vocab.pkl`, and greedy decoding (`do_sample=False`) identical.

- **Canonical Immutability:** All 7 canonical prediction files in [`artifacts/predictions/`](./artifacts/predictions) remain byte-for-byte unchanged (`verify_canonical_predictions_unchanged()`); the 2 intervention artifacts are saved separately in [`artifacts/command_sensitivity/scene_02_keep_forward.json`](./artifacts/command_sensitivity/scene_02_keep_forward.json) and [`artifacts/command_sensitivity/scene_06_keep_forward.json`](./artifacts/command_sensitivity/scene_06_keep_forward.json) alongside [`comparison.csv`](./artifacts/command_sensitivity/comparison.csv) and [`summary.json`](./artifacts/command_sensitivity/summary.json).
- **Critical Interpretation Rule:** In both scenes, the logged human trajectory is a left-turn maneuver ($y_{\text{GT}}(5.0\text{ s}) = +16.6678\text{ m}$ in `scene_02`; $+8.3498\text{ m}$ in `scene_06`) and is **not** a valid ground-truth target for a deliberately different `"keep forward"` command. Open-loop ADE/FDE differences under `"keep forward"` quantify **command sensitivity relative to the recorded turning trajectory**, not policy quality or driving safety.

| Scene ID (`frame_token`) | Command Condition | Action Tokens `<action_k>` (Steps 1–10) | Tokens Changed (First Step) | Final 5.0 s Pose $(x_{10}, y_{10}, \psi_{10})$ | $\Delta y(5\text{ s})$ / Mean–Max L2 Div. | ADE / FDE vs Logged Turn GT ($\text{m}$)\* | Nominal / Wet ($\mu=0.5$) Feasibility | 1D Corridor Exit / Admissible R3B Steps |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `scene_02` (`3cacb287d398542f`) | Control: `turn left` | `[418, 728, 418, 728, 1506, 724, 841, 722, 684, 1429]` | — | `(29.28 m, +19.82 m, +63.41°)` | — | `2.4187` / `3.4684` | `SATISFIED` / **`VIOLATED` (`C7`)** | Exits at `1.5 s` / **`3/7` (`0.0–1.0 s`)** |
| `scene_02` (`3cacb287d398542f`) | Intervention: `keep forward` | `[1172, 42, 598, 1506, 1806, 1074, 1257, 522, 1475, 1814]` | **`10 / 10` (Step 1)** | `(32.11 m, +13.06 m, +55.33°)` | **`-6.75 m` (`-34.1%`)** / `3.77`–`7.32 m` | `1.5385` / `3.8597` | `SATISFIED` / **`VIOLATED` (`C7`)** | Exits at `3.0 s` / **`6/7` (`0.0–2.5 s`)** |
| `scene_06` (`c9d4d04945e85ef8`) | Control: `turn left` | `[773, 1466, 1898, 115, 1898, 39, 115, 1108, 672, 646]` | — | `(43.53 m, +7.60 m, +12.18°)` | — | `0.6595` / `1.8800` | `SATISFIED` / `SATISFIED` | Exits at `2.0 s` / Obs `0/7`, CF `4/7` |
| `scene_06` (`c9d4d04945e85ef8`) | Intervention: `keep forward` | `[1205, 1937, 1898, 13, 534, 39, 39, 1188, 120, 5]` | **`8 / 10` (Step 1)** | `(43.60 m, +5.04 m, +10.21°)` | **`-2.55 m` (`-33.6%`)** / `1.41`–`2.56 m` | `1.7793` / `3.6976` | `SATISFIED` / `SATISFIED` | Exits at `2.5 s` / Obs `0/7`, CF `5/7` |

---

## 6. RQ2 — Scene 05 `C10` Numerical Robustness Audit (`EXT-VLA-C08`, [`c10_robustness.py`](./c10_robustness.py))

To test whether the `scene_05_active_braking_deceleration` `C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY` violation is an artifact of a single finite-difference formula, [`c10_robustness.py`](./c10_robustness.py) evaluates a 75-cell parameter grid (**5 discrete derivative estimators $\times$ 5 temporal windows $\times$ 3 illustrative diagnostic thresholds** $\in \{2.0, 2.5, 3.0\}\text{ m/s}^2$) on both the canonical unsigned rollout (`1.56 m/s^2`) and the saved OOD signed-acceleration rollout (`-1.55 m/s^2`), outputting [`artifacts/c10_robustness/c10_robustness_matrix.csv`](./artifacts/c10_robustness/c10_robustness_matrix.csv) and [`artifacts/c10_robustness/c10_robustness_summary.json`](./artifacts/c10_robustness/c10_robustness_summary.json).

- **Overall Classification:** `SENSITIVE_TO_TEMPORAL_WINDOW_AND_SMOOTHED_THRESHOLD_ROBUST_FOR_WINDOWS_GE_1P5S_AT_LE_2P5MPS2`
- **Multi-Step Post-Reversal Robustness (`30/30` cells violated):** Across all 5 estimators (`E1` chord-speed backward difference, `E2` pure ego-$x$ Taylor/central second difference, `E3` body-frame projected velocity difference, `E4` $1.0\text{ s}$ central velocity difference, and `E5` 3-step moving average) and all windows covering the braking-to-acceleration reversal (`W3: 0.0–1.5 s`, `W4: 0.0–2.0 s`, `W5: 0.0–5.0 s`), the C10 violation holds in **30 / 30 cells** at both the `2.0 m/s^2` and canonical `2.5 m/s^2` thresholds (`peak |a_lon - a_x(0)| = 3.0967 m/s^2` on `E1/E2/E3`, `2.8516 m/s^2` on `E4`, and `2.6825 m/s^2` on `E5`), driven by **9 consecutive positive-acceleration steps** ($t = 1.0..5.0\text{ s}$, accelerating the ego vehicle from $3.87\text{ m/s}$ to $7.05\text{ m/s}$).
- **Where Binary C10 Classification Is Sensitive (`45/75` total cells violated):**
  1. *Early temporal windows ($t \le 1.0\text{ s}$):* `W1 (0.0–0.5 s)` passes `15/15` cells (`0/15` violations) because Step 1 still decelerates (`-0.8841 m/s^2` on `E1`, `-1.7658 m/s^2` on `E2`). `W2 (0.0–1.0 s)` violates the `2.0 m/s^2` threshold (`2.3442 m/s^2` on `E1/E2/E3`, `2.7200 m/s^2` on `E4`) but passes `2.5` and `3.0 m/s^2` on unsmoothed `E1/E2/E3`.
  2. *Smoothed estimators at the `3.0 m/s^2` threshold:* At `3.0 m/s^2`, unsmoothed estimators `E1/E2/E3` still violate (`3.0967 > 3.0 m/s^2`), whereas multi-step smoothing (`E4` central difference and `E5` 3-step moving average) damps the Step 3 peak to `2.8516` and `2.6825 m/s^2` (`< 3.0 m/s^2`).
- **D4 Sanity Checks & D5 Signed-Rollout Comparison:** Heading remains within $\pm 0.085^\circ$ over $[0, 1.5]\text{ s}$, producing `< 0.01301 m/s^2` (`< 0.42%`) discrepancy between chord-speed (`E1`) and pure ego-$x$ (`E2`) across Steps 2–10 (`0.00000 m/s^2` at the Step 3 peak) and `< 0.00120 m/s^2` (`< 0.04%`) between `E1` and body-frame `E3`. In contrast, the saved signed-acceleration OOD rollout (`-1.55 m/s^2`) records **0 / 75 active-motion C10 violations** (`max jump <= 0.6684 m/s^2`). *(Disclaimer: Thresholds `{2.0, 2.5, 3.0} m/s^2` are illustrative diagnostic bounds for sensitivity analysis, not externally validated safety standards.)*

---

## 7. Interactive R3B Human Takeover Feasibility Simulator & AutoVLA Trajectory Explorer ([`interactive_explorer.py`](./interactive_explorer.py))

To upgrade the extension from a static report into an interactive, reproducible engineering demonstrator, [`interactive_explorer.py`](./interactive_explorer.py) and [`report_generator.py`](./report_generator.py) integrate two live capabilities directly into the top of the HTML dashboard (`#interactive-demonstrator-workspace`):

### Capability 1 — Interactive AutoVLA Trajectory & Step-Aware Physics Explorer (`#interactive-trajectory-explorer`)
- **10 Saved Rollouts Across 7 Real Driving Scenes:** Supports interactive selection of all `7` canonical AutoVLA rollouts (`scene_01`–`scene_07`), the `2` controlled RQ1 command-sensitivity interventions (`scene_02` and `scene_06` `cmd='keep forward'`), and the `1` controlled Scene 05 signed-acceleration OOD diagnostic rollout (`-1.55 m/s^2`).
- **Step-by-Step Playback & Scrubber:** Play/Pause animation, Step `-0.5 s` / `+0.5 s` buttons, and timeline scrubber across `t = 0.0 s` (observed initial state $t_0$) and `10` discrete prediction steps $k \in \{1..10\}$ ($t \in \{0.5..5.0\}\text{ s}$), plus an optional `0.1 s` display interpolation toggle explicitly badged as `DISPLAY INTERPOLATION (0.1 s)` rather than a recorded model output.
- **Synchronized Bird's-Eye View (BEV) & Step Kinematics SVGs:** Plots ego-local `+x` forward / `+y` left trajectories, heading arrows, the $\pm 1.75\text{ m}$ R3B 1D longitudinal corridor, observed 3D lead obstacles or assumed counterfactual $d_0$ lines, logged human ground-truth trajectories, and command/ablation counterparts alongside step-indexed speed $v(t)$ and acceleration $a_{\text{lon}}(t), |a_{\text{tot}}(t)|$.
- **Strict Separation of `TIME_LOCAL_STEP` vs. `TRAJECTORY_WIDE` C1–C10 Checks:** At $t = 0.0\text{ s}$ (Step 0), finite-difference interval checks `C2`–`C10` are explicitly marked `NOT_DEFINED_AT_T0` (`evaluation_scope = TIME_LOCAL_STEP`) while `C1_TIMESTAMP_AND_HORIZON_CONTINUITY` is labeled `TRAJECTORY_WIDE_PASS` (`evaluation_scope = TRAJECTORY_WIDE`). At steps $k = 1..10$, each time-local check (`C2`–`C10`) is evaluated at step $k$ alongside its full-horizon summary.

### Capability 2 — Coupled & Standalone R3B Human Takeover Simulator (`#interactive-r3b-simulator`)
- **Exact Analytical R3B Engine:** Reuses `stopping_distance_r3b_analytical` and `braking_t_required` ([`src/metrics/oracle.py`](../../src/metrics/oracle.py)), `t_required`, `classify`, `PARAMETERS`, `BRANCHES`, `SUCCESS` ([`src/experiments/r3b_braking_bounds.py`](../../src/experiments/r3b_braking_bounds.py)), and `effective_braking_deceleration` ([`src/vehicle/models.py`](../../src/vehicle/models.py)) with zero textbook approximations.
- **Live Controls & Dual Speed Units (`m/s` $\leftrightarrow$ `km/h`):** Supports **Connected AutoVLA Trajectory Mode** (synchronized with the active scene, rollout condition, and scrubbed takeover request time $\tau_{\text{req}} \in [0.0, 3.0]\text{ s}$) and **Standalone R3B Parametric Mode** with interactive controls for vehicle speed (`m/s` or `km/h`), obstacle source (`Observed 3D Lead` vs. `Assumed Counterfactual d0`), policy branch (`P0`, `P1`, `P2`), road friction $\mu$ (`Dry 1.0`, `Wet 0.7`, `Rain 0.5`, `Snow 0.35`), human reaction delay $t_1 \in [1.15, 3.00]\text{ s}$, hydraulic delay $t_2$, ramp build-up $t_3$, max deceleration $a_{\max}$, and P2 supported deceleration $a_{\text{sup}}$.
- **Three-Layer Provenance Architecture & Non-Safety Presentation Mapping (Never `"SAFE"`):**
  - **Layer 1 — Observed / Recorded Evidence:** Scene token, logged ego $t_0$ kinematics, observed 3D in-lane annotation, and AutoVLA pose at $\tau_{\text{req}}$.
  - **Layer 2 — Assumed Counterfactual & Model Inputs:** Assumed obstacle distance $d_0$ (if counterfactual), exogenous takeover delay $\tau_{\text{req}}$, surface $\mu$, policy branch `P0`/`P1`/`P2`, and human/brake parameters.
  - **Layer 3 — Derived R3B Model Conclusions:** 4-phase stopping distance breakdown ($d_{\text{pre}}, d_{\text{delay}}, d_{\text{brake}}, +2.0\text{ m}$ standstill margin), available vs. required stopping distance/time, point margin, frozen R3B parameter-box interval, and causal explanation mapped strictly to five non-safety labels:

| Presentation Status Label | Underlying R3B / Verifier Classification | Technical Meaning |
| :--- | :--- | :--- |
| `NECESSARY_CONDITION_SATISFIED` | `ROBUSTLY SATISFIED` / `UNIFORMLY_POSITIVE` ($\Delta D \ge 0$) | Available 1D stopping distance/time meets or exceeds required stopping distance/time (including $+2.0\text{ m}$ standstill margin). Necessary condition only; **never** a guarantee of real-world safety. |
| `NECESSARY_CONDITION_VIOLATED` | `ROBUSTLY UNSATISFIED` / `UNIFORMLY_VIOLATED` ($\Delta D < 0$) | Required 1D stopping distance/time exceeds available obstacle distance/time under the selected assumptions. |
| `PARAMETER_SENSITIVE` | `PARAMETER-SENSITIVE` / `PARAMETER_SENSITIVE` | Optimistic R3B parameter-box corner satisfies the bound while conservative corner violates it ($\min \Delta T < 0 < \max \Delta T$). |
| `NOT_APPLICABLE` | `INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE` (Corridor Exit / Stationary) | State lies outside the validated 1D R3B domain ($v \le 0.05\text{ m/s}$, $|y| > 1.75\text{ m}$, $|\psi| > 0.35\text{ rad}$, $d_{\text{rem}} \le 0\text{ m}$, or $\tau_{\text{req}} > 3.0\text{ s}$). Numerical margins are withheld. |
| `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE` (No Obstacle Geometry) | No observed 3D in-lane obstacle exists in the dataset annotations and no counterfactual $d_0$ was supplied. |

---

## 8. Interactive English Dashboard, Screenshots & Landscape PDF Report

- **Interactive HTML Dashboard:** [`artifacts/report/index.html`](./artifacts/report/index.html)
- **Landscape PDF Export:** [`artifacts/report/vla_handover_feasibility_report.pdf`](./artifacts/report/vla_handover_feasibility_report.pdf)

### Dashboard Screenshots

![Screenshot 07: Interactive AutoVLA Trajectory Explorer and Coupled R3B Human Takeover Simulator](./artifacts/report/screenshots/07_interactive_r3b_and_trajectory_explorer.png)
*Screenshot 07: Interactive Demonstrator Workspace showing Capability 1 (AutoVLA Trajectory & Step-Aware C1–C10 Physics Explorer on Scene 02 `keep forward` vs `turn left` at $t = 1.5\text{ s}$) coupled live to Capability 2 (4-Phase R3B Human Takeover Feasibility Simulator across `P0`/`P1`/`P2` with 3-Layer Provenance and non-safety status mapping).*

![Screenshot 01: Executive Findings, Methodological Leakage Disclosure, and Overview](./artifacts/report/screenshots/01_executive_findings_and_overview.png)
*Screenshot 01: Executive Research Summary (`EXT-VLA-C01`–`EXT-VLA-C08`), driving-command leakage disclosure banner, interactive control bar, and Scene 01 overview.*

![Screenshot 02: Scene 05 Active-Braking Violation and Controlled Signed-Acceleration Ablation](./artifacts/report/screenshots/02_scene_05_braking_violation_and_ablation.png)
*Screenshot 02: Scene 05 `C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY` violation (`+1.5442 m/s^2` vs `-1.5525 m/s^2`) and single-variable signed-acceleration prompt ablation (`-1.55 m/s^2`) with OOD causal boundary notices.*

![Screenshot 03: Scene 03 Urban Lead-Following R3B Counterfactual Handover Analysis](./artifacts/report/screenshots/03_scene_03_urban_lead_r3b_handover.png)
*Screenshot 03: Scene 03 R3B braking-only stopping distance ($[m]$) and time ($[s]$) margins across takeover request times $\tau_{\text{req}} \in [0.0, 3.0]\text{ s}$ and policies `P0`, `P1`, and `P2`.*

![Screenshot 04: Scene 01 Counterfactual Obstacle Provenance Badge Verification](./artifacts/report/screenshots/04_scene_01_counterfactual_d0_provenance.png)
*Screenshot 04: Scene 01 counterfactual $d_0 = 45.00\text{ m}$ schedule explicitly badged as `Observed Ego (t0) + Assumed Obstacle (d0)` at $\tau_{\text{req}} = 0.0\text{ s}$ and `Hypothetical VLA + Assumed Obstacle (d0)` at $\tau_{\text{req}} > 0$.*

![Screenshot 05: RQ1 Controlled Driving-Command Sensitivity (Scenes 02 & 06)](./artifacts/report/screenshots/05_scene_02_06_command_sensitivity.png)
*Screenshot 05: RQ1 Controlled Driving-Command Sensitivity (`turn left` $\to$ `keep forward`, `EXT-VLA-C07`) on Scenes 02 and 06 with token-level divergence and R3B corridor admissibility impact.*

![Screenshot 06: RQ2 Scene 05 C10 Numerical Robustness Matrix](./artifacts/report/screenshots/06_scene_05_c10_robustness_matrix.png)
*Screenshot 06: RQ2 Scene 05 `C10` Numerical Robustness Audit (`EXT-VLA-C08`) across 5 discrete derivative estimators (`E1`–`E5`), 5 temporal windows, and 3 diagnostic thresholds.*

---

## 9. Licensing, Data Redistribution Policy & Reproducible Commands

### Licensing & External Data Availability

- **Extension Source Code & Evaluation Pipeline:** Licensed under the [MIT License](../../LICENSE).
- **AutoVLA Action Codebook ([`data/agent_vocab.pkl`](./data/agent_vocab.pkl)):** From [`ucla-mobility/AutoVLA`](https://github.com/ucla-mobility/AutoVLA) (MIT / Apache-2.0 compatible).
- **Raw Camera Sensor JPEGs Excluded from Git Redistribution:** The 84 multi-view camera history JPEGs (`data/scenes/*/images/*.jpg`) derive from the Motional nuPlan / OpenDriveLab OpenScene dataset (CC BY-NC-SA 4.0) and are **excluded from public Git redistribution via [`.gitignore`](../../.gitignore)**. Instead, [`data/camera_images_sha256.json`](./data/camera_images_sha256.json) records the cryptographic SHA-256 digests and byte sizes of all 84 frames so that the entire offline evaluation, provenance audit, dashboard generation, and `pytest` suite run immediately from a clean Git clone without downloading the 1.7 GB external sensor archive.
- **AutoVLA Model Checkpoint (`AutoVLA_PDMS_89.ckpt`):** Not bundled in Git (8.14 GB `bfloat16` / 16.29 GB raw); downloaded on demand from Hugging Face ([`Zewei-Zhou/AutoVLA`](https://huggingface.co/Zewei-Zhou/AutoVLA)) when running live inference.

### Reproducible CLI Workflow

```bash
# 0. One-Command Offline Demo (recomputes evaluation, RQ1/RQ2 audits, verifies provenance, and opens HTML dashboard):
.venv/bin/python -m extensions.vla_handover_feasibility.demo

# 1. Offline Provenance & Consistency Audit (runs out-of-the-box without external raw JPEGs):
.venv/bin/python -m extensions.vla_handover_feasibility.provenance_audit

# 2. Offline Re-evaluation of Saved Genuine AutoVLA Predictions (~1 second):
.venv/bin/python -m extensions.vla_handover_feasibility.experiment_runner --skip-inference

# 3. Offline Re-evaluation of RQ1 Controlled Command Sensitivity & RQ2 Scene 05 C10 Robustness:
.venv/bin/python -m extensions.vla_handover_feasibility.command_sensitivity --skip-inference
.venv/bin/python -m extensions.vla_handover_feasibility.c10_robustness

# 4. Regenerate the Self-Contained Interactive English HTML Dashboard:
.venv/bin/python -m extensions.vla_handover_feasibility.report_generator

# 5. Run the 21-Test Extension Verification Suite:
.venv/bin/pytest extensions/vla_handover_feasibility/tests -v

# 6. Optional: Stream & Verify the 84 Raw Camera JPEGs from OpenDriveLab/OpenScene for Live Inference:
.venv/bin/python -m extensions.vla_handover_feasibility.extract_navsim_scenes

# 7. Optional: Run Live Sequential (batch_size=1) AutoVLA Inference on Apple MPS / CUDA GPU:
.venv/bin/python -m extensions.vla_handover_feasibility.experiment_runner --scene-id scene_03_close_urban_lead_following
```

### Test & Baseline Regression Summary

- **Extension Test Suite ([`artifacts/extension_pytest_output.txt`](./artifacts/extension_pytest_output.txt)):** **`21 passed`** (`test_vla_handover_extension.py`).
- **Original Repository Test Suite ([`artifacts/baseline_pytest_output.txt`](./artifacts/baseline_pytest_output.txt)):** **`430 passed, 1 skipped, 1 deselected, 4 failed`** when audited against squashed pre-release git history (`all 27 R3B tests in tests/test_r3b.py and tests/test_r6a_figures.py::test_scientific_results_unchanged passing`):
  1. `tests/test_r2a.py::test_r2a_provenance`, `tests/test_r2b.py::test_r2b_provenance`, and `tests/test_r2c_lite.py::test_r2c_provenance` failed with `git diff` exit code `128` (`fatal: bad object 9d1c41d01a5a141f07020610c58879b76b214d11`) prior to the `tests/provenance_dependencies.py` content-hash verifier on `main`.
  2. `tests/test_r6a_figures.py::test_deterministic_rendering` fails on `FA2_participant_exposure_slopes.pdf` byte-level SHA-256 comparison due to Matplotlib / Python `3.14` PDF font stream metadata differences against the frozen PDF generated during release.
