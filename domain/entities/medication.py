"""Módulo de entidades do domínio de medicamentos, lotes, validade e controle de estoque."""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


class StockMovementType(str, Enum):
    """Tipo de movimentação física ou lógica de estoque."""

    ENTRADA = "ENTRADA"  # Adição/Entrada de novas unidades (ex: chegada de novo lote)
    SAIDA = "SAIDA"      # Saída/Baixa de unidades (ex: dispensação ao paciente via FEFO)
    AJUSTE = "AJUSTE"    # Ajuste de inventário (correção pontual)


class StockStatus(str, Enum):
    """Classificação do nível de estoque do medicamento."""

    OK = "OK"                      # Estoque suficiente
    LOW = "LOW"                    # Estoque baixo (abaixo do estoque mínimo)
    OUT_OF_STOCK = "OUT_OF_STOCK"  # Estoque zerado


class ExpirationStatus(str, Enum):
    """Classificação da validade de um lote ou medicamento."""

    VALID = "VALID"                  # Dentro do prazo de validade (> 30 dias)
    EXPIRING_SOON = "EXPIRING_SOON"  # Próximo do vencimento (<= 30 dias)
    EXPIRED = "EXPIRED"              # Lote vencido (bloqueado para dispensação)


class AlertLedColor(str, Enum):
    """Cor do LED de aviso para sinalização física no Arduino."""

    GREEN = "GREEN"    # Lote válido e estoque normal
    YELLOW = "YELLOW"  # Atenção: Lote vence em <= 30 dias ou estoque baixo
    RED = "RED"        # Crítico/Bloqueio: Lote vencido ou estoque esgotado


