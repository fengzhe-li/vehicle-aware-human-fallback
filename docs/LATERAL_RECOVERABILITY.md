# Lateral feasibility model and evidence boundary

## Research inspected

Development used the verified local fengzhe-li/vehicle-aware-human-fallback
checkout from the CAN commit f0c5e61edb128055d586ada2128f6a93dc4b394d. This branch,
feat/lateral-steering-recoverability, includes that local commit and requires no
cloud import.

Inspected contracts and evidence:

- src/metrics/oracle.py: R3B stopping-distance phases and required-time convention.
- src/experiments/r3b_braking_bounds.py: fixed scenario grid, assumption intervals,
  policy branches and ±0.01 s classification guard.
- src/vehicle/models.py, src/handover/models.py, src/scenarios/models.py:
  SI units, tyre-friction cap, explicit authority/effective-control times and
  stationary longitudinal hazard.
- tests/test_r3b_model_corrections.py, tests/test_r3b_bounds.py,
  tests/test_r3b_reporting.py: analytical references, interval checks and frozen
  output protection.
- docs/R4V_STEERING_SEQUENCE.md: steering onset is descriptive; onset, lane
  crossing, manoeuvre completion and recovery are distinct events. The extension
  does not infer human response distributions or steering capability from D003.
- automotive_can/dbc.py, its tests and engineering notes: decoded state and
  timestamp contract. No steering/road-geometry measurements are assumed present.

## Candidate path

Let the reference road have constant signed curvature k, station s and Frenet
tangent/normal vectors t,n. The lateral path is

~~~text
r(s) = r_road(s) + y(s) n(s)
u = s / S, 0 <= u <= 1
y(s) = h q(u)
q(u) = 10u³ - 15u⁴ + 6u⁵
~~~

Its initial and final lateral slopes and second derivatives are zero. The
vehicle begins tangent to the road and finishes tangent to the offset curve.
It then follows that offset curve; terminal continuation must be covered by the
clearance assumption. h is signed. On a curved road the final curvature is
k/(1-k*h), rather than k.

For initial speed v and total response delay T:

~~~text
T = observation latency + driver response delay + steering actuator delay
S = available road distance - longitudinal buffer - v T
~~~

During this delay the vehicle is assumed to keep following the reference road
at constant speed. Available distance is measured at the observation epoch;
latency is therefore counted once before the response delay. During the
manoeuvre speed is constant along the actual path, not along reference-road
station. Consequently ds/dt = v / sqrt(A²+B²) below.

For closed intervals, exact usable-distance bounds are

~~~text
S_min = D - buffer - v_max T_max
S_max = D - buffer - v_min T_min
~~~

S_max <= 0 certifies failure of this delayed candidate. If only S_min <= 0,
the outcome is unknown because the interval contains both exhausted and
positive horizons. No candidate path is generated at zero/negative length.

## Exact geometric curvature

Using A = 1-k*y, B = y', C = y'', E = y''':

~~~text
r'  = A t + B n
r'' = -2k B t + (k A + C) n
M = A² + B²
N = k A² + A C + 2k B²
curvature = N / M^(3/2)
N' = A E + 3k B C - 2k² A B
M' = 2B(C-k A)
curvature' = N'/M^(3/2) - (3/2) N M'/M^(5/2)
~~~

This avoids the small-angle shortcut of adding road curvature to y''.
Coordinates are restricted to min(1,1-k*h) >= 0.1, so the road-relative mapping
does not fold or approach its singularity. Unknown geometry and unsupported
domains are reported, not clipped into a feasible answer.

## Bicycle and grip constraints

With wheelbase L and front road-wheel steering angle delta:

~~~text
delta = atan(L * curvature)
lateral acceleration = v² * curvature
delta_dot = L * curvature' * v / (sqrt(M) * (1+(L*curvature)²))
~~~

Absolute demands are compared with configured steering, steering-rate and
lateral acceleration limits. Lateral capacity is the smaller of the configured
lateral limit and mu*g, using the original GRAVITY=9.81. No longitudinal
acceleration is commanded during this candidate. A friction circle for
simultaneous braking and steering is outside the scope.

