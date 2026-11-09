"""Endpoints de Cadastro de Medicamentos, Lotes com Validade e Comandos de Atualização de Estoque."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from application.dtos.medication_dto import (
    MedicationBatchCreateInputDTO,
    MedicationBatchResponseDTO,
    MedicationCreateInputDTO,
    MedicationUpdateInputDTO,
    StockUpdateCommandDTO,
    MedicationResponseDTO,
    StockMovementResponseDTO,
    QRCodeScanInputDTO,
    QRCodeResolveResponseDTO,
)
from application.use_cases.create_medication import CreateMedicationUseCase
from application.use_cases.update_medication import UpdateMedicationUseCase
from application.use_cases.delete_medication import DeleteMedicationUseCase
from application.use_cases.update_stock import UpdateStockCommandUseCase
from application.use_cases.list_medications import ListMedicationsUseCase
from domain.interfaces.medication_repository import IMedicationRepository
from infrastructure.database.connection import get_db
from infrastructure.repositories.sqlalchemy_medication_repository import (
    SqlAlchemyMedicationRepository,
)

router = APIRouter(prefix="/medications", tags=["Medicamentos, Lotes & Estoque"])


def get_medication_repository(
    db: Session = Depends(get_db),
) -> IMedicationRepository:
    """Provedor de injeção de dependência para o repositório de medicamentos."""
    return SqlAlchemyMedicationRepository(db=db)


@router.post(
    "/",
    response_model=MedicationResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Medicamento (com Lote Inicial e Validade)",
    description="Cadastra um novo medicamento no catálogo, cria o primeiro lote com data de validade e dispara o comando de entrada de estoque inicial.",
)
def create_medication(
    dto: MedicationCreateInputDTO,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> MedicationResponseDTO:
    """Executa o caso de uso de cadastro de medicamento e registro automático de lote/estoque."""
    use_case = CreateMedicationUseCase(repository=repo)
    return use_case.execute(dto)


@router.post(
    "/qrcode/resolve",
    response_model=QRCodeResolveResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Interpretar e Resolver Leitura de QR Code (Medicamento ou Lote)",
    description="Interpreta o texto/JSON lido de um QR Code, verifica se o medicamento/lote já existe no estoque e retorna os dados com validade e LED de alerta.",
)
def resolve_medication_qrcode(
    dto: QRCodeScanInputDTO,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> QRCodeResolveResponseDTO:
    """Resolve o conteúdo lido de um QR Code de medicamento ou lote."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.resolve_qrcode(raw_data=dto.raw_data)


