# Phase 2 safety acceptance audit — 2026-11-10

## Assessment and scope

**PASS for conditional model/software acceptance on the original local tree.**
**BLOCKED for repository-wide acceptance** by the independently reproduced
YOLO frozen-input guard failures and hosted R6A PNG hash mismatch described in
the Git delivery record.
**BLOCKED for validated collision avoidance or choosing a safe manoeuvre.** Those
claims require evidence and models outside this extension. Git delivery and the
current-main integration check are tracked in [LATERAL_GIT_DELIVERY.md](LATERAL_GIT_DELIVERY.md).

This audit extends the existing implementation; it does not replace its path
model, change R3B equations, or recalibrate protected research results. The
original commits `f0c5e61` and `d5911a4` and original offline patch are preserved.
The numerical equations and derivation are in
[LATERAL_RECOVERABILITY.md](LATERAL_RECOVERABILITY.md).

## Model audit findings

| Area | Finding / acceptance boundary |
|---|---|
| Geometry and units | SI rear-axle, no-slip bicycle; `delta=atan(L*kappa)`; exact constant-curvature Frenet geometry, including terminal `k/(1-k*h)`. Independent Cartesian finite differences and circle references pass. |
| Steering constraints | Angle and rate bounds checked over the whole prescribed quintic family. Steering acceleration, feedback and tracking error remain unmodelled. |
| Dynamic constraint | `a_y=v²*abs(kappa)`, capacity `min(a_y_limit, mu*9.81)`. This necessary force bound is not a tyre-dynamics or collision-avoidance validation. |
| Distance and delays | `S=D-buffer-v*(driver+actuator+latency)`; interval extrema use highest speed/delay for shortest horizon. Speed is along actual path; distance is road station. Delay follows the reference road. |
| Initial steering | Must match ideal road following within 1e-9 rad. Wider uncertainty/mismatch returns unknown, rather than assuming a corrective transient. |
| Braking and steering | Separate candidates; no grip budget is shared between them. New explicit simultaneous-request API always returns unknown. Curved-road braking already returned unknown. |
| Stopping-wrapper defect fixed | Straight-road stopping previously accepted missing/uncertain steering. It now withholds certification for unusable or nonzero/uncertain steering. The original R3B solver and classifier are unchanged. |
| Freshness and validity | Individual CAN signal timestamps/validity checked, explicit age threshold, future timestamps rejected, redundant disagreement fails closed. Direct State callers must supply already-gated evidence; the core has no independent clock. |
| Invalid inputs | Wrong dataclass types and malformed required fields raise ValueError. CAN None/string/bool/nonfinite/overflowing physical values become INVALID. Geometry helpers reject unsupported scales. |
| Clearance | External, pre-eroded swept-envelope corridor must cover delay, manoeuvre and terminal continuation. No obstacle intersection, moving-object or road-edge validation is performed. |

Geometry feasible alone cannot make a candidate feasible. Feasible requires both
geometry and all conservative demand upper bounds below their minimum capacities.
A certified lower-bound violation makes this candidate infeasible; it does not
rule out all possible paths. Missing evidence, unsupported modelling and overlapping
bounds remain unknown. Equality retains a relative 1e-9 guard. A known independent
clearance violation can still prove infeasibility when another input is unknown.
Every decision retains `collision_avoidance=not_validated` and no recommendation.
A conditional stopping certificate with absent lateral clearance remains a 1D
counterfactual result, not a selected safe manoeuvre.

## All 8,748 scenarios and unknown attribution

The unchanged grid is 3 speeds × 3 road curvatures × 3 distances × 3 steering
limits × 3 grip values × 3 driver delays × 3 latencies × 4 sensor modes. The exact
axes, vehicle constants and 175-case one-at-a-time sensitivity baseline are in
[summary.json](../lateral_recoverability/artifacts/summary.json). These synthetic
frequencies are not driving probabilities. Actuator delay is fixed at 0.2 s in
the grid; delay intervals and limits are tested separately.

| Candidate | Original feasible / infeasible / unknown | Audited feasible / infeasible / unknown |
|---|---:|---:|
| Lateral | 258 / 1,124 / 7,366 | **258 / 1,124 / 7,366** |
| Additive R3B stopping | 549 / 873 / 7,326 | **183 / 291 / 8,274** |

No lateral unknown was promoted. Exactly 948 previously non-unknown stopping
results are now unknown (366 feasible and 582 infeasible): the new gate prevents
unsupported certificates in either direction. The original solver produces the
same values for supported inputs, verified against direct oracle calls.

