"""Documentation-only renderer: actual adapter snapshots and existing lateral artifacts.

Run against a verified engineering checkout; this main-based media branch does
not include the implementation while PRs #1/#2 are pending.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

W, H = 1200, 680
BG, INK, MUTED, BLUE = '#f2f5fa', '#14263e', '#51657c', '#225ccd'
COLORS = {'available':'#08766b', 'stale':'#a45c08', 'invalid':'#bb3f50', 'missing':'#65758a'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshots(engineering_root):
    sys.path.insert(0, str(engineering_root.resolve()))
    from automotive_can import Dbc, Frame, Replay
    dbc_path = engineering_root/'automotive_can/examples/synthetic_vehicle.dbc'
    dbc = Dbc.parse(dbc_path.read_text())
    replay = Replay(dbc, stale_after_ns=100_000_000)
    good = bytes([0xD0, 0x07, 100, 80, 100, 50, 0, 0])
    bad = bytes([0xFF, 0xFF, 100, 80, 100, 50, 0, 0])
    # Exact example payload; invalid-speed transform follows the existing CAN test.
    events = [(900_000_000, None, 'Waiting for the first frame', 1800),
              (1_000_000_000, good, 'Decode the synthetic fixture', 3000)]
    events += [(1_000_000_000+age*1_000_000, None, 'Same values; freshness changes', 800)
               for age in (25, 50, 75)]
    events += [(1_100_000_000, None, 'At the freshness boundary', 2200),
               (1_125_000_000, None, 'Expired values are unavailable', 3000),
               (1_200_000_000, bad, 'Reject out-of-range speed', 3000),
               (1_300_000_000, good, 'A fresh valid frame restores availability', 2600)]
    rows=[]
    for index,(now,payload,title,duration) in enumerate(events):
        if payload is not None:
            replay.feed(Frame(256,payload,now))
        state = replay.snapshot(now)
        values=[]
        for spec in dbc.by_id[256]:
            signal=state.signals.get(spec.name)
            if signal is None:
                status='missing';value=None;reason='no measurement'
            else:
                try:
                    value=state.value(spec.name,max_age_ns=100_000_000,now_ns=now)
                    status='available';reason='within range and age limit'
                except ValueError as e:
                    value=None;status='invalid' if not signal.valid else 'stale';reason=str(e)
            values.append(dict(name=spec.name,unit=spec.unit or 'coefficient',
                decoded=None if signal is None else asdict(signal),available_value=value,
                status=status,reason=reason))
        rows.append(dict(index=index,title=title,now_ns=now,duration_ms=duration,
            incoming_payload_hex=None if payload is None else payload.hex(' ').upper(),
            can_id=256 if payload is not None else None,state_timestamp_ns=state.timestamp_ns,
            age_ns=None if not state.signals else now-state.timestamp_ns,
            state_valid=state.valid,signals=values,faults=state.faults))
    return rows


def render_frame(row,fonts):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    def txt(x,y,s,size=20,color=INK,bold=False):
        d.text((x,y),s,font=ImageFont.truetype(str(fonts/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size),fill=color)
    def box(x,y,w,h):d.rounded_rectangle((x,y,x+w,y+h),radius=15,fill='white',outline='#dce4ef',width=2)
    txt(35,23,'CAN / DBC     ·     SYNTHETIC SOFTWARE REPLAY',17,BLUE,True)
    txt(35,57,row['title'],30,bold=True)
    txt(35,103,'Actual decoder + VehicleState snapshots  |  No ECU or physical vehicle connected',17,MUTED)
    box(30,145,420,190);box(470,145,700,190)
    txt(50,164,'01  INPUT FRAME',16,BLUE,True)
    txt(50,197,'CAN ID 0x100  ·  Classical CAN',20,bold=True)
    txt(50,233,row['incoming_payload_hex'] or 'No incoming frame at this step',18)
    txt(50,271,f"Replay clock: {row['now_ns']/1e9:.3f} s",18,MUTED)
    txt(50,299,'Fixture payload is not recorded telemetry.',15,MUTED)
    txt(490,164,'02  DECODE AND FRESHNESS',16,BLUE,True)
    speed=row['signals'][0]
    if row['incoming_payload_hex']:
        raw=speed['decoded']['raw']
        txt(490,199,f"Speed: raw {raw} × 0.01 + 0 = {raw*.01:.2f} m/s",23,bold=True)
    else:
        txt(490,199,'Retained decoded state; no new measurement',21,bold=True)
    txt(490,238,'Speed range: 0–100 m/s   |   Maximum age: 100 ms',18,MUTED)
    age=row['age_ns']
    txt(490,276,'Signal age: — (missing)' if age is None else f"Signal age: {age/1e6:.0f} ms   |   Timestamp: {row['state_timestamp_ns']/1e9:.3f} s",20)
    box(30,355,1140,235)
    txt(50,372,'03  VEHICLESTATE READOUT',16,BLUE,True)
    txt(500,372,'Decoded value (retained)',16,MUTED)
    txt(785,372,'Available to consumer',16,MUTED)
    for i,s in enumerate(row['signals']):
        y=406+i*33
        txt(50,y,s['name'],19,bold=True)
        text='—' if s['decoded'] is None else f"{s['decoded']['physical']:.2f} {s['unit']}"
        txt(500,y,text,18)
        label=f"{s['available_value']:.2f} {s['unit']}" if s['status']=='available' else 'UNAVAILABLE · '+s['status'].upper()
        txt(785,y,label,18,COLORS[s['status']],True)
    txt(35,613,f"STEP {row['index']+1:02d} / 09",16,BLUE,True)
    txt(215,610,'Synthetic time is slowed for reading. Availability is not a safety verdict.',18,MUTED)
    d.rounded_rectangle((35,648,1165,654),radius=3,fill='#dce4ef')
    d.rounded_rectangle((35,648,35+1130*(row['index']+1)/9,654),radius=3,fill=BLUE)
    return im


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engineering-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('docs/media/engineering'))
    parser.add_argument('--ffmpeg',type=Path)
    args=parser.parse_args();root=args.engineering_root.resolve();out=args.output
    required=['automotive_can/dbc.py','automotive_can/examples/synthetic_vehicle.dbc','tests/test_automotive_can.py',
              'automotive_can/examples/replay_synthetic.py','lateral_recoverability/artifacts/summary.json']
    required += [f'lateral_recoverability/artifacts/{n}.png' for n in ('feasibility_map','sensitivity','path_geometry')]
    if any(not (root/f).is_file() for f in required):raise ValueError('Need the verified CAN + lateral checkout')
    out.mkdir(parents=True,exist_ok=True)
    import matplotlib
    fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
    rows=snapshots(root)
    (out/'can_trace.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    frames=[render_frame(r,fonts) for r in rows]
    frames[1].save(out/'can_decode_poster.png')
    frames[0].save(out/'can_decode.gif',save_all=True,append_images=frames[1:],
                   duration=[r['duration_ms'] for r in rows],loop=0,optimize=False,disposal=2)
    # MP4 repeats exact computed frames at 10 fps: no interpolated state values.
    if args.ffmpeg:
        proc=subprocess.Popen([str(args.ffmpeg),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
            '-s',f'{W}x{H}','-r','10','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(out/'can_decode.mp4')],stdin=subprocess.PIPE)
        for r,frame in zip(rows,frames):
            for _ in range(r['duration_ms']//100):proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait():raise RuntimeError('FFmpeg failed')
    # Byte copies, not new scientific renders: retain the actual existing plots.
    for name in ('feasibility_map','sensitivity','path_geometry'):
        shutil.copyfile(root/f'lateral_recoverability/artifacts/{name}.png',out/f'{name}.png')
    summary=json.loads((root/'lateral_recoverability/artifacts/summary.json').read_text())
    manifest=dict(synthetic_only=True,hardware_tested=False,collision_avoidance='not_validated',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        source_sha256={f:digest(root/f) for f in required},
        renderer_sha256=digest(__file__),font_sha256={n:digest(fonts/n) for n in ('DejaVuSans.ttf','DejaVuSans-Bold.ttf')},
        python=platform.python_version(),pillow=pillow_version,matplotlib=matplotlib.__version__,
        ffmpeg_version=None if not args.ffmpeg else subprocess.check_output([str(args.ffmpeg),'-version'],text=True).splitlines()[0],
        can=dict(states=len(rows),width=W,height=H,duration_ms=sum(r['duration_ms'] for r in rows),
                 freshness_limit_ns=100_000_000,animation='Held computed snapshots; wall time differs from synthetic timestamps'),
        lateral_counts=summary['lateral_counts'],
        lateral_animation='Not generated: static feasibility/sensitivity/path figures explain independent cases without suggesting a vehicle executes the paths.',
        output_sha256={name:digest(out/name) for name in sorted(
            ['can_decode.gif','can_decode_poster.png','can_trace.json','feasibility_map.png',
             'sensitivity.png','path_geometry.png'] + (['can_decode.mp4'] if args.ffmpeg else []))})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(manifest['can'],indent=2))

if __name__=='__main__':main()
