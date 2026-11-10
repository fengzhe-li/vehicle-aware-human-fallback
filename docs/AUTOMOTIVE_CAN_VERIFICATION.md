# Automotive CAN integration verification record

Run on 2026-11-10 in the local development environment (AppleClang 21.0.0,
Python 3.14.5, numpy 2.5.3, pandas 2.3.3, matplotlib 3.11.1, Pillow 12.3.0)
and verified in Linux x86_64 (`ubuntu-latest` / Python 3.11.18, numpy 2.4.6,
pandas 3.1.1, matplotlib 3.11.1, Pillow 12.3.0). Synthetic fixtures only.

| Check | Result |
|---|---|
| CMake configure and C++17 build | Passed |
| Native `ctest` | 1 passed |
| `tests/test_automotive_can.py` | 4 passed |
| Synthetic R3B replay example | Passed; stopping distance 61.9167 m and required time 3.19583 s for its labelled synthetic inputs |
| Existing full research suite (local macOS, pandas 2.3.3) | 427 passed, 11 skipped, 1 deselected, 1 failed (`tests/test_r2b.py`) |
| Existing full research suite (Linux CI, pandas 3.1.1) | 428 passed, 11 skipped, 1 deselected, 0 failed |

On the local macOS environment with pandas 2.3.3, the one full-suite failure on
this branch is the unchanged
`tests/test_r2b.py::test_exposure_order_and_participant_counts`, whose
comparison of a pandas Series of Python lists with a nested list raises a pandas
2.x shape mismatch (`(57,)` versus `(57, 9)`). Its pandas 2.x/3.x-compatible
list comparison is delivered with four mutation tests in the stacked Phase 2
branch. No research result, dataset, or model calculation is modified.

In `tests/test_r6a_figures.py::test_deterministic_rendering`, within-environment
byte-for-byte determinism across independent renders (all 24 PDF/PNG files) and
canonical reference-platform (`darwin`/`arm64`, matplotlib 3.11.1) byte identity
are verified alongside cross-platform content and visual verification against
`thesis/figures/*` (exact non-`IDAT` PNG chunk identity, exact decompressed
`IDAT` scanline and RGBA pixel identity for `F1`–`F9`, `FA1`, `FA2` including
`F8_transition_branch_comparison.png`, bounded 1-LSB / 4-pixel `arm64`-vs-`x86_64`
Bezier anti-aliasing check on `F10_identifiability_boundary.png`, and exact
decompressed PDF stream verification across all 12 PDFs). All frozen files in
`thesis/figures/*` remain untouched.
