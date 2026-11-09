"""Data Transfer Objects (DTOs) para cadastro de medicamentos, lotes, validade e comandos de estoque."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from domain.entities.medication import (
    AlertLedColor,
    ExpirationStatus,
    Medication,
    MedicationBatch,
    StockMovementType,
    StockStatus,
)


class MedicationBatchCreateInputDTO(BaseModel):
    """Payload de entrada para cadastrar um novo lote de um medicamento (ex: 50 caixas de Dipirona)."""

    batch_number: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Código identificador do lote na embalagem (ex: LOTE-2026A)",
        examples=["LOTE-2026A"],
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Quantidade de caixas/unidades recebidas neste lote",
        examples=[50],
    )
    expiration_date: date = Field(
        ...,
        description="Data de validade impressa no lote (formato YYYY-MM-DD)",
        examples=["2027-08-15"],
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Observação ou nota fiscal de entrada do lote",
        examples=["Entrada do lote com 50 caixas"],
    )


class MedicationBatchResponseDTO(BaseModel):
    """DTO de resposta com detalhes de um lote específico, vínculo com o medicamento e validade."""

    id: str = Field(description="UUID do lote")
    medication_id: str = Field(description="UUID do medicamento ao qual o lote pertence")
    medication_name: Optional[str] = Field(
        default=None, description="Nome do medicamento deste lote"
    )
    medication_dosage: Optional[str] = Field(
        default=None, description="Dosagem do medicamento deste lote"
    )
    batch_number: str = Field(description="Código do lote")
    quantity: int = Field(description="Saldo atual disponível neste lote")
    expiration_date: date = Field(description="Data de validade do lote")
    days_until_expiration: int = Field(description="Dias restantes até vencer (negativo se vencido)")
    is_expired: bool = Field(description="Indica se o lote está vencido")
    expiration_status: ExpirationStatus = Field(
        description="Status de validade do lote (VALID, EXPIRING_SOON, EXPIRED)"
    )
    created_at: datetime = Field(description="Data de registro do lote")


class MedicationCreateInputDTO(BaseModel):
    """Payload de entrada para cadastro de um novo medicamento (com lote inicial opcional)."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nome comercial ou genérico do medicamento",
        examples=["Dipirona Monoidratada"],
    )
    dosage: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Dosagem do medicamento",
        examples=["500mg"],
    )
    unit: str = Field(
        default="comprimido",
        max_length=30,
        description="Unidade de medida ou apresentação (ex: caixa, comprimido, ampola)",
        examples=["caixa", "comprimido", "gotas", "ml", "ampola"],
    )
    initial_stock: int = Field(
        default=0,
        ge=0,
        description="Estoque inicial a ser lançado automaticamente no primeiro lote",
        examples=[50],
    )
    minimum_stock: int = Field(
        default=10,
        ge=0,
        description="Estoque mínimo de segurança para alertas de reposição",
        examples=[10],
    )
    batch_number: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Código do lote inicial (se omitido, gera um código automático LOTE-INICIAL)",
        examples=["LOTE-2026-01"],
    )
    expiration_date: Optional[date] = Field(
        default=None,
        description="Data de validade do lote inicial (formato YYYY-MM-DD)",
        examples=["2027-12-31"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Indicações, modo de uso ou observações clínicas",
        examples=["Antitérmico e analgésico indicado para episódios de febre acima de 37.8°C."],
    )


class MedicationUpdateInputDTO(BaseModel):
    """Payload para atualização dos dados cadastrais do medicamento."""

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Nome comercial ou genérico do medicamento",
        examples=["Dipirona Sódica"],
    )
    dosage: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Dosagem do medicamento",
        examples=["1g"],
    )
    unit: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Unidade de medida ou apresentação",
        examples=["caixa", "comprimido", "gotas", "ml", "ampola"],
    )
    minimum_stock: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estoque mínimo de segurança para alertas de reposição",
        examples=[15],
    )
    description: Optional[str] = Field(
        default=None,
        description="Indicações, modo de uso ou observações clínicas",
        examples=["Uso sob prescrição médica."],
    )


