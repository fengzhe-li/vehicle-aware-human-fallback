# Gap Audit — Phase 0.1

**Purpose:** actively try to falsify the working gap hypothesis, not protect it.

**Working gap hypothesis (as stated in the project charter):**
> Vehicle-specific longitudinal response architecture (regenerative/friction blending, brake-response delay, deceleration build-up, jerk) may not yet be systematically integrated, as a manipulated takeover-relevant variable, into a unified human-fallback safety framework that also accounts for TOR timing and driver internal-model mismatch.

Search covered six themes (A1-A6) with 15+ distinct queries across takeover-timing, post-takeover control quality, regenerative/blended braking, driver internal models, vehicle-dynamics-in-takeover, and acceleration/risk-escalation literature (see `literature_matrix.csv`, entries L001-L014). This is a bounded, not exhaustive, search — see Section 7.

---

## 1. Clearly established literature

- **TOR time budget is scenario-dependent, not a fixed universal constant** (L001, L002, L007, L008). Multiple systematic reviews (2024-2026) converge on this.
- **Fast takeover does not imply safe recovery.** Drivers who take over quickly often over-brake or over-steer relative to what the hazard required (L003).
- **Post-takeover control does not stabilise instantly.** Driving-metric stabilisation is empirically estimated around 8-10 s after takeover, with physiological recovery lagging further (L009).
- **Braking/control architecture measurably changes emergency control behaviour in at least one directly relevant paradigm.** One-pedal (regen-heavy) vs two-pedal control changes throttle-to-brake transition time and brake-timing variability, with safety effects that depend on scenario urgency (L004). This is the strongest single piece of evidence that the project's core mechanism (architecture -> emergency outcome) is real in at least one setting.
- **Production braking-control architectures already differ measurably in the field.** Independent of propulsion type, AEB systems from different manufacturers show different onset TTC thresholds, deceleration-rate/speed scaling, and jerk trends (L011). This is non-takeover evidence but it establishes that "architecture, not label" is empirically the right framing (supports D002 directly).
- **Driver adaptation to altered vehicle dynamics is fast for small changes and produces after-effects for large changes** (L012). This constrains how M_mismatch should eventually be modeled — not novel by itself, but load-bearing evidence for Phase 2.
- **EV acceleration authority is already linked to traffic-conflict-level risk shifts** at intersections, independent of any takeover context (L013).
- **A fixed reaction-time assumption is an approximation, not a fact.** Naturalistic data show brake onset is better predicted by kinematic urgency than a constant (L014) — this is establishment of a *limitation*, not a gap in our favor.

## 2. Partially covered intersections

- **Braking-architecture x emergency behaviour** is covered (L004), but not inside an *automation takeover / TOR* paradigm — it is a manual lead-vehicle-braking paradigm. The mechanism (accelerator-release deceleration changing brake-timing variability) is analogous to what Experiment A wants to test, but the causal chain (automation disengagement -> TOR -> takeover -> braking-architecture-dependent recovery) has not been run end-to-end in this study.
- **Takeover-quality metrics and post-takeover stabilisation** are studied (L003, L009, L010), but as a function of *driver/scenario* variables (workload, experience, traffic density) — vehicle response architecture is not manipulated as an independent variable in these studies.
- **AEB architecture heterogeneity** (L011) is real and well characterised, but it is automation-controlled braking, not human-driver-executed braking after a handover. It establishes that the *physical* premise (architectures differ) is sound; it does not test the *human-fallback* premise.
- **EV acceleration and traffic risk** (L013) is a genuine empirical precedent for "propulsion/architecture capability changes risk exposure," but at the traffic-conflict level, not the post-hazard human-fallback-recovery level the project targets.

## 3. Closest competing frameworks