Primary means the **first emitted reason in evaluation order**. It is a disjoint
accounting convention, not causal importance. Overlapping counts include each
case once per category, and must not be summed. Early return can mask later gates.

| Lateral unknown category | Primary count | % of 7,366 unknown | % of 8,748 total | Overlapping count | Overlapping % of unknown |
|---|---:|---:|---:|---:|---:|
| combined braking steering uncertainty | 0 | 0.000% | 0.000% | 0 | 0.000% |
| missing model assumptions | 0 | 0.000% | 0.000% | 0 | 0.000% |
| missing road or obstacle geometry | 0 | 0.000% | 0.000% | 0 | 0.000% |
| missing sensor evidence | 1,458 | 19.794% | 16.667% | 2,187 | 29.690% |
| other | 0 | 0.000% | 0.000% | 0 | 0.000% |
| overlapping constraint bounds | 49 | 0.665% | 0.560% | 49 | 0.665% |
| r3b parameter sensitive | 0 | 0.000% | 0.000% | 0 | 0.000% |
| sensor disagreement | 1,458 | 19.794% | 16.667% | 1,458 | 19.794% |
| stale or invalid vehicle state | 2,916 | 39.587% | 33.333% | 2,916 | 39.587% |
| steering uncertainty | 1,458 | 19.794% | 16.667% | 1,458 | 19.794% |
| uncertain remaining distance | 27 | 0.367% | 0.309% | 27 | 0.367% |

All stale cases concern speed: 2,187 also have stale steering, and 729 have missing
steering. Thus emitted missing-steering reasons total 2,187 (25% of all cases),
although only 1,458 are primary. Invalid and future timestamps have zero cases in
this grid; both are tested separately. Complete signal reason counts and both
percentage denominators are preserved in the machine-readable report.

Each fault mode is present in 2,187 unknown cases. Staleness masks the steering
uncertainty reason in 729 uncertain-steering inputs and the sensor-disagreement
reason in 729 disagreement inputs. These are input conditions, not additional
emitted diagnoses. `unknown_input_conditions` records them separately. No missing
road/obstacle geometry, missing grip or missing braking assumption occurs in the
grid: their zero counts are coverage gaps, not evidence that they are resolved.
Supplementary cases and tests exercise those gates without changing the 8,748 denominator.

Audited longitudinal unknown reasons are independently counted below; these must
not be added to the lateral totals.

| Emitted stopping reason | Count | % of 8,274 unknown | % of all 8,748 |
|---|---:|---:|---:|
| `curved_or_unknown_road_requires_joint_grip_model_for_braking` | 2,916 | 35.243% | 33.333% |
| `nonzero_or_uncertain_steering_requires_joint_braking_model` | 486 | 5.874% | 5.556% |
| `speed:sensor_disagreement` | 1,458 | 17.621% | 16.667% |
| `speed:stale` | 2,916 | 35.243% | 33.333% |
| `steering:missing` | 486 | 5.874% | 5.556% |
| `unchanged_R3B_conditional_braking_model` | 12 | 0.145% | 0.137% |

The 12 `unchanged_R3B_conditional_braking_model` unknown results retain the
original `PARAMETER-SENSITIVE` label; the reason is generic but the label and
margin bounds identify the uncertainty. All 8,748 simultaneous brake/steer
requests would be unknown by the separate unsupported-model guard. That is a
capability statement, not an extra cause in the lateral partition.

Audited decision counts: 120 both conditionally feasible, 138 lateral certificates,
63 longitudinal certificates, 270 neither evaluated candidate feasible, and
8,157 insufficient-evidence cases. A certificate does not imply that the other
candidate is impossible or that this candidate is safer.

## Representative boundaries

Stable case IDs follow product order in `AXES`; complete input evidence, metrics
and results for each emitted reason are included in the JSON report.

- Case 449: speed 10 ±0.5 m/s, road curvature -0.01/m, distance 60 m, mu=0.3,
  driver delay 1.5 s and latency 0.1 s. Acceleration demand bounds
  [2.055365, 3.023236] m/s² straddle the 2.943 m/s² grip capacity: **unknown**.
- Case 6505: speed 30 ±0.5 m/s, distance 100 m, driver delay 3 s and actuator
  delay 0.2 s. Remaining distance [-2.6, 0.6] m: **unknown**, not a clipped path.