class StockUpdateCommandDTO(BaseModel):
    """Comando de movimentação e atualização de estoque com suporte a Lote e Validade."""

    movement_type: StockMovementType = Field(
        ...,
        description="Tipo de movimentação (ENTRADA, SAIDA, AJUSTE)",
        examples=["ENTRADA"],
    )
    quantity: int = Field(
        ...,
        ge=0,
        description="Quantidade a adicionar/subtrair ou novo saldo exato em caso de AJUSTE",
        examples=[20],
    )
    batch_number: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Código do lote (opcional na SAÍDA para usar FEFO automático; recomendado na ENTRADA)",
        examples=["LOTE-2026A"],
    )
    expiration_date: Optional[date] = Field(
        default=None,
        description="Data de validade do lote em comandos de ENTRADA (formato YYYY-MM-DD)",
        examples=["2027-08-15"],
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Motivo ou justificativa do comando de movimentação",
        examples=["Entrada de novo lote com 50 caixas", "Administrado para controle de febre do paciente"],
    )


class StockMovementResponseDTO(BaseModel):
    """DTO de resposta para uma transação de movimentação de estoque."""

    id: str = Field(description="UUID da movimentação")
    medication_id: str = Field(description="UUID do medicamento")
    batch_id: Optional[str] = Field(default=None, description="UUID do lote movimentado")
    batch_number: Optional[str] = Field(default=None, description="Código do lote movimentado")
    movement_type: str = Field(description="Tipo de movimentação realizada")
    quantity: int = Field(description="Quantidade movimentada")
    previous_stock: int = Field(description="Estoque anterior à operação")
    new_stock: int = Field(description="Novo saldo resultante")
    reason: Optional[str] = Field(default=None, description="Justificativa")
    created_at: datetime = Field(description="Data e hora da operação")


class MedicationResponseDTO(BaseModel):
    """DTO de resposta com dados cadastrais, saldo atual, lotes, validade e cor do LED de aviso."""

    id: str = Field(description="Identificador único UUID do medicamento")
    name: str = Field(description="Nome do medicamento")
    dosage: str = Field(description="Dosagem")
    unit: str = Field(description="Unidade de apresentação")
    current_stock: int = Field(description="Saldo atual em estoque")
    minimum_stock: int = Field(description="Estoque mínimo configurado")
    stock_status: StockStatus = Field(description="Status do estoque (OK, LOW, OUT_OF_STOCK)")
    nearest_expiration_date: Optional[date] = Field(
        default=None,
        description="Data de validade mais próxima dentre os lotes com saldo",
    )
    expiration_status: ExpirationStatus = Field(
        default=ExpirationStatus.VALID,
        description="Status de validade dos lotes ativos (VALID, EXPIRING_SOON, EXPIRED)",
    )
    expired_stock: int = Field(
        default=0,
        description="Quantidade retida em lotes já vencidos",
    )
    alert_led: AlertLedColor = Field(
        default=AlertLedColor.GREEN,
        description="Cor do LED de aviso para o Arduino (GREEN, YELLOW, RED)",
    )
    batches: List[MedicationBatchResponseDTO] = Field(
        default_factory=list,
        description="Lista de lotes deste medicamento ordenados por data de validade (FEFO)",
    )
    description: Optional[str] = Field(default=None, description="Instruções e descrição")
    created_at: datetime = Field(description="Data de cadastro")
    updated_at: Optional[datetime] = Field(default=None, description="Data da última alteração de estoque")


class QRCodeScanInputDTO(BaseModel):
    """Payload de entrada com o conteúdo bruto lido pelo scanner de QR Code."""

    raw_data: str = Field(
        ...,
        min_length=1,
        description="Conteúdo bruto decodificado do QR Code (JSON, formato separado por pipe ou ID/nome/lote)",
        examples=['{"name": "Dipirona", "dosage": "500mg", "unit": "caixa", "initial_stock": 50, "batch_number": "LOTE-2026A", "expiration_date": "2027-08-15"}'],
    )


class QRCodeParsedMedicationDTO(BaseModel):
    """Dados extraídos do QR Code prontos para pré-preenchimento de cadastro."""

    id: Optional[str] = None
    name: str = ""
    dosage: str = ""
    unit: str = "comprimido"
    initial_stock: int = 50
    minimum_stock: int = 15
    batch_number: Optional[str] = None
    expiration_date: Optional[date] = None
    description: Optional[str] = None


