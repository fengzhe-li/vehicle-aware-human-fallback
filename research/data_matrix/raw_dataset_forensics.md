# Raw Dataset Forensics — Phase 0.3

**Method:** actual data files were downloaded and parsed (not README claims). GitHub's REST API (`api.github.com/repos/.../contents/...`) was used to enumerate real committed file trees; `curl` with HTTP `Range` requests plus `pandas`/`json` were used to fetch and parse byte-limited chunks of large files without downloading entire multi-GB datasets. Where a claim below is README-only (not independently verified against bytes), it is labeled as such.

---

## OpenLKA Acceleration Dataset (D005)

**What was actually fetched:** the full `HYUNDAI_IONIQ_5_segments.json` (19,971,504 bytes, HTTP 200, committed directly in the GitHub repo root — no gating, no external host needed).

**Real structure (not documented anywhere in the README):**
- Top level: a JSON object keyed by **3** route/driver hash IDs for this vehicle model (`bdda168c0c35fad7`, `149d6f706527cfe1`, `530075d26cad58e4`) — far sparser per-model coverage than the aggregate "25 drivers / 12 models" headline suggests. (One of these hashes, `bdda168c0c35fad7`, also appears in the EV Dataset's directory tree — see below — confirming the two OpenLKA sibling repos share underlying driver/route identifiers.)
- Each hash maps to a list of 22 "groups" (purpose not documented; plausibly acceleration-magnitude or session bins — not confirmed).
- Each group is a list of **segment** dicts with keys: `start_idx`, `end_idx`, `duration`, `v` (velocity, m/s), `a` (acceleration, m/s²), `t` (time, s, **not zero-based** — starts mid-trip), `padel` (**note the misspelling — this is the actual field name in the data**, accelerator pedal position, normalized ~0-1), `v_range`, `max_padel`, `free_flow` (boolean quality flag).

**Sampling rate — measured directly, not assumed:** consecutive `t` differences were computed across 6+ segments spanning multiple groups. Every one clustered at **Δt ≈ 0.10s (≈10 Hz)**, e.g. `[0.1031, 0.0981, 0.100, 0.1008, 0.1002]`. **This directly contradicts the README's claim of "100 Hz CAN bus data."** The distributed `segments.json` files are effectively 10 Hz, whatever the underlying CAN bus rate was before this derived/resampled artifact was produced. This is a load-bearing, reportable negative finding: it rules out resolving `t_delay` (0.05-0.17s per Paquette & Porter) from this dataset — 10 Hz sampling (100ms period) cannot resolve a sub-100ms transient; it would alias into 0-1 samples.

**Content, not just schema:** the sampled segment (`v` rising 7.7→20.1 m/s, `a` positive 0.3-0.7 m/s² throughout, `padel` rising 0.31→0.47) is an **acceleration** event, consistent with the repo's name and purpose. **No `brake` field exists anywhere in this schema.** There is no regen-level field, no brake-pedal field, and no jerk field (jerk is derivable from `a` and `t`, not provided). **Correction to Phase 0.2:** this dataset cannot inform braking/regen-deceleration parameters at all — its only relevance is to the risk-state-escalation (Phase 1B, acceleration authority) branch, not to Experiment A's braking-response mechanism. Citing D005 for `a_coast` or regen magnitude (as Phase 0.1/0.2 implicitly allowed via cross-reference) was not correct; the only dataset with any regen-relevant field is the EV Dataset (D004).

---

## OpenLKA Electric Vehicle Kinematic Dataset (D004)

**What was actually fetched:** two byte-range chunks (~8MB from the start, ~2MB from mid-file) of `Hyundai_IONIQ_5/bdda168c0c35fad7/2024-06-05--16-17-00/data.csv`, a real 88,616,080-byte (88.6MB) file, confirmed to exist via the GitHub Contents API (not README-only). Combined, ~2,260 real rows across two non-contiguous windows of one real driving session were parsed with `pandas`.

**Exact schema (90 columns, all confirmed by direct parse):**
`unix_time, op_enable, op_long_enable, op_lat_enable, acc_enable, acc_set_speed, long_plan_source, plan_accel` (an **array-per-row** field — a full planned-acceleration trajectory, not a scalar), `has_lead, act_ctrl_gas, act_ctrl_brake, act_ctrl_accel, body_pitch_angle, body_roll_angle, body_yaw_angle, body_roll, aEgo, vEgo, vLead1, vLead2, lead1_spacing, lead2_spacing, vision_vLead, vision_dist, uPAccelCmd, uIAccelCmd, uFAccelCmd, uPTorque, uITorque, uFTorque, latOutput, aTarget, state_gas_pressed, state_gas_pos, state_regen_break_enable`, [lane-keeping/steering fields], `a_req_raw, a_req_value, jerk_upper_limit, jerk_lower_limit`, [steering-torque fields], `brake, brake_padel_status` (**note: same "padel" misspelling as D005 — confirms shared codebase/tooling between the two OpenLKA repos**), `wallTimeCentiseconds, easternTime, Time`.

**This is a materially richer schema than ADAS-TO's** — it includes `state_gas_pos`, a genuinely **continuous** accelerator-pedal-position field (confirmed: 26 distinct values in the sampled window, range 0.0-0.235), which ADAS-TO does not expose. It also has fields (`jerk_upper_limit`, `jerk_lower_limit`, `a_req_raw`, `a_req_value`) that ADAS-TO's documented schema does not mention.

**Sampling rate — measured, not assumed:** `wallTimeCentiseconds` spans ~14.16s over 1812 rows in the first chunk ⇒ ≈128 Hz average (many repeated centisecond stamps due to 10ms display resolution rounding, consistent with an underlying ≥100Hz source, not contradicting it). **This dataset's ~100Hz-class rate is empirically supported, in contrast to D005's confirmed 10Hz** — the two "100 Hz" claims in the original READMEs cannot be treated as interchangeable; one holds up under inspection, one does not.

**The central finding, and its direct bearing on Task 1 (control ownership):** in **both** sampled windows (session start and session middle), `act_ctrl_gas`, `act_ctrl_brake`, `act_ctrl_accel`, `aTarget`, `brake`, `brake_padel_status`, and `state_regen_break_enable` were **constant at their inactive value (0 / False) for every single row** — while `aEgo` and `vEgo` showed continuous, real variation (genuine driving dynamics were occurring). Cross-checking explains why: `op_enable`, `op_long_enable`, and `op_lat_enable` were **`False` for the entire sampled span** — openpilot's own longitudinal/lateral control loop was not engaged during this portion of the trip (only the vehicle's stock ACC, `acc_enable`, toggled). **This means the automation-command fields (`act_ctrl_*`, `aTarget`) are populated only while the automation stack is actively in control** — exactly the `w_authority`/`u_automation` split formalised in `control_ownership_timeline.md`, now grounded in real telemetry rather than asserted from first principles.

