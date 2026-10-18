# SPDX-License-Identifier: AGPL-3.0-only
from PIL import Image, ImageDraw

def render(path, detections, output):
    with Image.open(path) as src:
        im = src.convert("RGB")
    draw = ImageDraw.Draw(im)
    for d in detections:
        draw.rectangle(d["xyxy"], outline="yellow", width=3)
        draw.text((d["xyxy"][0], d["xyxy"][1]), f"{d['class_name']} {d['confidence']:.2f}", fill="yellow", stroke_width=1, stroke_fill="black")
    draw.text((12,12), "2D detections only - no distance or safety claim", fill="yellow", stroke_width=1, stroke_fill="black")
    im.save(output)


def render_report(rows, summary, associations, output):
    import html
    import json
    from pathlib import Path
    sections = []
    for r in rows:
        filename = r["scene_id"]+"_"+Path(r["relative_path"]).stem+".jpg"
        label = html.escape(f"{r['scene_id']} / {r['camera']} / history index {r['history_index']} / {r['status']}")
        visual = f'<img loading="lazy" width="960" src="overlays/{html.escape(filename)}" alt="{label}">' if r["status"] in ("SUCCESS", "SUCCESS_EMPTY") else html.escape(str(r["error"]))
        sections.append(f'<section><h2>{label}</h2>{visual}</section>')
    text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>YOLO local perception experiment</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;background:#f8fafc;color:#172033}img{max-width:100%;height:auto}pre{white-space:pre-wrap}section{margin:32px 0}</style><h1>YOLO local perception experiment</h1><p>Local restricted imagery. Two-dimensional detections only. Scores are uncalibrated; no accuracy, distance, collision-risk or safety claim. History indices have no verified per-image timestamps. VLA results below are read-only, independent trajectory checks.</p><h2>Measured descriptive results</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre><h2>Existing AutoVLA associations</h2><pre>'+html.escape(json.dumps(associations,indent=2))+'</pre>'+''.join(sections)+'</html>'
    (output/'report.html').write_text(text)
