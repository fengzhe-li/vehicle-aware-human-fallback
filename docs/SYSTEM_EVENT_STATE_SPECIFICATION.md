# System event and state specification (R3B-0)

**Status:** implementation-independent specification, 2026-09-23. Since R3B (commit `028786b`), the longitudinal timeline (`HandoverTimeline`) and pre-control profile (`PreControlProfile`) are implemented; lateral and combined parts are not. Machine-readable event registry: `research/SYSTEM_EVENT_REGISTRY.csv`, validated by `src/provenance/registry.py::validate_events` and `tests/test_r3b0.py`.
**Clock origin:** t = 0 at `E_TOR` unless stated otherwise.
**Regulatory references:** UN R157 Rev.1 (01 series, source S02) and the 00 series in OJ L 82 (source S31). Clause numbers are given as read.

---

## 1. Events

Three rules are binding:
- **`E_TOR` ≠ `E_authority_transfer`.** A request does not move authority.
- **Manual_Start ≠ `E_authority_transfer`.** In D003, Manual_Start is the proxy for `E_driver_acknowledgement` only (blocker B7).
- **First channel activity ≠ `E_first_human_input`.** D003 control channels are not driver-only (blocker B17).

| Event | Meaning | Observable / latent | Source | Identifiable in D003 | Modelled in code | Unresolved |
|---|---|---|---|---|---|---|
| `E_TOR` | request / transition demand issued (R157 §2.2) | observable | S02, S18 | yes (protocol-resolved TOR; multi-TOR B1) | yes (t = 0) | partial (B1) |
| `E_driver_acknowledgement` | explicit HMI action accepting the takeover | observable | S17, S18 | yes, as event marker (Manual_Start) | no | authority meaning (B7) |
| `E_authority_transfer` | a human input takes priority on a channel; for R157 systems, deactivation / override under §6.2.5.1–6.2.5.2 and §6.3.1–6.3.3 (conditional on holding the steering control, threshold-based, **per channel**) | **latent** | S02, S31 | **no** | explicit input since R3B (see §5) | yes |
| `E_first_human_input` | first human input on any control, whatever its effect | **latent** | S28 | **no** (B17) | no | yes |
| `E_first_channel_activity` | first logged change on a control channel after TOR, any author | observable | S28 | yes, as a channel event only | no | no |
| `E_effective_human_control` | first human input that changes motion on a channel the human has authority over | **latent** | S28, S02 | **no** | assumed (brake step at `t_reaction`) | yes |
| `E_lane_change` | vehicle crosses into the adjacent lane (validated against lane id) | observable | S18 | yes | no | no |
| `E_handback` | control returned to automation; a protocol competing event / observation boundary | observable | S17, S18 | yes (first Manual_Stop after Manual_Start) | no | partial (B14) |
| `E_hazard_boundary^m` | manoeuvre-specific boundary (§3) | derived | S27, S18 | partial (station crossing only; geometry unknown, B10) | braking only | geometry |
| `E_MRM_start` | system starts an MRM: earliest 10 s after the transition demand without deactivation, or immediately on severe failure (R157 §5.4.4.1, §5.4.4.1.1) | observable in systems that log it | S02, S31, S15 | no (not in D003) | no | no |
| `E_MRM_complete` | MRM ends at standstill or deactivation (00 series §5.5.2–5.5.4; Rev.1 renumbers §5.5, not re-checked for these clauses) | observable in systems that log it | S02, S31 | no | no | no |

**Required ordering** (model invariants, not empirical claims):

`E_TOR ≤ E_authority_transfer(ch) ≤ E_effective_human_control(ch)`, and `E_first_human_input ≤ E_effective_human_control`.

In R157 systems, human input can **precede** authority transfer. Examples: an accelerator input below the override condition, or holding the wheel before attentiveness is confirmed. `E_first_human_input` is therefore **not** ordered relative to `E_authority_transfer`.

---

## 2. State variables by layer

Minimal set. Latent variables are marked **(L)**.

**Vehicle (A)**
- position `x`, speed `v`, longitudinal acceleration `a` (lateral `y`, `ψ` only when steering is in scope)
- command state per channel: `u_acc`, `u_brake`, `δ_sw`. These are the **arbitrated** commands actually applied, a function of automation and human commands and the authority state (C).
- braking state `b ∈ {none, delay, build-up, saturated}`; a model state, used only by the longitudinal model

**Human (B)**
- observed markers only: `t_ack` (Manual_Start), `t_lc` (validated lane change), `t_hb` (handback)
- latent: `t_first_input` **(L)**, `t_eff(ch)` **(L)**, human command `u_h(t)` **(L)**
- no workload, trust or internal-model state is introduced (not identifiable; see earlier phases)

