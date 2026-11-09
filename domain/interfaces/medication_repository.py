"""Contrato de repositório para persistência de medicamentos, lotes, validade e movimentações de estoque."""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.medication import Medication, MedicationBatch, StockMovement


class IMedicationRepository(ABC):
    """Interface abstrata para operações de banco de dados de medicamentos, lotes e estoque."""

    @abstractmethod
    def create(self, medication: Medication) -> Medication:
        """Persiste um novo medicamento no banco de dados."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, medication_id: str) -> Optional[Medication]:
        """Recupera um medicamento pelo seu UUID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_name_and_dosage(self, name: str, dosage: str) -> Optional[Medication]:
        """Recupera um medicamento pelo nome e dosagem para evitar duplicidades."""
        raise NotImplementedError

    @abstractmethod
    def list_all(
        self, limit: int = 100, offset: int = 0, low_stock_only: bool = False
    ) -> List[Medication]:
        """Lista medicamentos cadastrados, com opção de filtrar apenas estoque crítico/baixo."""
        raise NotImplementedError

    @abstractmethod
    def update_stock(self, medication_id: str, new_stock: int) -> Medication:
        """Atualiza a quantidade em estoque do medicamento."""
        raise NotImplementedError

    @abstractmethod
    def update(self, medication: Medication) -> Medication:
        """Atualiza os dados cadastrais de um medicamento no banco de dados."""
        raise NotImplementedError

    @abstractmethod
    def create_batch(self, batch: MedicationBatch) -> MedicationBatch:
        """Registra um novo lote de medicamento com quantidade e data de validade."""
        raise NotImplementedError

    @abstractmethod
    def get_batch_by_id(self, batch_id: str) -> Optional[MedicationBatch]:
        """Recupera um lote pelo seu UUID."""
        raise NotImplementedError

    @abstractmethod
    def get_batch_by_number(
        self, medication_id: str, batch_number: str
    ) -> Optional[MedicationBatch]:
        """Recupera um lote específico de um medicamento pelo número do lote."""
        raise NotImplementedError

    @abstractmethod
    def find_batch_by_code(self, batch_number: str) -> Optional[MedicationBatch]:
        """Busca um lote diretamente pelo código do lote (ex: leitura do scanner)."""
        raise NotImplementedError

    @abstractmethod
    def list_batches(self, medication_id: str) -> List[MedicationBatch]:
        """Lista todos os lotes de um medicamento ordenados pela data de validade mais próxima (FEFO)."""
        raise NotImplementedError

    @abstractmethod
    def update_batch_quantity(self, batch_id: str, new_quantity: int) -> MedicationBatch:
        """Atualiza a quantidade disponível em um lote específico."""
        raise NotImplementedError

    @abstractmethod
    def record_movement(self, movement: StockMovement) -> StockMovement:
        """Registra uma transação ou comando de movimentação de estoque."""
        raise NotImplementedError

    @abstractmethod
    def get_movements(self, medication_id: str, limit: int = 50) -> List[StockMovement]:
        """Recupera o histórico cronológico de movimentações de estoque do medicamento."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, medication_id: str) -> None:
        """Remove um medicamento e seu histórico de lotes/movimentações do banco de dados."""
        raise NotImplementedError
