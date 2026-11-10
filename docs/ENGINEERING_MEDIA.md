# Engineering media — provenance and integration

## Scope and release status

This documentation/media branch starts from main
`f52230a5b836fa3049bfa407ca2ebf5768676816`. CAN PR #1 and lateral PR #2 are still
open and unmerged. Media uses verified engineering commit
`ed96d22194536e0b3a72197682063052b7111341`; it does not copy implementation code
onto main or change any research calculation. Module pages are explicitly
labelled previews and link to pinned engineering source where main lacks a file.

## Presentation choices

| Module | Presentation | Evidence |
|---|---|---|
| Existing AutoVLA + R3B | Preserve existing GIF, MP4 and Pages player | GIF frames visually inspected; MP4 fully decoded (389 frames, 38.9 s, 1280×720); Pages Play/Pause visibly advanced saved trajectory steps |
| CAN/DBC | New 18 s GIF and H.264 MP4, static poster and JSON trace | Nine snapshots computed by the existing decoder/replay/value APIs from the synthetic fixture and documented invalid-speed transform |
| Lateral | Three existing PNG figures, copied byte-for-byte | Actual feasibility map, 175-case sensitivity study and analytical path geometry; no invented vehicle motion |

The existing VLA GIF is 640×360, 37 frames, 39.2 s. Its small text is better read
in the linked 1280×720 MP4 or live demo; it remains an accurate overview and was
not re-recorded. New CAN frames are 1200×680 and held for reading, not real-time
capture. The CAN GIF's clock and the animation's playback time are intentionally
different. No telemetry interpolation is used.

No lateral animation was added: independent analytical cases are more clearly
explained by the existing static plots, without suggesting a controller executes
the candidate or avoids an obstacle. Their numerical contents are unchanged.

## Artifacts and README placement

- Root README retains the existing VLA/R3B animated hero and MP4/Pages links.
  CAN GIF and lateral feasibility map appear after the technical executive overview.
- `automotive_can/README.md` embeds the CAN GIF and links MP4, poster and exact trace.
- `lateral_recoverability/README.md` embeds feasibility_map, sensitivity and
  path_geometry; inherited model assumptions and limitations are retained.
- `docs/media/engineering/manifest.json` records source, renderer/font/output hashes,
  actual versions, dimensions, playback durations and the synthetic-only boundary.
- `docs/media/engineering/can_trace.json` records all decoded values, per-signal
  availability, timestamps, ages, faults and the exact incoming payloads.

The copied PNGs in `docs/media/engineering/` let the main-based review preview
render before the engineering branches merge. They remain exact copies of
`lateral_recoverability/artifacts/`; they are not alternate scientific baselines.

## Reproduction

Use the verified source checkout containing both engineering modules. From the
media branch, with the repository's existing matplotlib/Pillow dependencies:

```sh
python3 tools/engineering_media/render.py \
  --engineering-root ../vehicle-aware-delivery \
  --output /tmp/engineering-media-repeat \
  --ffmpeg /path/to/ffmpeg
VEHICLE_ENGINEERING_ROOT=../vehicle-aware-delivery \
  python3 -m pytest tools/engineering_media/test_render.py -q
```

FFmpeg is optional: omitting it generates the GIF, poster, trace and figures.
The tested encoder is FFmpeg 7.1 supplied by `imageio-ffmpeg==0.6.0`, installed
only into a temporary folder. No project runtime dependency was changed. The
renderer reads the supplied source tree and writes only the output directory.
Recorded hashes identify the actual source even if an input checkout has edits.

## Safe merge sequence

1. Review and explicitly approve CAN PR #1 into main. Current head is `16f18d6`;
   hosted native/research and VLA verification checks are green.
2. After that merge, retarget draft lateral PR #2 from CAN to updated main.
   Check its diff and rerun CI at the resulting head before requesting merge
   approval. Current lateral head `ed96d2` has green hosted engineering checks.
3. After lateral is explicitly approved and merged, update this separate media
   branch from main and reconcile the new module README with the approved text.
   Because main currently lacks `lateral_recoverability/README.md`, that page is
   an intentional add/add reconciliation point; retain all approved model content
   and the added visual sections. Preserve the existing root README integration.
4. Review the media-only diff and CI, replace pending-release wording with actual
   status, then request explicit approval to merge the media PR. No PR is merged
   automatically, and no release tag or GitHub Pages deployment is created here.

## Known integrity boundaries

The separate YOLO frozen manifest already disagrees with main's README and R3B
interval documentation. Engineering adds reviewed test changes. This media
branch intentionally changes README again. All discrepancies must remain visible;
`extensions/yolo_perception/frozen_inputs.json` is retained unchanged.
The existing VLA demo test writes tracked reports when camera JPEGs are absent;
verification is performed in a temporary checkout so those generated differences
cannot enter this media PR. No camera data, telemetry, ECU connection or empirical
collision-avoidance validation is invented.

Actual final test results and file/hash comparisons are recorded in
[verification.json](media/engineering/verification.json).

## Actual local results — 2026-11-10

| Check | Result |
|---|---|
| Current engineering research suite, R3B study included | 508 passed, 11 skipped, 0 failed (55.02 s) |
| Fresh native CAN configure/build/CTest | 1/1 passed |
| Media snapshot/value/frame/hash/README-link tests | 9 passed |
| Existing VLA suite in isolated main checkout | 24 passed |
| YOLO suite on pristine main after restoring VLA-generated files | 36 passed, 3 inherited frozen-input failures |
| All eight original lateral outputs regenerated | 8/8 byte-identical |
| Two new media runs | 8/8 generated files byte-identical, including GIF and MP4 |
| Existing tracked main files changed by this media work | README.md only; all other tracked files identical |
| Existing scientific sources, data, results and thesis figures | No changes |

The 11 skips are nine missing D003 archive tests, one missing EPA workbook test
and one local/embargoed thesis collection skip. Tested on macOS arm64, Python
3.14.5, numpy 2.5.3, pandas 2.3.3, matplotlib 3.11.1, Pillow 12.3.0,
AppleClang 21.0.0 and FFmpeg 7.1. Rendering was visually checked at fresh,
invalid and expired CAN states; all three lateral figures were inspected.

**PASS:** deterministic visual evidence and applicable local engineering checks.
**Pending approval:** CAN, lateral and media merges; no release has been published.
**Remaining blocker:** YOLO frozen-baseline reconciliation and its existing VLA
report-writing test interaction. The manifest and assertions are not refreshed.
The earlier hosted R6A PNG encoding discrepancy has been resolved in the current
engineering heads; both PRs' checks were green when inspected. Post-merge CI must
still be run against the actual updated main before approving the next PR.
