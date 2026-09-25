"""T_TOR_critical search solver and edge-case handling.

Per metric_definitions.md:
- Criterion 1: smallest TOR_lead_time such that stopping_margin >= 0.
- Criterion 2: smallest TOR_lead_time such that stopping_margin >= dt * v_stop.
- Numerical search: bisection over TOR_lead_time within [tor_min, tor_max].
- Edge cases:
  - No safe solution within range: T_TOR_critical > TOR_max (search bound).
  - Every tested TOR safe: T_TOR_critical <= TOR_min.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import math

from src.scenarios.models import ScenarioConfig
from src.vehicle.models import VehicleResponseConfig
from src.driver.models import HumanDriverConfig
from src.handover.models import WithdrawalPolicy

if TYPE_CHECKING:
    from src.simulation.simulator import MinimalSimulator


@dataclass(frozen=True)
class CriticalTorResult:
    """Result of T_TOR_critical calculation or search.

    Parameters
    ----------
    t_tor_critical : Optional[float]
        Critical TOR lead time in seconds, or None if outside bounds.
    criterion : str
        Criterion used: 'criterion_1' (collision-free) or 'criterion_2' (resolvable-margin).
    status : str
        'CONVERGED', 'SAFE_AT_MIN_BOUND', 'UNSAFE_AT_MAX_BOUND', or 'MAX_ITERATIONS_EXCEEDED'.
    message : str
        Human-readable explanation of the result or edge case.
    iterations : int
        Number of bisection iterations performed.
    stopping_margin_at_critical : Optional[float]
        Stopping margin achieved at t_tor_critical.
    tor_min : float
        Lower search bound.
    tor_max : float
        Upper search bound.
    """

    t_tor_critical: Optional[float]
    criterion: str
    status: str
    message: str
    iterations: int
    stopping_margin_at_critical: Optional[float]
    tor_min: float
    tor_max: float


def bisection_search_t_tor_critical(
    scenario_base: ScenarioConfig,
    vehicle: VehicleResponseConfig,
    driver: HumanDriverConfig = HumanDriverConfig(),
    withdrawal: WithdrawalPolicy = WithdrawalPolicy.W0,
    criterion: str = "criterion_1",
    tor_min: float = 0.1,
    tor_max: float = 15.0,
    tol: float = 1e-5,
    max_iter: int = 100,
    dt: float = 0.001,
    simulator: Optional["MinimalSimulator"] = None,
) -> CriticalTorResult:
    """Find T_TOR_critical via bisection search over TOR_lead_time.

    Parameters
    ----------
    scenario_base : ScenarioConfig
        Base scenario providing v0 and road_friction.
    vehicle : VehicleResponseConfig
        Vehicle response profile.
    driver : HumanDriverConfig
        Frozen human driver config.
    withdrawal : WithdrawalPolicy
        Withdrawal policy under test.
    criterion : str
        'criterion_1' (stopping_margin >= 0) or
        'criterion_2' (stopping_margin >= dt * v_near_stop).
    tor_min : float
        Lower bound of search interval (s).
    tor_max : float
        Upper bound of search interval (s).
    tol : float
        Convergence tolerance on TOR interval width (s).
    max_iter : int
        Maximum number of bisection iterations allowed.
    dt : float
        Integration timestep for simulator (s).
    simulator : Optional[MinimalSimulator]
        Optional simulator instance to reuse.

    Returns
    -------
    CriticalTorResult
    """
    from src.simulation.simulator import MinimalSimulator

    if simulator is None:
        sim = MinimalSimulator(dt=dt)
    else:
        sim = simulator

    if criterion not in ("criterion_1", "criterion_2"):
        raise ValueError(f"Unknown criterion: {criterion}. Must be 'criterion_1' or 'criterion_2'.")

    # Determine target margin based on criterion
    if criterion == "criterion_1":
        target_margin = 0.0
    else:
        # Criterion 2: margin >= dt * v_stop near stop.
        # Estimate entry speed in final step: approximately a_max * dt
        v_near_stop = vehicle.a_max * dt
        target_margin = dt * v_near_stop

    # Evaluate lower bound
    scen_min = ScenarioConfig(
        v0=scenario_base.v0,
        tor_lead_time=tor_min,
        road_friction=scenario_base.road_friction,
    )
    res_min = sim.simulate(scen_min, vehicle, driver, withdrawal)
    margin_min = res_min.outcomes.stopping_margin

    if margin_min >= target_margin:
        return CriticalTorResult(
            t_tor_critical=tor_min,
            criterion=criterion,
            status="SAFE_AT_MIN_BOUND",
            message=f"T_TOR_critical <= TOR_min ({tor_min:.4f}s)",
            iterations=1,
            stopping_margin_at_critical=margin_min,
            tor_min=tor_min,
            tor_max=tor_max,
        )

    # Evaluate upper bound
    scen_max = ScenarioConfig(
        v0=scenario_base.v0,
        tor_lead_time=tor_max,
        road_friction=scenario_base.road_friction,
    )
    res_max = sim.simulate(scen_max, vehicle, driver, withdrawal)
    margin_max = res_max.outcomes.stopping_margin

    if margin_max < target_margin:
        return CriticalTorResult(
            t_tor_critical=None,
            criterion=criterion,
            status="UNSAFE_AT_MAX_BOUND",
            message=f"T_TOR_critical > TOR_max ({tor_max:.4f}s) (search bound), not a hopeless scenario in the mathematical sense",
            iterations=2,
            stopping_margin_at_critical=margin_max,
            tor_min=tor_min,
            tor_max=tor_max,
        )

    # Bisection search
    low = tor_min
    high = tor_max
    iterations = 2

    while (high - low) > tol and iterations < max_iter:
        mid = 0.5 * (low + high)
        scen_mid = ScenarioConfig(
            v0=scenario_base.v0,
            tor_lead_time=mid,
            road_friction=scenario_base.road_friction,
        )
        res_mid = sim.simulate(scen_mid, vehicle, driver, withdrawal)
        margin_mid = res_mid.outcomes.stopping_margin
        iterations += 1

        if margin_mid >= target_margin:
            high = mid
        else:
            low = mid

    t_crit = high
    scen_final = ScenarioConfig(
        v0=scenario_base.v0,
        tor_lead_time=t_crit,
        road_friction=scenario_base.road_friction,
    )
    res_final = sim.simulate(scen_final, vehicle, driver, withdrawal)

    if (high - low) <= tol:
        status = "CONVERGED"
        msg = f"Converged to root {t_crit:.6f}s in {iterations} iterations."
    else:
        status = "MAX_ITERATIONS_EXCEEDED"
        msg = f"Reached maximum iterations ({max_iter}) without reaching tolerance."

    return CriticalTorResult(
        t_tor_critical=t_crit,
        criterion=criterion,
        status=status,
        message=msg,
        iterations=iterations,
        stopping_margin_at_critical=res_final.outcomes.stopping_margin,
        tor_min=tor_min,
        tor_max=tor_max,
    )