**Transition (C)**
- automation mode `m ∈ {AUTOMATED, TRANSITION_DEMAND(escalation level), EMERGENCY_MANOEUVRE, MRM, DEACTIVATED}`
- authority state per channel `α_lon, α_lat ∈ {automation, human}` **(L in D003)**
- transition policy `π`: behaviour while `m = TRANSITION_DEMAND` (hold speed / decelerate / release propulsion), bounded for R157 systems by §5.4.3 (continue to operate; may reduce speed; no standstill unless required) and §5.3.1.1 (a demand above 5.0 m/s² is an emergency manoeuvre)

**Hazard (D)**
- gap to hazard `d`, closing speed `Δv`
- `TTC = d / Δv` (derived; defined only for `Δv > 0`)
- friction `μ` (environment)
- geometry: hazard width `w_h`, lateral position `y_h`, length `L_h`
- target-lane gap state `G(t)`
- escape-path availability `E ∈ {0, 1}` (derived from geometry, `G` and vehicle limits)

Grade and lane width are environment parameters, added only when a scenario needs them.

---

## 3. Manoeuvre-specific `T_available` and `T_required`

**Bookkeeping convention (adopted; revises the R3A formulation).** `T_available^m` is the time from `E_TOR` to the boundary `B^m` under a **constant-velocity reference extrapolation** of the state at TOR. **All** transition-policy, human and vehicle dynamics go into `T_required^m`.

This convention:
- keeps `T_available` kinematic and observable (it equals TTC at TOR for a stationary obstacle)
- matches the existing braking slice
- avoids counting `a_pre` twice

The R3A recommendation `T_available^m(policy) = t_crit^m − t_TOR` is an equivalent reformulation, but it would move policy effects into `T_available`. It is not used.

### Braking
- **Clock start:** `E_TOR`.
- **Boundary `B^brake`:** the ego front reaches the hazard station (`d = 0`) with `v > 0`, for an obstacle that fully blocks the ego lane.
- **`T_available^brake`** = `d(0) / Δv(0)` = TTC at TOR (stationary or constant-speed obstacle). **Observable**, as long as the reference extrapolation is stated.
- **`T_required^brake(θ)`** = the smallest `T_available^brake` for which the sequence stops with `d ≥ 0` (optionally with a margin). The sequence is: policy `π` on `[0, t_auth^lon)`, then human command `u_brake(t)` from `t_eff^lon`, then vehicle response `t2`, `t3`, and `a_eff = min(u_brake · a_max, μg)` (R3B; the R3B-0 draft wrote `min(a_max, μg)` with u applied afterwards, identical for u = 1). **Derived.**
- **Recovery condition:** `T_available^brake ≥ T_required^brake`.
- **Assumptions:**
  - 1-D, in-lane, fully blocking hazard
  - known `π`
  - `t_auth^lon` and `t_eff^lon` supplied as inputs; they are latent in D003
  - a specified `u_brake(t)`; the current slice uses 1
  - μ-consistent `a_eff`

### Steering / evasion
- **Clock start:** `E_TOR`.
- **Boundary `B^steer`:** the ego reaches the hazard station while the lateral overlap `|y − y_h| < (w_e + w_h)/2 + c` persists (c = clearance).
- **`T_available^steer`** = the constant-velocity reference time to the hazard station. It has the same numerical value as braking for a stationary obstacle, but a different boundary. It is **defined only if `E = 1`**, i.e. the target lane stays free over the manoeuvre window. If `E = 0`, steering recovery is infeasible whatever the time.
- **`T_required^steer(θ)`** = `t_eff^lat + t_lat(y_req; lateral dynamics; a_y ≤ μg)`. Here `t_eff^lat` requires lateral authority (R157 §6.3.1: steering override needs force and duration thresholds) and `y_req` follows from the geometry. **Derived.**
- **Recovery condition:** `E = 1 ∧ T_available^steer ≥ T_required^steer`.
- **Assumptions:**
  - no concurrent braking (otherwise the manoeuvre is combined)
  - known geometry and lane state
  - a lateral model with documented parameters (none exists; not built here)
- **D003:** `E_lane_change` is observable, but `y_req`, `G(t)`, geometry and steering authorship are not, so `T_required^steer` **cannot be derived**.

### Combined braking + steering
**Undefined.** It needs friction-circle coupling, a trajectory choice and a lateral model; the evidence and model are insufficient.

---

## 4. What the specification forbids
- one universal `T_available`
- TOR-based authority
- Manual_Start-based authority
- channel-activity-based human input
- TTC as the complete hazard state
- steering conclusions drawn from the braking slice

## 5. Relation to the code

**Superseded in R3B (commit `028786b`).** Since then, `HandoverTimeline` carries `t_authority`, `t_effective` and `t_first_input` as separate inputs, and `PreControlProfile` applies the policy before authority transfer and vehicle-only response after it (`docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md` §1).

*Pre-R3B record (as written in R3B-0):* the `src/handover/models.py` docstring said "T_authority = 0 (TOR issuance, nominal); T_effective = t_reaction", and `get_control_authority` switched at `t_reaction`. Authority transfer, first input and effective control were therefore one instant. The legacy path still reproduces this for W0/W1 only.
