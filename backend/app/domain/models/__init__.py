"""Domain models package for Smart EV Charging Management System."""

from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.ev import EV, EVStatus
from app.domain.models.energy import GridState, SolarState, EnergyState
from app.domain.models.battery import VirtualBattery
from app.domain.models.parking import ParkingSlot, ParkingState

__all__ = [
    "HardwareTelemetry",
    "EV",
    "EVStatus",
    "GridState",
    "SolarState",
    "EnergyState",
    "VirtualBattery",
    "ParkingSlot",
    "ParkingState",
]
