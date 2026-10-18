# YOLO perception extension engineering report

Implemented Phases A, B and C on 18 October 2026 in the existing local repository. Changes are local and uncommitted. No push, PR, frozen experiment rerun, model training or dataset download occurred.

## Actual experiment

The three-view real-image smoke test completed 3/3 images with 12 detections, one empty result and zero processing failures. The initial attempt failed before inference because CPU-brand metadata access was denied by the sandbox; the failure is preserved in artifacts/smoke/run_manifest.json. Metadata collection was corrected to record unavailable fields without blocking inference. The successful smoke is artifacts/smoke-v2.

The final accepted run is artifacts/final-84, followed by artifacts/final-repeat-84. Both processed all 84 SHA-256-verified JPEGs from seven scenarios successfully. There are 455 above-threshold detections, 20 successful empty images and 0 failures. Counts are detections across correlated frames and views, not unique physical objects. No 2D labels exist, so accuracy metrics remain null.

| Timing boundary, after one warmup | Median ms | Mean ms | p95 ms | Maximum ms |
|---|---:|---:|---:|---:|
| Decode + preprocess + inference + postprocess | 22.887 | 22.925 | 23.470 | 23.811 |
| Backend inference only | 18.946 | 18.922 | 19.252 | 19.726 |

Rendering, report writing, model loading and warmup are excluded from these timings. Repeat-run end-to-end median: 22.788 ms. Timing is host-load dependent, not a real-time guarantee. Earlier full runs and their timings are retained; the first full run had a 26.291 ms median and 234.202 ms maximum. Peak process RSS in the final run: 426,754,048 bytes, including framework/model memory.

Confidence range 0.2502–0.9253; mean 0.5122, median 0.4909, p95 0.8312. Histogram counts for [0,.25), [.25,.5), [.5,.75), [.75,1]: [0, 231, 157, 67]. Scores are uncalibrated and threshold-conditioned.

| Predicted class | Count |
|---|---:|
| bench | 1 |
| bus | 1 |
| car | 196 |
| clock | 1 |
| fire hydrant | 3 |
| person | 97 |
| stop sign | 2 |
| traffic light | 138 |
| truck | 16 |

All 80 model classes were allowed. Rare predictions such as clock or bench are not verified true positives. A sampled overlay was visually inspected for successful rendering and original-image alignment; this was not an accuracy assessment.

## Model and environment

- Model: official COCO-pretrained YOLO11n detection, yolo11n.pt, 5,613,764 bytes.
- Weight SHA-256: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
- Source: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
- Python 3.14.5; macOS-26.3.2-arm64-arm-64bit-Mach-O; architecture arm64.
- Ultralytics 8.3.221; PyTorch 2.14.1; torchvision 0.29.1; NumPy 2.5.4; OpenCV 5.0.0.93; Pillow 13.0.0; pytest 9.1.1.
- Isolated .venv-yolo; original root requirements and original .venv not changed.
- CPU FP32, batch one, one PyTorch thread, 10 logical CPUs reported; MPS and CUDA unavailable in this process. CPU marketing name could not be queried due to sandbox restrictions.
- Image size 640, rectangular letterboxing, confidence 0.25, NMS IoU 0.7, class-aware NMS, maximum 300 detections. Original-image xyxy coordinates retained.
- Exact installed versions in requirements-lock-macos-arm64.txt; full runtime versions, config hash and per-source hashes in each run manifest. The Git base commit is 3e2f850bacf7a969b91ab9f874738bb2b4bfa787; implementation is uncommitted, so source hashes identify actual new code.

## Validation and immutability

- New software unit/integration tests: **39 passed**. Includes missing files, wrong hash, corrupt JPEG with a matching hash, invalid view/index, traversal, duplicate paths, malformed/non-finite boxes, empty detections, output conflicts, incorrect AutoVLA association, injected per-image inference failure and repeatability checks. Synthetic fixtures are explicitly software tests only.
- Existing selected regression tests: **74 passed, 2 deselected**. Covers VLA extension, R3B bounds/model corrections/reporting and scientific-result integrity. The existing report-generating demo test and frozen r3b_study rerun are excluded. This is not a claim that the complete repository suite or browser QA was rerun.
- All **361** pre-existing tracked files other than intentionally edited .gitignore match the pre-implementation SHA-256 snapshot, including root requirements, all AutoVLA predictions, scientific results, claims and equations.
- Final independent image check: **84/84** still match original SHA-256 and byte sizes and decode successfully.
- Repeatability: **84/84** exact detection-content matches across final and repeat runs; latency excluded. No cross-device guarantee.
- Git contains no tracked .pt weights or .jpg files. New artifacts, environment and runtime directories are ignored. No git commit, push or PR operations were executed.

