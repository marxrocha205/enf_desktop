"""CLI / Utilitário de Linha de Comando para Gestão de Medicamentos e Estoque.

Permite cadastrar medicamentos, executar comandos de atualização de estoque (Entrada, Saída, Ajuste)
e consultar o saldo e histórico de movimentações diretamente pelo terminal.
"""

import argparse
import sys
from typing import Optional

# Configura encoding no Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from infrastructure.database.connection import SessionLocal, init_db
from infrastructure.repositories.sqlalchemy_medication_repository import (
    SqlAlchemyMedicationRepository,
)
from application.dtos.medication_dto import (
    MedicationCreateInputDTO,
    MedicationUpdateInputDTO,
    StockUpdateCommandDTO,
)
from application.use_cases.create_medication import CreateMedicationUseCase
from application.use_cases.update_medication import UpdateMedicationUseCase
from application.use_cases.update_stock import UpdateStockCommandUseCase
from application.use_cases.list_medications import ListMedicationsUseCase
from domain.entities.medication import StockMovementType, StockStatus


def format_status(status: StockStatus) -> str:
    """Retorna uma formatação legível com ícone para o status do estoque."""
    if status == StockStatus.OK:
        return "[OK - SUFICIENTE]"
    elif status == StockStatus.LOW:
        return "[ALERTA - ESTOQUE BAIXO]"
    else:
        return "[CRÍTICO - ESGOTADO]"


