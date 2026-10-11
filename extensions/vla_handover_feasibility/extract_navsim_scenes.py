"""Reproducible OpenScene / nuPlan Camera Observation Extractor.

Streams the exact 84 multi-view camera history JPEGs (`CAM_F0`, `CAM_L0`, `CAM_R0`
across 4 frames at 2 Hz for each of the 7 scenes in `data/scenes_manifest.json`)
from the official `OpenDriveLab/OpenScene` mini sensor archive and verifies each
file's byte size and SHA-256 digest against `data/camera_images_sha256.json`.

Note on Licensing:
Raw nuPlan / OpenScene camera JPEGs are subject to the Motional nuPlan / OpenScene
CC BY-NC-SA 4.0 terms and are therefore excluded from public Git redistribution via
`.gitignore`. Offline evaluation (`experiment_runner --skip-inference`,
`provenance_audit`, `report_generator`, and `pytest`) runs directly from the
committed numeric manifests, cryptographic SHA-256 digests, and cached AutoVLA
prediction artifacts without requiring this download. Run this script only if you
wish to populate the raw camera JPEGs locally for live AutoVLA model inference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import time
import urllib.request


EXT_ROOT = Path(__file__).resolve().parent
DATA_DIR = EXT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "scenes_manifest.json"
CAMERA_SHA256_PATH = DATA_DIR / "camera_images_sha256.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_and_verify_camera_jpegs(
    manifest_path: str | Path = MANIFEST_PATH,
    camera_sha256_path: str | Path = CAMERA_SHA256_PATH,
    data_dir: str | Path = DATA_DIR,
) -> dict[str, int]:
    """Stream the 84 required camera JPEGs from OpenDriveLab/OpenScene and verify SHA-256 digests."""
    d_root = Path(data_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    sha_manifest = json.loads(Path(camera_sha256_path).read_text(encoding="utf-8"))

    cam_tgz_url = manifest["source_blobs_url"]
    logs_zip_url = manifest["source_logs_url"]

    # Map local relative path -> expected {sha256, size_bytes}
    expected_files: dict[str, dict[str, int | str]] = {}
    for sid, s_hash_info in sha_manifest["scenes"].items():
        for rel_p, finfo in s_hash_info["files"].items():
            expected_files[rel_p] = finfo

    # Check if all 84 files are already present and verified locally
    already_verified = 0
    for rel_p, finfo in expected_files.items():
        full_p = d_root / rel_p
        if full_p.exists() and full_p.stat().st_size == int(finfo["size_bytes"]):
            if sha256_bytes(full_p.read_bytes()) == str(finfo["sha256"]):
                already_verified += 1

    if already_verified == len(expected_files):
        print(f"All {already_verified} camera JPEGs already exist locally and match SHA-256 digests.")
        return {"total_expected": len(expected_files), "extracted": 0, "verified": already_verified}

    print(f"Streaming camera archive from {cam_tgz_url} (logs reference: {logs_zip_url})...")
    # We map each scene's camera frame back to its tar member via the log pickle if needed,
    # or match by SHA-256 digest directly from the OpenScene sensor tar stream!
    sha_to_dests: dict[str, list[Path]] = {}
    for rel_p, finfo in expected_files.items():
        full_p = d_root / rel_p
        full_p.parent.mkdir(parents=True, exist_ok=True)
        sha_to_dests.setdefault(str(finfo["sha256"]), []).append(full_p)

    remaining_shas = set(sha_to_dests.keys())
    t0 = time.time()
    req = urllib.request.Request(cam_tgz_url, headers={"User-Agent": "Mozilla/5.0"})
    extracted_count = 0
    with urllib.request.urlopen(req, timeout=180) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile() or not member.name.endswith(".jpg"):
                    continue
                fobj = tf.extractfile(member)
                if fobj is None:
                    continue
                img_bytes = fobj.read()
                digest = sha256_bytes(img_bytes)
                if digest in remaining_shas:
                    for dest in sha_to_dests[digest]:
                        dest.write_bytes(img_bytes)
                        extracted_count += 1
                    remaining_shas.remove(digest)
                    if not remaining_shas:
                        break

    if remaining_shas:
        raise RuntimeError(f"Could not locate {len(remaining_shas)} expected camera JPEGs in archive.")

    print(f"Extracted and SHA-256 verified {extracted_count} camera JPEGs in {time.time() - t0:.1f}s.")
    return {
        "total_expected": len(expected_files),
        "extracted": extracted_count,
        "verified": len(expected_files),
    }


if __name__ == "__main__":
    download_and_verify_camera_jpegs()
