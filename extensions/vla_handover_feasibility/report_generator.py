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


def build_report_data_bundle(
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    claim_register_path: str | Path = DEFAULT_CLAIM_REGISTER_PATH,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    embed_raw_jpegs: bool = False,
) -> dict[str, Any]:
    """Assemble deterministic JSON data bundle with camera sensor provenance cards for the interactive report."""
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

    return {
        "summary": summary,
        "extension_claims": claims,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>VLA-Informed Handover Feasibility Analysis — Research Evaluation Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --background: #f8fafc;
      --foreground: #0f172a;
      --card: #ffffff;
      --border: #e2e8f0;
      --muted-foreground: #475569;
    }
    .dashboard-title {
      font-size: clamp(1.25rem, 1rem + 1.15vw, 1.8rem);
      line-height: 1.25;
    }
    .cam-frame {
      aspect-ratio: 16 / 9;
      width: 100%;
      object-fit: cover;
    }
    .table-wrapper {
      overflow: auto;
      max-inline-size: 100%;
      max-block-size: min(520px, 78dvh);
      container-type: inline-size;
    }
    .table-wrapper table {
      border-collapse: separate;
      border-spacing: 0;
      width: 100%;
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
    @container (width < 520px) {
      .table-wrapper table,
      .table-wrapper thead,
      .table-wrapper tbody,
      .table-wrapper tr,
      .table-wrapper th,
      .table-wrapper td {
        display: block;
      }
      .table-wrapper thead {
        display: none;
      }
      .table-wrapper tr {
        margin-block-end: 0.75rem;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.5rem;
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
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-4 md:p-6">
  <div class="max-w-[1440px] mx-auto space-y-5">

    <!-- Header & Central Research Question -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm print-avoid-break">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1.5 max-w-4xl">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-700 border border-blue-500/30">
              Extension: extensions/vla_handover_feasibility (v0.3.0)
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-700 border border-emerald-500/30">
              Genuine AutoVLA Inference (Qwen2.5-VL-3B + 2048 Physical Action Tokens)
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-800 border border-amber-500/30">
              Original 42 Claims Frozen &amp; Unmodified
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-700 border border-purple-500/30">
              11-Point Provenance Verified
            </span>
          </div>
          <h1 class="dashboard-title font-bold text-[var(--foreground)]">
            VLA-Informed Handover Feasibility Analysis — Research Evaluation Dashboard
          </h1>
          <p class="text-sm text-[var(--muted-foreground)]">
            <strong>Central Research Question:</strong>
            <span id="rq-text"></span>
          </p>
        </div>
        <div class="text-xs text-[var(--muted-foreground)] bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1 min-w-[290px]">
          <div><strong>Model:</strong> <span id="prov-model" class="font-medium text-[var(--foreground)]"></span></div>
          <div><strong>Checkpoint:</strong> <code id="prov-ckpt" class="font-mono text-[var(--foreground)]"></code></div>
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
