# Automotive CAN integration verification record

Run on 2026-11-10 in the local development environment (AppleClang 21.0.0,
Python 3.14, pandas 2.3.3). Synthetic fixtures only.

| Check | Result |
|---|---|
| CMake configure and C++17 build | Passed |
| Native `ctest` | 1 passed |
| `tests/test_automotive_can.py` | 4 passed |
| Synthetic R3B replay example | Passed; stopping distance 61.9167 m and required time 3.19583 s for its labelled synthetic inputs |
| Existing full research suite | 427 passed, 11 skipped, 1 deselected, 1 failed |

The one full-suite failure is the unchanged
`tests/test_r2b.py::test_exposure_order_and_participant_counts`. Its comparison of
a pandas Series of Python lists with a nested list raises a pandas shape
mismatch (`(57,)` versus `(57, 9)`) under the installed pandas 2.3.3. No research
test, result, dataset, or model calculation was modified to mask this failure.

GitHub Actions has been added for the native build and complete Python suite,
but hosted CI has not run from this local branch. No push or pull request was
created during this verification.
