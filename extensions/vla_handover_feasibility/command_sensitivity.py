"""Phase B & C: Controlled Driving-Command Sensitivity Experiment & Comparative Evaluation.

Investigates RQ1:
To what extent do AutoVLA trajectory predictions change when the supplied high-level
driving command changes (`turn left` -> `keep forward`), while all 12 camera-history
frames, ego kinematics, model weights, action codebook decoding, and deterministic
inference settings remain fixed?

Target scenarios (both subject to documented `EXT-VLA-C06` command-conditioning /
future-displacement leakage under their canonical `turn left` command):
- `scene_02_stationary_lead_obstacle` (`frame_token = 3cacb287d398542f`)
- `scene_06_intersection_turn_maneuver` (`frame_token = c9d4d04945e85ef8`)

CRITICAL INTERPRETATION RULE:
The logged human trajectory in `scene_02` and `scene_06` reflects the actual human
left-turn maneuver (`y_GT(5.0s) = +16.67 m` and `+8.35 m`). It is NOT a valid ground-truth
target for a deliberately different `keep forward` command. Changes in ADE/FDE under
`keep forward` quantify command sensitivity relative to the recorded turning trajectory,
NOT policy quality, driving safety, or superiority/inferiority of either trajectory.
"""

from __future__ import annotations

import argparse
import copy
import csv
import gc
import json
import math
from pathlib import Path
from typing import Any

from extensions.vla_handover_feasibility.action_tokenizer import (
    ACTION_VOCAB_SIZE,
    BASE_QWEN_VOCAB_SIZE,
    DEFAULT_CODEBOOK_PATH,
    AutoVLAActionTokenizer,
    wrap_angle_rad,
)
from extensions.vla_handover_feasibility.provenance_audit import (
    ACTION_TAG_REGEX,
    ProvenanceMismatchError,
    sha256_file,
    verify_scene_and_prediction_provenance,
)
from extensions.vla_handover_feasibility.r3b_adapter import (
    DEFAULT_TAKEOVER_REQUEST_TIMES_S,
    LATERAL_CORRIDOR_HALF_WIDTH_M,
    MAX_LONGITUDINAL_HEADING_RAD,
    evaluate_takeover_timing_schedule,
)
from extensions.vla_handover_feasibility.schemas import (
    ObstacleSourceType,
    TakeoverR3BStatus,
    TrajectoryWaypoint,
    VLAPredictionArtifact,
)
from extensions.vla_handover_feasibility.trajectory_verifier import (
    VerifierLimits,
    verify_trajectory_feasibility,
)
from extensions.vla_handover_feasibility.vla_inference import (
    DEFAULT_AUTOVLA_MODEL_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_PREDICTIONS_DIR,
    AutoVLAInferenceEngine,
    load_prediction_artifact,
)


def recompute_ade_fde(
    pred_wps: list[TrajectoryWaypoint],
    gt_wps: list[TrajectoryWaypoint],
) -> tuple[float, float]:
    """Compute Euclidean ADE (m) and FDE (m) over the 10-step horizon."""
    errs = [math.hypot(p.x_m - g.x_m, p.y_m - g.y_m) for p, g in zip(pred_wps, gt_wps)]
    return round(sum(errs) / len(errs), 4), round(errs[-1], 4)



EXT_ROOT = Path(__file__).resolve().parent
DEFAULT_COMMAND_SENSITIVITY_DIR = EXT_ROOT / "artifacts" / "command_sensitivity"

# Official in-distribution driving commands supported by ucla-mobility/AutoVLA
# (mapped from NAVSIM 4-element one-hot vector [turn_left, keep_forward, turn_right, unknown]).
# Note: "unknown" is NOT a supported prompt command string in AutoVLA training configs.
SUPPORTED_AUTOVLA_COMMANDS: tuple[str, ...] = (
    "turn left",
    "keep forward",
    "turn right",
)

# Frozen SHA-256 digests of the 7 canonical prediction artifacts to guarantee immutability
CANONICAL_PREDICTION_SHA256: dict[str, str] = {
    "scene_01_high_speed_open_road_fast.json": "776a1f5121dd21d1cd2949f2e756a3c2efa6b6171bbec561718051bf663423ca",
    "scene_02_stationary_lead_obstacle_fast.json": "0d257927c044da1f59149ced11ae9d5fc0cf937af0a89fd99115f84fe7d182d4",
    "scene_03_close_urban_lead_following_fast.json": "5a516928de7a3c6c2732c0b4ede31d5e486919315a34fbe22ab2ce291b777aa2",
    "scene_04_fast_arterial_lead_vehicle_fast.json": "de61ef1c170292347f054f63af790c2ae2adc78c3c17d9900f7bd1ffed0bd746",
    "scene_05_active_braking_deceleration_fast.json": "b54884da70ccccfe516202595a44124c596af016b2d93d480dc81fedd2e81fe3",
    "scene_06_intersection_turn_maneuver_fast.json": "a53c5470a8902ecdfda828d65c70ae9a86ceaf620501ad03895302eabc918fd5",
    "scene_07_stationary_ego_baseline_fast.json": "88f5f4edd77fc6139d1eed8b0f4a408fca7764b32d45f15d8dc6862ed780e5a8",
}

COMMAND_SENSITIVITY_SPECS: tuple[dict[str, str], ...] = (
    {
        "scene_id": "scene_02_stationary_lead_obstacle",
        "short_id": "scene_02",
        "control_command": "turn left",
        "intervention_command": "keep forward",
        "control_filename": "scene_02_stationary_lead_obstacle_fast.json",
        "intervention_filename": "scene_02_keep_forward.json",
    },
    {
        "scene_id": "scene_06_intersection_turn_maneuver",
        "short_id": "scene_06",
        "control_command": "turn left",
        "intervention_command": "keep forward",
        "control_filename": "scene_06_intersection_turn_maneuver_fast.json",
        "intervention_filename": "scene_06_keep_forward.json",
    },
)


