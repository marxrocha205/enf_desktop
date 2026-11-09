"""Endpoints de ingestão e consulta de histórico de telemetria corporal."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from application.dtos.telemetry_dto import (
    TelemetryInputDTO,
    TelemetryResponseDTO,
    TelemetryHistoryItemDTO,
)
from application.use_cases.ingest_telemetry import IngestTelemetryUseCase
from application.use_cases.get_history import GetHistoryUseCase
from infrastructure.database.connection import get_db
from infrastructure.repositories.sqlalchemy_telemetry_repository import (
    SqlAlchemyTelemetryRepository,
)
from infrastructure.cache.redis_cache_service import RedisCacheService

router = APIRouter(tags=["Telemetry"])


def get_telemetry_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTelemetryRepository:
    """Provedor de injeção de dependência para o repositório de telemetria."""
    return SqlAlchemyTelemetryRepository(db=db)


def get_cache_service() -> RedisCacheService:
    """Provedor de injeção de dependência para o serviço de cache e debounce."""
    return RedisCacheService()


@router.post(
    "/telemetry/",
    response_model=TelemetryResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestão de Leitura de Temperatura",
    description="Recebe a telemetria do sensor corporal enviada pelo ESP32 via HTTP POST.",
)
def ingest_telemetry(
    dto: TelemetryInputDTO,
    repo: SqlAlchemyTelemetryRepository = Depends(get_telemetry_repository),
    cache_service: RedisCacheService = Depends(get_cache_service),
) -> TelemetryResponseDTO:
    """Executa o caso de uso de ingestão de telemetria com verificação de debounce."""
    use_case = IngestTelemetryUseCase(repository=repo, cache_service=cache_service)
    return use_case.execute(dto)


@router.get(
    "/history/{device_id}",
    response_model=List[TelemetryHistoryItemDTO],
    status_code=status.HTTP_200_OK,
    summary="Histórico de Temperatura por Dispositivo",
    description="Fornece o histórico temporal de leituras para renderização no aplicativo Flutter.",
)
def get_device_history(
    device_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Quantidade máxima de registros"),
    hours: Optional[int] = Query(
        24, ge=1, le=720, description="Janela de tempo retroativa em horas (padrão: 24h)"
    ),
    repo: SqlAlchemyTelemetryRepository = Depends(get_telemetry_repository),
) -> List[TelemetryHistoryItemDTO]:
    """Executa o caso de uso de consulta do histórico."""
    use_case = GetHistoryUseCase(repository=repo)
    return use_case.execute(device_id=device_id, limit=limit, hours=hours)
