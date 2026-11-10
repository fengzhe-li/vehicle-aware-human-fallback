"""Exact path geometry on a constant-curvature reference road.

Position is the bicycle rear-axle reference, speed is path arc-length speed.
Analytical bounds below cover every path point and every allowed path length.
"""
from __future__ import annotations

import math
from .schema import finite


def smoothstep(u: float) -> tuple[float, float, float, float]:
    """Quintic shift q and its first three derivatives with respect to u."""
    finite(u, "u", 0)
    if u > 1:
        raise ValueError("u must be in [0,1]")
    return (u**3 * (10 - 15*u + 6*u*u),
            30*u*u*(1-u)**2,
            60*u*(1-u)*(1-2*u),
            60 - 360*u + 360*u*u)


def path_point(u: float, length_m: float, offset_m: float, road_curvature: float) -> dict[str, float]:
    """Reference curve, exact curvature, and d(curvature)/d(road station)."""
    finite(length_m, "length_m")
    finite(offset_m, "offset_m")
    finite(road_curvature, "road_curvature")
    if not 1e-3 <= length_m <= 1e6 or max(abs(offset_m), abs(road_curvature)) > 1e6:
        raise ValueError("path inputs outside numerically supported domain")
    q, q1, q2, q3 = smoothstep(u)
    s, k = u * length_m, road_curvature
    y, b, c, d = offset_m*q, offset_m*q1/length_m, offset_m*q2/length_m**2, offset_m*q3/length_m**3
    a = 1-k*y
    if a <= 0:
        raise ValueError("singular/folded Frenet coordinates")
    metric = a*a + b*b
    numerator = k*a*a + a*c + 2*k*b*b
    numerator_prime = a*d + 3*k*b*c - 2*k*k*a*b
    metric_prime = 2*b*(c-k*a)
    curvature = numerator / metric**1.5
    derivative = numerator_prime / metric**1.5 - 1.5*numerator*metric_prime/metric**2.5
    angle = k*s
    # sinc/half-angle formula avoids catastrophic cancellation near k=0.
    road_x = s if angle == 0 else s * math.sin(angle)/angle
    road_y = 0.0 if angle == 0 else s * 2*math.sin(angle/2)**2/angle
    return dict(x_m=road_x-y*math.sin(angle), y_m=road_y+y*math.cos(angle),
                road_station_m=s, offset_m=y, curvature_per_m=curvature,
                curvature_derivative_per_m2=derivative,
                path_metric=math.sqrt(metric), heading_rad=angle+math.atan2(b, a))


def demand_bounds(length_low: float, length_high: float, offset: float,
                  road_k: float, wheelbase: float, speed_low: float, speed_high: float) -> dict[str, float]:
    """Certified conservative demand bounds (not extrema from a sampled grid).

    Upper bounds use triangle inequalities and A_min > 0. Lower certificates
    evaluate endpoints and q'' extrema with interval arithmetic over S.
    """
    for name, value in locals().copy().items():
        finite(value, name)
    if wheelbase <= 0 or not 0 <= speed_low <= speed_high:
        raise ValueError("need positive wheelbase and ordered nonnegative speeds")
    if length_low < 1e-3 or max(length_high, abs(offset), abs(road_k), wheelbase, speed_high) > 1e6:
        raise ValueError("demand inputs outside numerically supported domain")
    if not 0 < length_low <= length_high:
        raise ValueError("need 0 < length_low <= length_high")
    a_min, a_max = sorted((1.0, 1-road_k*offset))
    if a_min < 0.1:
        raise ValueError("Frenet metric too close to singularity")
    h, k = abs(offset), abs(road_k)
    b_max = 1.875*h/length_low
    c_max = (10/math.sqrt(3))*h/length_low**2
    d_max = 60*h/length_low**3
    n_max = k*a_max*a_max + a_max*c_max + 2*k*b_max*b_max
    curvature_upper = n_max/a_min**3
    np_max = a_max*d_max + 3*k*b_max*c_max + 2*k*k*a_max*b_max
    dp_max = 2*b_max*(c_max+k*a_max)
    kp_upper = np_max/a_min**3 + 1.5*n_max*dp_max/a_min**5
    rate_upper = wheelbase*speed_high*kp_upper/a_min

    curvature_lower = max(k, abs(road_k/(1-road_k*offset)))
    for u in ((3-math.sqrt(3))/6, (3+math.sqrt(3))/6):
        q, q1, q2, _ = smoothstep(u)
        a = 1-road_k*offset*q
        coefficient = a*offset*q2 + 2*road_k*(offset*q1)**2
        numerators = [road_k*a*a + coefficient/s**2 for s in (length_low, length_high)]
        lo, hi = min(numerators), max(numerators)
        min_abs = 0.0 if lo <= 0 <= hi else min(abs(lo), abs(hi))
        denom_max = (a*a + (offset*q1/length_low)**2)**1.5
        curvature_lower = max(curvature_lower, min_abs/denom_max)
    # q'=q''=0 at either endpoint, so the steering rate is analytic there.
    rate_lower = max(wheelbase*speed_low*60*h /
                     (length_high**3*a**3*(1+(wheelbase*road_k/a)**2))
                     for a in (1.0, 1-road_k*offset))
    return dict(curvature_lower_per_m=curvature_lower,
                curvature_upper_per_m=curvature_upper,
                steering_lower_rad=math.atan(wheelbase*curvature_lower),
                steering_upper_rad=math.atan(wheelbase*curvature_upper),
                lateral_accel_lower_mps2=speed_low**2*curvature_lower,
                lateral_accel_upper_mps2=speed_high**2*curvature_upper,
                steering_rate_lower_rad_s=rate_lower,
                steering_rate_upper_rad_s=rate_upper)