@dataclass(frozen=True)
class MedicationBatch:
    """Entidade representando um lote específico de um medicamento com sua validade e quantidade."""

    medication_id: uuid.UUID
    batch_number: str
    quantity: int
    expiration_date: date
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def days_until_expiration(self) -> int:
        """Retorna a quantidade de dias até o vencimento (negativo se já vencido)."""
        return (self.expiration_date - date.today()).days

    @property
    def is_expired(self) -> bool:
        """Indica se o lote já ultrapassou a data de validade."""
        return self.days_until_expiration < 0

    @property
    def expiration_status(self) -> ExpirationStatus:
        """Calcula o status de validade do lote (VALID, EXPIRING_SOON ou EXPIRED)."""
        days = self.days_until_expiration
        if days < 0:
            return ExpirationStatus.EXPIRED
        if days <= 30:
            return ExpirationStatus.EXPIRING_SOON
        return ExpirationStatus.VALID

    @classmethod
    def create(
        cls,
        medication_id: uuid.UUID,
        batch_number: str,
        quantity: int,
        expiration_date: date,
        batch_id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
    ) -> "MedicationBatch":
        """Factory method para criação e validação de um lote de medicamento."""
        clean_batch = batch_number.strip().upper() if batch_number else ""
        if not clean_batch:
            raise ValueError("O código do lote é obrigatório (ex: LOTE-2026A).")
        if len(clean_batch) > 80:
            raise ValueError("O código do lote não pode exceder 80 caracteres.")
        if quantity < 0:
            raise ValueError(f"A quantidade do lote não pode ser negativa ({quantity}).")

        return cls(
            id=batch_id or uuid.uuid4(),
            medication_id=medication_id,
            batch_number=clean_batch,
            quantity=quantity,
            expiration_date=expiration_date,
            created_at=created_at or datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class StockMovement:
    """Entidade pura que registra cada comando ou evento de movimentação de estoque."""

    medication_id: uuid.UUID
    movement_type: StockMovementType
    quantity: int
    previous_stock: int
    new_stock: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        medication_id: uuid.UUID,
        movement_type: StockMovementType,
        quantity: int,
        previous_stock: int,
        new_stock: int,
        reason: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        batch_number: Optional[str] = None,
        movement_id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
    ) -> "StockMovement":
        """Factory method para criação de registro de movimentação de estoque."""
        if quantity <= 0 and movement_type != StockMovementType.AJUSTE:
            raise ValueError("A quantidade movimentada deve ser maior que zero.")

        return cls(
            id=movement_id or uuid.uuid4(),
            medication_id=medication_id,
            movement_type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            batch_id=batch_id,
            batch_number=batch_number.strip().upper() if batch_number else None,
            reason=reason.strip() if reason else None,
            created_at=created_at or datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class Medication:
    """Entidade de domínio representando um medicamento cadastrado e seu saldo em estoque."""

    name: str
    dosage: str
    unit: str = "comprimido"
    current_stock: int = 0
    minimum_stock: int = 10
    description: Optional[str] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    @classmethod
    def validate_name(cls, name: str) -> str:
        """Valida o nome do medicamento."""
        clean_name = name.strip() if name else ""
        if len(clean_name) < 2:
            raise ValueError("O nome do medicamento deve conter ao menos 2 caracteres.")
        if len(clean_name) > 150:
            raise ValueError("O nome do medicamento não pode exceder 150 caracteres.")
        return clean_name

    @classmethod
    def validate_dosage(cls, dosage: str) -> str:
        """Valida a especificação de dosagem."""
        clean_dosage = dosage.strip() if dosage else ""
        if not clean_dosage:
            raise ValueError("A dosagem do medicamento é obrigatória (ex: 500mg, 10mg/ml).")
        return clean_dosage

    @property
    def stock_status(self) -> StockStatus:
        """Calcula o status atual de criticidade do estoque."""
        if self.current_stock <= 0:
            return StockStatus.OUT_OF_STOCK
        elif self.current_stock <= self.minimum_stock:
            return StockStatus.LOW
        return StockStatus.OK

    @classmethod
    def create(
        cls,
        name: str,
        dosage: str,
        unit: str = "comprimido",
        current_stock: int = 0,
        minimum_stock: int = 10,
        description: Optional[str] = None,
        medication_id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> "Medication":
        """Factory method com validação das regras de negócio."""
        valid_name = cls.validate_name(name)
        valid_dosage = cls.validate_dosage(dosage)

        if current_stock < 0:
            raise ValueError(f"O estoque inicial não pode ser negativo ({current_stock}).")

        if minimum_stock < 0:
            raise ValueError(f"O estoque mínimo de segurança não pode ser negativo ({minimum_stock}).")

        return cls(
            id=medication_id or uuid.uuid4(),
            name=valid_name,
            dosage=valid_dosage,
            unit=unit.strip() if unit else "comprimido",
            current_stock=current_stock,
            minimum_stock=minimum_stock,
            description=description.strip() if description else None,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at,
        )

    def update(
        self,
        name: Optional[str] = None,
        dosage: Optional[str] = None,
        unit: Optional[str] = None,
        minimum_stock: Optional[int] = None,
        description: Optional[str] = None,
    ) -> "Medication":
        """Retorna uma nova instância imutável com os dados cadastrais atualizados."""
        new_name = self.validate_name(name) if name is not None else self.name
        new_dosage = self.validate_dosage(dosage) if dosage is not None else self.dosage
        new_unit = unit.strip() if unit is not None and unit.strip() else self.unit

        new_min_stock = self.minimum_stock
        if minimum_stock is not None:
            if minimum_stock < 0:
                raise ValueError(f"O estoque mínimo de segurança não pode ser negativo ({minimum_stock}).")
            new_min_stock = minimum_stock

        new_description = self.description
        if description is not None:
            new_description = description.strip() if description.strip() else None

        return Medication(
            id=self.id,
            name=new_name,
            dosage=new_dosage,
            unit=new_unit,
            current_stock=self.current_stock,
            minimum_stock=new_min_stock,
            description=new_description,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
        )

    def apply_stock_movement(
        self,
        quantity: int,
        movement_type: StockMovementType,
    ) -> int:
        """Calcula e valida o novo saldo de estoque baseado no tipo de comando de movimentação."""
        if movement_type == StockMovementType.ENTRADA:
            if quantity <= 0:
                raise ValueError("A quantidade para comando de ENTRADA deve ser positiva.")
            return self.current_stock + quantity

        elif movement_type == StockMovementType.SAIDA:
            if quantity <= 0:
                raise ValueError("A quantidade para comando de SAÍDA deve ser positiva.")
            if self.current_stock < quantity:
                raise ValueError(
                    f"Estoque insuficiente de '{self.name} {self.dosage}'. "
                    f"Saldo disponível: {self.current_stock}, Saída solicitada: {quantity}."
                )
            return self.current_stock - quantity

        elif movement_type == StockMovementType.AJUSTE:
            if quantity < 0:
                raise ValueError("O novo saldo em comando de AJUSTE não pode ser negativo.")
            return quantity

        raise ValueError(f"Tipo de movimentação desconhecido: '{movement_type}'.")
