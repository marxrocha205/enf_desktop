"""DTOs de entrada e saída."""

from application.dtos.telemetry_dto import (
    TelemetryInputDTO,
    TelemetryResponseDTO,
    TelemetryHistoryItemDTO,
)
from application.dtos.medication_dto import (
    MedicationCreateInputDTO,
    MedicationUpdateInputDTO,
    StockUpdateCommandDTO,
    StockMovementResponseDTO,
    MedicationResponseDTO,
    QRCodeScanInputDTO,
    QRCodeParsedMedicationDTO,
    QRCodeResolveResponseDTO,
)

__all__ = [
    "TelemetryInputDTO",
    "TelemetryResponseDTO",
    "TelemetryHistoryItemDTO",
    "MedicationCreateInputDTO",
    "MedicationUpdateInputDTO",
    "StockUpdateCommandDTO",
    "StockMovementResponseDTO",
    "MedicationResponseDTO",
    "QRCodeScanInputDTO",
    "QRCodeParsedMedicationDTO",
    "QRCodeResolveResponseDTO",
]