**A genuine negative result, stated as such per the task's explicit instruction:** no braking or regen event was captured in either sampled window of this one session. This does **not** confirm regen deceleration magnitudes, and it does **not** refute them — it means this particular ~2,260-row sample of one session happened not to contain a hard-braking episode. Confirming the D004-README-documented "1-4 m/s² / 0.1-0.3g" regen range against raw files would require scanning many more sessions (or a targeted search within this file) specifically for `state_regen_break_enable = True` or a `brake` onset, which was not done in this pass — logged as unresolved, not silently assumed to be true.

**Structural note relevant to Task 6:** unlike D005, D004 ships **no pre-extracted event/episode index file** (no `segments.json` equivalent) — only raw per-session `data.csv` continuous logs. Episode extraction from D004 would need to be built from scratch (see `response_episode_definition.md`), scanning continuous signals for brake-onset events; D005's pre-extracted segments cannot substitute, since D005 has no brake channel at all.

---

## ADAS-TO (D001)

**What was actually fetched:** the underlying paper (arXiv:2603.06986, HTML) and the Hugging Face dataset page (`huggingface.co/datasets/HenryYHW/ADAS-TO`). Direct byte-level file inspection was **not achieved** — the dataset's actual per-clip CSVs are not committed to the GitHub repo (only template paths are documented there, consistent with the Phase 0.1 finding) and are hosted on Hugging Face Hub, where individual clip files were not accessible via the tools available in this pass (no dataset-viewer table content was returned, and the raw per-clip files are inside a gated, multi-GB archive, not individually browsable via `WebFetch`). **This is reported as a genuine access limitation, not papered over.**

