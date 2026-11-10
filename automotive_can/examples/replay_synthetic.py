"""Deterministic SIL example. Values are synthetic and not vehicle telemetry."""
from pathlib import Path

from automotive_can import Dbc, Frame, Replay

dbc = Dbc.parse(Path(__file__).with_name("synthetic_vehicle.dbc").read_text())
# Synthetic values: 20.0 m/s, mu=1.0, a_max=8.0 m/s2, t2=0.10 s, t3=0.50 s.
frame = Frame(256, bytes([0xD0, 0x07, 100, 80, 100, 50, 0, 0]), timestamp_ns=1_000_000_000)
state = Replay(dbc, stale_after_ns=100_000_000).feed(frame)
print(state.evaluate_braking(max_age_ns=100_000_000, now_ns=1_050_000_000,
                             t_effective=1.5, t_authority=1.5))
