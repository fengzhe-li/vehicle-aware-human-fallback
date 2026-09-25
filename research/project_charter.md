# Project Charter v1.0

## 1. Starting point

The motivating problem is **automated-driving human takeover**, not EV-versus-ICE comparison.

The project begins from a systems question:

> Automation may hand control authority to a human when it reaches a difficult state, but authority transfer does not necessarily mean that the human–vehicle system has recovered enough capability to avoid the hazard.

This leads to a vehicle-aware human fallback problem.

## 2. Core mother question

> Under what combinations of vehicle dynamics, driver capability, handover policy and scenario criticality does human fallback remain an effective and safe recovery mechanism during time-critical automated-driving takeovers?

## 3. Working thesis

Human fallback safety should be treated as a **joint recoverability property** of the human, vehicle and automation rather than as a function of TOR lead time alone.

A conceptual form is:

`P(safe fallback) = f(vehicle state, braking response, driver–vehicle mismatch, TOR budget, human response, environment/scenario criticality)`

## 4. Mechanism layers

### 4.1 Vehicle-response layer
Study the mapping from control input to actual longitudinal response, including:
- progressive friction-dominant braking
- regenerative braking
- one-pedal-like response
- blended/nonlinear braking
- response latency
- deceleration build-up
- jerk
- maximum deceleration
- road friction
- propulsion acceleration authority

**Important:** ICE and EV are examples of response architectures, not the final explanatory labels.

### 4.2 Driver internal-model layer
Let `f_hat_driver` represent the driver's expected input→vehicle-response mapping and `f_vehicle` the actual mapping.

Define a generic mismatch term:

`M = D(f_hat_driver, f_vehicle)`

Phase 1 fixes `M = 0`. Later phases test whether mismatch changes first control action, secondary corrections, TTC, stopping margin and stabilisation.

### 4.3 Handover layer
Distinguish:
- `T_authority`: nominal authority transfer
- `T_effective`: first effective human control
- `T_stable`: recovered stable control

The project must not equate “hand on wheel” or automation disengagement with safe control reacquisition.

### 4.4 System-level layer
Mechanisms that survive individual tests are coupled into a Human Fallback Safety Envelope.

## 5. Core Phase-1 variables

Inputs / controlled factors:
- initial speed `v0`
- initial TTC / hazard distance
- TOR lead time
- fixed reaction time
- road friction `mu`
- brake-response mapping
- maximum deceleration
- deceleration build-up / jerk
- automation withdrawal policy

Later extensions:
- vehicle mass
- acceleration capability
- driver–vehicle mismatch
- reaction-time distribution
- lateral avoidance dynamics

## 6. Primary outcomes

1. Collision indicator
2. Minimum TTC
3. Stopping margin
4. Impact speed
5. Stabilisation time
6. Secondary correction count

Collision alone is insufficient because a low-speed contact and a high-speed impact are not equivalent outcomes.

## 7. Evidence classes

Every parameter used in the project must be tagged as one of:

- `OBSERVED`
- `LITERATURE_CONSTRAINED`
- `DERIVED`
- `COUNTERFACTUAL`

A parameterised simulation value must never be described as if it were an observed production-vehicle calibration.

## 8. Claim boundaries

This project does **not** aim to:
- prove that EVs are more or less safe than ICE vehicles
- replicate a specific OEM brake-by-wire / regenerative-blending calibration
- infer a production vehicle's proprietary brake map
- build a complete ADS perception/planning stack
- treat fast takeover as equivalent to successful recovery
- assume that high acceleration capability itself causes crashes
- infer population-level human factors from a fixed driver model

## 9. Kill gates

### Gate A — vehicle-response effect
If realistic braking-response changes do not materially alter recovery metrics, kill or narrow the vehicle-response branch.

### Gate B — risk-state escalation
If propulsion acceleration authority does not materially change the rate at which fallback margin is consumed under controlled scenarios, kill or narrow the high-performance branch.

### Gate C — driver–vehicle mismatch
If mismatch does not materially change effective recovery, corrections or safety metrics, remove it from the final framework.

### Gate D — coupling
If vehicle × TOR and mismatch × TOR interactions are negligible, do not claim a unified vehicle-aware handover framework.

### Gate E — robustness
If effects only exist in a narrow hand-picked parameter region, do not make a broad system-level claim.

## 10. Simulation strategy

Do **not** start with CARLA.

Phase 1 begins with a transparent longitudinal simulator:

`v(t+dt) = v(t) + a(t) dt`

`x(t+dt) = x(t) + v(t) dt + 0.5 a(t) dt^2`

with

`a(t) = f(u_driver(t), v(t), theta_vehicle)`

CARLA becomes a later validation / extension environment only if the mechanism survives the simple simulator.

## 11. Novelty status

**Not yet frozen.**

Current literature clearly supports:
- takeover time-budget variability
- safety problems in critical takeovers
- behavioural differences under one-pedal / regenerative braking
- public takeover and EV-dynamics data availability

The stronger gap — that vehicle-specific response architecture is insufficiently integrated into human-fallback safety modelling — remains a **working gap hypothesis** until the Phase 0 literature matrix is expanded systematically.
