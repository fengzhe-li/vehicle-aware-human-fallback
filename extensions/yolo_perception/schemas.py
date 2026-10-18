# SPDX-License-Identifier: AGPL-3.0-only
import math

def validate_detections(detections, width, height):
    if not isinstance(detections, list):
        raise ValueError("detections must be a list")
    for d in detections:
        box = d["xyxy"]
        if len(box) != 4 or not all(math.isfinite(float(x)) for x in box):
            raise ValueError("non-finite or malformed box")
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("box outside original image or inverted")
        if not math.isfinite(d["confidence"]) or not 0 <= d["confidence"] <= 1:
            raise ValueError("invalid confidence")
        if type(d["class_id"]) is not int or d["class_id"] < 0 or not isinstance(d["class_name"], str) or not d["class_name"]:
            raise ValueError("invalid class")
    return detections
