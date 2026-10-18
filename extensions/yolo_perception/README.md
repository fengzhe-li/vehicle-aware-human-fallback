# Independent YOLO perception extension

Phases A–C implement local, offline 2D detection on the existing 84 original camera JPEGs, descriptive statistics, local overlays and a read-only join to saved AutoVLA results. Nothing feeds back into AutoVLA, C1–C10 or R3B. No distance, collision risk, safety, precision, recall or mAP is inferred.

## Architecture and read-only integration

![Independent YOLO workflow with a read-only join to saved AutoVLA results](docs/assets/architecture.png)

Image identity and SHA-256 checks precede inference. Validated 2D records support descriptive summaries and local visualisation; saved AutoVLA predictions and evaluations are associated by scene identity only. No detector output changes trajectory predictions, physical equations or research conclusions. The diagram shows the data relationship, not execution timing.

## Measured local results

The recorded YOLO11n CPU run processed **84/84 images**, yielding **455 retained detections**, **20 empty images** and **zero processing failures**. These are counts across correlated frames and views, not unique physical objects or verified true positives. End-to-end median latency was **22.887 ms**; backend inference median was **18.946 ms**.

![Measured local CPU median, mean and p95 latency; warmup, rendering and writing excluded](docs/assets/measured_latency.png)

Measurements are from the archived local run, not GitHub CI. The chart uses CPU FP32 with one thread; loading/warmup and output rendering/writing are excluded. Host-load dependence prevents a real-time guarantee. Precision, recall and mAP are unavailable without reviewed 2D ground truth. See the [engineering report](ENGINEERING_REPORT.md) for exact environment, measurement boundaries and limitations.

## Validation and provenance

![Historical validation: input hashes, repeatability and scoped software regression results](docs/assets/validation_summary.png)

This figure records the pre-publication checks: 39 extension tests, 74 selected regressions (2 deselected), 84 exact repeated detection matches, and 361 unchanged baseline files. It is historical evidence, not a complete-suite or cross-device claim. The presentation update intentionally changes the root README only among those 361 files; its single snapshot entry is updated explicitly, while the other 360 protected files and all original images remain unchanged. Previous and proposed README hashes are retained in the [visual provenance record](docs/assets/provenance.json).

All three figures are original diagrams/charts under the extension's AGPL-3.0-only licence. They contain no camera pixels, derived detection overlays, pretrained weights or synthetic perception evidence. Their [sources, hashes and sizes](docs/assets/provenance.json) are recorded for review.

The [manually triggered YOLO software-contract workflow](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/39082125271) passed on published commit `7d8e6396675c2961b62bd72ab98426f977c85820` (Linux, Python 3.11). It tests synthetic software contracts and frozen-file integrity, not live model accuracy. This local presentation update has not yet been pushed.

## Licensing and data

New extension source, tests, configuration, workflow and accompanying documentation are AGPL-3.0-only (see [LICENSE](LICENSE), SPDX headers and the root [LICENSING.md scope notice](../../LICENSING.md)). Existing repository code retains its existing licence. The repository's root MIT licence does not cover Ultralytics or its weights. Ultralytics 8.3.221 and YOLO11n weights are subject to AGPL-3.0 or an applicable commercial licence. This local integration does not resolve all obligations for any future public distribution or hosted service; review that deployment's licence requirements first. Directory or process separation is not a licence exemption.

Original OpenScene/nuPlan imagery remains third-party material, with OpenScene's CC BY-NC-SA 4.0 declaration and applicable upstream terms. Images and overlays are local only. Do not upload image-bearing HTML reports, overlays, weights or original images. The new workflow tests software contracts only and neither downloads weights nor deploys Pages.

Official weight: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt

Size: 5,613,764 bytes. SHA-256:
`0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`

Licence references: https://www.ultralytics.com/license and https://huggingface.co/datasets/OpenDriveLab/OpenScene/blob/main/README.md

## Reproduce in an isolated environment

Use a Git checkout: run provenance requires `git rev-parse HEAD`; an extracted source archive without Git metadata is insufficient. The tested environment is macOS arm64, Python 3.14.5. Do not install into the original `.venv`. The platform lock contains all installed versions; it is not claimed to be a Linux lock or a cryptographic package lock. Wheel availability and hashes should be archived for long-term environment preservation.

```sh
cd vehicle-aware-human-fallback  # from the parent of your checkout
python3.14 -m venv .venv-yolo
.venv-yolo/bin/python -m pip install -r extensions/yolo_perception/requirements-lock-macos-arm64.txt
export YOLO_CONFIG_DIR="$PWD/extensions/yolo_perception/.runtime"
export MPLCONFIGDIR="$PWD/extensions/yolo_perception/.runtime/matplotlib"
```

