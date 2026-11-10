# Automotive CAN/DBC vehicle-state adapter

This additive module provides a small C++17 DBC decoder, a Python SIL/replay
adapter, and a bridge into the existing R3B braking calculation. It does not
change the research model, its assumptions, or any historical result. No real
vehicle telemetry or ECU definition is included.

## Scope and supported signal handling

- Classical CAN payloads are limited to 8 bytes. CAN FD payloads are accepted up
  to 64 bytes. The decoder consumes a CAN identifier, frame format, timestamp,
  and payload supplied by the caller.
- DBC `BO_` and `SG_` declarations are supported for Intel (`@1`) and Motorola
  (`@0`) bit order, signed and unsigned integers, 1–64 bit widths, factor,
  offset, physical range, and unit.
- Physical values outside the DBC range are invalid. Missing mappings, malformed
  lengths, old timestamps, missing input, and stale state are surfaced as faults
  or rejected by the adapter.
- The parser intentionally implements this DBC subset rather than multiplexed
  signals, value tables, attributes, extended-ID conventions, or a complete DBC
  grammar. Production gateways should validate those semantics separately.

The Python adapter expects these signal names and SI units for fallback
integration: `VehicleSpeed` (m/s), `RoadFriction` (coefficient), `MaxDecel`
(m/s²), `BrakeDelay` (s), and `BrakeBuildup` (s). `VehicleState.evaluate_braking`
passes decoded values into the repository's existing
`src.metrics.oracle.stopping_distance_r3b_analytical` and
`braking_t_required` functions. Handover times and pre-control deceleration stay
explicit inputs because the CAN signals do not identify them.

## Deterministic SIL

`automotive_can/examples/synthetic_vehicle.dbc` and `replay_synthetic.py` are
explicitly synthetic fixtures. `FaultInjector` supports deterministic frame
drop, timestamp delay, and payload corruption. Replay rejects out-of-order
frames and snapshots report missing or stale state. These tests validate the
decoder and software interface only; they are not real-vehicle, ECU, HIL, or
ISO 26262 validation.

## Build and verification

```sh
cmake -S automotive_can -B build/automotive_can
cmake --build build/automotive_can --parallel
ctest --test-dir build/automotive_can --output-on-failure
python -m pytest tests/test_automotive_can.py -q
python -m pytest
python -m automotive_can.examples.replay_synthetic
```