def cmd_add(args: argparse.Namespace) -> None:
    """Comando: Cadastrar novo medicamento com entrada de estoque inicial."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        use_case = CreateMedicationUseCase(repository=repo)

        dto = MedicationCreateInputDTO(
            name=args.name,
            dosage=args.dosage,
            unit=args.unit,
            initial_stock=args.stock,
            minimum_stock=args.min_stock,
            description=args.desc,
        )

        medication = use_case.execute(dto)

        print("\n" + "=" * 65)
        print(" SUCESSO: MEDICAMENTO CADASTRADO COM ATUALIZAÇÃO DE ESTOQUE")
        print("=" * 65)
        print(f" ID:             {medication.id}")
        print(f" Nome:           {medication.name}")
        print(f" Dosagem:        {medication.dosage}")
        print(f" Unidade:        {medication.unit}")
        print(f" Saldo Atual:    {medication.current_stock} {medication.unit}(s)")
        print(f" Estoque Mínimo: {medication.minimum_stock}")
        print(f" Status:         {format_status(medication.stock_status)}")
        if medication.description:
            print(f" Descrição:      {medication.description}")
        if args.stock > 0:
            print(f" -> Comando de ENTRADA inicial de {args.stock} unidade(s) registrado no histórico!")
        print("=" * 65 + "\n")
    except Exception as err:
        print(f"\n[ERRO AO CADASTRAR]: {err}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def cmd_edit(args: argparse.Namespace) -> None:
    """Comando: Editar os dados cadastrais de um medicamento existente."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        use_case = UpdateMedicationUseCase(repository=repo)

        # Localiza o medicamento por ID ou Nome
        med_id = args.id
        if not med_id:
            if not args.name:
                print("Informe --id ou --name para identificar o medicamento.", file=sys.stderr)
                sys.exit(1)
            meds = repo.list_all(limit=100)
            matching = [m for m in meds if args.name.lower() in m.name.lower()]
            if not matching:
                print(f"Nenhum medicamento encontrado com o nome '{args.name}'.", file=sys.stderr)
                sys.exit(1)
            if len(matching) > 1 and not args.dosage:
                print("Foram encontrados múltiplos medicamentos correspondentes. Especifique --dosage ou use --id:")
                for m in matching:
                    print(f"  - ID: {m.id} | {m.name} ({m.dosage})")
                sys.exit(1)
            med_id = str(matching[0].id)

        dto = MedicationUpdateInputDTO(
            name=args.new_name,
            dosage=args.new_dosage,
            unit=args.new_unit,
            minimum_stock=args.new_min_stock,
            description=args.new_desc,
        )

        medication = use_case.execute(medication_id=med_id, dto=dto)

        print("\n" + "=" * 65)
        print(" SUCESSO: DADOS CADASTRAIS DO MEDICAMENTO ATUALIZADOS")
        print("=" * 65)
        print(f" ID:             {medication.id}")
        print(f" Nome:           {medication.name}")
        print(f" Dosagem:        {medication.dosage}")
        print(f" Unidade:        {medication.unit}")
        print(f" Saldo Atual:    {medication.current_stock} {medication.unit}(s)")
        print(f" Estoque Mínimo: {medication.minimum_stock}")
        print(f" Status:         {format_status(medication.stock_status)}")
        if medication.description:
            print(f" Descrição:      {medication.description}")
        if medication.updated_at:
            print(f" Atualizado em:  {medication.updated_at}")
        print("=" * 65 + "\n")
    except Exception as err:
        print(f"\n[ERRO AO ATUALIZAR DADOS CADASTRAIS]: {err}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def cmd_update_stock(args: argparse.Namespace) -> None:
    """Comando: Atualizar o estoque de um medicamento existente."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        use_case = UpdateStockCommandUseCase(repository=repo)

        # Localiza o medicamento por ID ou Nome
        med_id = args.id
        if not med_id:
            if not args.name:
                print("Informe --id ou --name para identificar o medicamento.", file=sys.stderr)
                sys.exit(1)
            # Busca pelo nome
            meds = repo.list_all(limit=100)
            matching = [m for m in meds if args.name.lower() in m.name.lower()]
            if not matching:
                print(f"Nenhum medicamento encontrado com o nome '{args.name}'.", file=sys.stderr)
                sys.exit(1)
            if len(matching) > 1 and not args.dosage:
                print(f"Foram encontrados múltiplos medicamentos correspondentes. Especifique --dosage ou use --id:")
                for m in matching:
                    print(f"  - ID: {m.id} | {m.name} ({m.dosage})")
                sys.exit(1)
            med_id = str(matching[0].id)

        movement_type = StockMovementType(args.type.upper())
        command_dto = StockUpdateCommandDTO(
            movement_type=movement_type,
            quantity=args.quantity,
            reason=args.reason or f"Comando CLI manual de {movement_type.value}",
        )

        medication, movement = use_case.execute(medication_id=med_id, command=command_dto)

        print("\n" + "=" * 65)
        print(f" COMANDO DE ESTOQUE EXECUTADO: {movement.movement_type}")
        print("=" * 65)
        print(f" Medicamento:    {medication.name} ({medication.dosage})")
        print(f" Estoque Prévio: {movement.previous_stock} {medication.unit}(s)")
        print(f" Movimentado:    {movement.quantity} {medication.unit}(s) [{movement.movement_type}]")
        print(f" Novo Saldo:     {medication.current_stock} {medication.unit}(s)")
        print(f" Status Atual:   {format_status(medication.stock_status)}")
        print(f" Motivo:         {movement.reason}")
        print(f" Data/Hora:      {movement.created_at}")
        print("=" * 65 + "\n")
    except Exception as err:
        print(f"\n[ERRO AO ATUALIZAR ESTOQUE]: {err}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def cmd_list(args: argparse.Namespace) -> None:
    """Comando: Listar medicamentos cadastrados."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        use_case = ListMedicationsUseCase(repository=repo)
        medications = use_case.list_all(low_stock_only=args.low_stock)

        print("\n" + "=" * 80)
        print(f" CATÁLOGO DE MEDICAMENTOS ({'ESTOQUE BAIXO' if args.low_stock else 'TODOS'}) - TOTAL: {len(medications)}")
        print("=" * 80)

        if not medications:
            print(" Nenhum medicamento encontrado com os critérios informados.")
        else:
            header = f"{'NOME':<25} {'DOSAGEM':<12} {'SALDO':<10} {'MÍN':<8} {'STATUS':<20}"
            print(header)
            print("-" * 80)
            for m in medications:
                status_str = format_status(m.stock_status)
                stock_str = f"{m.current_stock} {m.unit}"
                print(f"{m.name[:24]:<25} {m.dosage:<12} {stock_str:<10} {m.minimum_stock:<8} {status_str:<20}")

        print("=" * 80 + "\n")
    finally:
        db.close()


def cmd_history(args: argparse.Namespace) -> None:
    """Comando: Ver histórico de movimentações de um medicamento."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        use_case = ListMedicationsUseCase(repository=repo)

        med_id = args.id
        if not med_id and args.name:
            meds = repo.list_all(limit=100)
            matching = [m for m in meds if args.name.lower() in m.name.lower()]
            if matching:
                med_id = str(matching[0].id)
            else:
                print(f"Medicamento '{args.name}' não encontrado.", file=sys.stderr)
                sys.exit(1)

        if not med_id:
            print("Informe --id ou --name para ver o histórico.", file=sys.stderr)
            sys.exit(1)

        med = use_case.get_by_id(med_id)
        movements = use_case.get_movements(med_id, limit=args.limit)

        print("\n" + "=" * 80)
        print(f" HISTÓRICO DE ESTOQUE: {med.name} ({med.dosage}) - SALDO ATUAL: {med.current_stock} {med.unit}(s)")
        print("=" * 80)

        if not movements:
            print(" Nenhuma movimentação registrada.")
        else:
            header = f"{'DATA/HORA':<22} {'TIPO':<10} {'QTD':<6} {'ANTERIOR':<10} {'NOVO':<8} {'MOTIVO'}"
            print(header)
            print("-" * 80)
            for mov in movements:
                dt_str = mov.created_at.strftime("%d/%m/%Y %H:%M")
                reason_str = mov.reason or "-"
                print(f"{dt_str:<22} {mov.movement_type:<10} {mov.quantity:<6} {mov.previous_stock:<10} {mov.new_stock:<8} {reason_str}")

        print("=" * 80 + "\n")
    finally:
        db.close()


def main() -> None:
    """Ponto de entrada do CLI de gestão de medicamentos."""
    init_db()

    parser = argparse.ArgumentParser(
        description="Sistema de Gestão de Medicamentos e Controle de Estoque (IoT Medical API)"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comando a ser executado")

    # Subcomando: add
    parser_add = subparsers.add_parser("add", help="Cadastra um medicamento e atualiza o estoque inicial")
    parser_add.add_argument("--name", required=True, help="Nome do medicamento (ex: 'Dipirona')")
    parser_add.add_argument("--dosage", required=True, help="Dosagem (ex: '500mg')")
    parser_add.add_argument("--unit", default="comprimido", help="Unidade de medida (padrão: comprimido)")
    parser_add.add_argument("--stock", type=int, default=0, help="Quantidade inicial em estoque")
    parser_add.add_argument("--min-stock", type=int, default=10, help="Estoque mínimo de segurança")
    parser_add.add_argument("--desc", default=None, help="Descrição / Instruções de uso")
    parser_add.set_defaults(func=cmd_add)

    # Subcomando: edit
    parser_edit = subparsers.add_parser("edit", help="Edita os dados cadastrais de um medicamento existente")
    parser_edit.add_argument("--id", default=None, help="UUID do medicamento")
    parser_edit.add_argument("--name", default=None, help="Nome atual para busca do medicamento")
    parser_edit.add_argument("--dosage", default=None, help="Dosagem atual para refinar a busca")
    parser_edit.add_argument("--new-name", default=None, help="Novo nome do medicamento")
    parser_edit.add_argument("--new-dosage", default=None, help="Nova dosagem")
    parser_edit.add_argument("--new-unit", default=None, help="Nova unidade de apresentação")
    parser_edit.add_argument("--new-min-stock", type=int, default=None, help="Novo estoque mínimo de segurança")
    parser_edit.add_argument("--new-desc", default=None, help="Nova descrição / instruções")
    parser_edit.set_defaults(func=cmd_edit)

    # Subcomando: update-stock
    parser_update = subparsers.add_parser("update-stock", help="Executa comando de atualização de estoque")
    parser_update.add_argument("--id", default=None, help="UUID do medicamento")
    parser_update.add_argument("--name", default=None, help="Nome para busca do medicamento")
    parser_update.add_argument("--dosage", default=None, help="Dosagem para refinar a busca")
    parser_update.add_argument("--quantity", type=int, required=True, help="Quantidade da movimentação")
    parser_update.add_argument(
        "--type",
        choices=["ENTRADA", "SAIDA", "AJUSTE", "entrada", "saida", "ajuste"],
        default="ENTRADA",
        help="Tipo de comando (ENTRADA, SAIDA, AJUSTE)",
    )
    parser_update.add_argument("--reason", default=None, help="Motivo/Justificativa da movimentação")
    parser_update.set_defaults(func=cmd_update_stock)

    # Subcomando: list
    parser_list = subparsers.add_parser("list", help="Lista medicamentos cadastrados")
    parser_list.add_argument("--low-stock", action="store_true", help="Filtrar apenas estoque baixo ou zerado")
    parser_list.set_defaults(func=cmd_list)

    # Subcomando: history
    parser_history = subparsers.add_parser("history", help="Consulta histórico de movimentações")
    parser_history.add_argument("--id", default=None, help="UUID do medicamento")
    parser_history.add_argument("--name", default=None, help="Nome do medicamento")
    parser_history.add_argument("--limit", type=int, default=20, help="Quantidade máxima de registros")
    parser_history.set_defaults(func=cmd_history)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
