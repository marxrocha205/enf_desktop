"""Data Transfer Objects (DTOs) e validações com Pydantic."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from domain.entities.telemetry import TemperatureStatus


class TelemetryInputDTO(BaseModel):
    """Payload de entrada enviado pelo microcontrolador ESP32."""

    device_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Identificador único do hardware (ex: MAC address ou serial)",
        examples=["esp32_c3_mini_001"],
    )
    temperature: float = Field(
        ...,
        ge=30.0,
        le=45.0,
        description="Temperatura corporal aferida em graus Celsius (°C)",
        examples=[38.3],
    )


class TelemetryResponseDTO(BaseModel):
    """Resposta estruturada após ingestão ou consulta."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: str
    temperature: float
    status: TemperatureStatus
    timestamp: datetime
    message: Optional[str] = None


class TelemetryHistoryItemDTO(BaseModel):
    """Item do histórico de telemetria para o App mobile Flutter."""

    model_config = ConfigDict(from_attributes=True)

    temperature: float
    status: TemperatureStatus
    timestamp: datetime
