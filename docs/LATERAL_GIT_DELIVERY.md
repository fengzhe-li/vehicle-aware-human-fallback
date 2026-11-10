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

## Publication and hosted checks

- [CAN PR #1](https://github.com/fengzhe-li/vehicle-aware-human-fallback/pull/1):
  open, base main, head `feat/automotive-can-dbc-integration` (`ef3b5e2`).
- [Lateral PR #2](https://github.com/fengzhe-li/vehicle-aware-human-fallback/pull/2):
  open **draft**, base CAN branch, head `feat/lateral-steering-recoverability`.
  The implementation and integration record were pushed through `e4a46ba`;
  this publication record follows as a documentation-only commit.
- Both branch heads and main were verified using `git ls-remote`. Neither PR is merged.

Hosted CAN [run 42841275772](https://github.com/fengzhe-li/vehicle-aware-human-fallback/actions/runs/42841275772)
passed native CTest (1/1) but failed
`tests/test_r6a_figures.py::test_deterministic_rendering` on the unchanged
`F8_transition_branch_comparison.png`. Regression totals: **427 passed, 1 failed,
11 skipped, 1 deselected**; this existing workflow excludes the R3B study by default.
The protected PNG SHA-256 is
`757b0a9792eecb8c336104c95f844a615b0f4febd90f48701e25e1c464543058`;
the Ubuntu fresh render is
`fa5d85f1ac774402b0a861e8af2212b959dbc85878651adbb7b44276490a0244`.
CI uses Python 3.11, matplotlib 3.11.2, numpy 2.4.6, pandas 3.1.1 and Pillow 13.0.0;
local validation uses Python 3.14.5 and matplotlib 3.11.1. The exact contribution
of library/font/platform differences has not been isolated. No original figure
or hash assertion was replaced to make the job green. The CAN PR's separate VLA
verification job passed; its Pages deployment was skipped. Lateral hosted checks
were still running at this recording; no hosted success is claimed.

This hosted frozen-figure mismatch is an additional **BLOCKED** acceptance item.
The passing local research runs do not establish cross-platform byte determinism.

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