def verify_canonical_predictions_unchanged(
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
) -> dict[str, str]:
    """Verify all 7 canonical prediction JSON files are byte-for-byte identical to their frozen SHA-256 hashes."""
    p_dir = Path(predictions_dir)
    verified: dict[str, str] = {}
    for fname, expected_sha in CANONICAL_PREDICTION_SHA256.items():
        fpath = p_dir / fname
        if not fpath.exists():
            raise ProvenanceMismatchError(f"Canonical prediction file missing: {fpath}")
        actual_sha = sha256_file(fpath)
        if actual_sha != expected_sha:
            raise ProvenanceMismatchError(
                f"Canonical prediction file {fname} was modified! expected_sha={expected_sha}, actual_sha={actual_sha}"
            )
        verified[fname] = actual_sha
    return verified


def verify_command_intervention_provenance(
    scene_meta: dict[str, Any],
    control_artifact: VLAPredictionArtifact,
    intervention_artifact: VLAPredictionArtifact,
    expected_intervention_command: str,
    action_tokenizer: AutoVLAActionTokenizer | None = None,
    intervention_path: str | Path | None = None,
    control_path: str | Path | None = None,
) -> dict[str, Any]:
    """Strictly verify that `intervention_artifact` isolates a single-variable command change relative to `control_artifact`."""
    sid = str(scene_meta["scene_id"])
    if expected_intervention_command not in SUPPORTED_AUTOVLA_COMMANDS:
        raise ProvenanceMismatchError(
            f"[{sid}] Unsupported AutoVLA command {expected_intervention_command!r}; "
            f"supported commands: {SUPPORTED_AUTOVLA_COMMANDS}"
        )

    # 1. Scene & sample identity match
    if intervention_artifact.scene_id != sid or control_artifact.scene_id != sid:
        raise ProvenanceMismatchError(
            f"[{sid}] Scene ID mismatch: control={control_artifact.scene_id}, intervention={intervention_artifact.scene_id}"
        )
    for field in ("dataset_source", "log_file", "frame_token", "scene_name", "map_location", "timestamp_us"):
        c_val = getattr(control_artifact, field)
        i_val = getattr(intervention_artifact, field)
        m_val = scene_meta[field]
        if c_val != m_val or i_val != m_val:
            raise ProvenanceMismatchError(
                f"[{sid}] Provenance field {field!r} mismatch: manifest={m_val!r}, control={c_val!r}, intervention={i_val!r}"
            )

    # 2. Ego initial kinematics held strictly constant
    for k_field in (
        "ego_initial_speed_mps",
        "ego_initial_accel_mps2",
        "ego_vx_mps",
        "ego_vy_mps",
        "ego_ax_mps2",
        "ego_ay_mps2",
    ):
        c_num = float(getattr(control_artifact, k_field))
        i_num = float(getattr(intervention_artifact, k_field))
        if abs(c_num - i_num) > 1e-6:
            raise ProvenanceMismatchError(
                f"[{sid}] Ego kinematic field {k_field} changed between control ({c_num}) and intervention ({i_num})"
            )

    # 3. Checkpoint & architecture held strictly constant
    for ck_field in (
        "checkpoint_repo",
        "checkpoint_file",
        "checkpoint_etag",
        "base_vlm_architecture",
        "inference_mode",
        "predicts_human_takeover_request",
        "coordinate_frame",
        "horizon_s",
        "dt_s",
    ):
        c_ck = getattr(control_artifact, ck_field)
        i_ck = getattr(intervention_artifact, ck_field)
        if c_ck != i_ck:
            raise ProvenanceMismatchError(
                f"[{sid}] Model/config field {ck_field} changed: control={c_ck!r} vs intervention={i_ck!r}"
            )

    # 4. Command isolation check: prompt_text must differ ONLY in the driving command substring
    ctrl_cmd = control_artifact.driving_command
    if intervention_artifact.driving_command != expected_intervention_command:
        raise ProvenanceMismatchError(
            f"[{sid}] Intervention driving_command={intervention_artifact.driving_command!r} != expected {expected_intervention_command!r}"
        )
    expected_prompt = control_artifact.prompt_text.replace(
        f"driving command is {ctrl_cmd}.",
        f"driving command is {expected_intervention_command}.",
    )
    if intervention_artifact.prompt_text != expected_prompt:
        raise ProvenanceMismatchError(
            f"[{sid}] Prompt isolation violated!\n"
            f"  Expected: {expected_prompt!r}\n"
            f"  Actual  : {intervention_artifact.prompt_text!r}"
        )

    # 5. Action tokens & codebook decoding verification
    parsed_tags = [int(m) for m in ACTION_TAG_REGEX.findall(intervention_artifact.raw_generated_text)]
    if len(parsed_tags) < 10:
        raise ProvenanceMismatchError(
            f"[{sid}] Expected 10 <action_k> tags in intervention raw_generated_text, got {len(parsed_tags)}"
        )
    if parsed_tags[:10] != list(intervention_artifact.action_codebook_indices):
        raise ProvenanceMismatchError(
            f"[{sid}] Intervention action_codebook_indices {intervention_artifact.action_codebook_indices} "
            f"do not match raw_generated_text tags {parsed_tags[:10]}"
        )
    if any(k < 0 or k >= ACTION_VOCAB_SIZE for k in intervention_artifact.action_codebook_indices):
        raise ProvenanceMismatchError(
            f"[{sid}] Out-of-range intervention codebook indices: {intervention_artifact.action_codebook_indices}"
        )
    expected_token_ids = [BASE_QWEN_VOCAB_SIZE + int(k) for k in intervention_artifact.action_codebook_indices]
    if list(intervention_artifact.action_token_ids) != expected_token_ids:
        raise ProvenanceMismatchError(
            f"[{sid}] Intervention action_token_ids {intervention_artifact.action_token_ids} != {expected_token_ids}"
        )

    tok = action_tokenizer or AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    decoded_wps = tok.decode_indices_to_waypoints(intervention_artifact.action_codebook_indices)
    if len(decoded_wps) != 10 or len(intervention_artifact.predicted_waypoints) != 10:
        raise ProvenanceMismatchError(f"[{sid}] Expected 10 decoded waypoints in intervention artifact")
    for dw, pw in zip(decoded_wps, intervention_artifact.predicted_waypoints):
        if (
            dw.step != pw.step
            or abs(dw.t_s - pw.t_s) > 1e-5
            or abs(dw.x_m - pw.x_m) > 1e-5
            or abs(dw.y_m - pw.y_m) > 1e-5
            or abs(dw.heading_rad - pw.heading_rad) > 1e-5
        ):
            raise ProvenanceMismatchError(
                f"[{sid}] Intervention decoded waypoint mismatch at step {dw.step}: {dw} vs {pw}"
            )

    # 6. Ground-truth reference waypoints must be identical to control
    if len(control_artifact.ground_truth_waypoints) != len(intervention_artifact.ground_truth_waypoints):
        raise ProvenanceMismatchError(f"[{sid}] Ground-truth waypoint length mismatch")
    for cw, iw in zip(control_artifact.ground_truth_waypoints, intervention_artifact.ground_truth_waypoints):
        if (
            cw.step != iw.step
            or abs(cw.t_s - iw.t_s) > 1e-5
            or abs(cw.x_m - iw.x_m) > 1e-5
            or abs(cw.y_m - iw.y_m) > 1e-5
            or abs(cw.heading_rad - iw.heading_rad) > 1e-5
        ):
            raise ProvenanceMismatchError(f"[{sid}] Ground-truth waypoint mismatch at step {cw.step}")

    ctrl_ade, ctrl_fde = recompute_ade_fde(
        control_artifact.predicted_waypoints, control_artifact.ground_truth_waypoints
    )
    intv_ade, intv_fde = recompute_ade_fde(
        intervention_artifact.predicted_waypoints, intervention_artifact.ground_truth_waypoints
    )

    return {
        "scene_id": sid,
        "frame_token": intervention_artifact.frame_token,
        "artifact_role": "CONTROLLED_COMMAND_INTERVENTION",
        "control_command": ctrl_cmd,
        "intervention_command": expected_intervention_command,
        "prompt_isolation_verified": True,
        "control_artifact_sha256": sha256_file(control_path) if control_path and Path(control_path).exists() else None,
        "intervention_artifact_sha256": (
            sha256_file(intervention_path) if intervention_path and Path(intervention_path).exists() else None
        ),
        "control_ade_vs_logged_gt_m": ctrl_ade,
        "control_fde_vs_logged_gt_m": ctrl_fde,
        "intervention_ade_vs_logged_gt_m": intv_ade,
        "intervention_fde_vs_logged_gt_m": intv_fde,
    }