- **McDonald et al. (2019), Human Factors — "Toward Computational Simulations of Behavior During Automated Driving Takeovers"** (L010) is the closest broad framework identified. It reviews cognitive and control-theoretic models of takeover braking and steering, and explicitly treats existing manual-driving braking/steering models as plausibly transferable to takeover modeling. It does **not**, however, treat the vehicle's longitudinal-response mapping (regen/friction blending, brake delay, build-up shape) as a manipulated variable whose effect on recovery outcomes is tested — it takes the vehicle-response function as a fixed, largely unexamined part of the plant, not the object of study.
- **The one-pedal/two-pedal study (L004)** is the closest *mechanism-level* precedent. If a later, more targeted search finds a direct extension of this paradigm into an ADS-takeover context, that would materially weaken the gap and must be re-checked before Phase 1A is finalized.
- No paper found in this search combines all of: (a) manipulated vehicle longitudinal-response architecture, (b) an automation-to-human TOR/handover paradigm, (c) driver-vehicle familiarity/internal-model mismatch, and (d) a system-level recoverability/safety-envelope framing, in one study or framework.

## 4. What appears genuinely missing

- A study that **manipulates transient braking-response architecture** (not just presence/absence of regen, but shape: delay, build-up rate, blending nonlinearity) **as an independent variable inside a controlled ADS takeover/TOR paradigm**, holding driver, hazard, and maximum deceleration constant, and measuring standard recovery outcomes (TTC_min, stopping margin, impact speed).
- A framework that explicitly separates `T_authority`, `T_effective`, and `T_stable` and asks whether vehicle-response architecture shifts the gap between them.
- A "risk-state-escalation" framing of acceleration authority that is tied specifically to *human-fallback margin consumption* rather than general traffic-conflict frequency (L013 is traffic-conflict framing, not fallback-margin framing).
- Any published attempt at a unified `P(safe fallback) = f(vehicle response, driver-vehicle mismatch, TOR budget, human response, scenario criticality)` envelope model that integrates architecture-level vehicle variables (as opposed to only speed/mass) with handover-timing variables.

## 5. What is already done and must NOT be claimed as novel

- That TOR time budgets should be scenario/context-dependent rather than fixed (L001, L002, L007, L008) — already established.
- That fast takeover is not equivalent to safe recovery (L003) — already established; the project can cite this, not claim it.
- That post-takeover control takes several seconds to stabilise (L009) — already established as an empirical fact; the project should adopt, not "discover," this.
- That one-pedal/regen-heavy control changes emergency braking timing and variability (L004) — already established in a manual-driving/lead-vehicle-braking paradigm.
- That real production braking-control systems differ in deceleration/jerk signature independent of propulsion label (L011) — already established for AEB.
- That steering-gain/vehicle-dynamics adaptation is fast for small changes, slower with after-effects for large changes (L012) — already established.
- That EV acceleration capability is linked to traffic-conflict risk shifts (L013) — already established at the traffic-safety level.

## 6. Current novelty verdict

**MODERATE GAP.**

Rationale: the *physical* premise (architectures differ measurably; architecture changes emergency-braking timing in at least one paradigm) is well supported and not novel. The *specific integration* — vehicle-response architecture as a manipulated variable inside a controlled ADS TOR/handover paradigm, isolated from maximum deceleration, feeding into TTC/stopping-margin/impact-speed outcomes — was not found in this search. This is a real but narrower gap than the "STRONG / unified framework" framing in the original charter suggests. The System-level Human Fallback Safety Envelope (charter section 4.4 / mechanism layer 4) is not justified as a novelty claim at Phase 0 — see Section 6 of `PHASE0_1_REPORT.md`.

## 7. Confidence and remaining uncertainty

- This search used ~15 distinct queries across six themes via a general web/academic search tool, not a systematic database review (no Scopus/Web of Science protocol, no forward/backward citation chaining, no non-English literature). It is a **bounded plausibility check**, not a systematic review. A genuine novelty claim in a paper/thesis would require a documented systematic search protocol before this verdict can be upgraded past MODERATE.
- L006 (SAE regen-deceleration paper) numeric content is unverified — the paywalled full text was not retrieved; only the abstract-level claim (EVs differ, not all regen modes reach full stop) is confirmed.
- Several 2025-2026 items (L002, L007, L008, L009, L013) are very recent; some are preprints or single studies not yet cross-validated by independent replication.
- The negative result in Section 4 ("no direct hit found") is an absence-of-evidence finding from a bounded search, not proof of absence. Before any paper/thesis claims novelty, a formal systematic search (defined string, defined databases, PRISMA-style screening) is required.
