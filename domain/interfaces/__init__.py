"""Interfaces e contratos do domínio."""

from domain.interfaces.telemetry_repository import ITelemetryRepository
from domain.interfaces.cache_service import ICacheService
from domain.interfaces.medication_repository import IMedicationRepository

__all__ = [
    "ITelemetryRepository",
    "ICacheService",
    "IMedicationRepository",
]