- Cases 2/3/4: missing steering / disagreeing speed / steering ±0.01 rad each
  block lateral certification before the demand bounds are evaluated.
- Case 9: age 0.4 s exceeds the 0.25 s threshold; both signals are stale.
- Analytical tests set exact circular demand to 4 m/s². Capacity 4 gives unknown,
  4.01 feasible, 3.99 infeasible. At the freshness threshold evidence is accepted;
  one nanosecond beyond it is stale. Zero horizon is infeasible for the delayed
  path, whereas a 1e-5 m positive horizon is outside the numerical domain.

Reproduce the tables and supplementary missing-input boundaries:

```sh
python3 -m lateral_recoverability.audit
```

Outputs: [unknown_analysis.json](../lateral_recoverability/verification/audit/unknown_analysis.json)
and [case_reasons.csv](../lateral_recoverability/verification/audit/case_reasons.csv).

## Regression, compatibility and reproducibility

| Check on the original local tree | Actual result |
|---|---|
| Original lateral suite | 51 passed |
| Added acceptance tests | 28 passed |
| Entire research suite, including R3B study | **508 passed, 11 skipped, 0 failed** (59.10 s) |
| Fresh native CAN configure/build/CTest | **1/1 passed** |
| Before audit protected manifest | **258/258 byte-identical** |
| After audit protected manifest | **257/258 identical; one authorized test-only compatibility correction** |
| Original eight artifacts regenerated before editing | **8/8 byte-identical**, including PNGs |
| Audited artifacts vs original | **6/8 identical**; scenarios.csv and summary.json intentionally changed |
| Two final audited runs | **8/8 byte-identical** |

`tests/test_r2b.py` formerly compared a Series of lists (shape 57) with a nested
list (shape 57×9), which raises a pandas 2.3.3 broadcasting ValueError. Comparing
`.apply(sorted).tolist()` with the same 57 expected lists preserves the complete
assertion. Four mutation tests verify rejection of duplicate exposure, missing
row, extra row and wrong participant. No assertion or test was skipped or weakened.
The original baseline manifest is retained; the sole explicit exception is recorded
with before/after hashes in `verification/audit_validation.json`. All protected
scientific sources/data/results remain byte-identical.

The historical `verification/validation.json` remains the record of 479 passed,
1 failed and 11 skipped before this audit. The 11 current skips are unchanged:
nine unavailable D003 archive tests, one unavailable EPA workbook test, and one
collection skip for a local/embargoed thesis draft. No external evidence was invented.

```sh
MPLCONFIGDIR=/tmp/lateral-audit-mpl python3 -m pytest -o addopts= -q
cmake -S automotive_can -B /tmp/lateral-audit-can-build
cmake --build /tmp/lateral-audit-can-build
ctest --test-dir /tmp/lateral-audit-can-build --output-on-failure
MPLCONFIGDIR=/tmp/lateral-audit-mpl python3 -m lateral_recoverability.experiments
MPLCONFIGDIR=/tmp/lateral-audit-mpl python3 -m lateral_recoverability.experiments --output /tmp/lateral-repeat
```

`pre_audit.json` records all original artifact hashes. The changed scenario table
contains only revised longitudinal/decision labels; lateral outcomes and reasons
are unchanged. The summary updates counts, source hashes and scenario-file hash.
PNG figures, path samples, example result and sensitivity table are unchanged.
Environment: Python 3.14.5, numpy 2.5.3, pandas 2.3.3, matplotlib 3.11.1.
The clean delivery research suite also passed 508 tests with 11 skips. The
additional VLA/YOLO run passed 60 and failed 3 frozen-input checks, also reproduced
on pristine main; its preserved manifest needs separate reconciliation.
The separate clean delivery checkout inherits newer main changes; its results
and inherited baseline differences are reported separately in the Git delivery record.

## Remaining evidence gaps

No real-road, HIL, ECU, high-fidelity dynamics or controller validation is present.
Unknown initial steering requires a transient model. Simultaneous braking and
steering needs coupled force/path evolution. Grip calibration, heading/position,
road geometry, a swept vehicle envelope and obstacle clearance remain external
assumptions. The model excludes tyre slip, load transfer, bank/grade, yaw/roll,
variable curvature and moving traffic. Conservative bounds can be loose; an
unknown bound must not be converted into infeasibility or success by midpoint
sampling. Passing this audit authorizes review of a conditional feasibility
analysis; deployment or a collision-avoidance claim remains **BLOCKED**.