Weights are already downloaded locally in `.runtime/yolo11n.pt`. On a new machine, explicitly obtain the above 5.61 MB official asset after accepting the licence conditions and verify its hash. The runner requires an existing local weight and never downloads missing weights or datasets. Original JPEGs are read from the existing VLA data directory. Recovery, when needed, uses the existing extractor and is not invoked by this extension.

```sh
.venv-yolo/bin/python -m extensions.yolo_perception.cli check-frozen
.venv-yolo/bin/python -m extensions.yolo_perception.cli run \
  --weights extensions/yolo_perception/.runtime/yolo11n.pt \
  --weights-sha256 0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1 \
  --output extensions/yolo_perception/artifacts/my-smoke --smoke
.venv-yolo/bin/python -m extensions.yolo_perception.cli run \
  --weights extensions/yolo_perception/.runtime/yolo11n.pt \
  --weights-sha256 0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1 \
  --output extensions/yolo_perception/artifacts/my-full
```

Every output directory must be new. A conflicting directory fails without changing the existing run. Interrupted runs retain their completed per-frame JSON and a progress record; automatic resume is not implemented. Use a new directory for a retry. `STARTED` without completion is incomplete, not success.

Run the full command again with another output directory, then compare:

```sh
.venv-yolo/bin/python -m extensions.yolo_perception.cli compare \
  --first extensions/yolo_perception/artifacts/my-full \
  --second extensions/yolo_perception/artifacts/my-repeat
.venv-yolo/bin/python -m pytest extensions/yolo_perception/tests -q
.venv/bin/python -m pytest extensions/vla_handover_feasibility/tests \
  tests/test_r3b_bounds.py tests/test_r3b_model_corrections.py \
  tests/test_r3b_reporting.py tests/test_r6a_figures.py::test_scientific_results_unchanged \
  -q -k 'not one_command_offline_demo' -p no:cacheprovider
```

The existing demo test is excluded because it regenerates existing artifacts in place. The existing `r3b_study` marker remains excluded. No frozen study is rerun. CI uses synthetic JPEGs and fake detector outputs explicitly as software fixtures, never as empirical perception evidence. Live results are a separate local validation.

## Configuration and artifacts

`configs/baseline.json` fixes CPU FP32, one thread, batch size one, seed zero, image size 640, rectangular letterboxing, confidence 0.25, class-aware NMS IoU 0.7 and maximum 300 boxes. All 80 COCO classes are retained; there is no hidden road-class filter. Saved coordinates are Ultralytics' original-image pixel xyxy coordinates. Image decoding/preprocessing is handled by the pinned backend; input JPEGs are never resized or overwritten on disk.

A run contains `inventory.json`, `run_manifest.json`, `frames/*.json`, `detections.jsonl`, `summary.json`, `vla_associations.json`, `overlays/*.jpg` and `report.html`. Open the HTML locally. Every input carries a SHA-256 and scene/view/index identity. Camera capture timestamps remain null because they were not recovered. The scene reference timestamp is kept separately.

Inventory failure blocks inference. Empty detections are successful inference above the configured threshold, not proof that a scene is empty. Invalid boxes, non-finite values, backend errors and render errors become explicit failures. Per-frame records are atomically saved; failures are included in denominators. Model setup/warmup failure fails the run. CPU metadata restrictions are recorded without aborting inference.

Timing includes image loading and the predict call, excludes overlays and report writing, and excludes one warmup image. Backend inference time is separately reported. Peak RSS is whole-process high-water memory, not GPU memory. Confidence is uncalibrated and conditional on the configured threshold. The repeatability comparison requires COMPLETE run status, nonempty coverage matching the recorded image count, valid result-to-inventory associations, intact recorded output digests, and matching sources, dependencies, input manifests, runtime hardware metadata and configuration; timing fields are excluded. It does not promise equivalence across devices.

AutoVLA association validates scene ID, token, timestamp, log, scene manifest hash and exact agreement between saved prediction content and evaluation summary. Only JSON is read. Three-dimensional lead-obstacle records are not converted into 2D labels. Historical frames are not treated as observations of future predicted positions.

`frozen_inputs.json` freezes the 361 pre-existing tracked files except `.gitignore`; original images receive independent per-file SHA-256 verification. Future deliberate baseline changes require an explicit review of this snapshot, not automatic refresh. Root requirements and the original environment are untouched.

See [ENGINEERING_REPORT.md](ENGINEERING_REPORT.md) for historical measured local results, test results and remaining gaps. Its pre-publication status statements describe that earlier audit.
