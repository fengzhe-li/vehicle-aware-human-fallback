"""Automotive CAN/DBC input adapter for the vehicle-aware fallback model."""

from .dbc import Dbc, Signal, VehicleState, Frame, FrameFormat, Replay, FaultInjector

__all__ = ["Dbc", "Signal", "VehicleState", "Frame", "FrameFormat", "Replay", "FaultInjector"]
