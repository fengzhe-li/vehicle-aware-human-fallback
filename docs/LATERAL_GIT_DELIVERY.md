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
(52.48 s), with R3B reproduction included. Its eight regenerated lateral artifacts
and two audit outputs match the source checkout byte-for-byte. Git fsck passes.

Relative to the original 258-file manifest, four inherited current-main changes
are preserved: `research/data_matrix/D003_PIPELINE_REGISTRY.md`, `tests/test_r2a.py`,
`tests/test_r2b.py`, and `tests/test_r2c_lite.py`. The CAN test was absent from main
and is supplied by the CAN commit. A separate 257-file main baseline is recorded
in `verification/delivery_baseline_sha256.json`; only the authorized pandas
assertion correction changes one of those existing files. No research calculation
or result is modified by this delivery.

An additional run of the newer VLA/YOLO extension suites produced **60 passed,
3 failed**. The failing tests are YOLO `test_frozen_inputs` and both variants of
`test_pipeline_contract`. An isolated, unmodified worktree of GitHub main also
produces **36 passed, the same 3 failed** in YOLO. The existing frozen manifest
already disagrees with main's `README.md` and
`docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md`. Phase 2 additionally changes README
integration and the explicitly authorized `tests/test_r2b.py` assertion. Exact
expected/main/delivery hashes are retained in `verification/audit_validation.json`.
The frozen manifest and its assertions were not weakened or silently refreshed.

The VLA suite also rewrites its saved evaluation summary and HTML report when
external camera JPEGs are absent, changing only provenance evidence fields from
live JPEG presence to external-manifest evidence. These two test-generated files
were restored to their exact committed bytes; no VLA result changes are included.
Running YOLO separately after restoration still reproduces the three failures.

**PASS:** Phase 2 model/software checks and local research regressions.
**BLOCKED:** repository-wide acceptance until the existing frozen-input baseline
and test-output isolation are reconciled in a separately reviewed change.
Validated collision avoidance remains outside this model and is also BLOCKED.

## Publication

CAN PR: https://github.com/fengzhe-li/vehicle-aware-human-fallback/pull/1
against main, open and unmerged. Lateral publication is pending the final delivery
commit; it will be a draft against the CAN branch because of the recorded
repository-wide acceptance blocker. No merge is authorized automatically.
