"""Contratos e interfaces abstratas do repositório de telemetria."""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.telemetry import TelemetryReading


class ITelemetryRepository(ABC):
    """Interface (Porta) para persistência e consulta de telemetria corporal."""

    @abstractmethod
    def save(self, reading: TelemetryReading) -> TelemetryReading:
        """Persiste uma leitura de telemetria no armazenamento."""
        raise NotImplementedError

    @abstractmethod
    def get_by_device_id(
        self, device_id: str, limit: int = 100, hours: Optional[int] = None
    ) -> List[TelemetryReading]:
        """Recupera histórico de leituras de um dispositivo."""
        raise NotImplementedError
