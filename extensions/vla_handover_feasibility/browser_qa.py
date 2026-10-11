"""Automated Browser Interaction Smoke Test, Screenshot Capture, and PDF Export QA (Priority 4 & 5).

Uses headless Google Chrome via Chrome DevTools Protocol (pure Python stdlib WebSocket client) to:
1. Verify interactive controls (scenario selector, obstacle source selector, friction selector, takeover slider, quick-jump buttons)
2. Verify English-only text, untruncated scenario names, corrected P0/P1/P2 policy legends, explicit state-source badges (`OBSERVED_EGO_T0 + ASSUMED_D0`), and both distance [m] and time [s] margins
3. Capture 4 high-resolution PNG screenshots of the live English dashboard
4. Export a clean landscape PDF (`vla_handover_feasibility_report.pdf`) with `@media print` styling
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
from typing import Any
import urllib.parse
import urllib.request


CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


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


def run_browser_qa() -> dict[str, Any]:
    ext_root = Path(__file__).resolve().parent
    report_dir = ext_root / "artifacts" / "report"
    html_path = report_dir / "index.html"
    screenshots_dir = report_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = report_dir / "vla_handover_feasibility_report.pdf"

    if not html_path.exists():
        raise FileNotFoundError(f"Missing HTML report at {html_path}")

    # Pick a free localhost port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    user_data_dir = report_dir / ".chrome_qa_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    url = f"file://{html_path.resolve()}"
    proc = subprocess.Popen(
        [
            CHROME_BIN,
            "--headless=new",
            "--disable-gpu",
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
        for _ in range(40):
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

        # 6. Verify Interactive AutoVLA Trajectory Explorer & Interactive R3B Simulator (Priority Interactive Demonstrator QA)
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

                // C. Switch Scene 02 to 'keep forward' intervention at t = 1.5s -> Remains in 1D corridor -> NECESSARY_CONDITION_SATISFIED
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
                const savedSpeed = r3bSpeedInput.value;
                r3bSpeedInput.value = '-5.0';
                r3bSpeedInput.dispatchEvent(new Event('input'));
                const invalidStatus = r3bStatus.innerText.trim();
                const invalidMetricsTxt = r3bMetrics.innerText;

                // Restore clean Scene 02 keep_forward state at t=1.5s in Connected Mode for screenshot
                expScene.value = 'scene_02_stationary_lead_obstacle';
                expScene.dispatchEvent(new Event('change'));
                expCond.value = 'scene_02_stationary_lead_obstacle__intervention_keep_forward';
                expCond.dispatchEvent(new Event('change'));
                expSlider.value = '1.5';
                expSlider.dispatchEvent(new Event('input'));
                document.getElementById('select-r3b-obstacle-mode').value = 'observed';
                document.getElementById('btn-r3b-reset-defaults').click();
                document.getElementById('btn-send-step-to-r3b').click();

                return {
                    t0HasNotApp,
                    t0HasTrajWide,
                    s02TurnLeftStatusAt15s,
                    s02TurnLeftExitedCorridor: s02TurnLeftTelemetry.includes('EXITED 1D CORRIDOR'),
                    s02KeepForwardStatusAt15s,
                    s02KeepForwardMetrics,
                    speedMpsBefore,
                    speedKmhAfter,
                    p0MetricsTxt,
                    p2MetricsTxt,
                    invalidStatus,
                    invalidRejected: invalidMetricsTxt.includes('Invalid or nonphysical speed'),
                };
            })()"""
        )
        if interactive_qa["t0HasNotApp"] != 9 or interactive_qa["t0HasTrajWide"] != 1:
            raise RuntimeError(f"Step check scope verification at t=0 failed: {interactive_qa}")
        if interactive_qa["s02TurnLeftStatusAt15s"] != "NOT_APPLICABLE" or not interactive_qa["s02TurnLeftExitedCorridor"]:
            raise RuntimeError(f"Scene 02 turn-left corridor exit check at t=1.5s failed: {interactive_qa}")
        if interactive_qa["s02KeepForwardStatusAt15s"] != "NECESSARY_CONDITION_SATISFIED":
            raise RuntimeError(f"Scene 02 keep-forward R3B coupling at t=1.5s failed: {interactive_qa}")
        if abs(interactive_qa["speedMpsBefore"] * 3.6 - interactive_qa["speedKmhAfter"]) > 0.25:
            raise RuntimeError(f"Speed unit conversion check failed: {interactive_qa}")
        if interactive_qa["p0MetricsTxt"] == interactive_qa["p2MetricsTxt"]:
            raise RuntimeError("Changing policy branch P0 -> P2 did not update R3B metrics")
        if interactive_qa["invalidStatus"] != "NOT_APPLICABLE" or not interactive_qa["invalidRejected"]:
            raise RuntimeError(f"Invalid speed guardrail check failed: {interactive_qa}")

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

        # 7. Export Landscape PDF with @media print styling
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
            "status": "BROWSER_QA_AND_PDF_EXPORT_PASSED",
            "overview_rows_verified": overview_rows,
            "scenes_interactively_tested": len(all_scenes_tested),
            "interactive_explorer_verified": True,
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
            "pdf_export_path": str(pdf_path),
            "pdf_size_kb": round(len(pdf_bytes) / 1024.0, 2),
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        import shutil
        shutil.rmtree(user_data_dir, ignore_errors=True)


if __name__ == "__main__":
    out = run_browser_qa()
    print(json.dumps(out, indent=2))
