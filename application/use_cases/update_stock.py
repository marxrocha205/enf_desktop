"""Caso de uso para comando de atualização de estoque, gestão de lotes e controle de validade (FEFO)."""

from datetime import date, timedelta
from typing import Optional, Tuple
import uuid
from domain.entities.medication import (
    MedicationBatch,
    StockMovement,
    StockMovementType,
)
from domain.interfaces.medication_repository import IMedicationRepository
from application.dtos.medication_dto import (
    MedicationBatchCreateInputDTO,
    MedicationBatchResponseDTO,
    StockUpdateCommandDTO,
    MedicationResponseDTO,
    StockMovementResponseDTO,
    build_batch_response_dto,
    build_medication_response_dto,
)


class UpdateStockCommandUseCase:
    """Orquestra comandos de movimentação de estoque (Entrada, Saída FEFO com validação de validade e Ajuste)."""

    def __init__(self, repository: IMedicationRepository) -> None:
        self.repository = repository

    def create_batch(
        self, medication_id: str, dto: MedicationBatchCreateInputDTO
    ) -> Tuple[MedicationResponseDTO, MedicationBatchResponseDTO, StockMovementResponseDTO]:
        """Cadastra um novo lote de um medicamento (ex: 50 caixas de Dipirona) e atualiza o estoque total."""
        command = StockUpdateCommandDTO(
            movement_type=StockMovementType.ENTRADA,
            quantity=dto.quantity,
            batch_number=dto.batch_number,
            expiration_date=dto.expiration_date,
            reason=dto.reason or f"Entrada do lote {dto.batch_number.strip().upper()} ({dto.quantity} un)",
        )
        med_dto, mov_dto = self.execute(medication_id=medication_id, command=command)
        batch = self.repository.get_batch_by_number(medication_id, dto.batch_number)
        if not batch:
            raise ValueError("Falha ao recuperar o lote recém-criado.")
        med_entity = self.repository.get_by_id(medication_id)
        return med_dto, build_batch_response_dto(batch, medication=med_entity), mov_dto

    def execute(
        self, medication_id: str, command: StockUpdateCommandDTO
    ) -> Tuple[MedicationResponseDTO, StockMovementResponseDTO]:
        """Executa a movimentação de estoque respeitando lotes e validade (FEFO)."""
        # 1. Recupera o medicamento
        medication = self.repository.get_by_id(medication_id)
        if not medication:
            raise ValueError(f"Medicamento com ID '{medication_id}' não encontrado.")

        previous_stock = medication.current_stock
        new_stock = medication.apply_stock_movement(
            quantity=command.quantity,
            movement_type=command.movement_type,
        )

        affected_batch_id: Optional[str] = None
        affected_batch_number: Optional[str] = None
        batches = self.repository.list_batches(medication_id)

        # 2. Lógica de Lotes por tipo de movimentação
        if command.movement_type == StockMovementType.ENTRADA:
            target_batch_num = (
                command.batch_number.strip().upper()
                if command.batch_number and command.batch_number.strip()
                else None
            )

            if target_batch_num:
                existing_batch = self.repository.get_batch_by_number(
                    medication_id, target_batch_num
                )
                if existing_batch:
                    updated_batch = self.repository.update_batch_quantity(
                        str(existing_batch.id),
                        existing_batch.quantity + command.quantity,
                    )
                    affected_batch_id = str(updated_batch.id)
                    affected_batch_number = updated_batch.batch_number
                else:
                    exp_date = command.expiration_date or (date.today() + timedelta(days=365))
                    new_batch = MedicationBatch.create(
                        medication_id=medication.id,
                        batch_number=target_batch_num,
                        quantity=command.quantity,
                        expiration_date=exp_date,
                    )
                    saved_batch = self.repository.create_batch(new_batch)
                    affected_batch_id = str(saved_batch.id)
                    affected_batch_number = saved_batch.batch_number
            else:
                # Se não informou número do lote na entrada, adiciona ao lote válido mais recente ou cria um novo
                valid_batches = [b for b in batches if not b.is_expired]
                if valid_batches:
                    target = valid_batches[-1]
                    updated_batch = self.repository.update_batch_quantity(
                        str(target.id), target.quantity + command.quantity
                    )
                    affected_batch_id = str(updated_batch.id)
                    affected_batch_number = updated_batch.batch_number
                else:
                    auto_num = f"LOTE-{date.today().strftime('%Y%m')}-{len(batches) + 1:02d}"
                    exp_date = command.expiration_date or (date.today() + timedelta(days=365))
                    new_batch = MedicationBatch.create(
                        medication_id=medication.id,
                        batch_number=auto_num,
                        quantity=command.quantity,
                        expiration_date=exp_date,
                    )
                    saved_batch = self.repository.create_batch(new_batch)
                    affected_batch_id = str(saved_batch.id)
                    affected_batch_number = saved_batch.batch_number

        elif command.movement_type == StockMovementType.SAIDA:
            target_batch_num = (
                command.batch_number.strip().upper()
                if command.batch_number and command.batch_number.strip()
                else None
            )

            if target_batch_num:
                # Saída direcionada a um lote específico (ex: bipou o código do lote)
                batch = self.repository.get_batch_by_number(medication_id, target_batch_num)
                if not batch:
                    raise ValueError(
                        f"O lote '{target_batch_num}' não foi encontrado para '{medication.name} {medication.dosage}'."
                    )
                if batch.is_expired:
                    raise ValueError(
                        f"BLOQUEIO DE SEGURANÇA (VALIDADE): O lote '{batch.batch_number}' de "
                        f"'{medication.name} {medication.dosage}' está VENCIDO desde "
                        f"{batch.expiration_date.strftime('%d/%m/%Y')}! Separe o lote para descarte."
                    )
                if batch.quantity < command.quantity:
                    raise ValueError(
                        f"Saldo insuficiente no lote '{batch.batch_number}'. "
                        f"Disponível no lote: {batch.quantity}, solicitado: {command.quantity}."
                    )
                self.repository.update_batch_quantity(
                    str(batch.id), batch.quantity - command.quantity
                )
                affected_batch_id = str(batch.id)
                affected_batch_number = batch.batch_number
            elif batches:
                # Saída automática FEFO (First Expired, First Out) dentre os lotes não vencidos
                active_batches = [b for b in batches if b.quantity > 0]
                valid_active_batches = [b for b in active_batches if not b.is_expired]
                expired_active_batches = [b for b in active_batches if b.is_expired]

                total_valid_qty = sum(b.quantity for b in valid_active_batches)
                if total_valid_qty < command.quantity:
                    if expired_active_batches:
                        exp_info = ", ".join(
                            f"{b.batch_number} (venceu em {b.expiration_date.strftime('%d/%m/%Y')}: {b.quantity} un)"
                            for b in expired_active_batches
                        )
                        raise ValueError(
                            f"BLOQUEIO DE SEGURANÇA (VALIDADE): Saldo válido insuficiente ({total_valid_qty} un). "
                            f"Há unidades retidas em lote(s) VENCIDO(S): {exp_info}."
                        )

                remaining_to_deduct = command.quantity
                used_batch_numbers = []
                for b in valid_active_batches:
                    if remaining_to_deduct <= 0:
                        break
                    deduct = min(b.quantity, remaining_to_deduct)
                    self.repository.update_batch_quantity(str(b.id), b.quantity - deduct)
                    remaining_to_deduct -= deduct
                    if not affected_batch_id:
                        affected_batch_id = str(b.id)
                    used_batch_numbers.append(b.batch_number)

                if used_batch_numbers:
                    affected_batch_number = ", ".join(used_batch_numbers)

        # 3. Registra o comando de movimentação no histórico
        movement_reason = command.reason or f"Comando de {command.movement_type.value} de estoque"
        if affected_batch_number and f"Lote {affected_batch_number}" not in movement_reason:
            movement_reason = f"{movement_reason} [Lote: {affected_batch_number}]"

        movement_entity = StockMovement.create(
            medication_id=medication.id,
            batch_id=uuid.UUID(affected_batch_id) if affected_batch_id else None,
            batch_number=affected_batch_number,
            movement_type=command.movement_type,
            quantity=command.quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=movement_reason,
        )
        saved_movement = self.repository.record_movement(movement_entity)

        # 4. Atualiza o saldo total no registro do medicamento
        updated_medication = self.repository.update_stock(medication_id, new_stock)
        updated_batches = self.repository.list_batches(medication_id)

        # 5. Mapeia e retorna os DTOs
        medication_dto = build_medication_response_dto(updated_medication, updated_batches)

        movement_dto = StockMovementResponseDTO(
            id=str(saved_movement.id),
            medication_id=str(saved_movement.medication_id),
            batch_id=str(saved_movement.batch_id) if saved_movement.batch_id else None,
            batch_number=saved_movement.batch_number,
            movement_type=saved_movement.movement_type.value,
            quantity=saved_movement.quantity,
            previous_stock=saved_movement.previous_stock,
            new_stock=saved_movement.new_stock,
            reason=saved_movement.reason,
            created_at=saved_movement.created_at,
        )

        return medication_dto, movement_dto
