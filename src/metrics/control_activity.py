"""Neutral channel-activity detectors (Phase R2A).

These functions count features of recorded signals. They make no statement about
who produced the signal. In D003 the accelerator, brake and steering channels may
carry automation actuation, simulator/controller activity, driver activity, or a
mixture (blocker B17), so outputs of these functions must be described as
"channel activity", never as driver action, driver command or human input.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks


def count_hysteresis_reversals(signal: np.ndarray, gap: float) -> int:
    """Direction changes of a signal after it has moved at least `gap` from its last
    extreme (amplitude hysteresis; same algorithm as the pre-audit detector, after
    McLean & Hoffmann 1975). NaNs are dropped."""
    signal = np.asarray(signal, dtype=float)
    signal = signal[~np.isnan(signal)]
    if len(signal) < 2:
        return 0
    reversals, state, extreme = 0, 0, signal[0]
    for val in signal[1:]:
        if state == 0:
            if val - extreme >= gap:
                state, extreme = 1, val
            elif extreme - val >= gap:
                state, extreme = -1, val
        elif state == 1:
            if val > extreme:
                extreme = val
            elif extreme - val >= gap:
                reversals, state, extreme = reversals + 1, -1, val
        else:
            if val < extreme:
                extreme = val
            elif val - extreme >= gap:
                reversals, state, extreme = reversals + 1, 1, val
    return reversals


def lowpass(signal: np.ndarray, cutoff_hz: float = 2.0, fs_hz: float = 20.0) -> np.ndarray:
    """Zero-phase 2nd-order Butterworth low-pass; short or NaN-containing signals are returned unchanged."""
    signal = np.asarray(signal, dtype=float)
    if len(signal) <= 15 or np.isnan(signal).any():
        return signal
    b, a = butter(2, cutoff_hz / (fs_hz / 2), btype="low")
    return filtfilt(b, a, signal)


def count_signal_peaks(values: np.ndarray, prominence: float, min_separation_samples: int = 10) -> int:
    """Number of local maxima with at least `prominence` (signal units). NaNs are dropped."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 3:
        return 0
    peaks, _ = find_peaks(values, prominence=prominence, distance=min_separation_samples)
    return int(len(peaks))
