# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
from .storage import sha256

def read_associations(data_root):
    root = Path(data_root)
    scenes = json.loads((root / "scenes_manifest.json").read_text())["scenes"]
    summary_path = root.parent / "artifacts/evaluation_summary.json"
    summary = json.loads(summary_path.read_text())
    if summary["manifest_sha256"] != sha256(root / "scenes_manifest.json"):
        raise ValueError("VLA summary manifest mismatch")
    records = {x["scene_id"]: x for x in summary["records"]}
    if len(records) != len(scenes) or len(records) != len(summary["records"]):
        raise ValueError("VLA summary coverage mismatch")
    out = []
    for s in scenes:
        f = root.parent / "artifacts/predictions" / (s["scene_id"] + "_fast.json")
        a = json.loads(f.read_text())
        rec = records[s["scene_id"]]
        for field in ("scene_id", "frame_token", "timestamp_us", "log_file"):
            if a[field] != s[field] or rec["prediction_artifact"][field] != s[field]:
                raise ValueError("incorrect scene association: " + field)
        if a != rec["prediction_artifact"]:
            raise ValueError("saved prediction differs from evaluation summary")
        out.append(dict(scene_id=s["scene_id"], frame_token=s["frame_token"], prediction_sha256=sha256(f), summary_sha256=sha256(summary_path), nominal=rec["feasibility_nominal"]["classification"], wet=rec["feasibility_wet_mu0_5"]["classification"], interpretation="Independent saved trajectory checks; no causal or safety inference from detections"))
    return out
