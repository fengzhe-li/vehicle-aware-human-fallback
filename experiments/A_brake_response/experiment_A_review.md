# Experiment A — Adversarial Review

**Purpose:** attack `experiment_A_spec.md` before any implementation. This document does not implement anything; it identifies what must be fixed first.

## 1. Is the causal comparison identifiable?

Yes, but only as an **internal-validity** question, not yet as an **external-validity** one. Because profile shape is an experimenter-manipulated input inside a simulator, and driver/hazard/TOR/road-friction/nominal a_max are held fixed by construction, the causal contrast (profile P_i vs P_j, same everything else) is trivially identifiable inside the simulation. The open question is whether the *specific numeric shapes* assigned to P1-P4 are themselves identifiable from real evidence. Per `parameter_evidence_table.csv`, `deceleration_buildup_time`, `jerk_emergency_range`, and `regen_deceleration_range` are currently COUNTERFACTUAL or numerically unverified. So: the experiment is internally identifiable today; it is not yet externally anchored.

## 2. Are the controls sufficient?

Mostly, with one important gap: **the driver model's loop structure is unspecified.** The spec fixes "same decision rule" and "same correction rule" but never states whether the driver command sequence is **open-loop** (identical command trajectory injected regardless of resulting vehicle response) or **closed-loop** (driver reacts to perceived/vestibular deceleration feedback). If closed-loop, differences in vehicle response could change the driver's *subsequent* commands even under an identical decision rule — which would mean the experiment is no longer isolating the vehicle-response mechanism, but a vehicle-response-mediated-by-driver-feedback mechanism. This must be frozen explicitly before implementation. (Recommendation: Phase 1A prototype should be open-loop by construction, since the spec itself already defers `N_correction`/`t_stabilise` — i.e., correction-capable closed-loop behaviour — to a later stage.)

## 3. Are we accidentally comparing EV vs ICE labels rather than response functions?

Not in the spec's stated framing (P1-P4 are explicitly unlabeled generic architectures). But there is a **provenance-smuggling risk**: if P2's (regen-heavy) numeric parameters end up sourced predominantly from EV-labeled datasets (D004, D005, L006) while P1's (progressive friction-like) parameters end up sourced from generic/ICE-style engineering references, the EV/ICE label re-enters through the back door of parameter provenance even though no vehicle is named. Mitigation: anchor profile *shapes* to the architecture-level literature (L004's throttle-to-brake transition timing, L011's real cross-manufacturer deceleration/jerk differences — which are AEB-architecture differences independent of propulsion) rather than to any single EV-branded dataset, and note explicitly that blended/nonlinear braking (P3) exists in non-EV brake-by-wire systems too.

## 4. If maximum deceleration is held constant, what response differences remain physically meaningful?