def run_command_sensitivity_interventions(
    manifest_path: str | Path = DEFAULT_DATA_DIR / "scenes_manifest.json",
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
    output_dir: str | Path = DEFAULT_COMMAND_SENSITIVITY_DIR,
    model_dir: str | Path = DEFAULT_AUTOVLA_MODEL_DIR,
    force_recompute: bool = False,
    device: str | None = None,
) -> dict[str, tuple[VLAPredictionArtifact, VLAPredictionArtifact, Path, Path]]:
    """Load or execute sequential (batch_size=1) AutoVLA `keep forward` interventions for Scene 02 and Scene 06.

    Never modifies the 7 canonical prediction JSON files in `predictions_dir`.
    Reuses cached intervention JSON files in `output_dir` after validating their provenance.
    """
    verify_canonical_predictions_unchanged(predictions_dir)

    manifest_file = Path(manifest_path)
    manifest_sha = sha256_file(manifest_file)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    data_root = manifest_file.parent
    scene_by_id = {s["scene_id"]: s for s in manifest["scenes"]}
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)

    pred_root = Path(predictions_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    results: dict[str, tuple[VLAPredictionArtifact, VLAPredictionArtifact, Path, Path]] = {}
    pending_specs: list[tuple[dict[str, str], dict[str, Any], VLAPredictionArtifact, Path, Path]] = []

    for spec in COMMAND_SENSITIVITY_SPECS:
        sid = spec["scene_id"]
        scene_meta = scene_by_id[sid]
        ctrl_path = pred_root / spec["control_filename"]
        intv_path = out_root / spec["intervention_filename"]
        fallback_intv_path = DEFAULT_COMMAND_SENSITIVITY_DIR / spec["intervention_filename"]
        read_intv_path = intv_path if intv_path.exists() else fallback_intv_path

        ctrl_art = load_prediction_artifact(ctrl_path)
        verify_scene_and_prediction_provenance(
            scene_meta=scene_meta,
            artifact=ctrl_art,
            data_root=data_root,
            action_tokenizer=tokenizer,
            artifact_path=ctrl_path,
            manifest_sha256=manifest_sha,
        )

        if not force_recompute and read_intv_path.exists():
            cached_intv = load_prediction_artifact(read_intv_path)
            if cached_intv.prediction_valid:
                verify_command_intervention_provenance(
                    scene_meta=scene_meta,
                    control_artifact=ctrl_art,
                    intervention_artifact=cached_intv,
                    expected_intervention_command=spec["intervention_command"],
                    action_tokenizer=tokenizer,
                    intervention_path=read_intv_path,
                    control_path=ctrl_path,
                )
                results[sid] = (ctrl_art, cached_intv, ctrl_path, read_intv_path)
                continue

        pending_specs.append((spec, scene_meta, ctrl_art, ctrl_path, intv_path))

    if pending_specs:
        print(
            f"Loading genuine AutoVLA checkpoint from {model_dir} for {len(pending_specs)} sequential "
            f"command-sensitivity forward pass(es) (batch_size=1)...",
            flush=True,
        )
        engine = AutoVLAInferenceEngine(model_dir=model_dir, device=device)

        for spec, scene_meta, ctrl_art, ctrl_path, intv_path in pending_specs:
            sid = spec["scene_id"]
            intv_cmd = spec["intervention_command"]
            print(
                f"Running genuine sequential AutoVLA inference (batch_size=1) on {sid} "
                f"with controlled command intervention: {ctrl_art.driving_command!r} -> {intv_cmd!r}...",
                flush=True,
            )
            # Construct an isolated copy of scene_meta where ONLY effective_driving_command is changed
            scene_meta_intv = copy.deepcopy(scene_meta)
            scene_meta_intv["ego_state"]["effective_driving_command"] = intv_cmd

            intv_art = engine.predict_scene(
                scene_meta=scene_meta_intv,
                data_root=data_root,
                use_cot=False,
            )
            with open(intv_path, "w", encoding="utf-8") as f:
                json.dump(intv_art.to_dict(), f, indent=2)

            verify_command_intervention_provenance(
                scene_meta=scene_meta,
                control_artifact=ctrl_art,
                intervention_artifact=intv_art,
                expected_intervention_command=intv_cmd,
                action_tokenizer=tokenizer,
                intervention_path=intv_path,
                control_path=ctrl_path,
            )
            env_meta = intv_art.environment_metadata
            print(
                f"  -> Saved {intv_path.name} | latency={intv_art.inference_latency_ms:.1f}ms | "
                f"device={env_meta.get('device')} | peak_rss={env_meta.get('peak_rss_mb')}MB | "
                f"swap_used={env_meta.get('swap_used_mb')}MB | tokens={intv_art.action_codebook_indices}",
                flush=True,
            )
            results[sid] = (ctrl_art, intv_art, ctrl_path, intv_path)
            gc.collect()

    verify_canonical_predictions_unchanged(predictions_dir)
    return results


def _classify_qualitative_maneuver(waypoints: list[TrajectoryWaypoint]) -> dict[str, Any]:
    """Classify qualitative maneuver geometry and determine when/if the trajectory exits the R3B longitudinal corridor."""
    final_wp = waypoints[-1]
    max_abs_y = max(abs(w.y_m) for w in waypoints)
    max_abs_heading = max(abs(w.heading_rad) for w in waypoints)

    corridor_exit_step: int | None = None
    corridor_exit_tau_s: float | None = None
    for w in waypoints:
        if abs(w.y_m) > LATERAL_CORRIDOR_HALF_WIDTH_M or abs(w.heading_rad) > MAX_LONGITUDINAL_HEADING_RAD:
            corridor_exit_step = w.step
            corridor_exit_tau_s = w.t_s
            break

    if final_wp.y_m > LATERAL_CORRIDOR_HALF_WIDTH_M and final_wp.heading_rad > 0.15:
        maneuver_label = "LEFT_TURN_OR_LEFT_LANE_DEPARTURE"
    elif final_wp.y_m < -LATERAL_CORRIDOR_HALF_WIDTH_M and final_wp.heading_rad < -0.15:
        maneuver_label = "RIGHT_TURN_OR_RIGHT_LANE_DEPARTURE"
    elif max_abs_y <= LATERAL_CORRIDOR_HALF_WIDTH_M and max_abs_heading <= MAX_LONGITUDINAL_HEADING_RAD:
        maneuver_label = "STRAIGHT_IN_CORRIDOR_PROGRESSION"
    else:
        maneuver_label = "MODERATE_LATERAL_DRIFT_OR_SHALLOW_CURVE"

    return {
        "maneuver_label": maneuver_label,
        "final_x_m": round(final_wp.x_m, 4),
        "final_y_m": round(final_wp.y_m, 4),
        "final_heading_rad": round(final_wp.heading_rad, 4),
        "final_heading_deg": round(math.degrees(final_wp.heading_rad), 2),
        "max_abs_y_m": round(max_abs_y, 4),
        "max_abs_heading_rad": round(max_abs_heading, 4),
        "max_abs_heading_deg": round(math.degrees(max_abs_heading), 2),
        "remains_in_r3b_longitudinal_corridor_all_5s": corridor_exit_step is None,
        "first_corridor_exit_step": corridor_exit_step,
        "first_corridor_exit_tau_s": corridor_exit_tau_s,
    }


def _summarize_r3b_schedule(evals: list[Any]) -> dict[str, Any]:
    """Summarize R3B takeover schedule across tau_req in 0.0..3.0 s without fabricating margins outside the corridor."""
    admissible_taus: list[float] = []
    non_applicable_taus: list[dict[str, Any]] = []
    p1_dry_by_tau: dict[str, Any] = {}
    p1_wet_by_tau: dict[str, Any] = {}

    for ev in evals:
        tau_key = f"{ev.tau_req_s:.1f}s"
        if ev.status == TakeoverR3BStatus.EVALUATED:
            admissible_taus.append(ev.tau_req_s)
            for br in ev.branch_results:
                if br.branch_id == "P1" and abs(br.mu - 1.0) < 1e-3:
                    p1_dry_by_tau[tau_key] = {
                        "status": "APPLICABLE",
                        "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                        "d_rem_m": ev.remaining_obstacle_distance_m,
                        "margin_min_m": br.margin_min_m,
                        "margin_max_m": br.margin_max_m,
                        "margin_min_s": br.margin_min_s,
                        "margin_max_s": br.margin_max_s,
                        "interval_classification": br.interval_classification,
                        "state_source": ev.state_source,
                    }
                elif br.branch_id == "P1" and abs(br.mu - 0.5) < 1e-3:
                    p1_wet_by_tau[tau_key] = {
                        "status": "APPLICABLE",
                        "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                        "d_rem_m": ev.remaining_obstacle_distance_m,
                        "margin_min_m": br.margin_min_m,
                        "margin_max_m": br.margin_max_m,
                        "margin_min_s": br.margin_min_s,
                        "margin_max_s": br.margin_max_s,
                        "interval_classification": br.interval_classification,
                        "state_source": ev.state_source,
                    }
        else:
            reason_str = "; ".join(ev.insufficient_evidence_reasons)
            non_applicable_taus.append({"tau_req_s": ev.tau_req_s, "reason": reason_str})
            p1_dry_by_tau[tau_key] = {
                "status": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
                "reason": reason_str,
            }
            p1_wet_by_tau[tau_key] = {
                "status": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
                "reason": reason_str,
            }

    return {
        "admissible_tau_req_s": admissible_taus,
        "admissible_count": len(admissible_taus),
        "total_tau_count": len(evals),
        "non_applicable_taus": non_applicable_taus,
        "p1_dry_mu1.0_by_tau": p1_dry_by_tau,
        "p1_wet_mu0.5_by_tau": p1_wet_by_tau,
    }


def evaluate_command_sensitivity(
    manifest_path: str | Path = DEFAULT_DATA_DIR / "scenes_manifest.json",
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
    output_dir: str | Path = DEFAULT_COMMAND_SENSITIVITY_DIR,
    model_dir: str | Path = DEFAULT_AUTOVLA_MODEL_DIR,
    force_recompute_inference: bool = False,
    device: str | None = None,
) -> dict[str, Any]:
    """Run Phase C comparative evaluation on Scene 02 and Scene 06 (`turn left` control vs `keep forward` intervention)."""
    pairs = run_command_sensitivity_interventions(
        manifest_path=manifest_path,
        predictions_dir=predictions_dir,
        output_dir=output_dir,
        model_dir=model_dir,
        force_recompute=force_recompute_inference,
        device=device,
    )

    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    scene_by_id = {s["scene_id"]: s for s in manifest["scenes"]}
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    nominal_limits = VerifierLimits(
        max_lon_accel_mps2=4.0,
        max_braking_planning_mps2=4.0,
        max_braking_physical_mps2=8.0,
        max_abs_lat_accel_mps2=4.5,
        max_abs_yaw_rate_radps=0.75,
        reference_mu=1.0,
    )
    wet_limits = VerifierLimits(
        max_lon_accel_mps2=3.5,
        max_braking_planning_mps2=3.5,
        max_braking_physical_mps2=4.905,
        max_abs_lat_accel_mps2=2.0,
        max_abs_yaw_rate_radps=0.65,
        reference_mu=0.5,
    )

    scene_comparisons: dict[str, Any] = {}
    csv_rows: list[dict[str, Any]] = []

    for spec in COMMAND_SENSITIVITY_SPECS:
        sid = spec["scene_id"]
        scene_meta = scene_by_id[sid]
        ctrl_art, intv_art, ctrl_path, intv_path = pairs[sid]

        prov = verify_command_intervention_provenance(
            scene_meta=scene_meta,
            control_artifact=ctrl_art,
            intervention_artifact=intv_art,
            expected_intervention_command=spec["intervention_command"],
            action_tokenizer=tokenizer,
            intervention_path=intv_path,
            control_path=ctrl_path,
        )

        # Evaluate physical feasibility under dry (mu=1.0) and wet (mu=0.5)
        ctrl_feas_dry, ctrl_kin = verify_trajectory_feasibility(
            scene_id=sid,
            mode="control_turn_left_dry",
            waypoints=ctrl_art.predicted_waypoints,
            initial_speed_mps=ctrl_art.ego_initial_speed_mps,
            initial_accel_mps2=ctrl_art.ego_initial_accel_mps2,
            limits=nominal_limits,
        )
        ctrl_feas_wet, _ = verify_trajectory_feasibility(
            scene_id=sid,
            mode="control_turn_left_wet_mu0.5",
            waypoints=ctrl_art.predicted_waypoints,
            initial_speed_mps=ctrl_art.ego_initial_speed_mps,
            initial_accel_mps2=ctrl_art.ego_initial_accel_mps2,
            limits=wet_limits,
        )

        intv_feas_dry, intv_kin = verify_trajectory_feasibility(
            scene_id=sid,
            mode="intervention_keep_forward_dry",
            waypoints=intv_art.predicted_waypoints,
            initial_speed_mps=intv_art.ego_initial_speed_mps,
            initial_accel_mps2=intv_art.ego_initial_accel_mps2,
            limits=nominal_limits,
        )
        intv_feas_wet, _ = verify_trajectory_feasibility(
            scene_id=sid,
            mode="intervention_keep_forward_wet_mu0.5",
            waypoints=intv_art.predicted_waypoints,
            initial_speed_mps=intv_art.ego_initial_speed_mps,
            initial_accel_mps2=intv_art.ego_initial_accel_mps2,
            limits=wet_limits,
        )

        # Step-by-step trajectory & kinematic comparison
        step_deltas: list[dict[str, Any]] = []
        l2_divs: list[float] = []
        for c_wp, i_wp, g_wp, c_k, i_k in zip(
            ctrl_art.predicted_waypoints,
            intv_art.predicted_waypoints,
            ctrl_art.ground_truth_waypoints,
            ctrl_kin,
            intv_kin,
        ):
            dx_ci = i_wp.x_m - c_wp.x_m
            dy_ci = i_wp.y_m - c_wp.y_m
            l2_ci = math.hypot(dx_ci, dy_ci)
            l2_divs.append(l2_ci)
            dpsi_rad = float(wrap_angle_rad(i_wp.heading_rad - c_wp.heading_rad))
            dpsi_deg = math.degrees(dpsi_rad)

            step_row = {
                "scene_id": sid,
                "step": c_wp.step,
                "t_s": c_wp.t_s,
                "gt_x_m": round(g_wp.x_m, 4),
                "gt_y_m": round(g_wp.y_m, 4),
                "gt_heading_rad": round(g_wp.heading_rad, 4),
                "control_cmd": ctrl_art.driving_command,
                "control_token": ctrl_art.action_codebook_indices[c_wp.step - 1],
                "control_x_m": round(c_wp.x_m, 4),
                "control_y_m": round(c_wp.y_m, 4),
                "control_heading_rad": round(c_wp.heading_rad, 4),
                "control_heading_deg": round(math.degrees(c_wp.heading_rad), 2),
                "control_speed_mps": round(c_k.implied_speed_mps, 4),
                "control_a_lon_mps2": round(c_k.a_lon_mps2, 4),
                "control_a_lat_mps2": round(c_k.a_lat_mps2, 4),
                "control_yaw_rate_radps": round(c_k.yaw_rate_radps, 4),
                "intervention_cmd": intv_art.driving_command,
                "intervention_token": intv_art.action_codebook_indices[i_wp.step - 1],
                "intervention_x_m": round(i_wp.x_m, 4),
                "intervention_y_m": round(i_wp.y_m, 4),
                "intervention_heading_rad": round(i_wp.heading_rad, 4),
                "intervention_heading_deg": round(math.degrees(i_wp.heading_rad), 2),
                "intervention_speed_mps": round(i_k.implied_speed_mps, 4),
                "intervention_a_lon_mps2": round(i_k.a_lon_mps2, 4),
                "intervention_a_lat_mps2": round(i_k.a_lat_mps2, 4),
                "intervention_yaw_rate_radps": round(i_k.yaw_rate_radps, 4),
                "delta_x_m_intv_minus_ctrl": round(dx_ci, 4),
                "delta_y_m_intv_minus_ctrl": round(dy_ci, 4),
                "l2_divergence_m": round(l2_ci, 4),
                "delta_heading_rad_intv_minus_ctrl": round(dpsi_rad, 4),
                "delta_heading_deg_intv_minus_ctrl": round(dpsi_deg, 2),
            }
            step_deltas.append(step_row)
            csv_rows.append(step_row)

        ctrl_maneuver = _classify_qualitative_maneuver(ctrl_art.predicted_waypoints)
        intv_maneuver = _classify_qualitative_maneuver(intv_art.predicted_waypoints)

        # R3B Braking-Only Evaluation (strictly enforcing longitudinal corridor and obstacle evidence)
        obs_lead = scene_meta.get("observed_in_lane_lead_obstacle")
        if obs_lead is not None:
            obs_source = ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION
            obs_d0: float | None = float(obs_lead["x_m"])
            obs_v_lead: float | None = float(obs_lead["speed_mps"])
        else:
            obs_source = ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE
            obs_d0 = None
            obs_v_lead = None

        ctrl_obs_r3b = evaluate_takeover_timing_schedule(
            scene_id=sid,
            inference_mode="control_turn_left",
            initial_speed_mps=ctrl_art.ego_initial_speed_mps,
            waypoints=ctrl_art.predicted_waypoints,
            kinematics=ctrl_kin,
            obstacle_source=obs_source,
            initial_obstacle_distance_d0_m=obs_d0,
            observed_lead_speed_mps=obs_v_lead,
            request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
            strict_longitudinal_corridor=True,
        )
        intv_obs_r3b = evaluate_takeover_timing_schedule(
            scene_id=sid,
            inference_mode="intervention_keep_forward",
            initial_speed_mps=intv_art.ego_initial_speed_mps,
            waypoints=intv_art.predicted_waypoints,
            kinematics=intv_kin,
            obstacle_source=obs_source,
            initial_obstacle_distance_d0_m=obs_d0,
            observed_lead_speed_mps=obs_v_lead,
            request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
            strict_longitudinal_corridor=True,
        )

        cf_d0_list = scene_meta.get("counterfactual_obstacle_distances_m", [])
        ref_cf_d0 = float(cf_d0_list[0]) if cf_d0_list else 20.0
        ctrl_cf_r3b = evaluate_takeover_timing_schedule(
            scene_id=sid,
            inference_mode="control_turn_left_cf",
            initial_speed_mps=ctrl_art.ego_initial_speed_mps,
            waypoints=ctrl_art.predicted_waypoints,
            kinematics=ctrl_kin,
            obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
            initial_obstacle_distance_d0_m=ref_cf_d0,
            observed_lead_speed_mps=None,
            request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
            strict_longitudinal_corridor=True,
        )
        intv_cf_r3b = evaluate_takeover_timing_schedule(
            scene_id=sid,
            inference_mode="intervention_keep_forward_cf",
            initial_speed_mps=intv_art.ego_initial_speed_mps,
            waypoints=intv_art.predicted_waypoints,
            kinematics=intv_kin,
            obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
            initial_obstacle_distance_d0_m=ref_cf_d0,
            observed_lead_speed_mps=None,
            request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
            strict_longitudinal_corridor=True,
        )

        ctrl_failed_dry = [c.check_id for c in ctrl_feas_dry.checks if not c.passed]
        ctrl_failed_wet = [c.check_id for c in ctrl_feas_wet.checks if not c.passed]
        intv_failed_dry = [c.check_id for c in intv_feas_dry.checks if not c.passed]
        intv_failed_wet = [c.check_id for c in intv_feas_wet.checks if not c.passed]

        new_violations_dry = [cid for cid in intv_failed_dry if cid not in ctrl_failed_dry]
        new_violations_wet = [cid for cid in intv_failed_wet if cid not in ctrl_failed_wet]
        resolved_violations_dry = [cid for cid in ctrl_failed_dry if cid not in intv_failed_dry]
        resolved_violations_wet = [cid for cid in ctrl_failed_wet if cid not in intv_failed_wet]

        scene_comparisons[sid] = {
            "scene_id": sid,
            "frame_token": ctrl_art.frame_token,
            "scene_name": ctrl_art.scene_name,
            "map_location": ctrl_art.map_location,
            "ego_initial_speed_mps": ctrl_art.ego_initial_speed_mps,
            "ego_initial_accel_mps2": ctrl_art.ego_initial_accel_mps2,
            "provenance": prov,
            "critical_interpretation_notice": (
                "The logged human trajectory reflects the actual human left-turn maneuver. "
                "It is NOT a valid ground-truth target for a deliberately different `keep forward` command. "
                "ADE/FDE changes under `keep forward` measure command sensitivity relative to the recorded "
                "turning reference, not driving policy superiority or safety."
            ),
            "control_turn_left": {
                "artifact_path": str(ctrl_path.relative_to(EXT_ROOT)),
                "artifact_sha256": prov["control_artifact_sha256"],
                "driving_command": ctrl_art.driving_command,
                "prompt_text": ctrl_art.prompt_text,
                "action_codebook_indices": list(ctrl_art.action_codebook_indices),
                "inference_latency_ms": ctrl_art.inference_latency_ms,
                "device": ctrl_art.environment_metadata.get("device"),
                "ade_vs_logged_left_turn_gt_m": prov["control_ade_vs_logged_gt_m"],
                "fde_vs_logged_left_turn_gt_m": prov["control_fde_vs_logged_gt_m"],
                "final_displacement_x_m": round(ctrl_art.predicted_waypoints[-1].x_m, 4),
                "final_displacement_y_m": round(ctrl_art.predicted_waypoints[-1].y_m, 4),
                "final_heading_rad": round(ctrl_art.predicted_waypoints[-1].heading_rad, 4),
                "final_heading_deg": round(math.degrees(ctrl_art.predicted_waypoints[-1].heading_rad), 2),
                "kinematics_summary": {
                    "min_speed_mps": ctrl_feas_dry.min_implied_speed_mps,
                    "max_speed_mps": ctrl_feas_dry.max_implied_speed_mps,
                    "min_lon_accel_mps2": ctrl_feas_dry.min_lon_accel_mps2,
                    "max_lon_accel_mps2": ctrl_feas_dry.max_lon_accel_mps2,
                    "peak_abs_lon_accel_mps2": round(
                        max(abs(ctrl_feas_dry.min_lon_accel_mps2), abs(ctrl_feas_dry.max_lon_accel_mps2)), 4
                    ),
                    "max_braking_demand_mps2": ctrl_feas_dry.max_braking_demand_mps2,
                    "max_abs_lat_accel_mps2": ctrl_feas_dry.max_abs_lat_accel_mps2,
                    "max_total_accel_mps2": ctrl_feas_dry.max_total_accel_mps2,
                    "max_abs_yaw_rate_radps": ctrl_feas_dry.max_abs_yaw_rate_radps,
                    "total_path_length_m": ctrl_feas_dry.total_path_length_m,
                },
                "feasibility_dry_mu1.0": ctrl_feas_dry.classification.value,
                "feasibility_wet_mu0.5": ctrl_feas_wet.classification.value,
                "failed_checks_dry": ctrl_failed_dry,
                "failed_checks_wet": ctrl_failed_wet,
                "maneuver": ctrl_maneuver,
                "waypoints": [w.to_dict() for w in ctrl_art.predicted_waypoints],
            },
            "intervention_keep_forward": {
                "artifact_path": str(intv_path.relative_to(EXT_ROOT)),
                "artifact_sha256": prov["intervention_artifact_sha256"],
                "driving_command": intv_art.driving_command,
                "prompt_text": intv_art.prompt_text,
                "action_codebook_indices": list(intv_art.action_codebook_indices),
                "inference_latency_ms": round(intv_art.inference_latency_ms, 2),
                "device": intv_art.environment_metadata.get("device"),
                "peak_rss_mb": intv_art.environment_metadata.get("peak_rss_mb"),
                "swap_used_mb": intv_art.environment_metadata.get("swap_used_mb"),
                "ade_vs_logged_left_turn_gt_m": prov["intervention_ade_vs_logged_gt_m"],
                "fde_vs_logged_left_turn_gt_m": prov["intervention_fde_vs_logged_gt_m"],
                "final_displacement_x_m": round(intv_art.predicted_waypoints[-1].x_m, 4),
                "final_displacement_y_m": round(intv_art.predicted_waypoints[-1].y_m, 4),
                "final_heading_rad": round(intv_art.predicted_waypoints[-1].heading_rad, 4),
                "final_heading_deg": round(math.degrees(intv_art.predicted_waypoints[-1].heading_rad), 2),
                "kinematics_summary": {
                    "min_speed_mps": intv_feas_dry.min_implied_speed_mps,
                    "max_speed_mps": intv_feas_dry.max_implied_speed_mps,
                    "min_lon_accel_mps2": intv_feas_dry.min_lon_accel_mps2,
                    "max_lon_accel_mps2": intv_feas_dry.max_lon_accel_mps2,
                    "peak_abs_lon_accel_mps2": round(
                        max(abs(intv_feas_dry.min_lon_accel_mps2), abs(intv_feas_dry.max_lon_accel_mps2)), 4
                    ),
                    "max_braking_demand_mps2": intv_feas_dry.max_braking_demand_mps2,
                    "max_abs_lat_accel_mps2": intv_feas_dry.max_abs_lat_accel_mps2,
                    "max_total_accel_mps2": intv_feas_dry.max_total_accel_mps2,
                    "max_abs_yaw_rate_radps": intv_feas_dry.max_abs_yaw_rate_radps,
                    "total_path_length_m": intv_feas_dry.total_path_length_m,
                },
                "feasibility_dry_mu1.0": intv_feas_dry.classification.value,
                "feasibility_wet_mu0.5": intv_feas_wet.classification.value,
                "failed_checks_dry": intv_failed_dry,
                "failed_checks_wet": intv_failed_wet,
                "maneuver": intv_maneuver,
                "waypoints": [w.to_dict() for w in intv_art.predicted_waypoints],
            },
            "ground_truth_logged_maneuver": {
                "final_x_m": round(ctrl_art.ground_truth_waypoints[-1].x_m, 4),
                "final_y_m": round(ctrl_art.ground_truth_waypoints[-1].y_m, 4),
                "final_heading_rad": round(ctrl_art.ground_truth_waypoints[-1].heading_rad, 4),
                "final_heading_deg": round(math.degrees(ctrl_art.ground_truth_waypoints[-1].heading_rad), 2),
                "waypoints": [w.to_dict() for w in ctrl_art.ground_truth_waypoints],
            },
            "comparative_metrics": {
                "tokens_changed_count": sum(
                    1
                    for a, b in zip(ctrl_art.action_codebook_indices, intv_art.action_codebook_indices)
                    if a != b
                ),
                "first_divergent_step": next(
                    (
                        idx + 1
                        for idx, (a, b) in enumerate(
                            zip(ctrl_art.action_codebook_indices, intv_art.action_codebook_indices)
                        )
                        if a != b
                    ),
                    None,
                ),
                "mean_l2_trajectory_divergence_m": round(sum(l2_divs) / len(l2_divs), 4),
                "final_step_l2_divergence_m": round(l2_divs[-1], 4),
                "delta_final_x_m_intv_minus_ctrl": round(
                    intv_art.predicted_waypoints[-1].x_m - ctrl_art.predicted_waypoints[-1].x_m, 4
                ),
                "delta_final_y_m_intv_minus_ctrl": round(
                    intv_art.predicted_waypoints[-1].y_m - ctrl_art.predicted_waypoints[-1].y_m, 4
                ),
                "delta_y_3s_m_intv_minus_ctrl": round(
                    intv_art.predicted_waypoints[5].y_m - ctrl_art.predicted_waypoints[5].y_m, 4
                ),
                "max_abs_lateral_diff_m": round(
                    max(abs(r["delta_y_m_intv_minus_ctrl"]) for r in step_deltas), 4
                ),
                "delta_final_heading_rad_intv_minus_ctrl": step_deltas[-1]["delta_heading_rad_intv_minus_ctrl"],
                "delta_final_heading_deg_intv_minus_ctrl": step_deltas[-1]["delta_heading_deg_intv_minus_ctrl"],
                "max_abs_heading_diff_deg": round(
                    max(abs(r["delta_heading_deg_intv_minus_ctrl"]) for r in step_deltas), 2
                ),
                "ade_vs_logged_gt_delta_m": round(
                    prov["intervention_ade_vs_logged_gt_m"] - prov["control_ade_vs_logged_gt_m"], 4
                ),
                "fde_vs_logged_gt_delta_m": round(
                    prov["intervention_fde_vs_logged_gt_m"] - prov["control_fde_vs_logged_gt_m"], 4
                ),
                "qualitative_maneuver_changed": (
                    ctrl_maneuver["maneuver_label"] != intv_maneuver["maneuver_label"]
                ),
                "new_constraint_violations_dry": new_violations_dry,
                "new_constraint_violations_wet": new_violations_wet,
                "resolved_constraint_violations_dry": resolved_violations_dry,
                "resolved_constraint_violations_wet": resolved_violations_wet,
                "step_by_step_deltas": step_deltas,
            },
            "r3b_impact": {
                "observed_obstacle_present": obs_lead is not None,
                "observed_obstacle_d0_m": obs_d0,
                "observed_schedule_control_turn_left": _summarize_r3b_schedule(ctrl_obs_r3b),
                "observed_schedule_intervention_keep_forward": _summarize_r3b_schedule(intv_obs_r3b),
                "counterfactual_reference_d0_m": ref_cf_d0,
                "counterfactual_schedule_control_turn_left": _summarize_r3b_schedule(ctrl_cf_r3b),
                "counterfactual_schedule_intervention_keep_forward": _summarize_r3b_schedule(intv_cf_r3b),
            },
        }

    csv_path = out_root / "comparison.csv"
    if csv_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)

    summary = {
        "experiment_id": "AUTOVLA_COMMAND_SENSITIVITY_RQ1",
        "baseline_commit": "7225af0e72a415a6a73d3d86acaf2bdc8f0c7c8a",
        "supported_autovla_commands": list(SUPPORTED_AUTOVLA_COMMANDS),
        "canonical_predictions_verified_unchanged": True,
        "canonical_prediction_sha256": CANONICAL_PREDICTION_SHA256,
        "critical_interpretation_rule": (
            "The logged human trajectory is associated with the actual left-turn maneuver in Scene 02 and Scene 06. "
            "It is not a valid ground-truth target for a deliberately different `keep forward` command. "
            "Changes in ADE/FDE under `keep forward` measure command sensitivity relative to the recorded trajectory, "
            "not direct evidence that the intervention produced a better or worse driving policy."
        ),
        "scenes": scene_comparisons,
    }

    summary_path = out_root / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AutoVLA Phase B/C Command Sensitivity Experiment.")
    parser.add_argument("--force-recompute", action="store_true", help="Force live rerun of intervention inference")
    parser.add_argument("--device", type=str, default=None, help="Device override (e.g. mps, cpu)")
    args = parser.parse_args()

    summary = evaluate_command_sensitivity(
        force_recompute_inference=args.force_recompute,
        device=args.device,
    )
    for sid, sc in summary["scenes"].items():
        ctrl = sc["control_turn_left"]
        intv = sc["intervention_keep_forward"]
        cmp_m = sc["comparative_metrics"]
        print(
            f"[{sid}] Control ({ctrl['driving_command']}): tokens={ctrl['action_codebook_indices']} "
            f"end=({ctrl['final_displacement_x_m']:.2f}m, {ctrl['final_displacement_y_m']:+.2f}m, {ctrl['final_heading_deg']:+.1f}deg) "
            f"ADE/FDE={ctrl['ade_vs_logged_left_turn_gt_m']:.4f}/{ctrl['fde_vs_logged_left_turn_gt_m']:.4f}m "
            f"dry/wet={ctrl['feasibility_dry_mu1.0']}/{ctrl['feasibility_wet_mu0.5']}"
        )
        print(
            f"[{sid}] Interv  ({intv['driving_command']}): tokens={intv['action_codebook_indices']} "
            f"end=({intv['final_displacement_x_m']:.2f}m, {intv['final_displacement_y_m']:+.2f}m, {intv['final_heading_deg']:+.1f}deg) "
            f"ADE/FDE={intv['ade_vs_logged_left_turn_gt_m']:.4f}/{intv['fde_vs_logged_left_turn_gt_m']:.4f}m "
            f"dry/wet={intv['feasibility_dry_mu1.0']}/{intv['feasibility_wet_mu0.5']}"
        )
        print(
            f"  -> Delta: {cmp_m['tokens_changed_count']}/10 tokens changed (from step {cmp_m['first_divergent_step']}), "
            f"dy(5s)={cmp_m['delta_final_y_m_intv_minus_ctrl']:+.2f}m, "
            f"dpsi(5s)={cmp_m['delta_final_heading_deg_intv_minus_ctrl']:+.1f}deg, "
            f"mean_L2_div={cmp_m['mean_l2_trajectory_divergence_m']:.2f}m, "
            f"maneuver: {ctrl['maneuver']['maneuver_label']} -> {intv['maneuver']['maneuver_label']}"
        )


if __name__ == "__main__":
    main()
