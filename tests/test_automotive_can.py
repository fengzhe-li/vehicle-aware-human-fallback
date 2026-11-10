import pytest

from automotive_can import Dbc, FaultInjector, Frame, FrameFormat, Replay


DBC = '''BO_ 256 VehicleState: 8 ECU
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|100] "m/s" ECU
 SG_ SignedAccel : 16|8@1- (0.1,0) [-12|12] "m/s2" ECU
 SG_ Motorola : 31|8@0+ (1,0) [0|255] "" ECU
 SG_ RoadFriction : 32|8@1+ (0.01,0) [0|1.5] "" ECU
 SG_ MaxDecel : 40|8@1+ (0.1,0) [0|15] "m/s2" ECU
 SG_ BrakeDelay : 48|8@1+ (0.001,0) [0|1] "s" ECU
 SG_ BrakeBuildup : 56|8@1+ (0.01,0) [0|3] "s" ECU
'''


def fixture(timestamp=100):
    # Speed=12.34 m/s, signed acceleration=-1 m/s2, Motorola byte 0x5a;
    # remaining values are explicitly synthetic test inputs only.
    return Frame(256, bytes([0xD2, 0x04, 0xF6, 0x5A, 100, 85, 100, 50]), timestamp)


def test_intel_signed_motorola_and_physical_scaling():
    decoded = Dbc.parse(DBC).decode(fixture())
    assert decoded["VehicleSpeed"].physical == pytest.approx(12.34)
    assert decoded["SignedAccel"].physical == pytest.approx(-1.0)
    assert decoded["Motorola"].physical == 0x5A
    assert decoded["RoadFriction"].physical == 1.0


def test_can_fd_payload_and_classical_size_guard():
    assert Frame(256, bytes(64), 10, FrameFormat.FD)
    with pytest.raises(ValueError):
        Frame(256, bytes(9), 10)


def test_fresh_state_integrates_with_original_r3b_oracle():
    replay = Replay(Dbc.parse(DBC), stale_after_ns=20)
    state = replay.feed(fixture())
    result = state.evaluate_braking(max_age_ns=20, now_ns=110, t_effective=1.0, t_authority=1.0)
    assert result["stopping_distance_m"] > 0
    assert result["t_required_s"] > 0
    with pytest.raises(ValueError, match="stale"):
        state.value("VehicleSpeed", max_age_ns=20, now_ns=1000)


def test_missing_delayed_out_of_order_invalid_and_fault_injection():
    dbc = Dbc.parse(DBC)
    replay = Replay(dbc, stale_after_ns=10)
    assert not replay.snapshot(100).valid
    injector = FaultInjector(drop_ids={256})
    assert injector.apply(fixture()) is None
    replay.feed(fixture(100))
    replay.feed(fixture(90))
    assert "out-of-order frame" in replay.state.faults
    assert not replay.snapshot(111).valid
    bad = Frame(256, bytes([0xFF, 0xFF, 0, 0x5A, 100, 85, 100, 50]), 120)
    replay.feed(bad)
    assert not replay.state.valid
    assert any("VehicleSpeed" in fault for fault in replay.state.faults)
