# SPDX-License-Identifier: AGPL-3.0-only
import time
from pathlib import Path
from .schemas import validate_detections

class Detector:
    def __init__(self, weights, config):
        if not Path(weights).is_file():
            raise FileNotFoundError("Supply verified local weights; automatic download disabled")
        from ultralytics import YOLO
        import torch
        torch.manual_seed(0)
        torch.set_num_threads(config["threads"])
        torch.use_deterministic_algorithms(True)
        self.model = YOLO(str(Path(weights).resolve()), task="detect")
        self.config = config

    def predict(self, image):
        t = time.perf_counter()
        result = self.model.predict(source=str(image), device="cpu", imgsz=self.config["imgsz"], conf=self.config["conf"], iou=self.config["iou"], max_det=self.config["max_det"], rect=self.config["rect"], classes=self.config["classes"], batch=1, half=False, augment=False, agnostic_nms=False, save=False, verbose=False)[0]
        elapsed = (time.perf_counter()-t)*1000
        h,w = result.orig_shape
        ds = [dict(xyxy=[float(v) for v in box], confidence=float(conf), class_id=int(cls), class_name=result.names[int(cls)]) for box,conf,cls in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist(), result.boxes.cls.cpu().tolist())]
        validate_detections(ds,w,h)
        ds.sort(key=lambda d:(d["class_id"],*d["xyxy"],d["confidence"]))
        return ds,elapsed,{k:float(v) for k,v in result.speed.items()}
