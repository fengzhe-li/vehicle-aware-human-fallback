# Provenance of results in this release

This repository is a curated public release. Its Git history contains a single
release commit. The commit identifiers and tag names recorded in result files and
project documents refer to the **pre-release development history**, which is
intentionally not part of this repository's Git history. They are kept as
historical identifiers and have not been replaced by the release commit, because
no analysis was re-run from the release commit.

## R2A, R2B and R2C-lite

| Result set | Recorded `code_commit` | `src_tree_dirty` |
|---|---|---|
| `results/R2A_event_vehicle_descriptives/` | `9d1c41d01a5a141f07020610c58879b76b214d11` | `false` |
| `results/R2B_repeated_exposure/` | `7662114faf10f4d8325409ecb3a66ef37daa0ed6` | `false` |
| `results/R2C_lite/` | `49ed1f8b8825a49a28dd48f7ac29990f1573b9fa` | `false` |

The recorded `code_commit` remains the provenance identifier. The run-relevant
source files of each result set are byte-identical in this release to their
content at that commit. [`tests/provenance_dependency_hashes.json`](../tests/provenance_dependency_hashes.json)
lists each dependency with the SHA-256 of its content at the historical commit,
and `test_r2a_provenance`, `test_r2b_provenance` and `test_r2c_provenance` fail if
any listed file in this release has a different hash.

## R3B

`results/R3B_braking_bounds/provenance.json` records `code_commit`
`a4f2cc4cf402e9fe01b58b2cea5330e0d99d759c` with `src_tree_dirty: false`. The five
code files it lists were byte-identical to that commit when this release was
prepared; this check is not part of the automated test suite.

## R4V

`results/R4V_channel_authorship/provenance.json` and
`results/R4V_steering_sequence/provenance.json` record `src_tree_dirty: true`
(`code_commit` `3d99177470fce1ac875cdc6a1f117af1802c433a` and
`9c06946a69d379d7012fa6bdb19629f964666724`). The analysis scripts
`src/experiments/r4v_channel_authorship.py` and
`src/experiments/r4v_steering_sequence.py` were **uncommitted at execution time**;
the recorded `code_commit` is the committed base state at that moment, not a tree
containing the scripts. Both scripts were committed later, and the versions in
this release are those committed versions. Whether they differ from the exact
code that produced the outputs cannot be established from the record.

## Thesis figure freeze

`thesis/figures/figure_manifest.json` records `code_commit_at_render`
`e6c215c90f42b0ce7603f11691f0cfb1748a2fb7` (a pre-release commit) and the SHA-256 of
each figure's source inputs. Both are retained unchanged. `tests/test_r6a_figures.py`
re-renders every figure, checks that each output is byte-identical to the committed
figure file, and checks that every recorded source hash matches the corresponding
file in this release.

## Commit and tag names in audit and decision documents

Commit identifiers and tag names cited in the decision, status, audit and
handoff documents (for example the `phase0-frozen` and `pre-audit-2026-09-22`
tags, and review commits such as `fe34ffc` or `47347a0`) identify historical
pre-release states. Those commits and tags do not exist in this repository.
Where these documents refer to unmerged parallel branches, the branches are
identified by their commit IDs.
