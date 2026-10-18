# SPDX-License-Identifier: AGPL-3.0-only
"""Compare complete, intact run content, excluding measured timing fields."""
import json
from pathlib import Path

from .schemas import validate_detections
from .storage import sha256


def compare_runs(first, second):
    first, second = Path(first), Path(second)
    manifests = [json.loads((root / 'run_manifest.json').read_text()) for root in (first, second)]
    a, b = manifests
    for key in ('weight_sha256', 'config_sha256', 'scene_manifest_sha256',
                'image_hash_manifest_sha256', 'software', 'source_hashes',
                'config', 'python', 'platform', 'machine', 'hardware'):
        if a[key] != b[key]:
            raise ValueError('incompatible run identity: ' + key)

    def content(root, manifest):
        if manifest.get('status') != 'COMPLETE':
            raise ValueError('incomplete run cannot establish repeatability')
        for name, digest in manifest['outputs_sha256'].items():
            path = (root / name).resolve()
            if root.resolve() not in path.parents or sha256(path) != digest:
                raise ValueError('output integrity mismatch: ' + name)
        if 'detections.jsonl' not in manifest['outputs_sha256']:
            raise ValueError('missing detection output digest')
        records = [json.loads(line) for line in (root / 'detections.jsonl').read_text().splitlines()]
        expected = manifest['selected_images']
        if type(expected) is not int or expected <= 0 or len(records) != expected:
            raise ValueError('incomplete detection coverage')
        keys = [r['relative_path'] for r in records]
        if len(set(keys)) != len(keys):
            raise ValueError('duplicate result')
        inventory = {r['relative_path']: r for r in json.loads((root / 'inventory.json').read_text())}
        for r in records:
            observed = inventory.get(r['relative_path'])
            if observed is None or observed['status'] != 'VALID':
                raise ValueError('result not associated with validated inventory')
            for key in ('scene_id', 'frame_token', 'sha256', 'camera', 'history_index', 'width', 'height'):
                if r[key] != observed[key]:
                    raise ValueError('result/inventory mismatch: ' + key)
            if r['status'] not in ('SUCCESS', 'SUCCESS_EMPTY'):
                raise ValueError('failed runs cannot establish repeatability')
            validate_detections(r['detections'], r['width'], r['height'])
            if (r['status'] == 'SUCCESS_EMPTY') != (len(r['detections']) == 0):
                raise ValueError('empty detection status mismatch')
        fields = ('scene_id', 'frame_token', 'sha256', 'camera', 'history_index', 'width', 'height', 'status', 'detections')
        return {r['relative_path']: {key: r[key] for key in fields} for r in records}

    left, right = content(first, a), content(second, b)
    if set(left) != set(right):
        raise ValueError('different image coverage')
    differing = [key for key in left if left[key] != right[key]]
    return dict(images_compared=len(left), exact_detection_content_equal=not differing,
                differing_images=differing, timings_excluded=True, output_integrity_checked=True,
                scope='same software, source and CPU configuration; not a cross-device guarantee')