**New findings from the paper/HF page that update Phase 0.1/0.2:**
- **Sampling rate is not uniformly 100Hz**: the paper states **61.7% of clips are logged at 10Hz ("qlog") and 38.3% at 100Hz ("rlog")**. This was not previously known. It means `t_delay` (0.05-0.17s) is unresolvable from roughly six in ten ADAS-TO clips outright (10Hz = 100ms period, at the edge of or coarser than the whole phenomenon being measured), and only the 100Hz minority subset could in principle resolve it — any future use of ADAS-TO for `t_delay` estimation must filter to the rlog subset explicitly, or the resulting distribution will be dominated by an artifact of sampling rate, not by real physical variation.
- **Access is gated, not open-download.** The Hugging Face page states the license is "CC BY-NC 4.0 for non-commercial research **requiring manual access approval**." This is a material correction to Phase 0.1's dataset_inventory.csv entry, which recorded "direct download via Hugging Face Hub (huggingface-cli / git-lfs)" without noting a gating step.
- **Scale figures disagree between sources**: the arXiv paper states 15,659 clips / 327 drivers / 163 car models / 87.0 video-hours; the Hugging Face page states 16,446 clips / 364 drivers / 179 vehicle models / ~43.6GB. This is most plausibly two different dataset snapshots (paper vs. live HF release), but the discrepancy is **not resolved** in this pass and should not be silently averaged or picked from one source without noting the other.
- **A dataset-internal jerk threshold exists**: the paper describes extracting "longitudinal jerk (≥5.0 m/s³)" as an operational criterion (apparently for flagging notable/urgent events), computed from acceleration, not stored as a raw field. This is the authors' own working threshold, not a peer-reviewed physiological or safety-derived constant — it should not be cited as if it were the latter, but it is a real, traceable data point (unlike the untraceable "5.3 m/s³" figure excluded in Phase 0.2).
- **749 manually-vetted safety-critical clips** exist as a curated subset within the dataset, per the HF page — a promising target for future episode extraction (`response_episode_definition.md`) once gated access is obtained, not inspected in this pass.

**Confirms Phase 0.2's field-level finding** (binary `gasPressed`/`brakePressed`, continuous `actuators.accel`/`actuatorsOutput.*`/`aTarget`) via the paper's own text ("brake pedal pressed," "gas pressed" referenced as boolean flags; continuous pedal position not stated) — no correction needed there.

---

## Summary table

| dataset | raw file access achieved | sampling rate (measured, not claimed) | brake/regen signal | gating |
|---|---|---|---|---|
| D005 Acceleration Dataset | YES — full file, 20MB, parsed | **~10Hz** (measured; README claimed 100Hz — contradicted) | NONE — accelerator-only dataset | none, direct GitHub |
| D004 EV Dataset | YES — 2 chunks, ~2,260 rows, parsed | **~100Hz-class** (measured; consistent with README) | Present as fields; **not populated with an actual event in either sampled window** | none, direct GitHub |
| D001 ADAS-TO | NO — schema-level only (paper + HF page) | **Mixed: 61.7% at 10Hz, 38.3% at 100Hz** (newly discovered; not in Phase 0.1 audit) | Binary flags only (confirmed) | **Gated — manual approval required** (correction to Phase 0.1) |
