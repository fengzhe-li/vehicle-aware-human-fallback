# D003 owner-metric reconciliation (Phase R2B)

Owner source: Liang, Calvert & van Lint, "Multidimensional Assessment of Takeover Performance in Conditionally Automated Driving", arXiv 2507.22252 (HTML version read). The text read reports model-performance figures, not descriptive values of these metrics. Unless stated otherwise the status is therefore: **definition-compatible only; numerical replication not possible from available publication text.**

Our outputs: `results/R2A_event_vehicle_descriptives/` and `results/R2B_repeated_exposure/`.

| Metric (owners) | Owners' definition (as published) | Our reconstructed definition | Population (n) | Window | Exclusions | Numerically comparable? | Status |
|---|---|---|---|---|---|---|---|
| Button press time `t_button` | Time to press the mode-switch button enabling manual inputs after the TOR | `Manual_Start − selected TOR`. Manual_Start is treated as an event marker; authority transfer is UNRESOLVED (B7) | TOR_ANCHORED (492) | event difference | 15 without a TOR column; 6 multi-TOR unresolved | No published value found | Definition-compatible only |
| Road reorientation time `t_road` | First visual fixation on the road after the TOR | Not reconstructed | — | — | Eye-tracking semantics not audited | No | NOT ATTEMPTED |
| Takeover time (ToT) | "Time to perform the first conscious operational response"; thresholds not stated | Not reconstructed: our candidate would rely on accelerator, brake or steering channels | — | — | — | No | BLOCKED BY B17 |
| Minimum TTC | Minimum time to collision from TOR to lane change | Minimum `Time_TTC` over samples with distance > 0, speed > 0 and TTC > 0 | OWNER_WINDOW_ELIGIBLE (478) | [TOR, lane change] as published (not handback-bounded); a handback-bounded variant (477) is stored separately | 21 without a TOR anchor; 13 without a lane-change channel; 1 lane-change clock exception | No published value found; the owners' handling of a stationary vehicle / negative TTC is not stated | Definition-compatible only (domain rule is ours) |
| Maximum steering wheel angle | Maximum from TOR to lane change | Maximum absolute steering-wheel-angle channel, and maximum deviation from pre-TOR baseline (owners' variant not stated) | OWNER_WINDOW_ELIGIBLE (478) | owners' window | as above | No | Channel measurement only; driver attribution BLOCKED BY B17 |
| Maximum acceleration | Maximum from TOR to lane change | Maximum longitudinal acceleration (`accel.001`) | OWNER_WINDOW_ELIGIBLE (478) | owners' window | as above | No; axis and sign convention not stated | Definition-compatible only; **vehicle state**. The owners' use as takeover quality is their interpretation |
| Maximum deceleration | Maximum from TOR to lane change | −minimum longitudinal acceleration | OWNER_WINDOW_ELIGIBLE (478) | owners' window | as above | No; axis and sign convention not stated | Definition-compatible only; **vehicle state**, not driver braking (B17) |
| Perceived time sufficiency, perceived risk, performance satisfaction | Questionnaire items | Not reconstructed (questionnaire file present) | — | — | — | No | NOT ATTEMPTED |

**Irreconcilable definitions:** none found. Several are **ambiguous** (steering variant, acceleration axis and sign, TTC domain handling). The owners' analysis set (466) is not reconstructed (`D003_OWNER_RECONCILIATION_LEDGER.md`).

**Replication vs new work:** `t_button`, minimum TTC and maximum acceleration/deceleration are owner metrics, recomputed here. Their exposure-order analysis (R2B) was not found in the owners' text read, so it is presented as a new descriptive analysis on existing definitions.
