# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
from PIL import Image
from .storage import sha256

def inventory(data_root):
    root = Path(data_root).resolve()
    manifest = json.loads((root / "scenes_manifest.json").read_text())
    hashes = json.loads((root / "camera_images_sha256.json").read_text())
    rows = []
    seen = set()
    for scene in manifest["scenes"]:
        sid = scene["scene_id"]
        reference = hashes["scenes"][sid]
        if reference["frame_token"] != scene["frame_token"]:
            raise ValueError("scene token mismatch")
        expected = reference["files"]
        paths = []
        for camera, names in scene["camera_images"].items():
            if camera not in ("front_camera", "front_left_camera", "front_right_camera") or len(names) != 4:
                raise ValueError("invalid camera inventory")
            for index, name in enumerate(names):
                code = {"front_camera":"F0","front_left_camera":"L0","front_right_camera":"R0"}[camera]
                if name != f"scenes/{sid}/images/t{index}_CAM_{code}.jpg":
                    raise ValueError("camera view or history index mismatch")
                paths.append(name)
                f = (root / name).resolve()
                if root not in f.parents or name in seen or not name.startswith(f"scenes/{sid}/images/"):
                    raise ValueError("invalid or duplicate image path")
                seen.add(name)
                row = dict(scene_id=sid, frame_token=scene["frame_token"], scene_timestamp_us=scene["timestamp_us"], capture_timestamp_us=None, camera=camera, history_index=index, relative_path=name, sha256=None, width=None, height=None, status="VALID", error=None)
                try:
                    if not f.is_file():
                        raise FileNotFoundError(name)
                    digest = sha256(f)
                    row["sha256"] = digest
                    if digest != expected[name]["sha256"] or f.stat().st_size != expected[name]["size_bytes"]:
                        raise ValueError("SHA256_OR_SIZE_MISMATCH")
                    with Image.open(f) as im:
                        im.load()
                        if im.format != "JPEG":
                            raise ValueError("not JPEG")
                        row.update(width=im.width, height=im.height)
                except Exception as exc:
                    row.update(status="INVALID_INPUT", error=f"{type(exc).__name__}: {exc}")
                rows.append(row)
        if len(paths) != 12 or set(paths) != set(expected):
            raise ValueError("camera manifest coverage mismatch")
    if len(rows) != hashes["total_camera_jpeg_files"]:
        raise ValueError("total inventory mismatch")
    return rows