The distinction between a no-slip kinematic single-track model and tyre-slip
dynamics is illustrated in [Althoff, Koschi and Manzinger, CommonRoad: Composable Benchmarks for Motion
Planning on Roads](https://commonroad.in.tum.de/static/media/LA17.8f9d9dc3.pdf).
That presentation (model comparison, slide 6) supports this fidelity distinction;
it does not validate the numerical limits or synthetic scenarios here. The
rear-axle equations and curvature/interval certificates above are derived for
this extension.

## Certificates over the whole path

The derivative maxima of q are analytical:

~~~text
max |q'| = 15/8
max |q''| = 10/sqrt(3)
max |q'''| = 60
~~~

Since q is monotone between zero and one, A lies between the endpoint values 1
and 1-k*h. Write these positive endpoints as a_min, a_max, and use S_min for
derivative upper bounds b_max, c_max, e_max.

~~~text
n_max  = |k| a_max² + a_max c_max + 2 |k| b_max²
np_max = a_max e_max + 3 |k| b_max c_max + 2 k² a_max b_max
mp_max = 2 b_max (c_max + |k| a_max)
K_upper = n_max / a_min³
Kprime_upper = np_max/a_min³ + 1.5 n_max mp_max/a_min⁵
steering_rate_upper = L v_max Kprime_upper / a_min
~~~

These bounds can be loose, particularly on curved roads. A large upper bound
does not prove infeasibility.

Lower certificates come from the maximum of endpoint curvature magnitudes and
the curvature magnitudes at u=(3±sqrt(3))/6. At each fixed u, its numerator is
k*A² + coefficient/S², so an interval over S bounds its signed numerator.
The smallest absolute numerator divided by the largest possible denominator
is a valid lower bound for every S. An interval crossing zero contributes zero.
Endpoint steering rates have a closed form:

~~~text
|delta_dot| = L v |60h| /
              (S³ A³ [1 + (L k/A)²])
~~~

Using v_min and S_max yields a lower certificate for steering-rate demand.

A constraint is certified satisfied only when its upper demand is strictly
below its minimum capacity. It is certified violated only when its lower demand
exceeds its maximum capacity. A scale-relative 1e-9 numerical guard leaves
boundary equality unknown. Intermediate/overlapping bounds remain unknown;
they are not silently classified from midpoint or corner samples. Thus
infeasible rules out this prescribed quintic family under the stated bounds,
not every conceivable steering trajectory.

## Evidence and initial conditions

Speed and delay intervals propagate through all bounds. Grip intervals bound
capacity. A required observation with missing, stale, invalid, future_timestamp
or sensor_disagreement cannot support a feasibility certificate. The adapter
checks each signal's timestamp on one monotonic clock, and the oldest age is
consumed as latency.

The initial steering interval must agree with atan(L*k) to numerical tolerance
(1e-9 rad). Uncertainty or mismatch beyond that tolerance yields unknown, with
an explicit requirement for a transient model. This is a deliberate limitation,
not an inference that uncertainty is harmless. Initial heading, rear-axle
location, zero sideslip, constant-speed tracking and clearance remain stated
scenario conditions rather than measured facts.

The corridor is already eroded for the complete swept vehicle envelope and
clearance margins. The module checks monotone y between 0 and h against that
band and the declared required final offset. It does not compute a vehicle
footprint/obstacle intersection or validate road geometry.

## Additive longitudinal decision

decision.py calls the original stopping_distance_r3b_analytical with fixed,
explicit R3B timelines and pre-control profiles. It supports speed/friction
intervals: with fixed nonnegative pre-control decelerations and delays,
stopping distance is increasing in initial speed and decreasing in available
braking deceleration. The endpoint calls enclose these two uncertain inputs.

Observation latency consumes constant-speed distance before TOR. Distance
margin subtracts stopping distance and the explicit standstill margin from
available distance. Conservative interval division by speed gives time-margin
bounds, passed to the existing R3B classify function and its 0.01 s guard.
The R3B label is retained alongside the additive outcome.

Steering delay is not automatically substituted for R3B effective braking time.
On curved/unknown roads, stopping is unknown because R3B supplies no joint
lateral/longitudinal grip budget. With missing braking assumptions, it is also
unknown. The candidates are reported independently and never ranked as safer.

## Limitations

This is a deterministic kinematic feasibility study. It excludes tyre dynamics,
load transfer, road banking/grade, yaw and roll transients, actuator feedback,
steering acceleration limits, varying curvature, moving obstacles, friction
estimation, map/perception validation and initial steering correction. Numerical
input guards return unknown for extremely small usable distances or extreme
scales. No empirical calibration, real-road experiment, HIL, ECU test or safety
certification is implied by any result.

## Acceptance audit clarifications

The stopping adapter now requires usable initial steering consistent with zero
road curvature (within the same 1e-9 rad numerical tolerance). Otherwise it
returns unknown: the original R3B longitudinal equation cannot allocate grip to
an unmodelled lateral force. This gate changes additive classifications only;
the original solver, classifier and historical research outputs are untouched.
The standalone `assess_combined_braking_steering()` returns unknown for every
request. Separate feasible certificates cannot be combined into simultaneous
braking and steering. Even the necessary idealized circle condition
`sqrt(a_x²+a_y²) <= mu*g` would not validate the changing speed, path, tyre forces
or controller tracking; it is not implemented as a coupled feasibility model.

Direct `State` construction is a contract with the caller: evidence labels must
already reflect the caller's freshness policy. It has no wall clock or universal
maximum age. `from_can` enforces the explicitly supplied monotonic `now_ns` and
`max_age_ns` at each critical signal; equality at maximum age is accepted. Ages
are consumed once in the available-distance horizon. Runtime configuration
errors (wrong types, absent required delays, NaN/Infinity, reversed intervals)
raise ValueError before assessment. Represent absent measurements with a MISSING
Observation and absent road/grip/clearance with None to obtain unknown. Malformed
CAN physical values are INVALID evidence, never substituted with zero.
Public geometry helpers reject unsupported scales; the assessor reports unknown
when its demand calculation leaves that numerical domain.
