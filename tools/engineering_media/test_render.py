"""Verify presentation values without changing the engineering implementation."""
import importlib.util
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

from PIL import Image
import pytest

ROOT=Path(__file__).resolve().parents[2]
MEDIA=ROOT/'docs/media/engineering'
spec=importlib.util.spec_from_file_location('engineering_media_renderer',Path(__file__).with_name('render.py'))
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

@pytest.fixture(scope='module')
def rows():
    engineering=Path(os.environ.get('VEHICLE_ENGINEERING_ROOT',ROOT)).resolve()
    if not (engineering/'automotive_can/dbc.py').exists():
        pytest.fail('Set VEHICLE_ENGINEERING_ROOT to the verified CAN/lateral checkout; no synthetic substitute is used')
    result=renderer.snapshots(engineering)
    assert result==json.loads((MEDIA/'can_trace.json').read_text())
    return result


def test_fresh_fixture_decoding_and_timestamp(rows):
    assert [s['available_value'] for s in rows[1]['signals']]==[20,1,8,.1,.5]
    assert rows[1]['state_timestamp_ns']==1_000_000_000
    assert rows[1]['incoming_payload_hex']=='D0 07 64 50 64 32 00 00'
    assert rows[1]['signals'][0]['decoded']['raw']==2000


def test_missing_boundary_stale_invalid_and_recovery(rows):
    assert all(s['status']=='missing' and s['available_value'] is None for s in rows[0]['signals'])
    assert rows[5]['age_ns']==100_000_000
    assert all(s['status']=='available' for s in rows[5]['signals'])
    assert rows[6]['age_ns']==125_000_000
    assert all(s['status']=='stale' and s['available_value'] is None for s in rows[6]['signals'])
    assert rows[6]['signals'][0]['decoded']['physical']==20  # retained, not available
    assert rows[7]['signals'][0]['decoded']['physical']==655.35
    assert rows[7]['signals'][0]['status']=='invalid'
    assert rows[7]['signals'][0]['available_value'] is None
    assert all(s['status']=='available' for s in rows[7]['signals'][1:])
    assert rows[8]['signals'][0]['available_value']==20
    assert [r['state_valid'] for r in rows]==[False,True,True,True,True,True,False,False,True]


def test_animation_frames_match_computed_snapshots(rows):
    im=Image.open(MEDIA/'can_decode.gif')
    assert im.size==(1200,680) and im.n_frames==len(rows)==9
    durations=[]
    for i,r in enumerate(rows):
        im.seek(i);durations.append(im.info['duration'])
        assert im.info['duration']==r['duration_ms']
    assert sum(durations)==18000
    assert im.info['loop']==0


def test_artifact_hashes_and_lateral_source_identity():
    manifest=json.loads((MEDIA/'manifest.json').read_text())
    assert manifest['synthetic_only'] is True and manifest['hardware_tested'] is False
    assert manifest['collision_avoidance']=='not_validated'
    assert manifest['lateral_counts']=={'feasible':258,'infeasible':1124,'unknown':7366}
    assert renderer.digest(Path(__file__).with_name('render.py'))==manifest['renderer_sha256']
    for name,expected in manifest['output_sha256'].items():
        assert renderer.digest(MEDIA/name)==expected
    for name in ('feasibility_map','sensitivity','path_geometry'):
        assert renderer.digest(MEDIA/f'{name}.png')==manifest['source_sha256'][f'lateral_recoverability/artifacts/{name}.png']


@pytest.mark.parametrize('filename',['README.md','automotive_can/README.md','lateral_recoverability/README.md','docs/ENGINEERING_MEDIA.md'])
def test_all_local_readme_links_resolve(filename):
    p=ROOT/filename
    for match in re.finditer(r'\]\(([^)]+)\)',p.read_text()):
        link=match[1]
        if link.startswith(('http:', 'https:', '#','mailto:')):continue
        target=unquote(link.split('#')[0])
        assert (p.parent/target).exists(),(filename,target)


def test_root_readme_preserves_existing_hero_and_places_new_media_after_intro():
    text=(ROOT/'README.md').read_text()
    assert 'extensions/vla_handover_feasibility/artifacts/report/demo_preview.gif' in text
    assert 'extensions/vla_handover_feasibility/artifacts/report/demo_walkthrough.mp4' in text
    assert text.index('## Executive Overview') < text.index('docs/media/engineering/can_decode.gif')
    assert 'not yet released on main' in text
    assert 'collision avoidance remains unvalidated' in text
