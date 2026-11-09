"""Caso de uso para consulta e listagem do catálogo de medicamentos, lotes, validade e movimentações."""

from datetime import date
import json
import re
from typing import List
from domain.interfaces.medication_repository import IMedicationRepository
from application.dtos.medication_dto import (
    MedicationBatchResponseDTO,
    MedicationResponseDTO,
    StockMovementResponseDTO,
    QRCodeParsedMedicationDTO,
    QRCodeResolveResponseDTO,
    build_batch_response_dto,
    build_medication_response_dto,
)


class ListMedicationsUseCase:
    """Gerencia consultas de catálogo de medicamentos, lotes por validade e histórico de estoque."""

    def __init__(self, repository: IMedicationRepository) -> None:
        self.repository = repository

    def list_all(
        self, limit: int = 100, offset: int = 0, low_stock_only: bool = False
    ) -> List[MedicationResponseDTO]:
        """Lista medicamentos cadastrados com seus lotes e status de validade/estoque."""
        items = self.repository.list_all(
            limit=limit, offset=offset, low_stock_only=low_stock_only
        )
        result: List[MedicationResponseDTO] = []
        for m in items:
            batches = self.repository.list_batches(str(m.id))
            result.append(build_medication_response_dto(m, batches))
        return result

    def get_by_id(self, medication_id: str) -> MedicationResponseDTO:
        """Obtém detalhes de um medicamento pelo ID, incluindo todos os seus lotes."""
        medication = self.repository.get_by_id(medication_id)
        if not medication:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")

        batches = self.repository.list_batches(str(medication.id))
        return build_medication_response_dto(medication, batches)

    def get_batches(self, medication_id: str) -> List[MedicationBatchResponseDTO]:
        """Lista todos os lotes de um medicamento específico ordenados por validade (FEFO)."""
        medication = self.repository.get_by_id(medication_id)
        if not medication:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")
        batches = self.repository.list_batches(medication_id)
        return [build_batch_response_dto(b, medication=medication) for b in batches]

    def get_batch_by_code(self, batch_number: str) -> MedicationBatchResponseDTO:
        """Identifica a qual lote e a qual medicamento pertence uma caixa/código de lote."""
        batch = self.repository.find_batch_by_code(batch_number)
        if not batch:
            raise ValueError(f"Nenhum lote encontrado com o código '{batch_number}'.")
        medication = self.repository.get_by_id(str(batch.medication_id))
        return build_batch_response_dto(batch, medication=medication)

    def get_movements(
        self, medication_id: str, limit: int = 50
    ) -> List[StockMovementResponseDTO]:
        """Recupera o histórico cronológico de movimentações de estoque do medicamento."""
        self.get_by_id(medication_id)

        movements = self.repository.get_movements(medication_id, limit=limit)
        return [
            StockMovementResponseDTO(
                id=str(mov.id),
                medication_id=str(mov.medication_id),
                batch_id=str(mov.batch_id) if mov.batch_id else None,
                batch_number=mov.batch_number,
                movement_type=mov.movement_type.value,
                quantity=mov.quantity,
                previous_stock=mov.previous_stock,
                new_stock=mov.new_stock,
                reason=mov.reason,
                created_at=mov.created_at,
            )
            for mov in movements
        ]

    def resolve_qrcode(self, raw_data: str) -> QRCodeResolveResponseDTO:
        """Interpreta o conteúdo de um QR Code (medicamento ou lote) e verifica se já existe no catálogo."""
        cleaned = (raw_data or "").strip()
        if not cleaned:
            raise ValueError("O conteúdo do QR Code está vazio.")

        parsed = QRCodeParsedMedicationDTO()

        # 1. Tentativa de parse como JSON estruturado
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    parsed.id = str(data["id"]).strip() if data.get("id") else None
                    parsed.name = str(data.get("name") or data.get("medicamento") or "").strip()
                    parsed.dosage = str(data.get("dosage") or data.get("dosagem") or "").strip()
                    parsed.unit = str(data.get("unit") or data.get("unidade") or "comprimido").strip().lower()
                    parsed.initial_stock = int(data.get("initial_stock", data.get("current_stock", 50)) or 50)
                    parsed.minimum_stock = int(data.get("minimum_stock", 15) or 15)
                    parsed.batch_number = (
                        str(data.get("batch_number") or data.get("lote") or "").strip().upper() or None
                    )
                    exp_raw = data.get("expiration_date") or data.get("validade")
                    if exp_raw:
                        try:
                            parsed.expiration_date = date.fromisoformat(str(exp_raw).strip())
                        except Exception:
                            pass
                    parsed.description = str(data["description"]).strip() if data.get("description") else None
            except Exception:
                pass

        # 2. Tentativa de parse separado por pipe (|) ou ponto-e-vírgula (;)
        if not parsed.name and not parsed.id and ("|" in cleaned or ";" in cleaned):
            sep = "|" if "|" in cleaned else ";"
            parts = [p.strip() for p in cleaned.split(sep)]
            if len(parts) >= 2:
                parsed.name = parts[0]
                parsed.dosage = parts[1]
            if len(parts) >= 3 and parts[2]:
                parsed.unit = parts[2].lower()
            if len(parts) >= 4 and parts[3].isdigit():
                parsed.initial_stock = int(parts[3])
            if len(parts) >= 5 and parts[4].isdigit():
                parsed.minimum_stock = int(parts[4])
            if len(parts) >= 6 and parts[5]:
                parsed.description = parts[5]
            if len(parts) >= 7 and parts[6]:
                parsed.batch_number = parts[6].upper()
            if len(parts) >= 8 and parts[7]:
                try:
                    parsed.expiration_date = date.fromisoformat(parts[7])
                except Exception:
                    pass

        # 3. Verifica se o código lido é diretamente um código de lote cadastrado (ex: LOTE-2026A)
        existing_med = None
        matched_batch = self.repository.find_batch_by_code(cleaned)
        if matched_batch:
            existing_med = self.repository.get_by_id(str(matched_batch.medication_id))
            parsed.batch_number = matched_batch.batch_number
            parsed.expiration_date = matched_batch.expiration_date

        # 4. Texto simples: UUID direto ou "Nome Dosagem" (ex: "Dipirona 500mg")
        if not existing_med and not parsed.name and not parsed.id:
            uuid_pattern = re.compile(
                r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
            )
            if uuid_pattern.match(cleaned):
                parsed.id = cleaned
            else:
                dosage_match = re.search(
                    r"\b(\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|ui|%|gotas))\b",
                    cleaned,
                    re.IGNORECASE,
                )
                if dosage_match:
                    parsed.dosage = dosage_match.group(1).replace(" ", "")
                    name_part = (
                        cleaned[: dosage_match.start()] + cleaned[dosage_match.end() :]
                    ).strip(" -–,")
                    parsed.name = name_part or cleaned
                else:
                    parsed.name = cleaned
                    parsed.dosage = "500mg"

        # 5. Busca no repositório por ID ou por Nome + Dosagem
        if not existing_med and parsed.id:
            existing_med = self.repository.get_by_id(parsed.id)
        if not existing_med and parsed.name and parsed.dosage:
            existing_med = self.repository.get_by_name_and_dosage(parsed.name, parsed.dosage)

        if existing_med:
            batches = self.repository.list_batches(str(existing_med.id))
            med_dto = build_medication_response_dto(existing_med, batches)

            # Se o QR Code da caixa/medicamento especificava o lote (ou se o código lido era o próprio lote),
            # identifica exatamente a qual lote esta unidade pertence
            if not matched_batch and parsed.batch_number:
                matched_batch = self.repository.get_batch_by_number(
                    str(existing_med.id), parsed.batch_number
                )

            matched_batch_dto = (
                build_batch_response_dto(matched_batch, medication=existing_med)
                if matched_batch
                else None
            )

            parsed.id = str(existing_med.id)
            parsed.name = existing_med.name
            parsed.dosage = existing_med.dosage
            parsed.unit = existing_med.unit
            parsed.minimum_stock = existing_med.minimum_stock
            parsed.description = existing_med.description
            return QRCodeResolveResponseDTO(
                found=True,
                medication=med_dto,
                matched_batch=matched_batch_dto,
                parsed_data=parsed,
                raw_data=cleaned,
            )

        return QRCodeResolveResponseDTO(
            found=False,
            medication=None,
            matched_batch=None,
            parsed_data=parsed,
            raw_data=cleaned,
        )
