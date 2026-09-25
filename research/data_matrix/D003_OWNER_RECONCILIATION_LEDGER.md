# D003 owner-reconciliation ledger (Phase R2A)

**Conclusion (unchanged from R1): the owners' 466-trial analysis set cannot be reconstructed from verified public information.** This ledger records what is known. It is not an attempt to reach 466, and no exclusions have been manufactured.

Source of the owner figures: Liang, Calvert & van Lint, "Multidimensional Assessment of Takeover Performance in Conditionally Automated Driving", arXiv 2507.22252.

| Item | Owner description (public) | Owner count | Repo-side observation | Repo count | Confidence | Why exact reconstruction fails |
|---|---|---|---|---|---|---|
| Raw takeovers | 57 participants × 9 scenarios | 513 | Simulator CSVs in the archive | 513 | CONFIRMED | — |
| Exclusion A | "participants either took vehicle control before the takeover request or forgot to press the mode switch button" | 16 | Files without a TOR column (header variant `NO_TOR_44`) | 15 | PLAUSIBLE (for the 15); the 16th trial is UNKNOWN | No per-trial list is published. `Manual_Start` is present in all 513 files, so "forgot to press the button" cannot be identified from the data |
| Exclusion B | "incomplete questionnaires and hardware malfunctions" | 31 | Trials without an eye-tracking gaze file | 31 (3 overlap with the 15 no-TOR files) | PLAUSIBLE for a hardware subset only; UNKNOWN overall | The public questionnaire file has no missing values, so "incomplete questionnaires" is not observable. Hardware failures other than missing gaze files are not observable. The count match is coincidental until confirmed |
| Analysed set | Takeovers analysed | 466 | — | not constructed | UNKNOWN | Needs the owners' per-trial list or reproducible criteria |
| Multi-TOR trials | Not mentioned | — | 26 trials with 2–3 TOR values; 6 unresolved under the TTC ≈ 7 s protocol | 26 / 6 | UNKNOWN | How the owners anchored these trials is not stated |

**Repo populations are not the owners' set.** `TOR_ANCHORED` (492), `OWNER_WINDOW_ELIGIBLE` (478), `LANE_CHANGE_ANCHORED` (477) and `MANUAL_WINDOW_ELIGIBLE` (492) are repo-defined. None equals the owners' 466.

Per-trial candidate flags: `results/R1_ingestion_validation/owner_reconciliation.csv`. Questions to the owners: `research/D003_DATASET_OWNER_QUESTIONS.md`.
