"""Módulo de entidades do domínio de telemetria médica/corporal."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class TemperatureStatus(str, Enum):
    """Classificação clínica da temperatura corporal."""

    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    FEVER = "FEVER"


@dataclass(frozen=True)
class TelemetryReading:
    """Entidade pura representando uma leitura de temperatura corporal."""

    device_id: str
    temperature: float
    status: TemperatureStatus
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def evaluate_status(cls, temperature: float) -> TemperatureStatus:
        """Determina a classificação clínica de acordo com as regras de negócio."""
        if temperature < 37.5:
            return TemperatureStatus.NORMAL
        elif 37.5 <= temperature < 37.8:
            return TemperatureStatus.ELEVATED
        else:
            return TemperatureStatus.FEVER

    @classmethod
    def create(
        cls,
        device_id: str,
        temperature: float,
        reading_id: Optional[uuid.UUID] = None,
        timestamp: Optional[datetime] = None,
    ) -> "TelemetryReading":
        """Factory method que cria e classifica a leitura aplicando regras de domínio."""
        if not (30.0 <= temperature <= 45.0):
            raise ValueError(
                f"Temperatura ({temperature}°C) fora da escala corporal fisiológica aceitável (30.0°C - 45.0°C)."
            )

        status = cls.evaluate_status(temperature)
        return cls(
            id=reading_id or uuid.uuid4(),
            device_id=device_id,
            temperature=round(temperature, 2),
            status=status,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
