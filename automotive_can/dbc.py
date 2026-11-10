"""Small deterministic CAN/DBC decoder and fallback-model adapter.

The parser intentionally covers the DBC BO_/SG_ signal subset used by this
adapter. It is not a replacement for a production vehicle gateway.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Iterable


class FrameFormat(str, Enum):
    CLASSICAL = "classical"
    FD = "fd"


@dataclass(frozen=True)
class Frame:
    can_id: int
    data: bytes
    timestamp_ns: int
    format: FrameFormat = FrameFormat.CLASSICAL
    extended: bool = False

    def __post_init__(self):
        limit = 8 if self.format == FrameFormat.CLASSICAL else 64
        if self.timestamp_ns < 0 or len(self.data) > limit:
            raise ValueError("invalid timestamp or CAN payload length")
        if not 0 <= self.can_id <= (0x1FFFFFFF if self.extended else 0x7FF):
            raise ValueError("CAN identifier outside selected identifier width")


@dataclass(frozen=True)
class Signal:
    name: str
    message_id: int
    start: int
    length: int
    order: str
    signed: bool
    factor: float
    offset: float
    minimum: float
    maximum: float
    unit: str = ""


@dataclass(frozen=True)
class Decoded:
    raw: int
    physical: float
    timestamp_ns: int
    valid: bool
    reason: str = ""


@dataclass
class VehicleState:
    timestamp_ns: int = 0
    signals: dict[str, Decoded] = field(default_factory=dict)
    faults: list[str] = field(default_factory=list)
    valid: bool = False

    def value(self, name: str, *, max_age_ns: int | None = None, now_ns: int | None = None) -> float:
        item = self.signals[name]
        if not item.valid:
            raise ValueError(f"signal {name} is invalid: {item.reason}")
        if max_age_ns is not None and (now_ns is None or now_ns - item.timestamp_ns > max_age_ns):
            raise ValueError(f"signal {name} is stale")
        return item.physical

    def fallback_inputs(self, *, max_age_ns: int, now_ns: int) -> dict[str, float]:
        """Map named DBC signals to existing SI model inputs without changing equations."""
        return {
            "v0": self.value("VehicleSpeed", max_age_ns=max_age_ns, now_ns=now_ns),
            "a_max": self.value("MaxDecel", max_age_ns=max_age_ns, now_ns=now_ns),
            "road_friction": self.value("RoadFriction", max_age_ns=max_age_ns, now_ns=now_ns),
        }

    def evaluate_braking(self, *, max_age_ns: int, now_ns: int, t_effective: float,
                         t_authority: float, standstill_margin_m: float = 2.0,
                         a_before_authority: float = 0.0,
                         a_after_authority: float = 0.0) -> dict[str, float]:
        """Run the repository's existing R3B closed-form calculation on fresh decoded inputs.

        Handover timing and pre-control deceleration remain explicit scenario assumptions;
        the CAN fixture never supplies or invents them.
        """
        from src.metrics.oracle import braking_t_required, stopping_distance_r3b_analytical
        values = self.fallback_inputs(max_age_ns=max_age_ns, now_ns=now_ns)
        delay = self.value("BrakeDelay", max_age_ns=max_age_ns, now_ns=now_ns)
        buildup = self.value("BrakeBuildup", max_age_ns=max_age_ns, now_ns=now_ns)
        distance = stopping_distance_r3b_analytical(
            values["v0"], values["a_max"], t_effective, delay, buildup,
            t_authority, a_before_authority, a_after_authority,
            road_friction=values["road_friction"],
        )
        return {"stopping_distance_m": distance,
                "t_required_s": braking_t_required(distance, values["v0"], standstill_margin_m)}


class Dbc:
    _message = re.compile(r"^\s*BO_\s+(\d+)\s+[^:]+:\s+(\d+)")
    _signal = re.compile(r'^\s*SG_\s+(\w+)\s+(?:\w+\s+)?:\s*(\d+)\|(\d+)@(\d)([+-])\s*\(([-+\d.eE]+),([-+\d.eE]+)\)\s*\[([-+\d.eE]+)\|([-+\d.eE]+)\]\s*"([^"]*)"')

    def __init__(self, signals: Iterable[Signal]):
        self.by_id: dict[int, list[Signal]] = {}
        for signal in signals:
            if not 1 <= signal.length <= 64:
                raise ValueError("signal length must be 1..64")
            self.by_id.setdefault(signal.message_id, []).append(signal)

    @classmethod
    def parse(cls, text: str) -> "Dbc":
        current: int | None = None
        signals = []
        for line in text.splitlines():
            message = cls._message.search(line)
            if message:
                current = int(message.group(1))
                continue
            match = cls._signal.search(line)
            if match and current is not None:
                name, start, length, byte_order, sign, factor, offset, lo, hi, unit = match.groups()
                signals.append(Signal(name, current, int(start), int(length),
                                      "intel" if byte_order == "1" else "motorola", sign == "-",
                                      float(factor), float(offset), float(lo), float(hi), unit))
        return cls(signals)

    @staticmethod
    def _extract(data: bytes, signal: Signal) -> int:
        bits = []
        bit = signal.start
        for _ in range(signal.length):
            if bit // 8 >= len(data):
                raise ValueError("signal exceeds frame payload")
            bits.append((data[bit // 8] >> (bit % 8)) & 1)
            if signal.order == "intel":
                bit += 1
            else:
                bit = bit + 15 if bit % 8 == 0 else bit - 1
        if signal.order == "intel":
            return sum(value << i for i, value in enumerate(bits))
        value = 0
        for item in bits:
            value = (value << 1) | item
        return value

    def decode(self, frame: Frame) -> dict[str, Decoded]:
        result = {}
        for signal in self.by_id.get(frame.can_id, []):
            try:
                raw = self._extract(frame.data, signal)
                if signal.signed and raw & (1 << (signal.length - 1)):
                    raw -= 1 << signal.length
                physical = raw * signal.factor + signal.offset
                valid = math.isfinite(physical) and signal.minimum <= physical <= signal.maximum
                result[signal.name] = Decoded(raw, physical, frame.timestamp_ns, valid,
                                              "" if valid else "physical value outside DBC range")
            except ValueError as error:
                result[signal.name] = Decoded(0, math.nan, frame.timestamp_ns, False, str(error))
        return result


class FaultInjector:
    """Deterministic SIL frame drop, delay, and corruption transforms."""
    def __init__(self, *, drop_ids=(), delay_ns=0, corrupt_ids=()):
        self.drop_ids = set(drop_ids)
        self.delay_ns = delay_ns
        self.corrupt_ids = set(corrupt_ids)

    def apply(self, frame: Frame) -> Frame | None:
        if frame.can_id in self.drop_ids:
            return None
        data = bytearray(frame.data)
        if frame.can_id in self.corrupt_ids and data:
            data[0] ^= 0xFF
        return Frame(frame.can_id, bytes(data), frame.timestamp_ns + self.delay_ns,
                     frame.format, frame.extended)


class Replay:
    def __init__(self, dbc: Dbc, stale_after_ns: int):
        self.dbc, self.stale_after_ns = dbc, stale_after_ns
        self.state = VehicleState()
        self._last_timestamp = -1

    def feed(self, frame: Frame) -> VehicleState:
        if frame.timestamp_ns < self._last_timestamp:
            self.state.faults.append("out-of-order frame")
            return self.state
        decoded = self.dbc.decode(frame)
        if not decoded:
            self.state.faults.append("unmapped frame")
            return self.state
        self._last_timestamp = frame.timestamp_ns
        self.state.timestamp_ns = frame.timestamp_ns
        self.state.signals.update(decoded)
        self.state.valid = all(signal.valid for signal in decoded.values())
        self.state.faults.extend(f"invalid signal: {name}" for name, signal in decoded.items() if not signal.valid)
        return self.state

    def snapshot(self, now_ns: int) -> VehicleState:
        copy = VehicleState(self.state.timestamp_ns, dict(self.state.signals), list(self.state.faults), self.state.valid)
        if self._last_timestamp < 0 or now_ns < self._last_timestamp or now_ns - self._last_timestamp > self.stale_after_ns:
            copy.valid = False
            copy.faults.append("vehicle state stale or missing")
        for name, signal in copy.signals.items():
            if now_ns < signal.timestamp_ns or now_ns - signal.timestamp_ns > self.stale_after_ns:
                copy.valid = False
                copy.faults.append(f"signal stale: {name}")
        return copy
