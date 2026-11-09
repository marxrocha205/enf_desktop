"""Caso de uso para exclusão de cadastro de medicamento e histórico de movimentações."""

from typing import Dict, Any
from domain.interfaces.medication_repository import IMedicationRepository


class DeleteMedicationUseCase:
    """Orquestra a validação e remoção de um medicamento cadastrado no sistema."""

    def __init__(self, repository: IMedicationRepository) -> None:
        self.repository = repository

    def execute(self, medication_id: str) -> Dict[str, Any]:
        """Verifica a existência do medicamento e apaga seu cadastro e histórico."""
        existing = self.repository.get_by_id(medication_id)
        if not existing:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")

        self.repository.delete(medication_id)

        return {
            "id": str(existing.id),
            "name": existing.name,
            "dosage": existing.dosage,
            "message": f"Cadastro do medicamento '{existing.name} ({existing.dosage})' apagado com sucesso.",
        }

