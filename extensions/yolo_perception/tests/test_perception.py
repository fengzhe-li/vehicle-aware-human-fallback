# SPDX-License-Identifier: AGPL-3.0-only
import copy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest
from PIL import Image
from extensions.yolo_perception.inventory import inventory
from extensions.yolo_perception.storage import sha256, reserve_output, write_json
from extensions.yolo_perception.schemas import validate_detections
from extensions.yolo_perception.evaluation import summarize
from extensions.yolo_perception.vla_readonly import read_associations
from extensions.yolo_perception.cli import ROOT, check_frozen, run

@pytest.fixture
def data(tmp_path):
    root=tmp_path/'vla'/'data';root.mkdir(parents=True)
    paths={};files={}
    for camera,code in [('front_camera','F0'),('front_left_camera','L0'),('front_right_camera','R0')]:
        paths[camera]=[]
        for i in range(4):
            rel=f'scenes/test/images/t{i}_CAM_{code}.jpg'; f=root/rel;f.parent.mkdir(parents=True,exist_ok=True)
            Image.new('RGB',(32,24),(i*30,0,0)).save(f)
            paths[camera].append(rel);files[rel]={'sha256':sha256(f),'size_bytes':f.stat().st_size}
    s={'scene_id':'test','frame_token':'abc','timestamp_us':123,'camera_images':paths}
    write_json(root/'scenes_manifest.json',{'scenes':[s]})
    write_json(root/'camera_images_sha256.json',{'total_camera_jpeg_files':12,'scenes':{'test':{'frame_token':'abc','files':files}}})
    return root

def test_inventory_valid(data):
    rows=inventory(data);assert len(rows)==12
    assert all(r['status']=='VALID' and r['width']==32 and r['capture_timestamp_us'] is None for r in rows)

@pytest.mark.parametrize('kind',['missing','hash','corrupt'])
def test_bad_inputs(data,kind):
    f=next(data.glob('scenes/*/images/*.jpg'))
    if kind=='missing':f.unlink()
    else:
        f.write_bytes(b'not an image')
        if kind=='corrupt':
            p=data/'camera_images_sha256.json';j=json.loads(p.read_text());j['scenes']['test']['files'][str(f.relative_to(data))]={'sha256':sha256(f),'size_bytes':f.stat().st_size};p.write_text(json.dumps(j))
    rows=inventory(data);bad=[r for r in rows if r['status']!='VALID'];assert len(bad)==1 and bad[0]['error']

@pytest.mark.parametrize('kind',['token','traversal','duplicate','coverage','camera'])
def test_bad_inventory_structure(data,kind):
    p=data/'scenes_manifest.json';j=json.loads(p.read_text());s=j['scenes'][0]
    if kind=='token':s['frame_token']='wrong'
    if kind=='traversal':s['camera_images']['front_camera'][0]='../outside.jpg'
    if kind=='duplicate':s['camera_images']['front_camera'][1]=s['camera_images']['front_camera'][0]
    if kind=='coverage':s['camera_images'].pop('front_camera')
    if kind=='camera':s['camera_images']['front_camera'],s['camera_images']['front_left_camera']=s['camera_images']['front_left_camera'],s['camera_images']['front_camera']
    p.write_text(json.dumps(j))
    with pytest.raises(ValueError):inventory(data)

@pytest.mark.parametrize('box,confidence', [([1,1,0,2],.5),([-1,0,3,3],.5),([0,0,33,3],.5),([0,0,float('nan'),3],.5),([0,0,3],.5),([0,0,3,3],float('nan')),([0,0,3,3],1.1)])
def test_malformed_detections(box,confidence):
    with pytest.raises(ValueError):validate_detections([{'xyxy':box,'confidence':confidence,'class_id':0,'class_name':'person'}],32,24)

def test_empty_and_valid_detection():
    assert validate_detections([],32,24)==[]
    assert validate_detections([{'xyxy':[0,0,32,24],'confidence':.5,'class_id':0,'class_name':'person'}],32,24)

def test_output_conflict_and_protected_path(tmp_path):
    out=reserve_output(tmp_path/'run',tmp_path/'protected')
    with pytest.raises(FileExistsError):reserve_output(out,tmp_path/'protected')
    with pytest.raises(ValueError):reserve_output(tmp_path/'protected'/'run',tmp_path/'protected')
    write_json(out/'record.json',{'x':1});assert json.loads((out/'record.json').read_text())=={'x':1}

def test_summary_does_not_invent_accuracy():
    s=summarize([{'status':'SUCCESS_EMPTY','detections':[],'elapsed_ms':10,'backend_ms':{'inference':5}},{'status':'PROCESSING_ERROR'}])
    assert s['failures']==1 and s['empty_images']==1 and s['accuracy_metrics'] is None

@pytest.fixture
def vla_copy(tmp_path):
    src=ROOT/'extensions/vla_handover_feasibility';dst=tmp_path/'vla'
    (dst/'data').mkdir(parents=True);(dst/'artifacts').mkdir()
    shutil.copy(src/'data/scenes_manifest.json',dst/'data')
    shutil.copy(src/'artifacts/evaluation_summary.json',dst/'artifacts')
    shutil.copytree(src/'artifacts/predictions',dst/'artifacts/predictions')
    return dst

