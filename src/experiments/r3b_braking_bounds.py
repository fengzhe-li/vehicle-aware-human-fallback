"""Phase R3B: interval-bounded longitudinal braking recoverability slice.

Deterministic, braking-only, stationary in-lane obstacle, full braking command after
effective human control. NOT a probability model, NOT a claim that human fallback
succeeds, NOT a recoverability envelope. Labels refer only to this braking-only model:
ROBUSTLY SATISFIED / PARAMETER-SENSITIVE / ROBUSTLY UNSATISFIED.

Conventions (docs/SYSTEM_EVENT_STATE_SPECIFICATION.md):
- clock starts at TOR (t = 0);
- T_available^brake = TTC at TOR under a constant-velocity reference (scenario value);
- T_required^brake = (D_stop + standstill margin) / v0, with all transition-policy,
  human and vehicle dynamics inside D_stop (src/metrics/oracle.py);
- recoverability margin = T_available - T_required (seconds); distance margin = v0 * that.

Interval propagation: no distributions. Bounds are the exact minimum / maximum over the
parameter box, obtained by evaluating every corner and verified against a dense interior
grid (the stopping distance is monotone in each parameter, so extremes lie on corners).

Usage:
    python -m src.experiments.r3b_braking_bounds [output_dir]
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import sys
from typing import Dict, List, Tuple

import numpy as np

from src.experiments.r2a_event_vehicle_descriptives import git_state
from src.handover.models import HandoverTimeline, PreControlProfile
from src.metrics.braking_derivatives import stopping_distance_and_gradient
from src.metrics.oracle import braking_t_required, stopping_distance_r3b_analytical
from src.scenarios.models import ScenarioConfig
from src.simulation.simulator import MinimalSimulator
from src.vehicle.models import GRAVITY, VehicleResponseConfig, effective_braking_deceleration

DEFAULT_OUTPUT = "results/R3B_braking_bounds"
EPA_TABLE = "research/data_matrix/r3a_epa_coastdown_deceleration.csv"
REGISTRY = "research/PARAMETER_PROVENANCE_REGISTRY.csv"
SLICE_LABEL = "Interval-bounded longitudinal braking recoverability slice"

SOURCE, ASSUMPTION, BLOCKED = "SOURCE-SUPPORTED", "EXPLICIT ASSUMPTION INTERVAL", "BLOCKED"

# ---------------------------------------------------------------------------
# Frozen scenario grid (fixed before any result was computed)
# ---------------------------------------------------------------------------

SPEEDS_KMH = {
    60: "original UN R157 (00 series) ALKS speed limit, S31 §5.2.3.1",
    100: "D003 motorway speed limit (S17)",
    130: "UN R157 Rev.1 maximum ALKS speed, S02 §5.2.3.1",
}
TTC_S = {
    2.0: "short budget; UN R157 Annex 3 uses TTC 2 s as its longitudinal danger threshold (S02)",
    3.0: "intermediate short budget (grid fill)",
    5.0: "intermediate budget (grid fill)",
    7.0: "D003 protocol TOR at TTC 7 s (S17)",
    10.0: "long budget (grid fill); not a regulatory TTC",
}
FRICTION = {
    1.0: "reference road friction used by the UN R157 Annex 3 benchmark (S02); non-binding for a_max <= 9.81",
    0.5: "reduced-friction scenario value (assumption, not a wet-road measurement); binding: mu*g = 4.905 m/s2",
}

# ---------------------------------------------------------------------------
# Frozen parameter intervals with class and provenance
# ---------------------------------------------------------------------------

PARAMETERS = {
    "t1": dict(cls=ASSUMPTION, low=1.15, high=3.0, unit="s", registry="P02",
               label="assumption interval for sensitivity analysis: TOR -> effective human braking. Lower end = "
                     "UN R157 Annex 3 attentive-driver benchmark (0.4 s + 0.75 s, S02; a regulatory reference, not "
                     "a takeover measurement); upper end = scenario choice. Not t_button, not Manual_Start, not the "
                     "meta-analysis takeover time."),
    "t2": dict(cls=SOURCE, low=0.05, high=0.17, unit="s", registry="P08",
               label="hydraulic brake actuation delay, instrumented hard braking (S20); within the R13-H 0.6 s bound (S01)"),
    "t3": dict(cls=ASSUMPTION, low=0.3, high=1.2, unit="s", registry="P09",
               label="assumption interval for sensitivity analysis: deceleration build-up (human x vehicle). Informed "
                     "by S02 benchmark 0.6 s and S04 non-professional pedal build-up (0.83 s mean, up to 1.26 s); "
                     "not a measured takeover build-up distribution"),
    "a_max": dict(cls=SOURCE, low=6.43, high=9.1, unit="m/s2", registry="P10",
                  label="dry-road braking capability: R13-H approval floor 6.43 (S01) to measured ~9.1 (S04)"),
    "a_drag": dict(cls=SOURCE, low=None, high=None, unit="m/s2", registry="P03",
                   label="coast/drag deceleration, EPA road-load 5th-95th percentile at the scenario speed (S07)"),
    "f_auth": dict(cls=ASSUMPTION, low=0.0, high=1.0, unit="-", registry="P24",
                   label="assumption: authority transfer at fraction f of the TOR -> effective-control interval "
                         "(R157 permits deactivation by holding the steering control before braking, §6.2.5.2, or "
                         "by a braking override, §6.3.2); not identified from D003"),
    "a_sup": dict(cls=ASSUMPTION, low=1.0, high=3.0, unit="m/s2", registry="P25",
                  label="assumption interval for P2 supported deceleration; kept below the UN R157 emergency-manoeuvre "
                        "threshold of 5.0 m/s2 (S02 §5.3.1.1); no direct source for its magnitude"),
}
SUCCESS = {
    "standstill_margin_m": 2.0,
    "u_brake": 1.0,
    "class_standstill_margin": ASSUMPTION,
    "class_u_brake": "MODEL CONDITION (definition of this slice, not evidence)",
    "definition": "speed reaches zero at least 2.0 m before the stationary obstacle; T_available = TTC at TOR "
                  "(constant-velocity reference); T_required = (D_stop + 2.0 m) / v0",
}
BLOCKED_INPUTS = {
    "u_eff": "human takeover braking-strength distribution (P14)",
    "j_brake": "braking jerk as an independent input (P13)",
    "a_auto_max": "ISO 15622 ACC numeric limits (P19, secondary only)",
    "TOT": "abstract-only takeover-time distribution (P21)",
    "a_engine_brake": "engine braking magnitude (P05)",
    "v_rolloff": "regen low-speed roll-off (P15)",
    "a_liftoff": "lift-off regenerative deceleration (P04; excluded, so P1 uses drag only)",
    "d003_vehicle": "unidentified D003 vehicle properties (V21)",
}

# ---------------------------------------------------------------------------
# Counterfactual policy branches (not production policies)
# ---------------------------------------------------------------------------

BRANCHES = {
    "P0|AUTH_AT_EFFECTIVE": dict(policy="P0", auth="AT_EFFECTIVE", params=["t1", "t2", "t3", "a_max", "a_drag"],
                                 desc="automation holds speed (net 0) until authority transfer at effective human "
                                      "braking; equals the legacy W0 pre-control behaviour"),
    "P0|AUTH_UNCERTAIN": dict(policy="P0", auth="UNCERTAIN", params=["t1", "t2", "t3", "a_max", "a_drag", "f_auth"],
                              desc="automation holds speed until authority transfer at f*t1, f in [0, 1]; drag only "
                                   "afterwards"),
    "P1": dict(policy="P1", auth="IRRELEVANT", params=["t1", "t2", "t3", "a_max", "a_drag"],
               desc="automation ceases propulsion at TOR; drag only until effective braking. Authority timing has no "
                    "longitudinal effect because both sides of it are drag. Lift-off regen / engine braking excluded, "
                    "so this is the powertrain-conservative passive case"),
    "P2|AUTH_AT_EFFECTIVE": dict(policy="P2", auth="AT_EFFECTIVE", params=["t1", "t2", "t3", "a_max", "a_drag", "a_sup"],
                                 desc="automation applies net deceleration a_sup until effective human braking"),
    "P2|AUTH_UNCERTAIN": dict(policy="P2", auth="UNCERTAIN",
                              params=["t1", "t2", "t3", "a_max", "a_drag", "a_sup", "f_auth"],
                              desc="automation applies a_sup until authority transfer at f*t1, then drag only"),
}
# P0 / P2 with authority at TOR are identical to P1 by construction and are not repeated.


def drag_interval(v_kmh: int, path: str = EPA_TABLE) -> Tuple[float, float]:
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["group"] == "all" and int(r["speed_kmh"]) == v_kmh:
                return float(r["p05_mps2"]), float(r["p95_mps2"])
    raise KeyError(f"no EPA drag row for {v_kmh} km/h")


def intervals_for(v_kmh: int) -> Dict[str, Tuple[float, float]]:
    out = {k: (p["low"], p["high"]) for k, p in PARAMETERS.items() if k != "a_drag"}
    out["a_drag"] = drag_interval(v_kmh)
    return out


def profile(branch: str, p: Dict[str, float]) -> Tuple[HandoverTimeline, PreControlProfile]:
    """Map a parameter point to the explicit timeline and pre-control profile of a branch."""
    b = BRANCHES[branch]
    t1 = p["t1"]
    if b["policy"] == "P1":
        return HandoverTimeline(0.0, t1), PreControlProfile(p["a_drag"], p["a_drag"], "P1 passive release")
    f = 1.0 if b["auth"] == "AT_EFFECTIVE" else p["f_auth"]
    a_before = 0.0 if b["policy"] == "P0" else p["a_sup"]
    return HandoverTimeline(f * t1, t1), PreControlProfile(a_before, p["a_drag"], branch)


def t_required(v0: float, mu: float, branch: str, p: Dict[str, float]) -> float:
    tl, pc = profile(branch, p)
    d = stopping_distance_r3b_analytical(v0, p["a_max"], tl.t_effective, p["t2"], p["t3"], tl.t_authority,
                                         pc.a_before_authority, pc.a_after_authority, SUCCESS["u_brake"], mu)
    return braking_t_required(d, v0, SUCCESS["standstill_margin_m"])


# Classification tolerance (gate decision, docs/R3B_GATE_REVIEW.md §3). The classified margins are
# TIME margins in seconds (T_available - T_required), never distance margins, so the tolerance
# is a time: 0.01 s exceeds the closed-form vs simulator verification tolerance (<= 0.0075 s).
EPSILON_S = 0.01
MARGIN_UNITS = "s"


def classify(margin_worst_s: float, margin_best_s: float, epsilon_s: float = EPSILON_S) -> str:
    """Braking-only model labels from TIME margins (seconds).

    ROBUSTLY SATISFIED only if the worst margin exceeds +epsilon; ROBUSTLY UNSATISFIED only if the
    best margin is below -epsilon; everything touching the +-epsilon band is PARAMETER-SENSITIVE.
    """
    if epsilon_s < 0:
        raise ValueError("epsilon_s must be non-negative")
    if margin_worst_s > epsilon_s:
        return "ROBUSTLY SATISFIED"
    if margin_best_s < -epsilon_s:
        return "ROBUSTLY UNSATISFIED"
    return "PARAMETER-SENSITIVE"


def boundary_flag(margin_worst_s: float, margin_best_s: float, epsilon_s: float = EPSILON_S) -> bool:
    """True if either bound lies within the +-epsilon band (seconds): numerically at the boundary."""
    return abs(margin_worst_s) <= epsilon_s or abs(margin_best_s) <= epsilon_s


class MonotonicityGuardError(RuntimeError):
    """Endpoint/corner bounds are not valid: a true constrained-bound search is required."""


GUARD_MAX_POINTS = 1_000_000  # dense-grid budget per case
GUARD_TOL = 1e-9              # |dT/dp| below this is treated as zero (sign-neutral)


def _branch_coords(branch: str, grid: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Map branch parameters to (t1, f, a1, a2) of the derivative model."""
    b = BRANCHES[branch]
    t1 = grid["t1"]
    if b["policy"] == "P1":
        return dict(f=np.zeros_like(t1), a1=grid["a_drag"], a2=grid["a_drag"])
    f = np.ones_like(t1) if b["auth"] == "AT_EFFECTIVE" else grid["f_auth"]
    a1 = np.zeros_like(t1) if b["policy"] == "P0" else grid["a_sup"]
    return dict(f=f, a1=a1, a2=grid["a_drag"])


