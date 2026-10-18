# SPDX-License-Identifier: AGPL-3.0-only
import argparse
import importlib.metadata
import json
import platform
import os
import resource
import subprocess
from pathlib import Path
from .inventory import inventory
from .storage import reserve_output, sha256, write_json
from .vla_readonly import read_associations
from .evaluation import summarize

ROOT = Path(__file__).resolve().parents[2]

def check_frozen():
    hashes = json.loads((Path(__file__).parent / "frozen_inputs.json").read_text())
    changed = [name for name,digest in hashes.items() if not (ROOT/name).is_file() or sha256(ROOT/name)!=digest]
    if changed:
        raise ValueError("Frozen files changed: " + str(changed))
    return {"verified_files":len(hashes),"changed":[]}

def run(args):
    before = check_frozen()
    out = reserve_output(args.output,args.data_root.parent)
    args._owned_output = True
    rows = inventory(args.data_root)
    write_json(out/"inventory.json",rows)
    if any(r["status"]!="VALID" for r in rows):
        write_json(out/"failure.json",{"reason":"input validation failed"})
        raise ValueError("input validation failed; see inventory.json")
    associations = read_associations(args.data_root)
    write_json(out/"vla_associations.json",associations)
    cfg = json.loads((Path(__file__).parent/"configs/baseline.json").read_text())
    if sha256(args.weights)!=args.weights_sha256:
        raise ValueError("weight hash mismatch")
    selected = rows if not args.smoke else [next(r for r in rows if r["camera"]==camera) for camera in ("front_camera","front_left_camera","front_right_camera")]
    versions = {d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}
    manifest = dict(schema_version=1,status="STARTED",model="YOLO11n COCO detection",weight_sha256=sha256(args.weights),weight_source="https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",config=cfg,config_sha256=sha256(Path(__file__).parent/"configs/baseline.json"),scene_manifest_sha256=sha256(args.data_root/"scenes_manifest.json"),image_hash_manifest_sha256=sha256(args.data_root/"camera_images_sha256.json"),python=platform.python_version(),platform=platform.platform(),machine=platform.machine(),software=versions,code_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),source_hashes={str(p.relative_to(ROOT)):sha256(p) for p in Path(__file__).parent.rglob("*.py")},frozen_before=before,selected_images=len(selected),warmup_images=1,measurement="wall time around predict includes decode/preprocess/inference/postprocess, excludes rendering; backend timings separately; warmup excluded",license="Ultralytics AGPL-3.0/commercial; images CC BY-NC-SA-4.0; not covered by root MIT")
    write_json(out/"run_manifest.json",manifest)
    from .inference import Detector
    from .visualization import render
    detector = Detector(args.weights,cfg)
    import torch
    cpu = platform.processor() or platform.machine()
    hardware_note = None
    if platform.system() == "Darwin":
        try:
            cpu = subprocess.check_output(["sysctl","-n","machdep.cpu.brand_string"],text=True,stderr=subprocess.PIPE).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            hardware_note = "CPU brand query unavailable in execution sandbox; architecture recorded"
    manifest["hardware"] = dict(cpu=cpu, logical_cpus=os.cpu_count(), brand_query_note=hardware_note, mps_available=torch.backends.mps.is_available(), cuda_available=torch.cuda.is_available(), threads=torch.get_num_threads())
    write_json(out/"run_manifest.json",manifest)
    detector.predict(args.data_root/selected[0]["relative_path"])
    results=[]
    (out/"overlays").mkdir()
    (out/"frames").mkdir()
    for row in selected:
        record=dict(row, detections=[], elapsed_ms=None, backend_ms=None)
        try:
            image=args.data_root/row["relative_path"]
            if sha256(image)!=row["sha256"]:
                raise ValueError("image changed after inventory")
            ds,ms,backend=detector.predict(image)
            record.update(detections=ds,elapsed_ms=ms,backend_ms=backend,status="SUCCESS" if ds else "SUCCESS_EMPTY")
            render(image,ds,out/"overlays"/(row["scene_id"]+"_"+Path(row["relative_path"]).stem+".jpg"))
        except Exception as exc:
            record.update(status="PROCESSING_ERROR",error=f"{type(exc).__name__}: {exc}")
        results.append(record)
        write_json(out/"frames"/(row["scene_id"]+"_"+Path(row["relative_path"]).stem+".json"),record)
        write_json(out/"progress.json",{"processed":len(results),"total":len(selected)})
    with (out/"detections.jsonl").open("x") as f:
        for row in results:f.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
    manifest["peak_process_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system()=="Darwin" else 1024)
    summary=summarize(results)
    write_json(out/"summary.json",summary)
    from .visualization import render_report
    render_report(results, summary, associations, out)
    manifest.update(status="COMPLETE" if not summary["failures"] else "COMPLETE_WITH_FAILURES",frozen_after=check_frozen(),outputs_sha256={name:sha256(out/name) for name in ("detections.jsonl","summary.json","vla_associations.json")})
    write_json(out/"run_manifest.json",manifest)
    print(json.dumps(summary,indent=2))
    if summary["failures"]:raise RuntimeError("processing failures recorded")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["run","check-frozen","compare"])
    p.add_argument("--data-root",type=Path,default=ROOT/"extensions/vla_handover_feasibility/data")
    p.add_argument("--weights",type=Path)
    p.add_argument("--weights-sha256")
    p.add_argument("--output",type=Path)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--first",type=Path)
    p.add_argument("--second",type=Path)
    a=p.parse_args()
    if a.command=="check-frozen":print(json.dumps(check_frozen()))
    elif a.command=="compare":
        if not a.first or not a.second:p.error("compare requires --first and --second")
        from .reproducibility import compare_runs
        result=compare_runs(a.first,a.second)
        print(json.dumps(result,indent=2))
        if not result["exact_detection_content_equal"]:raise SystemExit(1)
    else:
        if not all((a.weights,a.weights_sha256,a.output)):p.error("run requires weights, weights-sha256, output")
        try:
            run(a)
        except Exception as exc:
            # Never touch an existing run after an output reservation conflict.
            if getattr(a, "_owned_output", False):
                write_json(a.output/"failure.json", {"error":f"{type(exc).__name__}: {exc}"})
            if getattr(a, "_owned_output", False) and a.output and (a.output/"run_manifest.json").is_file():
                m=json.loads((a.output/"run_manifest.json").read_text())
                if m["status"]=="STARTED":
                    m.update(status="FAILED",error=f"{type(exc).__name__}: {exc}")
                    write_json(a.output/"run_manifest.json",m)
            raise
if __name__=="__main__":main()
