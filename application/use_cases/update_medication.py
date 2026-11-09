"""Caso de uso para atualização de dados cadastrais de medicamentos."""

from domain.interfaces.medication_repository import IMedicationRepository
from application.dtos.medication_dto import (
    MedicationUpdateInputDTO,
    MedicationResponseDTO,
    build_medication_response_dto,
)


class UpdateMedicationUseCase:
    """Orquestra a atualização dos dados cadastrais do medicamento no catálogo."""

    def __init__(self, repository: IMedicationRepository) -> None:
        self.repository = repository

    def execute(
        self, medication_id: str, dto: MedicationUpdateInputDTO
    ) -> MedicationResponseDTO:
        """Atualiza informações cadastrais de um medicamento com validações de unicidade e integridade."""
        # 1. Recupera o medicamento existente
        medication = self.repository.get_by_id(medication_id)
        if not medication:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")

        # 2. Se name ou dosage forem alterados, verifica se não conflita com outro medicamento já cadastrado
        target_name = dto.name if dto.name is not None else medication.name
        target_dosage = dto.dosage if dto.dosage is not None else medication.dosage

        name_changed = target_name.strip().lower() != medication.name.strip().lower()
        dosage_changed = target_dosage.strip().lower() != medication.dosage.strip().lower()

        if name_changed or dosage_changed:
            existing = self.repository.get_by_name_and_dosage(target_name, target_dosage)
            if existing and str(existing.id) != str(medication.id):
                raise ValueError(
                    f"Já existe outro medicamento cadastrado com o nome '{target_name}' e dosagem '{target_dosage}' (ID: {existing.id})."
                )

        # 3. Atualiza a entidade aplicando regras de negócio
        updated_entity = medication.update(
            name=dto.name,
            dosage=dto.dosage,
            unit=dto.unit,
            minimum_stock=dto.minimum_stock,
            description=dto.description,
        )

        # 4. Salva no repositório
        saved = self.repository.update(updated_entity)
        batches = self.repository.list_batches(str(saved.id))

        # 5. Retorna o DTO com o status de criticidade e lotes recalculados
        return build_medication_response_dto(saved, batches)