def _guard_scan(v0: float, mu: float, branch: str, iv: Dict[str, Tuple[float, float]]):
    """Guard scan without raising: (report, {coordinate: violation message})."""
    names = BRANCHES[branch]["params"]
    n = max(3, int(GUARD_MAX_POINTS ** (1.0 / len(names))))
    axes = [np.linspace(*iv[k], n) for k in names]
    mesh = dict(zip(names, np.meshgrid(*axes, indexing="ij")))
    c = _branch_coords(branch, mesh)
    g = stopping_distance_and_gradient(v0, mesh["a_max"], mu, mesh["t1"], mesh["t2"], mesh["t3"],
                                       c["f"], c["a1"], c["a2"])
    pol = BRANCHES[branch]["policy"]
    deriv = {"t1": g["t1"], "t2": g["t2"], "t3": g["t3"], "a_max": g["a_max"],
             "a_drag": g["a1"] + g["a2"] if pol == "P1" else g["a2"]}
    if "a_sup" in names:
        deriv["a_sup"] = g["a1"]
    if "f_auth" in names:
        deriv["f_auth"] = g["f"]
    report = {"resolution_points_per_dim": n, "grid_points": int(n ** len(names)), "coordinates": {}}
    violations = {}
    for ax, k in enumerate(names):
        d = deriv[k] / v0  # dT/dp
        pos, neg = (d > GUARD_TOL).any(axis=ax), (d < -GUARD_TOL).any(axis=ax)
        bad = int((pos & neg).sum())
        signed = d[np.abs(d) > GUARD_TOL]
        report["coordinates"][k] = {"dT_dp_min": float(d.min()), "dT_dp_max": float(d.max()),
                                    "min_abs_nonzero": float(np.abs(signed).min()) if signed.size else 0.0,
                                    "lines_with_sign_reversal": bad}
        if bad:
            violations[k] = (f"{k}: {bad} grid lines with an interior sign reversal of dT/d{k} "
                             f"(range {d.min():+.4f} .. {d.max():+.4f})")
    report["monotone"] = not violations
    return report, violations