class QRCodeResolveResponseDTO(BaseModel):
    """Resposta da interpretação de um QR Code de medicamento ou de uma caixa de um lote específico."""

    found: bool = Field(description="Indica se o medicamento já está cadastrado no catálogo")
    medication: Optional[MedicationResponseDTO] = Field(
        default=None,
        description="Dados completos, lotes e estoque atual caso o medicamento já esteja cadastrado",
    )
    matched_batch: Optional[MedicationBatchResponseDTO] = Field(
        default=None,
        description="Lote específico identificado na leitura da caixa/QR Code (quando a caixa indica seu lote)",
    )
    parsed_data: QRCodeParsedMedicationDTO = Field(
        description="Dados interpretados do QR Code para preenchimento automático"
    )
    raw_data: str = Field(description="Conteúdo original lido do QR Code")


def build_batch_response_dto(
    batch: MedicationBatch,
    medication: Optional[Medication] = None,
) -> MedicationBatchResponseDTO:
    """Converte a entidade MedicationBatch para MedicationBatchResponseDTO com identificação do medicamento."""
    return MedicationBatchResponseDTO(
        id=str(batch.id),
        medication_id=str(batch.medication_id),
        medication_name=medication.name if medication else None,
        medication_dosage=medication.dosage if medication else None,
        batch_number=batch.batch_number,
        quantity=batch.quantity,
        expiration_date=batch.expiration_date,
        days_until_expiration=batch.days_until_expiration,
        is_expired=batch.is_expired,
        expiration_status=batch.expiration_status,
        created_at=batch.created_at,
    )


def build_medication_response_dto(
    medication: Medication,
    batches: Optional[List[MedicationBatch]] = None,
) -> MedicationResponseDTO:
    """Constrói o MedicationResponseDTO consolidando lotes, validade mais próxima e cor do LED Arduino."""
    batch_list = batches or []
    batch_dtos = [build_batch_response_dto(b, medication=medication) for b in batch_list]

    active_batches = [b for b in batch_list if b.quantity > 0]
    expired_batches = [b for b in active_batches if b.is_expired]
    expiring_soon_batches = [
        b for b in active_batches if b.expiration_status == ExpirationStatus.EXPIRING_SOON
    ]

    expired_stock = sum(b.quantity for b in expired_batches)
    nearest_exp: Optional[date] = None
    if active_batches:
        nearest_exp = min(b.expiration_date for b in active_batches)
    elif batch_list:
        nearest_exp = min(b.expiration_date for b in batch_list)

    # Classifica o status geral de validade dos lotes ativos
    if expired_batches:
        exp_status = ExpirationStatus.EXPIRED
    elif expiring_soon_batches:
        exp_status = ExpirationStatus.EXPIRING_SOON
    else:
        exp_status = ExpirationStatus.VALID

    # Determina a cor do LED de aviso para o Arduino:
    # RED    -> Estoque zerado OU existe lote ativo vencido
    # YELLOW -> Estoque baixo (<= mínimo) OU existe lote vencendo em <= 30 dias
    # GREEN  -> Estoque OK e todos os lotes dentro da validade
    if medication.stock_status == StockStatus.OUT_OF_STOCK or exp_status == ExpirationStatus.EXPIRED:
        led_color = AlertLedColor.RED
    elif medication.stock_status == StockStatus.LOW or exp_status == ExpirationStatus.EXPIRING_SOON:
        led_color = AlertLedColor.YELLOW
    else:
        led_color = AlertLedColor.GREEN

    return MedicationResponseDTO(
        id=str(medication.id),
        name=medication.name,
        dosage=medication.dosage,
        unit=medication.unit,
        current_stock=medication.current_stock,
        minimum_stock=medication.minimum_stock,
        stock_status=medication.stock_status,
        nearest_expiration_date=nearest_exp,
        expiration_status=exp_status,
        expired_stock=expired_stock,
        alert_led=led_color,
        batches=batch_dtos,
        description=medication.description,
        created_at=medication.created_at,
        updated_at=medication.updated_at,
    )
