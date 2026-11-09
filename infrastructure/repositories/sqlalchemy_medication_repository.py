"""Implementação concreta do repositório de medicamentos, lotes e estoque via SQLAlchemy."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session

from domain.entities.medication import (
    Medication,
    MedicationBatch,
    StockMovement,
    StockMovementType,
)
from domain.interfaces.medication_repository import IMedicationRepository
from infrastructure.database.models import (
    MedicationModel,
    MedicationBatchModel,
    StockMovementModel,
)


class SqlAlchemyMedicationRepository(IMedicationRepository):
    """Repositório SQLAlchemy para gerenciamento de catálogo de medicamentos, lotes e movimentações."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _to_entity(self, model: MedicationModel) -> Medication:
        """Converte o modelo relacional MedicationModel para a entidade pura Medication."""
        return Medication(
            id=uuid.UUID(model.id),
            name=model.name,
            dosage=model.dosage,
            unit=model.unit,
            current_stock=model.current_stock,
            minimum_stock=model.minimum_stock,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_batch_entity(self, model: MedicationBatchModel) -> MedicationBatch:
        """Converte o modelo relacional MedicationBatchModel para a entidade MedicationBatch."""
        return MedicationBatch(
            id=uuid.UUID(model.id),
            medication_id=uuid.UUID(model.medication_id),
            batch_number=model.batch_number,
            quantity=model.quantity,
            expiration_date=model.expiration_date,
            created_at=model.created_at,
        )

    def _to_movement_entity(self, model: StockMovementModel) -> StockMovement:
        """Converte o modelo relacional StockMovementModel para a entidade StockMovement."""
        return StockMovement(
            id=uuid.UUID(model.id),
            medication_id=uuid.UUID(model.medication_id),
            batch_id=uuid.UUID(model.batch_id) if model.batch_id else None,
            batch_number=model.batch_number,
            movement_type=StockMovementType(model.movement_type),
            quantity=model.quantity,
            previous_stock=model.previous_stock,
            new_stock=model.new_stock,
            reason=model.reason,
            created_at=model.created_at,
        )

    def create(self, medication: Medication) -> Medication:
        """Persiste um novo medicamento no catálogo."""
        model = MedicationModel(
            id=str(medication.id),
            name=medication.name,
            dosage=medication.dosage,
            unit=medication.unit,
            current_stock=medication.current_stock,
            minimum_stock=medication.minimum_stock,
            description=medication.description,
            created_at=medication.created_at,
            updated_at=medication.updated_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, medication_id: str) -> Optional[Medication]:
        """Recupera um medicamento pelo identificador UUID."""
        model = (
            self.db.query(MedicationModel)
            .filter(MedicationModel.id == medication_id)
            .first()
        )
        return self._to_entity(model) if model else None

    def get_by_name_and_dosage(self, name: str, dosage: str) -> Optional[Medication]:
        """Recupera um medicamento pelo nome e dosagem (case-insensitive)."""
        clean_name = name.strip().lower()
        clean_dosage = dosage.strip().lower()
        model = (
            self.db.query(MedicationModel)
            .filter(
                MedicationModel.name.ilike(clean_name),
                MedicationModel.dosage.ilike(clean_dosage),
            )
            .first()
        )
        return self._to_entity(model) if model else None

    def list_all(
        self, limit: int = 100, offset: int = 0, low_stock_only: bool = False
    ) -> List[Medication]:
        """Retorna a listagem de medicamentos cadastrados com filtros opcionais de estoque."""
        query = self.db.query(MedicationModel)
        if low_stock_only:
            query = query.filter(MedicationModel.current_stock <= MedicationModel.minimum_stock)

        models = (
            query.order_by(MedicationModel.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def update_stock(self, medication_id: str, new_stock: int) -> Medication:
        """Atualiza a quantidade em estoque do medicamento."""
        model = (
            self.db.query(MedicationModel)
            .filter(MedicationModel.id == medication_id)
            .first()
        )
        if not model:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")

        model.current_stock = new_stock
        model.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def update(self, medication: Medication) -> Medication:
        """Atualiza os dados cadastrais do medicamento no banco de dados."""
        model = (
            self.db.query(MedicationModel)
            .filter(MedicationModel.id == str(medication.id))
            .first()
        )
        if not model:
            raise ValueError(f"Medicamento com ID '{medication.id}' não encontrado.")

        model.name = medication.name
        model.dosage = medication.dosage
        model.unit = medication.unit
        model.minimum_stock = medication.minimum_stock
        model.description = medication.description
        model.updated_at = medication.updated_at or datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def create_batch(self, batch: MedicationBatch) -> MedicationBatch:
        """Persiste um novo lote de medicamento."""
        model = MedicationBatchModel(
            id=str(batch.id),
            medication_id=str(batch.medication_id),
            batch_number=batch.batch_number,
            quantity=batch.quantity,
            expiration_date=batch.expiration_date,
            created_at=batch.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_batch_entity(model)

    def get_batch_by_id(self, batch_id: str) -> Optional[MedicationBatch]:
        """Recupera um lote pelo ID."""
        model = (
            self.db.query(MedicationBatchModel)
            .filter(MedicationBatchModel.id == batch_id)
            .first()
        )
        return self._to_batch_entity(model) if model else None

    def get_batch_by_number(
        self, medication_id: str, batch_number: str
    ) -> Optional[MedicationBatch]:
        """Recupera um lote específico de um medicamento pelo número do lote."""
        clean_num = batch_number.strip().upper()
        model = (
            self.db.query(MedicationBatchModel)
            .filter(
                MedicationBatchModel.medication_id == medication_id,
                MedicationBatchModel.batch_number.ilike(clean_num),
            )
            .first()
        )
        return self._to_batch_entity(model) if model else None

    def find_batch_by_code(self, batch_number: str) -> Optional[MedicationBatch]:
        """Busca um lote diretamente pelo código do lote."""
        clean_num = batch_number.strip().upper()
        model = (
            self.db.query(MedicationBatchModel)
            .filter(MedicationBatchModel.batch_number.ilike(clean_num))
            .order_by(MedicationBatchModel.expiration_date.asc())
            .first()
        )
        return self._to_batch_entity(model) if model else None

    def list_batches(self, medication_id: str) -> List[MedicationBatch]:
        """Lista os lotes de um medicamento ordenados pela data de validade mais próxima (FEFO)."""
        models = (
            self.db.query(MedicationBatchModel)
            .filter(MedicationBatchModel.medication_id == medication_id)
            .order_by(
                MedicationBatchModel.expiration_date.asc(),
                MedicationBatchModel.created_at.asc(),
            )
            .all()
        )
        return [self._to_batch_entity(m) for m in models]

    def update_batch_quantity(self, batch_id: str, new_quantity: int) -> MedicationBatch:
        """Atualiza o saldo de unidades de um lote."""
        model = (
            self.db.query(MedicationBatchModel)
            .filter(MedicationBatchModel.id == batch_id)
            .first()
        )
        if not model:
            raise ValueError(f"Lote com ID '{batch_id}' não encontrado.")

        model.quantity = new_quantity
        self.db.commit()
        self.db.refresh(model)
        return self._to_batch_entity(model)

    def record_movement(self, movement: StockMovement) -> StockMovement:
        """Registra a transação de movimentação no histórico de estoque."""
        model = StockMovementModel(
            id=str(movement.id),
            medication_id=str(movement.medication_id),
            batch_id=str(movement.batch_id) if movement.batch_id else None,
            batch_number=movement.batch_number,
            movement_type=movement.movement_type.value,
            quantity=movement.quantity,
            previous_stock=movement.previous_stock,
            new_stock=movement.new_stock,
            reason=movement.reason,
            created_at=movement.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_movement_entity(model)

    def get_movements(self, medication_id: str, limit: int = 50) -> List[StockMovement]:
        """Consulta as últimas movimentações de estoque registradas para o medicamento."""
        models = (
            self.db.query(StockMovementModel)
            .filter(StockMovementModel.medication_id == medication_id)
            .order_by(StockMovementModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_movement_entity(m) for m in models]

    def delete(self, medication_id: str) -> None:
        """Remove o cadastro do medicamento e seus lotes/movimentações associadas (cascade)."""
        model = (
            self.db.query(MedicationModel)
            .filter(MedicationModel.id == medication_id)
            .first()
        )
        if not model:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado para exclusão.")

        self.db.delete(model)
        self.db.commit()
