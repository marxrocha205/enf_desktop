"""Modelos relacionais ORM mapeados via SQLAlchemy."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from infrastructure.database.connection import Base


class DeviceModel(Base):
    """Tabela de equipamentos IoT de monitoramento corporal."""

    __tablename__ = "devices"

    id = Column(String(64), primary_key=True)  # MAC Address ou identificador único
    is_active = Column(Boolean, default=True, nullable=False)

    readings = relationship("TemperatureReadingModel", back_populates="device")


class TemperatureReadingModel(Base):
    """Tabela de histórico de leituras de telemetria corporal."""

    __tablename__ = "temperature_readings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    device = relationship("DeviceModel", back_populates="readings")

    __table_args__ = (
        Index("idx_device_timestamp", "device_id", "timestamp"),
    )


class MedicationModel(Base):
    """Tabela de medicamentos cadastrados e controle de estoque."""

    __tablename__ = "medications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    barcode = Column(String(100), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    dosage = Column(String(50), nullable=False)
    unit = Column(String(30), default="comprimido", nullable=False)
    current_stock = Column(Integer, default=0, nullable=False)
    minimum_stock = Column(Integer, default=10, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    batches = relationship(
        "MedicationBatchModel",
        back_populates="medication",
        cascade="all, delete-orphan",
        order_by="asc(MedicationBatchModel.expiration_date)",
    )

    movements = relationship(
        "StockMovementModel",
        back_populates="medication",
        cascade="all, delete-orphan",
        order_by="desc(StockMovementModel.created_at)",
    )

    __table_args__ = (
        Index("idx_medication_name_dosage", "name", "dosage"),
    )


class MedicationBatchModel(Base):
    """Tabela de lotes de medicamentos com quantidade por lote e data de validade."""

    __tablename__ = "medication_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("medications.id"), nullable=False, index=True)
    batch_number = Column(String(80), nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    expiration_date = Column(Date, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    medication = relationship("MedicationModel", back_populates="batches")

    __table_args__ = (
        Index("idx_batch_med_number", "medication_id", "batch_number"),
    )


class StockMovementModel(Base):
    """Tabela de histórico e auditoria de comandos de movimentação de estoque."""

    __tablename__ = "stock_movements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("medications.id"), nullable=False, index=True)
    batch_id = Column(String(36), ForeignKey("medication_batches.id"), nullable=True, index=True)
    batch_number = Column(String(80), nullable=True)
    movement_type = Column(String(20), nullable=False)  # ENTRADA, SAIDA, AJUSTE
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    medication = relationship("MedicationModel", back_populates="movements")
