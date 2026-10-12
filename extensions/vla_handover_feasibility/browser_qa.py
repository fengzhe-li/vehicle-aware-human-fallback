"""Automated Browser Interaction Smoke Test, R3B Python/Browser Parity QA, Responsive Layout Check,
Video Walkthrough Recording, Screenshot Capture, and PDF Export QA.

Uses headless Google Chrome via Chrome DevTools Protocol (pure Python stdlib WebSocket client) to:
1. Verify 100% mathematical parity between Python and Browser JS R3B evaluators across all 42
   deterministic reference cases (`r3b_browser_python_parity_report.json`)
2. Verify animated AutoVLA trajectory playback controls (`Play`, `Pause`, `Restart`, `0.5x`/`1x`/`2x`
   speed, timeline scrubbing, 7 scenes, 10 rollout variants, progressive BEV trail, ego marker, and
   recorded-sample vs display-interpolation visual distinction)
3. Verify responsive layout across Desktop (`1480x1050`), Tablet (`768x1024`), and Mobile (`390x844`)
   viewports without horizontal overflow or broken controls
4. Capture 7 high-resolution PNG screenshots of the live English dashboard
5. Record an authentic 38-second 16:9 (`1280x720`) H.264 MP4 demonstration video (`demo_walkthrough.mp4`)
   and lightweight animated GIF preview (`demo_preview.gif`) directly from the live browser DOM
6. Export a clean landscape PDF (`vla_handover_feasibility_report.pdf`) with `@media print` styling
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time
from typing import Any
import urllib.parse
import urllib.request


def resolve_chrome_binary() -> str:
    """Resolve Google Chrome or Chromium executable across macOS and Linux CI runners."""
    env_bin = os.environ.get("CHROME_BIN", "").strip()
    if env_bin and Path(env_bin).exists():
        return env_bin

    macos_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if macos_chrome.exists():
        return str(macos_chrome)

    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(candidate)
        if found:
            return found

    raise FileNotFoundError(
        "Could not locate Google Chrome or Chromium binary. Set CHROME_BIN or install Chrome/Chromium."
    )


class SimpleCDPClient:
    """Minimal RFC 6455 WebSocket client for local Chrome DevTools Protocol."""

    def __init__(self, ws_url: str) -> None:
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9222
        path = parsed.path or "/"

        self.sock = socket.create_connection((host, port), timeout=30.0)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode("ascii"))
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket handshake closed unexpectedly")
            resp += chunk
        if b" 101 " not in resp.split(b"\r\n")[0]:
            raise RuntimeError(f"WebSocket handshake failed: {resp!r}")
        self._buf = resp.split(b"\r\n\r\n", 1)[1]
        self._msg_id = 0

    def _recv_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("WebSocket connection closed while reading frame")
            self._buf += chunk
        out = self._buf[:n]
        self._buf = self._buf[n:]
        return out

    def _read_frame(self) -> str:
        while True:
            hdr = self._recv_exact(2)
            opcode = hdr[0] & 0x0F
            masked = (hdr[1] & 0x80) != 0
            length = hdr[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise RuntimeError("WebSocket closed by server")
            if opcode == 0x9:  # Ping -> send Pong
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode in (0x1, 0x2):
                return payload.decode("utf-8", errors="replace")

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        mask_key = os.urandom(4)
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask_key)
        masked_payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked_payload)

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._msg_id += 1
        req_id = self._msg_id
        msg = json.dumps({"id": req_id, "method": method, "params": params or {}}).encode("utf-8")
        self._send_frame(msg)
        while True:
            raw = self._read_frame()
            data = json.loads(raw)
            if data.get("id") == req_id:
                if "error" in data:
                    raise RuntimeError(f"CDP error calling {method}: {data['error']}")
                return data.get("result", {})

    def eval_js(self, expression: str) -> Any:
        res = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS exception: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


def record_authentic_demo_video(
    cdp: SimpleCDPClient,
    mp4_path: Path,
    gif_path: Path,
) -> dict[str, Any]:
    """Capture an authentic 16:9 (1280x720) walkthrough video and animated GIF from the live browser."""
    import av
    from PIL import Image

    fps = 10
    width, height = 1280, 720
    cdp.call(
        "Emulation.setDeviceMetricsOverride",
        {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
    )

    frames_With_repeats: list[tuple[bytes, int]] = []

    def capture_step(hold_frames: int = 1) -> None:
        b64 = cdp.call(
            "Page.captureScreenshot",
            {"format": "jpeg", "quality": 92, "fromSurface": True},
        )["data"]
        frames_With_repeats.append((base64.b64decode(b64), max(1, int(hold_frames))))

    # Segment 1 (0.0s - 5.5s = 55 frames): Executive overview & smooth scroll to Interactive Trajectory Explorer
    cdp.eval_js(
        """(() => {
            window.VLA_INTERACTIVE_EXPLORER.pausePlayback();
            const expScene = document.getElementById('select-explorer-scene');
            expScene.value = 'scene_02_stationary_lead_obstacle';
            expScene.dispatchEvent(new Event('change'));
            const smoothChk = document.getElementById('chk-explorer-smooth');
            if (smoothChk) {
                smoothChk.checked = true;
                smoothChk.dispatchEvent(new Event('change'));
            }
            window.VLA_INTERACTIVE_EXPLORER.setTime(0.0);
            window.scrollTo(0, 0);
        })()"""
    )
    time.sleep(0.15)
    capture_step(hold_frames=18)  # 1.8s at top executive summary

    # Smooth scroll down to #interactive-trajectory-explorer
    target_y = int(
        cdp.eval_js(
            "Math.max(0, document.getElementById('interactive-trajectory-explorer').getBoundingClientRect().top + window.scrollY - 12)"
        )
        or 500
    )
    for frac in (0.25, 0.50, 0.75, 1.0):
        cdp.eval_js(f"window.scrollTo(0, {int(target_y * frac)})")
        capture_step(hold_frames=3)
    capture_step(hold_frames=25)  # 2.5s inspecting initial state at t=0.0s

    # Segment 2 (5.5s - 17.5s = 120 frames): Animated AutoVLA trajectory playback across 0.0s -> 5.0s
    # Step in 0.1s increments (51 steps x 2 frames = 102 frames + 18 hold frames = 120 frames = 12.0s)
    for step_idx in range(51):
        t_val = round(step_idx * 0.1, 2)
        cdp.eval_js(f"window.VLA_INTERACTIVE_EXPLORER.setTime({t_val})")
        hold = 6 if t_val in (0.0, 1.0, 1.5, 5.0) else 2
        capture_step(hold_frames=hold)

    # Segment 3 (17.5s - 26.5s = 90 frames): Command-sensitivity intervention ('keep forward') & Scene 05 C10 ablation
    # 3A: Scrub back to t=1.5s on Scene 02 ('turn left' exits 1D corridor -> NOT_APPLICABLE)
    cdp.eval_js("window.VLA_INTERACTIVE_EXPLORER.setTime(1.5)")
    capture_step(hold_frames=15)

    # Switch rollout condition to 'keep forward' -> stays in 1D corridor (NECESSARY_CONDITION_SATISFIED)
    cdp.eval_js(
        """(() => {
            const cond = document.getElementById('select-explorer-condition');
            cond.value = 'scene_02_stationary_lead_obstacle__intervention_keep_forward';
            cond.dispatchEvent(new Event('change'));
        })()"""
    )
    for t_val in (1.5, 2.0, 2.5, 3.0, 3.5):
        cdp.eval_js(f"window.VLA_INTERACTIVE_EXPLORER.setTime({t_val})")
        capture_step(hold_frames=6)

    # 3B: Switch to Scene 05 Active Braking Deceleration to show C10 violation vs Signed-Accel Ablation
    cdp.eval_js(
        """(() => {
            const expScene = document.getElementById('select-explorer-scene');
            expScene.value = 'scene_05_active_braking_deceleration';
            expScene.dispatchEvent(new Event('change'));
            window.VLA_INTERACTIVE_EXPLORER.setTime(0.5);
        })()"""
    )
    capture_step(hold_frames=22)

    cdp.eval_js(
        """(() => {
            const cond = document.getElementById('select-explorer-condition');
            cond.value = 'scene_05_active_braking_deceleration__ablation_signed_accel';
            cond.dispatchEvent(new Event('change'));
            window.VLA_INTERACTIVE_EXPLORER.setTime(0.5);
        })()"""
    )
    capture_step(hold_frames=23)

    # Segment 4 (26.5s - 38.5s = 120 frames): Interactive R3B Simulator Parameter & Policy Sweep
    r3b_y = int(
        cdp.eval_js(
            "Math.max(0, document.getElementById('interactive-r3b-simulator').getBoundingClientRect().top + window.scrollY - 16)"
        )
        or 950
    )
    for frac in (0.35, 0.70, 1.0):
         y_pos = int(target_y + (r3b_y - target_y) * frac)
         cdp.eval_js(f"window.scrollTo(0, {y_pos})")
         capture_step(hold_frames=3)

    # Reset to Scene 02 keep_forward at t=1.0s and sweep speed, friction, reaction delay, and policy P0/P1/P2
    cdp.eval_js(
        """(() => {
            const expScene = document.getElementById('select-explorer-scene');
            expScene.value = 'scene_02_stationary_lead_obstacle';
            expScene.dispatchEvent(new Event('change'));
            const cond = document.getElementById('select-explorer-condition');
            cond.value = 'scene_02_stationary_lead_obstacle__intervention_keep_forward';
            cond.dispatchEvent(new Event('change'));
            window.VLA_INTERACTIVE_EXPLORER.setTime(1.0);
            document.getElementById('btn-r3b-reset-defaults').click();
            document.getElementById('btn-send-step-to-r3b').click();
        })()"""
    )
    capture_step(hold_frames=18)

    # Toggle unit to km/h and back to m/s
    cdp.eval_js(
        """(() => {
            const u = document.getElementById('select-r3b-speed-unit');
            u.value = 'kmh';
            u.dispatchEvent(new Event('change'));
        })()"""
    )
    capture_step(hold_frames=12)
    cdp.eval_js(
        """(() => {
            const u = document.getElementById('select-r3b-speed-unit');
            u.value = 'mps';
            u.dispatchEvent(new Event('change'));
        })()"""
    )

    # Sweep speed from 14.0 m/s to 21.0 m/s
    for spd in (14.5, 16.0, 17.5, 19.0, 20.5):
        cdp.eval_js(
            f"""(() => {{
                const el = document.getElementById('input-r3b-speed');
                el.value = '{spd}';
                el.dispatchEvent(new Event('input'));
            }})()"""
        )
        capture_step(hold_frames=6)

    # Sweep friction mu from 0.8 (Dry) -> 0.5 (Wet) -> 0.3 (Snow)
    for mu_val in (0.8, 0.5, 0.3):
        cdp.eval_js(
            f"""(() => {{
                const el = document.getElementById('input-r3b-mu');
                el.value = '{mu_val}';
                el.dispatchEvent(new Event('input'));
            }})()"""
        )
        capture_step(hold_frames=10)

    # Compare policy branch P0 vs P2 vs non-zero road grade domain boundary
    for pol in ("P0", "P2", "P1"):
        cdp.eval_js(
            f"""(() => {{
                const el = document.getElementById('input-r3b-mu');
                el.value = '0.75';
                el.dispatchEvent(new Event('input'));
                const p = document.getElementById('select-r3b-policy');
                p.value = '{pol}';
                p.dispatchEvent(new Event('change'));
            }})()"""
        )
        capture_step(hold_frames=9)

    total_frames = sum(count for _, count in frames_With_repeats)
    duration_s = round(total_frames / float(fps), 2)

    # Encode H.264 MP4 using PyAV
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(mp4_path), mode="w")
    stream = container.add_stream("libx264", rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "23", "preset": "fast", "movflags": "+faststart"}

    gif_pil_frames: list[Image.Image] = []
    gif_step_stride = 8  # covers full 39s walkthrough in ~49 lightweight frames
    frame_counter = 0

    for jpg_bytes, repeat_count in frames_With_repeats:
        pil_img = Image.open(io.BytesIO(jpg_bytes)).convert("RGB")
        av_frame = av.VideoFrame.from_image(pil_img)
        for _ in range(repeat_count):
            for packet in stream.encode(av_frame):
                container.mux(packet)
            if frame_counter % gif_step_stride == 0 and len(gif_pil_frames) < 52:
                resized = pil_img.resize((640, 360), Image.Resampling.LANCZOS)
                gif_pil_frames.append(resized.quantize(colors=96, method=Image.Quantize.FASTOCTREE))
            frame_counter += 1

    for packet in stream.encode():
        container.mux(packet)
    container.close()

    # Save animated GIF preview
    if gif_pil_frames:
        gif_pil_frames[0].save(
            str(gif_path),
            save_all=True,
            append_images=gif_pil_frames[1:],
            optimize=True,
            duration=int(1000 * gif_step_stride / fps),
            loop=0,
        )

    return {
        "mp4_path": str(mp4_path),
        "mp4_size_kb": round(mp4_path.stat().st_size / 1024.0, 2),
        "gif_path": str(gif_path),
        "gif_size_kb": round(gif_path.stat().st_size / 1024.0, 2),
        "fps": fps,
        "resolution": f"{width}x{height}",
        "total_frames": total_frames,
        "duration_s": duration_s,
    }


def run_browser_qa(record_video: bool = True) -> dict[str, Any]:
    ext_root = Path(__file__).resolve().parent
    report_dir = ext_root / "artifacts" / "report"
    html_path = report_dir / "index.html"
    screenshots_dir = report_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = report_dir / "vla_handover_feasibility_report.pdf"
    mp4_path = report_dir / "demo_walkthrough.mp4"
    gif_path = report_dir / "demo_preview.gif"
    parity_report_path = ext_root / "artifacts" / "r3b_browser_python_parity_report.json"

    if not html_path.exists():
        raise FileNotFoundError(f"Missing HTML report at {html_path}")

    chrome_bin = resolve_chrome_binary()

    # Pick a free localhost port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    user_data_dir = report_dir / ".chrome_qa_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    url = f"file://{html_path.resolve()}"
    proc = subprocess.Popen(
        [
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data_dir}",
            "--window-size=1480,1050",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for DevTools HTTP endpoint
        ws_url = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1.0) as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                for t in targets:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except Exception:
                time.sleep(0.2)

        if not ws_url:
            raise RuntimeError("Could not connect to headless Chrome DevTools endpoint")

        cdp = SimpleCDPClient(ws_url)
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1480, "height": 1080, "deviceScaleFactor": 2, "mobile": False},
        )

        # Wait until dashboard JS has initialized (#tbody-all-scenes populated)
        for _ in range(30):
            ready = cdp.eval_js("document.querySelectorAll('#tbody-all-scenes tr').length")
            if ready == 7:
                break
            time.sleep(0.2)

        overview_rows = cdp.eval_js("document.querySelectorAll('#tbody-all-scenes tr').length")
        if overview_rows != 7:
            raise RuntimeError(f"Expected 7 overview rows in dashboard, found {overview_rows}")

        # 0. Verify Python vs. Browser JS R3B Mathematical Parity across all 42 Reference Cases
        parity_report = cdp.eval_js("window.VLA_INTERACTIVE_EXPLORER.verifyAllParityCasesInBrowser()")
        if not isinstance(parity_report, dict):
            raise RuntimeError(f"Failed to execute verifyAllParityCasesInBrowser(): {parity_report}")
        parity_report_path.write_text(json.dumps(parity_report, indent=2) + "\n", encoding="utf-8")
        if parity_report.get("total_cases", 0) < 42 or parity_report.get("failed_count", 1) != 0 or not parity_report.get("all_passed"):
            failed_details = [c for c in parity_report.get("results", []) if not c.get("passed")]
            raise RuntimeError(
                f"Browser vs. Python R3B parity check failed ({parity_report.get('failed_count')} mismatches): "
                f"{json.dumps(failed_details[:3], indent=2)}"
            )

        # 1. Capture Screenshot 01: Executive Research Findings & Interactive Selector Bar
        cdp.eval_js("window.scrollTo(0, 0)")
        time.sleep(0.25)
        shot1_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot1_path = screenshots_dir / "01_executive_findings_and_overview.png"
        shot1_path.write_bytes(base64.b64decode(shot1_b64))

        # 2. Verify Scene 01 Counterfactual d0 = 45.00 m State Provenance (Priority 2 check)
        s01_check = cdp.eval_js(
            """(() => {
                const sel = document.getElementById('select-record');
                sel.value = '0';
                sel.dispatchEvent(new Event('change'));
                const obsSel = document.getElementById('select-obstacle');
                obsSel.value = 'd0_45.00m';
                obsSel.dispatchEvent(new Event('change'));
                const firstRowBadge = document.querySelector('#tbody-r3b-schedule tr:first-child td:nth-child(2)')?.innerText || '';
                const secondRowBadge = document.querySelector('#tbody-r3b-schedule tr:nth-child(2) td:nth-child(2)')?.innerText || '';
                const firstRowCells = Array.from(document.querySelectorAll('#tbody-r3b-schedule tr:first-child td')).map(td => td.innerText.trim());
                const bannerText = document.getElementById('active-selection-strip')?.innerText || '';
                const obsBadgeText = document.getElementById('obstacle-provenance-badge')?.innerText || '';
                const r3bSvgText = document.getElementById('svg-r3b-margin-container')?.textContent || '';
                return { firstRowBadge, secondRowBadge, firstRowCells, bannerText, obsBadgeText, hasP2Legend: r3bSvgText.includes('P2: Supported Decel') };
            })()"""
        )
        if "Observed Ego (t0) + Assumed Obstacle (d0)" not in s01_check["firstRowBadge"]:
            raise RuntimeError(f"Scene 01 t=0 badge check failed: {s01_check['firstRowBadge']}")
        if s01_check["firstRowBadge"].strip() == "OBSERVED_T0":
            raise RuntimeError("Scene 01 with counterfactual d0=45m was erroneously labelled OBSERVED_T0!")
        if "Hypothetical VLA + Assumed Obstacle (d0)" not in s01_check["secondRowBadge"]:
            raise RuntimeError(f"Scene 01 t>0 badge check failed: {s01_check['secondRowBadge']}")
        if not s01_check["hasP2Legend"]:
            raise RuntimeError("R3B legend text check failed: missing 'P2: Supported Decel (1–3 m/s² during t₁)'")

        # Scroll to R3B Counterfactual Takeover section for Scene 01 screenshot
        cdp.eval_js("document.getElementById('obstacle-provenance-badge').scrollIntoView({behavior: 'instant'})")
        time.sleep(0.25)
        shot4_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot4_path = screenshots_dir / "04_scene_01_counterfactual_d0_provenance.png"
        shot4_path.write_bytes(base64.b64decode(shot4_b64))

        # 3. Smoke-test jumping to Scene 05 and capture Screenshot 02 (Controlled Signed-Acceleration Ablation & C10 Violation)
        s05_check = cdp.eval_js(
            """(() => {
                document.querySelector('[data-jump-scene="scene_05_active_braking_deceleration"]').click();
                const banner = document.getElementById('active-selection-strip')?.innerText || '';
                const feasBadge = document.getElementById('feas-classification-badge')?.innerText || '';
                const c10Row = Array.from(document.querySelectorAll('#tbody-feas-checks tr')).find(r => r.innerText.includes('C10'))?.innerText || '';
                const ablationHasSvg = !!document.querySelector('#svg-scene05-ablation-container svg');
                return { banner, feasBadge, c10Row, ablationHasSvg };
            })()"""
        )
        if "scene_05_active_braking_deceleration" not in s05_check["banner"]:
            raise RuntimeError(f"Scene 05 jump failed: {s05_check['banner']}")
        if "CONSTRAINTS_VIOLATED" not in s05_check["feasBadge"]:
            raise RuntimeError(f"Scene 05 did not display CONSTRAINTS_VIOLATED: {s05_check['feasBadge']}")
        if not s05_check["ablationHasSvg"]:
            raise RuntimeError("Scene 05 ablation SVG did not render")

        cdp.eval_js("document.getElementById('scene05-ablation-section').scrollIntoView({behavior: 'instant'})")
        time.sleep(0.25)
        shot2_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot2_path = screenshots_dir / "02_scene_05_braking_violation_and_ablation.png"
        shot2_path.write_bytes(base64.b64decode(shot2_b64))

        # 4. Smoke-test clicking Scene 03 in overview table, testing select-mu and slider-tau, and capture Screenshot 03
        s03_check = cdp.eval_js(
            """(() => {
                document.querySelector('#tbody-all-scenes tr[data-rec-idx="2"]').click();
                const muSel = document.getElementById('select-mu');
                muSel.value = '0.5';
                muSel.dispatchEvent(new Event('change'));
                const slider = document.getElementById('slider-tau');
                slider.value = '1.0';
                slider.dispatchEvent(new Event('input'));
                const tauVal = document.getElementById('tau-val-label')?.innerText || '';
                const firstBadge = document.querySelector('#tbody-r3b-schedule tr:first-child td:nth-child(2)')?.innerText || '';
                return { tauVal, firstBadge };
            })()"""
        )
        if "1.0" not in s03_check["tauVal"]:
            raise RuntimeError(f"Slider interaction failed: tauVal={s03_check['tauVal']}")
        if "Observed Ego (t0) + Static Proj. of Moving Lead" not in s03_check["firstBadge"]:
            raise RuntimeError(f"Scene 03 moving-lead static projection badge check failed: {s03_check['firstBadge']}")

        # Reset mu=1.0 and tau=0.0 for clean Scene 03 R3B visual screenshot
        cdp.eval_js(
            """(() => {
                const muSel = document.getElementById('select-mu');
                muSel.value = '1.0';
                muSel.dispatchEvent(new Event('change'));
                const slider = document.getElementById('slider-tau');
                slider.value = '0.0';
                slider.dispatchEvent(new Event('input'));
                document.getElementById('obstacle-provenance-badge').scrollIntoView({behavior: 'instant'});
            })()"""
        )
        time.sleep(0.25)
        shot3_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot3_path = screenshots_dir / "03_scene_03_urban_lead_r3b_handover.png"
        shot3_path.write_bytes(base64.b64decode(shot3_b64))

        # 5. Iterate through all 7 scenarios in #select-record to confirm all render without error
        all_scenes_tested = cdp.eval_js(
            """(() => {
                const sel = document.getElementById('select-record');
                const results = [];
                for (const opt of Array.from(sel.options)) {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change'));
                    const camFrontSrc = document.getElementById('img-cam-front')?.getAttribute('src') || '';
                    const bevHasSvg = !!document.querySelector('#svg-bev-container svg');
                    const speedHasSvg = !!document.querySelector('#svg-speed-container svg');
                    const accelHasSvg = !!document.querySelector('#svg-accel-container svg');
                    const checksRows = document.querySelectorAll('#tbody-feas-checks tr').length;
                    results.push({ key: opt.text, camFrontOk: camFrontSrc.startsWith('data:image/svg+xml;base64,') || camFrontSrc.startsWith('data:image/jpeg;base64,'), bevHasSvg, speedHasSvg, accelHasSvg, checksRows });
                }
                return results;
            })()"""
        )
        for item in all_scenes_tested:
            if not item["camFrontOk"] or not item["bevHasSvg"] or not item["speedHasSvg"] or not item["accelHasSvg"] or item["checksRows"] < 10:
                raise RuntimeError(f"Scene render check failed for {item['key']}: {item}")

        # 6. Verify Interactive AutoVLA Trajectory Explorer, Animation Playback Controls & R3B Simulator
        interactive_qa = cdp.eval_js(
            """(() => {
                const expScene = document.getElementById('select-explorer-scene');
                const expCond = document.getElementById('select-explorer-condition');
                const expSlider = document.getElementById('slider-explorer-time');
                const r3bStatus = document.getElementById('r3b-sim-status-badge');
                const r3bMetrics = document.getElementById('r3b-sim-metrics-grid');
                const r3bSpeedUnit = document.getElementById('select-r3b-speed-unit');
                const r3bSpeedInput = document.getElementById('input-r3b-speed');
                const r3bMuInput = document.getElementById('input-r3b-mu');
                const r3bPolicy = document.getElementById('select-r3b-policy');

                // A. Check t=0.0s step checks: TIME_LOCAL_STEP must be NOT_DEFINED_AT_T0, C1 must be TRAJECTORY_WIDE
                expScene.value = 'scene_02_stationary_lead_obstacle';
                expScene.dispatchEvent(new Event('change'));
                expSlider.value = '0.0';
                expSlider.dispatchEvent(new Event('input'));
                const t0StepRows = Array.from(document.querySelectorAll('#tbody-explorer-step-checks tr')).map(tr => tr.innerText);
                const t0HasNotApp = t0StepRows.filter(txt => txt.includes('TIME_LOCAL_STEP') && txt.includes('NOT_DEFINED_AT_T0')).length;
                const t0HasTrajWide = t0StepRows.filter(txt => txt.includes('C1_TIMESTAMP_AND_HORIZON_CONTINUITY') && txt.includes('TRAJECTORY_WIDE')).length;

                // B. Scrub Scene 02 canonical ('turn left') to t = 1.5s -> Exits 1D corridor -> R3B NOT_APPLICABLE
                expSlider.value = '1.5';
                expSlider.dispatchEvent(new Event('input'));
                const s02TurnLeftStatusAt15s = r3bStatus.innerText.trim();
                const s02TurnLeftTelemetry = document.getElementById('explorer-step-telemetry').innerText;
                const interpBadgeAt15s = document.getElementById('explorer-interp-badge').innerText.trim();

                // B2. Enable smooth 0.1s interpolation and scrub to t = 1.2s -> DISPLAY INTERPOLATION badge
                const smoothChk = document.getElementById('chk-explorer-smooth');
                smoothChk.checked = true;
                smoothChk.dispatchEvent(new Event('change'));
                expSlider.value = '1.2';
                expSlider.dispatchEvent(new Event('input'));
                const interpBadgeAt12s = document.getElementById('explorer-interp-badge').innerText.trim();
                smoothChk.checked = false;
                smoothChk.dispatchEvent(new Event('change'));

                // C. Switch Scene 02 to 'keep forward' intervention at t = 1.5s -> Remains in 1D corridor -> NECESSARY_CONDITION_SATISFIED
                expSlider.value = '1.5';
                expSlider.dispatchEvent(new Event('input'));
                expCond.value = 'scene_02_stationary_lead_obstacle__intervention_keep_forward';
                expCond.dispatchEvent(new Event('change'));
                const s02KeepForwardStatusAt15s = r3bStatus.innerText.trim();
                const s02KeepForwardMetrics = r3bMetrics.innerText;

                // D. Verify speed unit toggle (m/s -> km/h) updates input and dual readout
                const speedMpsBefore = parseFloat(r3bSpeedInput.value);
                r3bSpeedUnit.value = 'kmh';
                r3bSpeedUnit.dispatchEvent(new Event('change'));
                const speedKmhAfter = parseFloat(r3bSpeedInput.value);
                r3bSpeedUnit.value = 'mps';
                r3bSpeedUnit.dispatchEvent(new Event('change'));

                // E. Verify policy branch P0 vs P2 changes required stopping distance
                r3bPolicy.value = 'P0';
                r3bPolicy.dispatchEvent(new Event('change'));
                const p0MetricsTxt = r3bMetrics.innerText;
                r3bPolicy.value = 'P2';
                r3bPolicy.dispatchEvent(new Event('change'));
                const p2MetricsTxt = r3bMetrics.innerText;

                // F. Verify invalid input guardrail (negative speed -5 m/s) returns NOT_APPLICABLE without fabricating margin
                r3bSpeedInput.value = '-5.0';
                r3bSpeedInput.dispatchEvent(new Event('input'));
                const invalidStatus = r3bStatus.innerText.trim();
                const invalidMetricsTxt = r3bMetrics.innerText;

                // G. Verify all 7 scenes and 10 rollout variants load cleanly in the explorer
                let totalVariantsTested = 0;
                for (const sOpt of Array.from(expScene.options)) {
                    expScene.value = sOpt.value;
                    expScene.dispatchEvent(new Event('change'));
                    for (const cOpt of Array.from(expCond.options)) {
                        expCond.value = cOpt.value;
                        expCond.dispatchEvent(new Event('change'));
                        if (document.querySelector('#svg-explorer-bev svg #bev-ego-vehicle-marker')) {
                            totalVariantsTested += 1;
                        }
                    }
                }

                // Restore Scene 02 keep_forward at t=0.0s to test live Play/Pause/Restart animation
                expScene.value = 'scene_02_stationary_lead_obstacle';
                expScene.dispatchEvent(new Event('change'));
                expCond.value = 'scene_02_stationary_lead_obstacle__intervention_keep_forward';
                expCond.dispatchEvent(new Event('change'));
                document.getElementById('btn-explorer-restart').click();
                document.querySelector('[data-playback-speed="2.0"]').click();
                document.getElementById('btn-explorer-play').click();

                return {
                    t0HasNotApp,
                    t0HasTrajWide,
                    s02TurnLeftStatusAt15s,
                    s02TurnLeftExitedCorridor: s02TurnLeftTelemetry.includes('EXITED 1D CORRIDOR'),
                    interpBadgeAt15s,
                    interpBadgeAt12s,
                    s02KeepForwardStatusAt15s,
                    s02KeepForwardMetrics,
                    speedMpsBefore,
                    speedKmhAfter,
                    p0MetricsTxt,
                    p2MetricsTxt,
                    invalidStatus,
                    invalidRejected: invalidMetricsTxt.includes('Invalid or nonphysical vehicle speed'),
                    totalVariantsTested,
                    playingStarted: window.VLA_INTERACTIVE_EXPLORER.getPlaybackState().playing,
                    speedMultiplierSet: window.VLA_INTERACTIVE_EXPLORER.getPlaybackState().speed,
                };
            })()"""
        )
        time.sleep(0.35)
        playback_progress = cdp.eval_js(
            """(() => {
                const stateWhilePlaying = window.VLA_INTERACTIVE_EXPLORER.getPlaybackState();
                document.getElementById('btn-explorer-pause').click();
                const stateAfterPause = window.VLA_INTERACTIVE_EXPLORER.getPlaybackState();
                document.getElementById('btn-explorer-restart').click();
                const stateAfterRestart = window.VLA_INTERACTIVE_EXPLORER.getPlaybackState();
                document.querySelector('[data-playback-speed="1.0"]').click();
                // Set to t=1.5s for Screenshot 07
                window.VLA_INTERACTIVE_EXPLORER.setTime(1.5);
                document.getElementById('select-r3b-obstacle-mode').value = 'observed';
                document.getElementById('btn-r3b-reset-defaults').click();
                document.getElementById('btn-send-step-to-r3b').click();
                return {
                    timeAdvancedTo: stateWhilePlaying.time_s,
                    pausedCleanly: !stateAfterPause.playing,
                    restartedToZero: stateAfterRestart.time_s === 0.0,
                };
            })()"""
        )

        if interactive_qa["t0HasNotApp"] != 9 or interactive_qa["t0HasTrajWide"] != 1:
            raise RuntimeError(f"Step check scope verification at t=0 failed: {interactive_qa}")
        if interactive_qa["s02TurnLeftStatusAt15s"] != "NOT_APPLICABLE" or not interactive_qa["s02TurnLeftExitedCorridor"]:
            raise RuntimeError(f"Scene 02 turn-left corridor exit check at t=1.5s failed: {interactive_qa}")
        if "RECORDED" not in interactive_qa["interpBadgeAt15s"] or "INTERPOLATION" not in interactive_qa["interpBadgeAt12s"]:
            raise RuntimeError(f"Recorded vs display interpolation label check failed: {interactive_qa}")
        if interactive_qa["s02KeepForwardStatusAt15s"] != "NECESSARY_CONDITION_SATISFIED":
            raise RuntimeError(f"Scene 02 keep-forward R3B coupling at t=1.5s failed: {interactive_qa}")
        if abs(interactive_qa["speedMpsBefore"] * 3.6 - interactive_qa["speedKmhAfter"]) > 0.25:
            raise RuntimeError(f"Speed unit conversion check failed: {interactive_qa}")
        if interactive_qa["p0MetricsTxt"] == interactive_qa["p2MetricsTxt"]:
            raise RuntimeError("Changing policy branch P0 -> P2 did not update R3B metrics")
        if interactive_qa["invalidStatus"] != "NOT_APPLICABLE" or not interactive_qa["invalidRejected"]:
            raise RuntimeError(f"Invalid speed guardrail check failed: {interactive_qa}")
        if interactive_qa["totalVariantsTested"] != 10:
            raise RuntimeError(f"Expected 10 trajectory rollout variants with ego markers, got {interactive_qa['totalVariantsTested']}")
        if not interactive_qa["playingStarted"] or playback_progress["timeAdvancedTo"] <= 0.05 or not playback_progress["pausedCleanly"] or not playback_progress["restartedToZero"]:
            raise RuntimeError(f"Trajectory animation playback verification failed: {interactive_qa} / {playback_progress}")

        # 6B. Verify Responsive Layout across Desktop (1480x1050), Tablet (768x1024), and Mobile (390x844)
        responsive_checks: dict[str, Any] = {}
        for vp_name, vp_w, vp_h, vp_mobile in (
            ("desktop_1480x1050", 1480, 1050, False),
            ("tablet_768x1024", 768, 1024, True),
            ("mobile_390x844", 390, 844, True),
        ):
            cdp.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": vp_w, "height": vp_h, "deviceScaleFactor": 2, "mobile": vp_mobile},
            )
            time.sleep(0.1)
            vp_res = cdp.eval_js(
                """(() => {
                    const docW = document.documentElement.clientWidth;
                    const scrollW = document.documentElement.scrollWidth;
                    const ids = ['select-explorer-scene', 'btn-explorer-play', 'slider-explorer-time', 'input-r3b-speed', 'r3b-sim-status-badge'];
                    const boxes = ids.map(id => {
                        const r = document.getElementById(id)?.getBoundingClientRect();
                        return { id, w: r ? Math.round(r.width) : 0, h: r ? Math.round(r.height) : 0 };
                    });
                    return {
                        clientWidth: docW,
                        scrollWidth: scrollW,
                        noHorizontalOverflow: scrollW <= docW + 4,
                        allControlsUsable: boxes.every(b => b.w >= 24 && b.h >= 14),
                        boxes,
                    };
                })()"""
            )
            if not vp_res["noHorizontalOverflow"] or not vp_res["allControlsUsable"]:
                raise RuntimeError(f"Responsive layout check failed on {vp_name}: {vp_res}")
            responsive_checks[vp_name] = vp_res

        # Capture Screenshot 07: Interactive AutoVLA Trajectory Explorer & Coupled R3B Simulator
        cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1600, "height": 1850, "deviceScaleFactor": 2, "mobile": False},
        )
        cdp.eval_js("document.getElementById('interactive-trajectory-explorer').scrollIntoView({behavior: 'instant'})")
        time.sleep(0.25)
        shot7_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot7_path = screenshots_dir / "07_interactive_r3b_and_trajectory_explorer.png"
        shot7_path.write_bytes(base64.b64decode(shot7_b64))
        cdp.call("Emulation.clearDeviceMetricsOverride")

        # Capture Screenshot 05 (RQ1 Command Sensitivity) & Screenshot 06 (RQ2 C10 Robustness Matrix)
        cdp.eval_js("document.getElementById('rq1-command-sensitivity-section').scrollIntoView({behavior: 'instant'})")
        time.sleep(0.2)
        shot5_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot5_path = screenshots_dir / "05_scene_02_06_command_sensitivity.png"
        shot5_path.write_bytes(base64.b64decode(shot5_b64))

        cdp.eval_js("document.getElementById('rq2-c10-robustness-section').scrollIntoView({behavior: 'instant'})")
        time.sleep(0.2)
        shot6_b64 = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
        shot6_path = screenshots_dir / "06_scene_05_c10_robustness_matrix.png"
        shot6_path.write_bytes(base64.b64decode(shot6_b64))

        # 7. Record Authentic 16:9 Demo Video & Animated GIF Preview
        video_metadata: dict[str, Any] = {}
        if record_video:
            video_metadata = record_authentic_demo_video(cdp=cdp, mp4_path=mp4_path, gif_path=gif_path)

        # 8. Export Landscape PDF with @media print styling
        cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1480, "height": 1080, "deviceScaleFactor": 2, "mobile": False},
        )
        cdp.eval_js(
            """(() => {
                document.querySelector('[data-jump-scene="scene_05_active_braking_deceleration"]').click();
                window.scrollTo(0, 0);
            })()"""
        )
        time.sleep(0.2)
        pdf_b64 = cdp.call(
            "Page.printToPDF",
            {
                "landscape": True,
                "printBackground": True,
                "paperWidth": 11.69,   # A4 landscape width in inches
                "paperHeight": 8.27,   # A4 landscape height in inches
                "marginTop": 0.35,
                "marginBottom": 0.35,
                "marginLeft": 0.35,
                "marginRight": 0.35,
                "preferCSSPageSize": True,
            },
        )["data"]
        pdf_bytes = base64.b64decode(pdf_b64)
        pdf_path.write_bytes(pdf_bytes)

        cdp.close()

        return {
            "status": "BROWSER_QA_PARITY_AND_EXPORT_PASSED",
            "overview_rows_verified": overview_rows,
            "scenes_interactively_tested": len(all_scenes_tested),
            "rollout_variants_tested": interactive_qa["totalVariantsTested"],
            "interactive_explorer_verified": True,
            "animation_playback_verified": playback_progress,
            "r3b_browser_python_parity": {
                "total_cases": parity_report["total_cases"],
                "passed_cases": parity_report["passed_count"],
                "failed_cases": parity_report["failed_count"],
                "all_passed": parity_report["all_passed"],
                "report_path": str(parity_report_path),
            },
            "responsive_viewports_verified": list(responsive_checks.keys()),
            "scene_01_t0_badge": s01_check["firstRowBadge"],
            "scene_01_t05_badge": s01_check["secondRowBadge"],
            "scene_03_t0_badge": s03_check["firstBadge"],
            "scene_02_turn_left_15s_r3b_status": interactive_qa["s02TurnLeftStatusAt15s"],
            "scene_02_keep_forward_15s_r3b_status": interactive_qa["s02KeepForwardStatusAt15s"],
            "screenshots": [
                str(shot1_path),
                str(shot2_path),
                str(shot3_path),
                str(shot4_path),
                str(shot5_path),
                str(shot6_path),
                str(shot7_path),
            ],
            "video_walkthrough": video_metadata,
            "pdf_export_path": str(pdf_path),
            "pdf_size_kb": round(len(pdf_bytes) / 1024.0, 2),
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run headless Chrome QA, R3B parity verification, and video capture.")
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Skip recording demo_walkthrough.mp4 and demo_preview.gif (for fast CI parity checks).",
    )
    args = parser.parse_args()
    out = run_browser_qa(record_video=not args.skip_video)
    print(json.dumps(out, indent=2))
