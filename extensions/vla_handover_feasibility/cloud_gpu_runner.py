"""Reproducible Zero-Cost Cloud GPU Execution Alternative for AutoVLA Inference.

Provides a self-contained CLI / notebook-compatible runner for executing the exact
same AutoVLA (`Zewei-Zhou/AutoVLA` -> `AutoVLA_PDMS_89.ckpt`) checkpoint and
7 extracted nuPlan/OpenScene/NAVSIM scenes on a cloud CUDA GPU (e.g. free-tier
Google Colab T4 16GB VRAM or Kaggle 2xT4, incurring $0.00 cost) when local
16GB unified-memory Apple Silicon execution is memory-constrained.

Usage on a Cloud CUDA GPU instance (e.g., Google Colab / Kaggle):
    1. Clone the repository and upload `extensions/vla_handover_feasibility/data/`
    2. Install requirements:
       pip install torch torchvision transformers==4.57.1 accelerate safetensors qwen-vl-utils pillow scipy numpy
    3. Convert the AutoVLA checkpoint once (~45 seconds on cloud bandwidth):
       python -m extensions.vla_handover_feasibility.download_convert_autovla
    4. Run sequential batch_size=1 inference on CUDA (~1.2 s per scene on T4/L4):
       python -m extensions.vla_handover_feasibility.cloud_gpu_runner --device cuda
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from extensions.vla_handover_feasibility.experiment_runner import (
    DEFAULT_ARTIFACTS_DIR,
    evaluate_all_predictions_and_counterfactuals,
    run_genuine_vla_inference_all_scenes,
)
from extensions.vla_handover_feasibility.report_generator import (
    generate_interactive_report,
)
from extensions.vla_handover_feasibility.vla_inference import (
    DEFAULT_AUTOVLA_MODEL_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_PREDICTIONS_DIR,
)


def print_cloud_gpu_diagnostics() -> dict[str, object]:
    """Inspect CUDA availability and VRAM capacity without incurring any external API costs."""
    cuda_ok = bool(torch.cuda.is_available())
    info: dict[str, object] = {
        "cuda_available": cuda_ok,
        "mps_available": bool(torch.backends.mps.is_available()),
        "torch_version": torch.__version__,
    }
    if cuda_ok:
        dev_idx = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(dev_idx)
        info["cuda_device_name"] = props.name
        info["cuda_total_vram_gb"] = round(props.total_memory / (1024**3), 2)
    return info


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproducible zero-cost Cloud GPU runner for AutoVLA trajectory inference and R3B evaluation."
    )
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "mps")
    parser.add_argument("--scene-id", action="append", dest="scene_ids", help="Optional scene_id filter.")
    parser.add_argument("--force-inference", action="store_true")
    parser.add_argument("--check-only", action="store_true", help="Print GPU diagnostics and exit without running inference.")
    args = parser.parse_args()

    diag = print_cloud_gpu_diagnostics()
    print("Cloud/Local GPU Diagnostics:", json.dumps(diag, indent=2), flush=True)
    if args.check_only:
        return

    run_genuine_vla_inference_all_scenes(
        manifest_path=DEFAULT_DATA_DIR / "scenes_manifest.json",
        predictions_dir=DEFAULT_PREDICTIONS_DIR,
        model_dir=DEFAULT_AUTOVLA_MODEL_DIR,
        force_recompute=args.force_inference,
        scene_ids=args.scene_ids,
        device=args.device,
    )
    summary = evaluate_all_predictions_and_counterfactuals(artifacts_dir=DEFAULT_ARTIFACTS_DIR)
    report_path = generate_interactive_report()
    print(f"Completed evaluation ({summary['summary_counts']['total_evaluated_predictions']} predictions) -> {report_path}")


if __name__ == "__main__":
    main()
