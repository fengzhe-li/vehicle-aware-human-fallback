# Phase 2 Git delivery record

The original checkout is `vehicle-aware-human-fallback` on
`feat/lateral-steering-recoverability`. Original commit `d5911a4` directly has
`f0c5e61` as parent and imports its automotive_can adapter. Both original commits
and the original sibling `vehicle-aware-can-and-lateral.patch` remain preserved.
Original patch SHA-256:
`c7c153206e2ade1c5975c58ffbb0d1e2bdb765a686fb1ad0d75aa2ad45878771`.

The remote was verified as
`https://github.com/fengzhe-li/vehicle-aware-human-fallback.git`. Network access
requires the approved network permission in this environment. Authenticated
GitHub verification found no published feat/* branches or existing PRs and no
accessible original CAN SHA (HTTP 422) before delivery.

A fresh, full sibling clone `vehicle-aware-delivery` passes `git fsck --full
--no-dangling`. Its main is `f52230a5b836fa3049bfa407ca2ebf5768676816`, containing
newer VLA/YOLO work. That work is retained. The incomplete historical objects in
the original checkout are not used for pushing.

Original patches were transplanted without rewriting the source checkout:

| Original | Clean clone |
|---|---|
| CAN `f0c5e61` | `ef3b5e2` |
| Lateral `d5911a4` | `da713e6` |
| Audit `588bcf7` | `74392f4` |

The lateral patch's README hunk did not match newer main. It was excluded during
patch application and its concise integration is restored in the audit commit,
while retaining the current-main README. All other original implementation files
were applied. No force push, hard reset, merge or deletion of local work occurred.

## Integration results and remaining blocker

The clean current-main research suite passed **508 tests, 11 skipped, 0 failed**
(48.61 s), with R3B reproduction included. Its eight regenerated lateral artifacts
and two audit outputs match the source checkout byte-for-byte. Git fsck passes.

Relative to the original 258-file manifest, four inherited current-main changes
are preserved: `research/data_matrix/D003_PIPELINE_REGISTRY.md`, `tests/test_r2a.py`,
`tests/test_r2b.py`, and `tests/test_r2c_lite.py`. The CAN test was absent from main
and is supplied by the CAN commit. A separate 257-file main baseline is recorded
in `verification/delivery_baseline_sha256.json`; only two explicitly authorized
test-only updates (`tests/test_r2b.py` for pandas 2.x list comparison and
`tests/test_r6a_figures.py` for cross-platform R6A content vs DEFLATE verification)
change existing baseline test files. No research calculation, dataset, or frozen
figure in `thesis/figures/*` is modified by this delivery.

An additional run of the newer VLA/YOLO extension suites produced **60 passed,
3 failed**. The failing tests are YOLO `test_frozen_inputs` and both variants of
`test_pipeline_contract` (`[False]` and `[True]`, which invoke `cli.check_frozen()`).
An isolated, unmodified worktree of GitHub main (`f52230a`) also produces **36 passed,
the same 3 failed** in YOLO. Git history forensics confirms that
`extensions/yolo_perception/frozen_inputs.json` (361 files) was frozen at commit
`88498643e79fea51cdb19a21a8f81ddef4a522e5` (2026-10-18), after which two
documentation commits on `main` (2026-10-31) modified tracked files without
refreshing `frozen_inputs.json`:
- `e46c9f0a2a5848b755d9dbe2c290d777850df1fc` (`docs: align VLA test count with current suite`) modified `README.md` (`5e5f57f3...` -> `f1291520...`).
- `f52230a5b836fa3049bfa407ca2ebf5768676816` (`docs: document R3B classification tolerance`) modified `docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md` (`cfe3bf7b...` -> `4e9e40dd...`).

All other 359/361 files in `frozen_inputs.json` match `main` byte-for-byte.
CAN PR #1 additionally modifies `tests/test_r6a_figures.py` (`6dd8373d...` ->
`6167838e...`), and Phase 2 additionally modifies `README.md` (`f1291520...` ->
`0e14ce6c...`) and `tests/test_r2b.py` (`0ccdbb35...` -> `316f2a3e...`). Exact
expected/main/delivery hashes are retained in `verification/audit_validation.json`.
The frozen manifest and its assertions were not weakened or silently refreshed.

The VLA suite (`test_one_command_offline_demo_and_readme_assets`) also invokes
`demo.run_offline_demo()` without a temporary output directory, rewriting the
tracked `extensions/vla_handover_feasibility/artifacts/evaluation_summary.json`
and `extensions/vla_handover_feasibility/artifacts/report/index.html` in place
when the 84 external camera JPEGs are absent (`camera_live_jpegs_present: 12 -> 0`).
These two test-generated files were restored to their exact committed bytes; no
VLA result changes are included. Running YOLO separately after restoration still
reproduces the three failures.

**PASS:** Phase 1 and Phase 2 model/software checks, local research regressions,
and hosted Linux CI checks.
**BLOCKED:** separate YOLO `frozen_inputs.json` baseline reconciliation (requires
explicit maintainer sign-off before refreshing the manifest and isolating VLA
demo test outputs to `tmp_path`). Validated collision avoidance remains outside
this model and is also BLOCKED.

## Publication and hosted checks

- [CAN PR #1](https://github.com/fengzhe-li/vehicle-aware-human-fallback/pull/1):
  open, base `main`, head `feat/automotive-can-dbc-integration` (`16f18d6`,
  updating `ef3b5e2`).
- [Lateral PR #2](https://github.com/fengzhe-li/vehicle-aware-human-fallback/pull/2):
  open **draft**, base `feat/automotive-can-dbc-integration`, head
  `feat/lateral-steering-recoverability` (merged cleanly with `16f18d6` without
  force-pushing).
- Both branch heads and `main` were verified using `git ls-remote`. Neither PR is merged.

Initial hosted CAN [run 42841275772](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42841275772)
and Lateral [run 42841988209](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42841988209)
passed native CTest (1/1) and 427 / 505 Python tests, failing solely in
`tests/test_r6a_figures.py::test_deterministic_rendering` on
`F8_transition_branch_comparison.png` (`expected=757b0a9792eecb8c336104c95f844a615b0f4febd90f48701e25e1c464543058`,
`observed=fa5d85f1ac774402b0a861e8af2212b959dbc85878651adbb7b44276490a0244`).
Chunk-level PNG and PDF stream forensics across macOS `arm64` and Linux `x86_64`
established the exact root causes:
1. **Zero plotted-data, font, or pixel differences on `F8_transition_branch_comparison.png` (and 11 of 12 PNGs — `F1`–`F9`, `FA1`, `FA2`):**
   Non-`IDAT` chunks (`IHDR`, `pHYs`, `IEND`) and CRCs are 100% identical, and
   `zlib.decompress(IDAT)` yields the **exact same 2,624,643-byte uncompressed
   scanline stream** (`0` filter-byte differences across 567 scanlines; `0`
   RGBA pixel differences across 656,019 pixels). The file SHA-256 differed
   solely because the `libz` DEFLATE encoder compiled into the Linux `manylinux`
   `x86_64` Pillow wheel emits a 69,663-byte `IDAT` stream whereas the macOS
   `arm64` Pillow wheel emits a 58,506-byte `IDAT` stream for the identical
   uncompressed scanline bytes. (`F8` failed first because `os.listdir()` on
   Linux `ext4` returned `F8_transition_branch_comparison.png` first.)
2. **Architecture (`arm64` vs `x86_64`) 1-ULP rounding on `F10.png` and `F9.pdf`:**
   `F10_identifiability_boundary.png` (`855 × 1205 = 1,030,275` pixels) has
   `1,030,271` bit-identical pixels and 4 anti-aliased `FancyArrowPatch` cubic
   Bezier edge pixels differing by `1/255` (1 LSB). With `matplotlib==3.11.1`,
   11 of 12 PDFs are 100% byte-for-byte identical across macOS and Linux;
   `F9_steering_sequence_vs_assumed_interval.pdf` has byte-identical streams
   `1..11` and a single $10^{-10}\text{ pt}$ coordinate rounding difference on
   line 1266 of stream `0` (`-15.3734381114` vs `-15.3734381115`).
3. **Unpinned `matplotlib` (`3.11.1` vs `3.11.2`) PDF `/Creator` string:**
   `r6a_thesis_figures.py` passes `metadata={"CreationDate": None, "ModDate": None, "Producer": None}`
   without `"Creator": None`, so `matplotlib 3.11.2` wrote `/Creator (matplotlib 3.11.2...)`
   into the PDF Info dictionary while keeping all decompressed PDF streams identical.

Commit `16f18d6` on `feat/automotive-can-dbc-integration` resolves this without
replacing any frozen figure in `thesis/figures/*` or weakening scientific
assertions: `.github/workflows/automotive-can.yml` pins the verified Python 3.11
scientific/rendering environment (`matplotlib==3.11.1`, `pillow==12.3.0`,
`fonttools==4.65.0`, `numpy==2.4.6`, `scipy==1.17.1`, `pandas==3.1.1`,
`sympy==1.14.0`, `contourpy==1.3.3`, `kiwisolver==1.5.1`, `cycler==0.12.1`,
`pyparsing==3.3.2`, `pytest==9.2.0`, `jsonschema==4.26.0`), and
`tests/test_r6a_figures.py::test_deterministic_rendering` verifies (a) within-environment
byte-for-byte determinism across two independent renders for all 24 files,
(b) exact byte-for-byte identity against `thesis/figures/*` on the canonical
reference platform (`darwin`/`arm64`, `matplotlib 3.11.1`), and (c) cross-platform
decompressed scanline, pixel, chunk, and PDF content-stream equivalence on all
platforms. Hosted CAN runs [42847646926](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42847646926)
(`pull_request`), [42847631755](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42847631755)
(`push`), and [42847646873](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42847646873)
(VLA workflow) all passed (`428 passed, 11 skipped, 1 deselected, 0 failed`).

## Review and handoff procedure

1. Use the clean `vehicle-aware-delivery` checkout or clone the published feature
   branches. The original `vehicle-aware-human-fallback` checkout deliberately
   retains its original history and has incomplete historical Git objects.
2. Review CAN PR #1 against main, including its hosted frozen-figure failure.
3. Review draft lateral PR #2 against CAN. Review exact frozen-input differences
   before any baseline reconciliation; retain assertions and research results.
   Isolate the existing VLA test outputs so one suite cannot rewrite the other's
   frozen inputs. Resolve/pin the figure rendering environment based on measured
   evidence, not a regenerated replacement for protected results.
4. Rerun the documented research, native and extension checks; keep repository-wide
   acceptance BLOCKED while any required check fails. No real-road safety claim
   follows even after software checks pass.
5. After CAN is merged, verify its implementation is present in main and retarget:

   ```sh
   gh pr edit 2 --repo fengzhe-li/vehicle-aware-human-fallback --base main
   ```

   Review the resulting diff and rerun checks before marking the lateral PR ready.
   Do not merge automatically or force-push to resolve the stack.

The original patch remains untouched. A separate sibling
`vehicle-aware-reviewed-delivery.patch` contains the complete clean delivery
changes against main `f52230a`; apply with `git am` only in a clean checkout of
that base (or review conflicts against newer main). Both original commits remain
available in the original local repository.
