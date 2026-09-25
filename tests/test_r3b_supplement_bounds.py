"""R3B t1 = 4 s supplement: stationary-point t1 bound (Option A), fail-closed behaviour, and
operational decoupling from the main domain. No test runs the R3B scenario study."""

import itertools

import numpy as np
import pytest
from scipy.optimize import brentq, minimize

from src.experiments import r3b_braking_bounds as r3b

V0, MU = 60 / 3.6, 0.5
P2_CASES = ["P2|AUTH_AT_EFFECTIVE", "P2|AUTH_UNCERTAIN"]
GLOBAL = {"P2|AUTH_AT_EFFECTIVE": (2.376852, 5.188854), "P2|AUTH_UNCERTAIN": (2.376852, 6.385743)}


def _sup(v):
    iv = r3b.intervals_for(v)
    return dict(iv, t1=(iv["t1"][0], 4.0))


# --- the two known non-monotone P2 cases ----------------------------------------------------------


@pytest.mark.parametrize("branch", P2_CASES)
def test_known_p2_cases_use_stationary_point_method(branch):
    b = r3b.bound_supplement(V0, MU, branch, _sup(60))
    assert b["method"] == r3b.METHOD_T1_STATIONARY and b["non_monotone"] == ["t1"]
    assert b["n_interior_stationary_points"] > 0
    assert b["t_req_min"] == pytest.approx(GLOBAL[branch][0], abs=1e-6)
    assert b["t_req_max"] == pytest.approx(GLOBAL[branch][1], abs=1e-6)


@pytest.mark.parametrize("branch", P2_CASES)
def test_known_p2_cases_agree_with_dense_and_global_search(branch):
    iv, names = _sup(60), r3b.BRANCHES[branch]["params"]
    b = r3b.bound_supplement(V0, MU, branch, iv)
    fn = lambda x: r3b.t_required(V0, MU, branch, dict(zip(names, x)))
    dense = [fn(c) for c in itertools.product(*[np.linspace(*iv[k], 5) for k in names])]
    assert min(dense) >= b["t_req_min"] - 1e-9 and max(dense) <= b["t_req_max"] + 1e-9
    rng, bnds = np.random.default_rng(3), [iv[k] for k in names]
    for _ in range(6):
        x0 = [rng.uniform(*bb) for bb in bnds]
        assert minimize(fn, x0, bounds=bnds, method="L-BFGS-B").fun >= b["t_req_min"] - 1e-7
        assert -minimize(lambda x: -fn(x), x0, bounds=bnds, method="L-BFGS-B").fun <= b["t_req_max"] + 1e-7


# --- a case with a known interior t1 extremum ------------------------------------------------------


def test_interior_t1_maximum_is_found_on_a_single_line():
    """Degenerate intervals fix every parameter except t1 on the line where dT/dt1 changes sign at about
    3.573 s: the true maximum is interior, above both endpoints, and endpoint-only bounds would miss it."""
    iv = dict(_sup(60), t2=(0.17, 0.17), t3=(1.2, 1.2), a_max=(6.43, 6.43), a_drag=(0.2267, 0.2267), a_sup=(3.0, 3.0))
    br = "P2|AUTH_AT_EFFECTIVE"
    fixed = {k: iv[k][0] for k in ("t2", "t3", "a_max", "a_drag", "a_sup")}
    t_star = brentq(lambda t: r3b.dT_dt1(V0, MU, br, dict(fixed, t1=t)), 1.15, 4.0)
    b = r3b.bound_supplement(V0, MU, br, iv)
    t_end = max(r3b.t_required(V0, MU, br, dict(fixed, t1=t)) for t in (1.15, 4.0))
    assert b["method"] == r3b.METHOD_T1_STATIONARY
    assert b["argmax"]["t1"] == pytest.approx(t_star, abs=1e-8) and 3.5 < t_star < 3.65
    assert b["t_req_max"] > t_end + 1e-4
    fine = max(r3b.t_required(V0, MU, br, dict(fixed, t1=t)) for t in np.linspace(1.15, 4.0, 20001))
    assert b["t_req_max"] >= fine - 1e-12


def test_line_candidates_find_roots_of_a_synthetic_derivative():
    c = r3b.t1_line_candidates(V0, MU, "P1", {}, 0.0, 7.0, derivative=np.cos)
    assert any(abs(x - np.pi / 2) < 1e-10 for x in c) and any(abs(x - 3 * np.pi / 2) < 1e-10 for x in c)
    assert c[0] == 0.0 and c[-1] == 7.0


