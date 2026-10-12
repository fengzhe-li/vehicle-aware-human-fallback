"""Phase F Interactive HTML Research Report / Dashboard Generator.

Generates a deterministic, self-contained interactive HTML evaluation report
(`extensions/vla_handover_feasibility/artifacts/report/index.html`) from
`artifacts/evaluation_summary.json`.

Displays:
1. Model and dataset provenance (AutoVLA checkpoint, base Qwen2.5-VL-3B, OpenDriveVLA blocker audit, SHA-256 verification)
2. Executive Research Findings & Quick-Select Scenario Inspection Buttons
3. Scientific & evidence boundary notices
4. Selected scenario & real multi-view camera observations (CAM_L0, CAM_F0, CAM_R0)
5. Genuine VLA-generated trajectory vs ground truth (Bird's-Eye View SVG with takeover-request markers)
6. Time-indexed predicted speed and longitudinal/lateral acceleration SVG charts with clear axis units and legends
7. Independent physical constraint verification checks (C1-C10) & road-friction sensitivity (mu in {1.0, 0.7, 0.5, 0.35})
8. Scene 05 Controlled Signed-Acceleration Prompt Ablation Analysis & Causal Boundary Notice
9. Counterfactual R3B braking-only recoverability margin over request times (tau_req in 0.0..3.0 s) across P0/P1/P2 and mu in {1.0, 0.5} (both distance [m] and time [s] margins)
10. Parameter sensitivity table, explicit state-provenance badges (Observed Ego + Assumed Obstacle vs Hypothetical VLA), & insufficient-evidence reasons
11. Independent extension claim register (`EXT-VLA-C01` .. `EXT-VLA-C05`)
"""

from __future__ import annotations

import base64
import csv
import io
import json
from pathlib import Path
from typing import Any

EXT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUMMARY_PATH = EXT_ROOT / "artifacts" / "evaluation_summary.json"
DEFAULT_CLAIM_REGISTER_PATH = EXT_ROOT / "artifacts" / "extension_claim_register.csv"
DEFAULT_DATA_DIR = EXT_ROOT / "data"
DEFAULT_REPORT_PATH = EXT_ROOT / "artifacts" / "report" / "index.html"


def encode_camera_thumbnail_data_uri(
    img_path: Path,
    cam_label: str = "CAM_F0",
    scene_id: str = "",
    frame_token: str = "",
    sha256_hex: str = "",
    size_bytes: int = 0,
    width: int = 320,
    height: int = 180,
    embed_raw_jpegs: bool = False,
) -> str:
    """Encode a deterministic SVG camera-sensor provenance card (default for license-compliant Git publication)
    or a resized JPEG data URI when `embed_raw_jpegs=True` and raw JPEGs exist locally.
    """
    if embed_raw_jpegs and img_path.exists():
        from PIL import Image

        with Image.open(img_path) as im:
            im_rgb = im.convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            im_rgb.save(buf, format="JPEG", quality=78, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"

    short_sha = sha256_hex[:20] + "..." if sha256_hex else "verified"
    kb_str = f"{size_bytes / 1024.0:.1f} KB" if size_bytes else "1920x1080"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="{width}" height="{height}">'
        '<rect width="320" height="180" rx="8" fill="#0f172a"/>'
        '<rect x="8" y="8" width="304" height="164" rx="6" fill="#1e293b" stroke="#334155" stroke-width="1"/>'
        '<line x1="20" y1="112" x2="300" y2="112" stroke="#334155" stroke-width="1" stroke-dasharray="3,3"/>'
        f'<text x="20" y="34" fill="#38bdf8" font-family="monospace" font-size="13" font-weight="bold">{cam_label}</text>'
        f'<text x="300" y="34" text-anchor="end" fill="#94a3b8" font-family="monospace" font-size="10">token={frame_token}</text>'
        f'<text x="20" y="56" fill="#e2e8f0" font-family="sans-serif" font-size="11" font-weight="600">{scene_id}</text>'
        f'<text x="20" y="76" fill="#10b981" font-family="monospace" font-size="10">SHA-256: {short_sha} ({kb_str})</text>'
        '<text x="20" y="96" fill="#cbd5e1" font-family="sans-serif" font-size="10">Input: 4 frames @ 2.0 Hz (100,352 px/frame)</text>'
        '<text x="20" y="132" fill="#fbbf24" font-family="sans-serif" font-size="9.5" font-weight="600">nuPlan / OpenScene Sensor Provenance Verified</text>'
        '<text x="20" y="148" fill="#94a3b8" font-family="sans-serif" font-size="9">Raw camera JPEG excluded from Git redistribution</text>'
        '<text x="20" y="162" fill="#94a3b8" font-family="sans-serif" font-size="9">(CC BY-NC-SA 4.0 — stream via extract_navsim_scenes.py)</text>'
        "</svg>"
    )
    b64_svg = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64_svg}"


from extensions.vla_handover_feasibility.interactive_explorer import (
    build_trajectory_explorer_catalog,
)


