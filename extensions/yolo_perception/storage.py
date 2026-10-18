# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import json
import os
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def reserve_output(path, protected_root):
    path = Path(path).resolve()
    protected_root = Path(protected_root).resolve()
    if path == protected_root or protected_root in path.parents:
        raise ValueError("output cannot be inside protected VLA input directory")
    path.mkdir(parents=True, exist_ok=False)
    return path