# --- monotone cases unchanged -----------------------------------------------------------------------


@pytest.mark.parametrize("v,mu,branch", [(v, mu, br) for v in r3b.SPEEDS_KMH for mu in r3b.FRICTION
                                          for br in r3b.BRANCHES if not (v == 60 and mu == 0.5 and br in P2_CASES)])
def test_monotone_supplement_cases_keep_endpoint_method(v, mu, branch):
    iv = _sup(v)
    s, e = r3b.bound_supplement(v / 3.6, mu, branch, iv), r3b.bound(v / 3.6, mu, branch, iv)
    assert s["method"] == r3b.METHOD_ENDPOINT
    assert (s["t_req_min"], s["t_req_max"]) == (e["t_req_min"], e["t_req_max"])


@pytest.mark.parametrize("v,mu,branch", [(v, mu, br) for v in r3b.SPEEDS_KMH for mu in r3b.FRICTION for br in r3b.BRANCHES])
def test_main_domain_path_unchanged(v, mu, branch):
    s = r3b.bound_supplement(v / 3.6, mu, branch, r3b.intervals_for(v))
    assert s["method"] == r3b.METHOD_ENDPOINT


# --- fail closed ------------------------------------------------------------------------------------


@pytest.mark.parametrize("violations", [{"t1": "t1: x", "t3": "t3: y"}, {"a_sup": "a_sup: y"}, {"t1": "t1", "f_auth": "f"}])
def test_fail_closed_if_a_non_t1_parameter_is_non_monotone(monkeypatch, violations):
    monkeypatch.setattr(r3b, "_guard_scan", lambda *a, **k: ({"monotone": False, "coordinates": {}}, violations))
    with pytest.raises(r3b.MonotonicityGuardError, match="general constrained-bound search"):
        r3b.bound_supplement(V0, MU, "P2|AUTH_UNCERTAIN", _sup(60))


def test_fail_closed_if_stationary_points_do_not_bound_the_line():
    # a wrong derivative (claims monotone everywhere) yields endpoint-only candidates; the line scan must
    # detect the missed interior maximum and refuse to return bounds
    with pytest.raises(r3b.SupplementBoundError, match="cannot establish valid bounds"):
        r3b.bound_supplement(V0, MU, "P2|AUTH_AT_EFFECTIVE", _sup(60), derivative_factory=lambda o: (lambda t: 1.0))


def test_guard_behaviour_unchanged_for_endpoint_path():
    with pytest.raises(r3b.MonotonicityGuardError, match="constrained-bound search is required"):
        r3b.bound(V0, MU, "P2|AUTH_AT_EFFECTIVE", _sup(60))


# --- operational decoupling ---------------------------------------------------------------------------


def test_supplement_failure_cannot_block_or_alter_main_rows(monkeypatch):
    def boom(*a, **k):
        raise r3b.SupplementBoundError("synthetic failure")
    monkeypatch.setattr(r3b, "bound_supplement", boom)
    sup = r3b.evaluate_supplement(4.0)  # must not raise
    assert len(sup) == 30 and all(x["method"] == "NOT BOUNDED" for x in sup.values())
    brow = {"speed_kmh": 60, "mu": 0.5, "branch": "P1", "t_required_max_s": 5.0}
    rrow = {"v0_kmh": 60, "mu": 0.5, "branch": "P1", "ttc_s": 7.0, "classification": "ROBUSTLY SATISFIED"}
    before = (dict(brow), dict(rrow))
    r3b.attach_supplement([brow], [rrow], sup)
    assert rrow["classification_if_t1_high_4s"] == "NOT BOUNDED" and rrow["t1_high_4s_bound_method"] == "NOT BOUNDED"
    assert all(brow[k] == v for k, v in before[0].items()) and all(rrow[k] == v for k, v in before[1].items())


def test_attach_supplement_records_method_and_uses_supplement_min_and_max():
    sup = {(60, 0.5, "P1"): {"method": r3b.METHOD_T1_STATIONARY, "t_req_min": 3.0, "t_req_max": 6.0}}
    brow, rrow = {"speed_kmh": 60, "mu": 0.5, "branch": "P1"}, {"v0_kmh": 60, "mu": 0.5, "branch": "P1", "ttc_s": 7.0}
    r3b.attach_supplement([brow], [rrow], sup)
    assert brow["t1_high_4s_bound_method"] == r3b.METHOD_T1_STATIONARY and brow["t_required_max_if_t1_high_4s"] == 6.0
    assert rrow["classification_if_t1_high_4s"] == r3b.classify(1.0, 4.0)