def monotonicity_guard(v0: float, mu: float, branch: str, iv: Dict[str, Tuple[float, float]]) -> Dict[str, object]:
    """Fail-closed check that T_required is monotone along every coordinate line of the box.

    Uses the exact analytic partial derivatives (src/metrics/braking_derivatives.py) evaluated on a
    dense grid including all endpoints (n points per dimension, n^d <= GUARD_MAX_POINTS). A
    coordinate passes if, along every axis-parallel grid line, dT/dp never takes both signs (values
    with |dT/dp| <= GUARD_TOL are sign-neutral). This detects interior sign reversals, not only
    endpoint differences. Resolution limit: a reversal confined between adjacent grid nodes of every
    line is not resolved; the reported minimum derivative margin shows how close each coordinate is.
    Raises MonotonicityGuardError on any violation.
    """
    report, violations = _guard_scan(v0, mu, branch, iv)
    if violations:
        raise MonotonicityGuardError(
            f"monotonicity guard failed for v0={v0:.3f} m/s, mu={mu}, branch={branch}: " + "; ".join(violations.values())
            + ". Endpoint/corner bounds are NOT valid on this domain; a true constrained-bound search is required.")
    return report


def interior_extrema_check(fn, box: Dict[str, Tuple[float, float]], corner_min: float, corner_max: float,
                           n: int = 4, tol: float = 1e-9) -> Dict[str, object]:
    """Independent cross-check: do any interior grid points (n per dimension) fall outside the corner bounds?

    ok is False if an interior extremum is missed by the endpoint/corner bounds.
    """
    names = list(box)
    vals = [fn(dict(zip(names, combo))) for combo in itertools.product(*[np.linspace(*box[k], n) for k in names])]
    return {"ok": bool(min(vals) >= corner_min - tol and max(vals) <= corner_max + tol),
            "grid_min": float(min(vals)), "grid_max": float(max(vals)), "points_per_dim": n}


