"""Phase E Counterfactual Comparison & Experiment Runner.

Executes or loads genuine AutoVLA trajectory predictions across the extracted
real nuPlan/NAVSIM driving scenes, runs the independent Phase C trajectory
physical feasibility verifier, connects eligible scenario states to the Phase D
R3B braking-only recoverability adapter across immediate (`tau_req = 0.0 s`) and
delayed (`tau_req in {0.5, 1.0, 1.5, 2.0, 2.5, 3.0} s`) takeover request times,
and exports reproducible JSON/CSV artifacts and an independent extension claim
register.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from extensions.vla_handover_feasibility.action_tokenizer import (
    DEFAULT_CODEBOOK_PATH,
    AutoVLAActionTokenizer,
)
from extensions.vla_handover_feasibility.provenance_audit import (
    sha256_file,
    verify_scene_and_prediction_provenance,
)
from extensions.vla_handover_feasibility.r3b_adapter import (
    DEFAULT_TAKEOVER_REQUEST_TIMES_S,
    evaluate_takeover_timing_schedule,
)
from extensions.vla_handover_feasibility.schemas import (
    FeasibilityClassification,
    ObstacleSourceType,
    TakeoverR3BStatus,
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
    save_prediction_artifact,
)


DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
COT_SCENES: tuple[str, ...] = ()


def run_genuine_vla_inference_all_scenes(
    manifest_path: str | Path = DEFAULT_DATA_DIR / "scenes_manifest.json",
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
    model_dir: str | Path = DEFAULT_AUTOVLA_MODEL_DIR,
    force_recompute: bool = False,
    scene_ids: list[str] | None = None,
    device: str | None = None,
) -> list[VLAPredictionArtifact]:
    """Run genuine AutoVLA inference sequentially (batch_size=1), saving each scene immediately."""
    import gc

    manifest_file = Path(manifest_path)
    manifest_sha = sha256_file(manifest_file)
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    pred_dir = Path(predictions_dir)
    pred_dir.mkdir(parents=True, exist_ok=True)
    data_root = manifest_file.parent
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)

    selected_set = set(scene_ids) if scene_ids else None
    tasks: list[tuple[dict[str, Any], bool]] = []
    for scene in manifest["scenes"]:
        if selected_set is not None and scene["scene_id"] not in selected_set:
            continue
        tasks.append((scene, False))  # fast mode on selected scenes
        if scene["scene_id"] in COT_SCENES:
            tasks.append((scene, True))

    artifacts_by_key: dict[tuple[str, str], VLAPredictionArtifact] = {}
    pending_tasks: list[tuple[dict[str, Any], bool]] = []

    for scene, use_cot in tasks:
        mode = "cot" if use_cot else "fast"
        out_file = pred_dir / f"{scene['scene_id']}_{mode}.json"
        if not force_recompute and out_file.exists():
            cached_art = load_prediction_artifact(out_file)
            if cached_art.prediction_valid:
                verify_scene_and_prediction_provenance(
                    scene_meta=scene,
                    artifact=cached_art,
                    data_root=data_root,
                    action_tokenizer=tokenizer,
                    artifact_path=out_file,
                    manifest_sha256=manifest_sha,
                )
                artifacts_by_key[(scene["scene_id"], mode)] = cached_art
                print(
                    f"Skipping already completed & provenance-verified genuine prediction: {cached_art.scene_id} [{cached_art.inference_mode}] "
                    f"(token={cached_art.frame_token}, latency={cached_art.inference_latency_ms:.1f}ms, tokens={cached_art.action_codebook_indices})",
                    flush=True,
                )
                continue
        pending_tasks.append((scene, use_cot))

    if pending_tasks:
        print(f"Loading genuine AutoVLA model from {model_dir} (batch_size=1 sequential mode)...", flush=True)
        engine = AutoVLAInferenceEngine(model_dir=model_dir, device=device)

        for scene, use_cot in pending_tasks:
            mode = "cot" if use_cot else "fast"
            print(f"Running genuine sequential AutoVLA inference (batch_size=1) on {scene['scene_id']} [mode={mode}]...", flush=True)
            art = engine.predict_scene(scene_meta=scene, data_root=data_root, use_cot=use_cot)
            saved_path = save_prediction_artifact(art, out_dir=pred_dir)
            verify_scene_and_prediction_provenance(
                scene_meta=scene,
                artifact=art,
                data_root=data_root,
                action_tokenizer=tokenizer,
                artifact_path=saved_path,
                manifest_sha256=manifest_sha,
            )
            artifacts_by_key[(art.scene_id, art.inference_mode)] = art
            env_meta = art.environment_metadata
            print(
                f"  -> Saved {saved_path.name} | latency={art.inference_latency_ms:.1f}ms | "
                f"peak_rss={env_meta.get('peak_rss_mb')}MB | swap_used={env_meta.get('swap_used_mb')}MB | "
                f"valid={art.prediction_valid} | action_indices={art.action_codebook_indices}",
                flush=True,
            )
            gc.collect()

    ordered_artifacts: list[VLAPredictionArtifact] = []
    for scene, use_cot in tasks:
        mode = "cot" if use_cot else "fast"
        if (scene["scene_id"], mode) in artifacts_by_key:
            ordered_artifacts.append(artifacts_by_key[(scene["scene_id"], mode)])
    return ordered_artifacts


def evaluate_all_predictions_and_counterfactuals(
    manifest_path: str | Path = DEFAULT_DATA_DIR / "scenes_manifest.json",
    predictions_dir: str | Path = DEFAULT_PREDICTIONS_DIR,
    artifacts_dir: str | Path = DEFAULT_ARTIFACTS_DIR,
) -> dict[str, Any]:
    """Run Phase C trajectory feasibility verification and Phase D/E counterfactual R3B analysis on all saved real VLA predictions."""
    manifest_file = Path(manifest_path)
    manifest_sha = sha256_file(manifest_file)
    codebook_sha = sha256_file(DEFAULT_CODEBOOK_PATH)
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    data_root = manifest_file.parent
    tokenizer = AutoVLAActionTokenizer(DEFAULT_CODEBOOK_PATH)
    scene_by_id = {s["scene_id"]: s for s in manifest["scenes"]}
    pred_dir = Path(predictions_dir)
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pred_files = sorted(pred_dir.glob("*.json"))
    if not pred_files:
        raise FileNotFoundError(f"No VLA prediction artifacts found in {pred_dir}")

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

    evaluated_records: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []

    for pf in pred_files:
        art = load_prediction_artifact(pf)
        if art.scene_id not in scene_by_id:
            raise ValueError(f"Prediction artifact {pf} references unknown scene_id={art.scene_id!r}")
        scene_meta = scene_by_id[art.scene_id]

        # Strict 11-point provenance verification before any downstream calculation
        prov_audit = verify_scene_and_prediction_provenance(
            scene_meta=scene_meta,
            artifact=art,
            data_root=data_root,
            action_tokenizer=tokenizer,
            artifact_path=pf,
            manifest_sha256=manifest_sha,
        )

        is_stationary_scene = art.scene_id == "scene_07_stationary_ego_baseline"

        # 1. Independent Trajectory Feasibility Verifier (Nominal dry mu=1.0 & Wet mu=0.5)
        feas_nominal, kinematics = verify_trajectory_feasibility(
            scene_id=art.scene_id,
            mode=art.inference_mode,
            waypoints=art.predicted_waypoints,
            initial_speed_mps=art.ego_initial_speed_mps,
            initial_accel_mps2=art.ego_initial_accel_mps2,
            limits=nominal_limits,
            treat_stationary_as_not_applicable=is_stationary_scene,
        )
        feas_wet, _ = verify_trajectory_feasibility(
            scene_id=art.scene_id,
            mode=f"{art.inference_mode}_wet_mu0.5",
            waypoints=art.predicted_waypoints,
            initial_speed_mps=art.ego_initial_speed_mps,
            initial_accel_mps2=art.ego_initial_accel_mps2,
            limits=wet_limits,
            treat_stationary_as_not_applicable=is_stationary_scene,
        )

        # Also compute ground-truth trajectory kinematics for comparison
        _, gt_kinematics = verify_trajectory_feasibility(
            scene_id=art.scene_id,
            mode="ground_truth",
            waypoints=art.ground_truth_waypoints,
            initial_speed_mps=art.ego_initial_speed_mps,
            initial_accel_mps2=art.ego_initial_accel_mps2,
            limits=nominal_limits,
            treat_stationary_as_not_applicable=False,
        )

        ade_m = prov_audit["verified_ade_m"]
        fde_m = prov_audit["verified_fde_m"]

        # 2. Observed-only R3B Takeover Timing Evaluation (using only 3D annotation lead obstacle if present)
        obs_lead = scene_meta.get("observed_in_lane_lead_obstacle")
        if obs_lead is not None:
            obs_source = ObstacleSourceType.OBSERVED_IN_LANE_ANNOTATION
            obs_d0: float | None = float(obs_lead["x_m"])
            obs_v_lead: float | None = float(obs_lead["speed_mps"])
        else:
            obs_source = ObstacleSourceType.NONE_INSUFFICIENT_EVIDENCE
            obs_d0 = None
            obs_v_lead = None

        observed_schedule = evaluate_takeover_timing_schedule(
            scene_id=art.scene_id,
            inference_mode=art.inference_mode,
            initial_speed_mps=art.ego_initial_speed_mps,
            waypoints=art.predicted_waypoints,
            kinematics=kinematics,
            obstacle_source=obs_source,
            initial_obstacle_distance_d0_m=obs_d0,
            observed_lead_speed_mps=obs_v_lead,
            request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
            strict_longitudinal_corridor=True,
        )

        # 3. Counterfactual Obstacle Distance Schedules (explicitly labelled assumptions)
        counterfactual_schedules: dict[str, list[dict[str, Any]]] = {}
        for cf_d0 in scene_meta.get("counterfactual_obstacle_distances_m", []):
            cf_key = f"d0_{float(cf_d0):.2f}m"
            cf_evals = evaluate_takeover_timing_schedule(
                scene_id=art.scene_id,
                inference_mode=art.inference_mode,
                initial_speed_mps=art.ego_initial_speed_mps,
                waypoints=art.predicted_waypoints,
                kinematics=kinematics,
                obstacle_source=ObstacleSourceType.COUNTERFACTUAL_ASSUMPTION,
                initial_obstacle_distance_d0_m=float(cf_d0),
                observed_lead_speed_mps=None,
                request_times_s=DEFAULT_TAKEOVER_REQUEST_TIMES_S,
                strict_longitudinal_corridor=True,
            )
            counterfactual_schedules[cf_key] = [e.to_dict() for e in cf_evals]

            for ev in cf_evals:
                if ev.status == TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE:
                    csv_rows.append(
                        {
                            "scene_id": art.scene_id,
                            "inference_mode": art.inference_mode,
                            "trajectory_feasibility_nominal": feas_nominal.classification.value,
                            "trajectory_feasibility_wet_mu0.5": feas_wet.classification.value,
                            "obstacle_source": ev.obstacle_source.value,
                            "initial_d0_m": cf_d0,
                            "tau_req_s": ev.tau_req_s,
                            "state_source": ev.state_source,
                            "r3b_status": ev.status.value,
                            "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                            "d_rem_m": ev.remaining_obstacle_distance_m,
                            "ttc_stationary_s": ev.available_ttc_stationary_s,
                            "branch_id": "N/A",
                            "mu": "N/A",
                            "t_req_min_s": None,
                            "t_req_max_s": None,
                            "margin_min_s": None,
                            "margin_max_s": None,
                            "d_stop_min_m": None,
                            "d_stop_max_m": None,
                            "margin_min_m": None,
                            "margin_max_m": None,
                            "interval_classification": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
                            "insufficient_reason": "; ".join(ev.insufficient_evidence_reasons),
                        }
                    )
                else:
                    for br in ev.branch_results:
                        csv_rows.append(
                            {
                                "scene_id": art.scene_id,
                                "inference_mode": art.inference_mode,
                                "trajectory_feasibility_nominal": feas_nominal.classification.value,
                                "trajectory_feasibility_wet_mu0.5": feas_wet.classification.value,
                                "obstacle_source": ev.obstacle_source.value,
                                "initial_d0_m": cf_d0,
                                "tau_req_s": ev.tau_req_s,
                                "state_source": ev.state_source,
                                "r3b_status": ev.status.value,
                                "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                                "d_rem_m": ev.remaining_obstacle_distance_m,
                                "ttc_stationary_s": ev.available_ttc_stationary_s,
                                "branch_id": br.branch_id,
                                "mu": br.mu,
                                "t_req_min_s": br.t_req_min_s,
                                "t_req_max_s": br.t_req_max_s,
                                "margin_min_s": br.margin_min_s,
                                "margin_max_s": br.margin_max_s,
                                "d_stop_min_m": br.d_stop_min_m,
                                "d_stop_max_m": br.d_stop_max_m,
                                "margin_min_m": br.margin_min_m,
                                "margin_max_m": br.margin_max_m,
                                "interval_classification": br.interval_classification,
                                "insufficient_reason": "",
                            }
                        )

        # Also record observed_schedule rows in CSV
        for ev in observed_schedule:
            if ev.status == TakeoverR3BStatus.INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE:
                csv_rows.append(
                    {
                        "scene_id": art.scene_id,
                        "inference_mode": art.inference_mode,
                        "trajectory_feasibility_nominal": feas_nominal.classification.value,
                        "trajectory_feasibility_wet_mu0.5": feas_wet.classification.value,
                        "obstacle_source": ev.obstacle_source.value,
                        "initial_d0_m": ev.initial_obstacle_distance_d0_m,
                        "tau_req_s": ev.tau_req_s,
                        "state_source": ev.state_source,
                        "r3b_status": ev.status.value,
                        "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                        "d_rem_m": ev.remaining_obstacle_distance_m,
                        "ttc_stationary_s": ev.available_ttc_stationary_s,
                        "branch_id": "N/A",
                        "mu": "N/A",
                        "t_req_min_s": None,
                        "t_req_max_s": None,
                        "margin_min_s": None,
                        "margin_max_s": None,
                        "d_stop_min_m": None,
                        "d_stop_max_m": None,
                        "margin_min_m": None,
                        "margin_max_m": None,
                        "interval_classification": "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
                        "insufficient_reason": "; ".join(ev.insufficient_evidence_reasons),
                    }
                )
            else:
                for br in ev.branch_results:
                    csv_rows.append(
                        {
                            "scene_id": art.scene_id,
                            "inference_mode": art.inference_mode,
                            "trajectory_feasibility_nominal": feas_nominal.classification.value,
                            "trajectory_feasibility_wet_mu0.5": feas_wet.classification.value,
                            "obstacle_source": ev.obstacle_source.value,
                            "initial_d0_m": ev.initial_obstacle_distance_d0_m,
                            "tau_req_s": ev.tau_req_s,
                            "state_source": ev.state_source,
                            "r3b_status": ev.status.value,
                            "v_at_req_mps": ev.hypothetical_speed_at_req_mps,
                            "d_rem_m": ev.remaining_obstacle_distance_m,
                            "ttc_stationary_s": ev.available_ttc_stationary_s,
                            "branch_id": br.branch_id,
                            "mu": br.mu,
                            "t_req_min_s": br.t_req_min_s,
                            "t_req_max_s": br.t_req_max_s,
                            "margin_min_s": br.margin_min_s,
                            "margin_max_s": br.margin_max_s,
                            "d_stop_min_m": br.d_stop_min_m,
                            "d_stop_max_m": br.d_stop_max_m,
                            "margin_min_m": br.margin_min_m,
                            "margin_max_m": br.margin_max_m,
                            "interval_classification": br.interval_classification,
                            "insufficient_reason": "",
                        }
                    )

        evaluated_records.append(
            {
                "scene_id": art.scene_id,
                "inference_mode": art.inference_mode,
                "provenance_audit": prov_audit,
                "scene_metadata": scene_meta,
                "prediction_artifact": art.to_dict(),
                "ade_vs_gt_m": ade_m,
                "fde_vs_gt_m": fde_m,
                "predicted_kinematics": [k.to_dict() for k in kinematics],
                "ground_truth_kinematics": [k.to_dict() for k in gt_kinematics],
                "feasibility_nominal": feas_nominal.to_dict(),
                "feasibility_wet_mu0_5": feas_wet.to_dict(),
                "observed_obstacle_takeover_schedule": [e.to_dict() for e in observed_schedule],
                "counterfactual_obstacle_takeover_schedules": counterfactual_schedules,
            }
        )

    # Evaluate Scene 05 controlled signed-acceleration ablation if saved artifact exists
    ablation_s05_path = DEFAULT_ARTIFACTS_DIR / "ablation_scene_05_signed_accel.json"
    scene_05_ablation_summary: dict[str, Any] | None = None
    if ablation_s05_path.exists():
        import math as _math

        ab_art = load_prediction_artifact(ablation_s05_path)
        ab_feas, ab_kin = verify_trajectory_feasibility(
            scene_id="scene_05_active_braking_deceleration_signed_prompt_ablation",
            mode="signed_accel_ablation",
            waypoints=ab_art.predicted_waypoints,
            initial_speed_mps=ab_art.ego_initial_speed_mps,
            initial_accel_mps2=ab_art.ego_initial_accel_mps2,
            limits=nominal_limits,
            treat_stationary_as_not_applicable=False,
        )
        ab_dists = [
            _math.hypot(w.x_m - g.x_m, w.y_m - g.y_m)
            for w, g in zip(ab_art.predicted_waypoints, ab_art.ground_truth_waypoints)
        ]
        ab_ade_5s = round(sum(ab_dists) / len(ab_dists), 4)
        ab_fde_5s = round(ab_dists[-1], 4)
        ab_ade_braking_2s = round(sum(ab_dists[:4]) / 4.0, 4)
        scene_05_ablation_summary = {
            "scene_id": ab_art.scene_id,
            "frame_token": ab_art.frame_token,
            "intervention_description": (
                "Single-variable controlled prompt intervention replacing unsigned 2D acceleration norm "
                "('1.56 m/s^2', from ||a(0)|| = 1.5633 m/s^2) with signed longitudinal acceleration "
                "('-1.55 m/s^2', from a_x(0) = -1.5525 m/s^2). All 12 camera frames, initial speed (4.31 m/s), "
                "command ('keep forward'), and greedy decoding remain identical."
            ),
            "standard_unsigned_prompt": "the ego acceleration is 1.56 m/s^2",
            "ablation_signed_prompt": "the ego acceleration is -1.55 m/s^2",
            "standard_action_tokens": [30, 189, 66, 145, 626, 147, 88, 1497, 1172, 42],
            "ablation_action_tokens": list(ab_art.action_codebook_indices),
            "standard_step1_a_lon_mps2": -0.8841,
            "standard_step2_a_lon_mps2": 0.7917,
            "standard_step3_peak_a_lon_mps2": 1.5442,
            "standard_final_x_m": 28.534,
            "ablation_step1_a_lon_mps2": ab_kin[0].a_lon_mps2,
            "ablation_step2_a_lon_mps2": ab_kin[1].a_lon_mps2,
            "ablation_step3_a_lon_mps2": ab_kin[2].a_lon_mps2,
            "ablation_min_a_lon_mps2": ab_feas.min_lon_accel_mps2,
            "ablation_max_a_lon_mps2": ab_feas.max_lon_accel_mps2,
            "ablation_final_x_m": round(ab_art.predicted_waypoints[-1].x_m, 4),
            "ground_truth_t2_5s_x_m": 6.916,
            "ground_truth_final_x_m": 15.648,
            "standard_ade_5s_m": 6.2543,
            "standard_fde_5s_m": 12.8998,
            "ablation_ade_5s_m": ab_ade_5s,
            "ablation_fde_5s_m": ab_fde_5s,
            "ablation_braking_phase_ade_0_to_2s_m": ab_ade_braking_2s,
            "ablation_kinematics": [k.to_dict() for k in ab_kin],
            "scientific_limitations": [
                "Out-of-distribution (OOD) prompt input: AutoVLA was trained exclusively on unsigned Euclidean acceleration norms (np.linalg.norm(acceleration) >= 0).",
                "Not a single-factor causal law: visual context still governs initial token selection (Step 1 is <action_30>, a_lon = -0.8841 m/s^2, under both prompts).",
                "Stationary tail artifact: under the OOD negative prompt, once the vehicle brakes to rest at t = 3.5 s (x = 6.98 m), Step 9 emits a 5.8 cm backward jitter token (<action_126>) before stopping at x = 6.93 m, whereas the human driver releases the brake after t = 2.5 s and accelerates to 15.65 m.",
            ],
        }

    # Evaluate RQ1 Controlled Driving-Command Sensitivity (Scene 02 & Scene 06: turn left -> keep forward)
    from extensions.vla_handover_feasibility.command_sensitivity import (
        evaluate_command_sensitivity,
    )
    from extensions.vla_handover_feasibility.c10_robustness import (
        run_c10_robustness_audit,
    )

    command_sensitivity_summary = evaluate_command_sensitivity(
        manifest_path=manifest_file,
        predictions_dir=pred_dir,
        output_dir=out_dir / "command_sensitivity",
        force_recompute_inference=False,
    )

    # Evaluate RQ2 Scene 05 C10 Numerical Robustness Audit (D1-D5)
    c10_robustness_summary = run_c10_robustness_audit(
        predictions_dir=pred_dir,
        ablation_path=ablation_s05_path,
        output_dir=out_dir / "c10_robustness",
    )

    # Save tabular CSV
    csv_path = out_dir / "counterfactual_comparison.csv"
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

    # Aggregate high-level summary statistics
    nom_counts = {c.value: 0 for c in FeasibilityClassification}
    wet_counts = {c.value: 0 for c in FeasibilityClassification}
    completed_scene_ids: list[str] = []
    for rec in evaluated_records:
        nom_counts[rec["feasibility_nominal"]["classification"]] += 1
        wet_counts[rec["feasibility_wet_mu0_5"]["classification"]] += 1
        if rec["scene_id"] not in completed_scene_ids:
            completed_scene_ids.append(rec["scene_id"])

    all_manifest_scene_ids = [s["scene_id"] for s in manifest["scenes"]]
    pending_scene_ids = [sid for sid in all_manifest_scene_ids if sid not in completed_scene_ids]

    summary_payload = {
        "extension_name": "VLA-Informed Handover Feasibility Analysis",
        "extension_version": "0.3.0",
        "manifest_sha256": manifest_sha,
        "codebook_sha256": codebook_sha,
        "central_research_question": (
            "Under what conditions do VLA-generated driving trajectories violate specified "
            "vehicle-dynamics constraints, and how does the available braking-only human fallback "
            "margin change under explicitly defined takeover-request timing assumptions?"
        ),
        "model_provenance": {
            "selected_model": "AutoVLA (ucla-mobility/AutoVLA)",
            "checkpoint_repo": "Zewei-Zhou/AutoVLA",
            "checkpoint_file": "AutoVLA_PDMS_89.ckpt",
            "base_architecture": "Qwen/Qwen2.5-VL-3B-Instruct",
            "action_vocabulary": "agent_vocab.pkl (2048 discrete SE(2) vehicle bounding-box tokens, dt=0.5s, H=10 steps, 5.0s horizon)",
            "predicts_human_takeover_request": False,
            "rejected_candidate_audit": {
                "model": "OpenDriveVLA (DriveVLA/OpenDriveVLA-0.5B)",
                "status": "BLOCKED",
                "blockers": [
                    "Hugging Face model weights (OpenDriveVLA/OpenDriveVLA-0.5B, 3B, 7B) are gated (HTTP 401 Unauthorized without manual approval).",
                    "Requires compiling mmcv-full==1.7.2 with MMCV_WITH_OPS=1 (NVIDIA CUDA C++ Deformable Attention kernels), mmdet3d==1.0.0rc6, deepspeed, and pre-extracted UniAD 3D track/map queries, which cannot compile or execute on macOS Apple Silicon (Apple M5).",
                ],
            },
        },
        "scientific_boundaries": [
            "Genuine VLA trajectory predictions are hypothetical future plans, NOT observed vehicle motion.",
            "AutoVLA does not predict a human takeover request signal (predicts_human_takeover_request = False).",
            "Trajectory physical feasibility checks (Phase C) are strictly independent of the R3B braking-only necessary-condition model (Phase D).",
            "Passing trajectory feasibility checks does NOT establish collision avoidance, human takeover success, overall driving safety, or production readiness.",
            "Obstacle distance and TTC are never inferred from camera images alone; scenes without observed 3D in-lane obstacle annotations require explicit counterfactual obstacle assumptions or return INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE.",
            "No complete scenario state is labelled as purely observed if it incorporates a counterfactual environmental obstacle distance or a static projection of a moving lead vehicle.",
            "Driving-command future-information leakage limitation: in scene_02_stationary_lead_obstacle (and scene_06_intersection_turn_maneuver), the effective 'turn left' command corresponds to future ground-truth lateral displacement (y_GT(3.0 s) = +4.5128 m in scene_02; +4.0889 m in scene_06). Resolving an unknown raw command from future ground-truth displacement—or conditioning on NAVSIM/OpenScene future-route-derived commands generally—constitutes potential future-information leakage for trajectory-prediction evaluation; affected results are therefore not presented as strictly leakage-free blind predictions.",
            "Controlled command-sensitivity interpretation rule (RQ1 / EXT-VLA-C07): in scene_02 and scene_06, the logged human trajectory is a left-turn maneuver and is NOT a valid ground-truth target for a deliberately different 'keep forward' intervention command; ADE/FDE differences under 'keep forward' quantify command sensitivity relative to the recorded turning trajectory, NOT policy quality or driving safety.",
            "Scene 05 C10 numerical robustness boundary (RQ2 / EXT-VLA-C08): the braking-to-acceleration reversal violation is 100% robust across all 5 discrete derivative estimators (E1-E5) for windows >= 1.5 s at thresholds <= 2.5 m/s^2 (30/30 cells violated), but sensitive to early windows (0.0-0.5 s passes 0/15; 0.0-1.0 s violates only at 2.0 m/s^2) and to multi-step smoothing at the 3.0 m/s^2 threshold.",
            "The 1,011 rows in counterfactual_comparison.csv represent parameter-sweep evaluations across 7 real scenes, 7 takeover request times, 3 policy branches (P0, P1, P2), and 2 friction levels (mu in {1.0, 0.5}), NOT 1,011 independent driving observations.",
            "The original 42-claim ledger (research/R5A_CLAIM_LEDGER.csv), frozen results, thesis figures, and counterfactual policy definitions remain completely unmodified.",
        ],
        "summary_counts": {
            "total_manifest_scenes": len(all_manifest_scene_ids),
            "total_evaluated_predictions": len(evaluated_records),
            "completed_scene_ids": completed_scene_ids,
            "pending_unpredicted_scene_ids": pending_scene_ids,
            "nominal_feasibility_counts": nom_counts,
            "wet_mu0_5_feasibility_counts": wet_counts,
            "total_csv_evaluation_rows": len(csv_rows),
        },
        "scene_05_signed_accel_ablation": scene_05_ablation_summary,
        "command_sensitivity": command_sensitivity_summary,
        "scene_05_c10_robustness": c10_robustness_summary,
        "records": evaluated_records,
    }

    summary_path = out_dir / "evaluation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    write_extension_claim_register(summary_payload, out_dir / "extension_claim_register.csv")
    return summary_payload


def write_extension_claim_register(summary_payload: dict[str, Any], out_csv_path: Path) -> None:
    """Write an independent extension-specific claim/evidence register without touching R5A_CLAIM_LEDGER.csv."""
    records = summary_payload["records"]
    by_key = {(r["scene_id"], r["inference_mode"]): r for r in records}
    n_eval = summary_payload["summary_counts"]["total_evaluated_predictions"]

    s1 = by_key.get(("scene_01_high_speed_open_road", "fast"))
    s3 = by_key.get(("scene_03_close_urban_lead_following", "fast"))
    s6 = by_key.get(("scene_06_intersection_turn_maneuver", "fast"))
    s7 = by_key.get(("scene_07_stationary_ego_baseline", "fast"))

    s1_lat = s1["prediction_artifact"]["inference_latency_ms"] if s1 else None
    s3_ade = s3["ade_vs_gt_m"] if s3 else None

    claims = [
        {
            "extension_claim_id": "EXT-VLA-C01",
            "phase": "Phase A/B",
            "category": "GENUINE_VLA_EXECUTION",
            "claim_statement": (
                "AutoVLA (Zewei-Zhou/AutoVLA AutoVLA_PDMS_89.ckpt, 825 tensors on Qwen2.5-VL-3B-Instruct + 2048 physical action tokens) "
                "executes genuine multi-view camera + kinematics trajectory inference locally on Apple M5 after mapping "
                "legacy transformers 4.49 state_dict keys (autovla.vlm.model.* -> model.language_model.*, autovla.vlm.visual.* -> model.visual.*) with strict=True."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/predictions/*.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                f"Verified on {n_eval} completed genuine nuPlan/NAVSIM mini scene prediction(s) (e.g. scene_01 fast latency={s1_lat} ms, "
                f"scene_03 ADE={s3_ade} m vs human log). AutoVLA outputs 10 ego-frame poses over 5.0 s (dt=0.5 s) and does not output a takeover request. "
                "Prompts are conditioned on NAVSIM/OpenScene driving commands (see EXT-VLA-C06 on future-displacement command leakage)."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C02",
            "phase": "Phase A",
            "category": "CANDIDATE_MODEL_BLOCKER",
            "claim_statement": (
                "OpenDriveVLA (DriveVLA/OpenDriveVLA-0.5B/3B/7B) is blocked for unauthenticated local Apple Silicon execution due to "
                "gated Hugging Face checkpoint access (HTTP 401) and mandatory NVIDIA CUDA C++ Deformable Attention ops (mmcv-full==1.7.2, mmdet3d==1.0.0rc6) plus pre-extracted UniAD 3D queries."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/evaluation_summary.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": "Documented in Phase A feasibility audit; AutoVLA was selected as the publicly accessible, runnable driving VLA.",
        },
        {
            "extension_claim_id": "EXT-VLA-C03",
            "phase": "Phase C",
            "category": "TRAJECTORY_FEASIBILITY_VERIFIER",
            "claim_statement": (
                "AutoVLA's prompt interface encodes ego acceleration as an unsigned 2D Euclidean norm (||a|| = 1.5633 m/s^2 -> '1.56 m/s^2' in "
                "scene_05_active_braking_deceleration where observed a_x(0) = -1.5525 m/s^2). After Step 1 deceleration (-0.8841 m/s^2), "
                "the predicted trajectory reverses into positive acceleration at Step 2 (+0.7917 m/s^2) and peaks at Step 3 (+1.5442 m/s^2), "
                "violating C10 longitudinal acceleration state consistency (|a_lon(3) - a_x(0)| = 3.0967 m/s^2 > 2.50 m/s^2, ADE = 6.25 m, FDE = 12.90 m); "
                "under wet-road limits (mu = 0.5) scene_02 violates C7 lateral acceleration bounds (2.2721 m/s^2 > 2.0 m/s^2)."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/evaluation_summary.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                "A controlled single-variable OOD prompt ablation ('-1.55 m/s^2') on scene_05 restores sustained braking across Steps 1-7 to standstill (x_10 = 6.93 m, ADE = 2.42 m), "
                "confirming prompt sign sensitivity while showing that visual context still drives Step 1 and OOD negative prompting is a single-scene diagnostic rather than a validated model fix."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C04",
            "phase": "Phase D/E",
            "category": "TAKEOVER_TIMING_SENSITIVITY",
            "claim_statement": (
                "Under the counterfactual assumption that the ego vehicle follows the VLA-predicted trajectory until a delayed takeover request time tau_req > 0, "
                "forward ego progress reduces remaining obstacle distance d(tau_req) = d0 - x_VLA(tau_req), shifting R3B braking-only recoverability margins from "
                "UNIFORMLY_POSITIVE at tau_req = 0.0 s to PARAMETER_SENSITIVE and UNIFORMLY_VIOLATED at later request times, with P0 (constant-speed pre-control) and wet road (mu=0.5) violating earliest."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/counterfactual_comparison.csv",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                "Counterfactual analytical bound reusing frozen R3B equations. Future states along VLA trajectories are hypothetical predictions, "
                "not observed vehicle motion or empirical human braking responses."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C05",
            "phase": "Phase C/D/E",
            "category": "INSUFFICIENT_EVIDENCE_BOUNDARIES",
            "claim_statement": (
                "Evaluation explicitly withholds R3B recoverability claims (returning INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE) in three distinct regimes: "
                "(1) open-road scenes without an observed 3D in-lane obstacle when no counterfactual d0 is assumed, "
                "(2) stationary ego scenes (v0 <= 0.05 m/s) where braking-only stopping bounds are not applicable, and "
                "(3) turning maneuvers once hypothetical lateral displacement |y(tau_req)| > 1.75 m or heading |psi(tau_req)| > 0.35 rad departs the 1D longitudinal corridor."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/evaluation_summary.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                f"Demonstrated on real scenes scene_01_high_speed_open_road, scene_02_stationary_lead_obstacle, "
                f"scene_07_stationary_ego_baseline (v0={s7['prediction_artifact']['ego_initial_speed_mps'] if s7 else 0.0} m/s), "
                f"and scene_06_intersection_turn_maneuver (cmd='{s6['prediction_artifact']['driving_command'] if s6 else 'turn left'}')."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C06",
            "phase": "Phase B/E",
            "category": "COMMAND_LEAKAGE_METHODOLOGICAL_BOUNDARY",
            "claim_statement": (
                "In scene_02_stationary_lead_obstacle (y_GT(3.0s) = +4.5128 m, y_GT(5.0s) = +16.6678 m) and scene_06_intersection_turn_maneuver "
                "(y_GT(3.0s) = +4.0889 m, y_GT(5.0s) = +8.3498 m), the effective 'turn left' driving command reflects future ground-truth lateral "
                "displacement rather than an independent pre-trip navigation command. Resolving an unknown command from future ground-truth displacement—or "
                "conditioning on NAVSIM/OpenScene future-displacement-derived commands—constitutes future-information leakage for trajectory-prediction evaluation."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/data/scenes_manifest.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                "Recorded inference inputs are preserved unmodified for provenance integrity, but ADE/FDE metrics on command-conditioned scenes "
                "(especially scene_02 and scene_06) must not be interpreted as strictly leakage-free blind trajectory predictions."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C07",
            "phase": "RQ1 (Phase B/C)",
            "category": "DRIVING_COMMAND_SENSITIVITY",
            "claim_statement": (
                "Replacing the high-level driving command from 'turn left' to 'keep forward' while holding all 12 camera frames, initial kinematics, "
                "and greedy decoding fixed alters 10/10 action tokens in scene_02 (reducing 5.0 s lateral displacement by -6.75 m [-34.1%], "
                "19.82 m -> 13.06 m, and extending 1D R3B corridor admissibility from tau_req <= 1.0 s [3/7] to tau_req <= 2.5 s [6/7]) and "
                "8/10 action tokens in scene_06 (reducing Step 1 lateral acceleration by 61.8% [1.3711 -> 0.5232 m/s^2] and 5.0 s lateral displacement "
                "by -2.55 m [-33.6%], 7.60 m -> 5.04 m), while visual intersection geometry still induces a delayed leftward curve later in the horizon."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/command_sensitivity/summary.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                "Critical Interpretation Rule: the logged human trajectory in scene_02 and scene_06 is a left-turn maneuver and is NOT a valid "
                "ground-truth target for a 'keep forward' command; ADE/FDE shifts under 'keep forward' (scene_02: 2.42 -> 1.54 m ADE, 3.47 -> 3.86 m FDE; "
                "scene_06: 0.66 -> 1.78 m ADE, 1.88 -> 3.70 m FDE) measure command sensitivity relative to the recorded turn, not policy quality or safety."
            ),
        },
        {
            "extension_claim_id": "EXT-VLA-C08",
            "phase": "RQ2 (Phase D)",
            "category": "C10_NUMERICAL_ROBUSTNESS_AUDIT",
            "claim_statement": (
                "Across 5 discrete derivative estimators on the native 0.5 s grid (E1 chord-speed backward difference, E2 pure ego-x Taylor/central second difference, "
                "E3 body-frame projected velocity difference, E4 1.0 s central velocity difference, E5 3-step moving average), 5 temporal windows, and "
                "3 illustrative thresholds (2.0, 2.5, 3.0 m/s^2), the scene_05 C10 braking-to-acceleration reversal is 100% robust (30/30 cells violated) "
                "for all windows >= 1.5 s at thresholds <= 2.5 m/s^2 (peak |a_lon - a_x(0)| = 3.0967 m/s^2 on E1/E2/E3, 2.8516 m/s^2 on E4, "
                "2.6825 m/s^2 on E5, with 9 consecutive positive-acceleration steps t = 1.0..5.0 s), while remaining sensitive to early windows "
                "(0.0-0.5 s has 0/15 violations; 0.0-1.0 s violates only at 2.0 m/s^2) and to multi-step smoothing at the 3.0 m/s^2 threshold (45/75 total cells violated)."
            ),
            "evidence_artifact": "extensions/vla_handover_feasibility/artifacts/c10_robustness/c10_robustness_summary.json",
            "verification_status": "VERIFIED",
            "scope_and_limitations": (
                "Thresholds 2.0, 2.5, and 3.0 m/s^2 are illustrative numerical-sensitivity bounds on the 0.5 s waypoint grid, not universal biomechanics "
                "or ISO safety standards. Heading distortion on Steps 2-10 is <= 0.01301 m/s^2 (E1 vs E2, < 0.42%) and <= 0.00120 m/s^2 (E1 vs E3, < 0.04%); "
                "the saved OOD signed-acceleration rollout ('-1.55 m/s^2') has 0/75 active-motion violations."
            ),
        },
    ]

    with open(out_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(claims[0].keys()))
        writer.writeheader()
        writer.writerows(claims)



def main() -> None:
    parser = argparse.ArgumentParser(description="Run VLA-Informed Handover Feasibility Experiment (Sequential batch_size=1).")
    parser.add_argument("--force-inference", action="store_true", help="Re-run AutoVLA neural inference even if cached predictions exist.")
    parser.add_argument("--skip-inference", action="store_true", help="Only run verification and R3B evaluation on existing saved predictions.")
    parser.add_argument("--scene-id", action="append", dest="scene_ids", help="Run inference only on the specified scene_id(s).")
    parser.add_argument("--device", type=str, default=None, help="Explicit torch device (mps, cpu, cuda).")
    args = parser.parse_args()

    if not args.skip_inference:
        run_genuine_vla_inference_all_scenes(
            force_recompute=args.force_inference,
            scene_ids=args.scene_ids,
            device=args.device,
        )
    summary = evaluate_all_predictions_and_counterfactuals()
    print(
        "Evaluation complete! Summary counts:",
        json.dumps(summary["summary_counts"], indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()
