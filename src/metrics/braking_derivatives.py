"""Exact partial derivatives of the R3B braking stopping distance (vectorised).

Model (src/metrics/oracle.py::stopping_distance_r3b_analytical, u_brake = 1):
  segment 1 [0, ta):   constant deceleration a1 (policy before authority)
  segment 2 [ta, te):  constant deceleration a2 (vehicle only after authority)
  delay t2 at zero acceleration, linear ramp over t3 to ae = min(a_max, mu g), then ae.
With tau1 = ta, tau2 = te - ta and G(v) = t2 + B'(v), where B is the post-delay
braking distance, the derivatives are (no standstill before effective control):
  dD/dtau2 = v_e - a2 G(v_e)
  dD/dtau1 = (v1 - a1 tau2) - a1 G(v_e)
  dD/da1   = -tau1^2/2 - tau1 tau2 - tau1 G(v_e)
  dD/da2   = -tau2^2/2 - tau2 G(v_e)
  dD/dt2   = v_e
  dD/dt3   = v_e/2 - ae t3/12                     (no standstill in the ramp)
           = (1/3) v_e sqrt(2 v_e / (ae t3))      (standstill in the ramp)
  dD/dae   = -v_e^2/(2 ae^2) - t3^2/24             (no standstill in the ramp)
           = -(1/3) v_e^1.5 sqrt(2 t3) ae^-1.5    (standstill in the ramp)
  dae/da_max = 1 if a_max < mu g else 0            (friction saturation)
Standstill inside segment 1 or 2 makes D independent of every later quantity
(derivative 0 for those coordinates). T_required = (D + margin) / v0, so the sign of
dT/dp equals the sign of dD/dp.

The R3B branch parameterisation maps (t1, f) to (ta, te) = (f t1, t1), so
  dD/dt1 = f dD/dtau1 + (1 - f) dD/dtau2,   dD/df = t1 (dD/dtau1 - dD/dtau2).
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from src.vehicle.models import GRAVITY


def stopping_distance_and_gradient(v0, a_max, mu, t1, t2, t3, f, a1, a2) -> Dict[str, np.ndarray]:
    """Vectorised stopping distance D and its partial derivatives in branch coordinates.

    Returns D and dD/d{t1, t2, t3, a_max, f, a1, a2}. Inputs broadcast (numpy).
    """
    v0, a_max, t1, t2, t3, f, a1, a2 = map(lambda x: np.asarray(x, dtype=float),
                                           (v0, a_max, t1, t2, t3, f, a1, a2))
    ta, te = f * t1, t1
    tau1, tau2 = ta, te - ta
    ae = np.minimum(a_max, mu * GRAVITY)
    dae = np.where(a_max < mu * GRAVITY, 1.0, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        stop1 = (a1 > 0) & (v0 - a1 * tau1 <= 0)
        v1 = np.maximum(v0 - a1 * tau1, 0.0)
        x1 = v0 * tau1 - 0.5 * a1 * tau1 ** 2
        stop2 = ~stop1 & (a2 > 0) & (v1 - a2 * tau2 <= 0)
        ve = np.maximum(v1 - a2 * tau2, 0.0)
        xe = x1 + v1 * tau2 - 0.5 * a2 * tau2 ** 2
        ramp_stop = ve <= 0.5 * ae * t3
        # post-delay braking distance B and dB/dv
        B = np.where(ramp_stop, (2.0 / 3.0) * ve * np.sqrt(2.0 * ve * t3 / ae),
                     ve ** 2 / (2 * ae) + ve * t3 / 2 - ae * t3 ** 2 / 24)
        dB_dv = np.where(ramp_stop, np.sqrt(2.0 * ve * t3 / ae), ve / ae + t3 / 2)
        G = t2 + dB_dv
        D_run = xe + ve * t2 + B
        D_stop1 = np.where(a1 > 0, v0 ** 2 / (2 * np.where(a1 > 0, a1, 1.0)), 0.0)
        D_stop2 = x1 + np.where(a2 > 0, v1 ** 2 / (2 * np.where(a2 > 0, a2, 1.0)), 0.0)
        D = np.where(stop1, D_stop1, np.where(stop2, D_stop2, D_run))

        d_tau2 = ve - a2 * G
        d_tau1 = (v1 - a1 * tau2) - a1 * G
        d_t2 = ve
        d_t3 = np.where(ramp_stop, (1.0 / 3.0) * ve * np.sqrt(2.0 * ve / (ae * t3)), ve / 2 - ae * t3 / 12)
        d_ae = np.where(ramp_stop, -(1.0 / 3.0) * ve ** 1.5 * np.sqrt(2.0 * t3) * ae ** -1.5,
                        -ve ** 2 / (2 * ae ** 2) - t3 ** 2 / 24)
        d_a1 = -0.5 * tau1 ** 2 - tau1 * tau2 - tau1 * G
        d_a2 = -0.5 * tau2 ** 2 - tau2 * G
        # standstill before effective control
        # stop in segment 2: D = x1 + v1^2/(2 a2): depends on tau1 and a1, a2 only
        d_tau1_s2 = np.where(a2 > 0, v1 - a1 * v1 / np.where(a2 > 0, a2, 1.0), 0.0)
        d_a1_s2 = -0.5 * tau1 ** 2 - tau1 * v1 / np.where(a2 > 0, a2, 1.0)
        d_a2_s2 = -v1 ** 2 / (2 * np.where(a2 > 0, a2, 1.0) ** 2)
        # stop in segment 1: D = v0^2/(2 a1)
        d_a1_s1 = -v0 ** 2 / (2 * np.where(a1 > 0, a1, 1.0) ** 2)

    zero = np.zeros_like(D)
    running = ~stop1 & ~stop2
    dt1 = np.where(running, f * d_tau1 + (1 - f) * d_tau2, np.where(stop2, f * d_tau1_s2, zero))
    df = np.where(running, t1 * (d_tau1 - d_tau2), np.where(stop2, t1 * d_tau1_s2, zero))
    return {
        "D": D,
        "t1": dt1,
        "f": df,
        "t2": np.where(running, d_t2, zero),
        "t3": np.where(running, d_t3, zero),
        "a_max": np.where(running, d_ae * dae, zero),
        "a1": np.where(running, d_a1, np.where(stop2, d_a1_s2, np.where(stop1, d_a1_s1, zero))),
        "a2": np.where(running, d_a2, np.where(stop2, d_a2_s2, zero)),
    }
