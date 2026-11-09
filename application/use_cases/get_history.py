"""Caso de uso: Consulta de histórico de leituras de temperatura."""

import logging
from typing import List, Optional
from domain.interfaces.telemetry_repository import ITelemetryRepository
from application.dtos.telemetry_dto import TelemetryHistoryItemDTO

logger = logging.getLogger(__name__)


class GetHistoryUseCase:
    """Recupera a série temporal de temperaturas corporais de um dispositivo."""

    def __init__(self, repository: ITelemetryRepository) -> None:
        self.repository = repository

    def execute(
        self, device_id: str, limit: int = 100, hours: Optional[int] = 24
    ) -> List[TelemetryHistoryItemDTO]:
        """Executa a busca do histórico de leituras."""
        logger.debug(
            "Consultando histórico para dispositivo %s (limit=%d, hours=%s)",
            device_id,
            limit,
            hours,
        )
        readings = self.repository.get_by_device_id(
            device_id=device_id, limit=limit, hours=hours
        )
        return [
            TelemetryHistoryItemDTO(
                temperature=r.temperature,
                status=r.status,
                timestamp=r.timestamp,
            )
            for r in readings
        ]
