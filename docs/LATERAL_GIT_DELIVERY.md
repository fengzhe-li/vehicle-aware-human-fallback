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

The lateral patch's README hunk did not match newer main. It was excluded during
patch application and its concise integration is restored in the audit commit,
while retaining the current-main README. All other original implementation files
were applied. No force push, hard reset, merge or deletion of local work occurred.

Delivery status: branches prepared; tests and PR publication pending. The intended
stack is CAN -> main, then lateral -> CAN. Retarget the lateral PR to main after
CAN is merged; neither PR is to be merged automatically.
