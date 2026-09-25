"""R3B gate engineering: margin units, epsilon classification, monotonicity guard, t1 = 4 s supplement
cross-check, analytic derivatives, and the legacy WithdrawalPolicy guard. None of these tests runs the
R3B scenario study."""

import csv
import itertools

import numpy as np
import pytest

from src.experiments import r3b_braking_bounds as r3b
from src.handover.models import HandoverTimeline, PreControlProfile, WithdrawalPolicy
from src.metrics.braking_derivatives import stopping_distance_and_gradient
from src.metrics.oracle import stopping_distance_r3b_analytical
from src.scenarios.models import ScenarioConfig
from src.simulation.simulator import MinimalSimulator
from src.vehicle.models import VehicleResponseConfig, calculate_acceleration

EPS = r3b.EPSILON_S
CASES = [(v, mu, br) for v in r3b.SPEEDS_KMH for mu in r3b.FRICTION for br in r3b.BRANCHES]


def _t1_supplement(v):
    iv = r3b.intervals_for(v)
    return dict(iv, t1=(iv["t1"][0], 4.0))


# --- 0. margin units --------------------------------------------------------------------------


def test_classifier_margin_is_time_in_seconds():
    assert r3b.MARGIN_UNITS == "s" and EPS == 0.01
    # 130 km/h: a 0.005 s time margin is 0.18 m. A distance-based comparison against 0.01 would
    # call it satisfied; the time-based classifier must call it parameter-sensitive.
    v0 = 130 / 3.6
    assert v0 * 0.005 > EPS
    assert r3b.classify(0.005, 1.0) == "PARAMETER-SENSITIVE"
    with open("results/R3B_braking_bounds/results.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            v = float(r["v0_kmh"]) / 3.6
            assert float(r["distance_margin_worst_m"]) == pytest.approx(v * float(r["recoverability_margin_worst_s"]), abs=0.01)
            assert r["classification"] == r3b.classify(float(r["recoverability_margin_worst_s"]),
                                                       float(r["recoverability_margin_best_s"]))


# --- 3. zero-margin classification ------------------------------------------------------------


@pytest.mark.parametrize("worst,best,label,flag", [
    (0.0, 0.0, "PARAMETER-SENSITIVE", True),                    # exactly zero
    (EPS, 1.0, "PARAMETER-SENSITIVE", True),                    # worst exactly +epsilon
    (EPS + 1e-9, 1.0, "ROBUSTLY SATISFIED", False),             # just above +epsilon
    (-1.0, -EPS, "PARAMETER-SENSITIVE", True),                  # best exactly -epsilon
    (-1.0, -EPS - 1e-9, "ROBUSTLY UNSATISFIED", False),         # just below -epsilon
    (-0.5, 0.5, "PARAMETER-SENSITIVE", False),                  # straddles zero
])
def test_epsilon_band_classification(worst, best, label, flag):
    assert r3b.classify(worst, best) == label
    assert r3b.boundary_flag(worst, best) is flag


def test_no_committed_margin_inside_epsilon_band():
    with open("results/R3B_braking_bounds/results.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    closest = min(min(abs(float(r["recoverability_margin_worst_s"])), abs(float(r["recoverability_margin_best_s"])))
                  for r in rows)
    assert closest > EPS  # ~0.047 s: no current label changes under the epsilon rule


# --- 1. monotonicity guard ----------------------------------------------------------------------


def test_analytic_derivatives_match_oracle_and_finite_differences():
    rng = np.random.default_rng(7)
    for _ in range(400):
        v0, a_max, mu = rng.uniform(2, 40), rng.uniform(4, 9.5), rng.choice([0.3, 0.5, 1.0])
        t1, t2, t3, f = rng.uniform(0.2, 4), rng.uniform(0, 0.3), rng.uniform(0.1, 1.5), rng.uniform(0, 1)
        a1, a2 = rng.choice([0.0, rng.uniform(0, 5)]), rng.uniform(0, 1.5)
        p = dict(v0=v0, a_max=a_max, mu=mu, t1=t1, t2=t2, t3=t3, f=f, a1=a1, a2=a2)
        D = lambda q: stopping_distance_r3b_analytical(q["v0"], q["a_max"], q["t1"], q["t2"], q["t3"],
                                                       q["f"] * q["t1"], q["a1"], q["a2"], 1.0, q["mu"])
        g = stopping_distance_and_gradient(**p)
        assert float(g["D"]) == pytest.approx(D(p), rel=1e-12)
        for k in ("t1", "t2", "t3", "a_max", "f", "a1", "a2"):
            h = 1e-6 * max(1.0, abs(p[k]))
            lo = max(p[k] - h, 0.0) if k in ("f", "a1", "a2", "t2") else p[k] - h
            hi = min(p[k] + h, 1.0) if k == "f" else p[k] + h
            fd = (D(dict(p, **{k: hi})) - D(dict(p, **{k: lo}))) / (hi - lo)
            assert float(g[k]) == pytest.approx(fd, rel=1e-5, abs=1e-5), k


@pytest.mark.parametrize("v,mu,branch", CASES)
def test_guard_passes_on_committed_main_domain(v, mu, branch):
    rep = r3b.monotonicity_guard(v / 3.6, mu, branch, r3b.intervals_for(v))
    assert rep["monotone"] and rep["grid_points"] <= r3b.GUARD_MAX_POINTS
    assert set(rep["coordinates"]) == set(r3b.BRANCHES[branch]["params"])  # every bounded parameter covered


def test_guard_fails_closed_when_p2_support_breaks_t1_monotonicity():
    iv = dict(r3b.intervals_for(60), t1=(1.15, 4.0), a_sup=(1.0, 4.0))
    with pytest.raises(r3b.MonotonicityGuardError, match="constrained-bound search is required"):
        r3b.monotonicity_guard(60 / 3.6, 0.5, "P2|AUTH_AT_EFFECTIVE", iv)
    with pytest.raises(r3b.MonotonicityGuardError):
        r3b.bound(60 / 3.6, 0.5, "P2|AUTH_AT_EFFECTIVE", iv)  # no silent endpoint bounds


def test_guard_detects_interior_reversal_that_endpoint_comparison_misses():
    """On this domain T(t1_hi) > T(t1_lo) on every grid line, so an endpoint-difference check passes;
    the derivative still changes sign inside, and the guard must fail."""
    v0, mu, br = 60 / 3.6, 0.5, "P2|AUTH_AT_EFFECTIVE"
    iv = _t1_supplement(60)
    others = [k for k in r3b.BRANCHES[br]["params"] if k != "t1"]
    for combo in itertools.product(*[np.linspace(*iv[k], 4) for k in others]):
        p = dict(zip(others, combo))
        assert r3b.t_required(v0, mu, br, dict(p, t1=4.0)) > r3b.t_required(v0, mu, br, dict(p, t1=iv["t1"][0]))
    with pytest.raises(r3b.MonotonicityGuardError, match="dT/dt1"):
        r3b.monotonicity_guard(v0, mu, br, iv)


# --- 2. t1 = 4 s supplement ---------------------------------------------------------------------


@pytest.mark.parametrize("v,mu,branch", CASES)
def test_t1_supplement_interior_cross_check(v, mu, branch):
    """Endpoint bounds on the t1 <= 4 s supplement must not miss an interior extremum."""
    iv = _t1_supplement(v)
    names = r3b.BRANCHES[branch]["params"]
    fn = lambda p: r3b.t_required(v / 3.6, mu, branch, p)
    corners = [fn(dict(zip(names, c))) for c in itertools.product(*[iv[k] for k in names])]
    chk = r3b.interior_extrema_check(fn, {k: iv[k] for k in names}, min(corners), max(corners))
    assert chk["ok"], (v, mu, branch, chk)
    stored = {(int(r["speed_kmh"]), float(r["mu"]), r["branch"]): float(r["t_required_max_if_t1_high_4s"])
              for r in csv.DictReader(open("results/R3B_braking_bounds/t_required_bounds.csv", newline=""))}
    assert stored[(v, mu, branch)] == pytest.approx(max(corners), abs=1e-4)


@pytest.mark.parametrize("branch", ["P2|AUTH_AT_EFFECTIVE", "P2|AUTH_UNCERTAIN"])
def test_t1_supplement_guard_status_is_recorded(branch):
    """The supplement leaves the guarded (endpoint) domain at 60 km/h, mu 0.5 for P2: the plain endpoint
    guard must fail closed there; bound_supplement handles these cases with the stationary-point t1 method."""
    with pytest.raises(r3b.MonotonicityGuardError):
        r3b.monotonicity_guard(60 / 3.6, 0.5, branch, _t1_supplement(60))


def test_interior_check_detects_missed_extremum():
    fn = lambda p: -(p["x"] - 0.5) ** 2  # maximum at the interior point x = 0.5
    chk = r3b.interior_extrema_check(fn, {"x": (0.0, 1.0)}, corner_min=-0.25, corner_max=-0.25, n=5)
    assert not chk["ok"]


# --- 4. legacy WithdrawalPolicy guard -------------------------------------------------------------


def test_withdrawal_policy_is_legacy_w0_w1_only():
    assert {m.value for m in WithdrawalPolicy} == {"W0", "W1"}
    veh = VehicleResponseConfig(t_delay=0.1, t_buildup=0.5, a_max=8.5)
    with pytest.raises(ValueError):  # R3B pre-control needs an explicit authority time
        calculate_acceleration(0.5, 20.0, veh, WithdrawalPolicy.W0, 1.0, pre_control=PreControlProfile(1.0, 0.3))
    with pytest.raises(ValueError):  # timeline and pre-control profile only together
        MinimalSimulator().simulate(ScenarioConfig(v0=20.0, tor_lead_time=5.0), veh,
                                    timeline=HandoverTimeline(0.5, 1.0))
    assert all(b["policy"] in ("P0", "P1", "P2") for b in r3b.BRANCHES.values())
    assert not any(b["policy"] in {m.value for m in WithdrawalPolicy} for b in r3b.BRANCHES.values())


def test_write_handles_rows_with_branch_dependent_columns(tmp_path):
    """monotonicity_guard.csv rows differ by branch (f_auth / a_sup columns); _write must use the union."""
    path = tmp_path / "g.csv"
    r3b._write(str(path), [{"branch": "P0", "min_abs_dT_dt1": 1.0},
                           {"branch": "P2", "min_abs_dT_dt1": 0.04, "min_abs_dT_da_sup": 0.2}])
    rows = list(csv.DictReader(open(path, newline="")))
    assert list(rows[0]) == ["branch", "min_abs_dT_dt1", "min_abs_dT_da_sup"]
    assert rows[0]["min_abs_dT_da_sup"] == "" and rows[1]["min_abs_dT_da_sup"] == "0.2"