@router.get(
    "/batches/lookup/{batch_number}",
    response_model=MedicationBatchResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Consultar a qual Lote e Medicamento pertence um Código de Lote",
    description="Identifica imediatamente de qual lote e de qual medicamento é uma caixa/embalagem a partir do código do lote.",
)
def lookup_batch_by_code(
    batch_number: str,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> MedicationBatchResponseDTO:
    """Retorna o lote, validade e o medicamento correspondente ao código informado."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.get_batch_by_code(batch_number=batch_number)


@router.post(
    "/{medication_id}/batches",
    response_model=MedicationBatchResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Novo Lote com Validade para o Medicamento",
    description="Registra a chegada de um novo lote do medicamento (ex: 50 caixas de Dipirona com validade) e incrementa automaticamente o estoque total.",
)
def create_medication_batch(
    medication_id: str,
    dto: MedicationBatchCreateInputDTO,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> MedicationBatchResponseDTO:
    """Cadastra um novo lote vinculado ao medicamento e lança a entrada de estoque."""
    use_case = UpdateStockCommandUseCase(repository=repo)
    _, batch_dto, _ = use_case.create_batch(medication_id=medication_id, dto=dto)
    return batch_dto


@router.get(
    "/{medication_id}/batches",
    response_model=List[MedicationBatchResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Listar Lotes e Validades do Medicamento (FEFO)",
    description="Retorna todos os lotes cadastrados para o medicamento ordenados pela data de validade mais próxima (First Expired, First Out).",
)
def list_medication_batches(
    medication_id: str,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> List[MedicationBatchResponseDTO]:
    """Lista os lotes do medicamento com dias para vencer e status de validade."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.get_batches(medication_id=medication_id)


@router.post(
    "/{medication_id}/stock",
    response_model=StockMovementResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Comando de Atualização de Estoque (com Regra FEFO e Bloqueio de Vencidos)",
    description="Executa um comando de movimentação física no estoque (ENTRADA, SAÍDA ou AJUSTE). Na SAÍDA, bloqueia lotes vencidos e desconta do lote válido que vence primeiro.",
)
def update_stock(
    medication_id: str,
    command: StockUpdateCommandDTO,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> StockMovementResponseDTO:
    """Executa o comando de atualização de estoque com cálculo de saldo, validação de lote/validade e auditoria."""
    use_case = UpdateStockCommandUseCase(repository=repo)
    _, movement = use_case.execute(medication_id=medication_id, command=command)
    return movement


@router.get(
    "/",
    response_model=List[MedicationResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Listar Medicamentos em Catálogo (com Lotes, Validade e LED de Aviso)",
    description="Retorna a lista de medicamentos cadastrados com seus saldos de estoque, lotes, validade mais próxima e cor do LED de alerta para o Arduino.",
)
def list_medications(
    limit: int = Query(100, ge=1, le=500, description="Quantidade máxima de registros"),
    offset: int = Query(0, ge=0, description="Deslocamento para paginação"),
    low_stock_only: bool = Query(
        False, description="Filtrar apenas medicamentos com estoque baixo ou zerado"
    ),
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> List[MedicationResponseDTO]:
    """Lista medicamentos com filtro opcional de estoque crítico."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.list_all(limit=limit, offset=offset, low_stock_only=low_stock_only)


@router.get(
    "/{medication_id}",
    response_model=MedicationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Detalhes do Medicamento e seus Lotes",
    description="Recupera o cadastro completo, os lotes com validade e o saldo atual de estoque de um medicamento.",
)
def get_medication_by_id(
    medication_id: str,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> MedicationResponseDTO:
    """Busca dados de um medicamento específico."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.get_by_id(medication_id=medication_id)


@router.put(
    "/{medication_id}",
    response_model=MedicationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Dados do Medicamento (PUT)",
    description="Atualiza as informações cadastrais do medicamento (nome, dosagem, unidade, estoque mínimo, descrição).",
)
@router.patch(
    "/{medication_id}",
    response_model=MedicationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Dados do Medicamento (PATCH)",
    description="Atualização parcial das informações cadastrais do medicamento.",
)
def update_medication(
    medication_id: str,
    dto: MedicationUpdateInputDTO,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> MedicationResponseDTO:
    """Atualiza as informações cadastrais de um medicamento."""
    use_case = UpdateMedicationUseCase(repository=repo)
    return use_case.execute(medication_id=medication_id, dto=dto)


@router.get(
    "/{medication_id}/movements",
    response_model=List[StockMovementResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Histórico de Movimentações de Estoque (com Rastreio de Lote)",
    description="Retorna todas as operações de entrada, saída e ajustes já realizadas para o medicamento, incluindo o código do lote utilizado.",
)
def get_medication_movements(
    medication_id: str,
    limit: int = Query(50, ge=1, le=200, description="Limite de registros retornados"),
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> List[StockMovementResponseDTO]:
    """Recupera o histórico cronológico de transações de estoque."""
    use_case = ListMedicationsUseCase(repository=repo)
    return use_case.get_movements(medication_id=medication_id, limit=limit)


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_200_OK,
    summary="Apagar Cadastro de Medicamento",
    description="Remove definitivamente o cadastro de um medicamento, todos os seus lotes e seu histórico de movimentações de estoque.",
)
def delete_medication(
    medication_id: str,
    repo: IMedicationRepository = Depends(get_medication_repository),
) -> Dict[str, Any]:
    """Executa o caso de uso de exclusão do cadastro do medicamento."""
    use_case = DeleteMedicationUseCase(repository=repo)
    return use_case.execute(medication_id=medication_id)
