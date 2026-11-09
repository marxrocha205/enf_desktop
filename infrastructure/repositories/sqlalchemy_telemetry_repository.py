"""Implementação concreta do repositório de telemetria utilizando SQLAlchemy."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from domain.entities.telemetry import TelemetryReading, TemperatureStatus
from domain.interfaces.telemetry_repository import ITelemetryRepository
from infrastructure.database.models import DeviceModel, TemperatureReadingModel


class SqlAlchemyTelemetryRepository(ITelemetryRepository):
    """Repositório SQLAlchemy para persistência de dados de telemetria."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _ensure_device_exists(self, device_id: str) -> None:
        """Garante a existência do dispositivo para satisfazer restrições relacionais."""
        device = self.db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
        if not device:
            new_device = DeviceModel(id=device_id, is_active=True)
            self.db.add(new_device)
            self.db.flush()

    def save(self, reading: TelemetryReading) -> TelemetryReading:
        """Persiste uma leitura no banco de dados relacional."""
        self._ensure_device_exists(reading.device_id)

        model = TemperatureReadingModel(
            id=str(reading.id),
            device_id=reading.device_id,
            temperature=reading.temperature,
            status=reading.status.value,
            timestamp=reading.timestamp,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return TelemetryReading(
            id=uuid.UUID(model.id),
            device_id=model.device_id,
            temperature=model.temperature,
            status=TemperatureStatus(model.status),
            timestamp=model.timestamp,
        )

    def get_by_device_id(
        self, device_id: str, limit: int = 100, hours: Optional[int] = None
    ) -> List[TelemetryReading]:
        """Consulta as leituras mais recentes de um dispositivo filtradas por janela de tempo."""
        query = self.db.query(TemperatureReadingModel).filter(
            TemperatureReadingModel.device_id == device_id
        )

        if hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = query.filter(TemperatureReadingModel.timestamp >= cutoff)

        results = (
            query.order_by(TemperatureReadingModel.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            TelemetryReading(
                id=uuid.UUID(r.id),
                device_id=r.device_id,
                temperature=r.temperature,
                status=TemperatureStatus(r.status),
                timestamp=r.timestamp,
            )
            for r in results
        ]