Onset delay (time to first meaningful deceleration), build-up rate/shape (time-to-reach-a_max), near-stop roll-off (regen fade close to standstill, per L006's qualitative finding that not all regen modes reach a full stop), and mid-range blending nonlinearity (P3). These are meaningful because, for a fixed eventual a_max, stopping distance is driven by the area under the velocity curve during the transient ramp — a slower build-up genuinely consumes more distance before full braking is reached, independent of the eventual maximum. This is not vacuous.

## 5. Could the result become mathematically trivial?

**Yes, this is a real risk.** In the minimal kinematic model (`v[t+1] = v[t] + a[t]*dt`), if P1-P4 differ only in *how fast* they ramp to the same a_max, the outcome differences may collapse to a single scalar — an "effective added delay" or "build-up integral" — making the result a restatement of "later full braking is worse," not evidence of a distinctive architecture effect. To avoid triviality, at least one profile must introduce a feature that is **not reducible to a simple monotonic delay**: e.g., P2's near-stop regen roll-off (non-monotonic relative to a pure delay model) or P3's mid-range gain change. If all four profiles are just different monotonic ramps to the same asymptote, Gate A risks measuring "time-shift sensitivity" rather than "architecture sensitivity," and that distinction should be stated explicitly in any report of results.

## 6. Could stopping margin be determined almost entirely by reaction time and a_max?

Likely yes, **outside a narrow scenario band**. With fixed reaction time and fixed a_max, standard stopping-distance physics is dominated by (v0, reaction_time, a_max); transient shape is a second-order correction. That correction will only be decisive where the scenario TTC margin is tight relative to total available stopping time — i.e., in a "marginal recoverability" band, not in easy (large-margin) or hopeless (no-margin-regardless) scenarios. This mirrors the charter's own Gate A kill condition ("disappear when maximum deceleration is controlled") and should be treated as an *expected* pattern to test for, not a surprise if observed. A result showing effects only in a narrow marginal band is not automatically a kill signal — it may simply reflect where the mechanism is physically expected to matter — but it must be pre-registered as expected, not discovered and then rationalized post hoc.

## 7. Which transient response features could realistically create a measurable difference?

1. **Onset delay** — directly consumes usable stopping distance/time.
2. **Build-up rate** — determines time spent at sub-maximal deceleration.
3. **Near-stop roll-off** (regen fade, L006) — most likely to matter for continuous outcomes (`impact_speed`, `stopping_margin`) at the margin, even when it doesn't flip the binary `collision` outcome.
4. **Mid-range blending nonlinearity** (P3) — could matter for driver-perceived deceleration *if* a closed-loop driver model exists, but under the current open-loop Phase-1A scoping (see Q2, Q10) this feature has no channel to affect outcomes, since there is no correction-capable controller to respond to it yet. This is an important scoping caveat: P3 as currently scoped is likely to behave identically to a smooth P1/P4 variant in the minimal open-loop prototype.

## 8. Is longitudinal-only simulation sufficient for Gate A?

Yes, for a **first, scoped** test — the research question and primary outcomes (collision, TTC_min, stopping_margin, impact_speed) are explicitly longitudinal, and lateral avoidance is correctly deferred by the charter. But the Gate A verdict must be scoped in its wording to **"longitudinal-recoverability under braking-dominant hazards,"** not generalized to takeover recovery broadly, since real critical takeovers (per L003) often involve combined braking-and-steering responses that a longitudinal-only model cannot represent.

## 9. What would falsify the mechanism?

The mechanism is falsified if, across literature-constrained (not hand-picked) profile parameter ranges, differences in TTC_min/stopping_margin/impact_speed are smaller than (a) the simulation's own noise/discretization floor, or (b) the effect of perturbing reaction time by one literature-derived standard deviation, **across a pre-registered, non-cherry-picked scenario grid** spanning easy/marginal/hopeless regions — not just a hand-picked marginal band. It is also falsified (in the "realistic architecture matters" sense specifically) if any observed effect only appears when profile parameters are pushed outside literature-constrained ranges into COUNTERFACTUAL territory.

## 10. What minimum experiment would be scientifically meaningful?

A one-at-a-time diagnostic sweep, consistent with `PHASE0_CHECKLIST.md`'s own instruction to avoid a large Cartesian grid first:
1. Fix v0, TTC0, TOR, mu, and all driver parameters.
2. Vary only the response profile (P1-P4), using literature-constrained parameter values where available and explicitly-labeled COUNTERFACTUAL placeholders elsewhere.
3. Repeat across a small, pre-registered grid of scenario "tightness" (TTC0 x TOR combinations spanning easy -> marginal -> unrecoverable), specifically to test whether effects concentrate in the marginal band as physically expected (Q6).
4. Report effect sizes against two explicit comparators, decided *before* the run: (i) the simulation noise floor, (ii) the outcome sensitivity to a one-standard-deviation reaction-time perturbation. A profile effect smaller than either comparator should not be reported as "material."

## 11. What must be fixed before implementation?

- **Freeze the driver-loop structure** (open-loop vs closed-loop) — currently unspecified and directly affects confound risk (Q2) and which profile features (e.g. P3's mid-range nonlinearity) can even produce an effect (Q7).
- **Freeze numeric ranges** for `deceleration_buildup_time`, `jerk_emergency_range`, and `regen_deceleration_range`, or explicitly label the first Gate-A run as a COUNTERFACTUAL/internal-validity-only prototype, separate from any later literature-anchored run. Do not let a COUNTERFACTUAL prototype result be reported as a literature-anchored Gate-A decision.
- **Freeze the practical-effect threshold** before seeing results (the spec already requires this — retain and sharpen it using the two comparators in Q10).
- **Pre-register the scenario-tightness grid** so the run cannot retroactively select a favorable region — this directly protects against the spec's own "occur only under hand-picked extreme parameters" kill condition.
- **State the longitudinal-only scope explicitly** in any reported Gate A conclusion (Q8), so a KEEP verdict is not silently generalized beyond braking-dominant hazards.
