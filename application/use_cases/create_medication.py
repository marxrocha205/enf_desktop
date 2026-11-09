"""Caso de uso para cadastro de medicamento com lote inicial e comando automático de estoque."""

from datetime import date, timedelta
from domain.entities.medication import (
    Medication,
    MedicationBatch,
    StockMovement,
    StockMovementType,
)
from domain.interfaces.medication_repository import IMedicationRepository
from application.dtos.medication_dto import (
    MedicationCreateInputDTO,
    MedicationResponseDTO,
    build_medication_response_dto,
)


class CreateMedicationUseCase:
    """Orquestra o cadastro de novos medicamentos, cria o primeiro lote e dispara a entrada de estoque."""

    def __init__(self, repository: IMedicationRepository) -> None:
        self.repository = repository

    def execute(self, dto: MedicationCreateInputDTO) -> MedicationResponseDTO:
        """Cadastra o medicamento, registra o lote inicial com validade e audita a movimentação."""
        # 1. Verifica se já existe medicamento cadastrado com o mesmo nome e dosagem
        existing = self.repository.get_by_name_and_dosage(dto.name, dto.dosage)
        if existing:
            raise ValueError(
                f"O medicamento '{dto.name}' com dosagem '{dto.dosage}' já está cadastrado no sistema (ID: {existing.id})."
            )

        # 2. Cria a entidade Medication aplicando regras de negócio
        medication_entity = Medication.create(
            name=dto.name,
            dosage=dto.dosage,
            unit=dto.unit,
            current_stock=dto.initial_stock,
            minimum_stock=dto.minimum_stock,
            description=dto.description,
        )

        # 3. Salva o medicamento no repositório
        saved_medication = self.repository.create(medication_entity)

        created_batches = []
        # 4. Se houver estoque inicial ou lote informado, cria o registro do lote com validade
        if dto.initial_stock > 0 or dto.batch_number or dto.expiration_date:
            batch_num = (
                dto.batch_number.strip().upper()
                if dto.batch_number and dto.batch_number.strip()
                else f"LOTE-{date.today().strftime('%Y%m')}-01"
            )
            exp_date = dto.expiration_date or (date.today() + timedelta(days=365))

            batch_entity = MedicationBatch.create(
                medication_id=saved_medication.id,
                batch_number=batch_num,
                quantity=dto.initial_stock,
                expiration_date=exp_date,
            )
            saved_batch = self.repository.create_batch(batch_entity)
            created_batches.append(saved_batch)

            if dto.initial_stock > 0:
                initial_movement = StockMovement.create(
                    medication_id=saved_medication.id,
                    batch_id=saved_batch.id,
                    batch_number=saved_batch.batch_number,
                    movement_type=StockMovementType.ENTRADA,
                    quantity=dto.initial_stock,
                    previous_stock=0,
                    new_stock=dto.initial_stock,
                    reason=(
                        f"Entrada inicial do lote {saved_batch.batch_number} "
                        f"(Validade: {saved_batch.expiration_date.strftime('%d/%m/%Y')})"
                    ),
                )
                self.repository.record_movement(initial_movement)

        # 5. Retorna o DTO completo com lotes, validade e cor do LED
        return build_medication_response_dto(saved_medication, created_batches)