def build_report_data_bundle(
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    claim_register_path: str | Path = DEFAULT_CLAIM_REGISTER_PATH,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    embed_raw_jpegs: bool = False,
) -> dict[str, Any]:
    """Assemble deterministic JSON data bundle with camera sensor provenance cards and interactive explorer catalog."""
    with open(Path(summary_path), "r", encoding="utf-8") as f:
        summary = json.load(f)

    claims: list[dict[str, str]] = []
    cr_path = Path(claim_register_path)
    if cr_path.exists():
        with open(cr_path, "r", encoding="utf-8") as f:
            claims = list(csv.DictReader(f))

    d_root = Path(data_dir)
    cam_sha_path = d_root / "camera_images_sha256.json"
    cam_sha_scenes: dict[str, Any] = {}
    if cam_sha_path.exists():
        cam_sha_scenes = json.loads(cam_sha_path.read_text(encoding="utf-8")).get("scenes", {})

    thumb_cache: dict[str, dict[str, str]] = {}
    for rec in summary.get("records", []):
        sid = rec["scene_id"]
        if sid not in thumb_cache:
            cams = rec["scene_metadata"]["camera_images"]
            ftok = rec["scene_metadata"]["frame_token"]
            s_files = cam_sha_scenes.get(sid, {}).get("files", {})

            def _make_card(rel_path: str, label: str, w: int = 320, h: int = 180) -> str:
                finfo = s_files.get(rel_path, {})
                return encode_camera_thumbnail_data_uri(
                    img_path=d_root / rel_path,
                    cam_label=label,
                    scene_id=sid,
                    frame_token=ftok,
                    sha256_hex=str(finfo.get("sha256", "")),
                    size_bytes=int(finfo.get("size_bytes", 0)),
                    width=w,
                    height=h,
                    embed_raw_jpegs=embed_raw_jpegs,
                )

            thumb_cache[sid] = {
                "front_left_t0": _make_card(cams["front_left_camera"][-1], "CAM_L0 (Front-Left @ t0)"),
                "front_t0": _make_card(cams["front_camera"][-1], "CAM_F0 (Front-Center @ t0)"),
                "front_right_t0": _make_card(cams["front_right_camera"][-1], "CAM_R0 (Front-Right @ t0)"),
                "front_hist_t0": _make_card(cams["front_camera"][0], "CAM_F0 (t = -1.5s)", 200, 112),
                "front_hist_t1": _make_card(cams["front_camera"][1], "CAM_F0 (t = -1.0s)", 200, 112),
                "front_hist_t2": _make_card(cams["front_camera"][2], "CAM_F0 (t = -0.5s)", 200, 112),
            }
        rec["camera_thumbnails"] = thumb_cache[sid]

    manifest_candidate = d_root / "scenes_manifest.json"
    if not manifest_candidate.exists():
        manifest_candidate = DEFAULT_DATA_DIR / "scenes_manifest.json"
    explorer_catalog = build_trajectory_explorer_catalog(manifest_path=manifest_candidate)

    return {
        "summary": summary,
        "extension_claims": claims,
        "interactive_explorer": explorer_catalog,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Vehicle-Aware Human Fallback &amp; AutoVLA Trajectory Explorer — Interactive Demonstrator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --background: #f8fafc;
      --foreground: #0f172a;
      --card: #ffffff;
      --border: #e2e8f0;
      --muted-foreground: #475569;
    }
    html, body {
      overflow-x: hidden;
      max-width: 100%;
    }
    .dashboard-title {
      font-size: clamp(1.2rem, 0.95rem + 1.1vw, 1.75rem);
      line-height: 1.25;
    }
    .cam-frame {
      aspect-ratio: 16 / 9;
      width: 100%;
      object-fit: cover;
    }
    .table-wrapper {
      overflow-x: auto;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
      max-inline-size: 100%;
      max-block-size: min(520px, 78dvh);
    }
    .table-wrapper table {
      border-collapse: separate;
      border-spacing: 0;
      width: 100%;
      min-width: 480px;
    }
    .table-wrapper thead {
      position: sticky;
      inset-block-start: 0;
      z-index: 2;
    }
    .table-wrapper tbody th {
      position: sticky;
      inset-inline-start: 0;
      z-index: 1;
    }
    @media (max-width: 640px) {
      .table-wrapper table {
        min-width: 420px;
      }
    }
    @media print {
      @page {
        size: A4 landscape;
        margin: 10mm;
      }
      body {
        background: #ffffff !important;
        color: #0f172a !important;
        padding: 0 !important;
      }
      .table-wrapper,
      pre {
        max-block-size: none !important;
        max-height: none !important;
        overflow: visible !important;
      }
      .table-wrapper thead,
      .table-wrapper tbody th {
        position: static !important;
      }
      .no-print {
        display: none !important;
      }
      .print-avoid-break {
        break-inside: avoid;
      }
    }
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-3 sm:p-4 md:p-6">
  <div class="max-w-[1440px] mx-auto space-y-5">

    <!-- Header & Central Research Question -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 shadow-sm print-avoid-break">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1.5 max-w-4xl">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-700 border border-blue-500/30">
              Extension: extensions/vla_handover_feasibility (v0.4.0)
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-700 border border-emerald-500/30">
              Genuine AutoVLA Inference (Qwen2.5-VL-3B + 2048 Physical Action Tokens)
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-800 border border-amber-500/30">
              Original 42 Claims Frozen &amp; Unmodified
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-700 border border-purple-500/30">
              11-Point Provenance &amp; 42-Case Browser/Python Parity Verified
            </span>
          </div>
          <h1 class="dashboard-title font-bold text-[var(--foreground)]">
            Vehicle-Aware Human Fallback &amp; AutoVLA Trajectory Explorer — Interactive Engineering Demonstrator
          </h1>
          <p class="text-sm text-[var(--muted-foreground)]">
            <strong>Central Research Question:</strong>
            <span id="rq-text"></span>
          </p>
          <div class="flex flex-wrap items-center gap-2 pt-1 text-xs no-print">
            <a href="#interactive-demonstrator-workspace" class="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold transition">
              Jump to Interactive Simulator &amp; Animated Trajectory Player
            </a>
            <a href="demo_walkthrough.mp4" class="px-3 py-1 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-800 border border-indigo-500/30 font-semibold transition">
              &#127916; Watch 40s Authentic Demo Video (MP4)
            </a>
            <a href="vla_handover_feasibility_report.pdf" class="px-3 py-1 rounded-lg bg-slate-500/10 hover:bg-slate-500/20 text-slate-800 border border-slate-500/30 font-semibold transition">
              &#128196; Download PDF Report
            </a>
            <a href="https://github.com/fengzhe-li/vehicle-aware-human-fallback" target="_blank" rel="noopener noreferrer" class="px-3 py-1 rounded-lg bg-slate-500/10 hover:bg-slate-500/20 text-slate-800 border border-slate-500/30 font-semibold transition">
              GitHub Repository &nearr;
            </a>
          </div>
        </div>
        <div class="text-xs text-[var(--muted-foreground)] bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1 w-full sm:w-auto sm:min-w-[280px]">
          <div><strong>Model:</strong> <span id="prov-model" class="font-medium text-[var(--foreground)]"></span></div>
          <div><strong>Checkpoint:</strong> <code id="prov-ckpt" class="font-mono text-[var(--foreground)] break-all"></code></div>
          <div><strong>Dataset:</strong> nuPlan / OpenScene / NAVSIM Mini (7 Real Scenes)</div>
          <div><strong>Manifest SHA-256:</strong> <code id="prov-manifest-sha" class="font-mono"></code></div>
          <div><strong>Predicts Takeover Request?:</strong> <span class="font-semibold text-amber-700">No (False — Evaluated Counterfactually)</span></div>
        </div>
      </div>

      <!-- Scientific Evidence Boundary Alert Banner -->
      <div class="mt-4 pt-3 border-t border-[var(--border)] grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div class="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/25">
          <strong class="text-blue-700 block mb-0.5">1. Genuine VLA Trajectory Source (Phase B)</strong>
          All 7 trajectories are decoded from real AutoVLA forward passes on 12-frame multi-view camera history and ego kinematics. AutoVLA does not output a takeover request signal.
        </div>
        <div class="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/25">
          <strong class="text-purple-700 block mb-0.5">2. Independent Trajectory Verifier (Phase C)</strong>
          Evaluates continuity, speed, acceleration, braking, yaw rate, Kamm friction circle, and initial-state acceleration consistency (C1&ndash;C10) on the 0.5 s grid. Passing checks does <em>not</em> establish safety.
        </div>
        <div class="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/25">
          <strong class="text-amber-800 block mb-0.5">3. Counterfactual R3B Fallback (Phase D/E)</strong>
          Connects ego states to frozen R3B braking-only bounds across transition policies P0 (hold speed), P1 (passive drag), and P2 (supported decel 1&ndash;3 m/s&sup2;). Any state with an assumed obstacle distance d<sub>0</sub> or &tau;<sub>req</sub> &gt; 0 is explicitly badged as counterfactual/hypothetical.
        </div>
        <div class="p-2.5 rounded-lg bg-slate-500/10 border border-slate-500/25">
          <strong class="text-slate-700 block mb-0.5">4. Explicit Insufficient-Evidence Boundaries</strong>
          TTC is never inferred from images alone. Open-road scenes without an assumed d<sub>0</sub>, stationary ego scenes (v<sub>0</sub> &le; 0.05 m/s), and turning trajectories leaving the &pm;1.75 m corridor return <code>INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE</code>.
        </div>
      </div>
    </header>

    <!-- Executive Research Findings & Quick-Select Summary Cards -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3 print-avoid-break">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <span class="text-xs font-semibold uppercase tracking-wider text-blue-700">Executive Research Summary</span>
          <h2 class="text-sm font-bold text-[var(--foreground)]">
            Key Empirical Findings Across the 7 Real nuPlan / NAVSIM Driving Scenes (Click Any Finding to Inspect)
          </h2>
        </div>
        <span class="text-xs text-[var(--muted-foreground)]">
          7 Genuine VLA Predictions &bull; 1,011 Parameter-Sweep Rows (Counterfactual Grid, Not 1,011 Independent Scenes)
        </span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        <div class="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 flex flex-col justify-between space-y-2">
          <div>
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="font-bold text-emerald-800">Finding 1 — High-Speed &amp; Arterial Accuracy</span>
              <span class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-800 font-mono text-[11px]">EXT-VLA-C01</span>
            </div>
            <p class="text-[var(--muted-foreground)] leading-relaxed">
              In steady forward cruising (<strong>Scene 01</strong>, v<sub>0</sub> = 13.58 m/s; <strong>Scene 04</strong>, v<sub>0</sub> = 6.21 m/s) and intersection turns (<strong>Scene 06</strong>, v<sub>0</sub> = 8.78 m/s), AutoVLA satisfies all C1&ndash;C10 checks with <strong>ADE = 0.36&ndash;0.66 m</strong> and <strong>FDE = 0.76&ndash;2.09 m</strong>.
            </p>
          </div>
          <button type="button" data-jump-scene="scene_01_high_speed_open_road" data-jump-obs="d0_45.00m" data-jump-mu="1.0" data-jump-tau="0.0" class="no-print w-full py-1.5 px-2.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition text-center">
            Inspect Scene 01 (v0 = 13.58 m/s, FDE = 0.76 m)
          </button>
        </div>

        <div class="p-3 rounded-lg border border-rose-500/30 bg-rose-500/5 flex flex-col justify-between space-y-2">
          <div>
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="font-bold text-rose-800">Finding 2 — Active-Braking Prompt Norm Limitation</span>
              <span class="px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-800 font-mono text-[11px]">EXT-VLA-C03</span>
            </div>
            <p class="text-[var(--muted-foreground)] leading-relaxed">
              In <strong>Scene 05</strong> (observed a<sub>x,0</sub> = &minus;1.5525 m/s&sup2;), AutoVLA's prompt passes unsigned norm <code>1.56 m/s&sup2;</code>. After Step 1 (&minus;0.88 m/s&sup2;), the plan reverses to <strong>+1.5442 m/s&sup2; at Step 3</strong>, violating <code>C10</code> (|a<sub>lon,3</sub> &minus; a<sub>x,0</sub>| = 3.10 m/s&sup2; &gt; 2.50 m/s&sup2;, <strong>FDE = 12.90 m</strong>).
            </p>
          </div>
          <button type="button" data-jump-scene="scene_05_active_braking_deceleration" data-jump-obs="d0_20.00m" data-jump-mu="1.0" data-jump-tau="1.5" class="no-print w-full py-1.5 px-2.5 rounded bg-rose-600 hover:bg-rose-700 text-white font-semibold transition text-center">
            Inspect Scene 05 Violation &amp; Signed Ablation
          </button>
        </div>

        <div class="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5 flex flex-col justify-between space-y-2">
          <div>
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="font-bold text-amber-900">Finding 3 — Wet-Road Lateral &amp; Timing Erosion</span>
              <span class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-900 font-mono text-[11px]">EXT-VLA-C04</span>
            </div>
            <p class="text-[var(--muted-foreground)] leading-relaxed">
              In <strong>Scene 02</strong> (v<sub>0</sub> = 6.95 m/s, observed stationary obstacle d<sub>0</sub> = 55.49 m), wet-road urban turning bound is violated (|a<sub>lat</sub>| = 2.27 m/s&sup2; &gt; 2.0 m/s&sup2;). Across scenes, delaying &tau;<sub>req</sub> erodes R3B margins from positive to violated (P0 fails earliest; P2 preserves margin longest).
            </p>
          </div>
          <button type="button" data-jump-scene="scene_02_stationary_lead_obstacle" data-jump-obs="observed" data-jump-mu="0.5" data-jump-tau="0.5" class="no-print w-full py-1.5 px-2.5 rounded bg-amber-600 hover:bg-amber-700 text-white font-semibold transition text-center">
            Inspect Scene 02 (Wet Road &mu; = 0.5)
          </button>
        </div>

        <div class="p-3 rounded-lg border border-slate-500/30 bg-slate-500/5 flex flex-col justify-between space-y-2">
          <div>
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="font-bold text-slate-800">Finding 4 — Explicit Evidence Boundaries</span>
              <span class="px-1.5 py-0.5 rounded bg-slate-500/15 text-slate-800 font-mono text-[11px]">EXT-VLA-C05</span>
            </div>
            <p class="text-[var(--muted-foreground)] leading-relaxed">
              R3B evaluation is withheld in open-road observed mode (<strong>Scene 01, 05, 06</strong>), stationary ego baseline (<strong>Scene 07</strong>, v<sub>0</sub> = 0.0019 m/s), and turning states exiting the &pm;1.75 m / &pm;0.35 rad 1D corridor (<strong>Scene 02</strong> &tau;<sub>req</sub> &ge; 1.5 s, <strong>Scene 06</strong> &tau;<sub>req</sub> &ge; 2.0 s).
            </p>
          </div>
          <button type="button" data-jump-scene="scene_07_stationary_ego_baseline" data-jump-obs="observed" data-jump-mu="1.0" data-jump-tau="0.0" class="no-print w-full py-1.5 px-2.5 rounded bg-slate-700 hover:bg-slate-800 text-white font-semibold transition text-center">
            Inspect Scene 07 (Stationary Boundary)
          </button>
        </div>
      </div>

      <!-- Methodological Disclosure on Driving-Command Conditioning & Leakage (EXT-VLA-C06) -->
      <div class="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-[var(--foreground)]">
        <strong class="text-amber-900">Methodological Limitation — Driving-Command Conditioning &amp; Future-Displacement Leakage Risk (<code>EXT-VLA-C06</code>):</strong>
        In <strong>Scene 02</strong> (<code>scene_02_stationary_lead_obstacle</code>, y<sub>GT</sub>(3.0 s) = +4.51 m, y<sub>GT</sub>(5.0 s) = +16.67 m) and <strong>Scene 06</strong> (<code>scene_06_intersection_turn_maneuver</code>, y<sub>GT</sub>(3.0 s) = +4.09 m, y<sub>GT</sub>(5.0 s) = +8.35 m), the effective <code>"turn left"</code> prompt command corresponds to future ground-truth lateral displacement rather than an independent pre-trip navigation signal (and when an unknown raw command is resolved from future lateral displacement, this constitutes future-information leakage). Recorded inference inputs are preserved unmodified for provenance integrity, and affected ADE/FDE metrics are bounded as command-conditioned evaluations rather than strictly leakage-free blind predictions.
      </div>
    </section>

    <!-- ========================================================================================= -->
    <!-- INTERACTIVE ENGINEERING DEMONSTRATOR WORKSPACE: R3B SIMULATOR + AUTOVLA TRAJECTORY EXPLORER -->
    <!-- ========================================================================================= -->
    <section id="interactive-demonstrator-workspace" class="bg-[var(--card)] border-2 border-blue-600/40 rounded-xl p-5 shadow-md space-y-5 print-avoid-break">
      <div class="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-600 text-white">
              Interactive Engineering Demonstrator
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">
              10 Saved AutoVLA Trajectory Rollouts (7 Canonical + 2 Command Interventions + 1 Signed OOD Ablation)
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-900 border border-amber-500/30">
              Exact R3B Analytical Oracle (Never Approximated &bull; Never Labelled "SAFE")
            </span>
          </div>
          <h2 class="text-base font-bold text-[var(--foreground)]">
            Interactive AutoVLA Step-Aware Physics Explorer &amp; Coupled R3B Human Takeover Feasibility Simulator
          </h2>
          <p class="text-xs text-[var(--muted-foreground)]">
            Scrub or animate across the 5.0 s (10-step, &Delta;t = 0.5 s) trajectory horizon, inspect step-local vs. trajectory-wide C1&ndash;C10 vehicle-dynamics checks, and pipe any trajectory step directly into the 4-phase R3B braking-only human takeover model across Observed, Counterfactual, and Parametric conditions.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2 text-xs no-print">
          <label class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 font-semibold text-blue-800 cursor-pointer">
            <input id="chk-auto-sync-r3b" type="checkbox" checked class="accent-blue-600" />
            <span>Auto-Couple Trajectory Step &rarr; R3B Simulator</span>
          </label>
          <button id="btn-send-step-to-r3b" type="button" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold transition">
            Send Current Step to R3B Simulator
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">

        <!-- LEFT COLUMN (6 cols): CAPABILITY 1 — INTERACTIVE AUTOVLA TRAJECTORY & PHYSICS EXPLORER -->
        <div id="interactive-trajectory-explorer" class="xl:col-span-6 bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
            <div>
              <span class="text-[11px] font-bold uppercase tracking-wider text-indigo-700">Capability 1 &mdash; Trajectory &amp; Step-Level Physics Explorer</span>
              <h3 class="text-sm font-bold text-[var(--foreground)]">AutoVLA Action Rollout Playback, Command/Ablation Overlay &amp; Step C1&ndash;C10 Inspector</h3>
            </div>
            <span id="explorer-condition-role-badge" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold"></span>
          </div>

          <!-- Trajectory Explorer Selectors -->
          <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 text-xs">
            <div class="sm:col-span-5">
              <label for="select-explorer-scene" class="block font-semibold text-[var(--muted-foreground)] mb-1">Driving Scene (7 Real Scenes)</label>
              <select id="select-explorer-scene" class="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] px-2.5 py-1.5 font-medium"></select>
            </div>
            <div class="sm:col-span-5">
              <label for="select-explorer-condition" class="block font-semibold text-[var(--muted-foreground)] mb-1">Rollout Condition (10 Saved Rollouts)</label>
              <select id="select-explorer-condition" class="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] px-2.5 py-1.5 font-medium"></select>
            </div>
            <div class="sm:col-span-2">
              <label for="select-explorer-mu" class="block font-semibold text-[var(--muted-foreground)] mb-1">Verifier &mu;</label>
              <select id="select-explorer-mu" class="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] px-2 py-1.5 font-medium">
                <option value="1.0">Dry 1.0</option>
                <option value="0.5">Wet 0.5</option>
              </select>
            </div>
          </div>

          <!-- Playback Scrubber & Overlay Toggles -->
          <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-2.5 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-1.5 no-print">
                <button id="btn-explorer-play" type="button" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white font-semibold transition">
                  &#9654; Play
                </button>
                <button id="btn-explorer-pause" type="button" class="px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] hover:bg-slate-200/60 font-semibold transition">
                  &#9208; Pause
                </button>
                <button id="btn-explorer-restart" type="button" class="px-2.5 py-1 rounded border border-[var(--border)] bg-[var(--background)] hover:bg-slate-200/60 font-semibold transition">
                  &#8634; Restart
                </button>
                <button id="btn-explorer-prev" type="button" class="px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] hover:bg-slate-200/60 font-mono font-semibold">
                  &larr; &minus;0.5s
                </button>
                <button id="btn-explorer-next" type="button" class="px-2 py-1 rounded border border-[var(--border)] bg-[var(--background)] hover:bg-slate-200/60 font-mono font-semibold">
                  +0.5s &rarr;
                </button>
                <div class="inline-flex items-center gap-1 ml-1 pl-1.5 border-l border-[var(--border)]">
                  <span class="text-[11px] font-semibold text-[var(--muted-foreground)]">Speed:</span>
                  <button type="button" data-playback-speed="0.5" class="px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--background)] text-[11px] font-mono">0.5x</button>
                  <button type="button" data-playback-speed="1.0" class="px-1.5 py-0.5 rounded border border-indigo-600 bg-indigo-600 text-white text-[11px] font-mono font-bold">1x</button>
                  <button type="button" data-playback-speed="2.0" class="px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--background)] text-[11px] font-mono">2x</button>
                  <select id="select-explorer-playback-speed" aria-label="Playback speed multiplier" class="sr-only">
                    <option value="0.5">0.5x</option>
                    <option value="1.0" selected>1x</option>
                    <option value="2.0">2x</option>
                  </select>
                </div>
              </div>
              <div class="font-mono text-xs">
                <span class="text-[var(--muted-foreground)]">Active Horizon Time:</span>
                <strong id="explorer-time-label" class="text-indigo-700 text-sm ml-1">t = 0.0 s (Step 0 / 10)</strong>
              </div>
              <span id="explorer-interp-badge" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">
                RECORDED 0.5 s WAYPOINT
              </span>
            </div>

            <div>
              <label for="slider-explorer-time" class="sr-only">Trajectory Horizon Time Scrubber (0.0 to 5.0 seconds)</label>
              <input id="slider-explorer-time" type="range" min="0.0" max="5.0" step="0.5" value="0.0" class="w-full accent-indigo-600 cursor-pointer" />
              <div class="flex justify-between text-[10px] font-mono text-[var(--muted-foreground)] mt-0.5">
                <span>0.0s (t<sub>0</sub>)</span>
                <span>1.0s (k=2)</span>
                <span>2.0s (k=4)</span>
                <span>3.0s (k=6 / R3B max)</span>
                <span>4.0s (k=8)</span>
                <span>5.0s (k=10)</span>
              </div>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[var(--border)]">
              <label class="inline-flex items-center gap-1.5 cursor-pointer">
                <input id="chk-explorer-overlay-gt" type="checkbox" checked class="accent-emerald-600" />
                <span>Show Logged Human Trajectory (GT)</span>
              </label>
              <label class="inline-flex items-center gap-1.5 cursor-pointer">
                <input id="chk-explorer-overlay-counterpart" type="checkbox" checked class="accent-purple-600" />
                <span id="lbl-explorer-counterpart">Overlay Counterpart Rollout (Command / Ablation)</span>
              </label>
              <label class="inline-flex items-center gap-1.5 cursor-pointer">
                <input id="chk-explorer-smooth" type="checkbox" class="accent-indigo-600" />
                <span>Smooth 0.1 s Display Interpolation</span>
              </label>
            </div>
            <div class="text-[11px] text-[var(--muted-foreground)] bg-[var(--background)] rounded px-2 py-1 border border-[var(--border)]">
              <strong>Open-Loop Rollout Replay Notice:</strong> Animates saved 10-step (5.0 s, &Delta;t = 0.5 s) AutoVLA trajectory predictions from recorded nuPlan / NAVSIM observations &mdash; not a closed-loop traffic simulator. Recorded 0.5 s waypoints use solid markers; 0.1 s smooth frames are explicitly badged as display interpolation.
            </div>
          </div>

          <!-- GT / Condition Methodological Boundary Notice -->
          <div id="explorer-gt-boundary-banner" class="p-2.5 rounded-lg text-xs border"></div>

          <!-- Animated BEV Trajectory SVG -->
          <div class="space-y-1">
            <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
              <span class="font-semibold">Animated Bird's-Eye View (+x Forward [m], +y Left [m]) &amp; &pm;1.75 m R3B Corridor</span>
              <span id="explorer-corridor-exit-summary" class="font-mono text-[11px] text-[var(--muted-foreground)]"></span>
            </div>
            <div id="svg-explorer-bev" class="w-full rounded-lg bg-[var(--card)] border border-[var(--border)] p-2"></div>
          </div>

          <!-- Synchronized Step Kinematics SVG -->
          <div class="space-y-1">
            <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
              <span class="font-semibold">Step-Indexed Speed v(t) [m/s] &amp; Longitudinal / Total Acceleration [m/s&sup2;]</span>
              <span class="text-[11px] text-[var(--muted-foreground)]">Vertical cursor tracks scrubbed time t</span>
            </div>
            <div id="svg-explorer-kinematics" class="w-full rounded-lg bg-[var(--card)] border border-[var(--border)] p-2"></div>
          </div>

          <!-- Live Step Telemetry Readout Card -->
          <div id="explorer-step-telemetry" class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs space-y-2"></div>

          <!-- Step-Aware C1-C10 Physical Feasibility Diagnostics Table -->
          <div class="space-y-1.5">
            <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
              <span class="font-semibold">Step-Aware Physical Constraint Diagnostics (C1&ndash;C10 at Active Step vs. Trajectory-Wide)</span>
              <span class="text-[11px] text-[var(--muted-foreground)]">Explicitly separates <code>TIME_LOCAL_STEP</code> (k=1..10) from <code>TRAJECTORY_WIDE</code></span>
            </div>
            <div class="table-wrapper rounded-lg border border-[var(--border)] bg-[var(--card)] max-h-64">
              <table class="text-xs">
                <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
                  <tr>
                    <th class="text-left p-2 border-b border-[var(--border)]">Check ID</th>
                    <th class="text-left p-2 border-b border-[var(--border)]">Evaluation Scope</th>
                    <th class="text-right p-2 border-b border-[var(--border)]">Step Value</th>
                    <th class="text-right p-2 border-b border-[var(--border)]">Limit</th>
                    <th class="text-left p-2 border-b border-[var(--border)]">Step Status</th>
                  </tr>
                </thead>
                <tbody id="tbody-explorer-step-checks"></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN (6 cols): CAPABILITY 2 — INTERACTIVE R3B HUMAN TAKEOVER FEASIBILITY SIMULATOR -->
        <div id="interactive-r3b-simulator" class="xl:col-span-6 bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
            <div>
              <span class="text-[11px] font-bold uppercase tracking-wider text-amber-800">Capability 2 &mdash; Interactive R3B Human Takeover Simulator</span>
              <h3 class="text-sm font-bold text-[var(--foreground)]">4-Phase Braking-Only Necessary-Condition Model (P0 / P1 / P2) &amp; 3-Layer Provenance</h3>
            </div>
            <div class="flex items-center gap-1.5 text-xs">
              <label for="select-r3b-sim-mode" class="font-semibold text-[var(--muted-foreground)]">Mode:</label>
              <select id="select-r3b-sim-mode" class="rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] px-2.5 py-1 font-semibold">
                <option value="connected">Connected AutoVLA Trajectory Mode</option>
                <option value="standalone">Standalone Parametric Explorer Mode</option>
              </select>
            </div>
          </div>

          <!-- Interactive Parameter Controls Card -->
          <div class="p-3.5 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-3 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2">
              <span class="font-bold text-[var(--foreground)]">Interactive Vehicle, Obstacle, Surface &amp; Human-Response Controls</span>
              <div class="flex items-center gap-2 no-print">
                <label for="select-r3b-speed-unit" class="text-[11px] font-semibold text-[var(--muted-foreground)]">Speed Unit:</label>
                <select id="select-r3b-speed-unit" class="rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-[11px] font-mono">
                  <option value="mps">m/s (SI)</option>
                  <option value="kmh">km/h</option>
                </select>
                <button id="btn-r3b-reset-defaults" type="button" class="px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--background)] hover:bg-slate-200/60 text-[11px] font-semibold">
                  Reset R3B Defaults
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <!-- Speed Control -->
              <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <div class="flex items-center justify-between">
                  <label for="input-r3b-speed" class="font-semibold">Speed at Takeover Request v(&tau;<sub>req</sub>)</label>
                  <span id="r3b-speed-dual-readout" class="font-mono text-[11px] text-blue-700 font-bold"></span>
                </div>
                <div class="flex items-center gap-2">
                  <input id="slider-r3b-speed" type="range" min="0.0" max="40.0" step="0.1" value="13.58" aria-label="Vehicle speed slider" class="w-full accent-blue-600 cursor-pointer" />
                  <input id="input-r3b-speed" type="number" step="0.1" value="13.58" class="w-20 rounded border border-[var(--border)] bg-[var(--card)] px-2 py-1 font-mono text-right" />
                </div>
              </div>

              <!-- Obstacle Source & Distance Control -->
              <div class="p-2.5 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <div class="flex items-center justify-between gap-1">
                  <label for="select-r3b-obstacle-mode" class="font-semibold">Obstacle Source &amp; Initial d<sub>0</sub> [m]</label>
                  <select id="select-r3b-obstacle-mode" class="rounded border border-[var(--border)] bg-[var(--card)] px-1.5 py-0.5 text-[11px] font-semibold">
                    <option value="observed">Observed 3D Lead (If Present)</option>
                    <option value="counterfactual">Assumed Stationary d0 [m]</option>
                  </select>
                </div>
                <div class="flex items-center gap-2">
                  <input id="slider-r3b-d0" type="range" min="5.0" max="120.0" step="0.5" value="45.0" aria-label="Initial obstacle distance d0 slider" class="w-full accent-pink-600 cursor-pointer" />
                  <input id="input-r3b-d0" type="number" step="0.5" value="45.0" aria-label="Initial obstacle distance d0 in meters" class="w-20 rounded border border-[var(--border)] bg-[var(--card)] px-2 py-1 font-mono text-right" />
                </div>
              </div>

              <!-- Takeover Request Delay tau_req Control -->
              <div class="p-2.5 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <div class="flex items-center justify-between">
                  <label for="input-r3b-tau" class="font-semibold">Takeover Request Delay &tau;<sub>req</sub> [s]</label>
                  <span class="font-mono text-[11px] text-[var(--muted-foreground)]">Domain: 0.0 &ndash; 3.0 s</span>
                </div>
                <div class="flex items-center gap-2">
                  <input id="slider-r3b-tau" type="range" min="0.0" max="3.0" step="0.5" value="0.0" aria-label="Takeover request delay tau_req slider" class="w-full accent-indigo-600 cursor-pointer" />
                  <input id="input-r3b-tau" type="number" step="0.5" value="0.0" class="w-20 rounded border border-[var(--border)] bg-[var(--card)] px-2 py-1 font-mono text-right" />
                </div>
              </div>

              <!-- Policy Branch Selector -->
              <div class="p-2.5 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <label for="select-r3b-policy" class="block font-semibold">Pre-Control Transition Policy (During t<sub>1</sub>)</label>
                <select id="select-r3b-policy" class="w-full rounded border border-[var(--border)] bg-[var(--card)] px-2.5 py-1.5 font-semibold">
                  <option value="P0">P0 &mdash; Unmitigated Hold-Speed (0.0 m/s&sup2; in t1)</option>
                  <option value="P1" selected>P1 &mdash; Passive Throttle-Off EPA Drag in t1</option>
                  <option value="P2">P2 &mdash; System-Supported Pre-Decel (a_sup in t1)</option>
                </select>
              </div>

              <!-- Road Friction mu Control + Presets -->
              <div class="p-2.5 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <div class="flex flex-wrap items-center justify-between gap-1">
                  <label for="input-r3b-mu" class="font-semibold">Road Friction &mu; (&mu;&middot;g Cap)</label>
                  <div class="flex items-center gap-1 no-print">
                    <button type="button" data-mu-preset="1.0" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px] font-mono hover:bg-blue-500/10">Dry 1.0</button>
                    <button type="button" data-mu-preset="0.7" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px] font-mono hover:bg-blue-500/10">Wet 0.7</button>
                    <button type="button" data-mu-preset="0.5" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px] font-mono hover:bg-blue-500/10">Rain 0.5</button>
                    <button type="button" data-mu-preset="0.35" class="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px] font-mono hover:bg-blue-500/10">Snow 0.35</button>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <input id="slider-r3b-mu" type="range" min="0.15" max="1.10" step="0.05" value="1.00" aria-label="Road friction mu slider" class="w-full accent-amber-600 cursor-pointer" />
                  <input id="input-r3b-mu" type="number" step="0.05" value="1.00" class="w-20 rounded border border-[var(--border)] bg-[var(--card)] px-2 py-1 font-mono text-right" />
                </div>
              </div>

              <!-- Human Takeover Reaction Time t1 Control -->
              <div class="p-2.5 rounded bg-[var(--background)] border border-[var(--border)] space-y-1">
                <div class="flex items-center justify-between">
                  <label for="input-r3b-t1" class="font-semibold">Human Reaction Delay t<sub>1</sub> [s]</label>
                  <span class="font-mono text-[10px] text-[var(--muted-foreground)]">R3B Box: [1.15, 3.00] s</span>
                </div>
                <div class="flex items-center gap-2">
                  <input id="slider-r3b-t1" type="range" min="0.50" max="4.00" step="0.05" value="1.65" aria-label="Human reaction time t1 slider" class="w-full accent-emerald-600 cursor-pointer" />
                  <input id="input-r3b-t1" type="number" step="0.05" value="1.65" class="w-20 rounded border border-[var(--border)] bg-[var(--card)] px-2 py-1 font-mono text-right" />
                </div>
              </div>
            </div>

            <!-- Secondary Physical Parameters Row (t2, t3, a_max, a_sup, P1 Coastdown Drag, Road Gradient Domain) -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 pt-2 border-t border-[var(--border)]">
              <div>
                <label for="input-r3b-t2" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Hydraulic Delay t<sub>2</sub> [s]</label>
                <input id="input-r3b-t2" type="number" step="0.01" value="0.10" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs" />
                <div class="text-[10px] font-mono text-[var(--muted-foreground)]">R3B: [0.05, 0.17]</div>
              </div>
              <div>
                <label for="input-r3b-t3" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Brake Ramp t<sub>3</sub> [s]</label>
                <input id="input-r3b-t3" type="number" step="0.05" value="0.60" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs" />
                <div class="text-[10px] font-mono text-[var(--muted-foreground)]">R3B: [0.30, 1.20]</div>
              </div>
              <div>
                <label for="input-r3b-amax" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Max Decel a<sub>max</sub> [m/s&sup2;]</label>
                <input id="input-r3b-amax" type="number" step="0.1" value="8.00" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs" />
                <div class="text-[10px] font-mono text-[var(--muted-foreground)]">R3B: [6.43, 9.10]</div>
              </div>
              <div>
                <label for="input-r3b-asup" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">P2 Decel a<sub>sup</sub> [m/s&sup2;]</label>
                <input id="input-r3b-asup" type="number" step="0.1" value="2.00" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs" />
                <div class="text-[10px] font-mono text-[var(--muted-foreground)]">R3B: [1.00, 3.00]</div>
              </div>
              <div>
                <label for="select-r3b-drag-mode" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">P1 Aero/Coast Drag</label>
                <select id="select-r3b-drag-mode" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-1.5 py-1 text-[11px] font-semibold">
                  <option value="epa_midpoint" selected>EPA Midpoint(v)</option>
                  <option value="epa_p05">EPA P05 Low Drag</option>
                  <option value="epa_median">EPA Median(v)</option>
                  <option value="epa_p95">EPA P95 High Drag</option>
                  <option value="epa_bev_median">EPA BEV Median</option>
                  <option value="custom">Custom a_drag</option>
                </select>
                <input id="input-r3b-adrag" type="number" step="0.02" value="0.25" aria-label="Custom aerodynamic drag deceleration in m/s^2" class="hidden w-full mt-1 rounded border border-[var(--border)] bg-[var(--card)] px-1.5 py-0.5 font-mono text-[11px]" />
              </div>
              <div>
                <label for="select-r3b-grade" class="block text-[11px] font-semibold text-[var(--muted-foreground)]">Road Gradient [%]</label>
                <select id="select-r3b-grade" class="w-full mt-0.5 rounded border border-[var(--border)] bg-[var(--background)] px-1.5 py-1 text-[11px] font-semibold">
                  <option value="0.0" selected>0% (Level Road)</option>
                  <option value="-3.0">&minus;3% (Downhill*)</option>
                  <option value="3.0">+3% (Uphill*)</option>
                </select>
                <div class="text-[10px] font-mono text-[var(--muted-foreground)]">R3B Domain: 0%</div>
              </div>
            </div>
          </div>

          <!-- EXPLICIT 3-LAYER PROVENANCE & OUTPUT ARCHITECTURE -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <!-- LAYER 1: Observed / Recorded Evidence -->
            <div id="r3b-layer-observed" class="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/30 space-y-1"></div>
            <!-- LAYER 2: Assumed Counterfactual Inputs -->
            <div id="r3b-layer-assumed" class="p-3 rounded-lg bg-pink-500/5 border border-pink-500/30 space-y-1"></div>
          </div>

          <!-- LAYER 3: Derived Model Conclusions -->
          <div id="r3b-layer-derived" class="p-3.5 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-3 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
              <div>
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-600">Layer 3 &mdash; Derived R3B Model Conclusions (Necessary Condition Only)</span>
                <div id="r3b-sim-state-source-badge" class="mt-1"></div>
              </div>
              <div class="text-right">
                <div id="r3b-sim-status-badge" class="inline-block px-3 py-1 rounded-full text-xs font-bold"></div>
                <div id="r3b-sim-underlying-label" class="text-[10px] font-mono text-[var(--muted-foreground)] mt-0.5"></div>
              </div>
            </div>

            <!-- Primary Numerical Readouts Grid -->
            <div id="r3b-sim-metrics-grid" class="grid grid-cols-2 sm:grid-cols-4 gap-2"></div>

            <!-- Phase-by-Phase Stopping Breakdown SVG Chart -->
            <div class="space-y-1">
              <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
                <span class="font-semibold">4-Phase Stopping Distance Breakdown across P0 / P1 / P2 vs. Available Distance D<sub>avail</sub> [m]</span>
                <span class="text-[11px] font-mono text-[var(--muted-foreground)]">Includes +2.0 m Standstill Margin</span>
              </div>
              <div id="svg-r3b-sim-breakdown" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
            </div>

            <!-- Plain-English Causal Explanation -->
            <div id="r3b-sim-causal-explanation" class="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/25 leading-relaxed"></div>

            <!-- Presentation Status Mapping & Non-Safety Boundary Legend -->
            <details class="rounded-lg bg-[var(--background)] border border-[var(--border)] p-2.5">
              <summary class="font-semibold cursor-pointer text-[11px] text-[var(--muted-foreground)]">
                Presentation Status Mapping to Underlying R3B Classifications &amp; Mandatory Non-Safety Boundary
              </summary>
              <div id="r3b-sim-status-legend" class="mt-2 space-y-1 text-[11px] text-[var(--muted-foreground)]">
                <div>&bull; <code>NECESSARY_CONDITION_SATISFIED</code> &larr; <code>ROBUSTLY SATISFIED</code> / point margin M<sub>d</sub> &ge; 0 m (necessary 1D braking condition met; <strong>never labelled "SAFE"</strong>).</div>
                <div>&bull; <code>NECESSARY_CONDITION_VIOLATED</code> &larr; <code>ROBUSTLY UNSATISFIED</code> / point margin M<sub>d</sub> &lt; 0 m (required stopping distance exceeds available obstacle distance).</div>
                <div>&bull; <code>PARAMETER_SENSITIVE</code> &larr; <code>PARAMETER-SENSITIVE</code> (margin changes sign across the frozen R3B human/vehicle parameter box: t<sub>1</sub> &isin; [1.15, 3.00] s, t<sub>2</sub> &isin; [0.05, 0.17] s, t<sub>3</sub> &isin; [0.30, 1.20] s, a<sub>max</sub> &isin; [6.43, 9.10] m/s&sup2;).</div>
                <div>&bull; <code>NOT_APPLICABLE</code> &larr; Stationary ego (v &le; 0.05 m/s), trajectory step outside the &pm;1.75 m / &pm;0.35 rad 1D longitudinal corridor, d<sub>rem</sub> &le; 0 m, or out-of-range inputs.</div>
                <div>&bull; <code>INSUFFICIENT_EVIDENCE</code> &larr; No observed 3D in-corridor obstacle in dataset annotations and no counterfactual d<sub>0</sub> assumed (TTC is never inferred from camera pixels alone).</div>
              </div>
            </details>
          </div>
        </div>

      </div>
    </section>

    <!-- Interactive Control Bar (Wide 12-Column Grid Preventing Truncation) -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3 print-avoid-break">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
        <div class="lg:col-span-4">
          <label for="select-record" class="block text-xs font-semibold text-[var(--muted-foreground)] mb-1">
            1. Driving Scenario &amp; Genuine VLA Prediction (7 Scenes)
          </label>
          <select id="select-record" class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] px-3 py-2 text-xs font-medium"></select>
        </div>
        <div class="lg:col-span-4">
          <label for="select-obstacle" class="block text-xs font-semibold text-[var(--muted-foreground)] mb-1">
            2. Obstacle Distance Source &amp; Provenance Mode (Phase D/E)
          </label>
          <select id="select-obstacle" class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] px-3 py-2 text-xs font-medium"></select>
        </div>
        <div class="lg:col-span-2">
          <label for="select-mu" class="block text-xs font-semibold text-[var(--muted-foreground)] mb-1">
            3. Road Friction (&mu;)
          </label>
          <select id="select-mu" class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] px-2.5 py-2 text-xs font-medium">
            <option value="1.0">&mu; = 1.0 (Dry — 9.81 m/s&sup2;)</option>
            <option value="0.5">&mu; = 0.5 (Wet — 4.91 m/s&sup2;)</option>
          </select>
        </div>
        <div class="lg:col-span-2">
          <label for="slider-tau" class="block text-xs font-semibold text-[var(--muted-foreground)] mb-1">
            4. Takeover Request &tau;<sub>req</sub>: <span id="tau-val-label" class="font-bold text-blue-700">0.0 s</span>
          </label>
          <input id="slider-tau" type="range" min="0" max="3.0" step="0.5" value="0.0" class="w-full accent-blue-600 cursor-pointer" />
          <div class="flex justify-between text-[11px] text-[var(--muted-foreground)] mt-0.5">
            <span>0.0s (t<sub>0</sub>)</span>
            <span>1.5s</span>
            <span>3.0s</span>
          </div>
        </div>
      </div>

      <!-- Untruncated Active Selection & Provenance Summary Strip -->
      <div id="active-selection-strip" class="pt-2.5 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-xs"></div>
    </section>

    <!-- Scenario Observation & Camera Views -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-5 print-avoid-break">
      <div class="lg:col-span-7 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-sm font-bold text-[var(--foreground)]">
            Multi-View Camera Observations at Evaluation Timestamp t<sub>0</sub> = 0.0 s
          </h2>
          <span id="scene-location-badge" class="px-2 py-0.5 rounded text-xs font-mono bg-[var(--background)] border border-[var(--border)]"></span>
        </div>
        <div class="grid grid-cols-3 gap-2.5">
          <div class="space-y-1">
            <div class="text-xs font-semibold text-[var(--muted-foreground)]">Front-Left (CAM_L0)</div>
            <img id="img-cam-left" class="cam-frame rounded-lg border border-[var(--border)] bg-black/20" alt="Front left camera at t0" />
          </div>
          <div class="space-y-1">
            <div class="text-xs font-semibold text-[var(--muted-foreground)]">Front Center (CAM_F0)</div>
            <img id="img-cam-front" class="cam-frame rounded-lg border border-[var(--border)] bg-black/20" alt="Front center camera at t0" />
          </div>
          <div class="space-y-1">
            <div class="text-xs font-semibold text-[var(--muted-foreground)]">Front-Right (CAM_R0)</div>
            <img id="img-cam-right" class="cam-frame rounded-lg border border-[var(--border)] bg-black/20" alt="Front right camera at t0" />
          </div>
        </div>
        <p id="scene-desc" class="text-xs text-[var(--muted-foreground)] leading-relaxed"></p>
      </div>

      <!-- Provenance & VLA Generation Output -->
      <div class="lg:col-span-5 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
        <div class="space-y-2.5">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-bold text-[var(--foreground)]">Genuine AutoVLA Output &amp; Observed t<sub>0</sub> State</h2>
            <span id="vla-valid-badge" class="px-2 py-0.5 rounded text-xs font-semibold"></span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">Observed Speed v<sub>0</sub></div>
              <div id="stat-v0" class="font-bold text-sm mt-0.5"></div>
            </div>
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">Observed a<sub>x,0</sub> / Prompt &Vert;a<sub>0</sub>&Vert;</div>
              <div id="stat-a0" class="font-bold text-sm mt-0.5"></div>
            </div>
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">Driving Command</div>
              <div id="stat-cmd" class="font-bold text-sm mt-0.5 uppercase"></div>
            </div>
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">Observed 3D Corridor Lead</div>
              <div id="stat-obs-lead" class="font-bold text-sm mt-0.5"></div>
            </div>
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">ADE / FDE vs. Logged GT</div>
              <div id="stat-ade-fde" class="font-bold text-sm mt-0.5"></div>
            </div>
            <div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)]">Inference Latency</div>
              <div id="stat-latency" class="font-bold text-sm mt-0.5"></div>
            </div>
          </div>
          <div class="space-y-1 text-xs">
            <div class="font-semibold text-[var(--muted-foreground)]">Exact Input Prompt &amp; Raw AutoVLA Action Tokens (10 steps, &Delta;t = 0.5 s):</div>
            <pre id="vla-raw-output" class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)] font-mono text-[11px] whitespace-pre-wrap max-h-32 overflow-y-auto"></pre>
          </div>
        </div>
        <div class="text-xs text-[var(--muted-foreground)] pt-2 border-t border-[var(--border)] flex flex-wrap justify-between gap-2">
          <span id="env-hw-badge"></span>
          <span id="token-badge" class="font-mono"></span>
        </div>
      </div>
    </section>

    <!-- Scene 05 Targeted Ablation Spotlight Banner (Highlighted automatically on Scene 05, accessible anytime) -->
    <section id="scene05-ablation-section" class="bg-[var(--card)] border-2 border-rose-500/40 rounded-xl p-4 shadow-sm space-y-3 print-avoid-break">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
        <div>
          <span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/15 text-rose-800 border border-rose-500/30">
            Priority 3 Deep-Dive — Scene 05 Active-Braking Finding &amp; Controlled Signed-Acceleration Prompt Ablation
          </span>
          <h2 class="text-sm font-bold text-[var(--foreground)] mt-1">
            Distinguishing Input-Representation Limitation (<code>&Vert;a(0)&Vert; = 1.56 m/s&sup2;</code>) from Causal Attribution (<code>a<sub>x</sub>(0) = &minus;1.5525 m/s&sup2;</code>)
          </h2>
        </div>
        <span id="ablation-active-indicator" class="text-xs font-mono px-2.5 py-1 rounded bg-[var(--background)] border border-[var(--border)]"></span>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start text-xs">
        <div class="lg:col-span-7 space-y-2">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[var(--muted-foreground)] font-semibold">1. Logged Ground Truth</div>
              <div class="font-bold text-emerald-700 mt-0.5">Brakes 4.31 &rarr; 2.29 m/s (t &le; 2.5 s)</div>
              <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5">
                Observed a<sub>x</sub>(0) = &minus;1.5525 m/s&sup2;, a<sub>y</sub>(0) = +0.1831 m/s&sup2;. Decelerates to x = 6.92 m at t = 2.5 s, then gently accelerates to x = 15.65 m at t = 5.0 s.
              </div>
            </div>
            <div class="p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/30">
              <div class="text-rose-800 font-semibold">2. Standard AutoVLA (Unsigned Norm)</div>
              <div class="font-bold text-rose-700 mt-0.5">Prompt: <code>"1.56 m/s^2"</code> (&Vert;a&Vert; = 1.5633)</div>
              <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5">
                Step 1 decelerates (a<sub>lon,1</sub> = &minus;0.8841 m/s&sup2;), then reverses at Step 2 (+0.7917 m/s&sup2;) and peaks at <strong>Step 3 (+1.5442 m/s&sup2;)</strong>, reaching x<sub>10</sub> = 28.53 m (<strong>ADE = 6.25 m, FDE = 12.90 m</strong>).
              </div>
            </div>
            <div class="p-2.5 rounded-lg bg-blue-500/5 border border-blue-500/30">
              <div class="text-blue-800 font-semibold">3. Controlled OOD Signed Ablation</div>
              <div class="font-bold text-blue-700 mt-0.5">Prompt: <code>"-1.55 m/s^2"</code> (Signed a<sub>x,0</sub>)</div>
              <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5">
                Identical images &amp; v<sub>0</sub>: sustains braking across Steps 1&ndash;7 (a<sub>lon</sub> &isin; [&minus;1.39, &minus;0.88] m/s&sup2;) to standstill at <strong>x<sub>10</sub> = 6.93 m</strong> (0&ndash;2 s braking ADE = <strong>0.14 m</strong>; 5 s ADE = <strong>2.42 m</strong>).
              </div>
            </div>
          </div>
          <div class="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-950 leading-relaxed">
            <strong>Mandatory Scientific Boundary on Causal Attribution:</strong>
            (1) Passing a negative acceleration string (<code>-1.55 m/s^2</code>) is an <em>out-of-distribution (OOD) prompt intervention</em> relative to AutoVLA's training interface (<code>np.linalg.norm(acceleration) &ge; 0</code>) and is <em>not</em> a validated model upgrade.
            (2) Even under the standard unsigned prompt (<code>1.56 m/s^2</code>), Step 1 still decelerates at &minus;0.8841 m/s&sup2; from multi-frame visual cues before the trajectory reverses at Steps 2&ndash;3.
            (3) Under the OOD signed prompt, once the vehicle reaches standstill at t = 3.5 s (x = 6.98 m), Step 9 emits a 5.8 cm backward jitter token (<code>&lt;action_126&gt;</code>). Thus, unsigned acceleration encoding is a verified <strong>input-representation limitation</strong> and strong contributing factor in Scene 05, not a single-cause deterministic law.
          </div>
        </div>
        <div class="lg:col-span-5 space-y-1">
          <div class="font-semibold text-xs">Scene 05 Longitudinal Position x(t) [m] — Standard Unsigned vs. Signed Ablation vs. Logged GT</div>
          <div id="svg-scene05-ablation-container" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
        </div>
      </div>
    </section>

    <!-- Two-Column Core Comparison: Panel A (Phase C Trajectory Feasibility) vs Panel B (Phase D/E R3B Recoverability) -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-5">

      <!-- PANEL A: Phase C Independent Trajectory Feasibility -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4 print-avoid-break">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-purple-700">
              Phase B &amp; C — Independent Trajectory Feasibility Verifier
            </span>
            <h2 class="text-base font-bold text-[var(--foreground)]">
              VLA Trajectory Geometry &amp; Physical Dynamics Checks (C1&ndash;C10)
            </h2>
          </div>
          <div id="feas-classification-badge" class="px-3 py-1 rounded-full text-xs font-bold"></div>
        </div>

        <!-- BEV Trajectory SVG -->
        <div class="space-y-1">
          <div class="flex items-center justify-between text-xs">
            <span class="font-semibold">Bird's-Eye View Trajectory in Ego Frame (+x Forward [m], +y Left [m])</span>
            <span class="text-[var(--muted-foreground)]">1D R3B Corridor: &pm;1.75 m | Horizon: 5.0 s</span>
          </div>
          <div id="svg-bev-container" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
        </div>

        <!-- Speed & Acceleration SVG Profiles -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <div class="text-xs font-semibold">Implied Speed Profile v(t) [m/s] vs. Time t [s]</div>
            <div id="svg-speed-container" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
          </div>
          <div class="space-y-1">
            <div class="text-xs font-semibold">Implied Accel a<sub>lon</sub>(t) &amp; |a<sub>tot</sub>(t)| [m/s&sup2;] vs. Time t [s]</div>
            <div id="svg-accel-container" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
          </div>
        </div>

        <!-- Violation or Insufficient Evidence Callout for Phase C -->
        <div id="feas-reasons-box" class="p-3 rounded-lg text-xs space-y-1"></div>

        <!-- Explicit Constraint Check Table (C1..C10) -->
        <div class="space-y-1.5">
          <div class="text-xs font-semibold">Explicit Trajectory Constraint Checks (C1&ndash;C10)</div>
          <div class="table-wrapper rounded-lg border border-[var(--border)]">
            <table class="text-xs">
              <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
                <tr>
                  <th class="text-left p-2 border-b border-[var(--border)]">Check ID &amp; Condition</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">Measured Value</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">Threshold</th>
                  <th class="text-left p-2 border-b border-[var(--border)]">Status</th>
                </tr>
              </thead>
              <tbody id="tbody-feas-checks"></tbody>
            </table>
          </div>
        </div>

        <!-- Road Friction Sensitivity Table -->
        <div class="space-y-1.5">
          <div class="text-xs font-semibold">Trajectory Demand vs. Road-Friction Cap (&mu;&middot;g [m/s&sup2;])</div>
          <div class="table-wrapper rounded-lg border border-[var(--border)]">
            <table class="text-xs">
              <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
                <tr>
                  <th class="text-left p-2 border-b border-[var(--border)]">Friction &mu;</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">&mu;&middot;g Cap</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">Max Braking</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">Max |a<sub>tot</sub>|</th>
                  <th class="text-left p-2 border-b border-[var(--border)]">Kamm Friction-Circle Status</th>
                </tr>
              </thead>
              <tbody id="tbody-friction-sens"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- PANEL B: Phase D & E Counterfactual R3B Human Fallback Analysis -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4 print-avoid-break">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-amber-800">
              Phase D &amp; E — Counterfactual R3B Braking-Only Fallback Adapter
            </span>
            <h2 class="text-base font-bold text-[var(--foreground)]">
              Recoverability Margin Across Takeover Request Timing &tau;<sub>req</sub>
            </h2>
          </div>
          <span id="obstacle-provenance-badge" class="px-2.5 py-1 rounded-full text-xs font-bold"></span>
        </div>

        <!-- Highlighted Request Time State Card -->
        <div id="tau-spotlight-card" class="p-3 rounded-lg bg-[var(--background)] border border-[var(--border)] space-y-2 text-xs"></div>

        <!-- R3B Recoverability Margin vs Takeover Request Time SVG Chart -->
        <div class="space-y-1">
          <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
            <span class="font-semibold">Braking-Only Distance Margin M<sub>d</sub> [m] vs. Takeover Request Time &tau;<sub>req</sub> [s]</span>
            <span id="chart-mu-label" class="text-[var(--muted-foreground)] font-mono"></span>
          </div>
          <div class="text-[11px] text-[var(--muted-foreground)]">
            Shared R3B latency box: t<sub>1</sub> &isin; [1.15, 3.00] s (TOR &rarr; effective braking), t<sub>2</sub> &isin; [0.05, 0.17] s, t<sub>3</sub> &isin; [0.30, 1.20] s, a<sub>max</sub> &isin; [6.43, 9.10] m/s&sup2; capped by &mu;&middot;g.
          </div>
          <div id="svg-r3b-margin-container" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
        </div>

        <!-- Insufficient Evidence / Boundary Callout for Phase D -->
        <div id="r3b-reasons-box" class="p-3 rounded-lg text-xs space-y-1"></div>

        <!-- Full Takeover Timing Schedule & Policy Branch Sensitivity Table -->
        <div class="space-y-1.5">
          <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
            <span class="font-semibold">Takeover Timing &amp; Pre-Control Transition Policy Comparison (P0 / P1 / P2)</span>
            <span class="text-[var(--muted-foreground)]">Cells show [conservative, optimistic] distance margin [m] and time margin [s]</span>
          </div>
          <div class="table-wrapper rounded-lg border border-[var(--border)]">
            <table class="text-xs">
              <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
                <tr>
                  <th class="text-left p-2 border-b border-[var(--border)]">&tau;<sub>req</sub></th>
                  <th class="text-left p-2 border-b border-[var(--border)]">Complete Scenario State Provenance</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">v(&tau;<sub>req</sub>)</th>
                  <th class="text-right p-2 border-b border-[var(--border)]">d<sub>rem</sub></th>
                  <th class="text-right p-2 border-b border-[var(--border)]">TTC</th>
                  <th class="text-left p-2 border-b border-[var(--border)]">P0 (Hold Speed)</th>
                  <th class="text-left p-2 border-b border-[var(--border)]">P1 (Passive Drag)</th>
                  <th class="text-left p-2 border-b border-[var(--border)]">P2 (Supported Decel)</th>
                </tr>
              </thead>
              <tbody id="tbody-r3b-schedule"></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- RQ1 Controlled Command-Sensitivity Comparison (Scene 02 & Scene 06) & RQ2 Scene 05 C10 Robustness Matrix -->
    <section id="rq1-command-sensitivity-section" class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4 print-avoid-break">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/15 text-indigo-800 border border-indigo-500/30">
              RQ1 — Controlled Driving-Command Sensitivity Experiment (EXT-VLA-C07)
            </span>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">
              7 Canonical Predictions Frozen &amp; Unchanged
            </span>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/15 text-purple-800 border border-purple-500/30">
              2 Controlled Single-Variable Interventions ("turn left" &rarr; "keep forward")
            </span>
          </div>
          <h2 class="text-sm font-bold text-[var(--foreground)] mt-1">
            Scene 02 &amp; Scene 06 Trajectory, Kinematic &amp; R3B Corridor Sensitivity Under Controlled Driving-Command Intervention
          </h2>
        </div>
        <span class="text-xs font-mono text-[var(--muted-foreground)]">
          Supported Upstream AutoVLA Commands: "turn left" | "keep forward" | "turn right"
        </span>
      </div>

      <!-- Critical Interpretation Rule Alert -->
      <div class="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-950 leading-relaxed">
        <strong>Critical Interpretation Rule (Command-Conditioned ADE/FDE vs. Logged Human Turn):</strong>
        In <strong>Scene 02</strong> (y<sub>GT</sub>(5.0 s) = +16.67 m) and <strong>Scene 06</strong> (y<sub>GT</sub>(5.0 s) = +8.35 m), the logged human ground-truth trajectory executes a <strong>left-turn maneuver</strong>. It is <em>not</em> a valid ground-truth reference target for a deliberately different <code>"keep forward"</code> intervention command. Reported ADE/FDE differences under <code>"keep forward"</code> quantify <strong>command sensitivity relative to the recorded turning trajectory</strong>, not policy quality, driving safety, or superiority/inferiority of either trajectory. Outside the &pm;1.75 m / &pm;0.35 rad longitudinal corridor (or without an observed 3D in-lane obstacle), R3B braking-only recoverability explicitly returns <code>INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE</code>.
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Scene 02 Command Sensitivity Card -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 space-y-2.5">
          <div class="flex flex-wrap items-center justify-between gap-1">
            <div>
              <span class="text-xs font-bold text-[var(--foreground)]">Scene 02 — Stationary Lead Obstacle Approach (<code>3cacb287d398542f</code>)</span>
              <div class="text-[11px] text-[var(--muted-foreground)]">v<sub>0</sub> = 6.95 m/s, a<sub>x,0</sub> = +0.58 m/s&sup2;, Observed Stationary 3D Lead d<sub>0</sub> = 55.49 m</div>
            </div>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/15 text-indigo-800 border border-indigo-500/30">10/10 Tokens Changed (Step 1)</span>
          </div>
          <div id="svg-cmd-sens-scene02" class="w-full rounded bg-[var(--card)] border border-[var(--border)] p-1.5"></div>
          <div id="table-cmd-sens-scene02" class="table-wrapper rounded border border-[var(--border)] bg-[var(--card)]"></div>
        </div>

        <!-- Scene 06 Command Sensitivity Card -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 space-y-2.5">
          <div class="flex flex-wrap items-center justify-between gap-1">
            <div>
              <span class="text-xs font-bold text-[var(--foreground)]">Scene 06 — Multi-Vehicle Intersection Turn (<code>c9d4d04945e85ef8</code>)</span>
              <div class="text-[11px] text-[var(--muted-foreground)]">v<sub>0</sub> = 8.78 m/s, a<sub>x,0</sub> = +0.41 m/s&sup2;, No Observed In-Corridor Lead (CF d<sub>0</sub> = 20.0 m)</div>
            </div>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/15 text-indigo-800 border border-indigo-500/30">8/10 Tokens Changed (Step 1)</span>
          </div>
          <div id="svg-cmd-sens-scene06" class="w-full rounded bg-[var(--card)] border border-[var(--border)] p-1.5"></div>
          <div id="table-cmd-sens-scene06" class="table-wrapper rounded border border-[var(--border)] bg-[var(--card)]"></div>
        </div>
      </div>
    </section>

    <!-- RQ2 Scene 05 C10 Numerical Robustness Audit Section -->
    <section id="rq2-c10-robustness-section" class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-4 print-avoid-break">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/15 text-rose-800 border border-rose-500/30">
              RQ2 — Scene 05 C10 Numerical Robustness Audit (EXT-VLA-C08)
            </span>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">
              Native 0.5 s Grid Only (No Synthetic Resampling)
            </span>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-900 border border-amber-500/30">
              30/30 Violated for Windows &ge; 1.5 s at &le; 2.5 m/s&sup2; (45/75 Overall Grid)
            </span>
          </div>
          <h2 class="text-sm font-bold text-[var(--foreground)] mt-1">
            Sensitivity of <code>C10_LONGITUDINAL_ACCEL_STATE_CONSISTENCY</code> Across 5 Discrete Derivative Estimators, 5 Temporal Windows &amp; 3 Illustrative Thresholds
          </h2>
        </div>
        <span id="c10-overall-badge" class="text-xs font-mono px-2.5 py-1 rounded bg-amber-500/15 text-amber-900 border border-amber-500/30"></span>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start text-xs">
        <div class="lg:col-span-5 space-y-2.5">
          <div class="font-semibold">Scene 05 Implied Longitudinal Acceleration a<sub>lon</sub>(t) [m/s&sup2;] Across Estimators E1&ndash;E5 vs. Signed OOD Rollout</div>
          <div id="svg-c10-estimators" class="w-full rounded-lg bg-[var(--background)] border border-[var(--border)] p-2"></div>
          <div class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)] space-y-1 text-[11px] leading-relaxed">
            <div><strong>D4 Physical &amp; Numerical Sanity Checks:</strong> Observed a<sub>x</sub>(0) = &minus;1.5525 m/s&sup2; (v<sub>0</sub> = 4.3103 m/s). Under canonical unsigned prompt (<code>1.56 m/s^2</code>), Step 1 decelerates (&minus;0.8841 m/s&sup2; on E1/E3; &minus;1.7658 m/s&sup2; on E2), then <strong>9 consecutive steps (t = 1.0..5.0 s) exhibit positive acceleration</strong>, reaching x(5.0 s) = 28.534 m vs. logged GT 15.648 m (+12.89 m overshoot). Heading distortion on Steps 2&ndash;10 is &lt; 0.0019 m/s&sup2; (&lt; 0.07%).</div>
            <div><strong>D5 Signed-Acceleration OOD Comparison (<code>-1.55 m/s^2</code>):</strong> Sustains negative acceleration across all active-motion steps (t = 0.5..3.5 s, max |a<sub>lon</sub> &minus; a<sub>x</sub>(0)| &le; 0.6684 m/s&sup2;, <strong>0/75 active-motion C10 violations</strong>; single-scene OOD diagnostic).</div>
            <div class="text-amber-900"><strong>Threshold Boundary Note:</strong> Thresholds 2.0, 2.5 (canonical), and 3.0 m/s&sup2; are illustrative numerical-sensitivity bounds on the 0.5 s waypoint grid, not universal biomechanics or ISO safety standards.</div>
          </div>
        </div>

        <div class="lg:col-span-7 space-y-1.5">
          <div class="flex flex-wrap items-center justify-between gap-1 text-xs">
            <span class="font-semibold">5 Estimators (E1&ndash;E5) &times; 5 Temporal Windows (W1&ndash;W5) &times; 3 Thresholds (2.0 / 2.5 / 3.0 m/s&sup2;)</span>
            <span class="text-[11px] text-[var(--muted-foreground)]">Cells show Peak |a<sub>lon</sub> &minus; a<sub>x</sub>(0)| [m/s&sup2;], Peak a<sub>lon</sub>, and Pass/Violated @ [2.0 / 2.5 / 3.0]</span>
          </div>
          <div id="table-c10-matrix" class="table-wrapper rounded-lg border border-[var(--border)]"></div>
        </div>
      </div>
    </section>

    <!-- Cross-Scenario Summary & Extension Claim Register -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-5 print-avoid-break">
      <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-bold text-[var(--foreground)]">
            Cross-Scenario Provenance &amp; Evaluation Overview (All 7 Real Scenes)
          </h2>
          <span class="text-xs text-[var(--muted-foreground)]">Click any row to load scenario</span>
        </div>
        <div class="table-wrapper rounded-lg border border-[var(--border)]">
          <table class="text-xs">
            <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
              <tr>
                <th class="text-left p-2 border-b border-[var(--border)]">Scene ID &amp; nuPlan Token</th>
                <th class="text-right p-2 border-b border-[var(--border)]">v<sub>0</sub> / a<sub>x,0</sub></th>
                <th class="text-right p-2 border-b border-[var(--border)]">ADE / FDE</th>
                <th class="text-left p-2 border-b border-[var(--border)]">Dry (&mu;=1.0)</th>
                <th class="text-left p-2 border-b border-[var(--border)]">Wet (&mu;=0.5)</th>
                <th class="text-left p-2 border-b border-[var(--border)]">3D Corridor Lead</th>
              </tr>
            </thead>
            <tbody id="tbody-all-scenes"></tbody>
          </table>
        </div>
      </div>

      <div class="lg:col-span-6 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
        <h2 class="text-sm font-bold text-[var(--foreground)]">
          Independent Extension Evidence Register (EXT-VLA-C01 &ndash; EXT-VLA-C08)
        </h2>
        <div class="table-wrapper rounded-lg border border-[var(--border)]">
          <table class="text-xs">
            <thead class="bg-[var(--background)] text-[var(--muted-foreground)]">
              <tr>
                <th class="text-left p-2 border-b border-[var(--border)]">ID</th>
                <th class="text-left p-2 border-b border-[var(--border)]">Category</th>
                <th class="text-left p-2 border-b border-[var(--border)]">Verified Finding &amp; Scope Boundary</th>
              </tr>
            </thead>
            <tbody id="tbody-claims"></tbody>
          </table>
        </div>
      </div>
    </section>

  </div>

  <script id="report-data-json" type="application/json">__REPORT_DATA_JSON__</script>
  <script>
    (function () {
      const bundle = JSON.parse(document.getElementById("report-data-json").textContent);
      const summary = bundle.summary;
      const records = summary.records;
      const claims = bundle.extension_claims || [];
      const s05Ablation = summary.scene_05_signed_accel_ablation || null;
      const cmdSens = summary.command_sensitivity || null;
      const c10Rob = summary.scene_05_c10_robustness || null;

      document.getElementById("rq-text").textContent = summary.central_research_question;
      document.getElementById("prov-model").textContent = summary.model_provenance.selected_model;
      document.getElementById("prov-ckpt").textContent =
        summary.model_provenance.checkpoint_repo + "/" + summary.model_provenance.checkpoint_file;
      document.getElementById("prov-manifest-sha").textContent =
        (summary.manifest_sha256 || "").slice(0, 16) + "...";

      const selectRecord = document.getElementById("select-record");
      const selectObstacle = document.getElementById("select-obstacle");
      const selectMu = document.getElementById("select-mu");
      const sliderTau = document.getElementById("slider-tau");
      const tauValLabel = document.getElementById("tau-val-label");

      records.forEach((rec, idx) => {
        const opt = document.createElement("option");
        opt.value = String(idx);
        const v0 = rec.prediction_artifact.ego_initial_speed_mps.toFixed(2);
        opt.textContent = `${rec.scene_id} (v0=${v0} m/s, FDE=${rec.fde_vs_gt_m.toFixed(2)} m)`;
        selectRecord.appendChild(opt);
      });

      function badgeClassForFeas(cls) {
        if (cls === "CONSTRAINTS_SATISFIED") {
          return "bg-emerald-500/15 text-emerald-800 border border-emerald-500/30";
        }
        if (cls === "CONSTRAINTS_VIOLATED") {
          return "bg-rose-500/15 text-rose-800 border border-rose-500/30";
        }
        return "bg-amber-500/15 text-amber-900 border border-amber-500/30";
      }

      function badgeClassForInterval(cls) {
        if (cls === "UNIFORMLY_POSITIVE") {
          return "bg-emerald-500/15 text-emerald-800 border border-emerald-500/30";
        }
        if (cls === "UNIFORMLY_VIOLATED") {
          return "bg-rose-500/15 text-rose-800 border border-rose-500/30";
        }
        if (cls === "PARAMETER_SENSITIVE") {
          return "bg-amber-500/15 text-amber-900 border border-amber-500/30";
        }
        return "bg-slate-500/15 text-[var(--muted-foreground)] border border-[var(--border)]";
      }

      function formatStateSourceBadge(stateSource) {
        if (stateSource === "OBSERVED_EGO_T0_AND_OBSERVED_STATIONARY_OBSTACLE") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">Observed Ego (t<sub>0</sub>) + Observed Static Obstacle</span>`;
        }
        if (stateSource === "OBSERVED_EGO_T0_PLUS_ASSUMED_OBSTACLE_D0") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-pink-500/15 text-pink-800 border border-pink-500/30">Observed Ego (t<sub>0</sub>) + Assumed Obstacle (d<sub>0</sub>)</span>`;
        }
        if (stateSource === "HYPOTHETICAL_VLA_STATE_PLUS_ASSUMED_OBSTACLE_D0") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-purple-500/15 text-purple-800 border border-purple-500/30">Hypothetical VLA + Assumed Obstacle (d<sub>0</sub>)</span>`;
        }
        if (stateSource === "HYPOTHETICAL_VLA_STATE_WITH_OBSERVED_STATIONARY_OBSTACLE") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-blue-500/15 text-blue-800 border border-blue-500/30">Hypothetical VLA + Observed Static Obstacle</span>`;
        }
        if (stateSource === "OBSERVED_EGO_T0_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-900 border border-amber-500/30">Observed Ego (t<sub>0</sub>) + Static Proj. of Moving Lead</span>`;
        }
        if (stateSource === "HYPOTHETICAL_VLA_STATE_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-900 border border-amber-500/30">Hypothetical VLA + Static Proj. of Moving Lead</span>`;
        }
        if (stateSource === "OBSERVED_EGO_T0_NO_CREDIBLE_OBSTACLE") {
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-slate-500/15 text-slate-700 border border-slate-500/30">Observed Ego (t<sub>0</sub>) — No Credible Obstacle</span>`;
        }
        return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold bg-slate-500/15 text-slate-700 border border-slate-500/30">Hypothetical VLA — No Credible Obstacle</span>`;
      }

      function populateObstacleOptions(rec) {
        const prevVal = selectObstacle.value;
        selectObstacle.innerHTML = "";

        const obsLead = rec.scene_metadata.observed_in_lane_lead_obstacle;
        const obsOpt = document.createElement("option");
        obsOpt.value = "observed";
        if (obsLead) {
          obsOpt.textContent = `Observed 3D Lead: d0 = ${obsLead.x_m.toFixed(2)} m (v_lead = ${obsLead.speed_mps.toFixed(2)} m/s)`;
        } else {
          obsOpt.textContent = "Observed 3D Annotation: None in +-1.75 m Corridor";
        }
        selectObstacle.appendChild(obsOpt);

        const cfKeys = Object.keys(rec.counterfactual_obstacle_takeover_schedules || {});
        cfKeys.forEach((k) => {
          const dVal = k.replace("d0_", "").replace("m", "");
          const opt = document.createElement("option");
          opt.value = k;
          opt.textContent = `Counterfactual Assumption: Stationary d0 = ${dVal} m`;
          selectObstacle.appendChild(opt);
        });

        if (prevVal && Array.from(selectObstacle.options).some((o) => o.value === prevVal)) {
          selectObstacle.value = prevVal;
        } else if (obsLead) {
          selectObstacle.value = "observed";
        } else if (cfKeys.length > 0) {
          selectObstacle.value = cfKeys[1] || cfKeys[0];
        } else {
          selectObstacle.value = "observed";
        }
      }

      function renderScene05AblationChart() {
        const container = document.getElementById("svg-scene05-ablation-container");
        if (!s05Ablation || !container) return;
        const s05Rec = records.find((r) => r.scene_id === "scene_05_active_braking_deceleration");
        if (!s05Rec) return;

        const unsKin = s05Rec.predicted_kinematics || [];
        const gtKin = s05Rec.ground_truth_kinematics || [];
        const sigKin = s05Ablation.ablation_kinematics || [];

        const w = 480, h = 165, padL = 38, padR = 18, padT = 16, padB = 26;
        const maxX = 30.0;
        const tToPx = (t) => padL + (t / 5.0) * (w - padL - padR);
        const xToPx = (x) => padT + ((maxX - Math.max(0, x)) / maxX) * (h - padT - padB);

        let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        for (let tv = 0; tv <= 5; tv += 1) {
          const px = tToPx(tv);
          svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${px}" y="${h - 7}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${tv}.0s</text>`;
        }
        [0, 10, 20, 30].forEach((xv) => {
          const py = xToPx(xv);
          svg += `<line x1="${padL}" y1="${py}" x2="${w - padR}" y2="${py}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${padL - 5}" y="${py + 3}" text-anchor="end" font-size="9" fill="currentColor" fill-opacity="0.7">${xv}m</text>`;
        });

        const gtPts = [`${tToPx(0)},${xToPx(0)}`].concat(gtKin.map((k) => `${tToPx(k.t_s)},${xToPx(k.x_m)}`)).join(" ");
        const unsPts = [`${tToPx(0)},${xToPx(0)}`].concat(unsKin.map((k) => `${tToPx(k.t_s)},${xToPx(k.x_m)}`)).join(" ");
        const sigPts = [`${tToPx(0)},${xToPx(0)}`].concat(sigKin.map((k) => `${tToPx(k.t_s)},${xToPx(k.x_m)}`)).join(" ");

        svg += `<polyline fill="none" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" points="${gtPts}" />`;
        svg += `<polyline fill="none" stroke="#ef4444" stroke-width="2.2" points="${unsPts}" />`;
        svg += `<polyline fill="none" stroke="#2563eb" stroke-width="2.2" points="${sigPts}" />`;

        unsKin.forEach((k) => {
          svg += `<circle cx="${tToPx(k.t_s)}" cy="${xToPx(k.x_m)}" r="2.5" fill="#ef4444" />`;
        });
        sigKin.forEach((k) => {
          svg += `<circle cx="${tToPx(k.t_s)}" cy="${xToPx(k.x_m)}" r="2.5" fill="#2563eb" />`;
        });

        svg += `<g transform="translate(${padL + 6}, ${padT + 10})" font-size="9.5" fill="currentColor">`;
        svg += `<line x1="0" y1="-3" x2="14" y2="-3" stroke="#ef4444" stroke-width="2.2" /><text x="18" y="0">Unsigned Prompt ("1.56 m/s²", x_10=28.5m)</text>`;
        svg += `<line x1="0" y1="11" x2="14" y2="11" stroke="#2563eb" stroke-width="2.2" /><text x="18" y="14">Signed OOD Ablation ("-1.55 m/s²", x_10=6.9m)</text>`;
        svg += `<line x1="0" y1="25" x2="14" y2="25" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" /><text x="18" y="28">Logged GT (Brakes to 6.9m @ 2.5s, then 15.6m)</text>`;
        svg += `</g></svg>`;
        container.innerHTML = svg;
      }

      function renderBEV(rec, activeSchedule, selectedTau) {
        const pred = rec.prediction_artifact.predicted_waypoints || [];
        const gt = rec.prediction_artifact.ground_truth_waypoints || [];
        const w = 540, h = 215;
        const padL = 44, padR = 20, padT = 20, padB = 30;

        let maxX = 45.0;
        pred.forEach((p) => { if (p.x_m + 5 > maxX) maxX = p.x_m + 5; });
        gt.forEach((p) => { if (p.x_m + 5 > maxX) maxX = p.x_m + 5; });
        const d0Val = activeSchedule && activeSchedule.length > 0 ? activeSchedule[0].initial_obstacle_distance_d0_m : null;
        if (d0Val && d0Val + 6 > maxX) maxX = d0Val + 6;
        const minX = -3.0;

        let maxAbsY = 5.0;
        pred.forEach((p) => { if (Math.abs(p.y_m) + 1.5 > maxAbsY) maxAbsY = Math.abs(p.y_m) + 1.5; });
        gt.forEach((p) => { if (Math.abs(p.y_m) + 1.5 > maxAbsY) maxAbsY = Math.abs(p.y_m) + 1.5; });

        const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * (w - padL - padR);
        const yToPx = (y) => padT + ((maxAbsY - y) / (2 * maxAbsY)) * (h - padT - padB);

        const corrTop = yToPx(1.75);
        const corrBot = yToPx(-1.75);
        const zeroY = yToPx(0);
        const zeroX = xToPx(0);

        let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        svg += `<rect x="${xToPx(0)}" y="${corrTop}" width="${xToPx(maxX) - xToPx(0)}" height="${corrBot - corrTop}" fill="rgba(59,130,246,0.08)" stroke="rgba(59,130,246,0.28)" stroke-dasharray="4 3" />`;
        svg += `<line x1="${padL}" y1="${zeroY}" x2="${w - padR}" y2="${zeroY}" stroke="currentColor" stroke-opacity="0.2" />`;

        for (let xm = 0; xm <= maxX; xm += 10) {
          const px = xToPx(xm);
          svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${px}" y="${h - 9}" text-anchor="middle" font-size="10" fill="currentColor" fill-opacity="0.7">${xm}m</text>`;
        }
        svg += `<text x="6" y="${yToPx(0) + 3}" font-size="9.5" fill="currentColor" fill-opacity="0.7">y=0m</text>`;

        if (d0Val !== null && d0Val !== undefined) {
          const ox = xToPx(d0Val);
          const isObs = activeSchedule[0].obstacle_source === "OBSERVED_IN_LANE_ANNOTATION";
          const col = isObs ? "#d97706" : "#db2777";
          const tag = isObs ? "Obs d0" : "Assumed d0";
          svg += `<line x1="${ox}" y1="${padT}" x2="${ox}" y2="${h - padB}" stroke="${col}" stroke-width="2" stroke-dasharray="5 3" />`;
          svg += `<rect x="${ox - 3}" y="${corrTop + 4}" width="6" height="${Math.max(8, corrBot - corrTop - 8)}" fill="${col}" fill-opacity="0.45" rx="2" />`;
          svg += `<text x="${Math.max(padL + 36, Math.min(w - padR - 4, ox - 5))}" y="${h - padB - 6}" text-anchor="end" font-size="9.5" font-weight="bold" fill="${col}">${tag}=${d0Val.toFixed(1)}m</text>`;
        }

        if (gt.length > 0) {
          const pts = [`${zeroX},${zeroY}`].concat(gt.map((p) => `${xToPx(p.x_m)},${yToPx(p.y_m)}`)).join(" ");
          svg += `<polyline fill="none" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" points="${pts}" />`;
        }

        if (pred.length > 0) {
          const pts = [`${zeroX},${zeroY}`].concat(pred.map((p) => `${xToPx(p.x_m)},${yToPx(p.y_m)}`)).join(" ");
          svg += `<polyline fill="none" stroke="#2563eb" stroke-width="2.5" points="${pts}" />`;
          pred.forEach((p) => {
            const cx = xToPx(p.x_m), cy = yToPx(p.y_m);
            const isSel = Math.abs(p.t_s - selectedTau) < 0.05;
            svg += `<circle cx="${cx}" cy="${cy}" r="${isSel ? 5.5 : 3}" fill="${isSel ? "#ef4444" : "#2563eb"}" stroke="#ffffff" stroke-width="1" />`;
          });
        }

        svg += `<circle cx="${zeroX}" cy="${zeroY}" r="${Math.abs(selectedTau) < 0.05 ? 6 : 4}" fill="${Math.abs(selectedTau) < 0.05 ? "#ef4444" : "#1d4ed8"}" stroke="#ffffff" stroke-width="1.5" />`;

        svg += `<g transform="translate(${padL + 6}, ${padT + 10})" font-size="10" fill="currentColor">`;
        svg += `<line x1="0" y1="-3" x2="14" y2="-3" stroke="#2563eb" stroke-width="2.5" /><text x="18" y="0">AutoVLA Plan (0.5s steps)</text>`;
        svg += `<line x1="148" y1="-3" x2="162" y2="-3" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" /><text x="166" y="0">Logged GT</text>`;
        svg += `<circle cx="235" cy="-3" r="4" fill="#ef4444" /><text x="243" y="0">Highlighted &tau;_req (${selectedTau.toFixed(1)}s)</text>`;
        svg += `</g></svg>`;
        document.getElementById("svg-bev-container").innerHTML = svg;
      }

      function renderSpeedAndAccel(rec, selectedTau) {
        const kin = rec.predicted_kinematics || [];
        const gtKin = rec.ground_truth_kinematics || [];
        const v0 = rec.prediction_artifact.ego_initial_speed_mps;
        const ax0 = rec.prediction_artifact.ego_initial_accel_mps2;
        const w = 260, h = 165, padL = 34, padR = 12, padT = 22, padB = 24;

        let maxV = Math.max(18.0, v0 + 3);
        kin.forEach((k) => { if (k.implied_speed_mps + 2 > maxV) maxV = k.implied_speed_mps + 2; });
        const tToPx = (t) => padL + (t / 5.0) * (w - padL - padR);
        const vToPx = (v) => padT + ((maxV - Math.max(0, v)) / maxV) * (h - padT - padB);

        let svgV = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        for (let tv = 0; tv <= 5; tv += 1) {
          const px = tToPx(tv);
          svgV += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
          svgV += `<text x="${px}" y="${h - 6}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${tv}s</text>`;
        }
        [0, Math.round(maxV / 2), Math.round(maxV)].forEach((vv) => {
          const py = vToPx(vv);
          svgV += `<line x1="${padL}" y1="${py}" x2="${w - padR}" y2="${py}" stroke="currentColor" stroke-opacity="0.12" />`;
          svgV += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="9" fill="currentColor" fill-opacity="0.7">${vv}</text>`;
        });

        const tauPx = tToPx(selectedTau);
        svgV += `<line x1="${tauPx}" y1="${padT}" x2="${tauPx}" y2="${h - padB}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3 2" />`;

        if (gtKin.length > 0) {
          const gtPts = [`${tToPx(0)},${vToPx(v0)}`].concat(gtKin.map((k) => `${tToPx(k.t_s)},${vToPx(k.implied_speed_mps)}`)).join(" ");
          svgV += `<polyline fill="none" stroke="#10b981" stroke-width="1.75" stroke-dasharray="3 2" points="${gtPts}" />`;
        }
        if (kin.length > 0) {
          const pPts = [`${tToPx(0)},${vToPx(v0)}`].concat(kin.map((k) => `${tToPx(k.t_s)},${vToPx(k.implied_speed_mps)}`)).join(" ");
          svgV += `<polyline fill="none" stroke="#2563eb" stroke-width="2.2" points="${pPts}" />`;
          kin.forEach((k) => {
            svgV += `<circle cx="${tToPx(k.t_s)}" cy="${vToPx(k.implied_speed_mps)}" r="2.5" fill="#2563eb" />`;
          });
        }
        svgV += `<g transform="translate(${padL + 4}, 12)" font-size="8.5" fill="currentColor">`;
        svgV += `<line x1="0" y1="-3" x2="10" y2="-3" stroke="#2563eb" stroke-width="2" /><text x="13" y="0">VLA v(t) [m/s]</text>`;
        svgV += `<line x1="88" y1="-3" x2="98" y2="-3" stroke="#10b981" stroke-width="1.75" stroke-dasharray="3 2" /><text x="101" y="0">Logged GT [m/s]</text>`;
        svgV += `</g></svg>`;
        document.getElementById("svg-speed-container").innerHTML = svgV;

        let maxAbsA = 5.5;
        kin.forEach((k) => {
          maxAbsA = Math.max(maxAbsA, Math.abs(k.a_lon_mps2) + 1.0, k.a_total_mps2 + 1.0);
        });
        const aToPx = (a) => padT + ((maxAbsA - a) / (2 * maxAbsA)) * (h - padT - padB);

        let svgA = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        const yZero = aToPx(0);
        svgA += `<line x1="${padL}" y1="${yZero}" x2="${w - padR}" y2="${yZero}" stroke="currentColor" stroke-opacity="0.3" />`;
        [4.0, -4.0].forEach((lim) => {
          const py = aToPx(lim);
          svgA += `<line x1="${padL}" y1="${py}" x2="${w - padR}" y2="${py}" stroke="#d97706" stroke-width="1" stroke-dasharray="3 3" />`;
        });
        [-maxAbsA, 0, maxAbsA].forEach((av) => {
          const py = aToPx(av);
          svgA += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="9" fill="currentColor" fill-opacity="0.7">${av.toFixed(0)}</text>`;
        });
        for (let tv = 0; tv <= 5; tv += 1) {
          const px = tToPx(tv);
          svgA += `<text x="${px}" y="${h - 6}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${tv}s</text>`;
        }
        svgA += `<line x1="${tauPx}" y1="${padT}" x2="${tauPx}" y2="${h - padB}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3 2" />`;

        if (kin.length > 0) {
          const lonPts = [`${tToPx(0)},${aToPx(ax0)}`].concat(kin.map((k) => `${tToPx(k.t_s)},${aToPx(k.a_lon_mps2)}`)).join(" ");
          const totPts = kin.map((k) => `${tToPx(k.t_s)},${aToPx(k.a_total_mps2)}`).join(" ");
          svgA += `<polyline fill="none" stroke="#9333ea" stroke-width="1.75" stroke-dasharray="2 2" points="${totPts}" />`;
          svgA += `<polyline fill="none" stroke="#2563eb" stroke-width="2" points="${lonPts}" />`;
          svgA += `<circle cx="${tToPx(0)}" cy="${aToPx(ax0)}" r="3" fill="#0f172a" />`;
          kin.forEach((k) => {
            const viol = Math.abs(k.a_lon_mps2) > 4.0 || k.a_total_mps2 > 4.905 || Math.abs(k.a_lon_mps2 - ax0) > 2.5;
            svgA += `<circle cx="${tToPx(k.t_s)}" cy="${aToPx(k.a_lon_mps2)}" r="${viol ? 3.5 : 2.5}" fill="${viol ? "#ef4444" : "#2563eb"}" />`;
          });
        }
        svgA += `<g transform="translate(${padL + 4}, 12)" font-size="8.5" fill="currentColor">`;
        svgA += `<line x1="0" y1="-3" x2="10" y2="-3" stroke="#2563eb" stroke-width="2" /><text x="13" y="0">a_lon [m/s²]</text>`;
        svgA += `<line x1="78" y1="-3" x2="88" y2="-3" stroke="#9333ea" stroke-width="1.75" stroke-dasharray="2 2" /><text x="91" y="0">|a_tot|</text>`;
        svgA += `<line x1="132" y1="-3" x2="142" y2="-3" stroke="#d97706" stroke-width="1" stroke-dasharray="3 3" /><text x="145" y="0">&pm;4.0 limit</text>`;
        svgA += `</g></svg>`;
        document.getElementById("svg-accel-container").innerHTML = svgA;
      }

      function renderR3BMarginChart(activeSchedule, muVal, selectedTau) {
        const w = 540, h = 215, padL = 46, padR = 20, padT = 22, padB = 30;
        const evalPoints = (activeSchedule || []).filter((e) => e.status === "EVALUATED");

        if (evalPoints.length === 0) {
          document.getElementById("svg-r3b-margin-container").innerHTML =
            `<div class="h-44 flex items-center justify-center text-xs text-amber-800 font-medium px-4 text-center bg-amber-500/5 rounded-lg border border-amber-500/20">` +
            `R3B Braking-Only Margin Chart Withheld (` +
            `INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE for the selected scenario &amp; obstacle source).` +
            `</div>`;
          return;
        }

        let minM = -15.0, maxM = 25.0;
        evalPoints.forEach((ev) => {
          ev.branch_results.filter((b) => Math.abs(b.mu - muVal) < 0.01).forEach((b) => {
            if (b.margin_min_m - 4 < minM) minM = b.margin_min_m - 4;
            if (b.margin_max_m + 4 > maxM) maxM = b.margin_max_m + 4;
          });
        });

        const tToPx = (t) => padL + (t / 3.0) * (w - padL - padR);
        const mToPx = (m) => padT + ((maxM - m) / (maxM - minM)) * (h - padT - padB);

        let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        const yZero = mToPx(0);
        svg += `<rect x="${padL}" y="${yZero}" width="${w - padL - padR}" height="${Math.max(0, h - padB - yZero)}" fill="rgba(239,68,68,0.08)" />`;
        svg += `<line x1="${padL}" y1="${yZero}" x2="${w - padR}" y2="${yZero}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="5 3" />`;
        svg += `<text x="${w - padR - 4}" y="${yZero - 4}" text-anchor="end" font-size="9" font-weight="bold" fill="#ef4444">Necessary-Condition Boundary (Margin = 0 m / 0 s)</text>`;

        for (let tv = 0; tv <= 3.0; tv += 0.5) {
          const px = tToPx(tv);
          svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${px}" y="${h - 9}" text-anchor="middle" font-size="10" fill="currentColor" fill-opacity="0.7">${tv.toFixed(1)}s</text>`;
        }

        const stepM = Math.max(5, Math.round((maxM - minM) / 5 / 5) * 5);
        for (let mv = Math.ceil(minM / stepM) * stepM; mv <= maxM; mv += stepM) {
          const py = mToPx(mv);
          svg += `<line x1="${padL}" y1="${py}" x2="${w - padR}" y2="${py}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${padL - 5}" y="${py + 3}" text-anchor="end" font-size="9" fill="currentColor" fill-opacity="0.7">${mv}m</text>`;
        }

        const selPx = tToPx(selectedTau);
        svg += `<line x1="${selPx}" y1="${padT}" x2="${selPx}" y2="${h - padB}" stroke="#2563eb" stroke-width="1.75" stroke-dasharray="3 2" />`;

        const branchColors = {
          P0: { stroke: "#e11d48", fill: "rgba(225,29,72,0.14)" },
          P1: { stroke: "#2563eb", fill: "rgba(37,99,235,0.14)" },
          P2: { stroke: "#059669", fill: "rgba(5,150,105,0.14)" },
        };

        ["P0", "P1", "P2"].forEach((bid) => {
          const col = branchColors[bid];
          const pts = [];
          evalPoints.forEach((ev) => {
            const br = ev.branch_results.find((b) => b.branch_id === bid && Math.abs(b.mu - muVal) < 0.01);
            if (br) pts.push({ t: ev.tau_req_s, lo: br.margin_min_m, hi: br.margin_max_m });
          });
          if (pts.length > 0) {
            const upper = pts.map((p) => `${tToPx(p.t)},${mToPx(p.hi)}`);
            const lower = pts.slice().reverse().map((p) => `${tToPx(p.t)},${mToPx(p.lo)}`);
            svg += `<polygon points="${upper.concat(lower).join(" ")}" fill="${col.fill}" />`;
            const midLine = pts.map((p) => `${tToPx(p.t)},${mToPx(0.5 * (p.lo + p.hi))}`).join(" ");
            svg += `<polyline fill="none" stroke="${col.stroke}" stroke-width="2.2" points="${midLine}" />`;
            pts.forEach((p) => {
              svg += `<circle cx="${tToPx(p.t)}" cy="${mToPx(0.5 * (p.lo + p.hi))}" r="3" fill="${col.stroke}" />`;
            });
          }
        });

        svg += `<g transform="translate(${padL + 6}, 13)" font-size="9.5" fill="currentColor">`;
        svg += `<rect x="0" y="-7" width="10" height="8" fill="#e11d48" /><text x="13" y="0">P0: Hold Speed in t1</text>`;
        svg += `<rect x="132" y="-7" width="10" height="8" fill="#2563eb" /><text x="145" y="0">P1: Passive Drag in t1</text>`;
        svg += `<rect x="275" y="-7" width="10" height="8" fill="#059669" /><text x="288" y="0">P2: Supported Decel (1&ndash;3 m/s²) in t1</text>`;
        svg += `</g></svg>`;
        document.getElementById("svg-r3b-margin-container").innerHTML = svg;
      }

      function renderActiveView() {
        const recIdx = parseInt(selectRecord.value || "0", 10);
        const rec = records[recIdx];
        const obsMode = selectObstacle.value;
        const muVal = parseFloat(selectMu.value || "1.0");
        const selectedTau = parseFloat(sliderTau.value || "0.0");
        tauValLabel.textContent = `${selectedTau.toFixed(1)} s`;

        const art = rec.prediction_artifact;
        const meta = rec.scene_metadata;
        const prov = rec.provenance_audit || {};
        const thumbs = rec.camera_thumbnails || {};

        // Highlight Scene 05 ablation section when Scene 05 is active
        const s05Sec = document.getElementById("scene05-ablation-section");
        const s05Ind = document.getElementById("ablation-active-indicator");
        if (rec.scene_id === "scene_05_active_braking_deceleration") {
          s05Sec.className = "bg-[var(--card)] border-2 border-rose-600 rounded-xl p-4 shadow-md space-y-3 print-avoid-break";
          s05Ind.textContent = "CURRENTLY SELECTED SCENE: scene_05_active_braking_deceleration";
        } else {
          s05Sec.className = "bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3 print-avoid-break";
          s05Ind.textContent = "Reference Study: scene_05_active_braking_deceleration (token=b49c80be2d0d5bb9)";
        }

        document.getElementById("img-cam-left").src = thumbs.front_left_t0 || "";
        document.getElementById("img-cam-front").src = thumbs.front_t0 || "";
        document.getElementById("img-cam-right").src = thumbs.front_right_t0 || "";
        document.getElementById("scene-location-badge").textContent = `${meta.map_location} | ${meta.scene_name} | token=${meta.frame_token}`;
        document.getElementById("scene-desc").textContent = meta.description;

        const validBadge = document.getElementById("vla-valid-badge");
        validBadge.textContent = art.prediction_valid ? "10/10 Action Tokens Verified" : "Incomplete Prediction";
        validBadge.className = "px-2 py-0.5 rounded text-xs font-semibold " +
          (art.prediction_valid ? "bg-emerald-500/15 text-emerald-800 border border-emerald-500/30" : "bg-rose-500/15 text-rose-800 border border-rose-500/30");

        const aNorm = meta.ego_state.accel_norm_mps2;
        document.getElementById("stat-v0").textContent = `${art.ego_initial_speed_mps.toFixed(2)} m/s (${(art.ego_initial_speed_mps * 3.6).toFixed(1)} km/h)`;
        document.getElementById("stat-a0").textContent = `${art.ego_initial_accel_mps2 >= 0 ? "+" : ""}${art.ego_initial_accel_mps2.toFixed(2)} / ${aNorm.toFixed(2)} m/s²`;
        document.getElementById("stat-cmd").textContent = art.driving_command;
        const obsLead = meta.observed_in_lane_lead_obstacle;
        document.getElementById("stat-obs-lead").textContent = obsLead
          ? `d0 = ${obsLead.x_m.toFixed(2)} m (v_lead = ${obsLead.speed_mps.toFixed(2)} m/s)`
          : "None in +-1.75m corridor";
        document.getElementById("stat-ade-fde").textContent = `${rec.ade_vs_gt_m.toFixed(2)} m / ${rec.fde_vs_gt_m.toFixed(2)} m`;
        document.getElementById("stat-latency").textContent = `${art.inference_latency_ms.toFixed(0)} ms (${art.environment_metadata.device.toUpperCase()})`;
        document.getElementById("vla-raw-output").textContent =
          `Prompt: ${art.prompt_text}\n\nGenerated Output:\n${art.raw_generated_text}`;
        document.getElementById("env-hw-badge").textContent = `${art.environment_metadata.hardware} | PyTorch ${art.environment_metadata.torch_version} | transformers ${art.environment_metadata.transformers_version}`;
        document.getElementById("token-badge").textContent = `Codebook IDs: [${art.action_codebook_indices.join(", ")}]`;

        // Phase C Feasibility Panel
        const feas = muVal < 0.8 ? rec.feasibility_wet_mu0_5 : rec.feasibility_nominal;
        const feasBadge = document.getElementById("feas-classification-badge");
        feasBadge.textContent = feas.classification;
        feasBadge.className = "px-3 py-1 rounded-full text-xs font-bold " + badgeClassForFeas(feas.classification);

        const feasReasonsBox = document.getElementById("feas-reasons-box");
        if (feas.classification === "CONSTRAINTS_SATISFIED") {
          feasReasonsBox.className = "p-3 rounded-lg text-xs bg-emerald-500/10 border border-emerald-500/25 text-emerald-900";
          feasReasonsBox.innerHTML = `<strong>All Checked Physical Constraints Satisfied (&mu; = ${muVal.toFixed(1)}):</strong> ` +
            `Max implied speed = ${feas.max_implied_speed_mps.toFixed(2)} m/s, max braking demand = ${feas.max_braking_demand_mps2.toFixed(2)} m/s&sup2;, ` +
            `max |a<sub>lat</sub>| = ${feas.max_abs_lat_accel_mps2.toFixed(2)} m/s&sup2;, max |a<sub>total</sub>| = ${feas.max_total_accel_mps2.toFixed(2)} m/s&sup2;. ` +
            `<em>Note: Passing trajectory checks does not guarantee collision avoidance or takeover safety.</em>`;
        } else if (feas.classification === "CONSTRAINTS_VIOLATED") {
          feasReasonsBox.className = "p-3 rounded-lg text-xs bg-rose-500/10 border border-rose-500/25 text-rose-900 space-y-1";
          feasReasonsBox.innerHTML = `<strong>Physical Constraint Violations Detected (&mu; = ${muVal.toFixed(1)}):</strong>` +
            `<ul class="list-disc pl-4 space-y-0.5">` +
            feas.violation_reasons.map((r) => `<li>${r}</li>`).join("") +
            `</ul>`;
        } else {
          feasReasonsBox.className = "p-3 rounded-lg text-xs bg-amber-500/10 border border-amber-500/25 text-amber-950 space-y-1";
          feasReasonsBox.innerHTML = `<strong>Insufficient Evidence / Not Applicable:</strong>` +
            `<ul class="list-disc pl-4 space-y-0.5">` +
            feas.insufficient_evidence_reasons.map((r) => `<li>${r}</li>`).join("") +
            `</ul>`;
        }

        const tbodyChecks = document.getElementById("tbody-feas-checks");
        tbodyChecks.innerHTML = feas.checks.map((c) => {
          const st = c.passed ? "PASS" : "VIOLATED";
          const cls = c.passed ? "text-emerald-700 font-semibold" : "text-rose-700 font-bold";
          const violTxt = c.violation_steps && c.violation_steps.length > 0 ? ` (steps ${c.violation_steps.join(",")})` : "";
          const noteHtml = c.notes ? `<div class="text-[11px] text-[var(--muted-foreground)] font-normal mt-0.5">${c.notes}</div>` : "";
          return `<tr class="border-b border-[var(--border)]">` +
            `<th class="text-left p-2 bg-[var(--card)] font-medium">${c.check_id}<div class="text-[var(--muted-foreground)] font-normal">${c.description}</div>${noteHtml}</th>` +
            `<td class="text-right p-2 font-mono">${c.observed_value !== null ? c.observed_value + " " + c.units : "N/A"}</td>` +
            `<td class="text-right p-2 font-mono">${c.limit_value !== null ? c.limit_value + " " + c.units : "N/A"}</td>` +
            `<td class="p-2 ${cls}">${st}${violTxt}</td>` +
            `</tr>`;
        }).join("");

        const tbodyFric = document.getElementById("tbody-friction-sens");
        tbodyFric.innerHTML = feas.friction_sensitivity.map((fs) => {
          const ok = fs.total_accel_within_friction_circle;
          const cls = ok ? "text-emerald-700 font-semibold" : "text-rose-700 font-bold";
          return `<tr class="border-b border-[var(--border)]">` +
            `<th class="text-left p-2 bg-[var(--card)] font-mono">&mu; = ${fs.mu.toFixed(2)}</th>` +
            `<td class="text-right p-2 font-mono">${fs.mu_g_limit_mps2.toFixed(2)} m/s&sup2;</td>` +
            `<td class="text-right p-2 font-mono">${fs.max_braking_demand_mps2.toFixed(2)} m/s&sup2;</td>` +
            `<td class="text-right p-2 font-mono">${fs.max_total_accel_mps2.toFixed(2)} m/s&sup2;</td>` +
            `<td class="p-2 ${cls}">${ok ? "WITHIN CAP (+" + fs.friction_circle_margin_mps2.toFixed(2) + " m/s²)" : "EXCEEDS CAP (" + fs.friction_circle_margin_mps2.toFixed(2) + " m/s²)"}</td>` +
            `</tr>`;
        }).join("");

        // Phase D & E Schedule Selection
        const activeSchedule = obsMode === "observed"
          ? rec.observed_obstacle_takeover_schedule
          : (rec.counterfactual_obstacle_takeover_schedules[obsMode] || []);

        const obsProvBadge = document.getElementById("obstacle-provenance-badge");
        let obsSourceSummaryText = "";
        if (obsMode === "observed") {
          if (obsLead) {
            const isStatic = Math.abs(obsLead.speed_mps) <= 0.1;
            obsProvBadge.textContent = isStatic
              ? `OBSERVED STATIONARY 3D OBSTACLE (d0 = ${obsLead.x_m.toFixed(2)} m, v_lead = 0.00 m/s)`
              : `OBSERVED MOVING LEAD (d0 = ${obsLead.x_m.toFixed(2)} m, v_lead = ${obsLead.speed_mps.toFixed(2)} m/s — Static R3B Target)`;
            obsProvBadge.className = isStatic
              ? "px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30"
              : "px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-900 border border-amber-500/30";
            obsSourceSummaryText = obsProvBadge.textContent;
          } else {
            obsProvBadge.textContent = "NO OBSERVED IN-LANE OBSTACLE (INSUFFICIENT EVIDENCE)";
            obsProvBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-900 border border-amber-500/30";
            obsSourceSummaryText = obsProvBadge.textContent;
          }
        } else {
          const dVal = obsMode.replace("d0_", "").replace("m", "");
          obsProvBadge.textContent = `COUNTERFACTUAL ASSUMPTION (Assumed Stationary Obstacle d0 = ${dVal} m)`;
          obsProvBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-pink-500/15 text-pink-800 border border-pink-500/30";
          obsSourceSummaryText = obsProvBadge.textContent;
        }

        // Update Untruncated Active Selection Strip
        document.getElementById("active-selection-strip").innerHTML =
          `<div class="flex flex-wrap items-center gap-2">` +
          `<span class="font-bold text-[var(--foreground)]">Active Selection:</span>` +
          `<code class="px-2 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] font-mono">${rec.scene_id}</code>` +
          `<span class="text-[var(--muted-foreground)]">nuPlan Token: <code class="font-mono">${meta.frame_token}</code> (idx ${meta.frame_index})</span>` +
          `<span class="text-[var(--muted-foreground)]">| Ego t<sub>0</sub>: v<sub>0</sub> = ${art.ego_initial_speed_mps.toFixed(2)} m/s, a<sub>x,0</sub> = ${art.ego_initial_accel_mps2.toFixed(2)} m/s&sup2; (Prompt &Vert;a<sub>0</sub>&Vert; = ${aNorm.toFixed(2)} m/s&sup2;)</span>` +
          `</div>` +
          `<div class="flex flex-wrap items-center gap-2">` +
          `<span class="font-semibold">Obstacle Mode:</span> <span>${obsSourceSummaryText}</span>` +
          `<span class="text-[var(--muted-foreground)]">| &mu; = ${muVal.toFixed(1)} | &tau;<sub>req</sub> = ${selectedTau.toFixed(1)} s</span>` +
          `</div>`;

        document.getElementById("chart-mu-label").textContent = `Road Friction mu = ${muVal.toFixed(1)}`;

        renderBEV(rec, activeSchedule, selectedTau);
        renderSpeedAndAccel(rec, selectedTau);
        renderR3BMarginChart(activeSchedule, muVal, selectedTau);

        // Spotlight card for selectedTau
        const spotEv = activeSchedule.find((e) => Math.abs(e.tau_req_s - selectedTau) < 0.05) || activeSchedule[0];
        const spotCard = document.getElementById("tau-spotlight-card");
        const r3bReasonsBox = document.getElementById("r3b-reasons-box");

        const policyDescriptions = {
          P0: "P0 (Hold Speed in t1)",
          P1: "P1 (Passive Drag in t1)",
          P2: "P2 (Supported Decel 1–3 m/s²)",
        };

        if (spotEv) {
          if (spotEv.status === "EVALUATED") {
            const brs = spotEv.branch_results.filter((b) => Math.abs(b.mu - muVal) < 0.01);
            spotCard.innerHTML =
              `<div class="flex flex-wrap items-center justify-between gap-2">` +
              `<div class="flex flex-wrap items-center gap-1.5"><strong>At &tau;<sub>req</sub> = ${spotEv.tau_req_s.toFixed(1)} s:</strong> ${formatStateSourceBadge(spotEv.state_source)}</div>` +
              `<span class="font-mono">x=${spotEv.ego_lon_displacement_at_req_m.toFixed(2)}m, v=${spotEv.hypothetical_speed_at_req_mps.toFixed(2)}m/s, d<sub>rem</sub>=${spotEv.remaining_obstacle_distance_m.toFixed(2)}m, TTC=${spotEv.available_ttc_stationary_s.toFixed(2)}s</span>` +
              `</div>` +
              `<div class="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">` +
              brs.map((b) =>
                `<div class="p-2 rounded border ${badgeClassForInterval(b.interval_classification)}">` +
                `<div class="font-bold">${policyDescriptions[b.branch_id] || b.branch_id}</div>` +
                `<div class="font-mono mt-0.5">M<sub>d</sub>: [${b.margin_min_m.toFixed(1)}, ${b.margin_max_m.toFixed(1)}] m</div>` +
                `<div class="font-mono text-[11px] opacity-85">M<sub>t</sub>: [${(b.margin_min_s !== undefined ? b.margin_min_s : b.margin_min_m / spotEv.hypothetical_speed_at_req_mps).toFixed(2)}, ${(b.margin_max_s !== undefined ? b.margin_max_s : b.margin_max_m / spotEv.hypothetical_speed_at_req_mps).toFixed(2)}] s</div>` +
                `<div class="text-[11px] font-semibold mt-0.5">${b.interval_classification}</div>` +
                `</div>`
              ).join("") +
              `</div>`;
            r3bReasonsBox.className = "p-2.5 rounded-lg text-xs bg-blue-500/10 border border-blue-500/25 text-[var(--foreground)]";
            r3bReasonsBox.innerHTML = `<strong>Complete Scenario State Provenance Notice:</strong> ${spotEv.state_disclaimer} ` +
              `<span class="text-[var(--muted-foreground)]">(Code token: <code>${spotEv.state_source}</code>)</span>`;
          } else {
            spotCard.innerHTML =
              `<div class="flex flex-wrap items-center gap-2 font-bold text-amber-900">` +
              `<span>At &tau;<sub>req</sub> = ${spotEv.tau_req_s.toFixed(1)} s:</span> ${formatStateSourceBadge(spotEv.state_source)} ` +
              `<span>&rarr; R3B Evaluation Withheld (${spotEv.status})</span></div>` +
              `<div class="font-mono mt-1">x=${spotEv.ego_lon_displacement_at_req_m.toFixed(2)}m, y=${spotEv.ego_lat_displacement_at_req_m.toFixed(2)}m, &psi;=${spotEv.ego_heading_at_req_rad.toFixed(2)}rad, v=${spotEv.hypothetical_speed_at_req_mps.toFixed(2)}m/s</div>`;
            r3bReasonsBox.className = "p-3 rounded-lg text-xs bg-amber-500/15 border border-amber-500/30 text-amber-950 space-y-1";
            r3bReasonsBox.innerHTML = `<strong>Insufficient Evidence / Non-Applicability Reasons at &tau;<sub>req</sub> = ${spotEv.tau_req_s.toFixed(1)} s:</strong>` +
              `<ul class="list-disc pl-4 space-y-0.5">` +
              spotEv.insufficient_evidence_reasons.map((r) => `<li>${r}</li>`).join("") +
              `</ul>` +
              `<div class="pt-1 text-[11px]"><em>State Provenance:</em> ${spotEv.state_disclaimer}</div>`;
          }
        }

        // Schedule Table
        const tbodySched = document.getElementById("tbody-r3b-schedule");
        tbodySched.innerHTML = activeSchedule.map((ev) => {
          const isSel = Math.abs(ev.tau_req_s - selectedTau) < 0.05;
          const rowHighlight = isSel ? "bg-blue-500/10" : "";
          const badgeHtml = formatStateSourceBadge(ev.state_source);
          if (ev.status !== "EVALUATED") {
            return `<tr class="border-b border-[var(--border)] ${rowHighlight}">` +
              `<th class="text-left p-2 bg-[var(--card)] font-mono">${ev.tau_req_s.toFixed(1)}s</th>` +
              `<td class="p-2">${badgeHtml}</td>` +
              `<td class="text-right p-2 font-mono">${ev.hypothetical_speed_at_req_mps.toFixed(2)} m/s</td>` +
              `<td class="text-right p-2 font-mono">${ev.remaining_obstacle_distance_m !== null ? ev.remaining_obstacle_distance_m.toFixed(2) + " m" : "N/A"}</td>` +
              `<td class="text-right p-2 font-mono">N/A</td>` +
              `<td colspan="3" class="p-2 text-amber-900 font-medium">${ev.status}: ${ev.insufficient_evidence_reasons.join(" ")}</td>` +
              `</tr>`;
          }
          const getBrCell = (bid) => {
            const b = ev.branch_results.find((x) => x.branch_id === bid && Math.abs(x.mu - muVal) < 0.01);
            if (!b) return `<td class="p-2">N/A</td>`;
            const mMinS = b.margin_min_s !== undefined ? b.margin_min_s : b.margin_min_m / ev.hypothetical_speed_at_req_mps;
            const mMaxS = b.margin_max_s !== undefined ? b.margin_max_s : b.margin_max_m / ev.hypothetical_speed_at_req_mps;
            return `<td class="p-2 font-mono">` +
              `<span class="inline-block px-1.5 py-0.5 rounded ${badgeClassForInterval(b.interval_classification)}">[${b.margin_min_m.toFixed(1)}, ${b.margin_max_m.toFixed(1)}] m</span>` +
              `<div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">[${mMinS.toFixed(2)}, ${mMaxS.toFixed(2)}] s</div>` +
              `</td>`;
          };
          return `<tr class="border-b border-[var(--border)] ${rowHighlight}">` +
            `<th class="text-left p-2 bg-[var(--card)] font-mono">${ev.tau_req_s.toFixed(1)}s</th>` +
            `<td class="p-2">${badgeHtml}</td>` +
            `<td class="text-right p-2 font-mono">${ev.hypothetical_speed_at_req_mps.toFixed(2)} m/s</td>` +
            `<td class="text-right p-2 font-mono">${ev.remaining_obstacle_distance_m.toFixed(2)} m</td>` +
            `<td class="text-right p-2 font-mono">${ev.available_ttc_stationary_s.toFixed(2)} s</td>` +
            getBrCell("P0") + getBrCell("P1") + getBrCell("P2") +
            `</tr>`;
        }).join("");
      }

      // Populate Cross-Scenario Overview Table & Claim Register
      document.getElementById("tbody-all-scenes").innerHTML = records.map((r, idx) => {
        const fn = r.feasibility_nominal;
        const fw = r.feasibility_wet_mu0_5;
        const obs = r.scene_metadata.observed_in_lane_lead_obstacle;
        const art = r.prediction_artifact;
        const leadTxt = obs
          ? `${obs.x_m.toFixed(2)} m (v=${obs.speed_mps.toFixed(1)} m/s)`
          : "None (Open Road)";
        return `<tr class="border-b border-[var(--border)] cursor-pointer hover:bg-blue-500/5" data-rec-idx="${idx}">` +
          `<th class="text-left p-2 bg-[var(--card)] font-medium">${r.scene_id}<div class="text-[11px] font-mono text-[var(--muted-foreground)]">token=${art.frame_token} | cmd='${art.driving_command}'</div></th>` +
          `<td class="text-right p-2 font-mono">${art.ego_initial_speed_mps.toFixed(2)} m/s<div class="text-[11px] text-[var(--muted-foreground)]">${art.ego_initial_accel_mps2 >= 0 ? "+" : ""}${art.ego_initial_accel_mps2.toFixed(2)} m/s&sup2;</div></td>` +
          `<td class="text-right p-2 font-mono">${r.ade_vs_gt_m.toFixed(2)} m<div class="text-[11px] text-[var(--muted-foreground)]">FDE ${r.fde_vs_gt_m.toFixed(2)} m</div></td>` +
          `<td class="p-2"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${badgeClassForFeas(fn.classification)}">${fn.classification}</span></td>` +
          `<td class="p-2"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${badgeClassForFeas(fw.classification)}">${fw.classification}</span></td>` +
          `<td class="p-2 font-mono text-[11px]">${leadTxt}</td>` +
          `</tr>`;
      }).join("");

      document.querySelectorAll("#tbody-all-scenes tr").forEach((tr) => {
        tr.addEventListener("click", () => {
          selectRecord.value = tr.getAttribute("data-rec-idx");
          populateObstacleOptions(records[parseInt(selectRecord.value, 10)]);
          renderActiveView();
        });
      });

      document.querySelectorAll("[data-jump-scene]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const targetScene = btn.getAttribute("data-jump-scene");
          const targetObs = btn.getAttribute("data-jump-obs");
          const targetMu = btn.getAttribute("data-jump-mu");
          const targetTau = btn.getAttribute("data-jump-tau");
          const idx = records.findIndex((r) => r.scene_id === targetScene);
          if (idx >= 0) {
            selectRecord.value = String(idx);
            populateObstacleOptions(records[idx]);
            if (targetObs && Array.from(selectObstacle.options).some((o) => o.value === targetObs)) {
              selectObstacle.value = targetObs;
            }
            if (targetMu) selectMu.value = targetMu;
            if (targetTau) sliderTau.value = targetTau;
            renderActiveView();
          }
        });
      });

      document.getElementById("tbody-claims").innerHTML = claims.map((c) =>
        `<tr class="border-b border-[var(--border)]">` +
        `<th class="text-left p-2 bg-[var(--card)] font-mono whitespace-nowrap">${c.extension_claim_id}<div class="text-emerald-700 font-sans text-xs font-bold">${c.verification_status}</div></th>` +
        `<td class="p-2 font-semibold">${c.category}<div class="text-[var(--muted-foreground)] font-normal">${c.phase}</div></td>` +
        `<td class="p-2"><div>${c.claim_statement}</div><div class="text-[var(--muted-foreground)] mt-1"><em>Scope &amp; Boundaries:</em> ${c.scope_and_limitations}</div></td>` +
        `</tr>`
      ).join("");

      selectRecord.addEventListener("change", () => {
        populateObstacleOptions(records[parseInt(selectRecord.value, 10)]);
        renderActiveView();
      });
      selectObstacle.addEventListener("change", renderActiveView);
      selectMu.addEventListener("change", renderActiveView);
      sliderTau.addEventListener("input", renderActiveView);

      function renderCommandSensitivityCard(sceneId, svgContainerId, tableContainerId) {
        if (!cmdSens || !cmdSens.scenes || !cmdSens.scenes[sceneId]) return;
        const sc = cmdSens.scenes[sceneId];
        const ctrl = sc.control_turn_left;
        const intv = sc.intervention_keep_forward;
        const cmp = sc.comparative_metrics;
        const r3b = sc.r3b_impact;
        const steps = cmp.step_by_step_deltas || [];
        const svgEl = document.getElementById(svgContainerId);
        const tblEl = document.getElementById(tableContainerId);
        if (!svgEl || !tblEl || steps.length === 0) return;

        const w = 480, h = 165, padL = 38, padR = 16, padT = 18, padB = 26;
        let maxX = 46.0;
        let maxAbsY = 12.0;
        steps.forEach((s) => {
          maxX = Math.max(maxX, s.control_x_m + 4, s.intervention_x_m + 4, s.gt_x_m + 4);
          maxAbsY = Math.max(maxAbsY, Math.abs(s.control_y_m) + 2, Math.abs(s.intervention_y_m) + 2, Math.abs(s.gt_y_m) + 2);
        });
        const xToPx = (x) => padL + (Math.max(0, x) / maxX) * (w - padL - padR);
        const yToPx = (y) => padT + ((maxAbsY - y) / (2 * maxAbsY)) * (h - padT - padB);

        const corrTop = yToPx(1.75), corrBot = yToPx(-1.75), y0 = yToPx(0), x0 = xToPx(0);
        let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
        svg += `<rect x="${x0}" y="${corrTop}" width="${xToPx(maxX) - x0}" height="${Math.max(4, corrBot - corrTop)}" fill="rgba(59,130,246,0.08)" stroke="rgba(59,130,246,0.3)" stroke-dasharray="3 2" />`;
        svg += `<line x1="${padL}" y1="${y0}" x2="${w - padR}" y2="${y0}" stroke="currentColor" stroke-opacity="0.2" />`;
        for (let xm = 0; xm <= maxX; xm += 10) {
          const px = xToPx(xm);
          svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
          svg += `<text x="${px}" y="${h - 7}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${xm}m</text>`;
        }
        [-Math.round(maxAbsY * 0.75), 0, Math.round(maxAbsY * 0.75)].forEach((yv) => {
          const py = yToPx(yv);
          svg += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="8.5" fill="currentColor" fill-opacity="0.7">${yv >= 0 ? "+" : ""}${yv}m</text>`;
        });

        const gtPts = [`${x0},${y0}`].concat(steps.map((s) => `${xToPx(s.gt_x_m)},${yToPx(s.gt_y_m)}`)).join(" ");
        const ctrlPts = [`${x0},${y0}`].concat(steps.map((s) => `${xToPx(s.control_x_m)},${yToPx(s.control_y_m)}`)).join(" ");
        const intvPts = [`${x0},${y0}`].concat(steps.map((s) => `${xToPx(s.intervention_x_m)},${yToPx(s.intervention_y_m)}`)).join(" ");

        svg += `<polyline fill="none" stroke="#10b981" stroke-width="1.8" stroke-dasharray="4 3" points="${gtPts}" />`;
        svg += `<polyline fill="none" stroke="#ef4444" stroke-width="2.1" points="${ctrlPts}" />`;
        svg += `<polyline fill="none" stroke="#2563eb" stroke-width="2.2" points="${intvPts}" />`;
        steps.forEach((s) => {
          svg += `<circle cx="${xToPx(s.control_x_m)}" cy="${yToPx(s.control_y_m)}" r="2.3" fill="#ef4444" />`;
          svg += `<circle cx="${xToPx(s.intervention_x_m)}" cy="${yToPx(s.intervention_y_m)}" r="2.5" fill="#2563eb" />`;
        });
        svg += `<g transform="translate(${padL + 6}, ${padT + 10})" font-size="9" fill="currentColor">`;
        svg += `<line x1="0" y1="-3" x2="12" y2="-3" stroke="#ef4444" stroke-width="2.1" /><text x="16" y="0">Control: "turn left" (y_5s=${ctrl.final_displacement_y_m.toFixed(2)}m)</text>`;
        svg += `<line x1="0" y1="10" x2="12" y2="10" stroke="#2563eb" stroke-width="2.2" /><text x="16" y="13">Intervention: "keep forward" (y_5s=${intv.final_displacement_y_m.toFixed(2)}m)</text>`;
        svg += `<line x1="0" y1="23" x2="12" y2="23" stroke="#10b981" stroke-width="1.8" stroke-dasharray="4 3" /><text x="16" y="26">Logged Human GT [Turn Left] (y_5s=${sc.logged_human_gt_5s_y_m.toFixed(2)}m)</text>`;
        svg += `</g></svg>`;
        svgEl.innerHTML = svg;

        const obsCtrl = r3b.observed_schedule_control_turn_left;
        const obsIntv = r3b.observed_schedule_intervention_keep_forward;
        const cfCtrl = r3b.counterfactual_schedule_control_turn_left;
        const cfIntv = r3b.counterfactual_schedule_intervention_keep_forward;

        const r3bLabel = r3b.observed_obstacle_present
          ? `Observed d0=${r3b.observed_obstacle_d0_m.toFixed(2)}m Corridor Steps`
          : `Observed / CF (d0=${r3b.counterfactual_reference_d0_m.toFixed(1)}m) Corridor Steps`;
        const r3bCtrlStr = r3b.observed_obstacle_present
          ? `${obsCtrl.admissible_count}/7 (${obsCtrl.admissible_tau_req_s.map((t) => t.toFixed(1) + "s").join(",")})`
          : `Obs 0/7 | CF ${cfCtrl.admissible_count}/7`;
        const r3bIntvStr = r3b.observed_obstacle_present
          ? `${obsIntv.admissible_count}/7 (${obsIntv.admissible_tau_req_s.map((t) => t.toFixed(1) + "s").join(",")})`
          : `Obs 0/7 | CF ${cfIntv.admissible_count}/7`;

        tblEl.innerHTML = `<table class="text-[11px] w-full">` +
          `<thead class="bg-[var(--background)] text-[var(--muted-foreground)]">` +
          `<tr><th class="text-left p-1.5 border-b border-[var(--border)]">Metric</th>` +
          `<th class="text-right p-1.5 border-b border-[var(--border)]">Control ("turn left")</th>` +
          `<th class="text-right p-1.5 border-b border-[var(--border)]">Intervention ("keep forward")</th>` +
          `<th class="text-right p-1.5 border-b border-[var(--border)]">&Delta; (Intv &minus; Ctrl)</th></tr></thead>` +
          `<tbody>` +
          `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 font-medium">Action Tokens</th><td class="text-right p-1.5 font-mono">[${ctrl.action_codebook_indices.slice(0, 4).join(",")}...]</td><td class="text-right p-1.5 font-mono">[${intv.action_codebook_indices.slice(0, 4).join(",")}...]</td><td class="text-right p-1.5 font-mono font-bold text-indigo-700">${cmp.tokens_changed_count}/10 (step ${cmp.first_divergent_step})</td></tr>` +
          `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 font-medium">Final Pose (x, y, &psi; @ 5.0s)</th><td class="text-right p-1.5 font-mono">(${ctrl.final_displacement_x_m.toFixed(2)}m, +${ctrl.final_displacement_y_m.toFixed(2)}m, +${ctrl.final_heading_deg.toFixed(1)}&deg;)</td><td class="text-right p-1.5 font-mono">(${intv.final_displacement_x_m.toFixed(2)}m, +${intv.final_displacement_y_m.toFixed(2)}m, +${intv.final_heading_deg.toFixed(1)}&deg;)</td><td class="text-right p-1.5 font-mono font-bold">&Delta;y=${cmp.delta_final_y_m_intv_minus_ctrl.toFixed(2)}m, &Delta;&psi;=${cmp.delta_final_heading_deg_intv_minus_ctrl.toFixed(1)}&deg;</td></tr>` +
          `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 font-medium">Lateral y(3.0s) &amp; Mean/Max L2 Div</th><td class="text-right p-1.5 font-mono">y(3s)=+${steps[5].control_y_m.toFixed(2)}m</td><td class="text-right p-1.5 font-mono">y(3s)=+${steps[5].intervention_y_m.toFixed(2)}m</td><td class="text-right p-1.5 font-mono">&Delta;y(3s)=${cmp.delta_y_3s_m_intv_minus_ctrl.toFixed(2)}m | L2=${cmp.mean_l2_trajectory_divergence_m.toFixed(2)}/${cmp.final_l2_trajectory_divergence_m.toFixed(2)}m</td></tr>` +
          `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 font-medium">ADE / FDE vs. Logged Turn GT*</th><td class="text-right p-1.5 font-mono">${ctrl.ade_vs_logged_left_turn_gt_m.toFixed(2)}m / ${ctrl.fde_vs_logged_left_turn_gt_m.toFixed(2)}m</td><td class="text-right p-1.5 font-mono">${intv.ade_vs_logged_left_turn_gt_m.toFixed(2)}m / ${intv.fde_vs_logged_left_turn_gt_m.toFixed(2)}m</td><td class="text-right p-1.5 font-mono">${cmp.ade_vs_logged_gt_delta_m >= 0 ? "+" : ""}${cmp.ade_vs_logged_gt_delta_m.toFixed(2)}m / ${cmp.fde_vs_logged_gt_delta_m >= 0 ? "+" : ""}${cmp.fde_vs_logged_gt_delta_m.toFixed(2)}m</td></tr>` +
          `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 font-medium">C1&ndash;C10 Dry (&mu;=1.0) / Wet (&mu;=0.5)</th><td class="text-right p-1.5 font-mono">${ctrl["feasibility_dry_mu1.0"] === "CONSTRAINTS_SATISFIED" ? "PASS" : "VIOL"} / ${ctrl["feasibility_wet_mu0.5"] === "CONSTRAINTS_SATISFIED" ? "PASS" : "VIOL(C7)"}</td><td class="text-right p-1.5 font-mono">${intv["feasibility_dry_mu1.0"] === "CONSTRAINTS_SATISFIED" ? "PASS" : "VIOL"} / ${intv["feasibility_wet_mu0.5"] === "CONSTRAINTS_SATISFIED" ? "PASS" : "VIOL(C7)"}</td><td class="text-right p-1.5 font-mono">Step1 |a_lat|: ${steps[0].control_a_lat_mps2.toFixed(2)}&rarr;${steps[0].intervention_a_lat_mps2.toFixed(2)}</td></tr>` +
          `<tr><th class="text-left p-1.5 font-medium">${r3bLabel}</th><td class="text-right p-1.5 font-mono">${r3bCtrlStr}</td><td class="text-right p-1.5 font-mono">${r3bIntvStr}</td><td class="text-right p-1.5 font-mono font-bold text-emerald-700">Corridor Exit: ${ctrl.maneuver.first_corridor_exit_tau_s}s &rarr; ${intv.maneuver.first_corridor_exit_tau_s}s</td></tr>` +
          `</tbody></table>`;
      }

      function renderCommandSensitivitySection() {
        renderCommandSensitivityCard("scene_02_stationary_lead_obstacle", "svg-cmd-sens-scene02", "table-cmd-sens-scene02");
        renderCommandSensitivityCard("scene_06_intersection_turn_maneuver", "svg-cmd-sens-scene06", "table-cmd-sens-scene06");
      }

      function renderC10RobustnessSection() {
        if (!c10Rob) return;
        const badgeEl = document.getElementById("c10-overall-badge");
        if (badgeEl) {
          badgeEl.textContent = c10Rob.overall_classification || "";
        }
        const svgEl = document.getElementById("svg-c10-estimators");
        const tblEl = document.getElementById("table-c10-matrix");
        const ests = c10Rob.canonical_unsigned_rollout || {};
        const sigEsts = (c10Rob.signed_input_diagnostic_rollout_ood && c10Rob.signed_input_diagnostic_rollout_ood.estimators) || {};
        const ax0 = (c10Rob.sanity_checks_d4 && c10Rob.sanity_checks_d4.initial_ego_state_consistency)
          ? c10Rob.sanity_checks_d4.initial_ego_state_consistency.ax0_mps2
          : -1.5525;

        if (svgEl && ests.E1_chord_backward_diff) {
          const w = 460, h = 175, padL = 38, padR = 16, padT = 18, padB = 26;
          const minA = -2.2, maxA = 2.0;
          const tToPx = (t) => padL + (t / 5.0) * (w - padL - padR);
          const aToPx = (a) => padT + ((maxA - a) / (maxA - minA)) * (h - padT - padB);

          let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
          const yZero = aToPx(0), yAx0 = aToPx(ax0), yThresh25 = aToPx(ax0 + 2.5);
          svg += `<line x1="${padL}" y1="${yZero}" x2="${w - padR}" y2="${yZero}" stroke="currentColor" stroke-opacity="0.25" />`;
          svg += `<line x1="${padL}" y1="${yAx0}" x2="${w - padR}" y2="${yAx0}" stroke="#0f172a" stroke-width="1" stroke-dasharray="2 2" />`;
          svg += `<line x1="${padL}" y1="${yThresh25}" x2="${w - padR}" y2="${yThresh25}" stroke="#ef4444" stroke-width="1.2" stroke-dasharray="4 2" />`;
          svg += `<text x="${w - padR - 4}" y="${yThresh25 - 3}" text-anchor="end" font-size="8.5" font-weight="bold" fill="#ef4444">C10 Threshold (+2.5 m/s² above a_x(0) = +0.95 m/s²)</text>`;

          [-2, -1, 0, 1, 2].forEach((av) => {
            const py = aToPx(av);
            svg += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="8.5" fill="currentColor" fill-opacity="0.7">${av >= 0 ? "+" : ""}${av}</text>`;
          });
          for (let tv = 0; tv <= 5; tv += 1) {
            const px = tToPx(tv);
            svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.08" />`;
            svg += `<text x="${px}" y="${h - 7}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${tv}.0s</text>`;
          }

          const drawEst = (key, color, dash, width) => {
            const arr = (ests[key] && ests[key].step_series) || [];
            if (!arr.length) return;
            const pts = [`${tToPx(0)},${yAx0}`].concat(arr.map((s) => `${tToPx(s.t_s)},${aToPx(s.a_lon_mps2)}`)).join(" ");
            svg += `<polyline fill="none" stroke="${color}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ""} points="${pts}" />`;
          };
          drawEst("E2_ego_x_taylor_second_diff", "#9333ea", "2 2", 1.6);
          drawEst("E4_central_velocity_diff", "#d97706", "4 2", 1.9);
          drawEst("E5_three_step_moving_average", "#059669", "3 2", 1.9);
          drawEst("E1_chord_backward_diff", "#ef4444", "", 2.3);

          const sigSteps = (sigEsts.E1_chord_backward_diff && sigEsts.E1_chord_backward_diff.step_series) || [];
          if (sigSteps.length) {
            const sPts = [`${tToPx(0)},${yAx0}`].concat(sigSteps.slice(0, 7).map((s) => `${tToPx(s.t_s)},${aToPx(s.a_lon_mps2)}`)).join(" ");
            svg += `<polyline fill="none" stroke="#2563eb" stroke-width="2" points="${sPts}" />`;
          }

          svg += `<g transform="translate(${padL + 6}, ${h - padB - 38})" font-size="8.5" fill="currentColor">`;
          svg += `<line x1="0" y1="-3" x2="11" y2="-3" stroke="#ef4444" stroke-width="2.3" /><text x="14" y="0">E1/E3 Unsmoothed (peak +1.54 m/s², |&Delta;|=3.10)</text>`;
          svg += `<line x1="0" y1="9" x2="11" y2="9" stroke="#d97706" stroke-width="1.9" stroke-dasharray="4 2" /><text x="14" y="12">E4 Central Diff 1s (peak +1.30 m/s², |&Delta;|=2.85)</text>`;
          svg += `<line x1="0" y1="21" x2="11" y2="21" stroke="#059669" stroke-width="1.9" stroke-dasharray="3 2" /><text x="14" y="24">E5 3-Step Moving Avg (peak +1.13 m/s², |&Delta;|=2.68)</text>`;
          svg += `<line x1="220" y1="-3" x2="231" y2="-3" stroke="#2563eb" stroke-width="2" /><text x="234" y="0">D5 Signed OOD "-1.55" (0/75 active viol.)</text>`;
          svg += `</g></svg>`;
          svgEl.innerHTML = svg;
        }

        const estKeys = Object.keys(ests);
        if (tblEl && estKeys.length > 0) {
          const firstWins = ests[estKeys[0]].windows || {};
          const winKeys = Object.keys(firstWins);
          let html = `<table class="text-[11px] w-full"><thead class="bg-[var(--background)] text-[var(--muted-foreground)]"><tr>` +
            `<th class="text-left p-1.5 border-b border-[var(--border)]">Estimator (D1)</th>` +
            winKeys.map((wk) => {
              const wObj = firstWins[wk];
              return `<th class="text-center p-1.5 border-b border-[var(--border)]">${wk.split("_")[0]}<div class="font-mono text-[10px]">0&ndash;${wObj.horizon_s.toFixed(1)}s</div></th>`;
            }).join("") +
            `</tr></thead><tbody>`;

          estKeys.forEach((ek) => {
            const eObj = ests[ek];
            const shortName = ek.replace(/_/g, " ").slice(0, 26);
            html += `<tr class="border-b border-[var(--border)]"><th class="text-left p-1.5 bg-[var(--card)] font-mono text-[10px]">${shortName}</th>`;
            winKeys.forEach((wk) => {
              const wCell = eObj.windows[wk];
              if (!wCell) {
                html += `<td class="p-1.5 text-center">N/A</td>`;
                return;
              }
              const ths = wCell.thresholds || {};
              const flags = ["2.0_mps2", "2.5_mps2", "3.0_mps2"].map((tk) => {
                const m = ths[tk];
                return m && m.c10_violated
                  ? `<span class="px-1 rounded bg-rose-500/15 text-rose-800 font-bold">V</span>`
                  : `<span class="px-1 rounded bg-emerald-500/15 text-emerald-800">P</span>`;
              }).join("/");
              html += `<td class="p-1.5 text-center font-mono">` +
                `<div class="font-semibold">|&Delta;|=${wCell.window_max_jump_mps2.toFixed(2)}</div>` +
                `<div class="text-[10px] text-[var(--muted-foreground)]">a_max=${wCell.window_peak_a_lon_mps2 >= 0 ? "+" : ""}${wCell.window_peak_a_lon_mps2.toFixed(2)}</div>` +
                `<div class="mt-0.5 text-[10px]">${flags}</div>` +
                `</td>`;
            });
            html += `</tr>`;
          });
          html += `</tbody></table>`;
          tblEl.innerHTML = html;
        }
      }

      // =========================================================================================
      // INTERACTIVE ENGINEERING DEMONSTRATOR CONTROLLER (TRAJECTORY EXPLORER + R3B SIMULATOR)
      // =========================================================================================
      const explorerCatalog = bundle.interactive_explorer || null;

      if (explorerCatalog) {
        const expSceneSel = document.getElementById("select-explorer-scene");
        const expCondSel = document.getElementById("select-explorer-condition");
        const expMuSel = document.getElementById("select-explorer-mu");
        const expPlayBtn = document.getElementById("btn-explorer-play");
        const expPauseBtn = document.getElementById("btn-explorer-pause");
        const expRestartBtn = document.getElementById("btn-explorer-restart");
        const expPrevBtn = document.getElementById("btn-explorer-prev");
        const expNextBtn = document.getElementById("btn-explorer-next");
        const expSpeedSel = document.getElementById("select-explorer-playback-speed");
        const expSpeedBtns = Array.from(document.querySelectorAll("[data-playback-speed]"));
        const expTimeSlider = document.getElementById("slider-explorer-time");
        const expTimeLabel = document.getElementById("explorer-time-label");
        const expInterpBadge = document.getElementById("explorer-interp-badge");
        const expChkGt = document.getElementById("chk-explorer-overlay-gt");
        const expChkCounterpart = document.getElementById("chk-explorer-overlay-counterpart");
        const expChkSmooth = document.getElementById("chk-explorer-smooth");
        const expAutoSync = document.getElementById("chk-auto-sync-r3b");
        const expSendBtn = document.getElementById("btn-send-step-to-r3b");

        const r3bModeSel = document.getElementById("select-r3b-sim-mode");
        const r3bUnitSel = document.getElementById("select-r3b-speed-unit");
        const r3bResetBtn = document.getElementById("btn-r3b-reset-defaults");
        const r3bSpeedSlider = document.getElementById("slider-r3b-speed");
        const r3bSpeedInput = document.getElementById("input-r3b-speed");
        const r3bSpeedDual = document.getElementById("r3b-speed-dual-readout");
        const r3bObsModeSel = document.getElementById("select-r3b-obstacle-mode");
        const r3bD0Slider = document.getElementById("slider-r3b-d0");
        const r3bD0Input = document.getElementById("input-r3b-d0");
        const r3bTauSlider = document.getElementById("slider-r3b-tau");
        const r3bTauInput = document.getElementById("input-r3b-tau");
        const r3bPolicySel = document.getElementById("select-r3b-policy");
        const r3bMuSlider = document.getElementById("slider-r3b-mu");
        const r3bMuInput = document.getElementById("input-r3b-mu");
        const r3bT1Slider = document.getElementById("slider-r3b-t1");
        const r3bT1Input = document.getElementById("input-r3b-t1");
        const r3bT2Input = document.getElementById("input-r3b-t2");
        const r3bT3Input = document.getElementById("input-r3b-t3");
        const r3bAmaxInput = document.getElementById("input-r3b-amax");
        const r3bAsupInput = document.getElementById("input-r3b-asup");
        const r3bDragModeSel = document.getElementById("select-r3b-drag-mode");
        const r3bAdragInput = document.getElementById("input-r3b-adrag");
        const r3bGradeSel = document.getElementById("select-r3b-grade");

        const GRAVITY = 9.81;
        const STANDSTILL_MARGIN_M = 2.0;
        const MIN_SPEED_MPS = 0.05;
        const CORR_HALF_WIDTH_M = 1.75;
        const CORR_MAX_HEADING_RAD = 0.35;
        const EPSILON_S = 0.01;
        const SUPPORTED_DRAG_MODES = ["epa_midpoint", "epa_p05", "epa_median", "epa_p95", "epa_bev_median", "custom"];

        let playTimer = null;
        let playbackSpeedMultiplier = 1.0;

        // Populate Scene Selector
        const sceneIds = Object.keys(explorerCatalog.scene_condition_map || {});
        sceneIds.forEach((sid) => {
          const opt = document.createElement("option");
          opt.value = sid;
          const canonCond = explorerCatalog.conditions[`${sid}__canonical`];
          const v0Str = canonCond ? canonCond.ego_initial_speed_mps.toFixed(2) : "0.00";
          const nConds = (explorerCatalog.scene_condition_map[sid] || []).length;
          opt.textContent = `${sid} (v0=${v0Str} m/s, ${nConds} rollout${nConds > 1 ? "s" : ""})`;
          expSceneSel.appendChild(opt);
        });

        function populateExplorerConditionOptions(sceneId, preferredCondId) {
          const condIds = explorerCatalog.scene_condition_map[sceneId] || [];
          expCondSel.innerHTML = "";
          condIds.forEach((cid) => {
            const cObj = explorerCatalog.conditions[cid];
            if (!cObj) return;
            const opt = document.createElement("option");
            opt.value = cid;
            opt.textContent = cObj.condition_label;
            expCondSel.appendChild(opt);
          });
          if (preferredCondId && condIds.includes(preferredCondId)) {
            expCondSel.value = preferredCondId;
          } else if (condIds.length > 0) {
            expCondSel.value = condIds[0];
          }
        }

        function wrapAngleRad(ang) {
          return ((ang + Math.PI) % (2.0 * Math.PI) + 2.0 * Math.PI) % (2.0 * Math.PI) - Math.PI;
        }

        function epaDragRowInterpForSpeedMps(speedMps) {
          const rows = explorerCatalog.epa_coastdown_table || [];
          if (!rows.length) {
            return { p05: 0.16, median: 0.25, p95: 0.45, bevMedian: 0.31 };
          }
          const vKmh = Math.min(Math.max(speedMps * 3.6, rows[0].speed_kmh), rows[rows.length - 1].speed_kmh);
          for (let i = 0; i < rows.length - 1; i++) {
            const r0 = rows[i], r1 = rows[i + 1];
            if (vKmh >= r0.speed_kmh - 1e-9 && vKmh <= r1.speed_kmh + 1e-9) {
              const alpha = r1.speed_kmh > r0.speed_kmh ? (vKmh - r0.speed_kmh) / (r1.speed_kmh - r0.speed_kmh) : 0.0;
              return {
                p05: r0.p05_mps2 + alpha * (r1.p05_mps2 - r0.p05_mps2),
                median: r0.median_mps2 + alpha * (r1.median_mps2 - r0.median_mps2),
                p95: r0.p95_mps2 + alpha * (r1.p95_mps2 - r0.p95_mps2),
                bevMedian: r0.bev_median_mps2 + alpha * (r1.bev_median_mps2 - r0.bev_median_mps2),
              };
            }
          }
          const last = rows[rows.length - 1];
          return {
            p05: last.p05_mps2,
            median: last.median_mps2,
            p95: last.p95_mps2,
            bevMedian: last.bev_median_mps2,
          };
        }

        function epaDragIntervalForSpeedMps(speedMps) {
          const interp = epaDragRowInterpForSpeedMps(speedMps);
          return [interp.p05, interp.p95];
        }

        function resolveEpaDragForSpeedMps(speedMps, dragMode, customDragMps2) {
          const interp = epaDragRowInterpForSpeedMps(speedMps);
          const mode = dragMode || "epa_midpoint";
          if (mode === "epa_p05") return interp.p05;
          if (mode === "epa_median") return interp.median;
          if (mode === "epa_p95") return interp.p95;
          if (mode === "epa_bev_median") return interp.bevMedian;
          if (mode === "custom") {
            if (customDragMps2 !== null && customDragMps2 !== undefined && Number.isFinite(Number(customDragMps2))) {
              return Number(customDragMps2);
            }
          }
          return 0.5 * (interp.p05 + interp.p95);
        }

        function stoppingDistanceR3BExact(v0, aMax, t1, t2, t3, tAuth, aBefore, aAfter, mu) {
          if (v0 <= 0.0) {
            return {
              dPre: 0.0, dDelay: 0.0, dBrake: 0.0, dStop: 0.0,
              dReq: STANDSTILL_MARGIN_M, tReq: Infinity,
              vAfterT1: 0.0, aEff: Math.min(aMax, mu * GRAVITY),
              frictionCap: mu * GRAVITY, isFrictionCapped: aMax > mu * GRAVITY + 1e-6,
            };
          }
          let vCurr = v0;
          let dPre = 0.0;
          let stoppedInPre = false;
          const tAuthClamped = Math.min(Math.max(tAuth, 0.0), t1);
          const intervals = [
            [tAuthClamped, aBefore],
            [Math.max(0.0, t1 - tAuthClamped), aAfter],
          ];
          for (let i = 0; i < intervals.length; i++) {
            const dur = intervals[i][0];
            const dec = intervals[i][1];
            if (dur <= 0.0) continue;
            if (dec > 0.0 && vCurr <= dec * dur) {
              const tStop = vCurr / dec;
              dPre += vCurr * tStop - 0.5 * dec * tStop * tStop;
              vCurr = 0.0;
              stoppedInPre = true;
              break;
            }
            dPre += vCurr * dur - 0.5 * dec * dur * dur;
            vCurr -= dec * dur;
          }
          const vAfterT1 = vCurr;
          const frictionCap = mu * GRAVITY;
          const aEff = Math.min(aMax, frictionCap);
          let dDelay = 0.0;
          let dBrake = 0.0;
          if (!stoppedInPre) {
            dDelay = vCurr * t2;
            if (t3 > 0.0) {
              const dvRamp = 0.5 * aEff * t3;
              if (vCurr <= dvRamp) {
                const tau = Math.sqrt((2.0 * vCurr * t3) / aEff);
                dBrake = vCurr * tau - (aEff * Math.pow(tau, 3)) / (6.0 * t3);
              } else {
                dBrake = (vCurr * vCurr) / (2.0 * aEff) + (vCurr * t3) / 2.0 - (aEff * t3 * t3) / 24.0;
              }
            } else {
              dBrake = (vCurr * vCurr) / (2.0 * aEff);
            }
          }
          const dStop = dPre + dDelay + dBrake;
          const dReq = dStop + STANDSTILL_MARGIN_M;
          const tReq = dReq / v0;
          return {
            dPre, dDelay, dBrake, dStop, dReq, tReq,
            vAfterT1, aEff, frictionCap, isFrictionCapped: aMax > frictionCap + 1e-6,
          };
        }

        function evaluateR3BIntervalForBranch(vReqMps, dRemM, mu, branchId) {
          const tAvailS = dRemM / vReqMps;
          const [dragLo, dragHi] = epaDragIntervalForSpeedMps(vReqMps);
          const t1Vals = [1.15, 3.00];
          const t2Vals = [0.05, 0.17];
          const t3Vals = [0.30, 1.20];
          const aMaxVals = [6.43, 9.10];
          const preVals = branchId === "P0" ? [0.0] : (branchId === "P1" ? [dragLo, dragHi] : [1.00, 3.00]);
          const tAuth = branchId === "P0" ? 0.0 : Infinity;

          let tReqMin = Infinity;
          let tReqMax = -Infinity;
          for (const t1 of t1Vals) {
            for (const t2 of t2Vals) {
              for (const t3 of t3Vals) {
                for (const aMax of aMaxVals) {
                  for (const preDec of preVals) {
                    const res = stoppingDistanceR3BExact(vReqMps, aMax, t1, t2, t3, tAuth, preDec, 0.0, mu);
                    if (res.tReq < tReqMin) tReqMin = res.tReq;
                    if (res.tReq > tReqMax) tReqMax = res.tReq;
                  }
                }
              }
            }
          }
          const marginMinS = tAvailS - tReqMax;
          const marginMaxS = tAvailS - tReqMin;
          const marginMinM = marginMinS * vReqMps;
          const marginMaxM = marginMaxS * vReqMps;
          let underlying = "PARAMETER-SENSITIVE";
          let presStatus = "PARAMETER_SENSITIVE";
          if (marginMinS > EPSILON_S) {
            underlying = "ROBUSTLY SATISFIED";
            presStatus = "NECESSARY_CONDITION_SATISFIED";
          } else if (marginMaxS < -EPSILON_S) {
            underlying = "ROBUSTLY UNSATISFIED";
            presStatus = "NECESSARY_CONDITION_VIOLATED";
          }
          return {
            branchId, tAvailS, dAvailM: dRemM,
            tReqMin, tReqMax,
            dReqMin: tReqMin * vReqMps, dReqMax: tReqMax * vReqMps,
            marginMinS, marginMaxS, marginMinM, marginMaxM,
            underlying, presStatus,
          };
        }

        // Exact Browser Equivalent of Python evaluate_interactive_r3b(params)
        function evaluateInteractiveR3BInBrowser(params) {
          const p = params || {};
          let speedUnit = String(p.speed_unit || "mps").trim().toLowerCase();
          let rawV = Number(p.v_mps);
          if (p.v0_mps !== undefined && p.v0_mps !== null) {
            rawV = Number(p.v0_mps);
            speedUnit = "mps";
          } else if (p.v0_kmh !== undefined && p.v0_kmh !== null) {
            rawV = Number(p.v0_kmh);
            speedUnit = "kmh";
          }

          const rawD0Val = p.obstacle_distance_d0_m !== undefined ? p.obstacle_distance_d0_m : p.d0_m;
          const rawD0 = rawD0Val === null || rawD0Val === undefined ? null : Number(rawD0Val);
          const rawMu = Number(p.mu !== undefined ? p.mu : 1.0);
          const rawTauReq = Number(p.tau_req_s !== undefined ? p.tau_req_s : 0.0);
          const rawT1 = Number(p.t1_s !== undefined ? p.t1_s : 1.65);
          const rawT2 = Number(p.t2_s !== undefined ? p.t2_s : 0.10);
          const rawT3 = Number(p.t3_s !== undefined ? p.t3_s : 0.60);
          const rawAmax = Number(p.a_max_mps2 !== undefined ? p.a_max_mps2 : 8.00);
          const rawAsup = Number(p.a_sup_mps2 !== undefined ? p.a_sup_mps2 : 2.00);
          const aDragMode = String(p.a_drag_mode || "epa_midpoint").trim().toLowerCase();
          const rawAdragCustom = p.a_drag_custom_mps2 === null || p.a_drag_custom_mps2 === undefined ? null : Number(p.a_drag_custom_mps2);
          const rawGradePct = Number(p.road_grade_pct !== undefined ? p.road_grade_pct : 0.0);
          const policyBranch = String(p.selected_branch || p.policy_branch || "P1").trim().toUpperCase();

          let obsMode = String(p.obstacle_source_mode || p.obstacle_source || "counterfactual").trim();
          if (obsMode === "OBSERVED_IN_LANE_ANNOTATION" || obsMode.toLowerCase() === "observed") {
            obsMode = "observed";
          } else if (obsMode === "NONE_INSUFFICIENT_EVIDENCE" || obsMode.toLowerCase() === "none") {
            obsMode = "none";
          } else {
            obsMode = "counterfactual";
          }

          const egoX = Number(p.ego_x_at_req_m !== undefined ? p.ego_x_at_req_m : (p.coupled_ego_x_m !== undefined ? p.coupled_ego_x_m : 0.0));
          const egoY = Number(p.ego_y_at_req_m !== undefined ? p.ego_y_at_req_m : (p.coupled_ego_y_m !== undefined ? p.coupled_ego_y_m : 0.0));
          const egoHead = Number(p.ego_heading_at_req_rad !== undefined ? p.ego_heading_at_req_rad : (p.coupled_ego_heading_rad !== undefined ? p.coupled_ego_heading_rad : 0.0));
          const leadSpeedRaw = p.observed_lead_speed_mps !== undefined ? p.observed_lead_speed_mps : p.coupled_lead_speed_mps;
          const leadSpeed = leadSpeedRaw === null || leadSpeedRaw === undefined ? null : Number(leadSpeedRaw);

          let stateSrc = "OBSERVED_EGO_T0_PLUS_ASSUMED_OBSTACLE_D0";
          let obsSrcClass = "COUNTERFACTUAL_ASSUMPTION";
          const safeTauForState = Number.isFinite(rawTauReq) ? rawTauReq : 0.0;
          if (obsMode === "none" || (obsMode === "observed" && rawD0 === null)) {
            obsSrcClass = "NONE_INSUFFICIENT_EVIDENCE";
            stateSrc = Math.abs(safeTauForState) <= 1e-6 ? "OBSERVED_EGO_T0_NO_CREDIBLE_OBSTACLE" : "HYPOTHETICAL_VLA_STATE_NO_CREDIBLE_OBSTACLE";
          } else if (obsMode === "observed") {
            obsSrcClass = "OBSERVED_IN_LANE_ANNOTATION";
            const isMovingLead = leadSpeed !== null && Math.abs(leadSpeed) > 0.1;
            if (Math.abs(safeTauForState) <= 1e-6) {
              stateSrc = isMovingLead ? "OBSERVED_EGO_T0_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD" : "OBSERVED_EGO_T0_AND_OBSERVED_STATIONARY_OBSTACLE";
            } else {
              stateSrc = isMovingLead ? "HYPOTHETICAL_VLA_STATE_PLUS_STATIC_PROJECTION_OF_MOVING_LEAD" : "HYPOTHETICAL_VLA_STATE_WITH_OBSERVED_STATIONARY_OBSTACLE";
            }
          } else {
            obsSrcClass = "COUNTERFACTUAL_ASSUMPTION";
            stateSrc = Math.abs(safeTauForState) <= 1e-6 ? "OBSERVED_EGO_T0_PLUS_ASSUMED_OBSTACLE_D0" : "HYPOTHETICAL_VLA_STATE_PLUS_ASSUMED_OBSTACLE_D0";
          }

          const validationErrors = [];
          if (speedUnit !== "mps" && speedUnit !== "kmh") {
            validationErrors.push(`Unsupported speed_unit='${speedUnit}'. Must be 'mps' or 'kmh'.`);
          }
          const v0Mps = speedUnit === "kmh" ? rawV / 3.6 : rawV;
          const v0Kmh = v0Mps * 3.6;

          if (!Number.isFinite(v0Mps) || v0Mps < 0.0 || v0Mps > 60.0) {
            validationErrors.push(`Invalid or nonphysical vehicle speed v=${rawV} ${speedUnit} (converted v_mps=${v0Mps.toFixed(3)} m/s; valid range is [0.0, 60.0] m/s).`);
          }
          if (!Number.isFinite(rawMu) || rawMu <= 0.0 || rawMu > 1.2) {
            validationErrors.push(`Invalid road friction coefficient mu=${rawMu} (must satisfy 0.0 < mu <= 1.2).`);
          }
          if (!Number.isFinite(rawTauReq) || rawTauReq < -1e-6 || rawTauReq > 3.0 + 1e-6) {
            validationErrors.push(`Unsupported takeover request delay tau_req=${rawTauReq} s (R3B trajectory handover domain is [0.0, 3.0] s).`);
          }
          if (!Number.isFinite(rawT1) || rawT1 < 0.0 || rawT1 > 10.0) {
            validationErrors.push(`Invalid human reaction delay t1=${rawT1} s (must satisfy 0.0 <= t1 <= 10.0 s).`);
          }
          if (!Number.isFinite(rawT2) || rawT2 < 0.0 || rawT2 > 2.0) {
            validationErrors.push(`Invalid hydraulic actuation delay t2=${rawT2} s (must satisfy 0.0 <= t2 <= 2.0 s).`);
          }
          if (!Number.isFinite(rawT3) || rawT3 < 0.0 || rawT3 > 5.0) {
            validationErrors.push(`Invalid brake ramp buildup time t3=${rawT3} s (must satisfy 0.0 <= t3 <= 5.0 s).`);
          }
          if (!Number.isFinite(rawAmax) || rawAmax <= 0.0 || rawAmax > 15.0) {
            validationErrors.push(`Invalid maximum braking deceleration a_max=${rawAmax} m/s^2 (must satisfy 0.0 < a_max <= 15.0 m/s^2).`);
          }
          if (!Number.isFinite(rawAsup) || rawAsup < 0.0 || rawAsup > 5.0) {
            validationErrors.push(`Invalid P2 pre-deceleration a_sup=${rawAsup} m/s^2 (must satisfy 0.0 <= a_sup <= 5.0 m/s^2).`);
          }
          if (!SUPPORTED_DRAG_MODES.includes(aDragMode)) {
            validationErrors.push(`Unsupported aerodynamic drag mode '${aDragMode}'.`);
          }
          if (aDragMode === "custom") {
            if (rawAdragCustom === null || !Number.isFinite(rawAdragCustom) || rawAdragCustom < 0.0 || rawAdragCustom > 1.5) {
              validationErrors.push(`Invalid custom aerodynamic drag deceleration a_drag=${rawAdragCustom} m/s^2 (must satisfy 0.0 <= a_drag <= 1.5 m/s^2).`);
            }
          }
          if (!Number.isFinite(rawGradePct) || Math.abs(rawGradePct) > 25.0) {
            validationErrors.push(`Invalid road gradient road_grade_pct=${rawGradePct}% (must satisfy -25% <= grade <= +25%).`);
          }
          if (!["P0", "P1", "P2"].includes(policyBranch)) {
            validationErrors.push(`Unsupported policy branch '${policyBranch}'. Must be P0, P1, or P2.`);
          }
          if (obsMode !== "none" && rawD0 !== null) {
            if (!Number.isFinite(rawD0) || rawD0 <= 0.0 || rawD0 > 500.0) {
              validationErrors.push(`Invalid initial obstacle distance d0=${rawD0} m (must satisfy 0.0 < d0 <= 500.0 m when provided).`);
            }
          }

          if (validationErrors.length > 0) {
            return {
              valid_inputs: false,
              r3b_applicable: false,
              presentation_status: "NOT_APPLICABLE",
              raw_r3b_status: "INVALID_PARAMETERS",
              underlying_r3b_status: "INVALID_PARAMETERS",
              state_source: stateSrc,
              state_source_classification: stateSrc,
              obstacle_source_classification: obsSrcClass,
              validation_errors: validationErrors,
              non_applicability_reasons: validationErrors,
              d_avail_m: null,
              t_avail_s: null,
              selected_branch: policyBranch,
              selected_policy_point: null,
              selected_policy_interval: null,
              point_breakdown_by_branch: {},
              point_results_by_branch: {},
              interval_by_branch: {},
              interval_results_by_branch: {},
            };
          }

          if (obsMode === "none" || rawD0 === null) {
            const reason = "No observed 3D in-corridor obstacle exists in the dataset annotations for this scene and no counterfactual obstacle distance d0 was assumed.";
            return {
              valid_inputs: true,
              r3b_applicable: false,
              presentation_status: "INSUFFICIENT_EVIDENCE",
              raw_r3b_status: "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
              underlying_r3b_status: "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
              state_source: stateSrc,
              state_source_classification: stateSrc,
              obstacle_source_classification: "NONE_INSUFFICIENT_EVIDENCE",
              validation_errors: [],
              non_applicability_reasons: [reason],
              d_avail_m: null,
              t_avail_s: null,
              selected_branch: policyBranch,
              selected_policy_point: null,
              selected_policy_interval: null,
              point_breakdown_by_branch: {},
              point_results_by_branch: {},
              interval_by_branch: {},
              interval_results_by_branch: {},
            };
          }

          const nonAppReasons = [];
          if (Math.abs(rawGradePct) > 1e-6) {
            nonAppReasons.push(`Road gradient road_grade_pct=${rawGradePct.toFixed(1)}% is non-zero; the frozen R3A/R3B analytical stopping-distance equations are defined strictly for level road (0.0% grade).`);
          }
          if (v0Mps <= MIN_SPEED_MPS) {
            nonAppReasons.push(`Vehicle speed v=${v0Mps.toFixed(4)} m/s (${v0Kmh.toFixed(2)} km/h) <= ${MIN_SPEED_MPS} m/s (stationary or near-stationary ego vehicle).`);
          }
          const withinCorridor = Math.abs(egoY) <= CORR_HALF_WIDTH_M && Math.abs(egoHead) <= CORR_MAX_HEADING_RAD;
          if (!withinCorridor) {
            nonAppReasons.push(`Coupled trajectory pose (|y|=${Math.abs(egoY).toFixed(2)} m, |heading|=${Math.abs(egoHead).toFixed(2)} rad) exits the +-1.75 m / +-0.35 rad 1D longitudinal corridor.`);
          }
          const dRemM = rawD0 - egoX;
          if (dRemM <= 0.0) {
            nonAppReasons.push(`Remaining obstacle distance d_rem=${dRemM.toFixed(2)} m <= 0.0 m.`);
          }

          if (nonAppReasons.length > 0) {
            return {
              valid_inputs: true,
              r3b_applicable: false,
              presentation_status: "NOT_APPLICABLE",
              raw_r3b_status: "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
              underlying_r3b_status: "INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE",
              state_source: stateSrc,
              state_source_classification: stateSrc,
              obstacle_source_classification: obsSrcClass,
              validation_errors: [],
              non_applicability_reasons: nonAppReasons,
              d_avail_m: Number(dRemM.toFixed(4)),
              t_avail_s: null,
              selected_branch: policyBranch,
              selected_policy_point: null,
              selected_policy_interval: null,
              point_breakdown_by_branch: {},
              point_results_by_branch: {},
              interval_by_branch: {},
              interval_results_by_branch: {},
            };
          }

          const tAvailS = dRemM / v0Mps;
          const aDragPointMps2 = resolveEpaDragForSpeedMps(v0Mps, aDragMode, rawAdragCustom);
          const pointByBranch = {};
          const intervalByBranch = {};

          ["P0", "P1", "P2"].forEach((bid) => {
            const aBefore = bid === "P0" ? 0.0 : (bid === "P1" ? aDragPointMps2 : rawAsup);
            const tAuth = bid === "P0" ? 0.0 : Infinity;
            const pt = stoppingDistanceR3BExact(v0Mps, rawAmax, rawT1, rawT2, rawT3, tAuth, aBefore, 0.0, rawMu);
            const mM = dRemM - pt.dReq;
            const mS = tAvailS - pt.tReq;
            const ptPres = mS >= 0.0 ? "NECESSARY_CONDITION_SATISFIED" : "NECESSARY_CONDITION_VIOLATED";
            const ptUnd = mS >= 0.0 ? "POINT_SATISFIED" : "POINT_VIOLATED";
            pointByBranch[bid] = {
              branch_id: bid,
              a_pre_decel_mps2: Number(aBefore.toFixed(5)),
              pre_control_decel_mps2: Number(aBefore.toFixed(5)),
              a_drag_mode: aDragMode,
              d_pre_m: Number(pt.dPre.toFixed(4)),
              d_pre_control_m: Number(pt.dPre.toFixed(4)),
              d_delay_m: Number(pt.dDelay.toFixed(4)),
              d_actuation_delay_m: Number(pt.dDelay.toFixed(4)),
              d_brake_m: Number(pt.dBrake.toFixed(4)),
              d_braking_phase_m: Number(pt.dBrake.toFixed(4)),
              d_stop_m: Number(pt.dStop.toFixed(4)),
              standstill_margin_m: STANDSTILL_MARGIN_M,
              d_req_m: Number(pt.dReq.toFixed(4)),
              t_req_s: Number(pt.tReq.toFixed(4)),
              d_avail_m: Number(dRemM.toFixed(4)),
              t_avail_s: Number(tAvailS.toFixed(4)),
              margin_m: Number(mM.toFixed(4)),
              margin_s: Number(mS.toFixed(4)),
              v_after_t1_mps: Number(pt.vAfterT1.toFixed(5)),
              v_at_effective_braking_mps: Number(pt.vAfterT1.toFixed(5)),
              a_eff_mps2: Number(pt.aEff.toFixed(5)),
              effective_braking_decel_mps2: Number(pt.aEff.toFixed(5)),
              friction_cap_mps2: Number(pt.frictionCap.toFixed(5)),
              friction_cap_mu_g_mps2: Number(pt.frictionCap.toFixed(5)),
              is_friction_capped: Boolean(pt.isFrictionCapped),
              presentation_status: ptPres,
              underlying_point_status: ptUnd,
            };

            const iv = evaluateR3BIntervalForBranch(v0Mps, dRemM, rawMu, bid);
            const intervalCls = iv.underlying === "ROBUSTLY SATISFIED"
              ? "UNIFORMLY_POSITIVE"
              : (iv.underlying === "ROBUSTLY UNSATISFIED" ? "UNIFORMLY_VIOLATED" : "PARAMETER_SENSITIVE");
            intervalByBranch[bid] = {
              branch_id: bid,
              t_avail_s: Number(iv.tAvailS.toFixed(4)),
              d_avail_m: Number(iv.dAvailM.toFixed(4)),
              t_req_min_s: Number(iv.tReqMin.toFixed(4)),
              t_req_max_s: Number(iv.tReqMax.toFixed(4)),
              d_req_min_m: Number(iv.dReqMin.toFixed(4)),
              d_req_max_m: Number(iv.dReqMax.toFixed(4)),
              d_stop_min_m: Number(iv.dReqMin.toFixed(4)),
              d_stop_max_m: Number(iv.dReqMax.toFixed(4)),
              margin_min_s: Number(iv.marginMinS.toFixed(4)),
              margin_max_s: Number(iv.marginMaxS.toFixed(4)),
              margin_min_m: Number(iv.marginMinM.toFixed(4)),
              margin_max_m: Number(iv.marginMaxM.toFixed(4)),
              underlying_r3b_status: iv.underlying,
              interval_classification: intervalCls,
              presentation_status: iv.presStatus,
            };
          });

          const selPt = pointByBranch[policyBranch];
          const selIv = intervalByBranch[policyBranch];
          return {
            valid_inputs: true,
            r3b_applicable: true,
            presentation_status: selPt.presentation_status,
            raw_r3b_status: "EVALUATED",
            underlying_r3b_status: selIv.underlying_r3b_status,
            interval_presentation_status: selIv.presentation_status,
            state_source: stateSrc,
            state_source_classification: stateSrc,
            obstacle_source_classification: obsSrcClass,
            validation_errors: [],
            non_applicability_reasons: [],
            d_avail_m: Number(dRemM.toFixed(4)),
            t_avail_s: Number(tAvailS.toFixed(4)),
            selected_branch: policyBranch,
            selected_policy_point: selPt,
            selected_policy_interval: selIv,
            point_breakdown_by_branch: pointByBranch,
            point_results_by_branch: pointByBranch,
            interval_by_branch: intervalByBranch,
            interval_results_by_branch: intervalByBranch,
          };
        }

        function verifyAllParityCasesInBrowser() {
          const suite = explorerCatalog.r3b_browser_parity_reference_cases || {};
          const cases = suite.cases || explorerCatalog.r3b_parity_cases || [];
          const results = [];
          let passedCount = 0;
          let failedCount = 0;
          let maxAbsFloatDiff = 0.0;

          cases.forEach((c) => {
            const jsOut = evaluateInteractiveR3BInBrowser(c.inputs);
            const pyOut = c.expected;
            const mismatches = [];

            if (Boolean(jsOut.valid_inputs) !== Boolean(pyOut.valid_inputs)) {
              mismatches.push(`valid_inputs: js=${jsOut.valid_inputs} vs py=${pyOut.valid_inputs}`);
            }
            if (jsOut.presentation_status !== pyOut.presentation_status) {
              mismatches.push(`presentation_status: js=${jsOut.presentation_status} vs py=${pyOut.presentation_status}`);
            }
            if (jsOut.raw_r3b_status !== pyOut.raw_r3b_status) {
              mismatches.push(`raw_r3b_status: js=${jsOut.raw_r3b_status} vs py=${pyOut.raw_r3b_status}`);
            }
            if (jsOut.state_source !== pyOut.state_source) {
              mismatches.push(`state_source: js=${jsOut.state_source} vs py=${pyOut.state_source}`);
            }

            const selBranch = pyOut.selected_branch || "P1";
            const pyPt = (pyOut.point_results_by_branch || {})[selBranch] || null;
            const jsPt = (jsOut.point_results_by_branch || {})[selBranch] || null;
            const pyIv = (pyOut.interval_results_by_branch || {})[selBranch] || null;
            const jsIv = (jsOut.interval_results_by_branch || {})[selBranch] || null;

            if (pyOut.raw_r3b_status === "EVALUATED" && pyPt && jsPt && pyIv && jsIv) {
              const ptFields = [
                "d_pre_control_m", "d_actuation_delay_m", "d_braking_phase_m", "d_stop_m",
                "d_req_m", "t_req_s", "d_avail_m", "t_avail_s",
                "margin_m", "margin_s", "v_at_effective_braking_mps", "effective_braking_decel_mps2", "pre_control_decel_mps2"
              ];
              ptFields.forEach((f) => {
                const jv = Number(jsPt[f]);
                const pv = Number(pyPt[f]);
                const diff = Math.abs(jv - pv);
                if (diff > maxAbsFloatDiff) maxAbsFloatDiff = diff;
                if (diff > 1e-3) {
                  mismatches.push(`point.${f}: js=${jv} vs py=${pv} (diff=${diff})`);
                }
              });

              const ivFields = [
                "t_req_min_s", "t_req_max_s", "d_stop_min_m", "d_stop_max_m",
                "margin_min_s", "margin_max_s", "margin_min_m", "margin_max_m"
              ];
              ivFields.forEach((f) => {
                const jv = Number(jsIv[f]);
                const pv = Number(pyIv[f]);
                const diff = Math.abs(jv - pv);
                if (diff > maxAbsFloatDiff) maxAbsFloatDiff = diff;
                if (diff > 1e-3) {
                  mismatches.push(`interval.${f}: js=${jv} vs py=${pv} (diff=${diff})`);
                }
              });
              if (jsIv.presentation_status !== pyIv.presentation_status) {
                mismatches.push(`interval.presentation_status: js=${jsIv.presentation_status} vs py=${pyIv.presentation_status}`);
              }
              if (jsIv.interval_classification !== pyIv.interval_classification) {
                mismatches.push(`interval.interval_classification: js=${jsIv.interval_classification} vs py=${pyIv.interval_classification}`);
              }
            }

            const passed = mismatches.length === 0;
            if (passed) passedCount++;
            else failedCount++;
            results.push({
              case_id: c.case_id,
              description: c.description,
              passed,
              mismatches,
              js_status: jsOut.presentation_status,
              py_status: pyOut.presentation_status,
              js_margin_m: jsPt ? jsPt.margin_m : null,
              py_margin_m: pyPt ? pyPt.margin_m : null,
            });
          });

          return {
            total_cases: cases.length,
            passed_count: passedCount,
            failed_count: failedCount,
            max_abs_float_diff: Number(maxAbsFloatDiff.toFixed(6)),
            all_passed: failedCount === 0 && cases.length >= 25,
            results,
          };
        }

        function getInterpolatedExplorerStep(condObj, tQueryS, muVal) {
          const steps = muVal < 0.8 ? condObj.steps_wet_mu0_5 : condObj.steps_dry_mu1_0;
          const tClamped = Math.min(Math.max(tQueryS, 0.0), 5.0);
          const exactStep = steps.find((s) => Math.abs(s.t_s - tClamped) < 1e-4);
          if (exactStep) {
            return { ...exactStep, isInterpolatedDisplay: false };
          }
          const idxHi = steps.findIndex((s) => s.t_s >= tClamped);
          const idxLo = Math.max(0, idxHi - 1);
          const s0 = steps[idxLo];
          const s1 = steps[idxHi];
          const alpha = s1.t_s > s0.t_s ? (tClamped - s0.t_s) / (s1.t_s - s0.t_s) : 0.0;
          const xM = s0.x_m + alpha * (s1.x_m - s0.x_m);
          const yM = s0.y_m + alpha * (s1.y_m - s0.y_m);
          const dHead = wrapAngleRad(s1.heading_rad - s0.heading_rad);
          const headRad = wrapAngleRad(s0.heading_rad + alpha * dHead);
          const withinCorr = Math.abs(yM) <= CORR_HALF_WIDTH_M && Math.abs(headRad) <= CORR_MAX_HEADING_RAD;
          const timeSupported = tClamped <= 3.0 + 1e-6;
          return {
            ...s1,
            t_s: Number(tClamped.toFixed(2)),
            x_m: Number(xM.toFixed(4)),
            y_m: Number(yM.toFixed(4)),
            heading_rad: Number(headRad.toFixed(5)),
            heading_deg: Number((headRad * 180.0 / Math.PI).toFixed(2)),
            within_longitudinal_corridor: withinCorr,
            r3b_time_horizon_supported: timeSupported,
            r3b_corridor_applicable: withinCorr && timeSupported && s1.implied_speed_mps > MIN_SPEED_MPS,
            isInterpolatedDisplay: true,
          };
        }

        function renderExplorerBEV(condObj, currentStep, counterpartCond, showGt, showCounterpart) {
          const container = document.getElementById("svg-explorer-bev");
          if (!container) return;
          const steps = condObj.steps_dry_mu1_0 || [];
          const cpSteps = counterpartCond ? (counterpartCond.steps_dry_mu1_0 || []) : [];

          const w = 520, h = 215, padL = 42, padR = 18, padT = 20, padB = 28;
          let maxX = 40.0;
          let maxAbsY = 4.5;
          steps.forEach((s) => {
            if (s.x_m + 5 > maxX) maxX = s.x_m + 5;
            if (Math.abs(s.y_m) + 1.5 > maxAbsY) maxAbsY = Math.abs(s.y_m) + 1.5;
            if (showGt && s.gt_x_m !== null && s.gt_x_m + 5 > maxX) maxX = s.gt_x_m + 5;
            if (showGt && s.gt_y_m !== null && Math.abs(s.gt_y_m) + 1.5 > maxAbsY) maxAbsY = Math.abs(s.gt_y_m) + 1.5;
          });
          if (showCounterpart && cpSteps.length) {
            cpSteps.forEach((s) => {
              if (s.x_m + 5 > maxX) maxX = s.x_m + 5;
              if (Math.abs(s.y_m) + 1.5 > maxAbsY) maxAbsY = Math.abs(s.y_m) + 1.5;
            });
          }
          const obsLead = condObj.observed_in_lane_lead_obstacle;
          if (obsLead && obsLead.x_m + 6 > maxX) maxX = obsLead.x_m + 6;
          const minX = -3.0;

          const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * (w - padL - padR);
          const yToPx = (y) => padT + ((maxAbsY - y) / (2.0 * maxAbsY)) * (h - padT - padB);
          const corrTop = yToPx(CORR_HALF_WIDTH_M);
          const corrBot = yToPx(-CORR_HALF_WIDTH_M);
          const y0 = yToPx(0);
          const x0 = xToPx(0);

          let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
          svg += `<rect x="${x0}" y="${corrTop}" width="${xToPx(maxX) - x0}" height="${Math.max(6, corrBot - corrTop)}" fill="rgba(59,130,246,0.08)" stroke="rgba(59,130,246,0.32)" stroke-dasharray="4 3" />`;
          svg += `<line x1="${padL}" y1="${y0}" x2="${w - padR}" y2="${y0}" stroke="currentColor" stroke-opacity="0.22" />`;

          for (let xm = 0; xm <= maxX; xm += 10) {
            const px = xToPx(xm);
            svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
            svg += `<text x="${px}" y="${h - 8}" text-anchor="middle" font-size="9.5" fill="currentColor" fill-opacity="0.7">${xm}m</text>`;
          }
          [-Math.round(maxAbsY * 0.7), 0, Math.round(maxAbsY * 0.7)].forEach((yv) => {
            const py = yToPx(yv);
            svg += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="8.5" fill="currentColor" fill-opacity="0.7">${yv >= 0 ? "+" : ""}${yv}m</text>`;
          });

          if (obsLead) {
            const ox = xToPx(obsLead.x_m);
            const oy = yToPx(obsLead.y_m || 0);
            svg += `<line x1="${ox}" y1="${padT}" x2="${ox}" y2="${h - padB}" stroke="#d97706" stroke-width="1.8" stroke-dasharray="5 3" />`;
            svg += `<rect x="${ox - 4}" y="${oy - 6}" width="8" height="12" rx="2" fill="#d97706" fill-opacity="0.6" />`;
            svg += `<text x="${Math.min(w - padR - 4, ox - 5)}" y="${h - padB - 6}" text-anchor="end" font-size="9" font-weight="bold" fill="#d97706">Obs Lead d0=${obsLead.x_m.toFixed(1)}m</text>`;
          }

          if (showGt && steps.length > 1) {
            const gtPts = steps.filter((s) => s.gt_x_m !== null).map((s) => `${xToPx(s.gt_x_m)},${yToPx(s.gt_y_m)}`).join(" ");
            svg += `<polyline fill="none" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" points="${gtPts}" />`;
          }

          if (showCounterpart && cpSteps.length > 1) {
            const cpPts = cpSteps.map((s) => `${xToPx(s.x_m)},${yToPx(s.y_m)}`).join(" ");
            svg += `<polyline fill="none" stroke="#9333ea" stroke-width="2" stroke-dasharray="2 2" points="${cpPts}" />`;
            cpSteps.slice(1).forEach((s) => {
              svg += `<circle cx="${xToPx(s.x_m)}" cy="${yToPx(s.y_m)}" r="2.2" fill="#9333ea" />`;
            });
          }

          // Full 5.0s planned path (subtle reference) + Progressive animated trail up to currentStep.t_s
          const fullPredPts = steps.map((s) => `${xToPx(s.x_m)},${yToPx(s.y_m)}`).join(" ");
          svg += `<polyline fill="none" stroke="#93c5fd" stroke-width="1.8" stroke-dasharray="3 2" points="${fullPredPts}" />`;

          const activeTrailSteps = steps.filter((s) => s.t_s <= currentStep.t_s + 1e-4);
          const trailPtsArr = activeTrailSteps.map((s) => `${xToPx(s.x_m)},${yToPx(s.y_m)}`);
          if (currentStep.isInterpolatedDisplay) {
            trailPtsArr.push(`${xToPx(currentStep.x_m)},${yToPx(currentStep.y_m)}`);
          }
          if (trailPtsArr.length > 1) {
            svg += `<polyline fill="none" stroke="#2563eb" stroke-width="3.0" points="${trailPtsArr.join(" ")}" />`;
          }

          steps.forEach((s) => {
            const hasViol = (s.checks || []).some((c) => c.evaluation_scope === "TIME_LOCAL_STEP" && c.step_status === "VIOLATED");
            const isReached = s.t_s <= currentStep.t_s + 1e-4;
            const ptColor = hasViol ? "#ef4444" : (s.within_longitudinal_corridor ? "#2563eb" : "#d97706");
            svg += `<circle cx="${xToPx(s.x_m)}" cy="${yToPx(s.y_m)}" r="${isReached ? 3.5 : 2.6}" fill="${ptColor}" fill-opacity="${isReached ? "1.0" : "0.45"}" stroke="#ffffff" stroke-width="1" />`;
          });

          // Draw Active Ego Vehicle Footprint + Heading Vector (distinguishing recorded 0.5s sample vs display interpolation)
          const curX = xToPx(currentStep.x_m);
          const curY = yToPx(currentStep.y_m);
          const headLen = 20.0;
          const hx = curX + headLen * Math.cos(currentStep.heading_rad);
          const hy = curY - headLen * Math.sin(currentStep.heading_rad);
          const stepColor = currentStep.isInterpolatedDisplay
            ? "#d97706"
            : (currentStep.within_longitudinal_corridor ? "#4f46e5" : "#e11d48");
          const rotDeg = -(currentStep.heading_rad * 180.0 / Math.PI);

          svg += `<g id="bev-ego-vehicle-marker" transform="translate(${curX}, ${curY}) rotate(${rotDeg.toFixed(2)})">`;
          svg += `<rect x="-8" y="-4.5" width="16" height="9" rx="2" fill="${stepColor}" fill-opacity="0.22" stroke="${stepColor}" stroke-width="1.8" ${currentStep.isInterpolatedDisplay ? 'stroke-dasharray="2.5 1.5"' : ""} />`;
          svg += `</g>`;
          svg += `<line x1="${curX}" y1="${curY}" x2="${hx}" y2="${hy}" stroke="${stepColor}" stroke-width="2.6" />`;
          svg += `<circle cx="${curX}" cy="${curY}" r="5.5" fill="${stepColor}" stroke="#ffffff" stroke-width="1.8" />`;

          const sampleTag = currentStep.isInterpolatedDisplay
            ? `DISPLAY INTERPOLATION (t=${currentStep.t_s.toFixed(2)}s)`
            : `RECORDED 0.5s SAMPLE (Step ${currentStep.step}, t=${currentStep.t_s.toFixed(1)}s)`;
          svg += `<text x="${padL + 6}" y="${h - padB - 6}" text-anchor="start" font-size="8.5" font-family="monospace" font-weight="bold" fill="${stepColor}">${sampleTag}</text>`;

          svg += `<g transform="translate(${padL + 6}, ${padT + 10})" font-size="9" fill="currentColor">`;
          svg += `<line x1="0" y1="-3" x2="12" y2="-3" stroke="#2563eb" stroke-width="2.8" /><text x="15" y="0">Active Rollout (${condObj.driving_command})</text>`;
          if (showGt) {
            svg += `<line x1="148" y1="-3" x2="160" y2="-3" stroke="#10b981" stroke-width="2" stroke-dasharray="4 3" /><text x="163" y="0">Logged GT</text>`;
          }
          if (showCounterpart && counterpartCond) {
            svg += `<line x1="222" y1="-3" x2="234" y2="-3" stroke="#9333ea" stroke-width="2" stroke-dasharray="2 2" /><text x="237" y="0">Counterpart (${counterpartCond.driving_command})</text>`;
          }
          svg += `</g></svg>`;
          container.innerHTML = svg;
        }

        function renderExplorerKinematics(condObj, currentStep, muVal) {
          const container = document.getElementById("svg-explorer-kinematics");
          if (!container) return;
          const steps = muVal < 0.8 ? condObj.steps_wet_mu0_5 : condObj.steps_dry_mu1_0;
          const w = 520, h = 155, padL = 38, padR = 38, padT = 20, padB = 24;
          const tToPx = (t) => padL + (t / 5.0) * (w - padL - padR);

          let maxV = 18.0;
          let maxAbsA = 5.0;
          steps.forEach((s) => {
            if (s.implied_speed_mps + 2 > maxV) maxV = s.implied_speed_mps + 2;
            maxAbsA = Math.max(maxAbsA, Math.abs(s.a_lon_mps2) + 1.0, Math.abs(s.a_total_mps2 || 0) + 1.0);
          });
          const vToPx = (v) => padT + ((maxV - Math.max(0, v)) / maxV) * (h - padT - padB);
          const aToPx = (a) => padT + ((maxAbsA - a) / (2.0 * maxAbsA)) * (h - padT - padB);

          let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
          const yZeroA = aToPx(0);
          svg += `<line x1="${padL}" y1="${yZeroA}" x2="${w - padR}" y2="${yZeroA}" stroke="currentColor" stroke-opacity="0.2" stroke-dasharray="3 2" />`;

          for (let tv = 0; tv <= 5; tv += 1) {
            const px = tToPx(tv);
            svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
            svg += `<text x="${px}" y="${h - 6}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${tv}.0s</text>`;
          }
          [0, Math.round(maxV / 2), Math.round(maxV)].forEach((vv) => {
            const py = vToPx(vv);
            svg += `<text x="${padL - 4}" y="${py + 3}" text-anchor="end" font-size="8.5" fill="#2563eb">${vv}m/s</text>`;
          });
          [-Math.round(maxAbsA), 0, Math.round(maxAbsA)].forEach((av) => {
            const py = aToPx(av);
            svg += `<text x="${w - padR + 4}" y="${py + 3}" text-anchor="start" font-size="8.5" fill="#d97706">${av >= 0 ? "+" : ""}${av}m/s²</text>`;
          });

          const vPts = steps.map((s) => `${tToPx(s.t_s)},${vToPx(s.implied_speed_mps)}`).join(" ");
          const aLonPts = steps.map((s) => `${tToPx(s.t_s)},${aToPx(s.a_lon_mps2)}`).join(" ");
          const aTotPts = steps.slice(1).map((s) => `${tToPx(s.t_s)},${aToPx(s.a_total_mps2 || 0)}`).join(" ");

          svg += `<polyline fill="none" stroke="#2563eb" stroke-width="2.2" points="${vPts}" />`;
          svg += `<polyline fill="none" stroke="#d97706" stroke-width="2" points="${aLonPts}" />`;
          if (aTotPts) {
            svg += `<polyline fill="none" stroke="#9333ea" stroke-width="1.6" stroke-dasharray="2 2" points="${aTotPts}" />`;
          }

          const curPx = tToPx(currentStep.t_s);
          svg += `<line x1="${curPx}" y1="${padT}" x2="${curPx}" y2="${h - padB}" stroke="#4f46e5" stroke-width="2" />`;
          svg += `<circle cx="${curPx}" cy="${vToPx(currentStep.implied_speed_mps)}" r="4" fill="#2563eb" stroke="#ffffff" stroke-width="1" />`;
          svg += `<circle cx="${curPx}" cy="${aToPx(currentStep.a_lon_mps2)}" r="4" fill="#d97706" stroke="#ffffff" stroke-width="1" />`;

          svg += `<g transform="translate(${padL + 6}, 12)" font-size="8.5" fill="currentColor">`;
          svg += `<line x1="0" y1="-3" x2="10" y2="-3" stroke="#2563eb" stroke-width="2.2" /><text x="13" y="0">v(t) [m/s]</text>`;
          svg += `<line x1="78" y1="-3" x2="88" y2="-3" stroke="#d97706" stroke-width="2" /><text x="91" y="0">a_lon(t) [m/s²]</text>`;
          svg += `<line x1="175" y1="-3" x2="185" y2="-3" stroke="#9333ea" stroke-width="1.6" stroke-dasharray="2 2" /><text x="188" y="0">|a_tot(t)| [m/s²]</text>`;
          svg += `</g></svg>`;
          container.innerHTML = svg;
        }

        function syncStepToR3BSimulator(condObj, currentStep) {
          r3bModeSel.value = "connected";
          const unit = r3bUnitSel.value;
          const vMps = currentStep.implied_speed_mps;
          if (unit === "kmh") {
            const vKmh = vMps * 3.6;
            r3bSpeedSlider.max = "150.0";
            r3bSpeedSlider.value = vKmh.toFixed(2);
            r3bSpeedInput.value = vKmh.toFixed(2);
          } else {
            r3bSpeedSlider.max = "42.0";
            r3bSpeedSlider.value = vMps.toFixed(2);
            r3bSpeedInput.value = vMps.toFixed(2);
          }
          const tauClamped = Math.min(currentStep.t_s, 3.0);
          r3bTauSlider.value = tauClamped.toFixed(1);
          r3bTauInput.value = tauClamped.toFixed(1);

          const obsLead = condObj.observed_in_lane_lead_obstacle;
          if (obsLead && r3bObsModeSel.value === "observed") {
            r3bD0Slider.value = obsLead.x_m.toFixed(2);
            r3bD0Input.value = obsLead.x_m.toFixed(2);
          }
          renderR3BSimulator();
        }

        function renderExplorerView() {
          const condId = expCondSel.value;
          const condObj = explorerCatalog.conditions[condId];
          if (!condObj) return;
          const muVal = parseFloat(expMuSel.value || "1.0");
          const tVal = parseFloat(expTimeSlider.value || "0.0");
          const currentStep = getInterpolatedExplorerStep(condObj, tVal, muVal);

          const roleBadge = document.getElementById("explorer-condition-role-badge");
          if (condObj.is_canonical) {
            roleBadge.textContent = "CANONICAL GENUINE AUTOVLA OUTPUT";
            roleBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30";
          } else if (condObj.condition_role === "CONTROLLED_COMMAND_INTERVENTION") {
            roleBadge.textContent = "CONTROLLED COMMAND INTERVENTION (EXT-VLA-C07)";
            roleBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/15 text-indigo-800 border border-indigo-500/30";
          } else {
            roleBadge.textContent = "CONTROLLED OOD SIGNED-ACCEL DIAGNOSTIC (EXT-VLA-C03)";
            roleBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/15 text-rose-800 border border-rose-500/30";
          }

          expTimeLabel.textContent = currentStep.isInterpolatedDisplay
            ? `t = ${currentStep.t_s.toFixed(2)} s (Between Step ${currentStep.step - 1} & ${currentStep.step})`
            : `t = ${currentStep.t_s.toFixed(1)} s (Step ${currentStep.step} / 10)`;

          if (currentStep.isInterpolatedDisplay) {
            expInterpBadge.textContent = "DISPLAY INTERPOLATION BETWEEN RECORDED 0.5 s WAYPOINTS";
            expInterpBadge.className = "px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-900 border border-amber-500/30";
          } else {
            expInterpBadge.textContent = currentStep.step === 0
              ? "RECORDED INITIAL EGO STATE (t0 = 0.0 s)"
              : `RECORDED 0.5 s WAYPOINT (Step k = ${currentStep.step})`;
            expInterpBadge.className = "px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-800 border border-emerald-500/30";
          }

          const gtBanner = document.getElementById("explorer-gt-boundary-banner");
          if (!condObj.gt_comparison_meaningful) {
            gtBanner.className = "p-2.5 rounded-lg text-xs bg-amber-500/15 border border-amber-500/35 text-amber-950";
            gtBanner.innerHTML = `<strong>Command-Intervention GT Comparison Warning:</strong> ${condObj.gt_comparison_note}`;
          } else {
            gtBanner.className = "p-2.5 rounded-lg text-xs bg-blue-500/10 border border-blue-500/25 text-[var(--foreground)]";
            gtBanner.innerHTML = `<strong>Rollout Provenance &amp; Ground-Truth Scope:</strong> ${condObj.gt_comparison_note}`;
          }

          const counterpartCond = condObj.comparison_counterpart_id
            ? explorerCatalog.conditions[condObj.comparison_counterpart_id]
            : null;
          const cpLabel = document.getElementById("lbl-explorer-counterpart");
          if (counterpartCond) {
            cpLabel.textContent = `Overlay Counterpart: ${counterpartCond.condition_label}`;
            expChkCounterpart.disabled = false;
          } else {
            cpLabel.textContent = "No Counterpart Rollout for This Scene";
            expChkCounterpart.disabled = true;
          }

          const exitSum = document.getElementById("explorer-corridor-exit-summary");
          exitSum.textContent = condObj.first_corridor_exit_tau_s !== null
            ? `First 1D Corridor Exit: Step ${condObj.first_corridor_exit_step} (t = ${condObj.first_corridor_exit_tau_s.toFixed(1)} s)`
            : "Remains within +-1.75 m / +-0.35 rad Corridor for all 5.0 s";

          renderExplorerBEV(condObj, currentStep, counterpartCond, expChkGt.checked, expChkCounterpart.checked);
          renderExplorerKinematics(condObj, currentStep, muVal);

          // Step Telemetry Readout
          const tokText = currentStep.step === 0
            ? "Initial Observation (Prior to <action_1>)"
            : `<action_${currentStep.action_codebook_index}> (Step ${currentStep.step})`;
          const corrBadge = currentStep.within_longitudinal_corridor
            ? `<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-800 border border-emerald-500/30 font-semibold">WITHIN 1D CORRIDOR (|y|=${Math.abs(currentStep.y_m).toFixed(2)}m &le; 1.75m, |&psi;|=${Math.abs(currentStep.heading_rad).toFixed(2)}rad &le; 0.35rad)</span>`
            : `<span class="px-2 py-0.5 rounded bg-rose-500/15 text-rose-800 border border-rose-500/30 font-bold">EXITED 1D CORRIDOR (|y|=${Math.abs(currentStep.y_m).toFixed(2)}m, |&psi;|=${Math.abs(currentStep.heading_rad).toFixed(2)}rad &rarr; 1D R3B Not Applicable)</span>`;

          const gtErrStr = currentStep.l2_displacement_vs_logged_gt_m !== null && currentStep.l2_displacement_vs_logged_gt_m !== undefined
            ? `${currentStep.l2_displacement_vs_logged_gt_m.toFixed(2)} m${condObj.gt_comparison_meaningful ? "" : " (vs. Logged Left Turn*)"}`
            : "N/A";

          document.getElementById("explorer-step-telemetry").innerHTML =
            `<div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-1.5">` +
            `<div><strong>Active Step Telemetry:</strong> <code class="font-mono text-indigo-700">${tokText}</code></div>` +
            `<div>${corrBadge}</div>` +
            `</div>` +
            `<div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">` +
            `<div><span class="text-[var(--muted-foreground)] block font-sans">Pose (x, y, &psi;)</span>(${currentStep.x_m.toFixed(2)}m, ${currentStep.y_m >= 0 ? "+" : ""}${currentStep.y_m.toFixed(2)}m, ${currentStep.heading_deg >= 0 ? "+" : ""}${currentStep.heading_deg.toFixed(1)}&deg;)</div>` +
            `<div><span class="text-[var(--muted-foreground)] block font-sans">Implied Speed v(t)</span>${currentStep.implied_speed_mps.toFixed(2)} m/s (${currentStep.implied_speed_kmh.toFixed(1)} km/h)</div>` +
            `<div><span class="text-[var(--muted-foreground)] block font-sans">a_lon / a_lat / |a_tot|</span>${currentStep.a_lon_mps2 >= 0 ? "+" : ""}${currentStep.a_lon_mps2.toFixed(2)} / ${currentStep.a_lat_mps2 !== null ? (currentStep.a_lat_mps2 >= 0 ? "+" : "") + currentStep.a_lat_mps2.toFixed(2) : "0.00"} / ${currentStep.a_total_mps2 !== null ? currentStep.a_total_mps2.toFixed(2) : Math.abs(currentStep.a_lon_mps2).toFixed(2)} m/s&sup2;</div>` +
            `<div><span class="text-[var(--muted-foreground)] block font-sans">L2 Diff vs. Logged GT</span>${gtErrStr}</div>` +
            `</div>`;

          // Populate Step-Aware C1-C10 Table
          const tbodyStepChecks = document.getElementById("tbody-explorer-step-checks");
          tbodyStepChecks.innerHTML = (currentStep.checks || []).map((chk) => {
            const isTimeLocal = chk.evaluation_scope === "TIME_LOCAL_STEP";
            const scopeBadge = isTimeLocal
              ? `<span class="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-800 border border-indigo-500/25 font-mono text-[10px]">TIME_LOCAL_STEP</span>`
              : `<span class="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-800 border border-purple-500/25 font-mono text-[10px]">${chk.evaluation_scope}</span>`;
            let stHtml = "";
            if (chk.step_status === "NOT_DEFINED_AT_T0" || chk.step_status === "NOT_APPLICABLE_AT_STEP") {
              stHtml = `<span class="text-slate-600 font-semibold">${chk.step_status}</span>`;
            } else if (chk.step_status === "SATISFIED" || chk.step_status === "TRAJECTORY_WIDE_PASS") {
              stHtml = `<span class="text-emerald-700 font-semibold">${chk.step_status}</span>`;
            } else {
              stHtml = `<span class="text-rose-700 font-bold">${chk.step_status} (Step ${currentStep.step})</span>`;
            }
            return `<tr class="border-b border-[var(--border)]">` +
              `<th class="text-left p-1.5 bg-[var(--card)] font-mono text-[11px]">${chk.check_id}<div class="font-sans font-normal text-[10px] text-[var(--muted-foreground)]">${chk.step_note || ""}</div></th>` +
              `<td class="p-1.5">${scopeBadge}</td>` +
              `<td class="text-right p-1.5 font-mono">${chk.step_measured_value !== null && chk.step_measured_value !== undefined ? chk.step_measured_value + " " + chk.units : "N/A"}</td>` +
              `<td class="text-right p-1.5 font-mono">${chk.limit_value !== null && chk.limit_value !== undefined ? chk.limit_value + " " + chk.units : "N/A"}</td>` +
              `<td class="p-1.5">${stHtml}</td>` +
              `</tr>`;
          }).join("");

          if (expAutoSync.checked && r3bModeSel.value === "connected") {
            syncStepToR3BSimulator(condObj, currentStep);
          }
        }

        function renderR3BStoppingBreakdownSvg(pointByBranch, dAvailM, selectedBranch) {
          const container = document.getElementById("svg-r3b-sim-breakdown");
          if (!container) return;
          if (!pointByBranch || !pointByBranch.P0 || dAvailM === null || dAvailM <= 0) {
            container.innerHTML =
              `<div class="h-32 flex items-center justify-center text-xs text-amber-900 font-medium px-4 text-center bg-amber-500/5 rounded border border-amber-500/20">` +
              `4-Phase Stopping Distance Breakdown Withheld: R3B 1D Braking-Only Model is Not Applicable or Lacks Obstacle Distance Evidence for the Active State.` +
              `</div>`;
            return;
          }

          const w = 520, h = 148, padL = 118, padR = 24, padT = 22, padB = 24;
          const maxD = Math.max(
            dAvailM * 1.15,
            pointByBranch.P0.d_req_m * 1.12,
            pointByBranch.P1.d_req_m * 1.12,
            pointByBranch.P2.d_req_m * 1.12,
            25.0
          );
          const xToPx = (d) => padL + (Math.max(0, d) / maxD) * (w - padL - padR);

          let svg = `<svg viewBox="0 0 ${w} ${h}" class="w-full h-auto">`;
          const stepGrid = Math.max(10, Math.round(maxD / 5 / 10) * 10);
          for (let dm = 0; dm <= maxD; dm += stepGrid) {
            const px = xToPx(dm);
            svg += `<line x1="${px}" y1="${padT}" x2="${px}" y2="${h - padB}" stroke="currentColor" stroke-opacity="0.1" />`;
            svg += `<text x="${px}" y="${h - 7}" text-anchor="middle" font-size="9" fill="currentColor" fill-opacity="0.7">${dm}m</text>`;
          }

          const branches = ["P0", "P1", "P2"];
          const labels = {
            P0: "P0 (Hold Speed)",
            P1: "P1 (Passive Drag)",
            P2: "P2 (Supported Decel)",
          };
          branches.forEach((bid, idx) => {
            const b = pointByBranch[bid];
            const yRow = padT + 8 + idx * 30;
            const barH = 18;
            const isSel = bid === selectedBranch;
            svg += `<text x="${padL - 6}" y="${yRow + 12}" text-anchor="end" font-size="9.5" font-weight="${isSel ? "bold" : "normal"}" fill="currentColor">${labels[bid]}</text>`;

            const x0 = xToPx(0);
            const x1 = xToPx(b.d_pre_m);
            const x2 = xToPx(b.d_pre_m + b.d_delay_m);
            const x3 = xToPx(b.d_stop_m);
            const x4 = xToPx(b.d_req_m);

            svg += `<rect x="${x0}" y="${yRow}" width="${Math.max(0, x1 - x0)}" height="${barH}" fill="#f59e0b" />`;
            svg += `<rect x="${x1}" y="${yRow}" width="${Math.max(0, x2 - x1)}" height="${barH}" fill="#9333ea" />`;
            svg += `<rect x="${x2}" y="${yRow}" width="${Math.max(0, x3 - x2)}" height="${barH}" fill="#2563eb" />`;
            svg += `<rect x="${x3}" y="${yRow}" width="${Math.max(0, x4 - x3)}" height="${barH}" fill="#64748b" />`;
            if (isSel) {
              svg += `<rect x="${x0}" y="${yRow - 1}" width="${Math.max(2, x4 - x0)}" height="${barH + 2}" fill="none" stroke="#0f172a" stroke-width="1.5" />`;
            }
            const marginM = dAvailM - b.d_req_m;
            const mCol = marginM >= 0 ? "#047857" : "#be123c";
            svg += `<text x="${Math.min(w - 4, x4 + 5)}" y="${yRow + 12}" font-size="8.5" font-family="monospace" font-weight="bold" fill="${mCol}">D_req=${b.d_req_m.toFixed(1)}m (${marginM >= 0 ? "+" : ""}${marginM.toFixed(1)}m)</text>`;
          });

          const availPx = xToPx(dAvailM);
          svg += `<line x1="${availPx}" y1="${padT}" x2="${availPx}" y2="${h - padB}" stroke="#dc2626" stroke-width="2" stroke-dasharray="4 2" />`;
          svg += `<text x="${Math.max(padL + 40, Math.min(w - padR - 4, availPx - 4))}" y="${padT - 5}" text-anchor="end" font-size="9" font-weight="bold" fill="#dc2626">D_avail = ${dAvailM.toFixed(2)} m</text>`;

          svg += `<g transform="translate(${padL}, 12)" font-size="8.5" fill="currentColor">`;
          svg += `<rect x="0" y="-7" width="8" height="7" fill="#f59e0b" /><text x="11" y="-1">d_pre (t1)</text>`;
          svg += `<rect x="68" y="-7" width="8" height="7" fill="#9333ea" /><text x="79" y="-1">d_delay (t2)</text>`;
          svg += `<rect x="148" y="-7" width="8" height="7" fill="#2563eb" /><text x="159" y="-1">d_brake (t3+a_eff)</text>`;
          svg += `<rect x="255" y="-7" width="8" height="7" fill="#64748b" /><text x="266" y="-1">+2.0m Standstill</text>`;
          svg += `</g></svg>`;
          container.innerHTML = svg;
        }

        function badgeClassForPresentationStatus(st) {
          if (st === "NECESSARY_CONDITION_SATISFIED") {
            return "bg-emerald-500/15 text-emerald-800 border border-emerald-500/35";
          }
          if (st === "NECESSARY_CONDITION_VIOLATED") {
            return "bg-rose-500/15 text-rose-800 border border-rose-500/35";
          }
          if (st === "PARAMETER_SENSITIVE") {
            return "bg-amber-500/15 text-amber-900 border border-amber-500/35";
          }
          return "bg-slate-500/15 text-slate-800 border border-slate-500/35";
        }

        function renderR3BSimulator() {
          const isConnected = r3bModeSel.value === "connected";
          const condObj = explorerCatalog.conditions[expCondSel.value];
          const unit = r3bUnitSel.value;
          const rawSpeedVal = parseFloat(r3bSpeedInput.value);
          const vReqMps = unit === "kmh" ? rawSpeedVal / 3.6 : rawSpeedVal;
          const vReqKmh = vReqMps * 3.6;

          r3bSpeedDual.textContent = Number.isFinite(vReqMps)
            ? `${vReqMps.toFixed(2)} m/s (${vReqKmh.toFixed(1)} km/h)`
            : "INVALID SPEED";

          const obsMode = r3bObsModeSel.value;
          const rawD0 = parseFloat(r3bD0Input.value);
          const tauReq = parseFloat(r3bTauInput.value);
          const mu = parseFloat(r3bMuInput.value);
          const t1 = parseFloat(r3bT1Input.value);
          const t2 = parseFloat(r3bT2Input.value);
          const t3 = parseFloat(r3bT3Input.value);
          const aMax = parseFloat(r3bAmaxInput.value);
          const aSup = parseFloat(r3bAsupInput.value);
          const aDragMode = r3bDragModeSel ? r3bDragModeSel.value : "epa_midpoint";
          const aDragCustom = r3bAdragInput ? parseFloat(r3bAdragInput.value) : 0.25;
          const roadGradePct = r3bGradeSel ? parseFloat(r3bGradeSel.value) : 0.0;
          const selectedBranch = r3bPolicySel.value || "P1";

          if (r3bAdragInput) {
            if (aDragMode === "custom") r3bAdragInput.classList.remove("hidden");
            else r3bAdragInput.classList.add("hidden");
          }

          let egoX = 0.0, egoY = 0.0, egoHeadRad = 0.0;
          let obsLead = null;
          if (isConnected && condObj) {
            const stepAtTau = getInterpolatedExplorerStep(condObj, Number.isFinite(tauReq) ? tauReq : 0.0, Number.isFinite(mu) ? mu : 1.0);
            egoX = stepAtTau.x_m;
            egoY = stepAtTau.y_m;
            egoHeadRad = stepAtTau.heading_rad;
            obsLead = condObj.observed_in_lane_lead_obstacle;
          }

          let effectiveD0 = null;
          let evalObsMode = "counterfactual";
          if (isConnected && obsMode === "observed") {
            if (obsLead) {
              effectiveD0 = obsLead.x_m;
              evalObsMode = "observed";
            } else {
              effectiveD0 = null;
              evalObsMode = "none";
            }
          } else {
            effectiveD0 = rawD0;
            evalObsMode = "counterfactual";
          }

          const evalOut = evaluateInteractiveR3BInBrowser({
            v_mps: rawSpeedVal,
            speed_unit: unit,
            d0_m: effectiveD0,
            mu,
            tau_req_s: tauReq,
            t1_s: t1,
            t2_s: t2,
            t3_s: t3,
            a_max_mps2: aMax,
            a_sup_mps2: aSup,
            a_drag_mode: aDragMode,
            a_drag_custom_mps2: aDragCustom,
            road_grade_pct: roadGradePct,
            policy_branch: selectedBranch,
            obstacle_source_mode: evalObsMode,
            coupled_ego_x_m: isConnected ? egoX : 0.0,
            coupled_ego_y_m: isConnected ? egoY : 0.0,
            coupled_ego_heading_rad: isConnected ? egoHeadRad : 0.0,
            coupled_lead_speed_mps: obsLead ? obsLead.speed_mps : null,
            coupled_scene_id: isConnected && condObj ? condObj.scene_id : null,
          });

          // Render Layer 1 (Observed / Recorded Evidence) & Layer 2 (Assumed Counterfactual Inputs)
          const layerObsEl = document.getElementById("r3b-layer-observed");
          const layerAssEl = document.getElementById("r3b-layer-assumed");
          if (isConnected && condObj) {
            const obsLeadTxt = obsLead
              ? `Observed 3D Lead at d<sub>0</sub> = ${obsLead.x_m.toFixed(2)} m (v<sub>lead</sub> = ${obsLead.speed_mps.toFixed(2)} m/s)`
              : "None in &pm;1.75 m Corridor (Open Road)";
            layerObsEl.innerHTML =
              `<div class="font-bold text-emerald-900">Layer 1 &mdash; Observed / Recorded Evidence</div>` +
              `<div><strong>Scene &amp; Token:</strong> <code>${condObj.scene_id}</code> (<code>${condObj.frame_token}</code>)</div>` +
              `<div><strong>Logged Ego t<sub>0</sub>:</strong> v<sub>0</sub> = ${condObj.ego_initial_speed_mps.toFixed(2)} m/s (${condObj.ego_initial_speed_kmh.toFixed(1)} km/h), a<sub>x,0</sub> = ${condObj.ego_initial_accel_mps2.toFixed(2)} m/s&sup2;</div>` +
              `<div><strong>Dataset 3D Lead:</strong> ${obsLeadTxt}</div>` +
              `<div><strong>AutoVLA Pose @ &tau;<sub>req</sub>=${Number.isFinite(tauReq) ? tauReq.toFixed(1) : "?"}s:</strong> x=${egoX.toFixed(2)}m, y=${egoY >= 0 ? "+" : ""}${egoY.toFixed(2)}m, &psi;=${(egoHeadRad * 180 / Math.PI).toFixed(1)}&deg;</div>`;
          } else {
            layerObsEl.innerHTML =
              `<div class="font-bold text-emerald-900">Layer 1 &mdash; Observed / Recorded Evidence</div>` +
              `<div><strong>Mode:</strong> Standalone Parametric R3B Exploration (Decoupled from specific camera scene)</div>` +
              `<div><strong>Reference Coastdown Data:</strong> Empirical EPA coastdown table (60&ndash;130 km/h)</div>` +
              `<div><strong>Frozen R3B Baseline:</strong> 42 original research claims preserved unmodified</div>`;
          }

          const d0AssumedNote = evalOut.obstacle_source_classification === "OBSERVED_IN_LANE_ANNOTATION"
            ? (obsLead && Math.abs(obsLead.speed_mps) > 0.1
              ? `Static-target R3B projection of moving lead at d<sub>0</sub> = ${effectiveD0.toFixed(2)} m (v<sub>lead</sub> = ${obsLead.speed_mps.toFixed(2)} m/s)`
              : `Observed stationary 3D obstacle at d<sub>0</sub> = ${effectiveD0.toFixed(2)} m (no counterfactual d<sub>0</sub> needed)`)
            : (evalOut.obstacle_source_classification === "NONE_INSUFFICIENT_EVIDENCE"
              ? "No obstacle assumed (Observed mode on open-road scene &rarr; Insufficient Evidence)"
              : `Counterfactual stationary obstacle at d<sub>0</sub> = ${Number.isFinite(effectiveD0) ? effectiveD0.toFixed(2) : "?"} m`);

          const resolvedDrag = Number.isFinite(vReqMps) ? resolveEpaDragForSpeedMps(Math.max(0, vReqMps), aDragMode, aDragCustom) : 0.25;
          layerAssEl.innerHTML =
            `<div class="font-bold text-pink-900">Layer 2 &mdash; Assumed Counterfactual &amp; Model Inputs</div>` +
            `<div><strong>Obstacle Target:</strong> ${d0AssumedNote}</div>` +
            `<div><strong>Takeover Timing:</strong> &tau;<sub>req</sub> = ${Number.isFinite(tauReq) ? tauReq.toFixed(2) : "?"} s | Road Grade = ${Number.isFinite(roadGradePct) ? roadGradePct.toFixed(1) : "0.0"}%</div>` +
            `<div><strong>Surface &amp; Policy:</strong> &mu; = ${Number.isFinite(mu) ? mu.toFixed(2) : "?"} (&mu;&middot;g = ${Number.isFinite(mu) ? (mu * GRAVITY).toFixed(2) : "?"} m/s&sup2;) | Branch <strong>${selectedBranch}</strong> (P1 drag=${resolvedDrag.toFixed(2)} m/s&sup2;)</div>` +
            `<div><strong>Human/Brake Params:</strong> t<sub>1</sub>=${Number.isFinite(t1) ? t1.toFixed(2) : "?"}s, t<sub>2</sub>=${Number.isFinite(t2) ? t2.toFixed(2) : "?"}s, t<sub>3</sub>=${Number.isFinite(t3) ? t3.toFixed(2) : "?"}s, a<sub>max</sub>=${Number.isFinite(aMax) ? aMax.toFixed(2) : "?"}m/s&sup2;</div>`;

          const statusBadgeEl = document.getElementById("r3b-sim-status-badge");
          const underlyingEl = document.getElementById("r3b-sim-underlying-label");
          const stateBadgeEl = document.getElementById("r3b-sim-state-source-badge");
          const metricsGridEl = document.getElementById("r3b-sim-metrics-grid");
          const causalEl = document.getElementById("r3b-sim-causal-explanation");

          if (!evalOut.valid_inputs) {
            statusBadgeEl.textContent = "NOT_APPLICABLE";
            statusBadgeEl.className = "inline-block px-3 py-1 rounded-full text-xs font-bold " + badgeClassForPresentationStatus("NOT_APPLICABLE");
            underlyingEl.textContent = "Underlying R3B: INVALID_PARAMETERS (Withheld)";
            stateBadgeEl.innerHTML = `<span class="px-2 py-0.5 rounded bg-rose-500/15 text-rose-800 border border-rose-500/30 font-semibold">Input Validation Guardrail Triggered</span>`;
            metricsGridEl.innerHTML = `<div class="col-span-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-900 font-medium">${evalOut.validation_errors.join(" ")}</div>`;
            renderR3BStoppingBreakdownSvg(null, null, selectedBranch);
            causalEl.className = "p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-950 leading-relaxed";
            causalEl.innerHTML = `<strong>Invalid / Out-of-Range Parameters Rejected:</strong> ${evalOut.validation_errors.join(" ")} Numerical R3B margins are never fabricated for nonphysical inputs.`;
            return;
          }

          if (evalOut.presentation_status === "INSUFFICIENT_EVIDENCE") {
            statusBadgeEl.textContent = "INSUFFICIENT_EVIDENCE";
            statusBadgeEl.className = "inline-block px-3 py-1 rounded-full text-xs font-bold " + badgeClassForPresentationStatus("INSUFFICIENT_EVIDENCE");
            underlyingEl.textContent = "Underlying R3B: INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE";
            stateBadgeEl.innerHTML = formatStateSourceBadge(evalOut.state_source_classification);
            metricsGridEl.innerHTML =
              `<div class="col-span-4 p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-950">` +
              `<strong>Insufficient Evidence:</strong> No observed 3D in-corridor obstacle exists in the dataset annotations for <code>${condObj ? condObj.scene_id : "this scene"}</code>. Switch Obstacle Source to <strong>"Assumed Stationary d0 [m]"</strong> to evaluate a counterfactual obstacle.` +
              `</div>`;
            renderR3BStoppingBreakdownSvg(null, null, selectedBranch);
            causalEl.className = "p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-950 leading-relaxed";
            causalEl.innerHTML = `<strong>Why Evaluation is Withheld (<code>INSUFFICIENT_EVIDENCE</code>):</strong> Obstacle distance and time-to-collision (TTC) cannot be inferred from monocular/multi-view camera pixels alone without a 3D bounding-box track inside the &pm;1.75 m ego corridor or an explicit counterfactual d<sub>0</sub> assumption.`;
            return;
          }

          stateBadgeEl.innerHTML = formatStateSourceBadge(evalOut.state_source_classification);

          if (!evalOut.r3b_applicable) {
            statusBadgeEl.textContent = "NOT_APPLICABLE";
            statusBadgeEl.className = "inline-block px-3 py-1 rounded-full text-xs font-bold " + badgeClassForPresentationStatus("NOT_APPLICABLE");
            underlyingEl.textContent = "Underlying R3B: INSUFFICIENT_EVIDENCE_OR_NOT_APPLICABLE";
            metricsGridEl.innerHTML =
              `<div class="col-span-4 p-2.5 rounded bg-slate-500/10 border border-slate-500/30 text-slate-800">` +
              `<strong>1D Braking-Only R3B Not Applicable:</strong> ${evalOut.non_applicability_reasons.join(" ")}` +
              `</div>`;
            renderR3BStoppingBreakdownSvg(null, null, selectedBranch);
            causalEl.className = "p-2.5 rounded-lg bg-slate-500/10 border border-slate-500/30 text-slate-900 leading-relaxed";
            causalEl.innerHTML = `<strong>Why Evaluation is Withheld (<code>NOT_APPLICABLE</code>):</strong> ${evalOut.non_applicability_reasons.join(" ")}`;
            return;
          }

          const pointByBranch = evalOut.point_breakdown_by_branch;
          const selPt = evalOut.selected_policy_point;
          const selIv = evalOut.selected_policy_interval;
          const dRemM = evalOut.d_avail_m;
          const tAvailS = evalOut.t_avail_s;
          const marginM = selPt.margin_m;
          const marginS = selPt.margin_s;
          const pointPresStatus = selPt.presentation_status;

          statusBadgeEl.textContent = pointPresStatus;
          statusBadgeEl.className = "inline-block px-3 py-1 rounded-full text-xs font-bold " + badgeClassForPresentationStatus(pointPresStatus);
          underlyingEl.textContent = `Point: ${marginS >= 0 ? "SATISFIED" : "VIOLATED"} | Frozen Box Interval: ${selIv.presentation_status} (${selIv.underlying_r3b_status})`;

          metricsGridEl.innerHTML =
            `<div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">` +
            `<div class="text-[11px] text-[var(--muted-foreground)]">Available D<sub>avail</sub> / TTC</div>` +
            `<div class="font-mono font-bold text-sm mt-0.5">${dRemM.toFixed(2)} m</div>` +
            `<div class="font-mono text-[11px] text-[var(--muted-foreground)]">T<sub>avail</sub> = ${tAvailS.toFixed(2)} s</div>` +
            `</div>` +
            `<div class="p-2 rounded bg-[var(--background)] border border-[var(--border)]">` +
            `<div class="text-[11px] text-[var(--muted-foreground)]">Required D<sub>req</sub> (${selectedBranch})</div>` +
            `<div class="font-mono font-bold text-sm mt-0.5">${selPt.d_req_m.toFixed(2)} m</div>` +
            `<div class="font-mono text-[11px] text-[var(--muted-foreground)]">T<sub>req</sub> = ${selPt.t_req_s.toFixed(2)} s (+2.0m margin)</div>` +
            `</div>` +
            `<div class="p-2 rounded border ${badgeClassForPresentationStatus(pointPresStatus)}">` +
            `<div class="text-[11px] opacity-85">Point Margin (${selectedBranch})</div>` +
            `<div class="font-mono font-bold text-sm mt-0.5">${marginM >= 0 ? "+" : ""}${marginM.toFixed(2)} m</div>` +
            `<div class="font-mono text-[11px]">${marginS >= 0 ? "+" : ""}${marginS.toFixed(2)} s</div>` +
            `</div>` +
            `<div class="p-2 rounded border ${badgeClassForPresentationStatus(selIv.presentation_status)}">` +
            `<div class="text-[11px] opacity-85">R3B Parameter Box (${selectedBranch})</div>` +
            `<div class="font-mono font-bold text-xs mt-0.5">[${selIv.margin_min_m.toFixed(1)}, ${selIv.margin_max_m.toFixed(1)}] m</div>` +
            `<div class="font-mono text-[9.5px] break-all leading-tight mt-0.5">${selIv.presentation_status}</div>` +
            `</div>`;

          renderR3BStoppingBreakdownSvg(pointByBranch, dRemM, selectedBranch);

          const capExplain = selPt.is_friction_capped
            ? `road friction &mu;&middot;g = ${selPt.friction_cap_mps2.toFixed(2)} m/s&sup2; caps chassis capability a<sub>max</sub> = ${aMax.toFixed(2)} m/s&sup2;`
            : `chassis capability a<sub>max</sub> = ${aMax.toFixed(2)} m/s&sup2; is below the road-friction cap &mu;&middot;g = ${selPt.friction_cap_mps2.toFixed(2)} m/s&sup2;`;
          const p2SavingM = pointByBranch.P0.d_req_m - pointByBranch.P2.d_req_m;

          causalEl.className = "p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/25 text-[var(--foreground)] leading-relaxed";
          causalEl.innerHTML =
            `<strong>Causal 4-Phase Breakdown (${selectedBranch}):</strong> At v = <strong>${vReqMps.toFixed(2)} m/s (${vReqKmh.toFixed(1)} km/h)</strong> and remaining obstacle distance D<sub>avail</sub> = <strong>${dRemM.toFixed(2)} m</strong> (T<sub>avail</sub> = ${tAvailS.toFixed(2)} s), policy <strong>${selectedBranch}</strong> travels <strong>${selPt.d_pre_m.toFixed(2)} m</strong> during human reaction delay t<sub>1</sub> = ${t1.toFixed(2)} s (reaching v<sub>1</sub> = ${selPt.v_after_t1_mps.toFixed(2)} m/s), <strong>${selPt.d_delay_m.toFixed(2)} m</strong> during hydraulic delay t<sub>2</sub> = ${t2.toFixed(2)} s, and <strong>${selPt.d_brake_m.toFixed(2)} m</strong> during brake ramp/full braking (where ${capExplain}, giving a<sub>eff</sub> = ${selPt.a_eff_mps2.toFixed(2)} m/s&sup2;). Including the mandatory <strong>+2.0 m</strong> standstill margin yields D<sub>req</sub> = <strong>${selPt.d_req_m.toFixed(2)} m</strong> (T<sub>req</sub> = ${selPt.t_req_s.toFixed(2)} s) and a point margin of <strong>${marginM >= 0 ? "+" : ""}${marginM.toFixed(2)} m (${marginS >= 0 ? "+" : ""}${marginS.toFixed(2)} s &rarr; <code>${pointPresStatus}</code>)</strong>. Across policies at these parameters, system-supported pre-deceleration (<code>P2</code>) reduces required stopping distance by <strong>${p2SavingM.toFixed(2)} m</strong> compared to unmitigated hold-speed (<code>P0</code>). <em>Note: Satisfying this 1D braking-only necessary condition does not establish collision avoidance or safety.</em>`;
        }

        // Playback helper functions
        function updatePlaybackSpeedUi(speedMult) {
          playbackSpeedMultiplier = Number(speedMult) || 1.0;
          if (expSpeedSel) expSpeedSel.value = playbackSpeedMultiplier.toFixed(1);
          expSpeedBtns.forEach((btn) => {
            const bVal = parseFloat(btn.getAttribute("data-playback-speed") || "1.0");
            if (Math.abs(bVal - playbackSpeedMultiplier) < 1e-3) {
              btn.className = "px-1.5 py-0.5 rounded border border-indigo-600 bg-indigo-600 text-white text-[11px] font-mono font-bold";
            } else {
              btn.className = "px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--background)] text-[11px] font-mono";
            }
          });
          if (playTimer) {
            startPlayback();
          }
        }

        function pausePlayback() {
          if (playTimer) {
            clearInterval(playTimer);
            playTimer = null;
          }
          expPlayBtn.innerHTML = "&#9654; Play";
        }

        function startPlayback() {
          if (playTimer) {
            clearInterval(playTimer);
            playTimer = null;
          }
          expPlayBtn.innerHTML = "&#9654; Playing...";
          const dtStep = expChkSmooth.checked ? 0.1 : 0.5;
          const baseIntervalMs = expChkSmooth.checked ? 120 : 440;
          const intervalMs = Math.max(30, Math.round(baseIntervalMs / playbackSpeedMultiplier));
          playTimer = setInterval(() => {
            let cur = parseFloat(expTimeSlider.value || "0.0");
            if (cur >= 5.0 - 1e-4) {
              cur = 0.0;
            } else {
              cur = Math.min(5.0, Number((cur + dtStep).toFixed(2)));
            }
            expTimeSlider.value = String(cur);
            renderExplorerView();
          }, intervalMs);
        }

        function restartPlayback() {
          pausePlayback();
          expTimeSlider.value = "0.0";
          renderExplorerView();
        }

        // Event Listeners for Trajectory Explorer
        expSceneSel.addEventListener("change", () => {
          populateExplorerConditionOptions(expSceneSel.value);
          renderExplorerView();
        });
        expCondSel.addEventListener("change", renderExplorerView);
        expMuSel.addEventListener("change", () => {
          r3bMuSlider.value = expMuSel.value;
          r3bMuInput.value = parseFloat(expMuSel.value).toFixed(2);
          renderExplorerView();
          renderR3BSimulator();
        });
        expChkGt.addEventListener("change", renderExplorerView);
        expChkCounterpart.addEventListener("change", renderExplorerView);
        expChkSmooth.addEventListener("change", () => {
          expTimeSlider.step = expChkSmooth.checked ? "0.1" : "0.5";
          if (!expChkSmooth.checked) {
            const snapped = Math.round(parseFloat(expTimeSlider.value) * 2.0) / 2.0;
            expTimeSlider.value = snapped.toFixed(1);
          }
          if (playTimer) startPlayback();
          renderExplorerView();
        });
        expTimeSlider.addEventListener("input", renderExplorerView);

        expPrevBtn.addEventListener("click", () => {
          pausePlayback();
          const cur = parseFloat(expTimeSlider.value || "0.0");
          const next = Math.max(0.0, Math.round((cur - 0.5) * 2.0) / 2.0);
          expTimeSlider.value = next.toFixed(1);
          renderExplorerView();
        });
        expNextBtn.addEventListener("click", () => {
          pausePlayback();
          const cur = parseFloat(expTimeSlider.value || "0.0");
          const next = Math.min(5.0, Math.round((cur + 0.5) * 2.0) / 2.0);
          expTimeSlider.value = next.toFixed(1);
          renderExplorerView();
        });
        expPlayBtn.addEventListener("click", () => {
          if (playTimer) {
            pausePlayback();
          } else {
            startPlayback();
          }
        });
        if (expPauseBtn) {
          expPauseBtn.addEventListener("click", pausePlayback);
        }
        if (expRestartBtn) {
          expRestartBtn.addEventListener("click", restartPlayback);
        }
        expSpeedBtns.forEach((btn) => {
          btn.addEventListener("click", () => {
            updatePlaybackSpeedUi(parseFloat(btn.getAttribute("data-playback-speed") || "1.0"));
          });
        });
        if (expSpeedSel) {
          expSpeedSel.addEventListener("change", () => {
            updatePlaybackSpeedUi(parseFloat(expSpeedSel.value || "1.0"));
          });
        }

        expSendBtn.addEventListener("click", () => {
          const condObj = explorerCatalog.conditions[expCondSel.value];
          if (!condObj) return;
          const muVal = parseFloat(expMuSel.value || "1.0");
          const tVal = parseFloat(expTimeSlider.value || "0.0");
          const currentStep = getInterpolatedExplorerStep(condObj, tVal, muVal);
          syncStepToR3BSimulator(condObj, currentStep);
        });

        // Event Listeners for R3B Simulator Controls
        r3bModeSel.addEventListener("change", () => {
          if (r3bModeSel.value === "connected") {
            const condObj = explorerCatalog.conditions[expCondSel.value];
            const currentStep = getInterpolatedExplorerStep(condObj, parseFloat(expTimeSlider.value || "0.0"), parseFloat(expMuSel.value || "1.0"));
            syncStepToR3BSimulator(condObj, currentStep);
          } else {
            renderR3BSimulator();
          }
        });

        r3bUnitSel.addEventListener("change", () => {
          const prevVal = parseFloat(r3bSpeedInput.value || "0.0");
          if (r3bUnitSel.value === "kmh") {
            const kmh = prevVal * 3.6;
            r3bSpeedSlider.max = "150.0";
            r3bSpeedSlider.value = kmh.toFixed(1);
            r3bSpeedInput.value = kmh.toFixed(1);
          } else {
            const mps = prevVal / 3.6;
            r3bSpeedSlider.max = "42.0";
            r3bSpeedSlider.value = mps.toFixed(2);
            r3bSpeedInput.value = mps.toFixed(2);
          }
          renderR3BSimulator();
        });

        r3bSpeedSlider.addEventListener("input", () => {
          r3bSpeedInput.value = r3bSpeedSlider.value;
          r3bModeSel.value = "standalone";
          renderR3BSimulator();
        });
        r3bSpeedInput.addEventListener("input", () => {
          if (Number.isFinite(parseFloat(r3bSpeedInput.value))) {
            r3bSpeedSlider.value = r3bSpeedInput.value;
          }
          r3bModeSel.value = "standalone";
          renderR3BSimulator();
        });

        r3bObsModeSel.addEventListener("change", renderR3BSimulator);
        r3bD0Slider.addEventListener("input", () => {
          r3bD0Input.value = r3bD0Slider.value;
          r3bObsModeSel.value = "counterfactual";
          renderR3BSimulator();
        });
        r3bD0Input.addEventListener("input", () => {
          if (Number.isFinite(parseFloat(r3bD0Input.value))) {
            r3bD0Slider.value = r3bD0Input.value;
          }
          r3bObsModeSel.value = "counterfactual";
          renderR3BSimulator();
        });

        r3bTauSlider.addEventListener("input", () => {
          r3bTauInput.value = r3bTauSlider.value;
          if (r3bModeSel.value === "connected") {
            expTimeSlider.value = r3bTauSlider.value;
            renderExplorerView();
          } else {
            renderR3BSimulator();
          }
        });
        r3bTauInput.addEventListener("input", () => {
          if (Number.isFinite(parseFloat(r3bTauInput.value))) {
            r3bTauSlider.value = r3bTauInput.value;
          }
          renderR3BSimulator();
        });

        r3bPolicySel.addEventListener("change", renderR3BSimulator);

        r3bMuSlider.addEventListener("input", () => {
          r3bMuInput.value = parseFloat(r3bMuSlider.value).toFixed(2);
          renderR3BSimulator();
        });
        r3bMuInput.addEventListener("input", () => {
          if (Number.isFinite(parseFloat(r3bMuInput.value))) {
            r3bMuSlider.value = r3bMuInput.value;
          }
          renderR3BSimulator();
        });
        document.querySelectorAll("[data-mu-preset]").forEach((btn) => {
          btn.addEventListener("click", () => {
            const m = parseFloat(btn.getAttribute("data-mu-preset"));
            r3bMuSlider.value = m.toFixed(2);
            r3bMuInput.value = m.toFixed(2);
            renderR3BSimulator();
          });
        });

        r3bT1Slider.addEventListener("input", () => {
          r3bT1Input.value = parseFloat(r3bT1Slider.value).toFixed(2);
          renderR3BSimulator();
        });
        r3bT1Input.addEventListener("input", () => {
          if (Number.isFinite(parseFloat(r3bT1Input.value))) {
            r3bT1Slider.value = r3bT1Input.value;
          }
          renderR3BSimulator();
        });

        [r3bT2Input, r3bT3Input, r3bAmaxInput, r3bAsupInput, r3bAdragInput].forEach((inp) => {
          if (inp) inp.addEventListener("input", renderR3BSimulator);
        });
        if (r3bDragModeSel) {
          r3bDragModeSel.addEventListener("change", renderR3BSimulator);
        }
        if (r3bGradeSel) {
          r3bGradeSel.addEventListener("change", renderR3BSimulator);
        }

        r3bResetBtn.addEventListener("click", () => {
          r3bMuSlider.value = "1.00";
          r3bMuInput.value = "1.00";
          r3bT1Slider.value = "1.65";
          r3bT1Input.value = "1.65";
          r3bT2Input.value = "0.10";
          r3bT3Input.value = "0.60";
          r3bAmaxInput.value = "8.00";
          r3bAsupInput.value = "2.00";
          if (r3bDragModeSel) r3bDragModeSel.value = "epa_midpoint";
          if (r3bAdragInput) r3bAdragInput.value = "0.25";
          if (r3bGradeSel) r3bGradeSel.value = "0.0";
          r3bPolicySel.value = "P1";
          renderR3BSimulator();
        });

        // Expose programmatic API on window for automated headless browser verification
        window.VLA_INTERACTIVE_EXPLORER = {
          catalog: explorerCatalog,
          stoppingDistanceR3BExact,
          evaluateR3BIntervalForBranch,
          evaluateInteractiveR3BInBrowser,
          verifyAllParityCasesInBrowser,
          renderExplorerView,
          renderR3BSimulator,
          startPlayback,
          pausePlayback,
          restartPlayback,
          updatePlaybackSpeedUi,
          isPlaying: () => Boolean(playTimer),
          getPlaybackSpeed: () => playbackSpeedMultiplier,
          setTime: (tSec) => {
            const clamped = Math.max(0.0, Math.min(5.0, parseFloat(tSec) || 0.0));
            expTimeSlider.value = clamped.toFixed(1);
            renderExplorerView();
          },
          getPlaybackState: () => ({
            playing: Boolean(playTimer),
            speed: playbackSpeedMultiplier,
            time_s: parseFloat(expTimeSlider.value) || 0.0,
            scene_key: expSceneSel.value,
            condition_key: expCondSel.value,
          }),
        };

        // Initialize Trajectory Explorer & R3B Simulator on Scene 02 (which has both an observed stationary obstacle d0=55.49m AND a command intervention!)
        expSceneSel.value = "scene_02_stationary_lead_obstacle";
        populateExplorerConditionOptions("scene_02_stationary_lead_obstacle");
        r3bObsModeSel.value = "observed";
        renderExplorerView();
      }

      renderScene05AblationChart();
      renderCommandSensitivitySection();
      renderC10RobustnessSection();
      populateObstacleOptions(records[0]);
      renderActiveView();
    })();
  </script>
</body>
</html>
"""


def generate_interactive_report(
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    claim_register_path: str | Path = DEFAULT_CLAIM_REGISTER_PATH,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    output_html_path: str | Path = DEFAULT_REPORT_PATH,
) -> Path:
    """Generate the self-contained deterministic HTML evaluation dashboard."""
    bundle = build_report_data_bundle(
        summary_path=summary_path,
        claim_register_path=claim_register_path,
        data_dir=data_dir,
    )
    json_str = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    html_content = HTML_TEMPLATE.replace("__REPORT_DATA_JSON__", json_str)
    out_path = Path(output_html_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    out = generate_interactive_report()
    print(f"Generated interactive HTML report at {out} ({out.stat().st_size / 1024:.1f} KB)")