def bound(v0: float, mu: float, branch: str, iv: Dict[str, Tuple[float, float]]) -> Dict[str, object]:
    """Exact box bounds by corner evaluation, valid only inside the guarded monotone domain."""
    guard = monotonicity_guard(v0, mu, branch, iv)  # raises MonotonicityGuardError if not monotone
    names = BRANCHES[branch]["params"]
    corners = []
    for combo in itertools.product(*[iv[n] for n in names]):
        p = dict(zip(names, combo))
        corners.append((t_required(v0, mu, branch, p), p))
    lo = min(corners, key=lambda c: c[0])
    hi = max(corners, key=lambda c: c[0])
    ok = interior_extrema_check(lambda p: t_required(v0, mu, branch, p), {n: iv[n] for n in names},
                                lo[0], hi[0])["ok"]
    mid = {n: 0.5 * (iv[n][0] + iv[n][1]) for n in names}
    return {"t_req_min": lo[0], "t_req_max": hi[0], "t_req_mid": t_required(v0, mu, branch, mid),
            "argmin": lo[1], "argmax": hi[1], "mid": mid, "dense_check_ok": bool(ok), "n_corners": len(corners),
            "guard": guard}


METHOD_ENDPOINT = "monotone_endpoint_bound"
METHOD_T1_STATIONARY = "stationary_point_t1_bound"
T1_SCAN_POINTS = 2001  # sign-change scan resolution for dT/dt1 along each line
T1_ROOT_XTOL = 1e-12   # brentq tolerance on t1 (s)


class SupplementBoundError(RuntimeError):
    """The stationary-point t1 method could not establish valid bounds (fail closed)."""


def dT_dt1(v0: float, mu: float, branch: str, p: Dict[str, float]) -> float:
    """Exact dT_required/dt1 (s/s) at a parameter point, from the analytic derivative module."""
    one = {k: np.asarray(x, dtype=float) for k, x in p.items()}
    c = _branch_coords(branch, one)
    g = stopping_distance_and_gradient(v0, one["a_max"], mu, one["t1"], one["t2"], one["t3"],
                                       c["f"], c["a1"], c["a2"])
    return float(g["t1"]) / v0


def t1_line_candidates(v0: float, mu: float, branch: str, others: Dict[str, float], t1_lo: float, t1_hi: float,
                       derivative=None) -> List[float]:
    """Candidate t1 values on one line: both endpoints and every interior root of dT/dt1.

    Roots are bracketed by sign changes of the exact derivative on a T1_SCAN_POINTS scan and refined with
    brentq. Scan nodes where |dT/dt1| <= GUARD_TOL are added as candidates too (tangencies). The caller
    verifies that no scanned T value lies outside the candidate extremes; otherwise it fails closed.
    """
    from scipy.optimize import brentq

    h = derivative or (lambda t1: dT_dt1(v0, mu, branch, dict(others, t1=t1)))
    ts = np.linspace(t1_lo, t1_hi, T1_SCAN_POINTS)
    hs = np.array([h(t) for t in ts])
    cands = [t1_lo, t1_hi] + [float(t) for t, x in zip(ts, hs) if abs(x) <= GUARD_TOL]
    for a, b, ha, hb in zip(ts[:-1], ts[1:], hs[:-1], hs[1:]):
        if ha * hb < 0:
            try:
                cands.append(float(brentq(h, a, b, xtol=T1_ROOT_XTOL)))
            except (ValueError, RuntimeError) as exc:
                raise SupplementBoundError(f"stationary-point solver failed on [{a}, {b}]: {exc}") from exc
    return sorted(set(cands))