def test_real_saved_associations_readonly(vla_copy):
    before={str(p):sha256(p) for p in vla_copy.rglob('*') if p.is_file()}
    assert len(read_associations(vla_copy/'data'))==7
    assert before=={str(p):sha256(p) for p in vla_copy.rglob('*') if p.is_file()}

@pytest.mark.parametrize('target',['prediction','summary','manifest'])
def test_incorrect_associations(vla_copy,target):
    if target=='prediction':p=next((vla_copy/'artifacts/predictions').glob('*.json'));j=json.loads(p.read_text());j['frame_token']='wrong'
    elif target=='summary':p=vla_copy/'artifacts/evaluation_summary.json';j=json.loads(p.read_text());j['records'][0]['prediction_artifact']['frame_token']='wrong'
    else:p=vla_copy/'data/scenes_manifest.json';j=json.loads(p.read_text());j['scenes'][0]['timestamp_us']=0
    p.write_text(json.dumps(j))
    with pytest.raises(ValueError):read_associations(vla_copy/'data')

def test_frozen_inputs():assert check_frozen()['changed']==[]

@pytest.mark.parametrize("failure",[False,True])
def test_pipeline_contract(data,tmp_path,monkeypatch,failure):
    import extensions.yolo_perception.cli as cli
    import extensions.yolo_perception.inference as inference
    monkeypatch.setattr(cli,'read_associations',lambda p:[])
    import sys
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda:False)),cuda=SimpleNamespace(is_available=lambda:False),get_num_threads=lambda:1))
    class Fake:
        def __init__(self,*a):self.calls=0
        def predict(self,p):
            self.calls+=1
            if failure and self.calls==3:raise RuntimeError("injected inference failure")
            return [],1.,{'preprocess':.2,'inference':.5,'postprocess':.3}
    monkeypatch.setattr(inference,'Detector',Fake)
    weights=tmp_path/'weights.pt';weights.write_bytes(b'TEST FIXTURE ONLY')
    out=tmp_path/'separate'/'run'
    args=SimpleNamespace(output=out,data_root=data,weights=weights,weights_sha256=sha256(weights),smoke=True)
    if failure:
        with pytest.raises(RuntimeError,match="processing failures"):run(args)
    else:run(args)
    s=json.loads((out/'summary.json').read_text());assert s['successful_images']==3-int(failure) and s['empty_images']==3-int(failure)
    assert s['failures']==int(failure)
    assert len(list((out/'overlays').glob('*.jpg')))==3-int(failure)
    assert len(list((out/'frames').glob('*.json')))==3

@pytest.mark.parametrize('mode',['identity','detection','coverage','failure','equal','truncated','empty','started','tampered','inventory','status','hardware'])
def test_repeatability_contract(tmp_path,mode):
    from extensions.yolo_perception.reproducibility import compare_runs
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    identity={k:'same' for k in ('weight_sha256','config_sha256','scene_manifest_sha256','image_hash_manifest_sha256','software','source_hashes','config','python','platform','machine','hardware')}
    identity.update(status='COMPLETE',selected_images=1)
    row=dict(relative_path='x',scene_id='s',frame_token='t',sha256='hash',camera='front_camera',history_index=0,width=32,height=24,status='SUCCESS_EMPTY',detections=[],elapsed_ms=1)
    for root in (a,b):
        write_json(root/'inventory.json',[dict(row,status='VALID')])
        other=dict(row,elapsed_ms=1 if root==a else 999)
        m=dict(identity)
        if root==b:
            if mode=='identity':m['weight_sha256']='different'
            if mode=='hardware':m['hardware']='different'
            if mode=='started':m['status']='STARTED'
            if mode=='detection':other.update(status='SUCCESS',detections=[dict(xyxy=[0,0,3,3],confidence=.5,class_id=0,class_name='person')])
            if mode=='coverage':other['relative_path']='y'
            if mode=='failure':other['status']='PROCESSING_ERROR'
            if mode=='inventory':other['sha256']='wrong'
            if mode=='status':other['status']='SUCCESS'
        # Both runs truncated identically must not pass merely because they agree.
        if mode=='truncated':m['selected_images']=2
        (root/'detections.jsonl').write_text('' if mode=='empty' else json.dumps(other)+'\n')
        m['outputs_sha256']={'detections.jsonl':sha256(root/'detections.jsonl')}
        write_json(root/'run_manifest.json',m)
    if mode=='tampered':
        with (b/'detections.jsonl').open('a') as f:f.write('\n')
    if mode not in ('detection','equal'):
        with pytest.raises(ValueError):compare_runs(a,b)
    else:assert compare_runs(a,b)['exact_detection_content_equal']==(mode=='equal')

def test_missing_weights_never_downloads(tmp_path):
    from extensions.yolo_perception.inference import Detector
    with pytest.raises(FileNotFoundError):Detector(tmp_path/'absent.pt',{})
