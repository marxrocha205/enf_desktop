"""Caso de uso: Ingestão e processamento de telemetria corporal com debounce de alertas."""

import logging
from typing import Optional
from domain.entities.telemetry import TelemetryReading, TemperatureStatus
from domain.interfaces.telemetry_repository import ITelemetryRepository
from domain.interfaces.cache_service import ICacheService
from application.dtos.telemetry_dto import TelemetryInputDTO, TelemetryResponseDTO

logger = logging.getLogger(__name__)


class IngestTelemetryUseCase:
    """Orquestra a validação, regra clínica, persistência e debounce de alertas de temperatura."""

    def __init__(
        self,
        repository: ITelemetryRepository,
        cache_service: Optional[ICacheService] = None,
    ) -> None:
        self.repository = repository
        self.cache_service = cache_service

    def execute(self, dto: TelemetryInputDTO) -> TelemetryResponseDTO:
        """Executa o caso de uso de ingestão."""
        logger.info(
            "Iniciando ingestão de telemetria. Dispositivo: %s, Temperatura: %.2f°C",
            dto.device_id,
            dto.temperature,
        )

        # 1. Criação da entidade de domínio (aplica regras e validações fisiológicas)
        reading = TelemetryReading.create(
            device_id=dto.device_id,
            temperature=dto.temperature,
        )

        # 2. Persistência via contrato de repositório
        saved_reading = self.repository.save(reading)

        # 3. Verificação de alerta clínico e regra de Debounce de 30 minutos (Redis)
        alert_msg = None
        if saved_reading.status == TemperatureStatus.FEVER:
            debounce_key = f"debounce:alert:{saved_reading.device_id}"
            can_alert = True

            if self.cache_service is not None:
                # 1800 segundos = 30 minutos de debounce
                can_alert = self.cache_service.check_and_set_debounce(
                    key=debounce_key, ttl_seconds=1800
                )

            if can_alert:
                logger.warning(
                    "ALERTA CLÍNICO DISPARADO: Febre detectada para o dispositivo %s! Temp: %.2f°C",
                    saved_reading.device_id,
                    saved_reading.temperature,
                )
                alert_msg = "Alerta de febre emitido com sucesso."
            else:
                logger.info(
                    "Alerta de febre para %s suprimido por debounce ativo nos últimos 30 min.",
                    saved_reading.device_id,
                )
                alert_msg = "Alerta de febre identificado (suprimido por debounce recente de 30 min)."

        return TelemetryResponseDTO(
            id=saved_reading.id,
            device_id=saved_reading.device_id,
            temperature=saved_reading.temperature,
            status=saved_reading.status,
            timestamp=saved_reading.timestamp,
            message=alert_msg,
        )