def bound_supplement(v0: float, mu: float, branch: str, iv: Dict[str, Tuple[float, float]],
                     derivative_factory=None) -> Dict[str, object]:
    """Bounds for the t1 supplement domain.

    - If the guard passes: the unchanged endpoint/corner method (METHOD_ENDPOINT).
    - If the guard fails only in t1: every other bounded parameter is monotone along every guarded line,
      so the extremes lie at the corners of the other parameters; along each such line, T is evaluated at
      both t1 endpoints and at every interior stationary point dT/dt1 = 0 (METHOD_T1_STATIONARY).
    - Otherwise (any other non-monotone coordinate, or an unverifiable line): fail closed.
    """
    report, violations = _guard_scan(v0, mu, branch, iv)
    if not violations:
        return dict(bound(v0, mu, branch, iv), method=METHOD_ENDPOINT)
    if set(violations) != {"t1"}:
        raise MonotonicityGuardError(
            f"supplement: non-monotone coordinate(s) other than t1 for v0={v0:.3f} m/s, mu={mu}, branch={branch}: "
            + "; ".join(violations.values()) + ". Neither the endpoint nor the stationary-point t1 method applies; "
            "a general constrained-bound search is required.")
    names = BRANCHES[branch]["params"]
    others = [k for k in names if k != "t1"]
    t1_lo, t1_hi = iv["t1"]
    fn = lambda p: t_required(v0, mu, branch, p)
    best_lo, best_hi, n_stationary = None, None, 0
    for combo in itertools.product(*[iv[k] for k in others]):
        o = dict(zip(others, combo))
        deriv = derivative_factory(o) if derivative_factory else None
        cands = t1_line_candidates(v0, mu, branch, o, t1_lo, t1_hi, deriv)
        n_stationary += len(cands) - 2
        vals = [(fn(dict(o, t1=t)), dict(o, t1=t)) for t in cands]
        lo, hi = min(vals, key=lambda x: x[0]), max(vals, key=lambda x: x[0])
        scan = [fn(dict(o, t1=t)) for t in np.linspace(t1_lo, t1_hi, 201)]
        if min(scan) < lo[0] - 1e-9 or max(scan) > hi[0] + 1e-9:
            raise SupplementBoundError(f"supplement: stationary-point candidates do not bound the scanned line "
                                       f"{o} for {branch}; cannot establish valid bounds")
        best_lo = lo if best_lo is None or lo[0] < best_lo[0] else best_lo
        best_hi = hi if best_hi is None or hi[0] > best_hi[0] else best_hi
    chk = interior_extrema_check(fn, {k: iv[k] for k in names}, best_lo[0], best_hi[0])
    if not chk["ok"]:
        raise SupplementBoundError(f"supplement: interior grid point outside stationary-point bounds for {branch}")
    mid = {k: 0.5 * (iv[k][0] + iv[k][1]) for k in names}
    return {"t_req_min": best_lo[0], "t_req_max": best_hi[0], "t_req_mid": fn(mid), "argmin": best_lo[1],
            "argmax": best_hi[1], "mid": mid, "dense_check_ok": True, "n_lines": 2 ** len(others),
            "n_interior_stationary_points": n_stationary, "guard": report, "method": METHOD_T1_STATIONARY,
            "non_monotone": sorted(violations)}


def sensitivity(v0: float, mu: float, branch: str, iv: Dict[str, Tuple[float, float]], mid: Dict[str, float]) -> List[Dict]:
    """Physical sensitivity (elasticity at the midpoint) vs epistemic swing (one-at-a-time interval width)."""
    t_mid = t_required(v0, mu, branch, mid)
    lo_all = t_required(v0, mu, branch, {n: iv[n][0] for n in mid})
    rows = []
    for n in mid:
        h = 1e-6 * max(abs(mid[n]), 1e-3)
        up, dn = dict(mid, **{n: mid[n] + h}), dict(mid, **{n: mid[n] - h})
        d = (t_required(v0, mu, branch, up) - t_required(v0, mu, branch, dn)) / (2 * h)
        swing = t_required(v0, mu, branch, dict(mid, **{n: iv[n][1]})) - t_required(v0, mu, branch, dict(mid, **{n: iv[n][0]}))
        rows.append({"parameter": n, "dT_dp_at_mid": d, "elasticity_at_mid": d * mid[n] / t_mid if mid[n] else 0.0,
                     "swing_s": swing, "abs_swing_s": abs(swing)})
    tot = sum(r["abs_swing_s"] for r in rows) or 1.0
    for r in rows:
        r["share_of_oat_swing"] = r["abs_swing_s"] / tot
    return rows


def cross_check(v0: float, mu: float, branch: str, points: List[Dict[str, float]], sim: MinimalSimulator) -> float:
    """Max relative difference of D_stop between closed form and simulator over the given points."""
    worst = 0.0
    for p in points:
        tl, pc = profile(branch, p)
        veh = VehicleResponseConfig(t_delay=p["t2"], t_buildup=p["t3"], a_max=p["a_max"])
        res = sim.simulate(ScenarioConfig(v0=v0, tor_lead_time=100.0, road_friction=mu), veh, timeline=tl, pre_control=pc)
        d = stopping_distance_r3b_analytical(v0, p["a_max"], tl.t_effective, p["t2"], p["t3"], tl.t_authority,
                                             pc.a_before_authority, pc.a_after_authority, SUCCESS["u_brake"], mu)
        worst = max(worst, abs(res.outcomes.x_stop_full - d) / d)
    return worst