## Files created and modified

Only existing file modified: `.gitignore` (new environment/runtime/artifact exclusions).

New workflow: `.github/workflows/yolo_perception_verify.yml` (software contracts, no weights, data downloads or deployment). It has not run on GitHub because no push or PR was created.

New root licence scope notice: `LICENSING.md`.

New extension files:

- `extensions/yolo_perception/ENGINEERING_REPORT.md`
- `extensions/yolo_perception/LICENSE`
- `extensions/yolo_perception/README.md`
- `extensions/yolo_perception/__init__.py`
- `extensions/yolo_perception/cli.py`
- `extensions/yolo_perception/configs/baseline.json`
- `extensions/yolo_perception/evaluation.py`
- `extensions/yolo_perception/frozen_inputs.json`
- `extensions/yolo_perception/inference.py`
- `extensions/yolo_perception/inventory.py`
- `extensions/yolo_perception/reproducibility.py`
- `extensions/yolo_perception/requirements-lock-macos-arm64.txt`
- `extensions/yolo_perception/requirements.in`
- `extensions/yolo_perception/schemas.py`
- `extensions/yolo_perception/storage.py`
- `extensions/yolo_perception/tests/conftest.py`
- `extensions/yolo_perception/tests/test_perception.py`
- `extensions/yolo_perception/visualization.py`
- `extensions/yolo_perception/vla_readonly.py`

Local ignored outputs include per-frame records, JSONL detections, aggregate statistics, seven read-only AutoVLA associations, run manifests, 84 overlays and a local HTML report for each full run. Source images are neither copied nor overwritten.

## Licensing and remaining limitations

New extension source, tests, configuration, workflow and documentation are AGPL-3.0-only; the AGPL text and SPDX headers are included. Ultralytics and its weights are not covered by the repository's MIT licence. Existing code keeps its existing licence. Future distribution or service deployment needs an assessment of the combined work's obligations or an applicable commercial licence. No public redistribution has occurred.

OpenScene image terms remain applicable, including its CC BY-NC-SA 4.0 declaration. Keep original imagery and image-bearing overlays/reports local. Hashes do not replace upstream attribution or licence requirements.

No precision, recall, mAP, calibration, distance, TTC, collision risk, safety improvement or causal relationship with VLA failures is claimed. Empty outputs mean no retained detections above threshold. Unknown camera capture times remain null. Camera calibration, human-reviewed 2D annotations, dataset expansion, GPU inference and automatic interrupted-run resume remain outside this delivery. Full install compatibility is validated only for the recorded macOS CPU environment; the new Linux workflow has not been executed remotely.

Reproduction commands and output contracts are in README.md. Read-only integration consumes existing JSON only; it does not run AutoVLA or alter R3B inputs. Stop point: implementation and testing complete, awaiting local review.

## Final pre-publication review

The review added a root LICENSING.md scope notice and an offline CI test guard in tests/conftest.py, removed a machine-specific documentation path, and strengthened the repeatability verifier against incomplete runs, truncated or tampered output, incorrect inventory associations and hardware mismatches. All additions remain local. The original core was not edited.

After these changes, 39 extension tests passed with network access and neural-backend imports blocked. The selected existing regression suite passed 74 tests with 2 deselected. Saved final runs still compare identically across 84 images with output digest verification. Inference was not repeated during publication review: the measured performance above belongs to the archived runs and their recorded source hashes; the review changed verification, tests and documentation, not the detector.

The isolated installed environment matches the complete version-pinned lock and passes pip check. A fresh installation from an empty environment and the remote Linux CI execution have not been performed. The lock lacks wheel hashes and is a platform-specific version snapshot, so indefinite or cross-platform reconstruction is not established.

The 39 extension tests also pass against a source-only export with zero original JPEGs and no model weights, using the existing Git metadata read-only to identify HEAD. An initial archive-only check failed two pipeline tests because Git metadata was absent; the checkout requirement is now explicit. No source or private image dependency was needed to resolve that failure.
