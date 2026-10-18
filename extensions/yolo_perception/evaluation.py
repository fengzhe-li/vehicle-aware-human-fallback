# SPDX-License-Identifier: AGPL-3.0-only
from collections import Counter
import numpy as np

def summarize(rows):
    ok = [r for r in rows if r["status"] in ("SUCCESS", "SUCCESS_EMPTY")]
    detections = [d for r in ok for d in r["detections"]]
    def distribution(values):
        return {"n": len(values), "min": float(min(values)), "median": float(np.median(values)), "p95": float(np.percentile(values,95)), "max": float(max(values)), "mean": float(np.mean(values))} if values else {"n": 0}
    result = dict(total_images=len(rows), successful_images=len(ok), failures=len(rows)-len(ok), empty_images=sum(r["status"]=="SUCCESS_EMPTY" for r in ok), detections=len(detections), class_counts=dict(Counter(d["class_name"] for d in detections)), confidence=distribution([d["confidence"] for d in detections]), end_to_end_ms=distribution([r["elapsed_ms"] for r in ok]), backend_inference_ms=distribution([r["backend_ms"]["inference"] for r in ok]), accuracy_metrics=None, accuracy_unavailable_reason="No reviewed 2D ground truth; counts and uncalibrated confidence are descriptive only")

    result["per_scene"] = {sid: {"images":sum(r["scene_id"]==sid for r in rows), "detections":sum(len(r["detections"]) for r in ok if r["scene_id"]==sid)} for sid in sorted({r["scene_id"] for r in rows if "scene_id" in r})}
    result["per_camera"] = {cam: {"images":sum(r["camera"]==cam for r in rows), "detections":sum(len(r["detections"]) for r in ok if r["camera"]==cam)} for cam in sorted({r["camera"] for r in rows if "camera" in r})}
    counts, edges = np.histogram([d["confidence"] for d in detections],bins=[0,.25,.5,.75,1.0])
    result["confidence_histogram"] = {"edges":edges.tolist(), "counts":counts.tolist(), "convention":"left-inclusive, right-exclusive except final bin"}
    return result