def make_figure(bound_rows: List[Dict], path: str) -> None:
    """Small multiples (speed x friction): T_required interval per branch vs the TTC grid."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, ink2, bar, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6", "#d8d7d0"
    speeds, mus, branches = list(SPEEDS_KMH), list(FRICTION), list(BRANCHES)
    fig, axes = plt.subplots(len(mus), len(speeds), figsize=(12, 5.6), sharex=True, sharey=True, facecolor=surface)
    for i, mu in enumerate(mus):
        for j, v in enumerate(speeds):
            ax = axes[i][j]
            ax.set_facecolor(surface)
            for ttc in TTC_S:
                ax.axvline(ttc, color=grid, lw=1, ls="--", zorder=0)
            for k, br in enumerate(branches):
                r = next(b for b in bound_rows if b["speed_kmh"] == v and b["mu"] == mu and b["branch"] == br)
                y = len(branches) - 1 - k
                ax.barh(y, r["t_required_max_s"] - r["t_required_min_s"], left=r["t_required_min_s"], height=0.5,
                        color=bar, zorder=2)
                ax.plot([r["t_required_mid_s"]] * 2, [y - 0.25, y + 0.25], color=ink, lw=2, zorder=3)
            ax.set_title(f"{v} km/h, mu = {mu}", fontsize=10, color=ink)
            ax.set_yticks(range(len(branches)), branches[::-1], fontsize=8, color=ink2)
            ax.tick_params(colors=ink2, labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(grid)
            if i == len(mus) - 1:
                ax.set_xlabel("T_required^brake interval (s); dashed lines = TTC grid", fontsize=8, color=ink2)
    fig.suptitle("Interval-bounded longitudinal braking recoverability slice: T_required bounds (bar) and "
                 "midpoint (tick). Braking-only model; not a probability.", fontsize=10, color=ink)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=surface, metadata={"Software": None})
    plt.close(fig)


CROSS_CHECK_REL_TOL = 1e-3  # A0 tolerance

VALIDITY_ENVELOPE = [
    "stationary longitudinal hazard fully blocking the ego lane",
    "no usable escape path: braking-only analysis",
    "deterministic point-mass longitudinal approximation (no tyre, load-transfer or ABS dynamics)",
    "full braking command (u = 1) after effective human control: capability bound, not observed human braking",
    "zero acceleration during actuation delay and drag neglected after effective control (conservative)",
    "drag held at its value at v0 during pre-control (slightly optimistic; <= 0.6 m/s2 over <= 3 s)",
    "authority-transfer timing, t1 and t3 are explicit assumptions, not identified from any data",
    "no detailed lateral dynamics and no human steering strategy",
    "no probabilistic driver model; interval bounds are not confidence intervals",
    "no D003 vehicle calibration; D003 values are used only to choose scenario values",
    "no claim about production automated-driving systems; P0/P1/P2 are counterfactual branches",
]


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _write(path: str, rows: List[Dict]) -> None:
    """Write rows as CSV. Columns = union of all row keys in first-seen order (rows may differ by branch,
    e.g. guard columns for f_auth / a_sup); missing fields are left empty."""
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(rows)


def _r(x, n=4):
    return round(float(x), n)


def evaluate_supplement(t1_high: float) -> Dict[Tuple[int, float, str], Dict[str, object]]:
    """Bound every case on the t1-supplement domain. Never raises for a single case: a case that cannot be
    bounded (guard or solver failure) is recorded as NOT BOUNDED with its error, so the supplement can
    neither block nor alter the main-domain results."""
    out = {}
    for v in SPEEDS_KMH:
        iv = intervals_for(v)
        t1hi = dict(iv, t1=(iv["t1"][0], t1_high))
        for mu in FRICTION:
            for br in BRANCHES:
                try:
                    out[(v, mu, br)] = bound_supplement(v / 3.6, mu, br, t1hi)
                except (MonotonicityGuardError, SupplementBoundError) as exc:
                    out[(v, mu, br)] = {"method": "NOT BOUNDED", "error": str(exc)}
    return out


def attach_supplement(bound_rows: List[Dict], res_rows: List[Dict], supplement: Dict) -> None:
    """Add supplement columns to already computed main-domain rows (main-domain fields are not modified)."""
    for row in bound_rows:
        sb = supplement[(row["speed_kmh"], row["mu"], row["branch"])]
        row["t_required_min_if_t1_high_4s"] = _r(sb["t_req_min"]) if "t_req_min" in sb else ""
        row["t_required_max_if_t1_high_4s"] = _r(sb["t_req_max"]) if "t_req_max" in sb else ""
        row["t1_high_4s_bound_method"] = sb["method"]
    for row in res_rows:
        sb = supplement[(row["v0_kmh"], row["mu"], row["branch"])]
        row["classification_if_t1_high_4s"] = (classify(row["ttc_s"] - sb["t_req_max"], row["ttc_s"] - sb["t_req_min"])
                                               if "t_req_max" in sb else "NOT BOUNDED")
        row["t1_high_4s_bound_method"] = sb["method"]


def run(output_dir: str = DEFAULT_OUTPUT, t1_high_sensitivity: float = 4.0) -> Dict[str, object]:
    os.makedirs(output_dir, exist_ok=True)
    blocked_used = set(BLOCKED_INPUTS) & {n for b in BRANCHES.values() for n in b["params"]}
    if blocked_used:
        raise RuntimeError(f"blocked parameters entered the computation: {blocked_used}")

    # 1. frozen definitions, written before any result
    param_rows = []
    for v in SPEEDS_KMH:
        for k, (lo, hi) in intervals_for(v).items():
            p = PARAMETERS[k]
            param_rows.append({"speed_kmh": v, "parameter": k, "class": p["cls"], "low": lo, "high": hi,
                               "unit": p["unit"], "registry_id": p["registry"], "provenance": p["label"]})
    _write(os.path.join(output_dir, "parameter_intervals.csv"), param_rows)
    scen_rows = [{"scenario_id": f"v{v}_mu{mu}_{br}_ttc{ttc}", "v0_kmh": v, "v0_mps": _r(v / 3.6), "ttc_s": ttc,
                  "hazard_distance_m": _r(v / 3.6 * ttc, 2), "mu": mu, "branch": br,
                  "policy": BRANCHES[br]["policy"], "authority_assumption": BRANCHES[br]["auth"],
                  "why_speed": SPEEDS_KMH[v], "why_ttc": TTC_S[ttc], "why_mu": FRICTION[mu]}
                 for v in SPEEDS_KMH for mu in FRICTION for br in BRANCHES for ttc in TTC_S]
    _write(os.path.join(output_dir, "scenario_table.csv"), scen_rows)

    # 2. bounds, sensitivity, cross-check
    sim = MinimalSimulator(dt=0.001)
    bound_rows, sens_rows, xc_rows, res_rows, guard_rows = [], [], [], [], []
    bounds = {}
    for v in SPEEDS_KMH:
        v0 = v / 3.6
        iv = intervals_for(v)
        for mu in FRICTION:
            for br in BRANCHES:
                b = bound(v0, mu, br, iv)
                if not b["dense_check_ok"]:
                    raise RuntimeError(f"interior extremum found for {v}, {mu}, {br}: corner propagation invalid")
                bounds[(v, mu, br)] = b
                xerr = cross_check(v0, mu, br, [b["argmin"], b["argmax"], b["mid"]], sim)
                if xerr > CROSS_CHECK_REL_TOL:
                    raise RuntimeError(f"closed form and simulator disagree ({xerr:.2e}) for {v}, {mu}, {br}")
                xc_rows.append({"speed_kmh": v, "mu": mu, "branch": br, "points": "argmin;argmax;midpoint",
                                "max_rel_diff_d_stop": f"{xerr:.3e}", "tolerance": CROSS_CHECK_REL_TOL})
                a_eff = (effective_braking_deceleration(iv["a_max"][0], 1.0, mu),
                         effective_braking_deceleration(iv["a_max"][1], 1.0, mu))
                guard_rows.append({"speed_kmh": v, "mu": mu, "branch": br, "domain": "main",
                                   "points_per_dim": b["guard"]["resolution_points_per_dim"],
                                   **{f"min_abs_dT_d{k}": _r(x["min_abs_nonzero"], 5)
                                      for k, x in b["guard"]["coordinates"].items()}})
                bound_rows.append({
                    "speed_kmh": v, "mu": mu, "branch": br, "a_eff_low": _r(a_eff[0]), "a_eff_high": _r(a_eff[1]),
                    "friction_binding": a_eff[1] < iv["a_max"][1],
                    "t_required_min_s": _r(b["t_req_min"]), "t_required_mid_s": _r(b["t_req_mid"]),
                    "t_required_max_s": _r(b["t_req_max"]), "width_s": _r(b["t_req_max"] - b["t_req_min"]),
                    "optimistic_corner": json.dumps({k: _r(x) for k, x in b["argmin"].items()}),
                    "conservative_corner": json.dumps({k: _r(x) for k, x in b["argmax"].items()}),
                    "bound_method": METHOD_ENDPOINT,
                })
                for s in sensitivity(v0, mu, br, iv, b["mid"]):
                    sens_rows.append({"speed_kmh": v, "mu": mu, "branch": br, **{k: (_r(x, 5) if isinstance(x, float) else x)
                                                                                for k, x in s.items()}})
                for ttc in TTC_S:
                    m_best, m_worst = ttc - b["t_req_min"], ttc - b["t_req_max"]
                    res_rows.append({
                        "scenario_id": f"v{v}_mu{mu}_{br}_ttc{ttc}", "v0_kmh": v, "ttc_s": ttc,
                        "hazard_distance_m": _r(v0 * ttc, 2), "mu": mu, "branch": br,
                        "policy": BRANCHES[br]["policy"], "authority_assumption": BRANCHES[br]["auth"],
                        "t1_s": f"[{iv['t1'][0]}, {iv['t1'][1]}]", "t2_s": f"[{iv['t2'][0]}, {iv['t2'][1]}]",
                        "t3_s": f"[{iv['t3'][0]}, {iv['t3'][1]}]",
                        "a_pre_profile": BRANCHES[br]["desc"],
                        "a_drag_mps2": f"[{iv['a_drag'][0]}, {iv['a_drag'][1]}]",
                        "a_sup_mps2": f"[{iv['a_sup'][0]}, {iv['a_sup'][1]}]" if "a_sup" in BRANCHES[br]["params"] else "",
                        "a_max_capability_mps2": f"[{iv['a_max'][0]}, {iv['a_max'][1]}]",
                        "a_effective_mps2": f"[{_r(a_eff[0])}, {_r(a_eff[1])}]",
                        "t_required_min_s": _r(b["t_req_min"]), "t_required_max_s": _r(b["t_req_max"]),
                        "recoverability_margin_best_s": _r(m_best), "recoverability_margin_worst_s": _r(m_worst),
                        "distance_margin_best_m": _r(v0 * m_best, 2), "distance_margin_worst_m": _r(v0 * m_worst, 2),
                        "classification": classify(m_worst, m_best),
                        "boundary_flag": boundary_flag(m_worst, m_best),
                    })

    # 2b. t1 supplement: evaluated after, and independently of, the main domain (see evaluate_supplement).
    supplement = evaluate_supplement(t1_high_sensitivity)
    attach_supplement(bound_rows, res_rows, supplement)
    _write(os.path.join(output_dir, "t_required_bounds.csv"), bound_rows)
    make_figure(bound_rows, os.path.join(output_dir, "t_required_bounds.png"))
    _write(os.path.join(output_dir, "results.csv"), res_rows)
    _write(os.path.join(output_dir, "sensitivity.csv"), sens_rows)
    _write(os.path.join(output_dir, "cross_check.csv"), xc_rows)
    _write(os.path.join(output_dir, "monotonicity_guard.csv"), guard_rows)

    # 3. policy comparison at matched parameters (midpoints) and bounds
    pol_rows = []
    for v in SPEEDS_KMH:
        for mu in FRICTION:
            ref = bounds[(v, mu, "P0|AUTH_AT_EFFECTIVE")]
            for br in BRANCHES:
                b = bounds[(v, mu, br)]
                changes = [ttc for ttc in TTC_S
                           if classify(ttc - b["t_req_max"], ttc - b["t_req_min"])
                           != classify(ttc - ref["t_req_max"], ttc - ref["t_req_min"])]
                pol_rows.append({"speed_kmh": v, "mu": mu, "branch": br, "reference": "P0|AUTH_AT_EFFECTIVE",
                                 "delta_t_required_mid_s": _r(b["t_req_mid"] - ref["t_req_mid"]),
                                 "delta_t_required_min_s": _r(b["t_req_min"] - ref["t_req_min"]),
                                 "delta_t_required_max_s": _r(b["t_req_max"] - ref["t_req_max"]),
                                 "ttc_values_with_changed_classification": ";".join(str(t) for t in changes)})
    _write(os.path.join(output_dir, "policy_comparison.csv"), pol_rows)

    counts = {}
    for r in res_rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    summary = {
        "label": SLICE_LABEL,
        "not": ["a probability model", "a claim that human fallback succeeds", "a recoverability envelope",
                "a Human Fallback Safety Envelope"],
        "success_definition": SUCCESS,
        "classification_rule": {"ROBUSTLY SATISFIED": "worst-case (conservative) time margin > +epsilon",
                                "ROBUSTLY UNSATISFIED": "best-case (optimistic) time margin < -epsilon",
                                "PARAMETER-SENSITIVE": "otherwise (bounds straddle or touch the +-epsilon band)",
                                "epsilon": EPSILON_S, "margin_units": MARGIN_UNITS,
                                "boundary_flag": "|worst| <= epsilon or |best| <= epsilon"},
        "bound_method": "corner evaluation, valid only where the analytic-derivative monotonicity guard passes "
                        "(fail-closed); not a general constrained-bound search",
        "bound_methods": {"main_domain": METHOD_ENDPOINT,
                          "t1_high_4s_supplement": {f"{v}|{mu}|{br}": sb["method"] for (v, mu, br), sb in supplement.items()},
                          "definitions": {METHOD_ENDPOINT: "corner evaluation inside the guarded monotone domain",
                                          METHOD_T1_STATIONARY: "corners of all other (guard-monotone) parameters x "
                                          "{t1 endpoints, interior roots of the exact dT/dt1}"}},
        "interval_method": "exact min/max over all corners of the parameter box; verified by a 4-point-per-"
                           "dimension interior grid; no distributions",
        "cross_check": {"tolerance_rel": CROSS_CHECK_REL_TOL,
                        "max_rel_diff": max(float(r["max_rel_diff_d_stop"]) for r in xc_rows)},
        "n_scenarios": len(res_rows), "classification_counts": counts,
        "branches": {k: v["desc"] for k, v in BRANCHES.items()},
        "blocked_inputs_not_used": BLOCKED_INPUTS,
        "validity_envelope": VALIDITY_ENVELOPE,
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    prov = {
        **git_state(),
        "code": ["src/experiments/r3b_braking_bounds.py", "src/metrics/oracle.py", "src/simulation/simulator.py",
                 "src/vehicle/models.py", "src/handover/models.py"],
        "inputs": {EPA_TABLE: _sha(EPA_TABLE), REGISTRY: _sha(REGISTRY)},
        "parameters": {k: {kk: vv for kk, vv in p.items()} for k, p in PARAMETERS.items()},
        "scenario_grid": {"speeds_kmh": SPEEDS_KMH, "ttc_s": TTC_S, "friction": FRICTION},
        "gravity_mps2": GRAVITY,
        "validity_envelope": VALIDITY_ENVELOPE,
    }
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2, default=str)
        fh.write("\n")
    return {"results": res_rows, "bounds": bound_rows, "sensitivity": sens_rows, "policy": pol_rows,
            "cross_check": xc_rows, "summary": summary, "provenance": prov}


if __name__ == "__main__":
    run(*sys.argv[1:2])
